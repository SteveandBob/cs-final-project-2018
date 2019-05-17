#!/usr/bin/env/python3
#Imports
import sys
import random
import time
import threading
import array
import math
import pygame
import win32api
import scipy

#Module inits
pygame.init()

#Screen init
pygame.display.set_caption("Zombiez", "pygame")
pygame.key.set_repeat(1, 1)

#Globals
screenWidth = win32api.GetSystemMetrics(0)
screenHeight = win32api.GetSystemMetrics(1)
screenDimensions = [screenWidth, screenHeight]
screen = pygame.display.set_mode([screenWidth, screenHeight], pygame.FULLSCREEN)

#functions
def setFPS(fps):
    return int(1000/fps)

def appendToList(updateList:list, newObj):
    updateList.append(newObj)

def sgn(input):
    if input > 0:
        return 1
    elif input == 0:
        return 0
    else:
        return -1

def rotateAboutPoint(points, anchor, ang):
    return scipy.dot(points-anchor, scipy.array([[scipy.cos(ang), scipy.sin(ang)],[-scipy.sin(ang),scipy.cos(ang)]]))+anchor

#Classes
class map:
    def __init__(self):
        self.grid = []
        for i in range(8):
            self.grid.append( [0, 0, 0, 0, 0, 0, 0, 0] )
        self.cameraGridCenter = [4000, 4000]
        self.cameraBounds = [[self.cameraGridCenter[0]-int(screenWidth/2), self.cameraGridCenter[1]-int(screenHeight/2)],[self.cameraGridCenter[0]+int(screenWidth/2),self.cameraGridCenter[1]+int(screenHeight/2)]]
        self.mapGrid = ((0,0),(8000,8000))
    def updateCamera(self, inputX:int, inputY:int):
        self.cameraGridCenter[0] += inputX
        self.cameraGridCenter[1] += inputY
        self.cameraBounds = [[self.cameraGridCenter[0]-int(screenWidth/2), self.cameraGridCenter[1]-int(screenHeight/2)],[self.cameraGridCenter[0]+int(screenWidth/2),self.cameraGridCenter[1]+int(screenHeight/2)]]

class bullet:
    def __init__(self):
        self.bulletType = "pistol"
        self.speed = 15
        self.centerX = int(screenWidth/2)
        self.centerY = int(screenHeight/2)
        self.length = 10
        self.speed = 25
        self.coordinates = [[self.centerX, self.centerY][self.centerX, self.centerY]]
        self.shot = False
        self.spread = 5*(scipy.pi)/180
        self.trajectory = 0
    def draw(self):
        pygame.draw.line(screen, (255,0,0),self.coordinates[0],self.coordinates[1])
    def update(aimAngle):
        if self.shot == False:
            self.coordinates = [[self.centerX, self.centerY][self.centerX, self.centerY]]
        else:
            self.trajectory = aimAngle += random.randint

class player():
    def __init__(self, screenWidth, screenHeight):
        self.centerX = int(screenWidth/2)
        self.centerY = int(screenHeight/2)
        self.vertices = [[self.centerX-10, self.centerY-10],[self.centerX+10, self.centerY+10]]
        self.gunVertices = [[self.centerX, self.centerY],[self.centerX, self.centerY - 35]]
        self.rect = pygame.Rect(self.vertices[0][0], self.vertices[0][1], 20, 20)
        self.aimAngle = 0
    def draw(self):
        pygame.draw.line(screen, (0,0,0), self.gunVertices[0], self.gunVertices[1], 4)
        pygame.draw.circle(screen, (0,255,0), (self.centerX, self.centerY), 10)
    def aim(self):
        self.mouseX, self.mouseY = win32api.GetCursorPos()
        if self.mouseX-self.centerX == 0:
            if sgn(self.mouseY) == 1:
                self.aimAngle = scipy.pi/2
            else:
                self.aimAngle = 3*(scipy.pi)/2
        else:
            self.aimAngle = scipy.arctan((self.mouseY-self.centerY)/(self.mouseX-self.centerX))
        if self.mouseX < self.centerX:
            self.gunVertices[1][0] = int(self.centerX - 30*scipy.cos(self.aimAngle))
        else:
            self.gunVertices[1][0] = int(30*scipy.cos(self.aimAngle) + self.centerX)
        if self.mouseY < self.centerY and self.mouseX > self.centerX:
            self.gunVertices[1][1] = int(30*scipy.sin(self.aimAngle) + self.centerY)
        elif self.mouseY < self.centerY and self.mouseX < self.centerX:
            self.gunVertices[1][1] = int(self.centerY - 30*scipy.sin(self.aimAngle))
        elif self.mouseY > self.centerY and self.mouseX > self.centerX:
            self.gunVertices[1][1] = int(30*scipy.sin(self.aimAngle) + self.centerY)
        elif self.mouseY > self.centerY and self.mouseX < self.centerX:
            self.gunVertices[1][1] = int(self.centerY - 30*scipy.sin(self.aimAngle))
    def collided(self, terrainList):
        for i in terrainList:
            if self.rect.colliderect(i.rect):
                return True
        return False
    def collisionCheck(self, terrainList, cameraCenter, screenDimensions, inputXY):
        entrance = None
        output = cameraCenter
        for i in terrainList:
            if not i.onscreen:
                continue
            if sgn(inputXY[0]) == 1:
                entrance = "Left"
            elif sgn(inputXY[0]) == -1:
                entrance = "Right"
            elif sgn(inputXY[1]) == -1:
                entrance = "Bottom"
            elif sgn(inputXY[1]) == 1:
                entrance = "Top"
            if self.rect.colliderect(i.rect):
                if entrance == "Left":
                    output[0] = i.vertices[0][0]-(10)
                elif entrance == "Right":
                    output[0] = i.vertices[1][0]+(10)
                if entrance == "Bottom":
                    output[1] = i.vertices[1][1]+(10)
                elif entrance == "Top":
                    output[1] = i.vertices[0][1]-(10)
        return output
    def shoot(self):
        x=2

