import sys
import time
import math
import scipy

class Node(object): #Node object, not class (object saves more memory)
    __slots__ = ['value', 'point', 'parent', 'H', 'G']
    def __init__(self, value, point):
        self.value = value  #Value points to " " or "%"
        self.point = point  #Coordinate grid point of the node
        self.parent = None  #Which node did the algorithm use to get here
        self.H = 0          #Heuristic
        self.G = 0          #Cost to move here
    def move_cost(self, other):
        return 0 if self.value == "." else 1 #Returns a move cost

def children(current, grid):    #Function to find the children of a node (nodes adjacent or diagonal to the current one)
    x,y=current.point   #unpack the current point
    checkList = [(x,y-1),(x-1,y-1),(x-1,y),(x-1,y+1),(x,y+1),(x+1,y+1),(x+1,y),(x+1,y-1)]   #Establish a list of all the coordinates to be returned
    links = None
    for i in checkList:
        if y-1 < 0:                         #Checks if any of the coordinates in checkList surpass the limits of the graph
            if (x, y-1) in checkList:
                checkList.remove((x, y-1))
            elif (x-1, y-1) in checkList:
                checkList.remove((x-1,y-1))
            elif (x+1, y-1) in checkList:
                checkList.remove((x+1,y-1))
        if y+1 > len(grid[0])-1:
            if (x, y+1) in checkList:
                checkList.remove((x, y+1))
            elif (x-1, y+1) in checkList:
                checkList.remove((x-1,y+1))
            elif (x+1, y+1) in checkList:
                checkList.remove((x+1,y+1))
        if x-1 < 0:
            if (x-1, y) in checkList:
                checkList.remove((x-1, y))
            elif (x-1, y+1) in checkList:
                checkList.remove((x-1,y+1))
            elif (x-1, y-1) in checkList:
                checkList.remove((x-1,y-1))        
        if x+1 > len(grid)-1:
            if (x+1, y) in checkList:
                checkList.remove((x+1, y))
            elif (x+1, y+1) in checkList:
                checkList.remove((x+1,y+1))
            elif (x+1, y-1) in checkList:
                checkList.remove((x+1,y-1))
    links = [grid[d[0]][d[1]] for d in checkList]   #Creates a list of everyvalue in checkList as a node on the graph
    return [link for link in links if link.value != "%"]    #Returns every element in links that doesn't have a value of "%"

def euclidean(point, point2): #Heuristic that calculates using manhattan distance
    return abs(point.point[0]-point2.point[0])+abs(point.point[1]-point2.point[1]) #Returns |x1-x2| + |y1-y2|

def calculatePath(start, goal, grid):   #Actual path finding algorithm
    for x in range(len(grid)):          #Resets every node's parent, G cost, and H cost
        for y in range(len(grid[x])):
            grid[x][y].parent = None
            grid[x][y].G = 0
            grid[x][y].H = 0
    current = start             #Sets the current node to the start node
    openset = set()             #Creates an openset for values that will be but haven't been explored
    closedset = set()           #Creates a closedset for values that have been explored
    openset.add(current)
    if goal.value == "%":   #Checks if the goal is in a wall, if so return no path
        path = []
        return path
    while openset:  #While there is still stuff in the openset
        current = min(openset, key=lambda o: o.G+o.H)   #Set current to node in openset with the smallest G + H value
        if current == goal: #Checks if the current point is the goal, if so
            path = []       #Return path
            while current.parent:           #While the current node has a parent
                path.append(current)        #Add the current node to the path
                current = current.parent    #Set the new node to the parent of the current node
            path.append(current)            #Add the last paren
            return path[::-1]               #Return everything in reverse order
        openset.remove(current)         #If the current point is not the goal
        closedset.add(current)          #Remove the current node from the openset and put into the openset
        for node in children(current, grid):    #Get the node's children and iterate through them
            if node in closedset:   #If the node is in the closedset (already explored)
                continue            #Skip it
            if node in openset:     #If the node is in the openset (not already explored)
                new_g = current.G + current.move_cost(node) #Reevaluate it
                if node.G > new_g:                          #If the cost is less than previous node
                    node.G = new_g                          #Set the current value to the previous one
                    node.parent = current                   #Set the node's parent to the current node
            else:                   #Otherwise if node is not in open or closed set
                node.G = current.G + current.move_cost(node)    #Evaluate the g cost
                node.H = euclidean(node, goal)                  #Evaluate the h cost
                node.parent = current                           #Set the parent
                openset.add(node)                               #Add it to the clsoed set

def next_move(zombie_center, player_center, mapGrid): #function that calculates path to the player
    pathToPlayer = calculatePath(mapGrid[zombie_center[0]][zombie_center[1]],mapGrid[player_center[0]][player_center[1]],mapGrid)
    # ^ Gets the path to the player from the zombie
    output = []                 #Takes the list of nodes
    if pathToPlayer != None:    #Returns the points of each node according to the real value on the map
        for i in pathToPlayer:
            output.append((i.point[0]*20+10,i.point[1]*20+10))
    return output
