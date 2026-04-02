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
        self.positionMC.append(self.YPxToMC[self.position[2] - 20]) #coord en y
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
            
    # ----------------------------------------------------
    # BASES Y ESQUELETOS (PENDIENTES A IMPLEMENTAR REALMENTE)
    # ----------------------------------------------------
    
    def alpha_beta_solo(self, pacmanXY):
        """
        Logica de Poda Alfa-Beta para Pinky (Solitario).
        Aquí se debe construir el arbol simulando el movimiento de este único fantasma
        y el jugador Pacman.
        """
        # TODO: Implementar árbol Poda Alfa-Beta
        # TODO: Incluir control de Horizonte Limitado, Tabú y Mejoras
        
        # Una vez evaluado, actualizar la direccion: self.direction = mejor_movimiento
        
        # Por ahora para evitar crasheos llama a random:
        self.interseccion_random()

    def eval_heuristic_pinky(self, estado_simulado_fantasma, estado_simulado_pacman):
        """
        Función de evaluación para Pinky (Solitario).
        Debe contener componentes como la distancia y restricciones de túneles.
        """
        score = 0
        # TODO: Implementar heurística 1 (Ej. Distancia Manhattan/Euclidiana)
        # TODO: Implementar heurística 2 (Ej. Grado de movilidad o caminos cerrados)
        return score

    def alpha_beta_manada(self, pacmanXY, partner):
        """
        Logica de Poda Alfa-Beta para Inky/Clyde (Manada).
        El Factor de Ramificación (b) se altera, ya que un nodo debe contemplar las opciones
        combinadas delFantasma A y del Fantasma B simultaneamente (cross-product de movimientos).
        """
        # TODO: Implementar árbol Poda Alfa-Beta con expansión MÚLTIPLE (2 fantasmas al mismo tiempo)
        # TODO: Incluir control de Horizonte Limitado, Tabú y Mejoras (Búsqueda ambiciosa)

        # Una vez evaluado, actualizar la direccion de AMBOS o solo del que llamó: 
        # self.direction = mejor_movimiento_propio
        
        # Por ahora para evitar crasheos llama a random:
        self.interseccion_random()

    def eval_heuristic_manada(self, estado_fantasma_1, estado_fantasma_2, estado_pacman):
        """
        Función de evaluación para Inky/Clyde.
        Se pondera qué tan bien están cooperando en base a las posiciones de ambos en el mismo turno.
        """
        score = 0
        # TODO: Implementar heurística 1 colaborativa (Ej. Distancia promedio de ambos hacia Pacman)
        # TODO: Implementar heurística 2 colaborativa (Ej. Maximizar separación entre los dos cazar en "pinza")
        return score

    def generar_hijos(self, estado, es_manada=False):
        """
        Base para generar ramas del arbol (movimientos posibles). 
        Se debe omitir self.dir_inv tal como se hace en la busqueda random.
        """
        # TODO: Devolver la lista de celdas accesibles adyacentes validas.
        # TODO: Si es_manada es True, devolver combinaciones (pares) de movimientos.
        return []
        
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
        if (celId != 0) and (celId != 26) and (celId != 27):
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
    
    def update2(self,pacmanXY, all_ghosts):
        #si el fantasma se encuentra en una interseccion (valida o "falsa interseccion")
        if ((self.YPxToMC[self.position[2] - 20] != -1) and 
            (self.XPxToMC[self.position[0] - 20] != -1)):
            # Aquí todos toman decisión de IA al llegar a intersección
            self.path_ia(pacmanXY, all_ghosts)
        else: #si no se encuentra en una interseccion o es falsa interseccion
            self.sigue_adelante()
        
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