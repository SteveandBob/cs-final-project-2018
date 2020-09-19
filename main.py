#!/usr/bin/env/python3

"""
Programmers: Shawn Hu, Jeffrey Lu
Program Name: Zombiez
Description: A top-down shooter modelled after Call of Duty: Nazi Zombies
Explanation of the camera and path-finding algorithm can be found in the READ_ME.txt
"""

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
import gui                              #.py file containing the button class necessary for the main menu and other ui stuff
from search_algorithm import next_move  #.py file containing the a-star graph algorithm use to find the path for each zombie
from search_algorithm import Node
from search_algorithm import euclidean

#Module inits
pygame.init()

#Screen init
pygame.display.set_caption("Zombiez", "assets/sprites/icon_logo.png")
pygame.key.set_repeat(10, 10)

#Mixer Channel Inits
bulletSFX1 = pygame.mixer.Channel(0)
bulletSFX2 = pygame.mixer.Channel(1)
bulletSFX3 = pygame.mixer.Channel(2)
bgMusic = pygame.mixer.Channel(3)
perkSFX = pygame.mixer.Channel(4)
mysterySFX = pygame.mixer.Channel(5)
papSFX = pygame.mixer.Channel(6)

#Globals
screenWidth = win32api.GetSystemMetrics(0)
screenHeight = win32api.GetSystemMetrics(1)
screenDimensions = [screenWidth, screenHeight]
screen = pygame.display.set_mode([screenWidth, screenHeight], pygame.FULLSCREEN)
reloadFont = pygame.font.SysFont('Times New Roman', 30)
promptFont = pygame.font.SysFont('Times New Roman', 12)
promptText = promptFont.render('Stuff', False, (0,0,0))
reloadText = reloadFont.render('Reloading...', False, (0, 0, 0))
currentGunText = promptFont.render('Stuff', False, (0, 0, 0))
pygame.mouse.set_cursor((8,8),(4,4),(24,24,24,231,231,24,24,24),(0,0,0,0,0,0,0,0))
cameraCenter = [4000,4000]
mapID = "map1"
channelNum = 1

#Thread locks
cameraCenterLock = threading.BoundedSemaphore(10)

#Functions
#Lambda function to set the fps delay
setFPS  = lambda fps : int(1000/fps)

#Function to determine the sign of an integer or float
def sgn(x):
    if x > 0:
        return 1
    elif x == 0:
        return 0
    else:
        return -1

#Function to determine the radian value of a degree
#Rad --> Deg
def degToRad(x):
    return x*(scipy.pi)/180

#Lambda function to get the number of milliseconds since January 1st, 1970
millis = lambda : int(round(time.time() * 1000))

#Lambda function to clear the screen
cls = lambda : screen.fill((255,255,255))

#Function to generate the 400x400 graph necessary for the a-star algorithm
#returns the generated grid
def createMapGrid(terrainList):
    grid = []
    row = []
    for x in range(400):
        for y in range(400):
            row.append(" ")         #A " " space represents a node on the graph where a zombie can move through
        grid.append(row)
        row=[]
    for x in range(400):
        for y in range(400):
            for i in terrainList:
                if i.rect.colliderect(pygame.Rect(x*20, y*20, 20, 20)) and not i.passable:  #A "%" represents a node on the graph where a zombie cannot move through
                    grid[x][y] = "%"                                                        #These include walls and doors
            for i in interactableList:                                                      #The passable var tells if the the zombie can pass through or not
                if i.rect.colliderect(pygame.Rect(x*20, y*20, 20, 20)) and not i.passable:
                    grid[x][y] = "%"
    return grid

#Takes an input graph and returns a graph with each point converted into a node
def convertMapGrid(inputGrid):      #Takes the created graph and converts every point into a special "Node" class which contains the
    temp = inputGrid                #necessary attributes to operate the a-star algorithm
    for x in range(len(temp)):
        for y in range(len(temp[x])):
            temp[x][y] = Node(temp[x][y], (x,y))
    return temp

#Function to check if a door has been unlocked or not
def checkMapChange(inputGrid, interactableList):
    for i in interactableList:
        if i.interactType == "door":
            if i.interacted:
                inputGrid[i.occupied[0][0]][i.occupied[0][1]].value = " "
                inputGrid[i.occupied[1][0]][i.occupied[1][1]].value = " "

#Function to spawn zombies
#If the spawn is successful, returns True, otherwise returns False
def spawnZombie(zombieList, spawnPoints, closestSpawns, cameraBounds, player, cameraCenter):
    zombieSpawned = False
    for i in zombieList:
        if i.alive == False and zombieSpawned == False:
            choice = random.choice(closestSpawns)
            i.centerX = choice.spawnX
            i.centerY = choice.spawnY
            zombieSpawned = True
            i.healthRemaining = i.health
            i.alive = True
            i.update(cameraBounds, player, cameraCenter)
            return True
        else:
            continue
    return False

#Takes a list of spawn point classes and evaluates the three closest spawns to the player
#Returns all three spawns using slicing
def evaluateClosestSpawns(zombieSpawnList, cameraCenter):
    key = 16000
    output = []
    for i in zombieSpawnList:
        distToPlayer = abs(i.spawnX - cameraCenter[0])+abs(i.spawnY - cameraCenter[1])
        if distToPlayer <= key:
            key = distToPlayer
            output.insert(0, i)
    return output[0:3]

#Small function to regulate bullet sfx
#Each time it is called, it'll switch to a different channel to play the sfx
#Essentially rotates through three different channels
def playBulletSFX(weaponName, weaponList):
    global channelNum
    bulletSound = None
    for i in weaponList:
        if i.weaponName == weaponName:
            bulletSound = i.weaponSFX
    if channelNum == 1:
        bulletSFX1.play(bulletSound)
    elif channelNum == 2:
        bulletSFX2.play(bulletSound)
    elif channelNum == 3:
        bulletSFX3.play(bulletSound)
    channelNum += 1
    if channelNum > 3:
        channelNum = 1

#Classes
class wave:                 #Wave class is used to determine the number of zombies in a round, if a round has progressed/ended
    def __init__(self):     #and to spawn zombies
        self.round = 1
        self.maxCount = 6
        self.hordeSize = 24
        self.multiplier = 0.4
        self.zombieHealth = 150
        self.previousTimeSpawn = 0
        self.spawnRate = 750
        self.spawnedZombies = 0
    def nextRound(self, zombieList):    #Class function to set the number of zombies per round
        if self.round < 5:              #Rounds 1-4 are modified by a multiplier to determine the num of zombies in the round
            self.maxCount = round(self.hordeSize * self.multiplier)
            self.multiplier += 0.2      #Health increases by a flat 100 each round
            self.zombieHealth += 100
        elif 5 <= self.round < 10:      #Round 5-9 have a flat 24 zombies
            self.maxCount = 24
            self.zombieHealth += 100    #Health increases by a flat 100 each round
        else:                           #Rounds 10+ have a special modifier to determine the num of zombies
            self.maxCount = round((self.round*0.15)*self.hordeSize)
            self.zombieHealth = round(self.zombieHealth * 1.1)  #Health increases by 10% from the previous round
        for i in zombieList:            #Sets zombie health
            i.health = self.zombieHealth
        if self.round % 5 == 0:         #Increases the zombie speed every 5 round
            for i in zombieList:
                i.speed += 1
        self.round += 1
        self.spawnedZombies = 0         #Resets the num of zombies that have been spawned as a new round is beginning
    def checkRoundState(self, player, zombieList):  #Class funtion to determine if the round has ended
        if player.killCount >= self.maxCount:       #Compares the player's killcount to the max num of zombies
            player.killCount = 0                    #Resets num of player kills
            self.nextRound(zombieList)              #Begins new round
            return False                            #Returns False if the round has ended
        return True                                 #Returns True if round has not ended
    def spawn(self, zombieList, spawnPoints, player, cameraCenter, cameraBounds):   #Class Function to spawn zombies
        if self.spawnedZombies < self.maxCount:     #Check to see if we have spawned too many zombies
            if (millis() - self.previousTimeSpawn) >= self.spawnRate:   #Internal timer checking if enough time has passed to spawn a new zombie
                if spawnZombie(zombieList, spawnPoints, evaluateClosestSpawns(spawnPoints, cameraCenter), cameraBounds, player, cameraCenter):  #If the spawn was successful then
                    self.previousTimeSpawn = millis()                                                                                           #set previous spawn time to now
                    self.spawnedZombies += 1                                                                                                    #increment the num of spawned zombies
    def update(self, zombieList, spawnPoints, cameraCenter, cameraBounds, player):      #Class Function to check if the round has ended and to spawn zombies
        if self.checkRoundState(player, zombieList):
            self.spawn(zombieList, spawnPoints, player, cameraCenter, cameraBounds)
    def reset(self):                #Class Function to reset the class
        self.round = 1              #Only called when the game has ended
        self.maxCount = 6
        self.hordeSize = 24
        self.multiplier = 0.4
        self.zombieHealth = 150
        self.previousTimeSpawn = 0
        self.spawnRate = 750
        self.spawnedZombies = 0

class mapClass:                     #Map Class to contain the attributes of the camera
    def __init__(self, gridCenterX, gridCenterY):
        self.startX = gridCenterX
        self.startY = gridCenterY
        self.cameraGridCenter = [gridCenterX, gridCenterY]
        self.cameraBounds = [[self.cameraGridCenter[0]-int(screenWidth/2), self.cameraGridCenter[1]-int(screenHeight/2)],[self.cameraGridCenter[0]+int(screenWidth/2),self.cameraGridCenter[1]+int(screenHeight/2)]]
    def updateCamera(self, inputX:int, inputY:int):     #Updates the camera's pos based on movement input from the keys
        global cameraCenter
        self.cameraGridCenter[0] += inputX
        self.cameraGridCenter[1] += inputY
        cameraCenter = self.cameraGridCenter
        self.cameraBounds = [[self.cameraGridCenter[0]-int(screenWidth/2), self.cameraGridCenter[1]-int(screenHeight/2)],[self.cameraGridCenter[0]+int(screenWidth/2),self.cameraGridCenter[1]+int(screenHeight/2)]]
    def reset(self):    #Class function to reset the camera to the initial position
        self.cameraGridCenter = [self.startX, self.startY]

