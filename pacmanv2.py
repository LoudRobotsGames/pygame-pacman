import pygame, sys, os, random
from pygame.locals import *

# Path to the location of the game. Used for loading assets
SCRIPT_PATH=sys.path[0]

# Constants
FRAME_TIME = 15
SPRITE_SIZE = 16
TILE_SIZE = 8
HALF_TILE_SIZE = 4
SCREEN_MULTIPLIER = 3

# Utility flags
DEBUGDRAW = 0

# Used to mark which tiles do not have art assets # TODO - add this to the crossref api
NO_GIF_TILES = [20, 21, 23]

# Containers to hold the level assets
tileIDName = {} # gives tile name (when the ID# is known)
tileID = {} # gives tile ID (when the name is known)
tileIDImage = {} # gives tile image (when the ID# is known)

# Initializing the sound mixer. Must come before pygame.init()
pygame.mixer.pre_init(22050,16,2,512)
pygame.mixer.init()

# Setting the realtime clock used to control frame rate
clock = pygame.time.Clock()
pygame.init()

window = pygame.display.set_mode((1, 1))
pygame.display.set_caption("Pacman")

# Set up some common colors as constants
RED    = (255,   0,   0)
GREEN  = (  0, 255,   0)
BLUE   = (  0,   0, 255)
PINK   = (255, 181, 255)
ORANGE = (248, 187,  85)
CYAN   = (  0, 255, 255)
YELLOW = (255, 255,   0)
WHITE  = (255, 255, 255)
GRID   = (255, 255, 255, 32)
LEGAL  = (255, 255, 255, 64)
TUNNEL = (255,  64,  64, 64)
TRANSPARENT_BLACK = (0, 0, 0, 0)

# Constants for ghost states
GHOSTSTATE_NORMAL = 1
GHOSTSTATE_FRIGHT = 2
GHOSTSTATE_DEAD   = 3

# Collision constants
COLLISION_NOTHING = 0
COLLISION_GHOST = 1
COLLISION_PELLET = 2
COLLISION_POWER_PELLET = 3
COLLISION_FRUIT = 4

# Tile Map constants. Not my favourite way. Todo - look into fixing this to be as dynamic as the crossref allows
TILE_MAP_PELLET = 2
TILE_MAP_POWER_PELLET = 3
TILE_MAP_PACMAN_START = 4
TILE_MAP_FRUIT_START = 5

# Tile flags. These are stored in a single integer as a bit-mask
TILE_FLAG_LEGAL = 1
TILE_FLAG_TUNNEL = 2
TILE_FLAG_GHOST_PEN = 4

# Fruit type constants
FRUIT = "fruit"
CHERRY = "cherry"
BERRY = "berry"

BONUS_POINTS_CHERRY = 100

# Direction constants
DIR_LEFT    = "left"
DIR_RIGHT   = "right"
DIR_UP      = "up"
DIR_DOWN    = "down"

# Utility functions
def getCell(v, spacing = 4):
    return int((v + spacing) / TILE_SIZE)

def sign(v):
    return 1 if v > 0 else (-1 if v < 0 else 0)

def cell(value):
    return value * TILE_SIZE

class bonus():

    offset = 2

    def __init__(self):
        self.row = 20
        self.col = 13
        self.bonusType = FRUIT
        self.points = 0
        self.SetType(CHERRY, BONUS_POINTS_CHERRY)
        self.active = True
        self.left = cell(self.col) + self.offset
        self.right = cell(self.col + 1)
        self.top = cell(self.row)
        self.bottom = cell(self.row + 1)

    def SetActive(self, value):
        self.active = value

    def SetType(self, type, points):
        self.type = type
        self.points = points
        self.image = pygame.image.load(os.path.join(SCRIPT_PATH,"res","sprite",self.bonusType+"_"+self.type+".png")).convert_alpha()

    def ScreenPos(self):
        return self.col * TILE_SIZE, self.row * TILE_SIZE - HALF_TILE_SIZE

    def DoesCollide(self, xPos, yPos):
        if xPos < self.left:
            return False
        if xPos > self.right:
            return False
        if yPos < self.top:
            return False
        if yPos > self.bottom:
            return False
        return True

    def GetRow(self):
        return self.row

    def Draw(self):
        if self.active:
            screen.blit(self.image, self.ScreenPos())
        if DEBUGDRAW:
            debugrect = (self.left * SCREEN_MULTIPLIER, self.top * SCREEN_MULTIPLIER, (TILE_SIZE - self.offset) * SCREEN_MULTIPLIER, TILE_SIZE * SCREEN_MULTIPLIER)
            pygame.draw.rect(debugLayer, GREEN, debugrect, 1)
            pygame.draw.circle(debugLayer, GREEN, (self.left * SCREEN_MULTIPLIER, self.top * SCREEN_MULTIPLIER), 2)
            pygame.draw.circle(debugLayer, GREEN, (self.right * SCREEN_MULTIPLIER, self.top * SCREEN_MULTIPLIER), 2)
            pygame.draw.circle(debugLayer, GREEN, (self.left * SCREEN_MULTIPLIER, self.bottom * SCREEN_MULTIPLIER), 2)
            pygame.draw.circle(debugLayer, GREEN, (self.right * SCREEN_MULTIPLIER, self.bottom * SCREEN_MULTIPLIER), 2)

