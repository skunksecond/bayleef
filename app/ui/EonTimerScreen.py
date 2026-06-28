import pygame
from ui.screen import Screen
from ui.set_screen import set_screen
from eontimer import get_status_text, request_exit
from ui.widgets import Button
from ui.layout import HEADER, MAIN
from ui.theme import THEME


def _fit_text(text, font, width):
    if font.size(text)[0] <= width:
        return text
    suffix = "..."
    while text and font.size(text + suffix)[0] > width:
        text = text[:-1]
    return text + suffix


class EonTimerScreen(Screen):
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
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                self._exit()

        self.exit_button.handle_event(event)

    def update(self):
        if self.done:
            self._exit()

    def draw(self, surface):
        font = pygame.font.SysFont(None, 28)
        title_font = pygame.font.SysFont(None, 36)

        text_color = pygame.Color(THEME["text"])
        title = title_font.render("EonTimer", True, text_color)
        surface.blit(title, (MAIN.left + 30, MAIN.top + 30))

        lines = [
            "EonTimer opens in a local Chromium window above Bayleef.",
            "Close that window or press Esc here to return to the menu.",
        ]

        y = MAIN.top + 90
        for line in lines:
            text = font.render(line, True, text_color)
            surface.blit(text, (MAIN.left + 30, y))
            y += 34

        status_text = _fit_text(get_status_text(), font, MAIN.width - 60)
        status = font.render(status_text, True, pygame.Color(THEME["button_select"]))
        surface.blit(status, (MAIN.left + 30, y + 18))

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