class bullet:           #Bullet class
    def __init__(self):
        self.centerX = int(screenWidth/2)
        self.centerY = int(screenHeight/2)
        self.length = 8
        self.speed = 16
        self.coordinates = [[None,None],[None,None]]
        self.shot = False
        self.trajectory = 0         #Trajectory refers to the angle of the bullet being fired
        self.direction = 0          #Direction is a var that holds which quadrant the bullet is being fired in
                                    #1 is bottom right, 2 is bottom left, 3 is top left, 4 is top right
        self.dx = 0         #Dx and Dy are variables to determine how much should be added or subtracted
        self.dy = 0         #after firing the bullet
    def draw(self):     #Class function to draw the bullet to the screen
        pygame.draw.line(screen, (255,0,0),self.coordinates[0],self.coordinates[1], 1)
    def update(self, player, terrainList, zombieList, interactableList):    #Class function to update the location of the bullet and to detect any collisions
        if self.shot == False:      #Bullet has not been fired yet so store it in the tip of the gun
            self.coordinates = [[player.gunVertices[1][0], player.gunVertices[1][1]], [player.gunVertices[1][0], player.gunVertices[1][1]]]
        else:                       #Bullet has been fired
            if self.coordinates[0] == self.coordinates[1] and self.shot == True: #Bullet has just been fired but has not left the gun
                spread = random.uniform(-player.spread, player.spread)      #Pick a random offset
                self.trajectory = player.aimAngle + spread                  #Set trajectory based on the angle of the player aiming and the spread
                self.dx = scipy.cos(self.trajectory)*self.speed             #Calculate DX
                self.dy = scipy.sin(self.trajectory)*self.speed             #Calculate DY
                if player.mouseX < player.gunVertices[1][0] and player.mouseY < player.gunVertices[1][1]:       #Calculate the first step in its flight and set a direction
                    self.coordinates[0] = [player.gunVertices[1][0]-self.speed*scipy.cos(self.trajectory), player.gunVertices[1][1]-self.speed*scipy.sin(self.trajectory)]
                    self.coordinates[1] = [self.coordinates[0][0]-self.length*scipy.cos(self.trajectory), self.coordinates[0][1]-self.length*scipy.sin(self.trajectory)]
                    self.direction = 3
                elif player.mouseX < player.gunVertices[1][0] and player.mouseY > player.gunVertices[1][1]:
                    self.coordinates[0] = [player.gunVertices[1][0]-self.speed*scipy.cos(self.trajectory), player.gunVertices[1][1]-self.speed*scipy.sin(self.trajectory)]
                    self.coordinates[1] = [self.coordinates[0][0]+self.length*scipy.cos(self.trajectory), self.coordinates[0][1]+self.length*scipy.sin(self.trajectory)]
                    self.direction = 2
                elif player.mouseX > player.gunVertices[1][0] and player.mouseY < player.gunVertices[1][1]:
                    self.coordinates[0] = [player.gunVertices[1][0]+self.speed*scipy.cos(self.trajectory), player.gunVertices[1][1]+self.speed*scipy.sin(self.trajectory)]
                    self.coordinates[1] = [self.coordinates[0][0]+self.length*scipy.cos(self.trajectory), self.coordinates[0][1]+self.length*scipy.sin(self.trajectory)]
                    self.direction = 4
                elif player.mouseX > player.gunVertices[1][0] and player.mouseY > player.gunVertices[1][1]:
                    self.coordinates[0] = [player.gunVertices[1][0]+self.speed*scipy.cos(self.trajectory), player.gunVertices[1][1]+self.speed*scipy.sin(self.trajectory)]
                    self.coordinates[1] = [self.coordinates[0][0]+self.length*scipy.cos(self.trajectory), self.coordinates[0][1]+self.length*scipy.sin(self.trajectory)]
                    self.direction = 1
            else:               #Bullet has been fired already and is travelling
                if self.direction == 1 or self.direction == 4:             
                    self.coordinates[0][0] += self.dx
                    self.coordinates[0][1] += self.dy
                    self.coordinates[1][0] += self.dx
                    self.coordinates[1][1] += self.dy
                elif self.direction == 2 or self.direction == 3:
                    self.coordinates[0][0] -= self.dx
                    self.coordinates[0][1] -= self.dy
                    self.coordinates[1][0] -= self.dx
                    self.coordinates[1][1] -= self.dy
            if self.coordinates[0][0] > screenWidth or self.coordinates[0][0] < 0 or self.coordinates[0][1] > screenHeight or self.coordinates[0][1] < 0: #If the bullet has left the screen, despawn it
                self.shot = False
            for i in terrainList:           #If the bullet collides with a wall
                if i.rect.collidepoint(self.coordinates[1][0], self.coordinates[1][1]) or i.rect.collidepoint(self.coordinates[0][0], self.coordinates[0][1]) or i.rect.collidepoint((self.coordinates[1][0]-self.coordinates[0][0])/2+self.coordinates[0][0],(self.coordinates[1][1]-self.coordinates[0][1])/2+self.coordinates[0][1]):
                    if not i.passable:
                        self.shot = False   #Despawn it
            for i in zombieList:            #If the bullet collides with a zombie
                if not i.alive:             #Check if the zombie is alive
                    continue            #If not alive, skip
                if player.guns[player.currentGun] == "Rail Gun" and i.rect.collidepoint(self.coordinates[1][0], self.coordinates[1][1]) or i.rect.collidepoint(self.coordinates[0][0], self.coordinates[0][1]):         #special case for the rail gun
                    i.healthRemaining -= player.bulletDMG       #Bullet has collided with an alive zombie so subtract the dmg inflicted from the zombie health
                    player.money += 10                          #Add money to the player, bullet is not despawned
                elif i.rect.collidepoint(self.coordinates[1][0], self.coordinates[1][1]) or i.rect.collidepoint(self.coordinates[0][0], self.coordinates[0][1]):            #regular case for all guns
                    self.shot = False                           #Inflict dmg and add money
                    i.healthRemaining -= player.bulletDMG       #Despawn bullet
                    player.money += 10
            for i in interactableList:
                if i.rect.collidepoint(self.coordinates[1][0], self.coordinates[1][1]) or i.rect.collidepoint(self.coordinates[0][0], self.coordinates[0][1]) or i.rect.collidepoint((self.coordinates[1][0]-self.coordinates[0][0])/2+self.coordinates[0][0],(self.coordinates[1][1]-self.coordinates[0][1])/2+self.coordinates[0][1]):
                    if not i.passable:          #If the bullet collides with an object that is not passable
                        self.shot = False       #despawn it

class player():             #Player class
    def __init__(self, screenWidth, screenHeight):
        self.alive = True
        self.health = 100
        self.healthRemaining = self.health
        self.centerX = int(screenWidth/2)
        self.centerY = int(screenHeight/2)
        self.center = [self.centerX, self.centerY]
        self.vertices = [[self.centerX-10, self.centerY-10],[self.centerX+10, self.centerY+10]]
        self.gunVertices = [[self.centerX, self.centerY],[self.centerX, self.centerY - 35]]
        self.rect = pygame.Rect(self.vertices[0][0], self.vertices[0][1], 20, 20)
        self.aimAngle = 0
        self.fireMode = "semiauto"
        self.bulletDMG = 40
        self.numOfBullets = 1
        self.rpm = 250
        self.prevTimeFired = 0
        self.timeFired = 0
        self.spread = degToRad(2)
        self.magSize = 9
        self.ammoCount = [self.magSize+1, 0]
        self.ammoReserves = [self.magSize*4, 0]
        self.reloadTime = 3000
        self.reloading = False
        self.startReloading = False
        self.reloadStart = 0
        self.previousClick = 0
        self.gun1 = "M1911"
        self.gun2 = None
        self.gun3 = None
        self.guns = [self.gun1,self.gun2]
        self.currentGun = 0
        self.perks = []
        self.money = 500
        self.killCount = 0
        self.totalKills = 0
        self.timeAttacked = 0
        self.regenTime = 5000
    def draw(self):     #Class function that draws the player to the screen
        pygame.draw.line(screen, (0,0,0), self.gunVertices[0], self.gunVertices[1], 4)
        pygame.draw.circle(screen, (0,255,0), (self.centerX, self.centerY), 10)
    def aim(self):      #Class function that aims the gun at the cursor
        self.mouseX, self.mouseY = win32api.GetCursorPos()
        if self.mouseX-self.centerX == 0:       #If the cursor has reached exactly the mid point of the screen
            if sgn(self.mouseY) == 1:
                self.aimAngle = scipy.pi/2
            else:
                self.aimAngle = 3*(scipy.pi)/2
        else:
            self.aimAngle = scipy.arctan((self.mouseY-self.centerY)/(self.mouseX-self.centerX)) #Otherwise do a normal calculation
        if self.mouseX < self.centerX:                                                  #Begin performing calculations based on angle
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
    def collided(self, terrainList):            #Class function to check if the player has collided with any wall
        for i in terrainList:
            if self.rect.colliderect(i.rect):
                return True         #If yes, then return True
        return False                #otherise return False
    def collisionCheck(self, terrainList, cameraCenter, screenDimensions, inputXY): #Class function to rectify any collision that occur
        entrance = None
        output = cameraCenter
        if sgn(inputXY[0]) == 1:    #Check which direction that the player is approaching from
            entrance = "Left"
        elif sgn(inputXY[0]) == -1:
            entrance = "Right"
        elif sgn(inputXY[1]) == -1:
            entrance = "Bottom"
        elif sgn(inputXY[1]) == 1:
            entrance = "Top"
        for i in terrainList:
            if not i.onscreen or not i.obstructing: #If wall is not on the screen, skip
                continue
            if self.rect.colliderect(i.rect):   #If it does collide
                if entrance == "Left":          #Rectify based on position
                    output[0] = i.vertices[0][0]-10
                elif entrance == "Right":
                    output[0] = i.vertices[1][0]+10
                if entrance == "Bottom":
                    output[1] = i.vertices[1][1]+10
                elif entrance == "Top":
                    output[1] = i.vertices[0][1]-10
        return output               #Returns the new pos of the camera center after rectifying
    def fire(self, bulletList, weaponList):     #Class function to fire a bullet
        bulletFired = False
        for i in bulletList:
            if i.shot == False and bulletFired == False:
                bulletFired = True
                i.shot = True
                self.prevTimeFired = millis()
                playBulletSFX(self.guns[self.currentGun], weaponList)
                return None
    def shoot(self, bulletList, mouseClick, weaponList):        #Class function that checks if the player has requested the gun to fire
        if not self.reloading and self.ammoCount[self.currentGun] > 0 and self.guns[self.currentGun] != None:   #If the guns is not reloading or the gun has ammo or the gun actuall exists
            if millis()-self.prevTimeFired >= 60000/self.rpm:   #Internal timer to check if enough time has passed to fire a bullet
                if self.fireMode == "semiauto":                 #If the gun is semiautomatic
                    if self.previousClick != mouseClick:        #Fire only if the player has lefted the mouse
                        self.previousClick = mouseClick
                        for i in range(self.numOfBullets):
                            self.fire(bulletList, weaponList)
                        self.ammoCount[self.currentGun] -= 1    #Gun fired succesfully so subtract ammo from the counter
                elif self.fireMode == "fullauto":           #If the gun is fully automatic
                    for i in range(self.numOfBullets):
                        self.fire(bulletList, weaponList)   #Fire the bullet
                    self.ammoCount[self.currentGun] -= 1    #Subtract ammo
    def refillMag(self):    #Class function to refill the magazine
        if sgn(self.ammoReserves[self.currentGun] - (self.magSize-self.ammoCount[self.currentGun])) == -1:  #If not enough ammo is left to refill the entire mag
            self.ammoCount[self.currentGun] += self.ammoReserves[self.currentGun]       #Refill what ammo is left
            self.ammoReserves[self.currentGun] = 0                                      #Then deplete the reserves
        else:                                                                                       #Otherwise perform normal reload
            self.ammoReserves[self.currentGun] -= (self.magSize - self.ammoCount[self.currentGun])  #Subtract the num of missing ammo in the mag from the reserves
            self.ammoCount[self.currentGun] = self.magSize                                          #Set the counter to the magsize as it is full now
        self.reloading = False                                  #Declare the gun is no longer reloading
    def reload(self):       #Class function that checks for reload requests and initiates any reload requests
        if not self.reloading and self.startReloading and self.ammoReserves[self.currentGun] > 0:   #If the player is not already reloading, a request has been put, and the reserve is not depleted
            self.reloading = True               #Player is reloading now
            self.startReloading = False         #Get rid of the request to start reloading
            self.startReload = millis()         #Record the exact time that the reload started
        elif self.reloading:    #If player is reloading
            if (millis()-self.startReload) >= self.reloadTime:  #If enough time has passed to declare that a reload has been finished
                self.refillMag()                                #Call the refill mags function
    def switchWeapon(self, keyboardInput, weaponList):  #Class function enables to switch between weapons they have equipped
        self.currentGun = keyboardInput-1       #Identifies the slot at which the player wants to switch to
        for i in weaponList:                                #Performs the switch
            if i.weaponName == self.guns[self.currentGun]:
                self.bulletDMG = i.bulletDMG                #Sets all necessary params
                self.spread = i.spread
                self.magSize = i.magSize
                self.reloadTime = i.reloadTime
                self.numOfBullets = i.numOfBullets
                self.rpm = i.rpm
                self.fireMode = i.fireMode
    def awardKill(self):        #Class function that awards the player a kill, only called when a zombie has changed from alive to dead
        self.money += 100       #Increases the player's point/money
        self.killCount += 1     #Increases the player' kill count
        self.totalKills += 1    #Increases the total number of kills the player has
    def regenHealth(self):  #Class function that regens health if enough time has passed
        if (millis()-self.timeAttacked) >= self.regenTime:  #Internal timer to check if enough time has passed to start regenerating health
            self.healthRemaining += 10              #Restores health by 10 points each frame
            if self.healthRemaining >= self.health: #Checks for overflow
                self.healthRemaining = self.health  #Gets rid of overflow
    def checkAlive(self):   #Class function that checks if the player has died or not
        if self.healthRemaining <= 0:   #Player has no health left
            self.alive = False  #Player is now dead
            return True #Return True, the player is dead
        return False    #Return False, the player is not dead
    def reset(self):    #Class function to reset the player class to the initial params
        self.alive = True
        self.health = 100
        self.healthRemaining = self.health
        self.aimAngle = 0
        self.fireMode = "semiauto"
        self.bulletDMG = 40
        self.numOfBullets = 1
        self.rpm = 250
        self.prevTimeFired = 0
        self.timeFired = 0
        self.spread = degToRad(2)
        self.magSize = 9
        self.ammoCount = [self.magSize+1, 0]
        self.ammoReserves = [self.magSize*4, 0]
        self.reloadTime = 3000
        self.reloading = False
        self.startReloading = False
        self.reloadStart = 0
        self.previousClick = 0
        self.gun1 = "M1911"
        self.gun2 = None
        self.gun3 = None
        self.guns = [self.gun1,self.gun2]
        self.currentGun = 0
        self.perks = []
        self.money = 500
        self.killCount = 0
        self.totalKills = 0
        self.timeAttacked = 0

