import pygame
from ui.screen import Screen

class MainMenu(Screen):

    def draw(self, surface):

        font = pygame.font.SysFont(None, 50)

        text = font.render("PokeHelper", True, (255, 255, 255))

        surface.blit(text, (250, 50))