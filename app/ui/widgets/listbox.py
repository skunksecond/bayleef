import pygame

# selectable items, scroll tracking, callback on enter

class ListBox:
    def __init__(
        self,
        rect,
        items=None,
        font=None,
        selected_index=0,
        item_height=32,
        bg_color=(25, 25, 25),
        fg_color=(255, 255, 255),
        selected_bg=(70, 70, 120),
        selected_fg=(255, 255, 255),
        border_color=(150, 150, 150),
        callback=None,
    ):
        self.rect = pygame.Rect(rect)
        self.items = list(items or [])
        self.font = font or pygame.font.SysFont(None, 22)
        self.selected_index = max(0, min(selected_index, len(self.items) - 1)) if self.items else 0
        self.item_height = item_height
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.selected_bg = selected_bg
        self.selected_fg = selected_fg
        self.border_color = border_color
        self.scroll = 0
        self.callback = callback

    @property
    def visible_count(self):
        return max(1, self.rect.height // self.item_height)

    def draw(self, surface):
        pygame.draw.rect(surface, self.bg_color, self.rect, border_radius=6)
        pygame.draw.rect(surface, self.border_color, self.rect, 2, border_radius=6)

        top = self.rect.y + 4
        start = self.scroll
        end = min(start + self.visible_count, len(self.items))

        for index in range(start, end):
            item_rect = pygame.Rect(self.rect.x + 4, top, self.rect.width - 8, self.item_height - 4)
            text = str(self.items[index])

            if index == self.selected_index:
                pygame.draw.rect(surface, self.selected_bg, item_rect, border_radius=4)
                color = self.selected_fg
            else:
                color = self.fg_color

            text_surf = self.font.render(text, True, color)
            surface.blit(text_surf, (item_rect.x + 8, item_rect.y + (item_rect.height - text_surf.get_height()) // 2))
            top += self.item_height

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected_index = min(self.selected_index + 1, len(self.items) - 1)
                self._scroll_to_selected()
                return True
            if event.key == pygame.K_UP:
                self.selected_index = max(self.selected_index - 1, 0)
                self._scroll_to_selected()
                return True
            if event.key == pygame.K_RETURN and self.callback:
                self.callback(self.selected_index)
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                relative_y = event.pos[1] - self.rect.y
                index = self.scroll + relative_y // self.item_height
                if 0 <= index < len(self.items):
                    self.selected_index = index
                    self._scroll_to_selected()
                    return True

        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll = max(0, min(self.scroll - event.y, max(0, len(self.items) - self.visible_count)))
                return True

        return False

    def _scroll_to_selected(self):
        if self.selected_index < self.scroll:
            self.scroll = self.selected_index
        elif self.selected_index >= self.scroll + self.visible_count:
            self.scroll = self.selected_index - self.visible_count + 1

    def set_items(self, items):
        self.items = list(items)
        self.selected_index = min(self.selected_index, len(self.items) - 1) if self.items else 0
        self.scroll = max(0, min(self.scroll, max(0, len(self.items) - self.visible_count)))
