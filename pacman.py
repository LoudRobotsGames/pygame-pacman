#! /usr/bin/python

# pacman.pyw
# By David Reilly

# Modified by Andy Sommerville, 8 October 2007:
# - Changed hard-coded DOS paths to os.path calls
# - Added constant SCRIPT_PATH (so you don't need to have pacman.pyw and res in your cwd, as long
# -   as those two are in the same directory)
# - Changed text-file reading to accomodate any known EOLn method (\n, \r, or \r\n)
# - I (happily) don't have a Windows box to test this. Blocks marked "WIN???"
# -   should be examined if this doesn't run in Windows
# - Added joystick support (configure by changing JS_* constants)
# - Added a high-score list. Depends on wx for querying the user's name

import pygame, sys, os, random
from pygame.locals import *

# WIN???
SCRIPT_PATH=sys.path[0]

# NO_GIF_TILES -- tile numbers which do not correspond to a GIF file
# currently only "23" for the high-score list
NO_GIF_TILES=[23]

FRAME_TIME = 20
DEBUGDRAW_CELLS = 1

NO_WX=1 # if set, the high-score code will not attempt to ask the user his name
USER_NAME=os.getlogin() # the default user name if wx fails to load or NO_WX

# Joystick defaults - maybe add a Preferences dialog in the future?
JS_DEVNUM=0 # device 0 (pygame joysticks always start at 0). if JS_DEVNUM is not a valid device, will use 0
JS_XAXIS=0 # axis 0 for left/right (default for most joysticks)
JS_YAXIS=1 # axis 1 for up/down (default for most joysticks)
JS_STARTBUTTON=0 # button number to start the game. this is a matter of personal preference, and will vary from device to device

# Must come before pygame.init()
pygame.mixer.pre_init(22050,16,2,512)
JS_STARTBUTTON=0 # button number to start the game. this is a matter of personal preference, and will vary from device to device
pygame.mixer.init()

clock = pygame.time.Clock()
pygame.init()

window = pygame.display.set_mode((1, 1))
pygame.display.set_caption("Pacman")

#screen = pygame.display.get_surface()

img_Background = pygame.image.load(os.path.join(SCRIPT_PATH,"res","backgrounds","1.gif")).convert()

snd_pellet = {}
snd_pellet[0] = pygame.mixer.Sound(os.path.join(SCRIPT_PATH,"res","sounds","pellet1.wav"))
snd_pellet[1] = pygame.mixer.Sound(os.path.join(SCRIPT_PATH,"res","sounds","pellet2.wav"))
snd_powerpellet = pygame.mixer.Sound(os.path.join(SCRIPT_PATH,"res","sounds","powerpellet.wav"))
snd_eatgh = pygame.mixer.Sound(os.path.join(SCRIPT_PATH,"res","sounds","eatgh2.wav"))
snd_fruitbounce = pygame.mixer.Sound(os.path.join(SCRIPT_PATH,"res","sounds","fruitbounce.wav"))
snd_eatfruit = pygame.mixer.Sound(os.path.join(SCRIPT_PATH,"res","sounds","eatfruit.wav"))
snd_extralife = pygame.mixer.Sound(os.path.join(SCRIPT_PATH,"res","sounds","extralife.wav"))

ghostcolor = {}
ghostcolor[0] = (255, 0, 0, 255)
ghostcolor[1] = (255, 181, 255, 255)
ghostcolor[2] = (128, 255, 255, 255)
ghostcolor[3] = (255, 128, 0, 255)
ghostcolor[4] = (50, 50, 255, 255) # blue, vulnerable ghost
ghostcolor[5] = (255, 255, 255, 255) # white, flashing ghost

GHOSTSTATE_NORMAL = 1
GHOSTSTATE_FRIGHT = 2
GHOSTSTATE_DEAD = 3

#      ___________________
# ___/  class definitions  \_______________________________________________

