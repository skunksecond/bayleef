import pygame
from ui.screen import Screen
from ui.set_screen import set_screen
from entralinked import get_status_text, request_exit
from ui.widgets import Button
from ui.layout import HEADER, MAIN


class EntralinkedScreen(Screen):
    def __init__(self):
        self.done = False
        self.exit_button = Button(
            pygame.Rect(HEADER.right - 150, HEADER.y + 8, 140, 34),
            "Exit",
            callback=self._exit,
            font=pygame.font.SysFont(None, 22),
            padding_y=8,
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
        small_font = pygame.font.SysFont(None, 22)

        title = title_font.render("Entralinked", True, (255, 255, 255))
        surface.blit(title, (MAIN.left + 30, MAIN.top + 24))

        lines = [
            "Entralinked opens as its own window above Bayleef.",
            "Bayleef will continue running in the background.",
            "Use the window close button or press Esc here to close it.",
        ]

        y = MAIN.top + 84
        for line in lines:
            text = font.render(line, True, (220, 220, 220))
            surface.blit(text, (MAIN.left + 30, y))
            y += 34

        status = get_status_text()
        status_label = small_font.render("Status:", True, (220, 220, 220))
        status_text = small_font.render(status, True, (200, 255, 200))
        surface.blit(status_label, (MAIN.left + 30, y + 10))
        surface.blit(status_text, (MAIN.left + 100, y + 10))

        self.exit_button.draw(surface)

    def _return_to_menu(self):
        self.done = True
        from ui.menu import MainMenu
        set_screen(MainMenu())

    def _exit(self):
        if self.done:
            return
        self.done = True
        request_exit(self._return_to_menu)
