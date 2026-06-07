import pygame
# placeholder text, keyboard handling, cursor blinking, support for no mouse
class TextBox:
    def __init__(
        self,
        rect,
        text="",
        placeholder="",
        font=None,
        bg_color=(30, 30, 30),
        fg_color=(255, 255, 255),
        border_color=(150, 150, 150),
        active_color=(100, 100, 255),
        max_length=128,
    ):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.placeholder = placeholder
        self.font = font or pygame.font.SysFont(None, 24)
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.border_color = border_color
        self.active_color = active_color
        self.max_length = max_length
        self.active = False
        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_interval = 500

    def update(self, delta_ms: int):
        if not self.active:
            self.cursor_visible = False
            return

        self.cursor_timer += delta_ms
        if self.cursor_timer >= self.cursor_interval:
            self.cursor_timer -= self.cursor_interval
            self.cursor_visible = not self.cursor_visible

    def draw(self, surface):
        pygame.draw.rect(surface, self.bg_color, self.rect, border_radius=4)
        border = self.active_color if self.active else self.border_color
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=4)

        display_text = self.text if self.text else self.placeholder
        text_color = self.fg_color if self.text else (180, 180, 180)
        text_surf = self.font.render(display_text, True, text_color)
        surface.blit(text_surf, (self.rect.x + 10, self.rect.y + (self.rect.height - text_surf.get_height()) // 2))

        if self.active and self.cursor_visible:
            cursor_x = self.rect.x + 10 + text_surf.get_width() + 2
            cursor_y = self.rect.y + 8
            cursor_height = self.rect.height - 16
            pygame.draw.rect(surface, self.fg_color, pygame.Rect(cursor_x, cursor_y, 2, cursor_height))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                return True

            if event.key == pygame.K_RETURN:
                return True

            if event.unicode and len(self.text) < self.max_length:
                self.text += event.unicode
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            return self.active

        return False

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False
