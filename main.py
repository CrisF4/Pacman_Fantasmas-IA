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

# Se carga el archivo de la clase Cubo
import sys
sys.path.append('..')
from Pacman import Pacman
from Ghost import Ghost


screen_width = 900
screen_height = 800
#vc para el obser.
FOVY=60.0
# Si este valor es muy pequeño, se recortaran los objetos cercanos al observador
ZNEAR=1.0
ZFAR=900.0
#Variables para definir la posicion del observador
#gluLookAt(EYE_X,EYE_Y,EYE_Z,CENTER_X,CENTER_Y,CENTER_Z,UP_X,UP_Y,UP_Z)
EYE_X = 300.0 + 200.0
EYE_Y = 200.0
EYE_Z = 300.0 + 200.0
CENTER_X = 0 + 200
CENTER_Y = 0
CENTER_Z = 0 + 200
UP_X=0
UP_Y=1
UP_Z=0
#Variables para dibujar los ejes del sistema
X_MIN=-500
X_MAX=500
Y_MIN=-500
Y_MAX=500
Z_MIN=-500
Z_MAX=500
#Dimension del plano
DimBoard = 400
#Variables para el control del observador
theta = 0.0
radius = 300


#Arreglo para el manejo de texturas
textures = []
#Nombre de los archivos a usar
BASE_PATH = os.path.abspath(os.path.dirname(__file__))
file_1 = os.path.join(BASE_PATH, 'mapa.bmp')
img_pacman = os.path.join(BASE_PATH, 'pacman.bmp')
img_ghost1 = os.path.join(BASE_PATH, 'fantasma1.bmp')
img_ghost2 = os.path.join(BASE_PATH, 'fantasma2.bmp')
img_ghost3 = os.path.join(BASE_PATH, 'fantasma3.bmp')
img_ghost4 = os.path.join(BASE_PATH, 'fantasma4.bmp')


file_csv = os.path.join(BASE_PATH, 'mapa.csv')
matrix = np.array(pd.io.parsers.read_csv(file_csv, header=None)).astype("int")
zmatrix = len(matrix)
xmatrix = len(matrix[0])


#Arreglos para imprimir intersecciones en el mapa del pacman
zarray = [-180 + 200, -128 + 200, -90 + 200, -50 + 200, -12 + 200, 28 + 200, 64 + 200, 102 + 200, 140 + 200, 180 + 200]
xarray = [-180 + 200, -150 + 200, -108 + 200, -65 + 200, -22 + 200, 21 + 200, 64 + 200, 107 + 200, 149 + 200, 178 + 200]

#Matriz de Control para mapeo entre pixeles <-> coord donde se localizan esquinas
MC = [
    [10,0,21,0,11,10,0,21,0,11],
    [24,0,25,21,23,23,21,25,0,22],
    [12,0,22,12,11,10,13,24,0,13],
    [0,0,0,10,23,23,11,0,0,0],
    [26,0,25,22,0,0,24,25,0,27],
    [0,0,0,24,0,0,22,0,0,0],
    [10,0,25,23,11,10,23,25,0,11],
    [12,11,24,21,23,23,21,22,10,13],
    [10,23,13,12,11,10,13,12,23,11],
    [12,0,0,0,23,23,0,0,0,13]
]

xMC = [0,30,71,114,156,199,242,286,328,358]
#XPxToMC = np.zeros((359,), dtype=int)
XPxToMC = np.full(359, -1, dtype=int)
XPxToMC[0] = 0
XPxToMC[30] = 1
XPxToMC[71] = 2
XPxToMC[114] = 3
XPxToMC[156] = 4
XPxToMC[199] = 5
XPxToMC[242] = 6
XPxToMC[286] = 7
XPxToMC[328] = 8
XPxToMC[358] = 9
 
yMC = [0,51,90,130,168,208,244,282,320,360]
#YPxToMC = np.zeros((361,), dtype=int)
YPxToMC = np.full(361, -1, dtype=int)
YPxToMC[0] = 0
YPxToMC[51] = 1
YPxToMC[90] = 2
YPxToMC[130] = 3
YPxToMC[168] = 4
YPxToMC[208] = 5
YPxToMC[244] = 6
YPxToMC[282] = 7
YPxToMC[320] = 8
YPxToMC[360] = 9

#pathfinding variables
path = []
grid = []

#pacman object
pc = Pacman(matrix, MC, XPxToMC, YPxToMC)
#fantasmas
ghosts = []
ghosts.append(Ghost(matrix, MC, XPxToMC, YPxToMC, 378, 380, 2, 0)) # Blinky (0)
ghosts.append(Ghost(matrix, MC, XPxToMC, YPxToMC, 378, 20, 0, 1)) # Pinky (1)
ghosts.append(Ghost(matrix, MC, XPxToMC, YPxToMC, 20, 380, 3, 2)) # Inky (2)
ghosts.append(Ghost(matrix, MC, XPxToMC, YPxToMC, 20, 20, 3, 3)) # Clyde (3)

pygame.init()

def Axis():
    glShadeModel(GL_FLAT)
    glLineWidth(3.0)
    #X axis in red
    glColor3f(1.0,0.0,0.0)
    glBegin(GL_LINES)
    glVertex3f(X_MIN,0.0,0.0)
    glVertex3f(X_MAX,0.0,0.0)
    glEnd()
    #Y axis in green
    glColor3f(0.0,1.0,0.0)
    glBegin(GL_LINES)
    glVertex3f(0.0,Y_MIN,0.0)
    glVertex3f(0.0,Y_MAX,0.0)
    glEnd()
    #Z axis in blue
    glColor3f(0.0,0.0,1.0)
    glBegin(GL_LINES)
    glVertex3f(0.0,0.0,Z_MIN)
    glVertex3f(0.0,0.0,Z_MAX)
    glEnd()
    glLineWidth(1.0)

