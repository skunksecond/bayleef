import pygame
from ui.clock import draw_clock
from ui.theme import THEME


HEADER = pygame.Rect(0, 0, 800, 50)
NAV = pygame.Rect(0, 50, 200, 390)
MAIN = pygame.Rect(200, 50, 600, 390)
FOOTER = pygame.Rect(0, 440, 800, 40)


def draw_layout(surface):
    pygame.draw.rect(surface, THEME["header"], HEADER)
    pygame.draw.rect(surface, THEME["nav"], NAV)
    pygame.draw.rect(surface, THEME["primary"], MAIN)
    pygame.draw.rect(surface, THEME["header"], FOOTER)

    pygame.draw.rect(surface, THEME["outline"], HEADER, 1)
    pygame.draw.rect(surface, THEME["outline"], NAV, 1)
    pygame.draw.rect(surface, THEME["outline"], MAIN, 1)
    pygame.draw.rect(surface, THEME["outline"], FOOTER, 1)

    clock_rect = pygame.Rect(FOOTER.right - 44, FOOTER.top + 2, 34, 34)
    draw_clock(surface, rect=clock_rect)