class hud:  #Hud Class, records and displays necessary information to the player, "Heads Up Display"
    def __init__(self):
        self.guns = [None, None, None]
        self.ammoFont = pygame.font.SysFont("Times New Roman", 20)
    def update(self, weaponList, player, roundNum): #Class Function that updates the hud
        tempString = str(player.ammoCount[player.currentGun]) + "/" + str(player.ammoReserves[player.currentGun])
        self.ammoText = self.ammoFont.render(tempString, False, (0,0,0))
        self.gunText = self.ammoFont.render(player.guns[player.currentGun], False, (0,0,0))
        self.moneyText = self.ammoFont.render(str(player.money), False, (0,0,0))
        self.roundText = self.ammoFont.render("Round: " + str(roundNum), False, (0,0,0))
        for i in weaponList:
            for j in range(len(self.guns)):
                if i.weaponName in player.guns:
                    self.guns[player.guns.index(i.weaponName)] = i.image2x
    def draw(self, screenDimensions, player):   #Class function that draws the hud with all the information to the screen
        pygame.draw.rect(screen, (0,165,0), pygame.Rect(20, screenDimensions[1]-220, 200, 160))
        if self.guns[0] != None:
            screen.blit(self.guns[0], (30, screenDimensions[1]-210))
        if self.guns[1] != None:
            screen.blit(self.guns[1], (30, screenDimensions[1]-160))
        if self.guns[2] != None:
            screen.blit(self.guns[2], (30, screenDimensions[1]-110))
        pygame.draw.rect(screen, (0,165,0), pygame.Rect(screenDimensions[0]-210, screenDimensions[1]-155, 170, 105))
        pygame.draw.rect(screen, (100, 0, 0), pygame.Rect(screenDimensions[0]-200, screenDimensions[1]-100, 100, 20))
        pygame.draw.rect(screen, (255, 0, 0), pygame.Rect(screenDimensions[0]-200, screenDimensions[1]-100, int((100*player.healthRemaining)/player.health), 20))
        pygame.draw.rect(screen, (0, 165, 0), pygame.Rect(100, 100, 90, 28))
        screen.blit(self.roundText, (110, 103))
        screen.blit(self.ammoText, (screenDimensions[0]-200, screenDimensions[1]-125))
        screen.blit(self.gunText, (screenDimensions[0]-200, screenDimensions[1]-75))
        screen.blit(self.moneyText, (screenDimensions[0]-200, screenDimensions[1]-150))
    def reset(self):    #Resets the hud
        self.guns[1] = None
        self.guns[2] = None

class zombie(): #Zombie class
    def __init__(self, centerX = 10, centerY = 10):
        self.alive = False
        self.x = centerX-10
        self.y = centerY-10
        self.healthRemaining = 100
        self.health = 100
        self.speed = 2
        self.angleToNextPoint = 0
        self.centerX = centerX
        self.centerY = centerY
        self.center = [self.centerX, self.centerY]
        self.coordinates = [[self.x, self.y],[self.x+20, self.y+20]]
        self.drawnCoordinates = [[None, None],[None, None]]
        self.rect = pygame.Rect(self.x, self.y, 20,20)
        self.pathToPlayer = [None]
        self.nextPointToPlayer = None
        self.attackDelay = 1000     #time in between attacks
        self.previousAttack = 0
    def attack(self, cameraCenter, player): #Class function that tells the zombie to attack the player
        if scipy.sqrt(abs(self.centerX-cameraCenter[0])**2+abs(self.centerY-cameraCenter[1])**2) <= 30: #Checks if player is close enough
            if (millis()-self.previousAttack) >= self.attackDelay:  #Internal timer to check if enough time has passed to attack
                player.healthRemaining -= 50        #Subtract a flat 50 hp from player health
                self.previousAttack = millis()      #Set the new time attacked
                player.timeAttacked = millis()      #Set the last time the player was attacked
    def update(self, cameraBounds, player, cameraCenter):   #Class Function to to move the zombie and then update where it is on the screen based on the camera pos
        if self.healthRemaining <= 0 and self.alive != False:   #If the zombie just died
            player.awardKill()  #Give the player a kill
            self.alive = False  #Zombie is now dead
            self.pathToPlayer = []  #Doesn't need a path anymore
        if self.alive:  #If zombie is alive
            self.attack(cameraCenter, player)   #Attack if possible
            if len(self.pathToPlayer) >= 2:     #If there is still a way to the player
                self.nextPointToPlayer = self.pathToPlayer[1]   #Retrieve the next point on the path
                if (self.nextPointToPlayer[0]-self.centerX) == 0:  #Special case if the zombie is directly above or below the next point
                    if self.nextPointToPlayer[1] < self.y:
                        self.angleToNextPoint = 3*(scipy.pi)/2
                    elif self.nextPointToPlayer[1] > self.y:
                        self.angleToNextPoint = scipy.pi/2
                else:
                    self.angleToNextPoint = scipy.arctan((self.nextPointToPlayer[1]-self.centerY)/(self.nextPointToPlayer[0]-self.centerX)) #regular angle calculation
                if self.nextPointToPlayer[0] > self.centerX and self.nextPointToPlayer[1] > self.centerY:   #Move the center of the zombie towards the next point
                    self.centerX += int(self.speed*scipy.cos(self.angleToNextPoint))
                    self.centerY += int(self.speed*scipy.sin(self.angleToNextPoint))
                elif self.nextPointToPlayer[0] < self.centerX and self.nextPointToPlayer[1] < self.centerY:
                    self.centerX -= int(self.speed*scipy.cos(self.angleToNextPoint))
                    self.centerY -= int(self.speed*scipy.sin(self.angleToNextPoint))
                elif self.nextPointToPlayer[0] < self.centerX and self.nextPointToPlayer[1] > self.centerY:
                    self.centerX -= int(self.speed*scipy.cos(self.angleToNextPoint))
                    self.centerY -= int(self.speed*scipy.sin(self.angleToNextPoint))
                elif self.nextPointToPlayer[0] > self.centerX and self.nextPointToPlayer[1] < self.centerY:
                    self.centerX += int(self.speed*scipy.cos(self.angleToNextPoint))
                    self.centerY += int(self.speed*scipy.sin(self.angleToNextPoint))
                elif self.nextPointToPlayer[0] < self.centerX and self.nextPointToPlayer[1] == self.centerY:    #If the zombie is directly to the left, right, top, or bottom of the next point
                    self.centerX -= self.speed
                elif self.nextPointToPlayer[0] > self.centerX and self.nextPointToPlayer[1] == self.centerY:
                    self.centerX += self.speed
                elif self.nextPointToPlayer[1] < self.centerY and self.nextPointToPlayer[0] == self.centerX:
                    self.centerY -= self.speed
                elif self.nextPointToPlayer[1] > self.centerY and self.nextPointToPlayer[0] == self.centerX:
                    self.centerY += self.speed
                if self.centerX >= self.nextPointToPlayer[0]-self.speed and self.centerX <= self.nextPointToPlayer[0]+self.speed and self.centerY >= self.nextPointToPlayer[1]-self.speed and self.centerY <= self.nextPointToPlayer[1]+self.speed:
                    del self.pathToPlayer[1]    #If the zombie is acceptably close to the next point to the player, delete that point
            self.coordinates[0][0] = self.centerX-10    #Update the vertices of the zombie based on the location of the new center of the zombie
            self.coordinates[0][1] = self.centerY-10
            self.coordinates[1][0] = self.centerX+10
            self.coordinates[1][1] = self.centerY+10
            self.drawnCoordinates[0][0] = self.centerX-(10+cameraBounds[0][0]) #Update the zombie pos on the screen based on the center and the camera
            self.drawnCoordinates[0][1] = self.centerY-(10+cameraBounds[0][1])
            self.drawnCoordinates[1][0] = self.drawnCoordinates[0][0]+20
            self.drawnCoordinates[1][1] = self.drawnCoordinates[0][1]+20
            self.rect = pygame.Rect(self.drawnCoordinates[0][0], self.drawnCoordinates[0][1], 20, 20) #Update the rect
    def draw(self, cameraBounds):   #Class function that draws the zombie to the screen
        if self.alive:  #Only draw if it's alive
            if self.coordinates[1][0] > cameraBounds[0][0] and self.coordinates[0][0] < cameraBounds[1][0]:     #Only draw if it's within the boundaries of the screen
                if self.coordinates[1][1] > cameraBounds[0][1] and self.coordinates[0][1] < cameraBounds[1][1]:
                    pygame.draw.rect(screen, (255,0,0), self.rect)
                    pygame.draw.rect(screen,(0,0,0),self.rect,2)

class window:   #Window class, a wall class that bullets and zombies can pass through
    def __init__(self, X, Y, width=20, height=20):
        if width < 20:
            self.width = 20
        else:
            self.width = width
        if height < 20:
            self.height = 20
        else:
            self.height = height
        self.centerX = X-width/2
        self.centerY = Y-height/2
        self.center = (self.centerX, self.centerY)
        self.vertices = [[X, Y], [X+self.width, Y+self.height]]
        self.rect = pygame.Rect(X, Y, width, height)
        self.drawnCoordinates = [[0,0],[0,0]]
        self.onscreen = False
        self.obstructing = True
        self.passable = True
    def draw(self, cameraBounds):   #Class function that draws it to the screen
        if self.vertices[1][0] >= cameraBounds[0][0] and self.vertices[0][0] < cameraBounds[1][0]:
            if self.vertices[1][1] >= cameraBounds[0][1] and self.vertices[0][1] < cameraBounds[1][1]: #Draw if it's within the boundaries of the camera
                self.onscreen = True    #var necessary for collision detection
                pygame.draw.rect(screen, (192,192,192), (self.drawnCoordinates[0][0], self.drawnCoordinates[0][1], self.width, self.height))
        else:
            self.onscreen = False
    def update(self, cameraBounds): #Class function that updates it position on the screen based on the camera
        self.drawnCoordinates[0][0] = int(self.vertices[0][0]-cameraBounds[0][0])
        self.drawnCoordinates[0][1] = int(self.vertices[0][1]-cameraBounds[0][1])
        self.drawnCoordinates[1][0] = int(self.vertices[1][0]-cameraBounds[0][0])
        self.drawnCoordinates[1][1] = int(self.vertices[1][1]-cameraBounds[0][1])
        self.rect = pygame.Rect(self.drawnCoordinates[0][0], self.drawnCoordinates[0][1], self.width, self.height)