class game ():

    def defaulthiscorelist(self):
        return [ (100000,"David") , (80000,"Andy") , (60000,"Count Pacula") , (40000,"Cleopacra") , (20000,"Brett Favre") , (10000,"Sergei Pachmaninoff") ]

    def gethiscores(self):
        """If res/hiscore.txt exists, read it. If not, return the default high scores.
           Output is [ (score,name) , (score,name) , .. ]. Always 6 entries."""
        try:
            f=open(os.path.join(SCRIPT_PATH,"res","hiscore.txt"))
            hs=[]
            for line in f:
                while len(line)>0 and (line[0]=="\n" or line[0]=="\r"): line=line[1:]
                while len(line)>0 and (line[-1]=="\n" or line[-1]=="\r"): line=line[:-1]
                score=int(line.split(" ")[0])
                name=line.partition(" ")[2]
                if score>99999999: score=99999999
                if len(name)>22: name=name[:22]
                hs.append((score,name))
            f.close()
            if len(hs)>6: hs=hs[:6]
            while len(hs)<6: hs.append((0,""))
            return hs
        except IOError:
            return self.defaulthiscorelist()

    def writehiscores(self,hs):
        """Given a new list, write it to the default file."""
        fname=os.path.join(SCRIPT_PATH,"res","hiscore.txt")
        f=open(fname,"w")
        for line in hs:
            f.write(str(line[0])+" "+line[1]+"\n")
        f.close()

    def getplayername(self):
        return USER_NAME

    def updatehiscores(self,newscore):
        """Add newscore to the high score list, if appropriate."""
        hs=self.gethiscores()
        for line in hs:
            if newscore>=line[0]:
                hs.insert(hs.index(line),(newscore,self.getplayername()))
                hs.pop(-1)
                break
        self.writehiscores(hs)

    def makehiscorelist(self):
        "Read the High-Score file and convert it to a useable Surface."
        # My apologies for all the hard-coded constants.... -Andy
        f=pygame.font.Font(os.path.join(SCRIPT_PATH,"res","VeraMoBd.ttf"),10)
        scoresurf=pygame.Surface((276,86),pygame.SRCALPHA)
        scoresurf.set_alpha(200)
        linesurf=f.render(" "*18+"HIGH SCORES",1,(255,255,0))
        scoresurf.blit(linesurf,(0,0))
        hs=self.gethiscores()
        vpos=0
        for line in hs:
            vpos+=12
            linesurf=f.render(line[1].rjust(22)+str(line[0]).rjust(9),1,(255,255,255))
            scoresurf.blit(linesurf,(0,vpos))
        return scoresurf

    def drawmidgamehiscores(self):
        """Redraw the high-score list image after pacman dies."""
        self.imHiscores=self.makehiscorelist()

    def __init__ (self):
        self.levelNum = 0
        self.score = 0
        self.lives = 3

        # game "mode" variable
        # 1 = normal
        # 2 = hit ghost
        # 3 = game over
        # 4 = wait to start
        # 5 = wait after eating ghost
        # 6 = wait after finishing level
        self.mode = 0
        self.lastDirectionPressed = 'none'
        self.modeTimer = 0
        self.ghostTimer = 0
        self.ghostValue = 0
        self.fruitTimer = 0
        self.fruitScoreTimer = 0
        self.fruitScorePos = (0, 0)

        self.SetMode( 3 )

        # camera variables
        self.screenPixelPos = (0, 0) # absolute x,y position of the screen from the upper-left corner of the level
        self.screenNearestTilePos = (0, 0) # nearest-tile position of the screen from the UL corner
        self.screenPixelOffset = (0, 0) # offset in pixels of the screen from its nearest-tile position

        self.screenTileSize = (23, 21)
        self.screenSize = (self.screenTileSize[1] * 16, self.screenTileSize[0] * 16)

        # numerical display digits
        self.digit = {}
        for i in range(0, 10, 1):
            self.digit[i] = pygame.image.load(os.path.join(SCRIPT_PATH,"res","text",str(i) + ".gif")).convert()
        self.imLife = pygame.image.load(os.path.join(SCRIPT_PATH,"res","text","life.gif")).convert()
        self.imGameOver = pygame.image.load(os.path.join(SCRIPT_PATH,"res","text","gameover.gif")).convert()
        self.imReady = pygame.image.load(os.path.join(SCRIPT_PATH,"res","text","ready.gif")).convert()
        self.imLogo = pygame.image.load(os.path.join(SCRIPT_PATH,"res","text","logo.gif")).convert()
        self.imHiscores = self.makehiscorelist()

    def StartNewGame (self):
        self.levelNum = 1
        self.score = 0
        self.lives = 3

        self.SetMode( 4 )
        thisLevel.LoadLevel( thisGame.GetLevelNum() )

    def AddToScore (self, amount):

        extraLifeSet = [25000, 50000, 100000, 150000]

        for specialScore in extraLifeSet:
            if self.score < specialScore and self.score + amount >= specialScore:
                snd_extralife.play()
                thisGame.lives += 1

        self.score += amount


    def DrawScore (self):
        self.DrawNumber (self.score, (24 + 16, self.screenSize[1] - 24) )

        for i in range(0, self.lives, 1):
            screen.blit (self.imLife, (24 + i * 10 + 16, self.screenSize[1] - 12) )

        screen.blit (thisFruit.imFruit[ thisFruit.fruitType ], (4 + 16, self.screenSize[1] - 20) )

        if self.mode == 3:
            screen.blit (self.imGameOver, (self.screenSize[0] / 2 - 32, self.screenSize[1] / 2 - 10) )
        elif self.mode == 4:
            screen.blit (self.imReady, (self.screenSize[0] / 2 - 20, self.screenSize[1] / 2 + 12) )

        self.DrawNumber (self.levelNum, (0, self.screenSize[1] - 12) )

    def DrawNumber (self, number, x_y):
        (x, y) = x_y
        strNumber = str(int(number))
        for i in range(0, len(strNumber), 1):
            iDigit = int(strNumber[i])
            screen.blit (self.digit[ iDigit ], (x + i * 9, y) )

    def SmartMoveScreen (self):

        possibleScreenX = player.x - self.screenTileSize[1] / 2 * 16
        possibleScreenY = player.y - self.screenTileSize[0] / 2 * 16

        if possibleScreenX < 0:
            possibleScreenX = 0
        elif possibleScreenX > thisLevel.lvlWidth * 16 - self.screenSize[0]:
            possibleScreenX = thisLevel.lvlWidth * 16 - self.screenSize[0]

        if possibleScreenY < 0:
            possibleScreenY = 0
        elif possibleScreenY > thisLevel.lvlHeight * 16 - self.screenSize[1]:
            possibleScreenY = thisLevel.lvlHeight * 16 - self.screenSize[1]

        thisGame.MoveScreen( (possibleScreenX, possibleScreenY) )

    def MoveScreen (self, newx_newy ):
        (newX, newY) = newx_newy
        self.screenPixelPos = (newX, newY)
        self.screenNearestTilePos = (int(newY / 16), int(newX / 16)) # nearest-tile position of the screen from the UL corner
        self.screenPixelOffset = (newX - self.screenNearestTilePos[1]*16, newY - self.screenNearestTilePos[0]*16)

    def GetScreenPos (self):
        return self.screenPixelPos

    def GetLevelNum (self):
        return self.levelNum

    def SetNextLevel (self):
        self.levelNum += 1

        self.SetMode( 4 )
        thisLevel.LoadLevel( thisGame.GetLevelNum() )

        player.velX = 0
        player.velY = 0
        player.anim_pacmanCurrent = player.anim_pacmanR
        player.animFrame = 2


    def SetMode (self, newMode):
        self.mode = newMode
        self.modeTimer = 0
        # print " ***** GAME MODE IS NOW ***** " + str(newMode)

class node ():

    def __init__ (self):
        self.g = -1 # movement cost to move from previous node to this one (usually +10)
        self.h = -1 # estimated movement cost to move from this node to the ending node (remaining horizontal and vertical steps * 10)
        self.f = -1 # total movement cost of this node (= g + h)
        # parent node - used to trace path back to the starting node at the end
        self.parent = (-1, -1)
        # node type - 0 for empty space, 1 for wall (optionally, 2 for starting node and 3 for end)
        self.type = -1

