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

    display_flags = pygame.NOFRAME if os.environ.get("SDL_VIDEODRIVER") == "x11" else 0
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), display_flags, vsync=1)
    except pygame.error:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), display_flags)
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

            keys = pygame.key.get_pressed()

            if (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]) and \
                keys[pygame.K_ESCAPE]:
                run = False

            current_screen.update()

            screen.fill((20, 20, 20))

            draw_layout(screen)
            current_screen.draw(screen)

            pygame.display.flip()
            clock.tick(max(1, getattr(current_screen, "target_fps", 10)))
    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
