#!/usr/bin/env python3

"""Flappy Bird, implemented using Pygame."""

import math
import os
from random import randint
from collections import deque

import pygame
from pygame.locals import *


FPS = 60
FRAME_ANIMATION_WIDTH = 3  # pixels per frame
WIN_WIDTH = 284 * 2        # BG image size: 284x512 px; tiled twice
WIN_HEIGHT = 512


class Bird(pygame.sprite.Sprite):
    """Represents the bird controlled by the player.
    
    The bird is the 'hero' of this game.  The player can make it jump
    (ascend quickly), otherwise it drops (descends more slowly).  It must
    pass through the space in between pipes (for every pipe passed, one
    point is scored); if it crashes into a pipe, the game ends.
    
    Attributes:
    x: The bird's X coordinate.
    y: The bird's Y coordinate.
    steps_to_jump: The number of steps left to jump, where a complete
        jump consists of Bird.JUMP_STEPS frames.
    
    Constants:
    WIDTH: The width, in pixels, of the bird's image.
    HEIGHT: The height, in pixels, of the bird's image.
    FRAME_DROP_HEIGHT: How many pixels the bird descends in one frame.
    FRAME_JUMP_HEIGHT: How many pixels the bird ascends in one frame
        while jumping, on average.  See also the Bird.update docstring.
    JUMP_STEPS: How many frames it takes the bird to execute a complete
        jump.
    """
    
    WIDTH = HEIGHT = 32
    FRAME_DROP_HEIGHT = 3     # pixels per frame
    FRAME_JUMP_HEIGHT = 5     # pixels per frame
    JUMP_STEPS = 20           # see Bird.update docstring
    
    def __init__(self, x, y, steps_to_jump, images):
        """Initialise a new Bird instance.
        
        Arguments:
        x: The bird's initial X coordinate.
        y: The bird's initial Y coordinate.
        steps_to_jump: The number of steps left to jump, where a
            complete jump consists of Bird.JUMP_STEPS frames.  Use this
            if you want the bird to make a (small?) jump at the very
            beginning of the game.
        images: A tuple containing the images used by this bird.  It
            must contain the following images, in the following order:
            0. image of the bird with its wing pointing upward
            1. image of the bird with its wing pointing downward
        """
        super(Bird, self).__init__()
        self.x, self.y = x, y
        self.steps_to_jump = steps_to_jump
        self._img_wingup, self._img_wingdown = images
    
    def update(self):
        """Update the bird's position.
        
        This function uses the cosine function to achieve a smooth jump:
        In the first and last few frames, the bird jumps very little, in the
        middle of the jump, it jumps a lot.
        After a completed jump, the bird will have jumped
        Bird.FRAME_JUMP_HEIGHT * Bird.JUMP_STEPS pixels high, thus jumping,
        on average, Bird.FRAME_JUMP_HEIGHT pixels every step.
        This Bird's steps_to_jump attribute will automatically be
        decremented if it was > 0 when this method was called.
        """
        if steps_to_jump > 0:
            frac_jump_done = ((Bird.JUMP_STEPS - self.steps_to_jump) /
                              float(Bird.JUMP_STEPS))
            self.y -= (Bird.FRAME_JUMP_HEIGHT *
                       (1 - math.cos(frac_jump_done * math.pi)))
            self.steps_to_jump -= 1
        else:
            self.y += Bird.FRAME_DROP_HEIGHT
    
    @property
    def image(self):
        """Get a Surface containing this bird's image.
        
        This will decide whether to return an image where the bird's
        visible wing is pointing upward or where it is pointing downward
        based on pygame.time.get_ticks().  This will animate the flapping
        bird, even though pygame doesn't support animated GIFs.
        """
        if pygame.time.get_ticks() % 500 >= 250:
            return self._img_wingup
        else:
            return self._img_wingdown
    
    @property
    def rect(self):
        """Get the bird's position, width, and height, as a pygame.Rect."""
        return Rect(self.x, self.y, Bird.WIDTH, Bird.HEIGHT)