class ghost():
    def __init__(self, color):
        self.x = 0
        self.y = 0
        self.color = color

        self.anim_left = {}
        self.anim_right = {}
        self.anim_up = {}
        self.anim_down = {}
        self.anim_current = None
        self.animFrame = 1

        for i in range(1, 3, 1):
            self.anim_left[i-1] = self.loadAnimFrame(DIR_LEFT, i)
            self.anim_right[i-1] = self.loadAnimFrame(DIR_RIGHT, i)
            self.anim_up[i-1] = self.loadAnimFrame(DIR_UP, i)
            self.anim_down[i-1] = self.loadAnimFrame(DIR_DOWN, i)

        self.anim_current = self.anim_right

    def loadAnimFrame(self, dir, frame):
        image = pygame.image.load(os.path.join(SCRIPT_PATH,"res","sprite","ghost_" + dir + "_" + str(frame) + ".png")).convert_alpha()
        for y in range(0, SPRITE_SIZE, 1):
            for x in range(0, SPRITE_SIZE, 1):
                if image.get_at( (x, y) ) == (255, 0, 0, 255):
                    # wall edge
                    image.set_at( (x, y), self.color )
        return image

    def ScreenPos(self):
        return (self.x - HALF_TILE_SIZE, self.y - HALF_TILE_SIZE)

    def Draw(self):
        screen.blit(self.anim_current[self.animFrame], self.ScreenPos())

