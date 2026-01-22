#! /usr/bin/env python3

"""Flappy Bird, implemented using Pygame."""

import math
import os
from random import randint
from collections import deque

import pygame
from pygame.locals import *


FPS = 60
ANIMATION_SPEED = 0.18  # pixels per millisecond
WIN_WIDTH = 284 * 2     # BG image size: 284x512 px; tiled twice
WIN_HEIGHT = 512


class Bird(pygame.sprite.Sprite):
    """Represents the bird controlled by the player.

    The bird is the 'hero' of this game.  The player can make it climb
    (ascend quickly), otherwise it sinks (descends more slowly).  It must
    pass through the space in between pipes (for every pipe passed, one
    point is scored); if it crashes into a pipe, the game ends.

    Attributes:
    x: The bird's X coordinate.
    y: The bird's Y coordinate.
    msec_to_climb: The number of milliseconds left to climb, where a
        complete climb lasts Bird.CLIMB_DURATION milliseconds.
    red_effect_end: Time when red circle effect ends (speed reduction)
    orange_effect_end: Time when orange circle effect ends (increased gravity)

    Constants:
    WIDTH: The width, in pixels, of the bird's image.
    HEIGHT: The height, in pixels, of the bird's image.
    SINK_SPEED: With which speed, in pixels per millisecond, the bird
        descends in one second while not climbing.
    CLIMB_SPEED: With which speed, in pixels per millisecond, the bird
        ascends in one second while climbing, on average.  See also the
        Bird.update docstring.
    CLIMB_DURATION: The number of milliseconds it takes the bird to
        execute a complete climb.
    """

    WIDTH = HEIGHT = 32
    SINK_SPEED = 0.18
    CLIMB_SPEED = 0.3
    CLIMB_DURATION = 333.3
    RED_EFFECT_DURATION = 5000  # 5 seconds
    ORANGE_EFFECT_DURATION = 10000  # 10 seconds

    def __init__(self, x, y, msec_to_climb, images):
        """Initialise a new Bird instance.

        Arguments:
        x: The bird's initial X coordinate.
        y: The bird's initial Y coordinate.
        msec_to_climb: The number of milliseconds left to climb, where a
            complete climb lasts Bird.CLIMB_DURATION milliseconds.  Use
            this if you want the bird to make a (small?) climb at the
            very beginning of the game.
        images: A tuple containing the images used by this bird.  It
            must contain the following images, in the following order:
                0. image of the bird with its wing pointing upward
                1. image of the bird with its wing pointing downward
        """
        super(Bird, self).__init__()
        self.x, self.y = x, y
        self.msec_to_climb = msec_to_climb
        self._img_wingup, self._img_wingdown = images
        self._mask_wingup = pygame.mask.from_surface(self._img_wingup)
        self._mask_wingdown = pygame.mask.from_surface(self._img_wingdown)
        self.red_effect_end = 0
        self.orange_effect_end = 0

    def update(self, delta_frames=1):
        """Update the bird's position.

        This function uses the cosine function to achieve a smooth climb:
        In the first and last few frames, the bird climbs very little, in the
        middle of the climb, it climbs a lot.
        One complete climb lasts CLIMB_DURATION milliseconds, during which
        the bird ascends with an average speed of CLIMB_SPEED px/ms.
        This Bird's msec_to_climb attribute will automatically be
        decreased accordingly if it was > 0 when this method was called.

        Arguments:
        delta_frames: The number of frames elapsed since this method was
            last called.
        """
        current_time = pygame.time.get_ticks()
        
        # Apply red circle effect (speed reduction)
        climb_speed = Bird.CLIMB_SPEED
        if current_time < self.red_effect_end:
            climb_speed *= 0.8  # 20% speed reduction
            
        # Apply orange circle effect (increased gravity)
        sink_speed = Bird.SINK_SPEED
        if current_time < self.orange_effect_end:
            sink_speed *= 1.5  # 50% increased gravity
            
        if self.msec_to_climb > 0:
            frac_climb_done = 1 - self.msec_to_climb/Bird.CLIMB_DURATION
            climb_distance = climb_speed * frames_to_msec(delta_frames) * (1 - math.cos(frac_climb_done * math.pi))
            
            # Apply orange effect to reduce climb effectiveness
            if current_time < self.orange_effect_end:
                climb_distance *= 0.7  # 30% less effective climb
                
            self.y -= climb_distance
            self.msec_to_climb -= frames_to_msec(delta_frames)
        else:
            self.y += sink_speed * frames_to_msec(delta_frames)

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
    def mask(self):
        """Get a bitmask for use in collision detection.

        The bitmask excludes all pixels in self.image with a
        transparency greater than 127."""
        if pygame.time.get_ticks() % 500 >= 250:
            return self._mask_wingup
        else:
            return self._mask_wingdown

    @property
    def rect(self):
        """Get the bird's position, width, and height, as a pygame.Rect."""
        return Rect(self.x, self.y, Bird.WIDTH, Bird.HEIGHT)