class path_finder ():

    def __init__ (self):
        # map is a 1-DIMENSIONAL array.
        # use the Unfold( (row, col) ) function to convert a 2D coordinate pair
        # into a 1D index to use with this array.
        self.map = {}
        self.size = (-1, -1) # rows by columns

        self.pathChainRev = ""
        self.pathChain = ""

        # starting and ending nodes
        self.start = (-1, -1)
        self.end = (-1, -1)

        # current node (used by algorithm)
        self.current = (-1, -1)

        # open and closed lists of nodes to consider (used by algorithm)
        self.openList = []
        self.closedList = []

        # used in algorithm (adjacent neighbors path finder is allowed to consider)
        self.neighborSet = [ (0, -1), (0, 1), (-1, 0), (1, 0) ]

    def ResizeMap (self, rows_cols):
        (numRows, numCols) = rows_cols
        self.map = {}
        self.size = (numRows, numCols)

        # initialize path_finder map to a 2D array of empty nodes
        for row in range(0, self.size[0], 1):
            for col in range(0, self.size[1], 1):
                self.Set( (row, col), node() )
                self.SetType( (row, col), 0 )

    def CleanUpTemp (self):

        # this resets variables needed for a search (but preserves the same map / maze)

        self.pathChainRev = ""
        self.pathChain = ""
        self.current = (-1, -1)
        self.openList = []
        self.closedList = []

    def FindPath (self, startPos, endPos ):

        self.CleanUpTemp()

        # (row, col) tuples
        self.start = startPos
        self.end = endPos

        # add start node to open list
        self.AddToOpenList( self.start )
        self.SetG ( self.start, 0 )
        self.SetH ( self.start, 0 )
        self.SetF ( self.start, 0 )

        doContinue = True

        while (doContinue == True):

            thisLowestFNode = self.GetLowestFNode()

            if not thisLowestFNode == self.end and not thisLowestFNode == False:
                self.current = thisLowestFNode
                self.RemoveFromOpenList( self.current )
                self.AddToClosedList( self.current )

                for offset in self.neighborSet:
                    thisNeighbor = (self.current[0] + offset[0], self.current[1] + offset[1])

                    if not thisNeighbor[0] < 0 and not thisNeighbor[1] < 0 and not thisNeighbor[0] > self.size[0] - 1 and not thisNeighbor[1] > self.size[1] - 1 and not self.GetType( thisNeighbor ) == 1:
                        cost = self.GetG( self.current ) + 10

                        if self.IsInOpenList( thisNeighbor ) and cost < self.GetG( thisNeighbor ):
                            self.RemoveFromOpenList( thisNeighbor )

                        #if self.IsInClosedList( thisNeighbor ) and cost < self.GetG( thisNeighbor ):
                        #   self.RemoveFromClosedList( thisNeighbor )

                        if not self.IsInOpenList( thisNeighbor ) and not self.IsInClosedList( thisNeighbor ):
                            self.AddToOpenList( thisNeighbor )
                            self.SetG( thisNeighbor, cost )
                            self.CalcH( thisNeighbor )
                            self.CalcF( thisNeighbor )
                            self.SetParent( thisNeighbor, self.current )
            else:
                doContinue = False

        if thisLowestFNode == False:
            return False

        # reconstruct path
        self.current = self.end
        while not self.current == self.start:
            # build a string representation of the path using R, L, D, U
            if self.current[1] > self.GetParent(self.current)[1]:
                self.pathChainRev += 'R'
            elif self.current[1] < self.GetParent(self.current)[1]:
                self.pathChainRev += 'L'
            elif self.current[0] > self.GetParent(self.current)[0]:
                self.pathChainRev += 'D'
            elif self.current[0] < self.GetParent(self.current)[0]:
                self.pathChainRev += 'U'
            self.current = self.GetParent(self.current)
            self.SetType( self.current, 4)

        # because pathChainRev was constructed in reverse order, it needs to be reversed!
        for i in range(len(self.pathChainRev) - 1, -1, -1):
            self.pathChain += self.pathChainRev[i]

        # set start and ending positions for future reference
        self.SetType( self.start, 2)
        self.SetType( self.end, 3)

        return self.pathChain

    def Unfold (self, row_col):
        (row, col) = row_col
        # this function converts a 2D array coordinate pair (row, col)
        # to a 1D-array index, for the object's 1D map array.
        return (row * self.size[1]) + col

    def Set (self, row_col, newNode):
        (row, col) = row_col
        # sets the value of a particular map cell (usually refers to a node object)
        self.map[ self.Unfold((row, col)) ] = newNode

    def GetType (self, row_col):
        (row, col) = row_col
        return self.map[ self.Unfold((row, col)) ].type

    def SetType (self, row_col, newValue):
        (row, col) = row_col
        self.map[ self.Unfold((row, col)) ].type = newValue

    def GetF (self, row_col):
        (row, col) = row_col
        return self.map[ self.Unfold((row, col)) ].f

    def GetG (self, row_col):
        (row, col) = row_col
        return self.map[ self.Unfold((row, col)) ].g

    def GetH (self, row_col):
        (row, col) = row_col
        return self.map[ self.Unfold((row, col)) ].h

    def SetG (self, row_col, newValue ):
        (row, col) = row_col
        self.map[ self.Unfold((row, col)) ].g = newValue

    def SetH (self, row_col, newValue ):
        (row, col) = row_col
        self.map[ self.Unfold((row, col)) ].h = newValue

    def SetF (self, row_col, newValue ):
        (row, col) = row_col
        self.map[ self.Unfold((row, col)) ].f = newValue

    def CalcH (self, row_col):
        (row, col) = row_col
        self.map[ self.Unfold((row, col)) ].h = abs(row - self.end[0]) + abs(col - self.end[0])

    def CalcF (self, row_col):
        (row, col) = row_col
        unfoldIndex = self.Unfold((row, col))
        self.map[unfoldIndex].f = self.map[unfoldIndex].g + self.map[unfoldIndex].h

    def AddToOpenList (self, row_col ):
        (row, col) = row_col
        self.openList.append( (row, col) )

    def RemoveFromOpenList (self, row_col ):
        (row, col) = row_col
        self.openList.remove( (row, col) )

    def IsInOpenList (self, row_col ):
        (row, col) = row_col
        if self.openList.count( (row, col) ) > 0:
            return True
        else:
            return False

    def GetLowestFNode (self):
        lowestValue = 1000 # start arbitrarily high
        lowestPair = (-1, -1)

        for iOrderedPair in self.openList:
            if self.GetF( iOrderedPair ) < lowestValue:
                lowestValue = self.GetF( iOrderedPair )
                lowestPair = iOrderedPair

        if not lowestPair == (-1, -1):
            return lowestPair
        else:
            return False

    def AddToClosedList (self, row_col ):
        (row, col) = row_col
        self.closedList.append( (row, col) )

    def IsInClosedList (self, row_col ):
        (row, col) = row_col
        if self.closedList.count( (row, col) ) > 0:
            return True
        else:
            return False

    def SetParent (self, row_col, prow_pcol ):
        (parentRow, parentCol) = prow_pcol
        (row, col) = row_col
        self.map[ self.Unfold((row, col)) ].parent = (parentRow, parentCol)

    def GetParent (self, row_col ):
        (row, col) = row_col
        return self.map[ self.Unfold((row, col)) ].parent

    def draw (self):
        for row in range(0, self.size[0], 1):
            for col in range(0, self.size[1], 1):

                thisTile = self.GetType((row, col))
                screen.blit (tileIDImage[ thisTile ], (col * 32, row * 32))

