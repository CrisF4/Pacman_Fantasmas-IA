"""
IDA* hibrido con BFS, Horizonte limitado y Busqueda tabú.
- Lee archivos .txt con el tablero inicial y el tablero meta (cuidar el formato)
- Tabú por iteración: Se limpia completamente cada iteración IDA*, manteniendo memoria constante.
- Profundización dinámica: d_limite crece según necesidad, permitiendo manejar casos difíciles
- Optimizado para casos difíciles (40-80 movimientos), con heurísticas combinadas y cache de estados.
"""
import sys
import math
import time
from collections import deque

# --- CONFIGURACIÓN ---
# RAM asignada: 2GB es compatible con equipos de 8GB RAM
# Para equipos potentes (16GB+), se puede aumentar a 4096 MB
MEM_RAM_MB = 2048
TIMEOUT = 60  # Tiempo límite en segundos (None para sin límite)

# Variables globales que se inicializan al leer el archivo
N_DIMENSION = None
GOAL_STATE = None
GOAL_POSITIONS = {}

class PuzzleNode:
    __slots__ = ['state', 'g', 'f', 'parent', 'action']

    def __init__(self, state, parent=None, action=None, g=0):
        self.state = state
        self.parent = parent
        self.action = action
        self.g = g
        self.f = 0

def print_board(state, title="Tablero"):
    d = int(math.sqrt(len(state)))
    max_digits = len(str(len(state) - 1))
    line = "-" * (d * (max_digits + 3) + 1)
    print(f"\n--- {title} ---")
    print(line)
    for i in range(d):
        row_str = "|"
        for j in range(d):
            val = state[i * d + j]
            display_val = " " * max_digits if val == 0 else str(val).rjust(max_digits)
            row_str += f" {display_val} |"
        print(row_str)
        print(line)
    print()

# HEURÍSTICAS OPTIMIZADAS
HEURISTIC_CACHE = {}

def clear_heuristic_cache():
    """
    Limpiar la caché de heurísticas para liberar memoria entre iteraciones o pruebas.
    Es importante llamar a esta función antes de cada prueba o iteración para evitar que la caché 
    crezca indefinidamente, especialmente en casos difíciles.
    """
    global HEURISTIC_CACHE
    HEURISTIC_CACHE.clear()

def h1_misplaced(state):
    """
    Número de piezas fuera de lugar (sin contar el espacio vacío).
    Rápida pero menos informativa.
    """
    count = 0
    for i in range(len(state)):
        if state[i] != 0 and state[i] != i + 1:
            count += 1
    return count

def h2_manhattan(state):
    """
    Distancia de Manhattan (sin contar el espacio vacío). Más informativa pero más lenta.
    h_2 (n) = ∑ |x_actual - x_meta| + |y_actual - y_meta| para cada pieza. 
    """
    dist = 0
    for i in range(len(state)):
        tile = state[i]
        if tile == 0:
            continue
        target_x, target_y = GOAL_POSITIONS[tile]
        curr_x, curr_y = i % N_DIMENSION, i // N_DIMENSION
        dist += abs(target_x - curr_x) + abs(target_y - curr_y)
    return dist

def h3_linear_conflict(state):
    """
    Contabiliza conflictos lineales: dos piezas en la misma fila o columna que están en su posición 
    objetivo pero bloqueándose mutuamente.
    h_3 (n) = 2k, donde k es el número de conflictos lineales.
    Complementa a distancia Manhattan.
    """
    conflict = 0
    size = N_DIMENSION
    
    # Conflictos en FILAS
    for row in range(size):
        start_idx = row * size
        end_idx = start_idx + size
        tiles_in_row = []
        for i in range(start_idx, end_idx):
            tile = state[i]
            if tile != 0 and (tile - 1) // size == row:
                tiles_in_row.append(tile)
        for i in range(len(tiles_in_row)):
            for j in range(i + 1, len(tiles_in_row)):
                if tiles_in_row[i] > tiles_in_row[j]:
                    conflict += 2
    
    # Conflictos en COLUMNAS
    for col in range(size):
        tiles_in_col = []
        for row in range(size):
            idx = row * size + col
            tile = state[idx]
            if tile != 0 and (tile - 1) % size == col:
                tiles_in_col.append(tile)
        for i in range(len(tiles_in_col)):
            for j in range(i + 1, len(tiles_in_col)):
                if tiles_in_col[i] > tiles_in_col[j]:
                    conflict += 2
    
    return conflict

