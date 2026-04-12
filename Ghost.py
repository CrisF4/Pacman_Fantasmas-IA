import pygame
from pygame.locals import *

# Cargamos las bibliotecas de OpenGL
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import math
import os
import numpy as np
import pandas as pd
import random
import time

class Ghost:
    def __init__(self,mapa, mc, x_mc, y_mc, xini, yini, dir, tipo):
        #Matriz de control que almacena los IDs de las intersecciones
        self.MC = mc
        #Vectores que almacenan las coordenadas 
        self.XPxToMC = x_mc
        self.YPxToMC = y_mc
        #se resplanda el mapa en terminos de pixeles
        self.mapa = mapa
        #se inicializa la posicion del fantasma en terminos de pixeles
        self.position = []
        self.position.append(xini)
        self.position.append(1) #YPos
        self.position.append(yini)
        #se define el arreglo para la posicion en la matriz de control
        self.positionMC = []
        self.positionMC.append(self.XPxToMC[self.position[0] - 20]) #coord en x
        self.positionMC.append(self.YPxToMC[self.position[2] - 20]) #coord en y (eje z en realidad)
        #se inicializa una direccion valida
        self.direction = dir
        #se almacena que tipo de fantasma sera:
        #0: fantasma aleatorio
        #1: fantasma con pathfinding
        self.tipo = tipo
        #arreglo para almacenar las opciones del fantasma
        self.options = [
            [1,2],
            [2,3],
            [0,1],
            [0,3],
            [1,2,3],
            [0,2,3],
            [0,1,3],
            [0,1,2],
            [0,1,2,3],
            [1],
            [3]
        ]
        self.option = []
        self.dir_inv = 0
        self.tabu_list = []

        # Parametros de busqueda por tipo de agente
        self.depth_base_solo = 4
        self.depth_base_manada = 3
        self.time_budget_ms_solo = 6
        self.time_budget_ms_manada = 8
        self.tabu_max_len = 6

        # Tabla de transposicion y metricas basicas
        self.transposition_table = {}
        self.transposition_max_size = 50000
        self.nodes_expanded = 0
        self.cache_hits = 0
        self.last_decision_ms = 0.0
        self.debug_ai = True
        
        # Margen epsilon para Poda de Inutilidades
        self.epsilon = 0.2
        
    def loadTextures(self, texturas, id):
        self.texturas = texturas
        self.Id = id

    def drawFace(self, x1, y1, z1, x2, y2, z2, x3, y3, z3, x4, y4, z4):
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 0.0)
        glVertex3f(x1, y1, z1)
        glTexCoord2f(0.0, 1.0)
        glVertex3f(x2, y2, z2)
        glTexCoord2f(1.0, 1.0)
        glVertex3f(x3, y3, z3)
        glTexCoord2f(1.0, 0.0)
        glVertex3f(x4, y4, z4)
        glEnd()

    # Correcion importante de esta funcion: 
    def _safe_mc_from_pixel(self, px, pz):
        # Offset de 20 px restado para alinearse con la matriz de control
        x_idx = px - 20
        y_idx = pz - 20

        # Funcion para encontrar el valor de la celda mas cercana que no sea -1 (no transitable)
        def nearest_valid(arr, idx):
            if idx < 0: idx = 0
            if idx >= len(arr): idx = len(arr) - 1
            if arr[idx] != -1: return int(arr[idx]) # Si el indice directo es un valor que representa una celda de interseccion, se retorna inmediatamente.
            # Radar de expansion: se busca hacia afuera desde el indice dado para encontrar el valor de interseccion más cercano que no sea -1.
            for r in range(1, len(arr)):
                if idx - r >= 0 and arr[idx - r] != -1:
                    return int(arr[idx - r])
                if idx + r < len(arr) and arr[idx + r] != -1:
                    return int(arr[idx + r])
            return -1

        return nearest_valid(self.XPxToMC, x_idx), nearest_valid(self.YPxToMC, y_idx)

    def _is_valid_mc(self, x, y):
        if y < 0 or y >= len(self.MC):
            return False
        if x < 0 or x >= len(self.MC[0]):
            return False
        return self.MC[y][x] != -1

    def _cell_id(self, x, y):
        if not self._is_valid_mc(x, y):
            return -1
        return int(self.MC[y][x])

    def _allowed_dirs(self, cell_id):
        mapping = {
            0: [0, 1, 2, 3],
            10: [1, 2],
            11: [2, 3],
            12: [0, 1],
            13: [0, 3],
            21: [1, 2, 3],
            22: [0, 2, 3],
            23: [0, 1, 3],
            24: [0, 1, 2],
            25: [0, 1, 2, 3],
            26: [1],
            27: [3],
        }
        return list(mapping.get(cell_id, []))

    def _opposite_dir(self, direction):
        if direction == 0:
            return 2
        if direction == 1:
            return 3
        if direction == 2:
            return 0
        if direction == 3:
            return 1
        return -1

    def _next_mc(self, x, y, direction):
        if direction == 0:
            return x, y - 1
        if direction == 1:
            return x + 1, y
        if direction == 2:
            return x, y + 1
        if direction == 3:
            return x - 1, y
        return x, y

    def _count_exits(self, x, y):
        """
        Cuenta el número de salidas disponibles desde la celda de intersección dada por (x, y) en la matriz de control.
        """
        return max(1, len(self._allowed_dirs(self._cell_id(x, y))))

    def _update_tabu(self, tabu_list, mc_pos):
        if mc_pos in tabu_list:
            tabu_list.remove(mc_pos)
        tabu_list.append(mc_pos)
        if len(tabu_list) > self.tabu_max_len:
            tabu_list.pop(0)
        return tabu_list

    def _move_pixel_step(self, direction):
        self.direction = direction
        if self.direction == 0:
            self.position[2] -= 1
        elif self.direction == 1:
            self.position[0] += 1
        elif self.direction == 2:
            self.position[2] += 1
        elif self.direction == 3:
            self.position[0] -= 1

    def _timeout_reached(self, t0, budget_ms):
        return ((time.perf_counter() - t0) * 1000.0) >= budget_ms

    def _trim_transposition(self):
        if len(self.transposition_table) > self.transposition_max_size:
            self.transposition_table.clear()

    def _debug_print_ai_metrics(self, mode, root_mc=None, selected_dir=None, depth_used=None, timeout_hit=False, note="", branch_factor=0, best_score=0.0):
        """
        Imprime información detallada sobre la decisión de la IA para propósitos de depuración y análisis.
        Cuidar que se estan imprimiendo las coordenadas logicas en orden [X,Y] para su facil interpretación, aunque en realidad
        sean [X,Z] e internamente se pasan a logica [Y,X] al pasar por las funciones auxiliares que traducen entre pixeles y matriz de control. 
        """
        
        if not self.debug_ai:
            return
        mc_text = "n/a"
        if root_mc is not None:
            mc_text = f"({root_mc[0]}, {root_mc[1]})"

        extra_info = ""
        if mode.startswith("alpha_beta"):
            extra_info = f" score={best_score:.2f} branches={branch_factor}"

        print(
            f"[Fantasma {self.tipo}] mode={mode} mc={mc_text} dir={selected_dir} "
            f"depth={depth_used} time_ms={self.last_decision_ms:.3f} "
            f"nodes={self.nodes_expanded} cache_hits={self.cache_hits} tabu={len(self.tabu_list)} "
            f"tt={len(self.transposition_table)} timeout={timeout_hit}{extra_info} {note}"
        )

    def _debug_print_collision(self, pacman_position, distance):
        if not self.debug_ai:
            return
        print(
            f"[COLLISION][Fantasma {self.tipo}] ghost_px={self.position[0]} ghost_pz={self.position[2]} "
            f"pacman_px={pacman_position[0]} pacman_pz={pacman_position[2]} dist={distance:.3f}"
        )
   
    def sigue_adelante(self):
        #si el fantasma esta en un tunel, no es necesario calcular la siguiente posicion a traves del path
        #solo se sigue la direccion actual y se aumenta el contador que accede a la posicion del path actual
        if self.direction == 0: #up
            self.position[2] -= 1
        elif self.direction == 1: #right
            self.position[0] += 1
        elif self.direction == 2: #down
            self.position[2] += 1
        else: #left
            self.position[0] -= 1
            
        # Nota: Se eliminó el bloque (if self.tipo == 1: self.path_n += 1) 
        # ya que la IA por Alfa-Beta decidirá su movimiento dinámicamente en 
        # cada intersección y ya no necesita recorrer con un índice rutas precalculadas.
        
    def path_ia(self,pacmanXY, all_ghosts):
        # bloque para implementar la IA en los fantasmas
        if self.tipo == 0:
            # Blinky - Movimiento aleatorio
            self.interseccion_random()
        elif self.tipo == 1:
            # Pinky - Poda Alfa-Beta en solitario
            self.alpha_beta_solo(pacmanXY)
        elif self.tipo in [2, 3]:
            # Inky y Clyde - Poda Alfa-Beta colaborativa (caza en manada)
            partner = None
            for g in all_ghosts:
                if g != self and g.tipo in [2, 3]:
                    partner = g
                    break
            self.alpha_beta_manada(pacmanXY, partner)
            
    # === Algoritmos de busqueda y funciones de evaluacion heuristica para los fantasmas de tipo 1, 2 y 3: ===

    def alpha_beta_solo(self, pacmanXY):
        """
        Logica de Poda Alfa-Beta para Pinky (Solitario).
        Aquí se debe construir el arbol simulando el movimiento de este único fantasma
        y el jugador Pacman.
        """
        gx, gy = self._safe_mc_from_pixel(self.position[0], self.position[2])
        px, py = self._safe_mc_from_pixel(pacmanXY[0], pacmanXY[2])
        if not self._is_valid_mc(gx, gy) or not self._is_valid_mc(px, py):
            self.interseccion_random()
            return

        self._trim_transposition()
        self.nodes_expanded = 0
        self.cache_hits = 0

        t0 = time.perf_counter()
        best_dir_global = None
        timeout_hit = False

        """
        Función recursiva para la búsqueda Alfa-Beta en caza solitaria. El estado se representa como un diccionario que contiene las coordenadas
        y direcciones actuales del fantasma y Pacman, así como las listas tabu para ambos. La función evalúa si se ha alcanzado 
        el tiempo límite o la profundidad máxima, y en ese caso retorna la evaluación heurística del estado. 
        Si no, genera los hijos (movimientos posibles) para el jugador actual (maximizador o minimizador) y recursivamente 
        evalúa cada uno, aplicando la poda alfa-beta según corresponda.
        """
        def alpha_beta_rec(state, depth, alpha, beta, is_max):
            nonlocal best_dir_global, timeout_hit
            # Bajada progresiva
            if self._timeout_reached(t0, self.time_budget_ms_solo):
                timeout_hit = True
                return self.eval_heuristic_pinky((state["gx"], state["gy"]), (state["px"], state["py"]))

            # Captura simulada o profundidad máxima alcanzada
            if depth == 0 or ((state["gx"], state["gy"]) == (state["px"], state["py"])):
                return self.eval_heuristic_pinky((state["gx"], state["gy"]), (state["px"], state["py"]))

            key = (
                state["gx"], state["gy"], state["gdir"],
                state["px"], state["py"], state["pdir"],
                depth, is_max
            )
            if key in self.transposition_table:
                self.cache_hits += 1
                return self.transposition_table[key]

            self.nodes_expanded += 1
            if is_max:
                best_val = -float("inf")
                children = self.generar_hijos({
                    "x": state["gx"],
                    "y": state["gy"],
                    "prev_dir": state["gdir"],
                    "tabu": state["tabu_g"],
                })
                if not children:
                    return self.eval_heuristic_pinky((state["gx"], state["gy"]), (state["px"], state["py"]))

                for child in children:
                    tabu_g = list(state["tabu_g"])
                    self._update_tabu(tabu_g, (child["x"], child["y"]))
                    next_state = {
                        "gx": child["x"], "gy": child["y"], "gdir": child["dir"],
                        "px": state["px"], "py": state["py"], "pdir": state["pdir"],
                        "tabu_g": tabu_g, "tabu_p": list(state["tabu_p"])
                    }
                    value = alpha_beta_rec(next_state, depth - 1, alpha, beta, False)
                    if value > best_val:
                        best_val = value
                        if depth == current_depth:
                            best_dir_global = child["dir"]
                    alpha = max(alpha, best_val)
                    if beta <= alpha + self.epsilon:
                        break
            else:
                best_val = float("inf")
                children = self.generar_hijos({
                    "x": state["px"],
                    "y": state["py"],
                    "prev_dir": state["pdir"],
                    "tabu": state["tabu_p"],
                })
                if not children:
                    return self.eval_heuristic_pinky((state["gx"], state["gy"]), (state["px"], state["py"]))

                for child in children:
                    tabu_p = list(state["tabu_p"])
                    self._update_tabu(tabu_p, (child["x"], child["y"]))
                    next_state = {
                        "gx": state["gx"], "gy": state["gy"], "gdir": state["gdir"],
                        "px": child["x"], "py": child["y"], "pdir": child["dir"],
                        "tabu_g": list(state["tabu_g"]), "tabu_p": tabu_p
                    }
                    value = alpha_beta_rec(next_state, depth - 1, alpha, beta, True)
                    best_val = min(best_val, value)
                    beta = min(beta, best_val)
                    if beta <= alpha + self.epsilon:
                        break

            self.transposition_table[key] = best_val
            return best_val

        root_state = {
            "gx": gx,
            "gy": gy,
            "gdir": self.direction,
            "px": px,
            "py": py,
            "pdir": -1,
            "tabu_g": list(self.tabu_list),
            "tabu_p": [],
        }

        for current_depth in range(1, self.depth_base_solo + 1):
            if self._timeout_reached(t0, self.time_budget_ms_solo):
                timeout_hit = True
                break
            best_val_global = alpha_beta_rec(root_state, current_depth, -float("inf"), float("inf"), True)

        self.last_decision_ms = (time.perf_counter() - t0) * 1000.0

        if best_dir_global is None:
            self.interseccion_random()
            self._debug_print_ai_metrics("alpha_beta_solo_fallback", root_mc=(gx, gy), selected_dir=self.direction, depth_used=0, timeout_hit=timeout_hit, note="fallback_random")
            return

        self._update_tabu(self.tabu_list, (gx, gy))
        self._move_pixel_step(best_dir_global)
        
        branches = len(self.generar_hijos({
            "x": gx,
            "y": gy,
            "prev_dir": self.direction,
            "tabu": self.tabu_list
        }, False))
        self._debug_print_ai_metrics("alpha_beta_solo", root_mc=(gx, gy), selected_dir=best_dir_global, depth_used=self.depth_base_solo, timeout_hit=timeout_hit, branch_factor=branches, best_score=best_val_global)

    def eval_heuristic_pinky(self, estado_simulado_fantasma, estado_simulado_pacman):
        """
        Función de evaluación para Pinky (Solitario).
        Debe contener componentes como la distancia y restricciones de túneles.
        """
        gx, gy = estado_simulado_fantasma
        px, py = estado_simulado_pacman

        # Heuristica 1: perseguir minimizando distancia Manhattan
        manhattan = abs(gx - px) + abs(gy - py)
        score_dist = -float(manhattan)

        # Heuristica 2: acorralar a Pacman en zonas con menos salidas
        exits_p = self._count_exits(px, py)
        score_mob = 10.0 / float(exits_p)

        # Bonus por captura simulada
        capture_bonus = 1000.0 if (gx, gy) == (px, py) else 0.0

        score = (0.7 * score_dist) + (0.3 * score_mob) + capture_bonus
        return score

    def alpha_beta_manada(self, pacmanXY, partner):
        """
        Logica de Poda Alfa-Beta para Inky/Clyde (Manada).
        El Factor de Ramificación (b) se altera, ya que un nodo debe contemplar las opciones
        combinadas delFantasma A y del Fantasma B simultaneamente (cross-product de movimientos).
        """
        if partner is None:
            self.interseccion_random()
            return

        g1x, g1y = self._safe_mc_from_pixel(self.position[0], self.position[2])
        g2x, g2y = self._safe_mc_from_pixel(partner.position[0], partner.position[2])
        px, py = self._safe_mc_from_pixel(pacmanXY[0], pacmanXY[2])
        if (not self._is_valid_mc(g1x, g1y) or not self._is_valid_mc(g2x, g2y)
                or not self._is_valid_mc(px, py)):
            self.interseccion_random()
            return

        self._trim_transposition()
        self.nodes_expanded = 0
        self.cache_hits = 0

        t0 = time.perf_counter()
        best_pair_global = None
        timeout_hit = False

        """
        Función recursiva para la búsqueda Alfa-Beta en modo manada.
        En este caso de caza en manada, para el nodo maximizador, se generan las combinaciones de movimientos posibles para ambos 
        fantasmas y se evalúan conjuntamente, mientras que para el nodo minimizador se generan los movimientos de Pacman como 
        respuesta a la configuración combinada de ambos fantasmas.
        La función de evaluación heurística para la manada debe considerar la posición conjunta de ambos fantasmas respecto a 
        Pacman, buscando estrategias de acorralamiento y aprovechando la capacidad de cubrir múltiples rutas de escape 
        simultáneamente.
        """
        
        def alpha_beta_rec(state, depth, alpha, beta, is_max):
            nonlocal best_pair_global, timeout_hit
            if self._timeout_reached(t0, self.time_budget_ms_manada):
                timeout_hit = True
                return self.eval_heuristic_manada(
                    (state["g1x"], state["g1y"]),
                    (state["g2x"], state["g2y"]),
                    (state["px"], state["py"])
                )

            if depth == 0 or (state["g1x"], state["g1y"]) == (state["px"], state["py"]) or (state["g2x"], state["g2y"]) == (state["px"], state["py"]):
                return self.eval_heuristic_manada(
                    (state["g1x"], state["g1y"]),
                    (state["g2x"], state["g2y"]),
                    (state["px"], state["py"])
                )

            key = (
                state["g1x"], state["g1y"], state["g1dir"],
                state["g2x"], state["g2y"], state["g2dir"],
                state["px"], state["py"], state["pdir"],
                depth, is_max
            )
            if key in self.transposition_table:
                self.cache_hits += 1
                return self.transposition_table[key]

            self.nodes_expanded += 1
            if is_max:
                best_val = -float("inf")
                pairs = self.generar_hijos({
                    "g1": {
                        "x": state["g1x"], "y": state["g1y"], "prev_dir": state["g1dir"], "tabu": state["tabu1"]
                    },
                    "g2": {
                        "x": state["g2x"], "y": state["g2y"], "prev_dir": state["g2dir"], "tabu": state["tabu2"]
                    }
                }, es_manada=True)
                if not pairs:
                    return self.eval_heuristic_manada(
                        (state["g1x"], state["g1y"]),
                        (state["g2x"], state["g2y"]),
                        (state["px"], state["py"])
                    )

                for pair in pairs:
                    tabu1 = list(state["tabu1"])
                    tabu2 = list(state["tabu2"])
                    self._update_tabu(tabu1, (pair["g1"]["x"], pair["g1"]["y"]))
                    self._update_tabu(tabu2, (pair["g2"]["x"], pair["g2"]["y"]))
                    next_state = {
                        "g1x": pair["g1"]["x"], "g1y": pair["g1"]["y"], "g1dir": pair["g1"]["dir"],
                        "g2x": pair["g2"]["x"], "g2y": pair["g2"]["y"], "g2dir": pair["g2"]["dir"],
                        "px": state["px"], "py": state["py"], "pdir": state["pdir"],
                        "tabu1": tabu1, "tabu2": tabu2, "tabu_p": list(state["tabu_p"])
                    }
                    value = alpha_beta_rec(next_state, depth - 1, alpha, beta, False)
                    if value > best_val:
                        best_val = value
                        if depth == current_depth:
                            best_pair_global = pair
                    alpha = max(alpha, best_val)
                    if beta <= alpha + self.epsilon:
                        break
            else:
                best_val = float("inf")
                children = self.generar_hijos({
                    "x": state["px"],
                    "y": state["py"],
                    "prev_dir": state["pdir"],
                    "tabu": state["tabu_p"],
                })
                if not children:
                    return self.eval_heuristic_manada(
                        (state["g1x"], state["g1y"]),
                        (state["g2x"], state["g2y"]),
                        (state["px"], state["py"])
                    )

                for child in children:
                    tabu_p = list(state["tabu_p"])
                    self._update_tabu(tabu_p, (child["x"], child["y"]))
                    next_state = {
                        "g1x": state["g1x"], "g1y": state["g1y"], "g1dir": state["g1dir"],
                        "g2x": state["g2x"], "g2y": state["g2y"], "g2dir": state["g2dir"],
                        "px": child["x"], "py": child["y"], "pdir": child["dir"],
                        "tabu1": list(state["tabu1"]), "tabu2": list(state["tabu2"]), "tabu_p": tabu_p
                    }
                    value = alpha_beta_rec(next_state, depth - 1, alpha, beta, True)
                    best_val = min(best_val, value)
                    beta = min(beta, best_val)
                    if beta <= alpha + self.epsilon:
                        break

            self.transposition_table[key] = best_val
            return best_val

        root_state = {
            "g1x": g1x, "g1y": g1y, "g1dir": self.direction,
            "g2x": g2x, "g2y": g2y, "g2dir": partner.direction,
            "px": px, "py": py, "pdir": -1,
            "tabu1": list(self.tabu_list), "tabu2": list(partner.tabu_list), "tabu_p": []
        }

        for current_depth in range(1, self.depth_base_manada + 1):
            if self._timeout_reached(t0, self.time_budget_ms_manada):
                timeout_hit = True
                break
            best_val_global = alpha_beta_rec(root_state, current_depth, -float("inf"), float("inf"), True)

        self.last_decision_ms = (time.perf_counter() - t0) * 1000.0

        if best_pair_global is None:
            self.interseccion_random()
            self._debug_print_ai_metrics("alpha_beta_manada_fallback", root_mc=(g1x, g1y), selected_dir=self.direction, depth_used=0, timeout_hit=timeout_hit, note="fallback_random")
            return

        self._update_tabu(self.tabu_list, (g1x, g1y))
        self._move_pixel_step(best_pair_global["g1"]["dir"])
        
        branches = len(self.generar_hijos({
            "g1": {"x": g1x, "y": g1y, "prev_dir": self.direction, "tabu": self.tabu_list},
            "g2": {"x": g2x, "y": g2y, "prev_dir": partner.direction if partner else self.direction, "tabu": partner.tabu_list if partner else []}
        }, True))
        self._debug_print_ai_metrics("alpha_beta_manada", root_mc=(g1x, g1y), selected_dir=best_pair_global["g1"]["dir"], depth_used=self.depth_base_manada, timeout_hit=timeout_hit, note=f"partner_dir={best_pair_global['g2']['dir']}", branch_factor=branches, best_score=best_val_global)

    def eval_heuristic_manada(self, estado_fantasma_1, estado_fantasma_2, estado_pacman):
        """
        Función de evaluación para Inky/Clyde.
        Se pondera qué tan bien están cooperando en base a las posiciones de ambos en el mismo turno.
        """
        g1x, g1y = estado_fantasma_1
        g2x, g2y = estado_fantasma_2
        px, py = estado_pacman

        # Heuristica 1: Pacman cerca del centro de masa
        cmx = 0.5 * (g1x + g2x)
        cmy = 0.5 * (g1y + g2y)
        score_cm = -(abs(cmx - px) + abs(cmy - py))

        # Heuristica 2: separacion moderada para formar pinza
        sep = abs(g1x - g2x) + abs(g1y - g2y)
        score_sep = min(8.0, float(sep))

        # Bonus de cierre: menos salidas en posicion de Pacman
        exits_p = self._count_exits(px, py)
        score_close = 8.0 / float(exits_p)

        capture_bonus = 1000.0 if ((g1x, g1y) == (px, py) or (g2x, g2y) == (px, py)) else 0.0
        score = (0.6 * score_cm) + (0.3 * score_sep) + (0.1 * score_close) + capture_bonus
        return score

    def generar_hijos(self, estado, es_manada=False):
        """
        Base para generar ramas del arbol (movimientos posibles). 
        Se debe omitir self.dir_inv tal como se hace en la busqueda random.
        """
        if not es_manada:
            x = estado["x"]
            y = estado["y"]
            prev_dir = estado["prev_dir"]
            tabu = estado.get("tabu", [])

            cell_id = self._cell_id(x, y)
            
            # En pasillos (0), la única opción es continuar en la misma dirección
            if cell_id == 0:
                dirs = [prev_dir]
            else:
                dirs = self._allowed_dirs(cell_id)
                
            inv = self._opposite_dir(prev_dir)

            # Regla de no retorno: omitir direccion inversa cuando aplica
            if inv in dirs and cell_id not in [0, 26, 27]:
                dirs.remove(inv)

            hijos = []
            for d in dirs:
                nx, ny = self._next_mc(x, y, d)
                if not self._is_valid_mc(nx, ny):
                    continue

                # Penalizacion tabú suave: se permite como ultima opcion si no hay mas
                tabu_penalty = 1 if (nx, ny) in tabu else 0
                hijos.append({"x": nx, "y": ny, "dir": d, "tabu_penalty": tabu_penalty})

            if not hijos:
                return []

            # Priorizar no-tabú para reducir ciclos
            hijos.sort(key=lambda h: h["tabu_penalty"])
            return hijos

        g1 = estado["g1"]
        g2 = estado["g2"]

        h1 = self.generar_hijos(g1, es_manada=False)
        h2 = self.generar_hijos(g2, es_manada=False)
        if not h1 or not h2:
            return []

        pares = []
        for a in h1:
            for b in h2:
                pares.append({"g1": a, "g2": b, "tabu_penalty": a["tabu_penalty"] + b["tabu_penalty"]})

        pares.sort(key=lambda p: p["tabu_penalty"])
        return pares
        
    def interseccion_random(self):
        #se determina en que tipo de celda esta el fantasma
        self.positionMC[0] = self.XPxToMC[self.position[0] - 20]
        self.positionMC[1] = self.YPxToMC[self.position[2] - 20]
        celId = self.MC[self.positionMC[1]][self.positionMC[0]]
        #a partir de la celda actual se generan sus opciones posibles
        if celId == 0:
            self.option = [self.direction]
        elif celId == 10: #options = [1, 2]
            self.option = self.options[0]
        elif celId == 11: #options = [2, 3]
            self.option = self.options[1]
        elif celId == 12: #options = [0, 1]
            self.option = self.options[2]
        elif celId == 13: #options = [0, 3]
            self.option = self.options[3]
        elif celId == 21: #options = [1, 2, 3]
            self.option = self.options[4]
        elif celId == 22: #options = [0, 2, 3]
            self.option = self.options[5]
        elif celId == 23: #options = [0, 1, 3]
            self.option = self.options[6]
        elif celId == 24: #options = [0, 1, 2]
            self.option = self.options[7]
        elif celId == 25: #options = [0, 1, 2, 3]
            self.option = self.options[8]
        elif celId == 26: #options = [1]
            self.option = self.options[9]
        elif celId == 27: #options = [3]
            self.option = self.options[10]
        else:
            self.option = [self.direction]
        
        #se calcula la direccion inversa a la actual
        if self.direction == 0:
            self.dir_inv = 2
        elif self.direction == 1:
            self.dir_inv = 3
        elif self.direction == 2:
            self.dir_inv = 0
        else:
            self.dir_inv = 1

        #se elimina la direccion invertida a la actual, evitando que el
        #fantasma regrese por el camion por donde llego (rebote)
        if (celId != 0) and (celId != 26) and (celId != 27) and (self.dir_inv in self.option):
            self.option.remove(self.dir_inv)
        
        #se elige aleatoriamente una opcion entre las disponibles
        size = len(self.option)
        dir_rand = random.randint(0, size - 1)
        
        #se actualiza el vector de direccion y posicion del fantasma
        self.direction = self.option[dir_rand]
        
        if self.direction == 0:
            self.position[2] -= 1
        elif self.direction == 1:
            self.position[0] += 1
        elif self.direction == 2:
            self.position[2] += 1
        elif self.direction == 3:
            self.position[0] -= 1
            
        if (celId != 0) and (celId != 26) and (celId != 27):
            self.option.append(self.dir_inv)    

        self._debug_print_ai_metrics("random", root_mc=(self.positionMC[0], self.positionMC[1]), selected_dir=self.direction, depth_used=0, timeout_hit=False)
    
    def update2(self,pacmanXY, all_ghosts):
        #si el fantasma se encuentra en una interseccion (valida o "falsa interseccion")
        if ((self.YPxToMC[self.position[2] - 20] != -1) and 
            (self.XPxToMC[self.position[0] - 20] != -1)):
            # Aquí todos toman decisión de IA al llegar a intersección
            self.path_ia(pacmanXY, all_ghosts)
        else: #si no se encuentra en una interseccion o es falsa interseccion
            self.sigue_adelante()
            # Mostrar debug de movimientos de fantasmas en tuneles
            # if self.debug_ai:
            #     print(
            #         f"[MOVE][Fantasma {self.tipo}] tunnel direction={self.direction} "
            #         f"px={self.position[0]} pz={self.position[2]}"
            #     )
        
    def draw(self):
        glPushMatrix()
        glColor3f(1.0, 1.0, 1.0)
        glTranslatef(self.position[0], self.position[1], self.position[2])
        glScaled(10,1,10)
        #Activate textures
        glEnable(GL_TEXTURE_2D)
        #front face
        glBindTexture(GL_TEXTURE_2D, self.texturas[self.Id])
        self.drawFace(-1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, -1.0)    
        glDisable(GL_TEXTURE_2D)  
        glPopMatrix()        