class ghost ():
    def __init__ (self, ghostID):
        self.x = 0
        self.y = 0
        self.velX = 0
        self.velY = 0
        self.speed = 0.5

        self.nearestRow = 0
        self.nearestCol = 0

        self.id = ghostID

        # ghost "state" variable
        # 1 = normal
        # 2 = fright
        # 3 = dead
        self.state = GHOSTSTATE_NORMAL

        self.homeX = 0
        self.homeY = 0

        self.currentPath = ""

        self.anim = dict([('left', []), ('right', []), ('up', []), ('down', [])])
        for i in range(1, 3, 1):
            d = 'left'
            self.anim[d].append(self.loadImage(i, d))
            d = 'right'
            self.anim[d].append(self.loadImage(i, d))
            d = 'up'
            self.anim[d].append(self.loadImage(i, d))
            d = 'down'
            self.anim[d].append(self.loadImage(i, d))

        self.animEyes = {}
        self.animEyes['left'] = pygame.image.load(os.path.join(SCRIPT_PATH,"res","sprite","ghost_eyes_left.png")).convert_alpha()
        self.animEyes['right'] = pygame.image.load(os.path.join(SCRIPT_PATH,"res","sprite","ghost_eyes_right.png")).convert_alpha()
        self.animEyes['up'] = pygame.image.load(os.path.join(SCRIPT_PATH,"res","sprite","ghost_eyes_up.png")).convert_alpha()
        self.animEyes['down'] = pygame.image.load(os.path.join(SCRIPT_PATH,"res","sprite","ghost_eyes_down.png")).convert_alpha()

        self.animFrame = 1
        self.animDelay = 0

    def loadImage(self, i, suffix):
        img = pygame.image.load(os.path.join(SCRIPT_PATH,"res","sprite","ghost_" + suffix + "_" + str(i) + ".png")).convert_alpha()

        # change the ghost color in this frame
        for y in range(0, 16, 1):
            for x in range(0, 16, 1):

                if img.get_at( (x, y) ) == (255, 0, 0, 255):
                    # default, red ghost body color
                    img.set_at( (x, y), ghostcolor[ self.id ] )
        return img

    def getDirection(self):
        if self.velX > 0:
            return 'right'
        if self.velX < 0:
            return 'left'
        if self.velY > 0:
            return 'down'
        if self.velY < 0:
            return 'up'
        return 'left'

    def Draw (self):

        if thisGame.mode == 3:
            return False

        if DEBUGDRAW_CELLS:
            cellx = (self.nearestCol * 16) - thisGame.screenPixelPos[0]
            celly = (self.nearestRow * 16) - thisGame.screenPixelPos[1]
            pygame.draw.rect(screen, ghostcolor[self.id], (cellx, celly, 16, 16), 1)

        if self.state == GHOSTSTATE_NORMAL:
            # draw regular ghost (this one)
            img = self.anim[self.getDirection()][ self.animFrame ]
            screen.blit (img, (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1]))
        elif self.state == GHOSTSTATE_FRIGHT:
            # draw vulnerable ghost

            if thisGame.ghostTimer > 100:
                # blue
                img = ghosts[4].anim[self.getDirection()][ self.animFrame ]
                screen.blit (img, (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1]))
            else:
                # blue/white flashing
                tempTimerI = int(thisGame.ghostTimer / 10)
                if tempTimerI == 1 or tempTimerI == 3 or tempTimerI == 5 or tempTimerI == 7 or tempTimerI == 9:
                    img = ghosts[5].anim[self.getDirection()][ self.animFrame ]
                    screen.blit (img, (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1]))
                else:
                    img = ghosts[4].anim[self.getDirection()][ self.animFrame ]
                    screen.blit (img, (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1]))

        elif self.state == GHOSTSTATE_DEAD:
            # draw glasses
            screen.blit (self.animEyes[self.getDirection()], (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1]))

        if thisGame.mode == 6 or thisGame.mode == 7:
            # don't animate ghost if the level is complete
            return False

        self.animDelay += 1

        if self.animDelay == 15:
            self.animFrame = (self.animFrame + 1) % 2

            self.animDelay = 0

    def Move (self):


        self.x += self.velX
        self.y += self.velY

        self.nearestRow = int(((self.y + 8) / 16))
        self.nearestCol = int(((self.x + 8) / 16))

        if (self.x % 16) == 0 and (self.y % 16) == 0:
            # if the ghost is lined up with the grid again
            # meaning, it's time to go to the next path item

            if (self.currentPath):
                self.currentPath = self.currentPath[1:]
                self.FollowNextPathWay()

            else:
                self.x = self.nearestCol * 16
                self.y = self.nearestRow * 16

                # chase pac-man
                self.currentPath = path.FindPath( (self.nearestRow, self.nearestCol), (player.nearestRow, player.nearestCol) )
                self.FollowNextPathWay()

    def FollowNextPathWay (self):

        # print "Ghost " + str(self.id) + " rem: " + self.currentPath

        # only follow this pathway if there is a possible path found!
        if not self.currentPath == False:

            if len(self.currentPath) > 0:
                if self.currentPath[0] == "L":
                    (self.velX, self.velY) = (-self.speed, 0)
                elif self.currentPath[0] == "R":
                    (self.velX, self.velY) = (self.speed, 0)
                elif self.currentPath[0] == "U":
                    (self.velX, self.velY) = (0, -self.speed)
                elif self.currentPath[0] == "D":
                    (self.velX, self.velY) = (0, self.speed)

            else:
                # this ghost has reached his destination!!

                if not self.state == GHOSTSTATE_DEAD:
                    # chase pac-man
                    self.currentPath = path.FindPath( (self.nearestRow, self.nearestCol), (player.nearestRow, player.nearestCol) )
                    self.FollowNextPathWay()

                else:
                    # glasses found way back to ghost box
                    self.state = GHOSTSTATE_NORMAL
                    #self.speed = self.speed / 2

                    # give ghost a path to a random spot (containing a pellet)
                    (randRow, randCol) = (0, 0)

                    while not thisLevel.GetMapTile((randRow, randCol)) == tileID[ 'pellet' ] or (randRow, randCol) == (0, 0):
                        randRow = random.randint(1, thisLevel.lvlHeight - 2)
                        randCol = random.randint(1, thisLevel.lvlWidth - 2)

                    self.currentPath = path.FindPath( (self.nearestRow, self.nearestCol), (randRow, randCol) )
                    self.FollowNextPathWay()

class fruit ():
    def __init__ (self):
        # when fruit is not in use, it's in the (-1, -1) position off-screen.
        self.slowTimer = 0
        self.x = -16
        self.y = -16
        self.velX = 0
        self.velY = 0
        self.speed = 1
        self.active = False

        self.bouncei = 0
        self.bounceY = 0

        self.nearestRow = (-1, -1)
        self.nearestCol = (-1, -1)

        self.imFruit = {}
        for i in range(0, 5, 1):
            self.imFruit[i] = pygame.image.load(os.path.join(SCRIPT_PATH,"res","sprite","fruit " + str(i) + ".gif")).convert()

        self.currentPath = ""
        self.fruitType = 1

    def Draw (self):

        if thisGame.mode == 3 or self.active == False:
            return False

        screen.blit (self.imFruit[ self.fruitType ], (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1] - self.bounceY))


    def Move (self):

        if self.active == False:
            return False

        self.bouncei += 1
        if self.bouncei == 1:
            self.bounceY = 2
        elif self.bouncei == 2:
            self.bounceY = 4
        elif self.bouncei == 3:
            self.bounceY = 5
        elif self.bouncei == 4:
            self.bounceY = 5
        elif self.bouncei == 5:
            self.bounceY = 6
        elif self.bouncei == 6:
            self.bounceY = 6
        elif self.bouncei == 9:
            self.bounceY = 6
        elif self.bouncei == 10:
            self.bounceY = 5
        elif self.bouncei == 11:
            self.bounceY = 5
        elif self.bouncei == 12:
            self.bounceY = 4
        elif self.bouncei == 13:
            self.bounceY = 3
        elif self.bouncei == 14:
            self.bounceY = 2
        elif self.bouncei == 15:
            self.bounceY = 1
        elif self.bouncei == 16:
            self.bounceY = 0
            self.bouncei = 0
            snd_fruitbounce.play()

        self.slowTimer += 1
        if self.slowTimer == 2:
            self.slowTimer = 0

            self.x += self.velX
            self.y += self.velY

            self.nearestRow = int(((self.y + 8) / 16))
            self.nearestCol = int(((self.x + 8) / 16))

            if (self.x % 16) == 0 and (self.y % 16) == 0:
                # if the fruit is lined up with the grid again
                # meaning, it's time to go to the next path item

                if len(self.currentPath) > 0:
                    self.currentPath = self.currentPath[1:]
                    self.FollowNextPathWay()

                else:
                    self.x = self.nearestCol * 16
                    self.y = self.nearestRow * 16

                    self.active = False
                    thisGame.fruitTimer = 0

    def FollowNextPathWay (self):


        # only follow this pathway if there is a possible path found!
        if not self.currentPath == False:

            if len(self.currentPath) > 0:
                if self.currentPath[0] == "L":
                    (self.velX, self.velY) = (-self.speed, 0)
                elif self.currentPath[0] == "R":
                    (self.velX, self.velY) = (self.speed, 0)
                elif self.currentPath[0] == "U":
                    (self.velX, self.velY) = (0, -self.speed)
                elif self.currentPath[0] == "D":
                    (self.velX, self.velY) = (0, self.speed)

def getCell(v, spacing = 8):
    return int((v + spacing) / 16)

def sign(v):
    return 1 if v > 0 else (-1 if v < 0 else 0)