class wall:     #Wall class, a class that nothing can pass through
    def __init__(self, X, Y, width=20, height=20):
        if width < 20:
            self.width = 20
        else:
            self.width = width
        if height < 20:
            self.height = 20
        else:
            self.height = height
        self.centerX = X-width/2
        self.centerY = Y-height/2
        self.center = (self.centerX, self.centerY)
        self.vertices = [ [X, Y], [X+self.width, Y+self.height] ]
        self.rect = pygame.Rect(X, Y, width, height)
        self.drawnCoordinates = [[0,0],[0,0]]
        self.onscreen = False
        self.obstructing = True
        self.passable = False
    def draw(self, cameraBounds):   #Class function to draw the wall to the screen
        if self.vertices[1][0] >= cameraBounds[0][0] and self.vertices[0][0] < cameraBounds[1][0]:
            if self.vertices[1][1] >= cameraBounds[0][1] and self.vertices[0][1] < cameraBounds[1][1]:  #Draw if it's within the boundaries of the camera
                self.onscreen = True    #var necessary for collision detection
                pygame.draw.rect(screen, (0,0,0), (self.drawnCoordinates[0][0], self.drawnCoordinates[0][1], self.width, self.height))
        else:
            self.onscreen = False
    def update(self, cameraBounds): #Class function that updates it's position on the screen based on the camera
        self.drawnCoordinates[0][0] = int(self.vertices[0][0]-cameraBounds[0][0])
        self.drawnCoordinates[0][1] = int(self.vertices[0][1]-cameraBounds[0][1])
        self.drawnCoordinates[1][0] = int(self.vertices[1][0]-cameraBounds[0][0])
        self.drawnCoordinates[1][1] = int(self.vertices[1][1]-cameraBounds[0][1])
        self.rect = pygame.Rect(self.drawnCoordinates[0][0], self.drawnCoordinates[0][1], self.width, self.height)

class weapon: #Weapon Class
    def __init__(self, fileName, weaponName, bulletDMG, spread, numOfBullets, rpm, fireMode, reloadTime, magSize, ammoReserves, DMGIncrease, MagIncrease, rpmIncrease, buyCost, weaponSFX = None, weighting = 0):
        self.image = fileName
        self.image2x = pygame.transform.scale2x(pygame.image.load(self.image))
        self.weaponName = weaponName        #All the necessary attributes to characterize the gun
        self.bulletDMG = bulletDMG
        self.spread = spread
        self.numOfBullets = numOfBullets
        self.rpm = rpm
        self.fireMode = fireMode
        self.reloadTime = reloadTime
        self.magSize = magSize
        self.ammoReserves = ammoReserves
        self.DMGIncrease = DMGIncrease
        self.MagIncrease = MagIncrease
        self.rpmIncrease = rpmIncrease
        self.buyCost = buyCost
        self.upgraded = False
        if self.weaponName != "Rail Gun":   #Special modifier that allows the "Rail Gun" to go through all zombies
            self.penetrating = False        #and not despawn on collision with a zombie
        else:
            self.penetrating = True
        self.weight = weighting
        if weaponSFX != None:
            self.weaponSFX = pygame.mixer.Sound(weaponSFX)  #Bullet firing sfx
        self.ammoCost = self.buyCost//2
        self.SFX = pygame.mixer.Sound("assets/sfx/money_interaction.wav") #Purchasing sfx
    def upgrade(self):  #Class function that upgrades the gun when a the gun is pack-a-punched
        self.bulletDMG += self.DMGIncrease
        self.magSize += self.MagIncrease
        self.rpm += self.rpmIncrease
        self.upgraded = True
    def spawn(self, player, weaponList):    #Class function that spawns the gun and switches it
        if not self.weaponName in player.guns:  #If the player doesn't already have the gun
            if player.guns[0] == None:                      #Check if any gun slots are empty
                player.guns[0] = self.weaponName            #If yes, put the new gun in that slot and then switch to that weapon
                player.ammoCount[0] = self.magSize
                player.ammoReserves[0] = self.ammoReserves
                player.switchWeapon(1, weaponList)
                return None
            elif player.guns[1] == None:
                player.guns[1] = self.weaponName
                player.ammoCount[1] = self.magSize
                player.switchWeapon(2, weaponList)
                player.ammoReserves[player.currentGun] = self.ammoReserves
                return None
            if "mule" in player.perks:          #If the player has the mule-kick(let's the player have a third gun
                if player.guns[2] == None:
                    player.guns[2] = self.weaponName
                    player.ammoCount[2] = self.magSize
                    player.switchWeapon(3, weaponList)
                    player.ammoReserves[player.currentGun] = self.ammoReserves
                    return None
            player.guns[player.currentGun] = self.weaponName            #If no slots are empty, puts the gun into the currently equipped slot
            player.ammoCount[player.currentGun] = self.magSize
            player.switchWeapon(player.currentGun+1, weaponList)
            player.ammoReserves[player.currentGun] = self.ammoReserves
        else:           #If the player already has the gun
            if player.guns[player.currentGun] == self.weaponName:               #Refill ammo instead of purchasing a gun
                player.ammoReserves[player.currentGun] = self.ammoReserves
                player.ammoCount[player.currentGun] = player.magSize
            elif self.weaponName in player.guns:
                player.ammoCount[player.guns.index(self.weaponName)] = self.magSize
                player.ammoReserves[player.guns.index(self.weaponName)] = self.ammoReserves
        papSFX.play(self.SFX)   #Play the purchase sfx
    def reset(self):    #Class function that resets the gun to it's original stats
        if self.upgraded:
            self.bulletDMG -= self.DMGIncrease
            self.magSize -= self.MagIncrease
            self.rpm -= self.rpmIncrease
            self.upgraded = False

class perk:     #Perk Class
    def __init__(self, fileName, perkType, perkName, buyCost):
        self.image = fileName
        self.perkType = perkType
        self.perkName = perkName
        self.buyCost = buyCost
        self.SFX = pygame.mixer.Sound("assets/sfx/perkacola.wav")
    def applyPerk(self, player, weaponList):    #Class function that applies a perk to the player based on the declared perkType
        if self.perkType == "juggernog" and not "juggernog" in player.perks:    #Checks the perkType and if the player already has the perk
            player.health = 250                         #applies perk
            player.perks.append("juggernog")            #adds perk to player
        elif self.perkType == "speedcola" and not "speedcola" in player.perks:      #Juggernog: Increases player health to 250
            player.reloadTime = player.reloadTime//2                                #Speedcola: Halves the reload time required
            player.perks.append("speedcola")                                        #Doubletap: Fires twice the numebr of bullets and increaes the rpm
        elif self.perkType == "doubletap" and not "doubletap" in player.perks:      #Mule: Let's the player have a third gun
            player.rpm = int(player.rpm*1.333333)
            player.numOfBullets = player.numOfBullets * 2
            player.perks.append("doubletap")
        elif self.perkType == "mule" and not "mule" in player.perks:
            player.guns.append(player.gun3)
            player.ammoCount.append(0)
            player.ammoReserves.append(0)
            player.perks.append("mule")
        perkSFX.play(self.SFX)  #Play the perk sfx
    def reset(self):        #Placeholder reset function that does nothing, exists so no runtime error pops up on reset
        do_stuff = False

class pack_a_punch:     #Pack-a-punch class
    def __init__(self, fileName):
        self.image = fileName
        self.buyCost = 5000
        self.SFX = pygame.mixer.Sound("assets/sfx/packapunch.wav")
    def upgradeWeapon(self, player, weaponList):    #Class function that upgrades the currently equipped gun
        for i in weaponList:
            if i.weaponName == player.guns[player.currentGun] and not i.upgraded: #Find the gun the player currently has equipped
                i.upgrade()     #Upgrade it
                player.switchWeapon(player.currentGun+1, weaponList)    #Refresh the stats
        papSFX.play(self.SFX)   #Play the sfx
    def reset(self):        #Placeholder reset function that does nothing, exists so no runtime error pops up on reset
        do_stuff = False

class mystery_box: #Mystery Box Class
    def __init__(self, fileName, weaponList):
        self.image = fileName
        self.choices = []
        self.weights = []
        for i in weaponList: #Selects the guns which have no purchase cost
            if i.buyCost == 0:
                self.choices.append(i)
                self.weights.append(i.weight)
        self.buyCost = 950
        self.numOfUses = 0
        self.sfx = pygame.mixer.Sound("assets/sfx/Mystery Box.wav")
    def spawnRandomWep(self, player, weaponList): #Class function that spawns a random weapon
        total = sum(self.weights)               #weighted random generation function
        threshold = random.uniform(0, total)
        for i in range(len(self.weights)):
            total -= self.weights[i]
            if total <= threshold:  #Random weapon has been selected
                self.timer = threading.Timer(7.0, self.choices[i].spawn, [player, weaponList])  #Start a threaded timer to spawn the gun after 7 seconds
                self.timer.start()
                mysterySFX.play(self.sfx)   #play the sfx (lasts 7s)
                self.numOfUses += 1         #increases the number of uses
                return None
    def reset(self):    #Class funciton that resets the number of uses
        self.numOfUses = 0

class door: #Door Class
    def __init__(self, fileName, buyCost):
        self.image = fileName
        self.buyCost = buyCost
        self.unlocked = False
        self.SFX = pygame.mixer.Sound("assets/sfx/money_interaction.wav")
    def unlock(self, player, weaponList): #Class function that despawns the door, allowing the player to pass through
        self.unlocked = True
        papSFX.play(self.SFX)   #plays the purchase sfx
    def reset(self):    #Class function that resets the state of the door
        self.unlocked = False

class power:    #Power Class
    def __init__(self, fileName):
        self.image = fileName
        self.powerON = False
        self.buyCost = 0
        self.SFX = pygame.mixer.Sound("assets/sfx/poweron.wav")
    def turnPowerON(self, player, weaponList): #Class function that turn the power on
        self.powerON = True         #Power is now on
        mysterySFX.play(self.SFX)   #Play the power sfx
    def reset(self):    #Class function that resets the state of the power
        self.powerON = False

