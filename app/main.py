import os
import pygame
from ui.menu import MainMenu
from ui.layout import *

script_dir = os.path.dirname(os.path.abspath(__file__))

WIDTH = 800
HEIGHT = 480

current_screen = None


def main():
    global current_screen

    pygame.init()

    icon_path = os.path.join(script_dir, "ui", "logo", "bayleef icon.png")
    icon_image = pygame.image.load(icon_path)

    pygame.display.set_icon(icon_image)

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Bayleef")

    clock = pygame.time.Clock()
    current_screen = MainMenu()

    run = True

    try:
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
    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