class pacman ():

    def __init__ (self):
        self.x = 0
        self.y = 0
        self.velX = 0
        self.velY = 0
        self.speed = 1

        self.nearestRow = 0
        self.nearestCol = 0
        self.nextRow = 0
        self.nextCol = 0

        self.homeX = 0
        self.homeY = 0

        self.anim_pacmanL = {}
        self.anim_pacmanR = {}
        self.anim_pacmanU = {}
        self.anim_pacmanD = {}
        self.anim_pacmanCurrent = {}
        self.animFrame = 1
        self.animDelay = 0

        for i in range(1, 4, 1):
            self.anim_pacmanL[i-1] = pygame.image.load(os.path.join(SCRIPT_PATH,"res","sprite","pacman_left_" + str(i) + ".png")).convert_alpha()
            self.anim_pacmanR[i-1] = pygame.image.load(os.path.join(SCRIPT_PATH,"res","sprite","pacman_right_" + str(i) + ".png")).convert_alpha()
            self.anim_pacmanU[i-1] = pygame.image.load(os.path.join(SCRIPT_PATH,"res","sprite","pacman_up_" + str(i) + ".png")).convert_alpha()
            self.anim_pacmanD[i-1] = pygame.image.load(os.path.join(SCRIPT_PATH,"res","sprite","pacman_down_" + str(i) + ".png")).convert_alpha()

        self.pelletSndNum = 0

    def Move (self):

        self.nearestRow = getCell(self.y)
        self.nearestCol = getCell(self.x)

        # make sure the current velocity will not cause a collision before moving
        nextRow = getCell(self.y + (sign(self.velY ) * 16))
        nextCol = getCell(self.x + (sign(self.velX ) * 16))

        moved = False
        if not thisLevel.IsWall((self.nearestRow, nextCol)):
            self.x += self.velX
            self.nextCol = nextCol
            moved = True
        else:
            self.velX = 0
            self.x = self.nearestCol * 16

        if not thisLevel.IsWall((nextRow, self.nearestCol)):
            self.y += self.velY
            self.nextRow = nextRow
            moved = True
        else:
            self.velY = 0
            self.y = self.nearestRow * 16

        if moved:
            # check for collisions with other tiles (pellets, etc)
            thisLevel.CheckIfHitSomething((self.x, self.y), (self.nearestRow, self.nearestCol))

            # check for collisions with the ghosts
            for i in range(0, 4, 1):
                #if thisLevel.CheckIfHit( (self.x, self.y), (ghosts[i].x, ghosts[i].y), 8):
                if thisLevel.CheckIfInSameCell((self.nearestCol, self.nearestRow), (ghosts[i].nearestCol, ghosts[i].nearestRow)):
                    # hit a ghost

                    if ghosts[i].state == GHOSTSTATE_NORMAL:
                        # ghost is normal
                        thisGame.SetMode( 2 )

                    elif ghosts[i].state == GHOSTSTATE_FRIGHT:
                        # ghost is vulnerable
                        # give them glasses
                        # make them run
                        thisGame.AddToScore(thisGame.ghostValue)
                        thisGame.ghostValue = thisGame.ghostValue * 2
                        snd_eatgh.play()

                        ghosts[i].state = GHOSTSTATE_DEAD
                        #ghosts[i].speed = ghosts[i].speed * 2
                        # and send them to the ghost box
                        ghosts[i].x = ghosts[i].nearestCol * 16
                        ghosts[i].y = ghosts[i].nearestRow * 16
                        ghosts[i].currentPath = path.FindPath( (ghosts[i].nearestRow, ghosts[i].nearestCol), (thisLevel.GetGhostBoxPos()[0]+1, thisLevel.GetGhostBoxPos()[1]) )
                        ghosts[i].FollowNextPathWay()

                        # set game mode to brief pause after eating
                        thisGame.SetMode( 5 )

            # check for collisions with the fruit
            if thisFruit.active == True:
                if thisLevel.CheckIfHit( (self.x, self.y), (thisFruit.x, thisFruit.y), 8):
                    thisGame.AddToScore(2500)
                    thisFruit.active = False
                    thisGame.fruitTimer = 0
                    thisGame.fruitScoreTimer = 120
                    snd_eatfruit.play()

        # deal with power-pellet ghost timer
        if thisGame.ghostTimer > 0:
            thisGame.ghostTimer -= 1

            if thisGame.ghostTimer == 0:
                for i in range(0, 4, 1):
                    if ghosts[i].state == GHOSTSTATE_FRIGHT:
                        ghosts[i].state = GHOSTSTATE_NORMAL
                self.ghostValue = 0

        # deal with fruit timer
        thisGame.fruitTimer += 1
        if thisGame.fruitTimer == 500:
            pathwayPair = thisLevel.GetPathwayPairPos()

            if not pathwayPair == False:

                pathwayEntrance = pathwayPair[0]
                pathwayExit = pathwayPair[1]

                thisFruit.active = True

                thisFruit.nearestRow = pathwayEntrance[0]
                thisFruit.nearestCol = pathwayEntrance[1]

                thisFruit.x = thisFruit.nearestCol * 16
                thisFruit.y = thisFruit.nearestRow * 16

                thisFruit.currentPath = path.FindPath( (thisFruit.nearestRow, thisFruit.nearestCol), pathwayExit )
                thisFruit.FollowNextPathWay()

        if thisGame.fruitScoreTimer > 0:
            thisGame.fruitScoreTimer -= 1


    def Draw (self):

        if thisGame.mode == 3:
            return False

        screenx = self.x - thisGame.screenPixelPos[0]
        screeny = self.y - thisGame.screenPixelPos[1]

        if DEBUGDRAW_CELLS:
            cellx = (self.nearestCol * 16) - thisGame.screenPixelPos[0]
            celly = (self.nearestRow * 16) - thisGame.screenPixelPos[1]
            pygame.draw.rect(screen, (255, 255, 0, 65), (cellx, celly, 16, 16), 1)
            cellx = (self.nextCol * 16) - thisGame.screenPixelPos[0]
            celly = (self.nextRow * 16) - thisGame.screenPixelPos[1]
            pygame.draw.rect(screen, (255, 255, 128, 65), (cellx, celly, 16, 16), 1)


        # set the current frame array to match the direction pacman is facing
        if self.velX > 0:
            self.anim_pacmanCurrent = self.anim_pacmanR
        elif self.velX < 0:
            self.anim_pacmanCurrent = self.anim_pacmanL
        elif self.velY > 0:
            self.anim_pacmanCurrent = self.anim_pacmanD
        elif self.velY < 0:
            self.anim_pacmanCurrent = self.anim_pacmanU

        screen.blit (self.anim_pacmanCurrent[ self.animFrame ], (screenx, screeny))

        if thisGame.mode == 1:
            if not self.velX == 0 or not self.velY == 0:
                # only Move mouth when pacman is moving
                self.animDelay += 1

                if self.animDelay == 5:
                    self.animFrame = (self.animFrame + 1) % 3
                    self.animDelay = 0