class interactable(pygame.sprite.Sprite):   #Interactable Class, subclass of pygame.sprite.Sprite
    def __init__(self, centerX, centerY, interactType, interactObject):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.image.load(interactObject.image)
        self.rect = self.image.get_rect()
        self.rect2 = pygame.Rect(self.rect[0], self.rect[1], self.rect[2],self.rect[3])
        self.rect[0] = centerX-self.rect[2]//2
        self.rect[1] = centerY-self.rect[3]//2
        self.obstructing = False
        self.passable = True
        self.interactType = interactType
        self.interactObject = interactObject #Var that points to a separate class
        self.interacted = False
        self.realRect = pygame.Rect((centerX-self.rect[2]//2),(centerY-self.rect[3]//2),self.rect[2],self.rect[3])
        self.cost = interactObject.buyCost
        self.centerX = centerX
        self.centerY = centerY
        self.center = [centerX, centerY]
        self.drawnCoordinates = [[None, None],[None, None]]
        self.pressed = False
        self.onscreen = False
        self.previousInteract = False
        if self.interactType == "gunSpawn":         #Setting the initial prompt and settings based on the interactType
            self.action = interactObject.spawn
            self.prompt = "Press E for " + interactObject.weaponName + " (Cost: " + str(interactObject.buyCost) + ")"
            self.vertices = [[(centerX-self.rect[2]//2),(centerY-self.rect[3]//2)],[(centerX+self.rect[2]//2),(centerY+self.rect[3]//2)]]
        elif self.interactType == "perk":
            self.action = interactObject.applyPerk
            self.prompt = "Turn power on"
            self.vertices = [[(centerX-self.rect[2]//2),(centerY-self.rect[3]//2)],[(centerX+self.rect[2]//2),(centerY+self.rect[3]//2)]]
        elif self.interactType == "packapunch":
            self.action = interactObject.upgradeWeapon
            self.prompt = "Turn power on"
            self.vertices = [[(centerX-self.rect[2]//2),(centerY-self.rect[3]//2)],[(centerX+self.rect[2]//2),(centerY+self.rect[3]//2)]]
        elif self.interactType == "mystery_box":
            self.action = interactObject.spawnRandomWep
            self.prompt = "Press E for Mystery Box Weapon (Cost: 950)"
            self.vertices = [[(centerX-self.rect[2]//2),(centerY-self.rect[3]//2)],[(centerX+self.rect[2]//2),(centerY+self.rect[3]//2)]]
        elif self.interactType == "power":
            self.action = interactObject.turnPowerON
            self.prompt = "Press E to turn the power on"
            self.vertices = [[(centerX-self.rect[2]//2),(centerY-self.rect[3]//2)],[(centerX+self.rect[2]//2),(centerY+self.rect[3]//2)]]
        elif self.interactType == "door":       #Special case for door where the obstructing area and the interactable area are very different
            self.occupied = [[None, None],[None, None]]
            self.action = interactObject.unlock
            self.prompt = "Press E to unlock this area (Cost: " + str(interactObject.buyCost) + ")"
            self.obstructing = True
            self.passable = False
            if "doorv2" in interactObject.image:
                self.rect[2] = 40
                self.rect[3] = 20
            elif "door" in interactObject.image:
                self.rect[2] = 20
                self.rect[3] = 40
            self.vertices = [[(centerX-self.rect[2]//2),(centerY-self.rect[3]//2)],[(centerX+self.rect[2]//2),(centerY+self.rect[3]//2)]]
            self.rect[0] = self.vertices[0][0]
            self.rect[1] = self.vertices[0][1]
            self.rect2[2] = self.image.get_rect()[2]
            self.rect2[3] = self.image.get_rect()[3]
            self.occupied[0] = [self.rect[0]//20, self.rect[1]//20]
            if "doorv2" in interactObject.image:
                self.occupied[1] = [self.rect[0]//20 + 1, self.rect[1]//20]
            elif "door" in interactObject.image:
                self.occupied[1] = [self.rect[0]//20, self.rect[1]//20 + 1]
        self.canInteract = True
    def update(self, player, weaponList, cameraBounds, powerON): #Class function that updates the interactable object
        self.drawnCoordinates[0][0] = self.center[0]-(cameraBounds[0][0]+self.rect2[2]//2)
        self.drawnCoordinates[0][1] = self.center[1]-(cameraBounds[0][1]+self.rect2[3]//2)
        self.drawnCoordinates[1][0] = self.drawnCoordinates[0][0] + self.rect2[2]
        self.drawnCoordinates[1][1] = self.drawnCoordinates[0][1] + self.rect2[3]
        self.rect2[0] = self.drawnCoordinates[0][0]
        self.rect2[1] = self.drawnCoordinates[0][1]
        self.rect[0] = self.vertices[0][0]-cameraBounds[0][0]
        self.rect[1] = self.vertices[0][1]-cameraBounds[0][1]
        if not self.interacted:     #Checks if the object has been interacted with
            if self.interactType == "gunSpawn":                 #Changes prompt based on the interactType
                if self.interactObject.weaponName in player.guns:
                    self.cost = self.interactObject.ammoCost
                    if self.interactObject.weaponName in player.guns and self.interactObject.upgraded:
                        self.cost = 4500
                    self.prompt = "Press E to refill your ammo for " + self.interactObject.weaponName + " (Cost: " + str(self.cost) + ")"
                else:
                    self.prompt = "Press E for " + self.interactObject.weaponName + " (Cost: " + str(self.interactObject.buyCost) + ")"
            elif self.interactType == "perk":
                if self.interactObject.perkType in player.perks:
                    self.prompt = "You already have this perk!"
                    self.interacted = True
                    self.canInteract = False
                elif powerON:
                    self.prompt = "Press E for " + self.interactObject.perkName + " (Cost: " + str(self.interactObject.buyCost) + ")"
                    self.canInteract = True
                else:
                    self.prompt = "Turn power on"
                    self.canInteract = False
            elif self.interactType == "packapunch":
                if powerON:
                    self.prompt = "Pack-A-Punch Upgrade! (Cost: 5000)"
                    self.canInteract = True
                else:
                    self.prompt = "Turn power on"
                    self.canInteract = False
                for i in weaponList:
                    if i.weaponName == player.guns[player.currentGun]:
                        if i.upgraded == True:
                            self.prompt = "You can't Pack-A-Punch this gun anymore!"
                            self.canInteract = False
                        """else:
                            self.prompt = "Pack-A-Punch Upgrade! (Cost: 5000)"
                            self.canInteract = True"""
            elif self.interactType == "mystery_box":
                if self.interactObject.numOfUses >= 5:
                    self.prompt = "You've reached the max amount of uses!"
                    self.interacted = True
                    self.canInteract = False
                else:
                    self.prompt = "Press E for Mystery Box Weapon (Cost: 950)"
                    self.canInteract = True
            elif self.interactType == "door":
                if self.interactObject.unlocked:
                    self.prompt = ""
                    self.obstructing = False
                    self.interacted = True
                    self.passable = True
                    self.canInteract = False
                else:
                    self.prompt = "Press E to unlock this area (Cost: " + str(self.interactObject.buyCost) + ")"
                    self.obstructing = True
                    self.interacted = False
                    self.passable = False
                    self.canInteract = True
            elif self.interactType == "power":
                if self.interactObject.powerON:
                    self.prompt = "Power is now on"
                    self.interacted = True
                    self.canInteract = False
                else:
                    self.prompt = "Press E to turn the power on"
                    self.canInteract = True
    def draw(self, cameraBounds):   #Class function that draws the interactable object to the screen
        if self.vertices[1][0] >= cameraBounds[0][0] and self.vertices[0][0] < cameraBounds[1][0] and self.vertices[1][1] >= cameraBounds[0][1] and self.vertices[0][1] < cameraBounds[1][1]: #Checks if it's within the boundaries of the camera
                self.onscreen = True    #Necessary for collision detection
                screen.blit(self.image, self.rect2)
        else:
            self.onscreen = False
    def withinRange(self, cameraCenter): #Class function that checks if the player is close enough to interact with the object (standing on top or next to it)
        if self.realRect.collidepoint(cameraCenter):return True #If close enough, return true
        return False                                            #Otherwise return False
    def callBack(self, player, weaponList, powerON):    #Class function that activates the interaction
        if player.money >= self.cost and self.interacted == False and self.canInteract: #if the necessary conditions are met
            if self.interactType == "packapunch" or self.interactType == "perk":    #If the type is one of these
                if powerON:                         #Check if the power is on
                    player.money -= self.cost       #Then subtract the cost from the player's points/money
                    self.action(player, weaponList) #Call the action
            else:                               #Type is not pack-a-punch or perk
                player.money -= self.cost       #Subtract cost
                self.action(player, weaponList) #Call action
    def interaction(self):  #Class function that determines if the object has turned from not interacted to interacted
        if self.previousInteract != self.interacted:
            self.previousInteract = self.interacted
            return True #Returns true if interaction has happened
        return False    #Otherwise return false
    def reset(self):    #Class function that resets the interactable and the class associated
        self.interactObject.reset()

class spawnPoint(): #Player Spawn Class, stores the initial position of the player
    def __init__(self, x, y):
        self.x = x
        self.y = y

class zombieSpawn(window):  #Zombie Spawn Class, subclass of the Window class
    def __init__(self, X, Y, width = 20, height = 20):
        super().__init__(X, Y, width, height)
        self.spawnX = (X + width/2) #Spawn location attributes to spawn zombies
        self.spawnY = (Y + height/2)
        self.passable = False #Player cannot pass through it
    def draw(self, cameraBounds): #Same draw function as the window class, only draws in a different colour
        if self.vertices[1][0] >= cameraBounds[0][0] and self.vertices[0][0] < cameraBounds[1][0]:
            if self.vertices[1][1] >= cameraBounds[0][1] and self.vertices[0][1] < cameraBounds[1][1]:
                self.onscreen = True
                pygame.draw.rect(screen, (0,0,0), (self.drawnCoordinates[0][0], self.drawnCoordinates[0][1], self.width, self.height))
        else:
            self.onscreen = False

#Class declarations
spawnPoint = spawnPoint(4000, 4000)             #Player spawn
mainPlayer = player(screenWidth, screenHeight)  #Player
mainMap = mapClass(spawnPoint.x, spawnPoint.y)  #Map
hud = hud()                                     #HUD
waveTracker = wave()                            #Round tracker
zombie1 = zombie()                              #All the zombies
zombie2 = zombie()                              #
zombie3 = zombie()                              #
zombie4 = zombie()                              #
zombie5 = zombie()                              #
zombie6 = zombie()                              #
zombie7 = zombie()                              #
zombie8 = zombie()                              #
zombie9 = zombie()                              #
zombie10 = zombie()                             #
zombie11 = zombie()                             #
zombie12 = zombie()                             #
zombie13 = zombie()                             #
zombie14 = zombie()                             #
zombie15 = zombie()                             #
zombie16 = zombie()                             #
zombie17 = zombie()                             #
zombie18 = zombie()                             #
zombie19 = zombie()                             #
zombie20 = zombie()                             #
zombie21 = zombie()                             #
zombie22 = zombie()                             #
zombie23 = zombie()                             #
zombie24 = zombie()                             #Putting it all in a list for easy access and iteration capabilities
zombieList = [zombie1, zombie2, zombie3, zombie4, zombie5, zombie6, zombie7, zombie8, zombie9, zombie10, zombie11, zombie12, zombie13, zombie14, zombie15, zombie16, zombie17, zombie18, zombie19, zombie20, zombie21, zombie22, zombie23, zombie24]
bullet1 = bullet()                              #All the bullets
bullet2 = bullet()                              #
bullet3 = bullet()                              #
bullet4 = bullet()                              #
bullet5 = bullet()                              #
bullet6 = bullet()                              #
bullet7 = bullet()                              #
bullet8 = bullet()                              #
bullet9 = bullet()                              #
bullet10 = bullet()                             #
bullet11 = bullet()                             #
bullet12 = bullet()                             #
bullet13 = bullet()                             #
bullet14 = bullet()                             #
bullet15 = bullet()                             #
bullet16 = bullet()                             #
bullet17 = bullet()                             #
bullet18 = bullet()                             #
bullet19 = bullet()                             #
bullet20 = bullet()                             #
bullet21 = bullet()                             #
bullet22 = bullet()                             #
bullet23 = bullet()                             #
bullet24 = bullet()                             #
bullet25 = bullet()                             #
bullet26 = bullet()                             #
bullet27 = bullet()                             #
bullet28 = bullet()                             #
bullet29 = bullet()                             #
bullet30 = bullet()                             #
bullet31 = bullet()                             #
bullet32 = bullet()                             #
bullet33 = bullet()                             #
bullet34 = bullet()                             #
bullet35 = bullet()                             #
bullet36 = bullet()                             #
bullet37 = bullet()                             #
bullet38 = bullet()                             #
bullet39 = bullet()                             #
bullet40 = bullet()                             #
bullet41 = bullet()                             #
bullet42 = bullet()                             #
bullet43 = bullet()                             #
bullet44 = bullet()                             #
bullet45 = bullet()                             #
bullet46 = bullet()                             #
bullet47 = bullet()                             #
bullet48 = bullet()                             #
bullet49 = bullet()                             #
bullet50 = bullet()                             #Bullets put into a list for easy access and iteration capabilites
bulletList = [bullet1, bullet2, bullet3, bullet4, bullet5, bullet6, bullet7, bullet8, bullet9, bullet10, bullet11, bullet12, bullet13, bullet14, bullet15, bullet16, bullet17, bullet18, bullet19, bullet19, bullet20, bullet21, bullet22, bullet23, bullet24, bullet25, bullet26, bullet27, bullet28, bullet29, bullet30, bullet31, bullet32, bullet33, bullet34, bullet35, bullet36, bullet37, bullet38, bullet39, bullet40, bullet41, bullet42, bullet43, bullet44, bullet45, bullet46, bullet47, bullet48, bullet49, bullet50]

#weapon class declarations
m1911 = weapon("assets/sprites/weapons/pistols/starting_pistol.png", "M1911", 40, degToRad(1), 1, 250, "semiauto", 1000, 9, 36, 50000, 6, 200, 100, weaponSFX = "assets/sfx/m1911_shot.wav")
revolver = weapon("assets/sprites/weapons/pistols/44_magnum.png", "Magnum .44 Revolver", 2000, degToRad(1), 1, 200, "semiauto", 2250, 6, 24, 2500, 6, 0, 1000, weaponSFX = "assets/sfx/revolver_shot.wav")
luger = weapon("assets/sprites/weapons/pistols/luger.png", "Luger", 200, degToRad(1), 1, 650, "fullauto", 1500, 16, 64, 400, 4, 400, 650, weaponSFX = "assets/sfx/luger_shot.wav")
double_barrel_sawed_off = weapon("assets/sprites/weapons/pistols/double_barrel_sawed_off.png", "Double Barrel Sawed Off", 200, degToRad(10), 10, 900, "semiauto", 1500, 2, 24, 200, 2, 0, 2000, weaponSFX = "assets/sfx/double_barrel_shot.wav")
ak_47 = weapon("assets/sprites/weapons/assault_rifles/ak47.png", "AK 47", 1500, degToRad(3), 1, 600, "fullauto", 1750, 30, 240, 3000, 25, 0, 2750, weaponSFX = "assets/sfx/ak47_shot.wav")
basic_ar = weapon("assets/sprites/weapons/assault_rifles/basic_ar.png", "Basic Rifle", 450, degToRad(2), 1, 900, "fullauto", 1500, 30, 300, 1000, 30, 0, 900, weaponSFX = "assets/sfx/basic_ar_shot.wav")
famas = weapon("assets/sprites/weapons/assault_rifles/famas.png", "Famas", 1050, degToRad(2), 1, 1200, "fullauto", 1350, 20, 220, 2000, 15, 0, 2550, weaponSFX = "assets/sfx/famas_shot.wav")
galil_ar = weapon("assets/sprites/weapons/assault_rifles/galil_ar.png", "Galil AR", 1150, degToRad(3), 1, 600, "fullauto", 1750, 30, 240, 2500, 20, 0, 1750, weaponSFX = "assets/sfx/galil_shot.wav")
m16 = weapon("assets/sprites/weapons/assault_rifles/m16.png", "M16", 1250, degToRad(2), 1, 900, "fullauto", 1500, 30, 240, 6000, 30, 0, 3000, weaponSFX = "assets/sfx/m4_shot.wav")
basic_shotgun = weapon("assets/sprites/weapons/shotguns/basic_shotgun.png", "Basic Shotgun", 100, degToRad(10), 12, 50, "semiauto", 4500, 8, 32, 200, 4, 0, 850, weaponSFX = "assets/sfx/mp133_shot.wav")
double_barrel_shotgun = weapon("assets/sprites/weapons/shotguns/double_barrel_shotgun.png", "Double Barrel Shotgun", 150, degToRad(7), 10, 900, "semiauto", 1500, 2, 24, 200, 2, 0, 1500, weaponSFX = "assets/sfx/double_barrel_shot.wav")
mp_133 = weapon("assets/sprites/weapons/shotguns/mp-133.png", "MP-133", 125, degToRad(10), 12, 90, "semiauto", 5000, 6, 24, 100, 4, 0, 2000, weaponSFX = "assets/sfx/mp133_shot.wav")
spas_12 = weapon("assets/sprites/weapons/shotguns/spas-12.png", "Spas-12", 200, degToRad(6), 10, 60, "semiauto", 5000, 6, 24, 300, 2, 0, 3250, weaponSFX = "assets/sfx/spas_12_shot.wav")
uzi = weapon("assets/sprites/weapons/sub_machine_guns/uzi.png", "Uzi", 700, degToRad(1), 1, 900, "fullauto", 1250, 25, 125, 1000, 15, 150, 1500, weaponSFX = "assets/sfx/uzi_shot.wav")
mp40 = weapon("assets/sprites/weapons/sub_machine_guns/mp40.png", "MP40", 850, degToRad(1), 1, 900, "fullauto", 1250, 20, 100, 1500, 20, 200, 1750, weaponSFX = "assets/sfx/mp40_shot.wav")
automatic_shotgun = weapon("assets/sprites/weapons/shotguns/automatic_shotgun.png", "Automatic Shotgun", 300, degToRad(12), 12, 300, "fullauto", 3500, 5, 50, 500, 2, 0, 0, weaponSFX = "assets/sfx/automatic_shotgun_shot.wav", weighting = 25)
mp5 = weapon("assets/sprites/weapons/sub_machine_guns/mp5.png", "MP5", 950, degToRad(1), 1, 1050, "fullauto", 1250, 30, 240, 4000, 20, 150, 0, weaponSFX = "assets/sfx/mp5_shot.wav", weighting = 38)
hk21 = weapon("assets/sprites/weapons/light_machine_guns/hk21.png", "HK21", 3500, degToRad(1), 1, 535, "fullauto", 3750, 125, 500, 4000, 25, 0, 0, weaponSFX = "assets/sfx/hk21_shot.wav", weighting = 15)
rpk = weapon("assets/sprites/weapons/light_machine_guns/rpk.png", "RPK", 3500, degToRad(3), 1, 750, "fullauto", 4000, 100, 400, 4000, 25, 0, 0, weaponSFX = "assets/sfx/rkp_shot.wav", weighting = 15)
mg42 = weapon("assets/sprites/weapons/light_machine_guns/mg42.png", "MG42", 4000, degToRad(1), 1, 937, "fullauto", 5000, 125, 500, 10000, 0, 426, 0, weaponSFX = "assets/sfx/mg42_shot.wav", weighting = 5)
rail_gun = weapon("assets/sprites/weapons/mystery_box_weapons/rail_gun.png", "Rail Gun", 5000, 0, 1, 120, "fullauto", 4000, 15, 160, 15000, 5, 0, 0, weaponSFX = "assets/sfx/railgun_shot.wav", weighting = 1)
death_machine = weapon("assets/sprites/weapons/mystery_box_weapons/death_machine.png", "Death Machine", 2000, degToRad(1), 1, 1500, "fullauto", 10000, 500, 1000, 5000, 250, 250, 0, weaponSFX = "assets/sfx/death_machine_shot.wav", weighting = 1)

#Weapon list containing all the weapons
weaponList = [
    m1911, revolver, luger, double_barrel_sawed_off,
    ak_47, basic_ar, famas, galil_ar, m16, hk21, rpk, mg42,
    basic_shotgun, double_barrel_shotgun, mp_133, spas_12,
    automatic_shotgun, mp5, uzi, mp40, rail_gun, death_machine
    ]

#perk class declarations
juggernog = perk("assets/sprites/perks/juggernog.png", "juggernog", "Juggernog", 2500)
speedcola = perk("assets/sprites/perks/speed_cola.png", "speedcola", "Speed Cola", 3000)
doubletap = perk("assets/sprites/perks/double_tap.png", "doubletap", "Double Tap Root Beer", 2000)
mule = perk("assets/sprites/perks/mule_kick.png", "mule", "Mule Kick", 4000)
packapunch1 = pack_a_punch("assets/sprites/pack-a-punch/packapunch.png")
packapunch2 = pack_a_punch("assets/sprites/pack-a-punch/packapunchv2.png")
power = power("assets/sprites/powerswitch.png")

#Lists and sprite groups stuff
interactableList = pygame.sprite.Group() #pygame.sprite.Group is a special list that contains sprites
spawnList = []

#Map Declaration
door2 = door("assets/sprites/doors/door.png", 1000)
door1 = door("assets/sprites/doors/door.png", 750)
door3 = door("assets/sprites/doors/door.png", 1000)
door4 = door("assets/sprites/doors/doorv2.png", 1000)
door5 = door("assets/sprites/doors/door.png", 750)
door6 = door("assets/sprites/doors/door.png", 1000)
door7 = door("assets/sprites/doors/doorv2.png", 1250)
door8 = door("assets/sprites/doors/door.png", 1000)
mysterybox = mystery_box("assets/sprites/mystery_box/mystery_box_v2.png", weaponList)
mysterybox1 = mystery_box("assets/sprites/mystery_box/mystery_box.png", weaponList)
mysterybox2 = mystery_box("assets/sprites/mystery_box/mystery_box.png", weaponList)
mysterybox3 = mystery_box("assets/sprites/mystery_box/mystery_box_v2.png", weaponList)
interactable1 = interactable(4100, 3760, "gunSpawn", basic_ar)
interactable2 = interactable(3810, 4140, "door", door1)
interactable3 = interactable(3810, 4380, "door", door2)
interactable4 = interactable(4560, 4960, "power", power)
interactable5 = interactable(4100, 3900, "gunSpawn", luger)
interactable6 = interactable(3310, 4160, "gunSpawn", m16)
interactable7 = interactable(3600, 4380, "gunSpawn", uzi)
interactable8 = interactable(4260, 4740, "gunSpawn", double_barrel_shotgun)
interactable9 = interactable(3400, 4380, "perk", speedcola)
interactable10 = interactable(4000, 4220, "gunSpawn", spas_12)
interactable11 = interactable(4560, 4720, "gunSpawn", famas)
interactable12 = interactable(4310, 4240, "door", door3)
interactable13 = interactable(4760, 4690, "door", door4)
interactable14 = interactable(4580, 4200, "mystery_box", mysterybox)
interactable15 = interactable(4130, 3940, "door", door5)
interactable16 = interactable(4370, 3640, "door", door6)
interactable17 = interactable(4780, 3720, "mystery_box", mysterybox2)
interactable18 = interactable(4660, 3900, "gunSpawn", revolver)
interactable19 = interactable(4560, 4100, "perk", mule)
interactable20 = interactable(3270, 4340, "door", door8)
interactable21 = interactable(3860, 3740, "packapunch", packapunch2)
interactable22 = interactable(4295, 3730, "gunSpawn", ak_47)
interactable23 = interactable(4500, 3560, "perk", doubletap)
interactable24 = interactable(4220, 3520, "mystery_box", mysterybox1)
interactable25 = interactable(3240, 4200, "perk", juggernog)
interactable26 = interactable(2900, 4340, "mystery_box", mysterybox3)
wall1 = wall(3760, 3700, 60, 300)
wall2 = wall(3760, 3660, 240, 60)
wall3 = wall(4060, 3660, 120, 60)
wall4 = wall(4120, 3720, 60, 80)
wall5 = wall(4120, 3860, 60, 60)
wall6 = wall(4120, 4020, 60, 40)
wall7 = wall(4120, 4120, 300, 40)
wall8 = wall(3880, 4160, 260, 20)
wall9 = wall(3400, 4060, 420, 60)
wall10 = wall(3760, 4000, 20, 60)
wall11 = wall(3260, 4060, 80, 60)
wall12 = wall(3260, 4120, 20, 200)
wall13 = wall(3340, 4400, 480, 60)
wall14 = wall(3780, 4160, 40, 140)
wall15 = wall(3800, 4420, 20, 300)
wall16 = wall(3800, 4780, 500, 20)
wall17 = wall(4300, 4260, 60, 540)
wall18 = wall(4140, 4160, 280, 20)
wall19 = wall(4300, 4300, 120, 20)
wall20 = wall(4480, 4300, 200, 20)
wall21 = wall(4480, 4120, 240, 60)
wall22 = wall(4680, 4300, 40, 400)
wall23 = wall(4680, 3600, 40, 580)
wall24 = wall(4800, 3600, 40, 1380)
wall25 = wall(4600, 4680, 100, 20)
wall26 = wall(4500, 4680, 20, 300)
wall27 = wall(4500, 4680, 40, 20)
wall28 = wall(4500, 4980, 100, 20)
wall29 = wall(4660, 4980, 180, 20)
wall30 = wall(4360, 3580, 480, 20)
wall31 = wall(4000, 3660, 60, 20)
wall32 = wall(4140, 3420, 60, 240)
wall33 = wall(4140, 3300, 60, 60)
wall34 = wall(4180, 3660, 200, 40)
wall35 = wall(4140, 3360, 20, 60)
wall36 = wall(4200, 3300, 220, 60)
wall37 = wall(4480, 3300, 160, 60)
wall38 = wall(4640, 3300, 60, 140)
wall39 = wall(4640, 3500, 60, 80)
wall40 = wall(4680, 3440, 20, 60)
wall41 = wall(3260, 4360, 20, 100)
wall42 = wall(3340, 4060, 60, 20)
wall43 = wall(3280, 4440, 60, 20)
wall44 = wall(4420, 3300, 60, 20)
wall45 = wall(2820, 4120, 160, 60)
wall46 = wall(2980, 4120, 60, 20)
wall47 = wall(3040, 4120, 220, 60)
wall48 = wall(2820, 4180, 40, 240)
wall49 = wall(2860, 4360, 200, 60)
wall50 = wall(3060, 4400, 60, 20)
wall51 = wall(3120, 4360, 140, 60)
window1 = window(3780, 4000, 40, 60)
window2 = window(4000, 3680, 60, 40)
window3 = window(4120, 3800, 60, 60)
window4 = window(4120, 3960, 20, 60)
window5 = window(4120, 4060, 60, 60)
window6 = window(3340, 4080, 60, 40)
window7 = window(3280, 4400, 60, 40)
window8 = window (3780, 4720, 40, 60)
window9 = window (4420, 4300, 60, 40)
window10 = window (4420, 4120, 60, 60)
window11 = window (4540, 4660, 60, 40)
window12 = window (4600, 4980, 60, 40)
window13 = window (4720, 3600, 80, 40)
window14 = window (4720, 4680, 20, 20)
window15 = window (4780, 4680, 20, 20)
window16 = window (4300, 4180, 20, 40)
window17 = window (3800, 4300, 20, 60)
window18 = window (3800, 4160, 80, 20)
window19 = window(4360, 3600, 20, 20)
window20 = window(4160, 3360, 40, 60)
window21 = window(4640, 3440, 40, 60)
window22 = window(2980, 4140, 60, 40)
window23 = window(3060, 4360, 60, 40)
window24 = window(4420, 3340, 60, 20)
spawn1 = zombieSpawn(4000, 3680, 60, 20)
spawn2 = zombieSpawn(4140, 3800, 20, 60)
spawn3 = zombieSpawn(4140, 4060, 20, 60)
spawn4 = zombieSpawn(3780, 4000, 20, 60)
spawn5 = zombieSpawn(3340, 4080, 60, 20)
spawn6 = zombieSpawn(3280, 4420, 60, 20)
spawn7 = zombieSpawn(3780, 4720, 20, 60)
spawn8 = zombieSpawn(4420, 4320, 60, 20)
spawn9 = zombieSpawn(4420, 4140, 60, 20)
spawn10 = zombieSpawn(4720, 3600, 80, 20)
spawn11 = zombieSpawn(4600, 5000, 60, 20)
spawn12 = zombieSpawn(4540, 4660, 60, 20)
spawn13 = zombieSpawn(4160, 3360, 20, 60)
spawn14 = zombieSpawn(4420, 3320, 60, 20)
spawn15 = zombieSpawn(4660, 3440, 20, 60)
spawn16 = zombieSpawn(2980, 4140, 60, 20)
spawn17 = zombieSpawn(3060, 4380, 60, 20)

#Putting the map parts into their respective lists
terrainList = [wall1, wall2, wall3, wall4, wall5, wall6, wall7, wall8, wall9, wall10, wall11, wall12, wall13, wall14, wall15, wall16, wall17, wall18, wall19, wall20, wall21, wall22, wall23, wall24, wall25, wall26, wall27, wall28, wall29]
terrainList.extend([wall30, wall31, wall32, wall33, wall34, wall35, wall36, wall37, wall38, wall39, wall40, wall41, wall42, wall43, wall44, wall45, wall46, wall47, wall48, wall49, wall50, wall51])
terrainList.extend([window1, window2, window3, window4, window5, window6, window7, window8, window9, window10, window11, window12, window13, window14, window15, window16, window17, window18, window19, window20, window21, window22, window23, window24])
interactableList.add(interactable1, interactable2, interactable3, interactable4, interactable5, interactable6, interactable7, interactable8, interactable9, interactable10, interactable11, interactable12, interactable13, interactable14)
interactableList.add(interactable15, interactable16, interactable17, interactable18, interactable19, interactable20, interactable21, interactable22, interactable23, interactable24, interactable25, interactable26)
spawnList.extend([spawn1, spawn2, spawn3, spawn4, spawn5, spawn6, spawn7, spawn8, spawn9, spawn10, spawn11, spawn12, spawn13, spawn14, spawn15, spawn16, spawn17])
realMapGrid = createMapGrid(terrainList)
convertedMapGrid = convertMapGrid(realMapGrid)

#Thread Classes and Functions
#Pathfinder algorithm
def zombies_next_move(zombie_list, player, camera_center, mapGrid):
    for i in zombie_list:
        if i.alive:     #Checks if the zombie is alive, then calculates the path
            i.pathToPlayer = next_move([int(i.coordinates[0][0]//20),int(i.coordinates[0][1]//20)], [int(camera_center[0]//20),int(camera_center[1]//20)], mapGrid) #next_move is found in search_algorithm.py
            time.sleep(0.2)
        if not player.alive:    #Checks if the player has died
            sys.exit()          #If so, stop the thread

#pathfinder thread class
class nextPointThread(threading.Thread):    #Pathfinder Thread, subclass of threading.Thread
    def __init__(self, Name, ID):
        threading.Thread.__init__(self)
        self.Name = Name
        self.ID = ID
    def run(self):  #Class function, runs the thread
        global cameraCenter     #Get access the current camera center
        while True:             #Begin the calculations
            cameraCenterLock.acquire()  #Acquire a lock so that this thread can access the variable safely
            try:
                zombies_next_move(zombieList, mainPlayer, cameraCenter, convertedMapGrid)   #Run the path-finder
                time.sleep(0.2)
            finally:
                cameraCenterLock.release()  #Release the lock

def runGame():
    bgMusic.stop() #Stop the background music playing from the menu
    pathFinder = nextPointThread("pathFinderThread", 1) #Declare the pathfinder thread
    pathFinder.start()  #Start it
    inputX = 0
    inputY = 0
    fpsDelay = setFPS(70) #Set FPS
    gameState = True
    while gameState:
        inputX = 0
        inputY = 0
        #Check User Input
        modifiers = pygame.key.get_mods()
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    gameState = False
                    mainPlayer.alive = False
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
                if event.key == pygame.K_r:
                    pressedReload = True
                if event.key == pygame.K_e:
                    for i in interactableList:
                        if i.withinRange(mainMap.cameraGridCenter):
                            i.pressed = True
                if event.key == pygame.K_1:
                    mainPlayer.switchWeapon(1, weaponList)
                elif event.key == pygame.K_2:
                    mainPlayer.switchWeapon(2, weaponList)
                elif event.key == pygame.K_3 and 'mule' in mainPlayer.perks:
                    mainPlayer.switchWeapon(3, weaponList)
            if event.type == pygame.KEYUP:
                for i in interactableList:
                    if i.interacted:
                        continue
                    elif i.interactType == "perk" or i.interactType == "packapunch":
                        if not power.powerON:
                            continue
                    if event.key == pygame.K_e and i.pressed == True:
                        i.callBack(mainPlayer, weaponList, power.powerON)
                        i.pressed = False
                if event.key == pygame.K_r:
                    mainPlayer.startReloading = True
        mouseClick = win32api.GetKeyState(0x01)
        if mouseClick == -127 or mouseClick == -128:
            mainPlayer.shoot(bulletList, mouseClick, weaponList)
        
        #Updating Sprites Players and everything in between and Checking Conditions
        mainMap.updateCamera(inputX, inputY)
        for i in terrainList:
            i.update(mainMap.cameraBounds)
        for i in spawnList:
            i.update(mainMap.cameraBounds)
        mainPlayer.aim()
        mainPlayer.reload()
        for i in bulletList:
            i.update(mainPlayer, terrainList, zombieList, interactableList)
        cameraCenterLock.acquire()
        try:
            for i in zombieList:
                i.update(mainMap.cameraBounds, mainPlayer, mainMap.cameraGridCenter)
        finally:
            cameraCenterLock.release()
        interactableList.update(mainPlayer, weaponList, mainMap.cameraBounds, power.powerON)
        if mainPlayer.collided(terrainList):    #Collision has occured
            mainMap.cameraGridCenter = mainPlayer.collisionCheck(terrainList, mainMap.cameraGridCenter, screenDimensions, (inputX, inputY)) #Rectify camera pos
            mainMap.updateCamera(0, 0)                  #Reupdate everything
            for i in terrainList:
                i.update(mainMap.cameraBounds)
            for i in spawnList:
                i.update(mainMap.cameraBounds)
            interactableList.update(mainPlayer, weaponList, mainMap.cameraBounds, power.powerON)
            for i in zombieList:
                i.update(mainMap.cameraBounds, mainPlayer, mainMap.cameraGridCenter)
        if mainPlayer.collided(interactableList):
            mainMap.cameraGridCenter = mainPlayer.collisionCheck(interactableList, mainMap.cameraGridCenter, screenDimensions, (inputX, inputY))
            mainMap.updateCamera(0, 0)
            for i in terrainList:
                i.update(mainMap.cameraBounds)
            for i in spawnList:
                i.update(mainMap.cameraBounds)
            interactableList.update(mainPlayer, weaponList, mainMap.cameraBounds, power.powerON)
            for i in zombieList:
                i.update(mainMap.cameraBounds, mainPlayer, mainMap.cameraGridCenter)
        checkMapChange(convertedMapGrid, interactableList)
        waveTracker.update(zombieList, spawnList, mainMap.cameraGridCenter, mainMap.cameraBounds, mainPlayer)
        mainPlayer.regenHealth()
        hud.update(weaponList, mainPlayer, waveTracker.round)
        if mainPlayer.checkAlive(): #Player is no longer alive
            gameState = False       #Stop the game
            mainMap.cameraGridCenter = [spawnPoint.x, spawnPoint.y]
            for i in zombieList:
                i.alive = False

        #Clear Screen
        cls()
        
        #Draw to Buffer
        for i in interactableList:
            if i.interactType == "door":
                continue
            i.draw(mainMap.cameraBounds)
        for i in terrainList:
            if i.passable:
                i.draw(mainMap.cameraBounds)
        for i in spawnList:
            i.draw(mainMap.cameraBounds)
        for i in zombieList:
            i.draw(mainMap.cameraBounds)
        for i in bulletList:
            i.draw()
        for i in interactableList:
            if i.interactType == "door":
                if i.interactObject.unlocked:
                    continue
                i.draw(mainMap.cameraBounds)
        for i in terrainList:
            if not i.passable:
                i.draw(mainMap.cameraBounds)
        mainPlayer.draw()
        if mainPlayer.reloading:
            pygame.draw.rect(screen, (0, 165, 0), pygame.Rect(90, screenHeight-58, 160, 55))
            screen.blit(reloadText, (100, screenHeight-48))
        hud.draw([screenWidth, screenHeight], mainPlayer)
        promptText = promptFont.render("", False, (0,0,0))
        for i in interactableList:
            if i.withinRange(mainMap.cameraGridCenter):
                promptText = promptFont.render(i.prompt, False, (0,175,255))
                break
        screen.blit(promptText, (screenWidth/2-75, screenHeight/2-50))
        pygame.display.flip()       #Draw the buffer to the screen
        pygame.time.wait(fpsDelay)  #Delay

def titleScreen(): #Function that represents the main menu
    playButton = gui.button("Play Game", (screenWidth/2-140,500))    #Create the ui elements
    quitButton = gui.button("Quit Game", (screenWidth/2,600))
    highscoreButton = gui.button("Highscores", (screenWidth/2-40, 500))
    tutorialButton = gui.button("Tutorial", (screenWidth/2+60, 500))
    buttonList = [playButton, quitButton, highscoreButton, tutorialButton]
    title = pygame.image.load("assets/sprites/main_menu_title.png")
    titleoffset = title.get_width()//2
    choice = -1
    menuMusic = pygame.mixer.Sound("assets/zambies.wav")
    while choice == -1: #Mini update and draw loop
        pygame.event.get()  #Get any and all events so that the screen will draw properly
        if win32api.GetKeyState(0x01) == -127 or win32api.GetKeyState(0x01) == -128:    #Check for a mouseclick
            if playButton.rect.collidepoint(win32api.GetCursorPos()):       #If the mousewas over any buttons
                choice = 1
            if quitButton.rect.collidepoint(win32api.GetCursorPos()):
                pygame.quit()
                sys.exit()
            if highscoreButton.rect.collidepoint(win32api.GetCursorPos()):
                choice = 2
            if tutorialButton.rect.collidepoint(win32api.GetCursorPos()):
                choice = 3
        if not bgMusic.get_busy():  #If music is not already playing, play music
            bgMusic.play(menuMusic)
        cls()   #Clear screen
        screen.blit(title, (screenWidth/2-titleoffset, 100))    #Draw everything to the buffer
        for i in buttonList:
            i.draw(screen)
        pygame.display.flip()   #Draw buffer to screen
        pygame.time.wait(30)    #Delay
    del playButton  #Buttons no longer necessary, delete them
    del quitButton
    del highscoreButton
    del tutorialButton
    return choice

def retrieveScores(): #Function to read the highscores from the highscores.txt file
    readStream = open("highscores.txt", "r")    #Open the readStream
    highscoreArr = []
    for i in range(10):
        tempStr = readStream.readline().split() #reads the line and splits it into a list
        for i in tempStr:   #Remove any white space from the elements in the list
            i = i.strip()
        highscoreArr.append(tempStr)    #Add it to an output array
    readStream.close()  #Close the readStream
    return highscoreArr #Return the output array

def writeScores(inputArr):  #Function to write an inputArr to the highscore.txt file
    writeStream = open("highscores.txt", "w")   #Open the writeStream
    for i in range(len(inputArr)):
        outputStr = ""
        for j in range(len(inputArr[i])):
            outputStr += inputArr[i][j]     #Append everything to a string
            outputStr += " "
        outputStr += "\n"
        writeStream.write(outputStr)    #Write the stream to the file
    writeStream.close() #Close the writeStream

def highscores(): #Function that represents the highscores page
    backButton = gui.button("Back", (screenWidth/2, 650))               #Create ui elements
    titleFont = pygame.font.SysFont("Times New Roman", 24, bold = True)
    scoreFont = pygame.font.SysFont("Times New Roman", 12)
    titleText = titleFont.render("Highscores", False, (0,0,0))
    arrayToDisplay = retrieveScores()   #retrieve the scores
    scoreText = None
    getHighscore = True
    menuMusic = pygame.mixer.Sound("assets/zambies.wav")
    while getHighscore: #Mini update and draw loop
        pygame.event.get()  #Get events
        if win32api.GetKeyState(0x01) == -127 or win32api.GetKeyState(0x01) == -128:    #Check for mouse click and location
            if backButton.rect.collidepoint(win32api.GetCursorPos()):   #Check if a button has been clicked
                getHighscore = False
        if not bgMusic.get_busy():  #Play music if not playing any
            bgMusic.play(menuMusic)
        cls()   #Clear screen
        screen.blit(titleText, (screenWidth/2-300,100))         #Blit text to buffer
        scoreText = scoreFont.render("Name:", False, (0,0,0))
        screen.blit(scoreText, (screenWidth/2-300, 180))
        scoreText = scoreFont.render("Points:", False,(0,0,0))
        screen.blit(scoreText, (screenWidth/2-150, 180))
        scoreText = scoreFont.render("Kills:", False, (0,0,0))
        screen.blit(scoreText, (screenWidth/2, 180))
        scoreText = scoreFont.render("Round:", False, (0,0,0))
        screen.blit(scoreText, (screenWidth/2+150, 180))
        for i in range(len(arrayToDisplay)):
            offset = 300
            for j in range(len(arrayToDisplay[i])):
                scoreText = scoreFont.render(arrayToDisplay[i][j], False, (0,0,0))
                screen.blit(scoreText,(screenWidth/2-offset, (i*20)+200))
                offset -= 150
        backButton.draw(screen) #Draw button to buffer
        pygame.display.flip()   #Draw buffer to screen
        pygame.time.wait(30)    #Delay
    del backButton  #Deleting button

def getName():  #Function to retrieve player name when a new highscore has been achieved
    pygame.key.set_repeat() #Disables the key repeat so it only inputs one char at a time
    textBox = gui.TextInput((screenWidth/2, 400))   #Creating ui elements
    textBox.set_active()
    titleFont = pygame.font.SysFont("Times New Roman", 24, bold = True)
    plainFont = pygame.font.SysFont("Times New Roman", 14)
    titleText = titleFont.render("New Highscore!", False, (0,0,0))
    plainText = plainFont.render("Input Name", False, (0,0,0))
    inputting = True
    while inputting:    #Mini update and draw loop
        events = pygame.event.get() #Get events from event queue
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:        #Check if the user has stopped inputting
                    if textBox.get_text() == "":
                        pygame.key.set_repeat(10,10)    #Reenable key_repeat
                        return "Anonymous"              #Return Anonymous if no name was inputted
                    else:
                        pygame.key.set_repeat(10,10)
                        return textBox.get_text()       #Return name
        cls()   #Clear screen
        textBox.update(events, screen)  #This update event updates the class and draws to the screen
        screen.blit(titleText, (screenWidth/2, 300))    #Drawing the text
        screen.blit(plainText, (screenWidth/2, 350))
        pygame.display.flip()   #Drawing buffer to screen
        pygame.time.wait(30)    #Delay

def deathScreen():  #Function representing the death screen
    continueButton = gui.button("Continue", (screenWidth/2,650))        #Creating ui elements
    titleFont = pygame.font.SysFont("Times New Roman", 24, bold = True)
    subtitleFont = pygame.font.SysFont("Times New Roman", 18)
    plainFont = pygame.font.SysFont("Times New Roman", 14)
    highscoreArray = retrieveScores()       #Getting highscores
    if mainPlayer.money > int(highscoreArray[9][1]):    #If the player's score is high than the lowest score on the highscore list
        for i in range(len(highscoreArray)):            #Check where the score should go and push it in there
            if mainPlayer.money > int(highscoreArray[i][1]):
                playerName = getName()                  #Get name of the new highscore
                highscoreArray.insert(i, [playerName, str(mainPlayer.money), str(mainPlayer.totalKills), str(waveTracker.round)])   #Insert score at the specified index
                highscoreArray.pop(10)                  #Pop the last element of the list
                break                                   #Stop the search for where the new score should go
        writeScores(highscoreArray) #Write the new highscore array to highscore.txt
    dead = True
    while dead: #Mini update/draw loop
        pygame.event.get()  #Get events from event queue
        if win32api.GetKeyState(0x01) == -127 or win32api.GetKeyState(0x01) == -128:    #Check for mouse click
            if continueButton.rect.collidepoint(win32api.GetCursorPos()):   #Check if mouse has collided with the button
                dead = False    #Stop the loop if user has hit the button
        cls()   #Clear screen
        titleText = titleFont.render("Stats:", False, (0,0,0))                  #Drawing everything to the screen
        subtitleText = subtitleFont.render("Player:", False, (0,0,0))
        plainText =  plainFont.render("Player 1", False, (0,0,0))
        screen.blit(titleText, (screenWidth/2-113, 100))
        screen.blit(subtitleText, (screenWidth/2-113, 150))
        screen.blit(plainText, (screenWidth/2-113, 180))
        subtitleText = subtitleFont.render("Points:", False, (0,0,0))
        plainText = plainFont.render(str(mainPlayer.money), False, (0,0,0))
        screen.blit(subtitleText, (screenWidth/2-38, 150))
        screen.blit(plainText, (screenWidth/2-38, 180))
        subtitleText = subtitleFont.render("Kills:", False, (0,0,0))
        plainText = plainFont.render(str(mainPlayer.totalKills), False, (0,0,0))
        screen.blit(subtitleText, (screenWidth/2+38, 150))
        screen.blit(plainText, (screenWidth/2+38, 180))
        subtitleText = subtitleFont.render("Round:", False, (0,0,0))
        plainText = plainFont.render(str(waveTracker.round), False, (0,0,0))
        screen.blit(subtitleText, (screenWidth/2+113, 150))
        screen.blit(plainText, (screenWidth/2+113, 180))
        continueButton.draw(screen)
        pygame.display.flip()   #Drawing to buffer
        pygame.time.wait(30)    #Delay
    mainPlayer.reset()      #Once the loop to view stats after death has terminated
    waveTracker.reset()     #reset everything
    mainMap.reset()
    hud.reset()
    for i in interactableList:
        i.interacted = False
        i.reset()
    for i in bulletList:
        i.shot = False
    for i in zombieList:
        i.alive = False
    for i in weaponList:
        i.reset()

def tutorial():
    backButton = gui.button("Back", (screenWidth/2, 650))               #Create ui elements
    titleFont = pygame.font.SysFont("Times New Roman", 24, bold = True)
    scoreFont = pygame.font.SysFont("Times New Roman", 12)
    titleText = titleFont.render("Tutorial", False, (0,0,0))
    tutorial = True
    while tutorial:
        pygame.event.get()
        if win32api.GetKeyState(0x01) == -127 or win32api.GetKeyState(0x01) == -128:    #Check for mouse click and location
            if backButton.rect.collidepoint(win32api.GetCursorPos()):   #Check if a button has been clicked
                tutorial = False
        if not bgMusic.get_busy():  #Play music if not playing any
            bgMusic.play(menuMusic)
        cls()
        scoreText = scoreFont.render("Use WASD to move around, W to go up, A to go left, S to go down, and D to go right", False, (0,0,0))      #Drawing text instructions to screen
        screen.blit(scoreText, (200, 100))
        scoreText = scoreFont.render("Different perks have different effects: Juggernog increases health, Speedcola increases reload time, Double tap Root Beer increases rate of fire, Mule Kick lets you have a third gun", False, (0,0,0))
        screen.blit(scoreText, (200, 150))
        scoreText = scoreFont.render("Press R to reload and E to interact with certain objects", False, (0,0,0))
        screen.blit(scoreText, (200, 125))
        backButton.draw(screen)
        pygame.display.flip()
        pygame.time.wait(30)

#main app loop
def main():
    playerChoice = -1       #Player hasn't made a choice yet
    while True:
        playerChoice = titleScreen()    #Run the title screen
        if playerChoice == 1:           #Player selected run game so run game, then when game terminates, run death screen
            runGame()
            deathScreen()
        elif playerChoice == 2:         #Player selected highscores so start highscores screen
            highscores()
        elif playerChoice == 3:         #Player selected tutorial, tutorial starts
            tutorial()                  #Loops back to title screen when done

if __name__ == "__main__":          #De facto to run main
    main()                          #Main will quit by itself when the quit game button has been clicked