class pacman():
    def __init__(self):
        self.x = 0
        self.y = 0
        self.targetX = 0
        self.targetY = 0
        self.speed = .7

        self.nearestRow = 0
        self.nearestCol = 0

        self.homeX = 0
        self.homeY = 0

        self.anim_left = {}
        self.anim_right = {}
        self.anim_up = {}
        self.anim_down = {}
        self.anim_current = None
        self.animFrame = 1
        self.animDelay = 0
        self.direction = DIR_RIGHT

        for i in range(1, 4, 1):
            self.anim_left[i-1] = pygame.image.load(os.path.join(SCRIPT_PATH,"res","sprite","pacman_left_" + str(i) + ".png")).convert_alpha()
            self.anim_right[i-1] = pygame.image.load(os.path.join(SCRIPT_PATH,"res","sprite","pacman_right_" + str(i) + ".png")).convert_alpha()
            self.anim_up[i-1] = pygame.image.load(os.path.join(SCRIPT_PATH,"res","sprite","pacman_up_" + str(i) + ".png")).convert_alpha()
            self.anim_down[i-1] = pygame.image.load(os.path.join(SCRIPT_PATH,"res","sprite","pacman_down_" + str(i) + ".png")).convert_alpha()

    def SnapToPosition(self, x, y):
        self.x = x
        self.y = y
        self.targetX = x
        self.targetY = y

    def AtTarget(self):
        return self.x == self.targetX and self.y == self.targetY

    def OnEnterTile(self, row, col):
        if self.direction == DIR_RIGHT:
            self.UpdateTarget(row, col + 1)
        elif self.direction == DIR_LEFT:
            self.UpdateTarget(row, col - 1)
        elif self.direction == DIR_UP:
            self.UpdateTarget(row - 1, col)
        elif self.direction == DIR_DOWN:
            self.UpdateTarget(row + 1, col)

    def UpdateTarget(self, row, col):
        if levelController.GetColTile(row, col) & TILE_FLAG_LEGAL:
            self.targetX = col * TILE_SIZE
            self.targetY = row * TILE_SIZE
        else:
            if self.direction == DIR_RIGHT:
                self.targetX = (col - 1) * TILE_SIZE
            elif self.direction == DIR_LEFT:
                self.targetX = (col + 1) * TILE_SIZE
            elif self.direction == DIR_UP:
                self.targetY = (row + 1) * TILE_SIZE
            elif self.direction == DIR_DOWN:
                self.targetY = (row - 1) * TILE_SIZE

    def Update(self):
        row = int((self.y + HALF_TILE_SIZE) / TILE_SIZE)
        col = int((self.x + HALF_TILE_SIZE) / TILE_SIZE)
        if row != self.nearestRow or col != self.nearestCol:
            self.nearestCol = col
            self.nearestRow = row
            self.OnEnterTile(row, col)

        #move towards target and select animation
        moved = False
        if self.direction == DIR_RIGHT:
            self.anim_current = self.anim_right
        elif self.direction == DIR_LEFT:
            self.anim_current = self.anim_left
        elif self.direction == DIR_UP:
            self.anim_current = self.anim_up
        elif self.direction == DIR_DOWN:
            self.anim_current = self.anim_down
        else:
            self.anim_current = self.anim_right
            self.animDelay = 0
            self.animFrame = 2

        if self.x < self.targetX:
            self.x = min(self.x + self.speed, self.targetX)
            moved = True
        elif self.x > self.targetX:
            self.x = max(self.x - self.speed, self.targetX)
            moved = True

        if self.y > self.targetY:
            self.y = max(self.y - self.speed, self.targetY)
            moved = True
        elif self.y < self.targetY:
            self.y = min(self.y + self.speed, self.targetY)
            moved = True

        if moved:
            self.animDelay += 1
        else:
            self.animFrame = 2

        if self.animDelay == 4:
            self.animFrame = (self.animFrame + 1) % 3
            self.animDelay = 0

    def ScreenPos(self):
        return (self.x - HALF_TILE_SIZE, self.y - HALF_TILE_SIZE)

    def Draw(self):
        screen.blit(self.anim_current[self.animFrame], self.ScreenPos())

        if DEBUGDRAW:
            row = self.nearestRow
            col = self.nearestCol
            debugrect = (col * TILE_SIZE* SCREEN_MULTIPLIER, row * TILE_SIZE * SCREEN_MULTIPLIER, TILE_SIZE * SCREEN_MULTIPLIER, TILE_SIZE * SCREEN_MULTIPLIER)
            pygame.draw.rect(debugLayer, RED, debugrect, 1)
            pygame.draw.circle(debugLayer, RED, (int(self.targetX * SCREEN_MULTIPLIER), int(self.targetY * SCREEN_MULTIPLIER)), 3, 1)
            pygame.draw.circle(debugLayer, BLUE, (int(self.x * SCREEN_MULTIPLIER), int(self.y * SCREEN_MULTIPLIER)), 3, 1)