class zombie():
    def __init__(self):
        do_stuff = False

class wall:
    def __init__(self, centerX, centerY, width, height):
        self.centerX = centerX
        self.centerY = centerY
        self.width = width
        self.height = height
        self.center = (self.centerX, self.centerY)
        self.vertices = [ [centerX-(width/2), centerY-(height/2)], [centerX+(width/2), centerY+(height/2)] ]
        self.rect = pygame.Rect(0, 0, width, height)
        self.drawnCoordinates = [[0,0],[0,0]]
        self.onscreen = False
    def draw(self, cameraBounds):
        if self.centerX > cameraBounds[0][0] and self.centerX < cameraBounds[1][0]:
            if self.centerY > cameraBounds[0][1] and self.centerY < cameraBounds[1][1]:
                self.onscreen = True
                pygame.draw.rect(screen, (1,1,1), (self.drawnCoordinates[0][0], self.drawnCoordinates[0][1], self.width, self.height))
        else:
            self.onscreen = False
    def update(self, cameraBounds):
        self.drawnCoordinates[0][0] = int(self.vertices[0][0]-cameraBounds[0][0])
        self.drawnCoordinates[0][1] = int(self.vertices[0][1]-cameraBounds[0][1])
        self.drawnCoordinates[1][0] = int(self.vertices[1][0]-cameraBounds[0][0])
        self.drawnCoordinates[1][1] = int(self.vertices[1][1]-cameraBounds[0][1])
        self.rect = pygame.Rect(self.drawnCoordinates[0][0], self.drawnCoordinates[0][1], self.width, self.height)

#Class Declarations
wall1 = wall(4000, 3800, 100, 10)
wall2 = wall(4200, 3800, 10, 100)
mainPlayer = player(screenWidth, screenHeight)
mainMap = map()

#Miscellaneous
terrainList = [wall1]

appendToList(terrainList, wall2)

#main procedure
def main():
    inputX = 0
    inputY = 0
    fpsDelay = setFPS(60)
    gameState = True
    while gameState:
        inputX = 0
        inputY = 0
        #Check User Input
        modifiers = pygame.key.get_mods()
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:gameState = False
                if modifiers & pygame.KMOD_SHIFT:
                    if event.key == pygame.K_w:inputY = -7
                    if event.key == pygame.K_a:inputX = -7
                    if event.key == pygame.K_s:inputY = 7
                    if event.key == pygame.K_d:inputX = 7
                elif modifiers & pygame.KMOD_CTRL:
                    if event.key == pygame.K_w:inputY = -1
                    if event.key == pygame.K_a:inputX = -1
                    if event.key == pygame.K_s:inputY = 1
                    if event.key == pygame.K_d:inputX = 1
                else:
                    if event.key == pygame.K_w:inputY = -3
                    if event.key == pygame.K_a:inputX = -3
                    if event.key == pygame.K_s:inputY = 3
                    if event.key == pygame.K_d:inputX = 3
        if win32api.GetKeyState(0x01) == -127 or win32api.GetKeyState(0x01) == -128:
            mainPlayer.shoot()
        
        #Updating Sprites and Checking Conditions
        if mainPlayer.collided(terrainList):
            mainMap.cameraGridCenter = mainPlayer.collisionCheck(terrainList, mainMap.cameraGridCenter, screenDimensions, (inputX, inputY))
            mainMap.updateCamera(0, 0)
        else:
            mainMap.updateCamera(inputX, inputY)
        for i in terrainList:
            i.update(mainMap.cameraBounds)
        mainPlayer.aim()

        #Clear Screen
        screen.fill((255, 255, 255))
        print(win32api.GetKeyState(0x01))
        #Draw to Screen
        for i in terrainList:
            i.draw(mainMap.cameraBounds)
        mainPlayer.draw()
        pygame.display.flip()
        pygame.time.wait(fpsDelay)

if __name__ == "__main__":
    main()
    pygame.display.quit()
    sys.exit()