class level ():

    def __init__ (self):
        self.lvlWidth = 0
        self.lvlHeight = 0
        self.edgeLightColor = (255, 255, 0, 255)
        self.edgeShadowColor = (255, 150, 0, 255)
        self.fillColor = (0, 255, 255, 255)
        self.pelletColor = (255, 255, 255, 255)

        self.map = {}

        self.pellets = 0
        self.powerPelletBlinkTimer = 0

    def SetMapTile (self, row_col, newValue):
        (row, col) = row_col
        self.map[ (row * self.lvlWidth) + col ] = newValue

    def GetMapTile (self, row_col):
        (row, col) = row_col
        if row >= 0 and row < self.lvlHeight and col >= 0 and col < self.lvlWidth:
            return self.map[ (row * self.lvlWidth) + col ]
        else:
            return 0

    def IsWall (self, row_col):
        (row, col) = row_col

        if row > thisLevel.lvlHeight - 1 or row < 0:
            return True

        if col > thisLevel.lvlWidth - 1 or col < 0:
            return True

        # check the offending tile ID
        result = thisLevel.GetMapTile((row, col))

        # if the tile was a wall
        if result >= 100 and result <= 199:
            return True
        else:
            return False


    def CheckIfHitWall (self, px_py, row_col):
        (possiblePlayerX, possiblePlayerY) = px_py
        (row, col) = row_col

        numCollisions = 0

        # check each of the 9 surrounding tiles for a collision
        for iRow in range(row - 1, row + 2, 1):
            for iCol in range(col - 1, col + 2, 1):

                if  (possiblePlayerX - (iCol * 16) < 16) and (possiblePlayerX - (iCol * 16) > -16) and (possiblePlayerY - (iRow * 16) < 16) and (possiblePlayerY - (iRow * 16) > -16):

                    if self.IsWall((iRow, iCol)):
                        numCollisions += 1

        if numCollisions > 0:
            return True
        else:
            return False


    def CheckIfInSameCell(self, ar_ac, br_bc):
        (alpha_row, alpha_col) = ar_ac
        (beta_row, beta_col) = br_bc
        if alpha_row == beta_row and alpha_col == beta_col:
            return True
        return False

    def CheckIfHit (self, px_py, x_y, cushion):
        (x, y) = x_y
        (playerX, playerY) = px_py

        if (playerX - x < cushion) and (playerX - x > -cushion) and (playerY - y < cushion) and (playerY - y > -cushion):
            return True
        else:
            return False


    def CheckIfHitSomething (self, px_py, row_col):
        (row, col) = row_col
        (playerX, playerY) = px_py

        result = self.GetMapTile((row, col))
        if result == tileID['pellet']:
            self.SetMapTile((row, col),0)
            snd_pellet[player.pelletSndNum].play()
            player.pelletSndNum = 1 - player.pelletSndNum
            self.pellets -= 1
            thisGame.AddToScore(10)
            if self.pellets == 0:
                thisGame.SetMode(6)

        elif result == tileID[ 'pellet-power' ]:
            # got a power pellet
            thisLevel.SetMapTile((row, col), 0)
            snd_powerpellet.play()

            thisGame.AddToScore(100)
            thisGame.ghostValue = 200

            thisGame.ghostTimer = 360
            for i in range(0, 4, 1):
                if ghosts[i].state == 1:
                    ghosts[i].state = 2

        elif result == tileID[ 'door-h' ]:
            # ran into a horizontal door
            for i in range(0, thisLevel.lvlWidth, 1):
                if not i == col:
                    if thisLevel.GetMapTile((row, i)) == tileID[ 'door-h' ]:
                        player.x = i * 16

                        if player.velX > 0:
                            player.x += 16
                        else:
                            player.x -= 16

        elif result == tileID[ 'door-v' ]:
            # ran into a vertical door
            for i in range(0, thisLevel.lvlHeight, 1):
                if not i == row:
                    if thisLevel.GetMapTile((i, col)) == tileID[ 'door-v' ]:
                        player.y = i * 16

                        if player.velY > 0:
                            player.y += 16
                        else:
                            player.y -= 16
        return

    def GetGhostBoxPos (self):
        for row in range(0, self.lvlHeight, 1):
            for col in range(0, self.lvlWidth, 1):
                if self.GetMapTile((row, col)) == tileID[ 'ghost-door' ]:
                    return (row, col)

        return False

    def GetPathwayPairPos (self):

        doorArray = []

        for row in range(0, self.lvlHeight, 1):
            for col in range(0, self.lvlWidth, 1):
                if self.GetMapTile((row, col)) == tileID[ 'door-h' ]:
                    # found a horizontal door
                    doorArray.append( (row, col) )
                elif self.GetMapTile((row, col)) == tileID[ 'door-v' ]:
                    # found a vertical door
                    doorArray.append( (row, col) )

        if len(doorArray) == 0:
            return False

        chosenDoor = random.randint(0, len(doorArray) - 1)

        if self.GetMapTile( doorArray[chosenDoor] ) == tileID[ 'door-h' ]:
            # horizontal door was chosen
            # look for the opposite one
            for i in range(0, thisLevel.lvlWidth, 1):
                if not i == doorArray[chosenDoor][1]:
                    if thisLevel.GetMapTile((doorArray[chosenDoor][0], i)) == tileID[ 'door-h' ]:
                        return doorArray[chosenDoor], (doorArray[chosenDoor][0], i)
        else:
            # vertical door was chosen
            # look for the opposite one
            for i in range(0, thisLevel.lvlHeight, 1):
                if not i == doorArray[chosenDoor][0]:
                    if thisLevel.GetMapTile((i, doorArray[chosenDoor][1])) == tileID[ 'door-v' ]:
                        return doorArray[chosenDoor], (i, doorArray[chosenDoor][1])

        return False

    def PrintMap (self):

        for row in range(0, self.lvlHeight, 1):
            outputLine = ""
            for col in range(0, self.lvlWidth, 1):

                outputLine += str( self.GetMapTile((row, col)) ) + ", "

                # print outputLine

    def DrawMap (self):

        self.powerPelletBlinkTimer += 1
        if self.powerPelletBlinkTimer == 60:
            self.powerPelletBlinkTimer = 0

        for row in range(-1, thisGame.screenTileSize[0] +1, 1):
            outputLine = ""
            for col in range(-1, thisGame.screenTileSize[1] +1, 1):

                # row containing tile that actually goes here
                actualRow = thisGame.screenNearestTilePos[0] + row
                actualCol = thisGame.screenNearestTilePos[1] + col

                useTile = self.GetMapTile((actualRow, actualCol))
                if not useTile == 0 and not useTile == tileID['door-h'] and not useTile == tileID['door-v']:
                    # if this isn't a blank tile

                    if useTile == tileID['pellet-power']:
                        if self.powerPelletBlinkTimer < 30:
                            screen.blit (tileIDImage[ useTile ], (col * 16 - thisGame.screenPixelOffset[0], row * 16 - thisGame.screenPixelOffset[1]) )

                    elif useTile == tileID['showlogo']:
                        screen.blit (thisGame.imLogo, (col * 16 - thisGame.screenPixelOffset[0], row * 16 - thisGame.screenPixelOffset[1]) )

                    elif useTile == tileID['hiscores']:
                        screen.blit(thisGame.imHiscores,(col*16-thisGame.screenPixelOffset[0],row*16-thisGame.screenPixelOffset[1]))

                    else:
                        screen.blit (tileIDImage[ useTile ], (col * 16 - thisGame.screenPixelOffset[0], row * 16 - thisGame.screenPixelOffset[1]) )

    def LoadLevel (self, levelNum):

        self.map = {}

        self.pellets = 0

        f = open(os.path.join(SCRIPT_PATH,"res","levels",str(levelNum) + ".txt"), 'r')
        # ANDY -- edit this
        #fileOutput = f.read()
        #str_splitByLine = fileOutput.split('\n')
        lineNum=-1
        rowNum = 0
        useLine = False
        isReadingLevelData = False

        for line in f:

            lineNum += 1

            # print " ------- Level Line " + str(lineNum) + " -------- "
            while len(line)>0 and (line[-1]=="\n" or line[-1]=="\r"): line=line[:-1]
            while len(line)>0 and (line[0]=="\n" or line[0]=="\r"): line=line[1:]
            str_splitBySpace = line.split(' ')


            j = str_splitBySpace[0]

            if (j == "'" or j == ""):
                # comment / whitespace line
                # print " ignoring comment line.. "
                useLine = False
            elif j == "#":
                # special divider / attribute line
                useLine = False

                firstWord = str_splitBySpace[1]

                if firstWord == "lvlwidth":
                    self.lvlWidth = int( str_splitBySpace[2] )
                    # print "Width is " + str( self.lvlWidth )

                elif firstWord == "lvlheight":
                    self.lvlHeight = int( str_splitBySpace[2] )
                    # print "Height is " + str( self.lvlHeight )

                elif firstWord == "edgecolor":
                    # edge color keyword for backwards compatibility (single edge color) mazes
                    red = int( str_splitBySpace[2] )
                    green = int( str_splitBySpace[3] )
                    blue = int( str_splitBySpace[4] )
                    self.edgeLightColor = (red, green, blue, 255)
                    self.edgeShadowColor = (red, green, blue, 255)

                elif firstWord == "edgelightcolor":
                    red = int( str_splitBySpace[2] )
                    green = int( str_splitBySpace[3] )
                    blue = int( str_splitBySpace[4] )
                    self.edgeLightColor = (red, green, blue, 255)

                elif firstWord == "edgeshadowcolor":
                    red = int( str_splitBySpace[2] )
                    green = int( str_splitBySpace[3] )
                    blue = int( str_splitBySpace[4] )
                    self.edgeShadowColor = (red, green, blue, 255)

                elif firstWord == "fillcolor":
                    red = int( str_splitBySpace[2] )
                    green = int( str_splitBySpace[3] )
                    blue = int( str_splitBySpace[4] )
                    self.fillColor = (red, green, blue, 255)

                elif firstWord == "pelletcolor":
                    red = int( str_splitBySpace[2] )
                    green = int( str_splitBySpace[3] )
                    blue = int( str_splitBySpace[4] )
                    self.pelletColor = (red, green, blue, 255)

                elif firstWord == "fruittype":
                    thisFruit.fruitType = int( str_splitBySpace[2] )

                elif firstWord == "startleveldata":
                    isReadingLevelData = True
                    # print "Level data has begun"
                    rowNum = 0

                elif firstWord == "endleveldata":
                    isReadingLevelData = False
                    # print "Level data has ended"

            else:
                useLine = True


                # this is a map data line
            if useLine == True:

                if isReadingLevelData == True:

                    # print str( len(str_splitBySpace) ) + " tiles in this column"

                    for k in range(0, self.lvlWidth, 1):
                        self.SetMapTile((rowNum, k), int(str_splitBySpace[k]) )

                        thisID = int(str_splitBySpace[k])
                        if thisID == 4:
                            # starting position for pac-man

                            player.homeX = k * 16
                            player.homeY = rowNum * 16
                            self.SetMapTile((rowNum, k), 0 )

                        elif thisID >= 10 and thisID <= 13:
                            # one of the ghosts

                            ghosts[thisID - 10].homeX = k * 16
                            ghosts[thisID - 10].homeY = rowNum * 16
                            self.SetMapTile((rowNum, k), 0 )

                        elif thisID == 2:
                            # pellet

                            self.pellets += 1

                    rowNum += 1


        # reload all tiles and set appropriate colors
        GetCrossRef()

        # load map into the pathfinder object
        path.ResizeMap( (self.lvlHeight, self.lvlWidth) )

        for row in range(0, path.size[0], 1):
            for col in range(0, path.size[1], 1):
                if self.IsWall( (row, col) ):
                    path.SetType( (row, col), 1 )
                else:
                    path.SetType( (row, col), 0 )

        # do all the level-starting stuff
        self.Restart()

    def Restart (self):

        for i in range(0, 4, 1):
            # move ghosts back to home

            ghosts[i].x = ghosts[i].homeX
            ghosts[i].y = ghosts[i].homeY
            ghosts[i].velX = 0
            ghosts[i].velY = 0
            ghosts[i].state = 1
            ghosts[i].speed = 1
            ghosts[i].Move()

            # give each ghost a path to a random spot (containing a pellet)
            (randRow, randCol) = (0, 0)

            while not self.GetMapTile((randRow, randCol)) == tileID[ 'pellet' ] or (randRow, randCol) == (0, 0):
                randRow = random.randint(1, self.lvlHeight - 2)
                randCol = random.randint(1, self.lvlWidth - 2)

            # print "Ghost " + str(i) + " headed towards " + str((randRow, randCol))
            ghosts[i].currentPath = path.FindPath( (ghosts[i].nearestRow, ghosts[i].nearestCol), (randRow, randCol) )
            ghosts[i].FollowNextPathWay()

        thisFruit.active = False

        thisGame.fruitTimer = 0

        player.x = player.homeX
        player.y = player.homeY
        player.velX = 0
        player.velY = 0

        player.anim_pacmanCurrent = player.anim_pacmanR
        player.animFrame = 2