def Texturas(filepath):
    textures.append(glGenTextures(1))
    id = len(textures) - 1
    glBindTexture(GL_TEXTURE_2D, textures[id])
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S, GL_CLAMP)
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T, GL_CLAMP)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    image = pygame.image.load(filepath).convert()
    w, h = image.get_rect().size
    image_data = pygame.image.tostring(image,"RGBA")
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, image_data)
    glGenerateMipmap(GL_TEXTURE_2D) 
    
def Init():
    screen = pygame.display.set_mode(
        (screen_width, screen_height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("OpenGL: cubos")

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOVY, screen_width/screen_height, ZNEAR, ZFAR)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(EYE_X,EYE_Y,EYE_Z,CENTER_X,CENTER_Y,CENTER_Z,UP_X,UP_Y,UP_Z)
    glClearColor(0,0,0,0)
    glEnable(GL_DEPTH_TEST)
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    #textures[0]: plano
    Texturas(file_1)
    #textures[1]: pacman
    Texturas(img_pacman)
    #textures[2]: fantasma1
    Texturas(img_ghost1)
    #textures[3]: fantasma2
    Texturas(img_ghost2)
    #textures[4]: fantasma3
    Texturas(img_ghost3)
    #textures[5]: fantasma4
    Texturas(img_ghost4)

    #se pasan las texturas a los objetos
    pc.loadTextures(textures,1)
    ghosts[0].loadTextures(textures,2)
    ghosts[1].loadTextures(textures,3)
    ghosts[2].loadTextures(textures,4)
    ghosts[3].loadTextures(textures,5)
    
def PlanoTexturizado():
    #Activate textures
    glColor3f(1.0,1.0,1.0)
    glEnable(GL_TEXTURE_2D)
    #front face
    glBindTexture(GL_TEXTURE_2D, textures[0])    
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0)
    glVertex3d(0, 0, 0)
    glTexCoord2f(0.0, 1.0)
    glVertex3d(0, 0, DimBoard)
    glTexCoord2f(1.0, 1.0)
    glVertex3d(DimBoard, 0, DimBoard)
    glTexCoord2f(1.0, 0.0)
    glVertex3d(DimBoard, 0, 0)
    glEnd()              
    glDisable(GL_TEXTURE_2D)

#Se mueve al observador circularmente al rededor del plano XZ a una altura fija (EYE_Y)
def lookat():
    global EYE_X
    global EYE_Z
    global radius
    center = DimBoard / 2
    EYE_X = radius * (math.cos(math.radians(theta)) + math.sin(math.radians(theta))) + center
    EYE_Z = radius * (-math.sin(math.radians(theta)) + math.cos(math.radians(theta))) + center
    glLoadIdentity()
    gluLookAt(EYE_X,EYE_Y,EYE_Z,CENTER_X,CENTER_Y,CENTER_Z,UP_X,UP_Y,UP_Z)

def display(update_game=True):
    global done
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    Axis()
    PlanoTexturizado()
    pc.draw()
    for g in ghosts:
        g.draw()
        if update_game:
            g.update2(pc.position, ghosts)
            
            # ---------------------------------------------------------
            # DISTANCIA EUCLIDIANA: Detección de colisiones e intercepción 
            # ---------------------------------------------------------
            # Calculamos la distancia basada en la posición en ambos ejes (X, Z).
            dist = math.sqrt((pc.position[0] - g.position[0])**2 + (pc.position[2] - g.position[2])**2)
            
            # Como los modelos tienen escala (20 de ancho/alto aprox originado por los cubos y movimiento de +-20),
            # un umbral de 20 es un cruce seguro y tangencial de las cajas del pacman / fantasmas.
            if dist < 20.0:  
                print(f"¡Pacman ha sido cazado por un fantasma (Fantasma de Tipo {g.tipo})!")
                # done = True # Terminar la partida en esta iteración
    
done = False
paused = False
slow_motion = False
Init()
#finding(matrix, (xarray[0]-20,zarray[0]-20), (xarray[9]-20,zarray[9]-20))
while not done:
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                done = True
            elif event.key == pygame.K_p:
                paused = not paused
                print(f"[JUEGO] {'Pausado' if paused else 'Reanudado'}")
            elif event.key == pygame.K_c:
                slow_motion = not slow_motion
                print(f"[JUEGO] Camara Lenta {'Activada' if slow_motion else 'Desactivada'}")
    
    if paused:
        pygame.time.wait(10)
        display(update_game=False)
        pygame.display.flip()
        continue

    keys = pygame.key.get_pressed()
    if keys[pygame.K_RIGHT]:
        if theta > 359.0:
            theta = 0
        else:
            theta += 1.0
        lookat()
    if keys[pygame.K_LEFT]:
        if theta < 1.0:
            theta = 360.0
        else:
            theta += -1.0
        lookat()
    #Se verifica la direccion para el pacman    
    if keys[pygame.K_w]:
        #direccion 0
        pc.update(0)
    elif keys[pygame.K_d]:
        #direccion 1
        pc.update(1)
    elif keys[pygame.K_s]:
        #direccion 2
        pc.update(2)
    elif keys[pygame.K_a]:
        #direccion 1
        pc.update(3)
    else:
        pc.update(-1)

    display(update_game=True)
    pygame.display.flip()
    
    if slow_motion:
        pygame.time.wait(80)
    else:
        pygame.time.wait(10)

pygame.quit()
    