def h4_corner_conflict(state):
    """
    Contabiliza conflictos de esquina: una pieza esquina esta en su posición objetivo, pero sus vecinas no, siendo bloqueados por dicha pieza esquina.
    h_4 (n) = 2k, donde k es el número de conflictos de esquina.
    Complementa a distancia Manhattan.
    """
    if N_DIMENSION < 2:
        return 0
    conflict = 0
    size = N_DIMENSION
    corners = [
        (0, [1, size]),
        (size - 1, [size - 2, 2 * size - 1]),
        (size * (size - 1), [size * (size - 1) + 1, size * (size - 2)]),
        (size * size - 1, [size * size - 2, size * (size - 1) - 1])
    ]
    for corner_idx, neighbor_indices in corners:
        corner_tile = state[corner_idx]
        if corner_tile != 0 and corner_tile == GOAL_STATE[corner_idx]:
            corner_x, corner_y = corner_idx % size, corner_idx // size
            for n_idx in neighbor_indices:
                if n_idx < 0 or n_idx >= len(state):
                    continue
                neighbor_tile = state[n_idx]
                if neighbor_tile != 0 and neighbor_tile != GOAL_STATE[n_idx]:
                    target_x, target_y = GOAL_POSITIONS[neighbor_tile]
                    if target_x == corner_x or target_y == corner_y:
                        conflict += 2
    return conflict

