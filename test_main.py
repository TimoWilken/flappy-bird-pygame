import unittest
import pygame
from flappybird import main, load_images, Bird, PipePair
from pygame.locals import *
from collections import deque

class TestGameOverScreen(unittest.TestCase):

    def setUp(self):
        pygame.init()
        self.display_surface = pygame.display.set_mode((568, 512))
        self.score_font = pygame.font.SysFont(None, 32, bold=True)
        self.images = load_images()
        self.bird = Bird(50, 256, 2,
                (self.images['bird-wingup'], self.images['bird-wingdown']))

        self.pipes = deque()
        self.frame_clock = 0
        self.score = 0
        self.done = False
        self.paused = False
        self.game_over = False
    
    def test_game_over_screen_displayed(self):
        # Simulate a collision to trigger game over
        self.bird.y = 0
        self.game_over = True

        # Check if game over screen is displayed
        self.assertTrue(self.game_over)

        # Check if score is displayed
        self.score_surface = self.score_font.render(str(self.score), True, (255, 255, 255))
        score_x = 568/2 - self.score_surface.get_width()/2
        self.display_surface.blit(self.score_surface, (score_x, 32))
        pygame.display.flip()
        self.assertTrue(self.game_over)

        # Check if play again is displayed
        play_again_text = self.score_font.render('Play Again?', True, (255, 255, 255))
        self.assertTrue(play_again_text)
        pygame.display.flip()

        #Check if the game is displayed
        pygame.display.flip()
        
    def test_game_can_be_restarted(self):
        
        self.game_over = True
        for event in pygame.event.get():
          if event.type == MOUSEBUTTONUP:
            self.game_over = False

        #Check if the game starts again.
        self.assertFalse(self.game_over)
