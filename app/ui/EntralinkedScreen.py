import pygame
from ui.screen import Screen
from ui.set_screen import set_screen
from entralinked import request_exit
from ui.widgets import Button
from ui.layout import MAIN


class EntralinkedScreen(Screen):
    def __init__(self):
        self.done = False
        self.exit_button = Button(
            pygame.Rect(MAIN.right - 150, MAIN.bottom - 70, 140, 44),
            "Back",
            callback=self._exit,
        )
        self.exit_button.set_selected(True)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._exit()
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._exit()

        self.exit_button.handle_event(event)

    def update(self):
        if self.done:
            self._exit()

    def draw(self, surface):
        font = pygame.font.SysFont(None, 28)
        title_font = pygame.font.SysFont(None, 36)

        title = title_font.render("Entralinked", True, (255, 255, 255))
        surface.blit(title, (MAIN.left + 30, MAIN.top + 30))

        lines = [
            "The Entralinked Java app is launching locally.",
            "Press Esc to return to the menu.",
        ]

        y = MAIN.top + 90
        for line in lines:
            text = font.render(line, True, (220, 220, 220))
            surface.blit(text, (MAIN.left + 30, y))
            y += 34

        self.exit_button.draw(surface)

    def _return_to_menu(self):
        if self.done:
            return
        self.done = True
        from ui.menu import MainMenu
        set_screen(MainMenu())

    def _exit(self):
        if self.done:
            return
        self.done = True
        request_exit(self._return_to_menu)