class level():
    def __init__(self):
        self.lvlWidth = 0
        self.lvlHeight = 0
        self.colWidth = 0
        self.colHeight = 0

        self.edgeLightColor = (0, 0, 255, 255)
        self.edgeShadowColor = (0, 0, 255, 255)
        self.fillColor = (255, 0, 0, 255)
        self.pelletColor = (255, 255, 255, 255)

        self.tilemap = {}
        self.colmap = {}
        self.pellets = 0

    def GetPelletCount(self):
        return self.pellets

    def EatPellet(self, row, col, powerpellet = False):
        self.pellets -= 1
        # todo - play pellet eaten sound
        # todo - player different sound if power pellet
        # todo - pacman pauses for one frame when eating a pellet. Do that
        self.SetMapTile(row, col, 0)

    def EatBonus(self, theBonus):
        theBonus.SetActive(False)

    def TileIndex(self, row, col):
        return (row + self.lvlWidth) + col

    def ColIndex(self, row, col):
        return (row * self.colWidth) + col

    def SetColTileFlag(self, row, col, flag):
        index = self.ColIndex(row, col)
        value = self.colmap[index]
        self.colmap[index] = (value | flag)

    def SetColTile(self, row, col, value):
        index = self.ColIndex(row, col)
        self.colmap[index] = value

    def RemoveColTileFlag(self, row, col, flag):
        index = self.ColIndex(row, col)
        value = self.colmap[index]
        self.colmap[index] = (value & ~flag)

    def GetColTile(self, row, col):
        if row >= 0 and row < self.lvlHeight and col >= 0 and col < self.lvlWidth:
            index = self.ColIndex(row, col)
            return self.colmap[index]
        else:
            return 0

    def HasColFlag(self, row, col, flag):
        if row >= 0 and row < self.lvlHeight and col >= 0 and col < self.lvlWidth:
            index = self.ColIndex(row, col)
            value = self.colmap[index]
            return value & flag
        else:
            return False

    def SetMapTile(self, row, col, value):
        self.tilemap[(row * self.lvlWidth) + col] = value
        # Todo - Make background only partially update instead of redraw everything
        self.render = True

    def GetMapTile(self, row, col):
        if row >= 0 and row < self.lvlHeight and col >= 0 and col < self.lvlWidth:
            return self.tilemap[(row * self.lvlWidth) + col]
        else:
            return 0

    def LoadLevel(self, levelNum):
        self.currentLevel = levelNum
        self.tilemap = {}
        self.pellets = 0
        self.render = True

        f = open(os.path.join(SCRIPT_PATH,"res","levels",str(levelNum) + ".txt"), 'r')
        lineNum = -1
        rowNum = 0
        useLine = False
        isReadingLevelData = False
        isReadingCollisionData = False

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
                    self.colWidth = self.lvlWidth
                    # print "Width is " + str( self.lvlWidth )

                elif firstWord == "lvlheight":
                    self.lvlHeight = int( str_splitBySpace[2] )
                    self.colHeight = self.lvlHeight
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

                elif firstWord == "startleveldata":
                    isReadingLevelData = True
                    # print "Level data has begun"
                    rowNum = 0

                elif firstWord == "endleveldata":
                    isReadingLevelData = False
                    # print "Level data has ended"
                elif firstWord == "startcollisiondata":
                    isReadingCollisionData = True
                    rowNum = 0
                elif firstWord == "endcollisiondata":
                    isReadingCollisionData = False
            else:
                useLine = True


            if useLine == True:
                if isReadingCollisionData == True:
                    for k in range(0, self.colWidth, 1):
                        self.SetColTile(rowNum, k, int(str_splitBySpace[k]))
                    rowNum += 1
                if isReadingLevelData == True:

                    # print str( len(str_splitBySpace) ) + " tiles in this column"

                    for k in range(0, self.lvlWidth, 1):
                        self.SetMapTile(rowNum, k, int(str_splitBySpace[k]))

                        thisID = int(str_splitBySpace[k])
                        if thisID == TILE_MAP_PACMAN_START:
                            # starting position for pac-man
                            if player.homeX == 0 and player.homeY == 0:
                                player.homeX = k * TILE_SIZE
                                player.homeY = rowNum * TILE_SIZE
                            else:
                                player.homeX = ((k * TILE_SIZE) + player.homeX) / 2
                                player.homeY = ((rowNum * TILE_SIZE) + player.homeY) / 2
                            self.SetMapTile(rowNum, k, 0)

                        elif thisID == TILE_MAP_FRUIT_START:
                            fruit.col = k
                            fruit.row = rowNum
                            self.SetMapTile(rowNum, k, 0)

                        elif thisID >= 10 and thisID <= 13:
                            # one of the ghosts

                            #ghosts[thisID - 10].homeX = k * TILE_SIZE
                            #ghosts[thisID - 10].homeY = rowNum * TILE_SIZE
                            self.SetMapTile(rowNum, k, 0)

                        elif thisID == TILE_MAP_PELLET:
                            # pellet
                            self.pellets += 1

                        elif thisID == TILE_MAP_POWER_PELLET:
                            self.pellets += 1

                    rowNum += 1
        GetCrossRef()

    def DrawLevel(self):
        if self.render:
            background.fill(TRANSPARENT_BLACK)

        for row in range(-1, screenTileSize[0] + 1, 1):
            for col in range(-1, screenTileSize[1] + 1, 1):
                if self.render:
                    useTile = self.GetMapTile(row, col)
                    if not useTile == 0 and not useTile == tileID['door-h'] and not useTile == tileID['door-v']:
                        background.blit(tileIDImage[useTile], (col * TILE_SIZE, row * TILE_SIZE))

                if DEBUGDRAW:
                    debugrect = (col * TILE_SIZE* SCREEN_MULTIPLIER, row * TILE_SIZE * SCREEN_MULTIPLIER, TILE_SIZE * SCREEN_MULTIPLIER, TILE_SIZE * SCREEN_MULTIPLIER)
                    pygame.draw.rect(debugLayer, GRID, debugrect, 1)
                    col = self.GetColTile(row, col)
                    if col & TILE_FLAG_LEGAL:
                        pygame.draw.rect(debugLayer, LEGAL, debugrect)
                    if col & TILE_FLAG_TUNNEL:
                        pygame.draw.rect(debugLayer, TUNNEL, debugrect)

        self.render = False

    def Restart(self):
        player.SnapToPosition(player.homeX, player.homeY)
        player.direction = DIR_RIGHT
        # todo - reset pellets if not a straight reload

