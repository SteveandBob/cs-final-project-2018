# CS Final Project 2018

Mr. Chu CS Grade 11

This project is a 2D top-down shooter styled after Call of Duty's Zombies mode.

Graphics are done by retrieving the colour of every pixel on the screen and then
painting the pixel according to the colour.

Graphics are done using pygame, although in retrospect pyglet would have been a
better option.

"Camera" system is done by placing all objects in a coordinate system 8000x8000
pixels large. Camera would occupy exactly the size of your screen large on that
coordinate system. Camera would then display anything within the area it's
supposed to display.

Sound is in the game as well and run on a separate thread.
