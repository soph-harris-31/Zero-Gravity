from Move import *
import math
import pygame

HEALTH_BAR_OFFSET = 10  # could be used but display is fine without it
HEALTH_BAR_WIDTH = 5

HITSTUN_CONSTANT = 5


class Char(pygame.sprite.Sprite):
    def __init__(self, name, game, player):
        pygame.sprite.Sprite.__init__(self)

        self.player = player  # player number
        self.game = game
        self.stage = self.game.stage
        self.screen = self.game.screen
        self.name = name  # use this to find the character datasheet, which determines all other character attributes

        self.canAct = True  # whether the character is in move lag or hitstun

        self.datasheet = open(self.name + ".txt")  # get data from the datasheet

        self.jumpSpeed = int(self.datasheet.readline()[7:])  # regular movement speed
        self.mass = float(self.datasheet.readline()[6:])
        self.startingHealth = int(self.datasheet.readline()[8:])  # starting health
        self.driftSpeed = int(self.datasheet.readline()[11:])  # how fast the character drifts

        self.spriteFile = self.datasheet.readline()[9:].strip()  # get the file with all the sprites
        self.spriteSheet = pygame.image.load(self.spriteFile).convert()
        self.spriteSheet.set_colorkey((255, 0, 255))  # remove background color

        next(self.datasheet)
        # sprite to be displayed when the character is in the air in a neutral position
        defSprite = self.datasheet.readline().split()
        self.defaultSprite = (int(defSprite[0]), int(defSprite[1]), int(defSprite[2]), int(defSprite[3]))

        next(self.datasheet)
        # sprite to be displayed whenever the character is on a wall
        wallSprite = self.datasheet.readline().split()
        self.wallSprite = (int(wallSprite[0]), int(wallSprite[1]), int(wallSprite[2]), int(wallSprite[3]))

        self.currSprite = self.wallSprite  # sprite to be displayed currently (points to a position on the spriteSheet)

        self.dims = (self.currSprite[2], self.currSprite[3])  # width and height
        # image of the character from sprite sheet
        self.image = self.spriteSheet.subsurface(self.currSprite[0], self.currSprite[1],
                                                 self.dims[0], self.dims[1]).copy()

        # start of left wall if you're player 1, right wall if you're player 2
        if self.player == 0:
            self.pos = (self.stage.p1start[0], self.stage.p1start[1] - self.dims[1] / 2)
            # start in the middle of the side wall
        if self.player == 1:
            self.pos = (self.stage.p2start[0] - self.dims[0] + 1, self.stage.p2start[1] - self.dims[1] / 2)

        self.moves = {}

        moveNames = ['neutralA', 'forwardA', 'backA', 'upA', 'downA']

        # for each move, read in the data from the file and create its move object
        for i in range(len(moveNames)):
            for k in range(3):
                next(self.datasheet)

            frames = self.datasheet.readline().split()
            damage = int(self.datasheet.readline()[7:])
            knockback = int(self.datasheet.readline()[10:])
            angle = int(self.datasheet.readline()[5:])
            numHitboxes = int(self.datasheet.readline()[10:12])

            hitboxes = []
            for k in range(numHitboxes):
                data = self.datasheet.readline().split()
                hitbox = []

                for c in range(len(data)-1):
                    hitbox.append(int(data[c]))

                if data[-1] == "True":
                    color = self.datasheet.readline().split()
                    hitbox.append((int(color[0]), int(color[1]), int(color[2])))

                else:
                    hitbox.append(None)

                hitboxes.append([pygame.Rect(hitbox[0:4]), hitbox[4]])

            next(self.datasheet)

            sprites = []
            for k in range(numHitboxes):
                data = self.datasheet.readline().split()
                sprite = []
                for datum in data:
                    sprite.append(int(datum))

                sprites.append(pygame.Rect(sprite))

            # create a move object with all the data read from the file
            self.moves[moveNames[i]] = Move(frames, damage, knockback, angle, hitboxes, sprites, self.game, self)

        self.hitstun = -1  # frames of hitstun remaining
        self.health = self.startingHealth  # starting health
        self.healthBar = pygame.Rect(0, 0, self.dims[0], HEALTH_BAR_WIDTH)

        self.hitboxes = []
        self.currMove = None  # the character's active move, if any

        self.rect = pygame.Rect(self.pos, self.dims)  # the character's hurtbox
        self.xVelocity = 0  # velocity in the x direction at any given time
        self.yVelocity = 0  # velocity in the y direction at any given time

        # orient the character based on which side of the field it is on
        if self.player == 0:
            self.side = 'right'
            self.orientation = 270  # angle the sprite has to be rotated
            self.onWall = [self.stage.leftWall]  # which wall(s) the character is on, if any

        if self.player == 1:
            self.side = 'left'
            self.orientation = 90
            self.onWall = [self.stage.rightWall]  # which wall(s) the character is on, if any

        self.flipped = False  # whether the sprite has to be flipped to face the opposite direction

    def jump(self, angle):  # character jumps off the wall based on input
        self.xVelocity = round(math.cos(math.radians(angle)), 2) * self.jumpSpeed
        self.yVelocity = round(-1 * math.sin(math.radians(angle)), 2) * self.jumpSpeed
        self.leaveWall()

    def drift(self, angle):  # move through the air in the direction being held
        x = math.cos(math.radians(angle)) * self.driftSpeed  # movement in the x direction
        y = -1 * math.sin(math.radians(angle)) * self.driftSpeed  # y direction
        self.move(x, y)

    def draw(self):  # displays itself on the screen
        sprite = self.image

        # sprite.fill(pygame.Color('White'), pygame.Rect(0,0,self.dims[0],HEALTH_BAR_WIDTH))
        sprite.fill(pygame.Color('Red'), self.healthBar)

        sprite = pygame.transform.rotate(sprite, self.orientation)  # rotate sprite depending on orientation

        if self.flipped:
            sprite = pygame.transform.flip(sprite, True, False)  # horizontally flip the sprite if necessary

        if self.hitstun != -1:
            color = (200, 255, 200)
        elif not self.canAct:
            if self.hitboxes:
                if self.hitboxes[0].shape.x > 0:
                    color = (255, 200, 200)
                else:
                    color = (255, 230, 200)
            else:
                color = (255, 230, 200)
        else:
            color = (255, 255, 200)

        pygame.draw.rect(self.screen, color, self.rect)  # draw the rectangle
        # draw the sprite--rect is used because rect is already in the correct location
        # if self.pos was used, sprite would appear hovering on right wall
        self.screen.blit(sprite, (self.rect.x, self.rect.y))

        for hitbox in self.hitboxes:  # draw the outline of the hitboxes
            outline = hitbox.mask.outline()
            print("Outline exists: " + str(len(outline) > 0))
            for point in outline:
                pygame.draw.circle(self.screen, pygame.Color("Red"),
                                   (point[0] + hitbox.rect.x, point[1] + hitbox.rect.y), 0)

    def update(self):  # operations that must be done every frame
        self.updateOrientation()
        self.move(self.xVelocity, self.yVelocity)
        self.updateCanAct()
        self.updateSprite()
        self.updateHurtbox()
        self.updateMoves()

    def updateMoves(self):
        self.hitboxes = []

        for key, value in self.moves.items():
            value.update()

    def updateCanAct(self):  # updates whether or not the character can act
        if self.hitstun != -1:
            self.hitstun -= 1

        if self.currMove is not None:
            self.canAct = False
        elif self.hitstun == 0:
            self.canAct = True
            self.hitstun = -1

    def updateHurtbox(self):  # makes sure the hurtbox matches the character's position
        self.rect = pygame.Rect(self.pos, self.dims)
        x = self.rect.x
        y = self.rect.y
        h = self.rect.h
        w = self.rect.w
        if self.orientation == 90:
            newDims = (h, w)
            newPos = (x + w - h, y - (w - h) / 2)
            self.rect = pygame.Rect(newPos, newDims)
        if self.orientation == 270:
            newDims = (h, w)
            newPos = (x, y + (h - w) / 2)
            self.rect = pygame.Rect(newPos, newDims)

    def updateOrientation(self):  # rotates the character so that it makes sense given its position
        if self.side == 'right':
            self.orientation = 270
        if self.side == 'down':
            self.orientation = 180
        if self.side == 'left':
            self.orientation = 90
        if self.side == 'up':
            self.orientation = 0
        if not self.onWall:
            self.orientation = 0

        if self.onWall == [] and self.player == 1:
            self.flipped = True
        else:
            self.flipped = False

    def updateSprite(self):
        if self.onWall:
            self.currSprite = self.wallSprite
        elif self.canAct:  # **could change
            self.currSprite = self.defaultSprite
        self.dims = (self.currSprite[2], self.currSprite[3])
        self.image = self.spriteSheet.subsurface(self.currSprite[0], self.currSprite[1],
                                                 self.dims[0], self.dims[1]).copy()

    def hitWall(self, wall):
        if wall not in self.onWall:
            self.canAct = True

            for key, value in self.moves.items():
                value.end()

            self.hitboxes = []
            self.onWall.append(wall)
            self.updateSprite()

            sides = self.stage.wallSide(self, walls=self.onWall)
            self.side = sides[0]
            wall = self.onWall[0]

            print("Sides: " + str(sides))

            # make sure character is completely on the wall
            if self.side == 'right':
                self.pos = (wall.x + wall.w - 1, self.pos[1])
                # print('right')
            elif self.side == 'down':
                self.pos = (self.pos[0], wall.y + wall.h - 1)
                # print('down')
            elif self.side == 'left':
                self.pos = (wall.x - self.dims[0] + 1, self.pos[1])
                # print('left')
            elif self.side == 'up':
                self.pos = (self.pos[0], wall.y - self.dims[1] + 1)
                # print('up')

            for wall in self.onWall:
                if wall == self.stage.walls[0]:
                    print("On left wall")
                if wall == self.stage.walls[1]:
                    print("On up wall")
                if wall == self.stage.walls[2]:
                    print("On right wall")
                if wall == self.stage.walls[3]:
                    print("On down wall")

            print("Pos: (%d,%d)" % (self.pos[0], self.pos[1]))
            # self.game.screen.fill(pygame.Color("Red"), pygame.Rect(500, 200, 10, 10))
            # self.game.screen.fill(pygame.Color("Blue"), pygame.Rect(835, 499, 10, 10))

    def leaveWall(self):
        self.onWall = []

    def hit(self, hitbox):  # get hit
        self.health -= hitbox.damage  # take the appropriate amount of damage
        if self.health <= 0:
            self.game.end(self)

        # update the health bar
        self.healthBar = pygame.Rect(0, 0, self.dims[0] * self.health / self.startingHealth, HEALTH_BAR_WIDTH)
        # Maybe change to: use the centers of each rectangle to determine the general direction the character will be sent in
        #  (i.e. the sign of the x and y velocity)
        #  the character will be sent in the opposite direction of the hurtbox
        #  the magnitude of the x and y velocity will be determined by the knockback and knockback angle of the hitbox
        if not self.onWall:
            self.xVelocity = math.sin(math.radians(hitbox.angle)) * hitbox.knockback * self.mass
            self.yVelocity = math.cos(math.radians(hitbox.angle)) * hitbox.knockback * self.mass

        self.canAct = False
        self.hitstun = int(hitbox.knockback * HITSTUN_CONSTANT)

        if self.hitstun != -1:
            print("Combo!")

    def move(self, x, y):
        self.pos = (self.pos[0] + x, self.pos[1] + y)

    def forwardA(self):
        if self.canAct:
            self.moves['forwardA'].start()

    def upA(self):
        if self.canAct:
            self.moves['upA'].start()

    def backA(self):
        if self.canAct:
            self.moves['backA'].start()

    def downA(self):
        if self.canAct:
            self.moves['downA'].start()

    def neutralA(self):
        if self.canAct:
            self.moves['neutralA'].start()

    def upB(self):
        pass

    def downB(self):
        pass

    def forwardB(self):
        pass

    def backB(self):
        pass

    def neutralB(self):
        pass

    def tether(self):
        pass

    def boost(self):
        pass

    def shield(self):
        # think about ideas for this--possibly a directional reflector shield that lasts for a short amount of time and has ending lag
        pass


class Button:
    def __init__(self, text, size, color, rect, game):
        self.words = text
        self.textSize = size
        self.rect = rect
        self.game = game
        self.color = color

    def draw(self):
        pygame.draw.rect(self.game.screen, (0, 0, 0), self.rect, 1)
        self.game.displayText(self.words, self.textSize, self.rect, (255, 255, 255), self.color)

    def clicked(self, pos):
        return self.rect.collidepoint(pos)