def CheckIfCloseButton(events):
    for event in events:
        if event.type == QUIT:
            sys.exit(0)

button_pressed = 0
debugRow = 0
debugCol = 0

def CheckInputs():
    global DEBUGDRAW, debugRow, debugCol, button_pressed
    if pygame.key.get_pressed()[pygame.K_r]:
        levelController.LoadLevel(levelController.currentLevel)
        levelController.Restart()
        fruit.SetActive(True)
    if pygame.key.get_pressed()[pygame.K_q]:
        if DEBUGDRAW == 1:
            DEBUGDRAW = 0
        else:
            DEBUGDRAW = 1

    row = player.nearestRow
    col = player.nearestCol
    debugCol = col
    debugRow = row
    if pygame.key.get_pressed()[pygame.K_RIGHT]:
        if (levelController.GetColTile(row, col + 1) & TILE_FLAG_LEGAL):
            player.direction = DIR_RIGHT
            debugCol = col + 1
            button_pressed = 1
            player.UpdateTarget(row, col + 1)
    elif pygame.key.get_pressed()[pygame.K_LEFT]:
        if (levelController.GetColTile(row, col - 1) & TILE_FLAG_LEGAL):
            player.direction = DIR_LEFT
            debugCol = col - 1
            button_pressed = 1
            player.UpdateTarget(row, col - 1)
    elif pygame.key.get_pressed()[pygame.K_UP]:
        if (levelController.GetColTile(row - 1, col) & TILE_FLAG_LEGAL):
            player.direction = DIR_UP
            button_pressed = 1
            debugRow = row - 1
            player.UpdateTarget(row - 1, col)
    elif pygame.key.get_pressed()[pygame.K_DOWN]:
        if (levelController.GetColTile(row + 1, col) & TILE_FLAG_LEGAL):
            player.direction = DIR_DOWN
            debugRow = row + 1
            button_pressed = 1
            player.UpdateTarget(row + 1, col)
#      _____________________________________________
# ___/  function: Get ID-Tilename Cross References  \______________________________________

EXT = ".gif"

