import pygame
from ui.screen import Screen
from ui.set_screen import set_screen
from entralinked import get_status_lines, request_exit
from ui.widgets import Button
from ui.layout import HEADER, MAIN
from ui.theme import THEME


def _wrap_text(text, font, width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and font.size(candidate)[0] > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


class EntralinkedScreen(Screen):
    target_fps = 2

    def __init__(self):
        self.done = False
        self.font = pygame.font.SysFont(None, 28)
        self.title_font = pygame.font.SysFont(None, 36)
        self.small_font = pygame.font.SysFont(None, 22)
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
        text_color = pygame.Color(THEME["text"])
        title = self.title_font.render("Entralinked", True, text_color)
        surface.blit(title, (MAIN.left + 30, MAIN.top + 24))

        lines = [
            "Entralinked opens as its own window above Bayleef.",
            "Bayleef will continue running in the background.",
            "Use the window close button or press Esc here to close it.",
        ]

        y = MAIN.top + 84
        for line in lines:
            text = self.font.render(line, True, text_color)
            surface.blit(text, (MAIN.left + 30, y))
            y += 34

        status_label = self.small_font.render("Launch log", True, text_color)
        surface.blit(status_label, (MAIN.left + 30, y + 8))

        log_rect = pygame.Rect(MAIN.left + 30, y + 34, MAIN.width - 60, MAIN.bottom - y - 48)
        previous_clip = surface.get_clip()
        surface.set_clip(log_rect)
        log_y = log_rect.top
        status_color = pygame.Color(THEME["button_select"])
        wrapped_lines = []
        for status in get_status_lines():
            wrapped_lines.extend(_wrap_text(status, self.small_font, log_rect.width))
        for line in wrapped_lines[-7:]:
            status_text = self.small_font.render(line, True, status_color)
            surface.blit(status_text, (log_rect.left, log_y))
            log_y += self.small_font.get_linesize()
        surface.set_clip(previous_clip)

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
