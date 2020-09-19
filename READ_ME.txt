Run the exe to play the game. Open .py file with IDLE to view code.
Do not try to run game with IDLE, will show up errors as you will need to
install extra libraries

About camera and path-finding algorithm:

We implemented an abstract concept called a camera into our game.

Rather than a static view where the walls stay still regardless of player
movement, the walls would move relative to the player allowing for an
increased field of play and map.

To do this, we first envisioned an are of 8000 by 8000 pixels. The camera
would display only MAXSCREENHEIGHT by MAXSCREENWIDTH pixels of that map.
Objects would then be given a location on the 8000 by 8000 grid. The camera
would also have a location on the 8000 by 8000 grid denoting where and what
it was displaying. If the object was within the camera's view, we would
take it's location on the 8000 by 8000 grid and subtract from it the value
of the lowest possible x and y value displayed by the camera.

E.g. Camera is displaying from (1000, 1000) to (2366, 1768)
An object with a pos of (1100, 1100) would be displayed at
(1100-1000, 1100-1000) on the screen. If the camera was to move up by 500
pixels to display all pixels from (1000, 1500) to (2366, 2268)
The object at the pos of (1100, 1100) would be displayed at
(1100-1000, 1100-1500) which is below the screen, this object would not be
displayed.

The implementation of the camera is easy, simply update the camera's
position based on input from the keyboard. Then update the position of each
and every object in the game. If it's within the camera's view, it will
draw the object to the screen, otherwise it won't.

The next part which is the path-finding algorithm is much harder. First
step was finding a graph algorithm that could quickly and efficiently
calculate the path from each zombie to the player without exploring useless
areas. This is why we chose an a-star algorithm to find the path from each
zombie to the player. Following this choice, we decided to shrink the grid
of that the algorithm would explore to 400 by 400. This would mean that the
zombies would follow nodes separated by approximately 20 pixels. After
finding the path, we translated onto the 8000 by 8000 grid by multiplying
the point of the node by 20.