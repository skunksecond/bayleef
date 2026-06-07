import pygame
from ui.menu import MainMenu

# create screen
pygame.init()

WIDTH = 800
HEIGHT =  480

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("PokeHelper")

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

    current_screen.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
