import pygame

# used for static text rendering

class Label:
    def __init__(self, text, pos, font=None, color=(255, 255, 255), align="topleft"):
        self.text = text
        self.pos = pos
        self.font = font or pygame.font.SysFont(None, 24)
        self.color = color
        self.align = align

    def draw(self, surface):
        text_surface = self.font.render(self.text, True, self.color)
        rect = text_surface.get_rect(**{self.align: self.pos})
        surface.blit(text_surface, rect)