def h5_inversion_distance(state):
    """
    Distancia de inversiones: mide cuantas piezas aparecen antes que otras con un numero menor o posicion menor al suyo, 
    tanto en filas como columnas. Bastante informativa, pero más costosa de calcular.
    M_v ó M_h = (inv_v // k) + (1 if inv_v % k else 0), donde inv_v es el número de inversiones verticales y k = N_DIMENSION - 1.
    h_5 (n) = M_v + M_h
    """
    size = N_DIMENSION
    if size <= 1:
        return 0
    k = size - 1
    seq_v = [tile for tile in state if tile != 0]
    inv_v = sum(1 for i in range(len(seq_v)) for j in range(i + 1, len(seq_v)) if seq_v[i] > seq_v[j])
    moves_v = inv_v // k + (1 if inv_v % k else 0)
    seq_h = []
    for col in range(size):
        for row in range(size):
            tile = state[row * size + col]
            if tile != 0:
                seq_h.append(tile)
    inv_h = 0
    for i in range(len(seq_h)):
        tile_i = seq_h[i]
        h_idx_i = ((tile_i - 1) % size) * size + ((tile_i - 1) // size)
        for j in range(i + 1, len(seq_h)):
            tile_j = seq_h[j]
            h_idx_j = ((tile_j - 1) % size) * size + ((tile_j - 1) // size)
            if h_idx_i > h_idx_j:
                inv_h += 1
    moves_h = inv_h // k + (1 if inv_h % k else 0)
    return moves_v + moves_h

def calculate_f_with_cache(node, strategy="custom", threshold=float('inf')):
    """
    Calcula el valor f de un nodo utilizando la cache de estados explorados construida en las iteraciones y ahorra tiempo de cálculo.
    Ademas, si el valor f calculado excede el threshold, se guarda en la cache para evitar cálculos futuros de estados similares.
    """
    state = node.state
    if state in HEURISTIC_CACHE:
        h_final = HEURISTIC_CACHE[state]
        return node.g + h_final
    
    # Utilizando maximo absoluto (tiempo de ejecución mas rapida, menos expansiones, pero menos informativa)
    if strategy == "custom":
        h1 = h1_misplaced(state)
        if node.g + h1 > threshold:
            HEURISTIC_CACHE[state] = h1
            return node.g + h1
        h2 = h2_manhattan(state)
        h3 = h3_linear_conflict(state)
        h4 = h4_corner_conflict(state)
        h_manhattan_completa = h2 + h3 + h4
        if node.g + h_manhattan_completa > threshold:
            HEURISTIC_CACHE[state] = h_manhattan_completa
            return node.g + h_manhattan_completa
        h5 = h5_inversion_distance(state)
        h_final = max(h1, h_manhattan_completa, h5)
    else:
        h2 = h2_manhattan(state)
        h_final = h2
    
    HEURISTIC_CACHE[state] = h_final
    return node.g + h_final

    # Utilizando ponderación personalizada (timepo de ejecución mas lenta, menos expansiones, pero mas informativa)
    # if strategy == "custom":
    #     w_g, w_h1, w_h2, w_h3, w_h4, w_h5 = 0.3, 0.05, 0.3, 0.1, 0.1, 0.15 # Pesos de cada componente. Sumados dan 1.0
    #     h1 = -(w_h1*h1_misplaced(state))
    #     if node.g + h1 > threshold:
    #         HEURISTIC_CACHE[state] = h1
    #         return node.g + h1
    #     h2 = w_h2*h2_manhattan(state)
    #     h3 = w_h3*h3_linear_conflict(state)
    #     h4 = w_h4*h4_corner_conflict(state)
    #     h_manhattan_completa = h2 + h3 + h4
    #     if node.g + h_manhattan_completa > threshold:
    #         HEURISTIC_CACHE[state] = h_manhattan_completa
    #         return node.g + h_manhattan_completa
    #     h5 = w_h5*h5_inversion_distance(state)
    #     h_final = max(h1, h_manhattan_completa, h5)
    # else:
    #     h2 = h2_manhattan(state)
    #     h_final = h2
    
    # HEURISTIC_CACHE[state] = h_final
    # return w_g*node.g + h_final

def get_neighbors_optimized(node):
    """
    Genera los nodos vecinos del nodo actual, aplicando movimientos posibles.
    """
    neighbors = []
    state = node.state
    idx = state.index(0)
    size = N_DIMENSION
    x, y = idx % size, idx // size
    
    if y > 0:
        nidx = idx - size
        new_state = list(state)
        new_state[idx], new_state[nidx] = new_state[nidx], new_state[idx]
        neighbors.append(PuzzleNode(tuple(new_state), node, 'U', node.g + 1))
    if y < size - 1:
        nidx = idx + size
        new_state = list(state)
        new_state[idx], new_state[nidx] = new_state[nidx], new_state[idx]
        neighbors.append(PuzzleNode(tuple(new_state), node, 'D', node.g + 1))
    if x > 0:
        nidx = idx - 1
        new_state = list(state)
        new_state[idx], new_state[nidx] = new_state[nidx], new_state[idx]
        neighbors.append(PuzzleNode(tuple(new_state), node, 'L', node.g + 1))
    if x < size - 1:
        nidx = idx + 1
        new_state = list(state)
        new_state[idx], new_state[nidx] = new_state[nidx], new_state[idx]
        neighbors.append(PuzzleNode(tuple(new_state), node, 'R', node.g + 1))
    
    return neighbors

# LECTURA DE ARCHIVOS DE TABLEROS
def read_puzzle_from_file(filepath):
    """
    Lee un archivo de tablero con el formato:
    - Primera línea: dimensión n
    - Siguientes n líneas: tablero inicial (números separados por comas)
    - Siguientes n líneas: tablero meta (números separados por comas)
    
    Retorna: (initial_state, goal_state, n_dimension)
    """
    try:
        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        # Leer dimensión
        n = int(lines[0])
        
        # Leer tablero inicial
        initial_board = []
        for i in range(1, n + 1):
            row = [int(x) for x in lines[i].split(',')]
            initial_board.extend(row)
        
        # Leer tablero meta
        goal_board = []
        for i in range(n + 1, 2 * n + 1):
            row = [int(x) for x in lines[i].split(',')]
            goal_board.extend(row)
        
        return tuple(initial_board), tuple(goal_board), n
    
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{filepath}'")
        return None, None, None
    except (IndexError, ValueError) as e:
        print(f"Error al leer el archivo: {e}")
        print("Formato esperado:")
        print("  Línea 1: dimensión (n)")
        print("  Líneas 2 a n+1: tablero inicial (números separados por comas)")
        print("  Líneas n+2 a 2n+1: tablero meta (números separados por comas)")
        return None, None, None

def initialize_goal_positions(goal_state, n_dimension):
    """
    Inicializa la tabla de lookup de posiciones objetivo.
    """
    global GOAL_POSITIONS
    GOAL_POSITIONS = {}
    for i, tile in enumerate(goal_state):
        if tile != 0:
            GOAL_POSITIONS[tile] = (i % n_dimension, i // n_dimension)

# BFS LIMITADO CON TABÚ POR ITERACIÓN
def bfs_limitado_tabu_iteracion(start_node, goal_state, threshold, d_limite, strategy, 
                                 start_time=None, timeout=None):
    """
    BFS con Tabú que se limpia completamente cada iteración IDA*:
    - Memoria acotada por iteración
    - Permite reexploraciones entre iteraciones (aceptable en IDA*)
    - Verifica timeout si se especifica
    """
    open_queue = deque()
    open_queue.append(start_node)
    
    min_f_exceeded = float('inf')
    expansions = 0
    closed_set = {}  # Tabú LOCAL a esta iteración
    
    while open_queue:
        # Verificar timeout cada cierto número de expansiones
        if timeout and start_time and expansions % 1000 == 0:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                return 'TIMEOUT', min_f_exceeded, expansions
        current = open_queue.popleft()
        
        if current.state == goal_state:
            return current, threshold, expansions
        
        if current.g >= d_limite:
            continue
        
        for neighbor in get_neighbors_optimized(current):
            neighbor.f = calculate_f_with_cache(neighbor, strategy, threshold)
            
            if neighbor.f > threshold:
                min_f_exceeded = min(min_f_exceeded, neighbor.f)
                continue
            
            # Tabú solo dentro de esta iteración
            if neighbor.state in closed_set:
                if closed_set[neighbor.state] <= neighbor.g:
                    continue
            
            closed_set[neighbor.state] = neighbor.g
            expansions += 1
            open_queue.append(neighbor)
    
    return None, min_f_exceeded, expansions

# SOLVER IDA* CON PROFUNDIZACIÓN ADAPTATIVA
def solve_ida_bfs_mem_eficiente(start_state, strategy="custom", mem_ram_mb=512, b=3, 
                                 adaptive_depth=True, verbose=True, timeout=60):
    """
    Solver BFS-IDA* con gestión eficiente de memoria y profundización adaptativa.
    
    - Limpia Tabú cada iteración para máxima eficiencia de memoria
    - adaptive_depth: Si True, incrementa d_limite cuando se agota sin solución
    - timeout: Tiempo máximo en segundos (None para sin límite)
    """
    clear_heuristic_cache()
    start_time = time.time()
    print(f"Memoria RAM asignada: {mem_ram_mb} MB")
    mem_ram_bytes = mem_ram_mb * 1024 * 1024
    dummy_node = PuzzleNode(start_state)
    mem_node = sys.getsizeof(dummy_node) + sys.getsizeof(start_state)
    
    # Calcular d_limite inicial
    ratio_memoria = mem_ram_bytes / mem_node
    try:
        d_limite_inicial = int(math.log(ratio_memoria * (b - 1) + 1, b)) - 1
    except ValueError:
        d_limite_inicial = 20
    
    # Hoorizonte limitado inicial: d_limite inicial
    # 16 es un buen balance: suficiente para casos medios, no excesivo para fáciles
    d_limite = min(d_limite_inicial, 16)
    d_limite_max = 30  # Máximo absoluto
    
    start_node = PuzzleNode(start_state)
    start_node.f = calculate_f_with_cache(start_node, strategy)
    
    threshold = start_node.f
    total_expansions = 0
    iteration = 1
    sin_progreso_count = 0
    last_expansion_count = 0
    
    if verbose:
        print(f"\n{'-'*60}")
        print(f" SOLVER BFS-IDA* HIBRIDO\n")
        print(f"Memoria RAM asignada : {mem_ram_mb} MB")
        print(f"d_limite inicial     : {d_limite} niveles")
        print(f"d_limite máximo      : {d_limite_max} niveles")
        print(f"Profund. adaptativa  : {'SÍ' if adaptive_depth else 'NO'}")
        print(f"Timeout              : {timeout if timeout else 'Sin límite'} segundos")
        print(f"Threshold inicial    : {threshold:.2f}")
        print()
    
    while True:
        # Verificar timeout global
        if timeout:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                if verbose:
                    print(f"\n[!] TIMEOUT: Se alcanzó el límite de {timeout} segundos ({elapsed:.2f}s)")
                return None, total_expansions
        
        # Tabú limpiado cada iteración
        if verbose and (iteration % 10 == 1 or iteration <= 3):
            elapsed = time.time() - start_time if timeout else 0
            print(f"[*] Iter {iteration} | Thresh: {threshold:.4f} | d_lim: {d_limite} | Exp: {total_expansions:,} | Tiempo: {elapsed:.1f}s")
        
        result_node, new_threshold, exp = bfs_limitado_tabu_iteracion(
            start_node, GOAL_STATE, threshold, d_limite, strategy, start_time, timeout
        )
        
        # Verificar si se alcanzó timeout
        if result_node == 'TIMEOUT':
            if verbose:
                print(f"\n[!] TIMEOUT: Se alcanzó el límite de {timeout} segundos")
            return None, total_expansions + exp
        
        total_expansions += exp
        
        # Detectar estancamiento (sin expansiones)
        if exp == last_expansion_count:
            sin_progreso_count += 1
        else:
            sin_progreso_count = 0
        last_expansion_count = exp
        
        # Condición de éxito
        if result_node is not None:
            if verbose:
                print(f"\n[+] ÉXITO: Solución encontrada en iteración {iteration}.")
                print(f"    Profundidad final: {result_node.g}")
            return result_node, total_expansions
        
        # **PROFUNDIZACIÓN ADAPTATIVA**: Si threshold crece pero exp=0, incrementar d_limite
        if new_threshold == float('inf') or (adaptive_depth and sin_progreso_count >= 3):
            if d_limite < d_limite_max:
                d_limite += 2  # Incrementar profundidad permitida
                sin_progreso_count = 0
                if verbose:
                    print(f"\n[!] Incrementando d_limite a {d_limite} (búsqueda más profunda)")
                # Reintentar con la misma threshold pero mayor profundidad
                continue
            else:
                if verbose:
                    print(f"\n[-] FALLO: Alcanzado d_limite máximo ({d_limite_max}).")
                return None, total_expansions
        
        threshold = new_threshold
        iteration += 1
        
        # Límite de seguridad
        if iteration > 150:
            if verbose:
                print("\n[-] FALLO: Excedido límite de iteraciones.")
            return None, total_expansions

# Calculo del horizonte limitado basado en la memoria RAM asignada y el tamaño de los nodos
def calculate_d_limit(mem_ram_bytes, b, sample_state):
    dummy_node = PuzzleNode(sample_state)
    mem_node = sys.getsizeof(dummy_node) + sys.getsizeof(sample_state)
    ratio_memoria = mem_ram_bytes / mem_node
    try:
        d_limite = int(math.log(ratio_memoria * (b - 1) + 1, b)) - 1
    except ValueError:
        d_limite = 20
    return d_limite, mem_node

if __name__ == "__main__":
    # Verificar argumentos de línea de comandos
    if len(sys.argv) < 2:
        print("[-] ERROR: Verificar el formato del archivo de entrada")
        sys.exit(1)
    
    # Leer archivo de tablero
    filepath = sys.argv[1]
    initial_state, goal_state, n_dimension = read_puzzle_from_file(filepath)
    
    if initial_state is None:
        sys.exit(1)
    
    # Inicializar variables globales
    N_DIMENSION = n_dimension
    GOAL_STATE = goal_state
    initialize_goal_positions(goal_state, n_dimension)
    
    # Mostrar tableros
    print_board(initial_state, f"TABLERO INICIAL ({N_DIMENSION}x{N_DIMENSION})")
    print_board(goal_state, f"TABLERO META ({N_DIMENSION}x{N_DIMENSION})")
    
    # Ejecución del solver
    start = time.time()
    resultado, expansiones = solve_ida_bfs_mem_eficiente(
        initial_state, 
        strategy="custom", 
        mem_ram_mb=MEM_RAM_MB,
        adaptive_depth=True,  # Clave para casos difíciles
        verbose=True,
        timeout=TIMEOUT  # Tiempo límite
    )
    tiempo_total = time.time() - start
    
    print("\n" + "-"*70)
    print(" RESULTADOS FINALES\n")
    print(f"Archivo:      {filepath}")
    print(f"Tiempo total: {tiempo_total:.4f} segundos")
    print(f"Expansiones:  {expansiones:,} nodos")
    
    if resultado:
        print(f"[+] Solución encontrada en {resultado.g} movimientos")
        
        # Reconstruir camino
        path = []
        node = resultado
        while node.parent:
            path.append(node.action)
            node = node.parent
        path.reverse()
        print(f"    Camino: {' -> '.join(path)}")
    else:
        print("[-] No se encontró solución dentro de los límites")
    
    print("="*70)
