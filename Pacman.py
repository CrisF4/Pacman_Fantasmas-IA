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

class Pacman:
    def __init__(self,mapa, mc, x_mc, y_mc):
        #Matriz de control que almacena los IDs de las intersecciones
        self.MC = mc
        #Vectores que almacenan las coordenadas 
        self.XPxToMC = x_mc
        self.YPxToMC = y_mc
        #se resplanda el mapa en terminos de pixeles
        self.mapa = mapa
        #se inicializa la posicion del pacman
        self.position = []
        self.position.append(0 + 240) # Originalmente 0+20 para esquina superior izquierda
        self.position.append(1) #YPos
        self.position.append(0 + 228) # Originalmente 0+20 para esquina superior izquierda
        #se define el arreglo para la posicion en la matriz de control
        self.positionMC = []
        self.positionMC.append(self.XPxToMC[self.position[0] - 20]) #coord en x
        self.positionMC.append(self.YPxToMC[self.position[2] - 20]) #coord en y
        #se almacena la direccion inicial del pacman
        self.direction = 1 #asumiendo que inicia en la posicion (0,0)
        #bandera para saber si el pacman se encuentra en estado inicial del juego
        self.start = 1      
        
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
        
    def update(self, dir):
        #si pacman se encuentra en una interseccion (valida o "falsa interseccion")
        if ((self.YPxToMC[self.position[2] - 20] != -1) and 
            (self.XPxToMC[self.position[0] - 20] != -1)):
            #print("esquina")
            self.positionMC[0] = self.XPxToMC[self.position[0] - 20]
            self.positionMC[1] = self.YPxToMC[self.position[2] - 20]
            #si pacman se encuentra en una "falsa interseccion", se debe seguir
            #con su direccion actual
            if self.MC[self.positionMC[1]][self.positionMC[0]] == 0:
                if self.direction == 0:
                    self.position[2] -= 1
                elif self.direction == 1:
                    self.position[0] += 1
                elif self.direction == 2:
                    self.position[2] += 1
                elif self.direction == 3:
                    self.position[0] -= 1
            else:    
                #si pacman se encuentra en una interseccion
                #si no se selecciono una direccion, entonces se evalua con la direccion actual
                if ((dir == -1) and (self.start != 1)):
                    dir = self.direction
                if dir == 0: #up
                    #print("up")
                    if ((self.MC[self.positionMC[1]][self.positionMC[0]] == 12) or 
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 13) or 
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 22) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 23) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 24) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 25)):
                        self.direction = 0
                        self.position[2] -= 1
                        self.start = 0
                if dir == 1: #right
                    #print("right")
                    if ((self.MC[self.positionMC[1]][self.positionMC[0]] == 10) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 12) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 21) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 23) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 24) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 25) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 26)):
                        self.direction = 1
                        self.position[0] += 1
                        self.start = 0
                if dir == 2: #down
                    #print("down")
                    if ((self.MC[self.positionMC[1]][self.positionMC[0]] == 10) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 11) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 21) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 22) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 24) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 25)):
                        self.direction = 2
                        self.position[2] += 1
                        self.start = 0
                if dir == 3: #left
                    #print("left")
                    if ((self.MC[self.positionMC[1]][self.positionMC[0]] == 11) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 13) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 21) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 22) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 23) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 25) or
                        (self.MC[self.positionMC[1]][self.positionMC[0]] == 27)):
                        self.direction = 3
                        self.position[0] -= 1
                        self.start = 0
      
        #si no se encuentra en una interseccion
        else:
            #lleva direccion hacia arriba
            if self.direction == 0:
                #se se aplasta flecha hacia abajo, se puede regresar
                if dir == 2:
                    self.position[2] += 1
                    self.direction = 2
                else:
                    #sigue su camino
                    self.position[2] -= 1    
            else:        
                #lleva direccion hacia la derecha
                if self.direction == 1:
                    #se se aplasta flecha hacia abajo, se puede regresar
                    if dir == 3:
                        self.position[0] -= 1
                        self.direction = 3
                    else:
                        #sigue su camino
                        self.position[0] += 1
                else:
                    #lleva una direccion hacia abajo
                    if self.direction == 2:
                        #si se aplasta flecha hacia arriba, se puede regresar
                        if dir == 0:
                            self.position[2] -= 1
                            self.direction = 0
                        else:
                            self.position[2] += 1
                    else:
                        #se lleva una direccion hacia la izquierda
                        if self.direction == 3:
                            #si se aplasta flecha hacia la derecha, se puede regresar
                            if dir == 1:
                                self.position[0] += 1
                                self.direction = 1
                            else:
                                self.position[0] -= 1
        
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