class PipePair:
    """Represents an obstacle.
    
    A PipePair has a top and a bottom pipe, and only between them can
    the bird pass -- if it collides with either part, the game is over.
    
    Attributes:
    x: The PipePair's X position.  Note that there is no y attribute,
        as it will only ever be 0.
    image: A pygame.Surface which can be blitted to the display surface
        to display the PipePair.
    top_pieces: The number of pieces, including the end piece, in the
        top pipe.
    bottom_pieces: The number of pieces, including the end piece, in
        the bottom pipe.
    
    Constants:
    WIDTH: The width, in pixels, of a pipe piece.  Because a pipe is
        only one piece wide, this is also the width of a PipePair's
        image.
    PIECE_HEIGHT: The height, in pixels, of a pipe piece.
    ADD_INTERVAL: The interval, in milliseconds, in between adding new
        pipes.
    ADD_EVENT: Identifies the event in the queue which signifies that a
        new pipe should be added.
    """
    
    WIDTH = 80
    PIECE_HEIGHT = 32
    ADD_INTERVAL = 3000  # milliseconds
    ADD_EVENT = USEREVENT + 1  # custom event
    
    def __init__(self, pipe_end_img, pipe_body_img):
        """Initialises a new random PipePair.
        
        The new PipePair will automatically be assigned an x attribute of
        WIN_WIDTH.
        
        Arguments:
        pipe_end_img: The image to use to represent a pipe's end piece.
        pipe_body_img: The image to use to represent one horizontal slice
            of a pipe's body.
        """
        self.x = WIN_WIDTH
        self.score_counted = False
        
        self.image = pygame.Surface((PipePair.WIDTH, WIN_HEIGHT), SRCALPHA)
        self.image.convert()   # speeds up blitting
        self.image.fill((0, 0, 0, 0))
        total_pipe_body_pieces = int(
            (WIN_HEIGHT -                # fill window from top to bottom
            3 * Bird.HEIGHT -            # make room for bird to fit through
            3 * PipePair.PIECE_HEIGHT) / # 2 end pieces + 1 body piece
            PipePair.PIECE_HEIGHT        # to get number of pipe pieces
        )
        self.bottom_pieces = randint(1, total_pipe_body_pieces)
        self.top_pieces = total_pipe_body_pieces - self.bottom_pieces
        
        # bottom pipe
        for i in range(1, self.bottom_pieces + 1):
            piece_pos = (0, WIN_HEIGHT - i*PipePair.PIECE_HEIGHT)
            self.image.blit(pipe_body_img, piece_pos)
        bottom_pipe_end_y = (WIN_HEIGHT - 
                             self.bottom_pieces*PipePair.PIECE_HEIGHT)
        bottom_end_piece_pos = (0, bottom_pipe_end_y - PipePair.PIECE_HEIGHT)
        self.image.blit(pipe_end_img, bottom_end_piece_pos)
        
        # top pipe
        for i in range(self.top_pieces):
            self.image.blit(pipe_body_img, (0, i * PipePair.PIECE_HEIGHT))
        top_pipe_end_y = self.top_pieces * PipePair.PIECE_HEIGHT
        self.image.blit(pipe_end_img, (0, top_pipe_end_y))
        
        # compensate for added end pieces
        self.top_pieces += 1
        self.bottom_pieces += 1
    
    @property
    def top_height_px(self):
        """Get the top pipe's height, in pixels."""
        return self.top_pieces * PipePair.PIECE_HEIGHT
    
    @property
    def bottom_height_px(self):
        """Get the bottom pipe's height, in pixels."""
        return self.bottom_pieces * PipePair.PIECE_HEIGHT
    
    def collides_with(self, rect):
        """Get whether an object collides with a pipe in this PipePair.
        
        Arguments:
        rect: The pygame.Rect of the object that should be tested for
            collision with this PipePair.
        """
        top_rect = Rect(self.x, 0, PipePair.WIDTH, self.top_height_px)
        bottom_rect = Rect(self.x, WIN_HEIGHT - self.bottom_height_px,
                           PipePair.WIDTH, self.bottom_height_px)
        return rect.collidelist((top_rect, bottom_rect)) > -1


def load_images():
    """Load all images required by the game and return a dict of them.
    
    The returned dict has the following keys:
    background: The game's background image.
    bird-wingup: An image of the bird with its wing pointing upward.
        Use this and bird-wingdown to create a flapping bird.
    bird-wingdown: An image of the bird with its wing pointing downward.
        Use this and bird-wingup to create a flapping bird.
    pipe-end: An image of a pipe's end piece (the slightly wider bit).
        Use this and pipe-body to make pipes.
    pipe-body: An image of a slice of a pipe's body.  Use this and
        pipe-body to make pipes.
    """
    
    def load_image(img_file_name):
        """Return the loaded pygame image with the specified file name.
        
        This function looks for images in the game's images folder
        (./images/).  All images are converted before being returned to
        speed up blitting.
        
        Arguments:
        img_file_name: The file name (including its extension, e.g.
            '.png') of the required image, without a file path.
        """
        file_name = os.path.join('.', 'images', img_file_name)
        img = pygame.image.load(file_name)
        # converting all images before use speeds up blitting
        img.convert()
        return img
    
    return {'background': load_image('background.png'),
            'pipe-end': load_image('pipe_end.png'),
            'pipe-body': load_image('pipe_body.png'),            
            # images for animating the flapping bird -- animated GIFs are
            # not supported in pygame
            'bird-wingup': load_image('bird_wing_up.png'),
            'bird-wingdown': load_image('bird_wing_down.png'),}


