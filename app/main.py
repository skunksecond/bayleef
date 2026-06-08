import os
import pygame
from ui.menu import MainMenu
from ui.layout import *

script_dir = os.path.dirname(os.path.abspath(__file__))

pygame.init()
WIDTH = 800
HEIGHT =  480 
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Bayleef")

clock = pygame.time.Clock()

current_screen = MainMenu()

run = True

while run:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        current_screen.handle_event(event)

    current_screen.update()

    screen.fill((20, 20, 20))

    draw_layout(screen)
    current_screen.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