def CheckIfCloseButton(events):
    for event in events:
        if event.type == QUIT:
            sys.exit(0)


def CheckInputs():
    row = getCell(player.y, 12)
    col = getCell(player.x, 12)

    if thisGame.mode == 1:
        if pygame.key.get_pressed()[ pygame.K_RIGHT ] or (js!=None and js.get_axis(JS_XAXIS)>0):
            #if not thisLevel.CheckIfHitWall((player.x + player.speed, player.y), (player.nearestRow, player.nearestCol)):
            if not thisLevel.IsWall((row, col + 1)):
                player.velX = player.speed

        elif pygame.key.get_pressed()[ pygame.K_LEFT ] or (js!=None and js.get_axis(JS_XAXIS)<0):
            #if not thisLevel.CheckIfHitWall((player.x - player.speed, player.y), (player.nearestRow, player.nearestCol)):
            if not thisLevel.IsWall((player.nearestRow, player.nearestCol - 1)):
                player.velX = -player.speed
                #player.velY = 0

        elif pygame.key.get_pressed()[ pygame.K_DOWN ] or (js!=None and js.get_axis(JS_YAXIS)>0):
            #if not thisLevel.CheckIfHitWall((player.x, player.y + player.speed), (player.nearestRow, player.nearestCol)):
            if not thisLevel.IsWall((player.nearestRow + 1, player.nearestCol)):
                #player.velX = 0
                player.velY = player.speed

        elif pygame.key.get_pressed()[ pygame.K_UP ] or (js!=None and js.get_axis(JS_YAXIS)<0):
            #if not thisLevel.CheckIfHitWall((player.x, player.y - player.speed), (player.nearestRow, player.nearestCol)):
            if not thisLevel.IsWall((player.nearestRow - 1, player.nearestCol)):
                #player.velX = 0
                player.velY = -player.speed

    if pygame.key.get_pressed()[ pygame.K_ESCAPE ]:
        sys.exit(0)

    elif thisGame.mode == 3:
        if pygame.key.get_pressed()[ pygame.K_RETURN ] or (js!=None and js.get_button(JS_STARTBUTTON)):
            thisGame.StartNewGame()



#      _____________________________________________
# ___/  function: Get ID-Tilename Cross References  \______________________________________