def GetCrossRef ():
    global EXT
    f = open(os.path.join(SCRIPT_PATH,"res","crossrefv2.txt"), 'r')
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

        if (j == "'" or j == ""):
            # comment / whitespace line
            # print " ignoring comment line.. "
            useLine = False
        elif (j == "#"):
            useLine = False
            firstWord = str_splitBySpace[1]
            if firstWord == "extension":
                EXT = str_splitBySpace[2]
        else:
            # print str(wordNum) + ". " + j
            useLine = True

        if useLine == True:
            tileIDName[ int(str_splitBySpace[0]) ] = str_splitBySpace[1]
            tileID[ str_splitBySpace[1] ] = int(str_splitBySpace[0])

            thisID = int(str_splitBySpace[0])
            if not thisID in NO_GIF_TILES:
                tileIDImage[ thisID ] = pygame.image.load(os.path.join(SCRIPT_PATH,"res","tiles",str_splitBySpace[1] + EXT)).convert_alpha()
            else:
                tileIDImage[ thisID ] = pygame.Surface((TILE_SIZE,TILE_SIZE))

            # change colors in tileIDImage to match maze colors
            for y in range(0, TILE_SIZE, 1):
                for x in range(0, TILE_SIZE, 1):

                    if tileIDImage[ thisID ].get_at( (x, y) ) == (202, 0, 0, 255):
                        # wall edge
                        tileIDImage[ thisID ].set_at( (x, y), levelController.edgeLightColor )

                    elif tileIDImage[ thisID ].get_at( (x, y) ) == (0, 0, 121, 255):
                        # wall fill
                        tileIDImage[ thisID ].set_at( (x, y), levelController.fillColor )

                    elif tileIDImage[ thisID ].get_at( (x, y) ) == (255, 0, 255, 255):
                        # pellet color
                        tileIDImage[ thisID ].set_at( (x, y), levelController.edgeShadowColor )

                    elif tileIDImage[ thisID ].get_at( (x, y) ) == (128, 0, 128, 255):
                        # pellet color
                        tileIDImage[ thisID ].set_at( (x, y), levelController.pelletColor )

                        # print str_splitBySpace[0] + " is married to " + str_splitBySpace[1]
        lineNum += 1

def CheckCollisions():
    row = player.nearestRow
    col = player.nearestCol
    # check player vs ghosts
        # check ghost state (Normal vs Frightened)

    # check player vs pellet
    maptile = levelController.GetMapTile(row, col)
    if maptile == TILE_MAP_PELLET:
        return COLLISION_PELLET
    if maptile == TILE_MAP_POWER_PELLET:
        return COLLISION_POWER_PELLET
    if fruit.active and fruit.DoesCollide(player.x, player.y):
        return COLLISION_FRUIT

    return COLLISION_NOTHING

screenTileSize = (36, 28)
screenSize = (screenTileSize[1] * TILE_SIZE, screenTileSize[0] * TILE_SIZE)

windowSize = (screenSize[0] * SCREEN_MULTIPLIER, screenSize[1] * SCREEN_MULTIPLIER)
window = pygame.display.set_mode( windowSize, pygame.DOUBLEBUF | pygame.HWSURFACE )
screen = pygame.Surface(screenSize)
background  = pygame.Surface(screenSize)
debugLayer = pygame.Surface(windowSize, pygame.SRCALPHA, 32)

player = pacman()
pinky = ghost(PINK)
pinky.x = 1 * TILE_SIZE
pinky.y = 4 * TILE_SIZE

fruit = bonus()

levelController = level()
levelController.LoadLevel(99)
levelController.Restart()

# todo - move this into Game class when written
lives = 3

while True:
    CheckIfCloseButton( pygame.event.get() )
    CheckInputs()

    player.Update()
    # ghost update

    # check collisions
    collision = CheckCollisions()
    if collision == COLLISION_GHOST:
        if lives > 0:
            # enter death state
            lives -= 1
            print("Pacman is dead")
        else:
            # gameover
            print("game over")
    elif collision == COLLISION_PELLET or collision == COLLISION_POWER_PELLET:
        levelController.EatPellet(player.nearestRow, player.nearestCol, (collision == COLLISION_POWER_PELLET))
        if levelController.GetPelletCount() == 0:
            # level is over, change to victory state
            print("You beat the level")
    elif collision == COLLISION_FRUIT:
        levelController.EatBonus(fruit)
        print("you ate the master fruit")

    screen.fill(TRANSPARENT_BLACK)
    if DEBUGDRAW:
        debugLayer.fill(TRANSPARENT_BLACK)

    levelController.DrawLevel()
    screen.blit(background, (0,0))
    fruit.Draw()
    player.Draw()
    pinky.Draw()

    if button_pressed:
        debugrect = (debugCol * TILE_SIZE* SCREEN_MULTIPLIER, debugRow * TILE_SIZE * SCREEN_MULTIPLIER, TILE_SIZE * SCREEN_MULTIPLIER, TILE_SIZE * SCREEN_MULTIPLIER)
        pygame.draw.rect(debugLayer, GREEN, debugrect, 1)

    button_pressed = 0
    pygame.transform.scale(screen, windowSize, window)
    if DEBUGDRAW:
        window.blit(debugLayer, (0,0))
    pygame.display.flip()

    clock.tick (FRAME_TIME)