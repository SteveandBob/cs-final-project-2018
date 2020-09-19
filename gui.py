import sys
import time
import pygame
import pygame.locals as pl
import os.path
pygame.init()

class button:   #Button Class
    def __init__(self, txt, location, action=None, bg=(255,255,255),fg=(0,0,0),size=(80,30),font_name="Times New Roman",font_size=16):
        self.colour = bg
        self.bg = bg
        self.fg = fg
        self.size = size
        self.font = pygame.font.SysFont(font_name,font_size)
        self.txt = txt
        self.txt_surf = self.font.render(self.txt, 1, self.fg)  #Prerenders the text
        self.txt_rect = self.txt_surf.get_rect(center=[s//2 for s in self.size])    #Gets the size of the text surface
        self.surface = pygame.surface.Surface(size) #Creates a new surface with the size param
        self.rect = self.surface.get_rect(center=location)  #Gets the rectangle of the new surface around the center
    def mouseover(self):    #Class function that changes the button colour if the mouse is hovering over the button
        self.bg = self.colour
        pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(pos):
            self.bg = (200,200,200)
    def draw(self, screen): #Class function that draws the button to the screen
        self.mouseover()    #First checks if the mouse is hovering to change the background colour
        self.surface.fill(self.bg)
        self.surface.blit(self.txt_surf, self.txt_rect)
        screen.blit(self.surface, self.rect)

class TextInput: #Text Box Class, retrieves input
    def __init__(self, location, font = "Times New Roman", fontsize = 24):
        self.active = False #Var that determines if the text box is receiving input or not
        self.input_string = ""
        self.location = location
        self.fontsize = fontsize
        self.font = pygame.font.SysFont(font, fontsize)
        self.renderText = None
    def update(self, events, screen):   #Class function that updates and draws the text box to the screen
        if self.active:     #Checks if the textbox is inputting
            drawColour = (0,0,0)
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pl.K_BACKSPACE:
                        self.input_string = self.input_string[:-1]  #Deletes last char from string
                    else:
                        self.input_string += event.unicode          #Adds the unicode of the event from string
        else:
            drawColour(100, 100, 100)
        self.renderText = self.font.render(self.input_string, False, drawColour)    #Renders text
        screen.blit(self.renderText, (self.location))   #Draws rendered text to screen
    def get_text(self): #Class function that return the string currently being typed into the text box
        return self.input_string
    def set_active(self):   #Class function that sets the class to active
        self.active = True
    def set_unactive(self): #Class function that sets the class to inactive
        self.active = False
