import pygame

# boxed content

class Panel:
    def __init__(self, rect, title=None, font=None, bg_color=(22, 22, 22), border_color=(120, 120, 120), title_color=(230, 230, 230)):
        self.rect = pygame.Rect(rect)
        self.title = title
        self.font = font or pygame.font.SysFont(None, 22)
        self.bg_color = bg_color
        self.border_color = border_color
        self.title_color = title_color

    def draw(self, surface):
        pygame.draw.rect(surface, self.bg_color, self.rect, border_radius=8)
        pygame.draw.rect(surface, self.border_color, self.rect, 2, border_radius=8)

        if self.title:
            title_surface = self.font.render(self.title, True, self.title_color)
            title_rect = title_surface.get_rect(topleft=(self.rect.x + 12, self.rect.y + 10))
            surface.blit(title_surface, title_rect)
