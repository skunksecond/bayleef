import pygame
from ui.theme import THEME

class Button:
    def __init__(
        self,
        rect,
        text,
        callback=None,
        font=None,
        bg_color=THEME["button_bg"],
        fg_color=THEME["button_fg"],
        selected_color=THEME["button_select"],
        padding_x=16,
        padding_y=12,
    ):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.font = font or pygame.font.SysFont(None, 24)
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.selected_color = selected_color
        self.padding_x = padding_x
        self.padding_y = padding_y
        self.selected = False

        text_surface = self.font.render(self.text, True, self.fg_color)
        min_width = text_surface.get_width() + self.padding_x * 2
        min_height = text_surface.get_height() + self.padding_y * 2
        if self.rect.width < min_width:
            self.rect.width = min_width
        if self.rect.height < min_height:
            self.rect.height = min_height

    def draw(self, surface):
        color = self.selected_color if self.selected else self.bg_color
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, (200, 200, 200), self.rect, 2)

        text_surface = self.font.render(self.text, True, self.fg_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and self.selected:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.callback:
                    self.callback()
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True

        return False

    def set_selected(self, selected: bool):
        self.selected = selected
