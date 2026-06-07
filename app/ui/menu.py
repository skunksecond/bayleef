import pygame
from ui.screen import Screen
from ui.layout import *
from ui.widgets import Button


class MainMenu(Screen):
    def __init__(self):
        self.buttons = []
        self.selected_index = 0
        self._build_buttons()

    def _build_buttons(self):
        labels = ["Pokedex", "Entralinked", "PKHex", "EonTimer", "Settings"]
        button_width = 180
        button_height = 56
        start_x = HEADER.left + 14
        start_y = HEADER.bottom + 24
        spacing = 18

        for index, label in enumerate(labels):
            rect = pygame.Rect(
                start_x,
                start_y + index * (button_height + spacing),
                button_width,
                button_height,
            )
            button = Button(rect, label)
            self.buttons.append(button)

        if self.buttons:
            self.buttons[0].set_selected(True)

    def update(self):
        pass

    def draw(self, surface):
        font = pygame.font.SysFont(None, 50)
        title = font.render("PokeHelper", True, (255, 255, 255))
        surface.blit(title, (HEADER.left + 20, 10))

        for button in self.buttons:
            button.draw(surface)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_DOWN:
            self._move_selection(1)
            return
        if event.key == pygame.K_UP:
            self._move_selection(-1)
            return
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            selected_button = self.buttons[self.selected_index]
            self._activate_button(selected_button)
            return

    def _move_selection(self, delta):
        if not self.buttons:
            return
        self.buttons[self.selected_index].set_selected(False)
        self.selected_index = (self.selected_index + delta) % len(self.buttons)
        self.buttons[self.selected_index].set_selected(True)

    def _activate_button(self, button):
        print(f"Selected: {button.text}")