def GetCrossRef ():

    f = open(os.path.join(SCRIPT_PATH,"res","crossref.txt"), 'r')
    # ANDY -- edit
    #fileOutput = f.read()
    #str_splitByLine = fileOutput.split('\n')

    lineNum = 0
    useLine = False

    for i in f.readlines():
        # print " ========= Line " + str(lineNum) + " ============ "
        while len(i)>0 and (i[-1]=='\n' or i[-1]=='\r'): i=i[:-1]
        while len(i)>0 and (i[0]=='\n' or i[0]=='\r'): i=i[1:]
        str_splitBySpace = i.split(' ')

        j = str_splitBySpace[0]

        if (j == "'" or j == "" or j == "#"):
            # comment / whitespace line
            # print " ignoring comment line.. "
            useLine = False
        else:
            # print str(wordNum) + ". " + j
            useLine = True

        if useLine == True:
            tileIDName[ int(str_splitBySpace[0]) ] = str_splitBySpace[1]
            tileID[ str_splitBySpace[1] ] = int(str_splitBySpace[0])

            thisID = int(str_splitBySpace[0])
            if not thisID in NO_GIF_TILES:
                tileIDImage[ thisID ] = pygame.image.load(os.path.join(SCRIPT_PATH,"res","tiles",str_splitBySpace[1] + ".gif")).convert()
            else:
                tileIDImage[ thisID ] = pygame.Surface((16,16))

            # change colors in tileIDImage to match maze colors
            for y in range(0, 16, 1):
                for x in range(0, 16, 1):

                    if tileIDImage[ thisID ].get_at( (x, y) ) == (255, 206, 255, 255):
                        # wall edge
                        tileIDImage[ thisID ].set_at( (x, y), thisLevel.edgeLightColor )

                    elif tileIDImage[ thisID ].get_at( (x, y) ) == (132, 0, 132, 255):
                        # wall fill
                        tileIDImage[ thisID ].set_at( (x, y), thisLevel.fillColor )

                    elif tileIDImage[ thisID ].get_at( (x, y) ) == (255, 0, 255, 255):
                        # pellet color
                        tileIDImage[ thisID ].set_at( (x, y), thisLevel.edgeShadowColor )

                    elif tileIDImage[ thisID ].get_at( (x, y) ) == (128, 0, 128, 255):
                        # pellet color
                        tileIDImage[ thisID ].set_at( (x, y), thisLevel.pelletColor )

                        # print str_splitBySpace[0] + " is married to " + str_splitBySpace[1]
        lineNum += 1


#      __________________
# ___/  main code block  \_____________________________________________________

# create the pacman
player = pacman()

# create a path_finder object
path = path_finder()

# create ghost objects
ghosts = {}
for i in range(0, 6, 1):
    # remember, ghost[4] is the blue, vulnerable ghost
    ghosts[i] = ghost(i)

# create piece of fruit
thisFruit = fruit()

tileIDName = {} # gives tile name (when the ID# is known)
tileID = {} # gives tile ID (when the name is known)
tileIDImage = {} # gives tile image (when the ID# is known)

# create game and level objects and load first level
thisGame = game()
thisLevel = level()
thisLevel.LoadLevel( thisGame.GetLevelNum() )

print( thisGame.screenSize )
windowSize = (thisGame.screenSize[0] * 2, thisGame.screenSize[1] * 2)
window = pygame.display.set_mode( windowSize, pygame.DOUBLEBUF | pygame.HWSURFACE )
screen = pygame.Surface(thisGame.screenSize)

# initialise the joystick
if pygame.joystick.get_count()>0:
    if JS_DEVNUM<pygame.joystick.get_count(): js=pygame.joystick.Joystick(JS_DEVNUM)
    else: js=pygame.joystick.Joystick(0)
    js.init()
else: js=None

while True:

    CheckIfCloseButton( pygame.event.get() )

    if thisGame.mode == 1:
        # normal gameplay mode
        CheckInputs()

        thisGame.modeTimer += 1
        player.Move()
        #for i in range(0, 4, 1):
        #    ghosts[i].Move()
        #thisFruit.Move()

    elif thisGame.mode == 2:
        # waiting after getting hit by a ghost
        thisGame.modeTimer += 1

        if thisGame.modeTimer == 90:
            thisLevel.Restart()

            thisGame.lives -= 1
            if thisGame.lives == -1:
                thisGame.updatehiscores(thisGame.score)
                thisGame.SetMode( 3 )
                thisGame.drawmidgamehiscores()
            else:
                thisGame.SetMode( 4 )

    elif thisGame.mode == 3:
        # game over
        CheckInputs()

    elif thisGame.mode == 4:
        # waiting to start
        thisGame.modeTimer += 1

        if thisGame.modeTimer == 90:
            thisGame.SetMode( 1 )
            player.velX = player.speed

    elif thisGame.mode == 5:
        # brief pause after munching a vulnerable ghost
        thisGame.modeTimer += 1

        if thisGame.modeTimer == 30:
            thisGame.SetMode( 1 )

    elif thisGame.mode == 6:
        # pause after eating all the pellets
        thisGame.modeTimer += 1

        if thisGame.modeTimer == 60:
            thisGame.SetMode( 7 )
            oldEdgeLightColor = thisLevel.edgeLightColor
            oldEdgeShadowColor = thisLevel.edgeShadowColor
            oldFillColor = thisLevel.fillColor

    elif thisGame.mode == 7:
        # flashing maze after finishing level
        thisGame.modeTimer += 1

        whiteSet = [10, 30, 50, 70]
        normalSet = [20, 40, 60, 80]

        if not whiteSet.count(thisGame.modeTimer) == 0:
            # member of white set
            thisLevel.edgeLightColor = (255, 255, 255, 255)
            thisLevel.edgeShadowColor = (255, 255, 255, 255)
            thisLevel.fillColor = (0, 0, 0, 255)
            GetCrossRef()
        elif not normalSet.count(thisGame.modeTimer) == 0:
            # member of normal set
            thisLevel.edgeLightColor = oldEdgeLightColor
            thisLevel.edgeShadowColor = oldEdgeShadowColor
            thisLevel.fillColor = oldFillColor
            GetCrossRef()
        elif thisGame.modeTimer == 150:
            thisGame.SetMode ( 8 )

    elif thisGame.mode == 8:
        # blank screen before changing levels
        thisGame.modeTimer += 1
        if thisGame.modeTimer == 10:
            thisGame.SetNextLevel()

    thisGame.SmartMoveScreen()

    screen.blit(img_Background, (0, 0))

    if not thisGame.mode == 8:
        thisLevel.DrawMap()

        if thisGame.fruitScoreTimer > 0:
            if thisGame.modeTimer % 2 == 0:
                thisGame.DrawNumber (2500, (thisFruit.x - thisGame.screenPixelPos[0] - 16, thisFruit.y - thisGame.screenPixelPos[1] + 4))

        for i in range(0, 4, 1):
            ghosts[i].Draw()
        thisFruit.Draw()
        player.Draw()

        #if thisGame.mode == 3:
        #    screen.blit(thisGame.imHiscores,(32,256))

    if thisGame.mode == 5:
        thisGame.DrawNumber (thisGame.ghostValue / 2, (player.x - thisGame.screenPixelPos[0] - 4, player.y - thisGame.screenPixelPos[1] + 6))



    thisGame.DrawScore()
    pygame.transform.scale(screen, windowSize, window)
    pygame.display.flip()

    clock.tick (FRAME_TIME)