def frames_to_msec(frames, fps=FPS):
    """Convert frames to milliseconds at the specified framerate.
    
    Arguments:
    frames: How many frames to convert to milliseconds.
    fps: The framerate to use for conversion.  Default: FPS.
    """
    return 1000.0 * frames / fps


def msec_to_frames(milliseconds, fps=FPS):
    """Convert milliseconds to frames at the specified framerate.
    
    Arguments:
    milliseconds: How many milliseconds to convert to frames.
    fps: The framerate to use for conversion.  Default: FPS.
    """
    return fps * milliseconds / 1000.0


def main():
    """The application's entry point.
    
    If someone executes this module (instead of importing it, for
    example), this function is called.
    """
    
    pygame.init()
    
    display_surface = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
    pygame.display.set_caption('Pygame Flappy Bird')
    
    clock = pygame.time.Clock()
    score_font = pygame.font.SysFont(None, 32, bold=True)  # default font
    images = load_images()
    
    # the bird stays in the same x position, so bird.x is a constant
    # center bird on screen
    bird = Bird(50, int(WIN_HEIGHT/2 - Bird.HEIGHT/2), 2
                (images['bird-wingup'], images['bird-wingdown']))
    
    pipes = deque()
    
    frame_clock = 0  # this counter is only incremented if the game isn't paused
    score = 0
    done = paused = False
    while not done:
        clock.tick(FPS)
        
        # Handle this 'manually'.  if we use pygame.time.set_timer(),
        # pipe addition would be messed up when paused.
        if not (paused or frame_clock % msec_to_frames(PipePair.ADD_INTERVAL)):
            pygame.event.post(pygame.event.Event(PipePair.ADD_EVENT))
        
        for e in pygame.event.get():
            if e.type == QUIT or (e.type == KEYUP and e.key == K_ESCAPE):
                done = True
                break
            elif e.type == KEYUP and e.key in (K_PAUSE, K_p):
                paused = not paused
            elif e.type == MOUSEBUTTONUP or (e.type == KEYUP and
                    e.key in (K_UP, K_RETURN, K_SPACE)):
                bird.steps_to_jump = Bird.JUMP_STEPS
            elif e.type == PipePair.ADD_EVENT:
                pp = PipePair(images['pipe-end'], images['pipe-body'])
                pipes.append(pp)
        
        if paused:
            continue  # don't draw anything
        
        # check for collisions
        pipe_collision = any(p.collides_with(bird.rect) for p in pipes)
        if pipe_collision or 0 >= bird.y or bird.y >= WIN_HEIGHT - Bird.HEIGHT:
            done = True
        
        for x in (0, WIN_WIDTH / 2):
            display_surface.blit(images['background'], (x, 0))
        
        while len(pipes) > 0 and pipes[0].x <= -PipePair.WIDTH:
            pipes.popleft()
        
        for p in pipes:
            p.x -= FRAME_ANIMATION_WIDTH
            display_surface.blit(p.image, (p.x, 0))
        
        bird.update()
        
        display_surface.blit(bird.image, bird.rect)
        
        # update and display score
        for p in pipes:
            if p.x + PipePair.WIDTH < bird.x and not p.score_counted:
                score += 1
                p.score_counted = True
        
        score_surface = score_font.render(str(score), True, (255, 255, 255))
        score_x = WIN_WIDTH/2 - score_surface.get_width()/2
        display_surface.blit(score_surface, (score_x, PipePair.PIECE_HEIGHT))
        
        pygame.display.flip()
        frame_clock += 1
    print('Game over! Score: %i' % score)
    pygame.quit()


if __name__ == '__main__':
    # If this module had been imported, __name__ would be 'flappybird'.
    # It was executed (e.g. by double-clicking the file), so call main.
    main()