class Circle(pygame.sprite.Sprite):
    """Represents a dynamic circle obstacle.

    Attributes:
    x: The Circle's X position.
    y: The Circle's Y position.
    type: The type of circle ("red", "orange", "yellow").
    speed: The vertical movement speed.
    direction: The current movement direction (1 for up, -1 for down).
    image: A pygame.Surface which can be blitted to the display surface.
    mask: A bitmask for collision detection.
    """

    WIDTH = 80  # Same as pipe width
    RED_SPEED = 1000 / 2  # 2 seconds to traverse Y axis
    ORANGE_SPEED = 1000 / 1.5  # 1.5 seconds
    YELLOW_SPEED = 1000 / 1.75  # 1.75 seconds
    RED_HEIGHT = WIN_HEIGHT // 6
    ORANGE_HEIGHT = WIN_HEIGHT // 6
    YELLOW_HEIGHT = WIN_HEIGHT // 4

    def __init__(self, circle_type):
        super(Circle, self).__init__()
        self.x = float(WIN_WIDTH - 1)
        self.type = circle_type
        self.direction = 1  # Start moving down
        self.score_counted = False

        # Set height and speed based on type
        if self.type == "red":
            self.height = Circle.RED_HEIGHT
            self.speed = Circle.RED_SPEED
            self.color = (255, 0, 0)
        elif self.type == "orange":
            self.height = Circle.ORANGE_HEIGHT
            self.speed = Circle.ORANGE_SPEED
            self.color = (255, 165, 0)
        else:  # yellow
            self.height = Circle.YELLOW_HEIGHT
            self.speed = Circle.YELLOW_SPEED
            self.color = (255, 255, 0)

        # Random initial Y position within valid range
        self.y = randint(self.height // 2, WIN_HEIGHT - self.height // 2)

        # Create the circle image
        self.image = pygame.Surface((Circle.WIDTH, self.height), SRCALPHA)
        self.image.convert()
        self.image.fill((0, 0, 0, 0))
        pygame.draw.ellipse(self.image, self.color, 
                           (0, 0, Circle.WIDTH, self.height))

        # Create mask for collision detection
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, delta_frames=1):
        """Update the circle's position."""
        self.x -= ANIMATION_SPEED * frames_to_msec(delta_frames)

        # Vertical movement
        distance = self.speed / FPS * delta_frames
        self.y += self.direction * distance

        # Reverse direction when hitting boundaries
        if self.y <= self.height // 2:
            self.y = self.height // 2
            self.direction = 1
        elif self.y >= WIN_HEIGHT - self.height // 2:
            self.y = WIN_HEIGHT - self.height // 2
            self.direction = -1

    @property
    def visible(self):
        """Get whether this Circle is on screen."""
        return -Circle.WIDTH < self.x < WIN_WIDTH

    @property
    def rect(self):
        """Get the Rect which contains this Circle."""
        return Rect(self.x, self.y - self.height // 2, Circle.WIDTH, self.height)

    def collides_with(self, bird):
        """Check collision with bird."""
        # Check if rects overlap first (fast check)
        if not self.rect.colliderect(bird.rect):
            return False
        
        # If rects overlap, do pixel-perfect collision check
        offset_x = int(self.x - bird.x)
        offset_y = int((self.y - self.height // 2) - bird.y)
        return bird.mask.overlap(self.mask, (offset_x, offset_y))


class PipePair(pygame.sprite.Sprite):
    """Represents an obstacle.

    A PipePair has a top and a bottom pipe, and only between them can
    the bird pass -- if it collides with either part, the game is over.

    Attributes:
    x: The PipePair's X position.  This is a float, to make movement
        smoother.  Note that there is no y attribute, as it will only
        ever be 0.
    image: A pygame.Surface which can be blitted to the display surface
        to display the PipePair.
    mask: A bitmask which excludes all pixels in self.image with a
        transparency greater than 127.  This can be used for collision
        detection.
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
    """

    WIDTH = 80
    PIECE_HEIGHT = 32
    ADD_INTERVAL = 3000

    def __init__(self, pipe_end_img, pipe_body_img):
        """Initialises a new random PipePair.

        The new PipePair will automatically be assigned an x attribute of
        float(WIN_WIDTH - 1).

        Arguments:
        pipe_end_img: The image to use to represent a pipe's end piece.
        pipe_body_img: The image to use to represent one horizontal slice
            of a pipe's body.
        """
        self.x = float(WIN_WIDTH - 1)
        self.score_counted = False

        self.image = pygame.Surface((PipePair.WIDTH, WIN_HEIGHT), SRCALPHA)
        self.image.convert()   # speeds up blitting
        self.image.fill((0, 0, 0, 0))
        total_pipe_body_pieces = int(
            (WIN_HEIGHT -                  # fill window from top to bottom
             3 * Bird.HEIGHT -             # make room for bird to fit through
             3 * PipePair.PIECE_HEIGHT) /  # 2 end pieces + 1 body piece
            PipePair.PIECE_HEIGHT          # to get number of pipe pieces
        )
        self.bottom_pieces = randint(1, total_pipe_body_pieces)
        self.top_pieces = total_pipe_body_pieces - self.bottom_pieces

        # bottom pipe
        for i in range(1, self.bottom_pieces + 1):
            piece_pos = (0, WIN_HEIGHT - i*PipePair.PIECE_HEIGHT)
            self.image.blit(pipe_body_img, piece_pos)
        bottom_pipe_end_y = WIN_HEIGHT - self.bottom_height_px
        bottom_end_piece_pos = (0, bottom_pipe_end_y - PipePair.PIECE_HEIGHT)
        self.image.blit(pipe_end_img, bottom_end_piece_pos)

        # top pipe
        for i in range(self.top_pieces):
            self.image.blit(pipe_body_img, (0, i * PipePair.PIECE_HEIGHT))
        top_pipe_end_y = self.top_height_px
        self.image.blit(pipe_end_img, (0, top_pipe_end_y))

        # compensate for added end pieces
        self.top_pieces += 1
        self.bottom_pieces += 1

        # for collision detection
        self.mask = pygame.mask.from_surface(self.image)

    @property
    def top_height_px(self):
        """Get the top pipe's height, in pixels."""
        return self.top_pieces * PipePair.PIECE_HEIGHT

    @property
    def bottom_height_px(self):
        """Get the bottom pipe's height, in pixels."""
        return self.bottom_pieces * PipePair.PIECE_HEIGHT

    @property
    def visible(self):
        """Get whether this PipePair on screen, visible to the player."""
        return -PipePair.WIDTH < self.x < WIN_WIDTH

    @property
    def rect(self):
        """Get the Rect which contains this PipePair."""
        return Rect(self.x, 0, PipePair.WIDTH, PipePair.PIECE_HEIGHT)

    def update(self, delta_frames=1):
        """Update the PipePair's position.

        Arguments:
        delta_frames: The number of frames elapsed since this method was
            last called.
        """
        self.x -= ANIMATION_SPEED * frames_to_msec(delta_frames)

    def collides_with(self, bird):
        """Get whether the bird collides with a pipe in this PipePair.

        Arguments:
        bird: The Bird which should be tested for collision with this
            PipePair.
        """
        return pygame.sprite.collide_mask(self, bird)


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
        (dirname(__file__)/images/). All images are converted before being
        returned to speed up blitting.

        Arguments:
        img_file_name: The file name (including its extension, e.g.
            '.png') of the required image, without a file path.
        """
        # Look for images relative to this script, so we don't have to "cd" to
        # the script's directory before running it.
        # See also: https://github.com/TimoWilken/flappy-bird-pygame/pull/3
        file_name = os.path.join(os.path.dirname(__file__),
                                 'images', img_file_name)
        img = pygame.image.load(file_name)
        img.convert()
        return img

    return {'background': load_image('background.png'),
            'pipe-end': load_image('pipe_end.png'),
            'pipe-body': load_image('pipe_body.png'),
            # images for animating the flapping bird -- animated GIFs are
            # not supported in pygame
            'bird-wingup': load_image('bird_wing_up.png'),
            'bird-wingdown': load_image('bird_wing_down.png')}


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
    bird = Bird(50, int(WIN_HEIGHT/2 - Bird.HEIGHT/2), 2,
                (images['bird-wingup'], images['bird-wingdown']))

    pipes = deque()
    circles = deque()
    circle_spawn_timer = 0
    CIRCLE_ADD_INTERVAL = 4000  # 4 seconds between circles

    frame_clock = 0  # this counter is only incremented if the game isn't paused
    score = 0
    done = paused = False
    while not done:
        clock.tick(FPS)

        # Handle this 'manually'.  If we used pygame.time.set_timer(),
        # pipe addition would be messed up when paused.
        if not (paused or frame_clock % msec_to_frames(PipePair.ADD_INTERVAL)):
            pp = PipePair(images['pipe-end'], images['pipe-body'])
            pipes.append(pp)

        # Add circles at intervals
        if not paused:
            circle_spawn_timer += frames_to_msec(1)
            if circle_spawn_timer >= CIRCLE_ADD_INTERVAL:
                circle_spawn_timer = 0
                # Choose circle type based on 3:2:1 ratio
                rand_val = randint(1, 6)
                if rand_val <= 3:
                    circle_type = "red"
                elif rand_val <= 5:
                    circle_type = "orange"
                else:
                    circle_type = "yellow"
                circle = Circle(circle_type)
                circles.append(circle)

        for e in pygame.event.get():
            if e.type == QUIT or (e.type == KEYUP and e.key == K_ESCAPE):
                done = True
                break
            elif e.type == KEYUP and e.key in (K_PAUSE, K_p):
                paused = not paused
            elif e.type == MOUSEBUTTONUP or (e.type == KEYUP and
                    e.key in (K_UP, K_RETURN, K_SPACE)):
                bird.msec_to_climb = Bird.CLIMB_DURATION

        if paused:
            continue  # don't draw anything

        # check for collisions
        pipe_collision = any(p.collides_with(bird) for p in pipes)
        circle_collisions = [c for c in circles if c.collides_with(bird)]
        
        # Handle circle collisions
        current_time = pygame.time.get_ticks()
        for circle in circle_collisions:
            if circle.type == "red":
                bird.red_effect_end = current_time + Bird.RED_EFFECT_DURATION
            elif circle.type == "orange":
                bird.orange_effect_end = current_time + Bird.ORANGE_EFFECT_DURATION
            else:  # yellow
                done = True
                break
            
        if pipe_collision or 0 >= bird.y or bird.y >= WIN_HEIGHT - Bird.HEIGHT:
            done = True

        for x in (0, WIN_WIDTH / 2):
            display_surface.blit(images['background'], (x, 0))

        while pipes and not pipes[0].visible:
            pipes.popleft()

        for p in pipes:
            p.update()
            display_surface.blit(p.image, p.rect)

        # Update and draw circles
        while circles and not circles[0].visible:
            circles.popleft()

        for circle in circles:
            circle.update()
            display_surface.blit(circle.image, circle.rect)

        bird.update()
        display_surface.blit(bird.image, bird.rect)

        # update and display score
        for p in pipes:
            if p.x + PipePair.WIDTH < bird.x and not p.score_counted:
                score += 1
                p.score_counted = True

        # Count score for circles
        for circle in circles:
            if circle.x + Circle.WIDTH < bird.x and not circle.score_counted:
                score += 1
                circle.score_counted = True

        score_surface = score_font.render(str(score), True, (255, 255, 255))
        score_x = WIN_WIDTH/2 - score_surface.get_width()/2
        display_surface.blit(score_surface, (score_x, PipePair.PIECE_HEIGHT))

        # Display effect status
        current_time = pygame.time.get_ticks()
        if current_time < bird.red_effect_end:
            effect_text = score_font.render("Speed Reduced!", True, (255, 0, 0))
            display_surface.blit(effect_text, (10, PipePair.PIECE_HEIGHT + 30))
        if current_time < bird.orange_effect_end:
            effect_text = score_font.render("Increased Gravity!", True, (255, 165, 0))
            display_surface.blit(effect_text, (10, PipePair.PIECE_HEIGHT + 60))

        pygame.display.flip()
        frame_clock += 1
    print('Game over! Score: %i' % score)
    pygame.quit()


if __name__ == '__main__':
    # If this module had been imported, __name__ would be 'flappybird'.
    # It was executed (e.g. by double-clicking the file), so call main.
    main()
