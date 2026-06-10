import os
import pygame
from ui.screen import Screen
from ui.layout import *
from ui.widgets import Button
from eontimer import start_eontimer
from entralinked import start_entralinked
from ui.set_screen import *

script_dir = os.path.dirname(os.path.abspath(__file__))

class MainMenu(Screen):
    def __init__(self):
        self.buttons = []
        self.selected_index = 0
        self._build_buttons()

    def _build_buttons(self):
        labels = ["Pokedex", "Entralinked", "PKHex", "EonTimer", "Settings"]
        button_width = 180
        button_height = 56
        spacing = 18
        total_height = len(labels) * button_height + (len(labels) - 1) * spacing
        start_x = NAV.x + (NAV.width - button_width) // 2
        start_y = NAV.y + (NAV.height - total_height) // 2

        for index, label in enumerate(labels):
            rect = pygame.Rect(
                start_x,
                start_y + index * (button_height + spacing),
                button_width,
                button_height,
            )

            button = Button(rect, label)

            if label == "Entralinked":
                button.callback = self._open_entralinked
            elif label == "EonTimer":
                button.callback = self._open_eontimer
            
            self.buttons.append(button)

        if self.buttons:
            self.buttons[0].set_selected(True)

    def update(self):
        pass

    def draw(self, surface):
        font = pygame.font.SysFont(None, 36)
        header_img = pygame.image.load(script_dir + "/logo/" + THEME["logo"])
        header_img_resized = pygame.transform.scale(header_img, (162, 50))
        surface.blit(header_img_resized, (HEADER.left + 20, 1))

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

    def _open_entralinked(self):
        print("Opening Entralinked")
        from ui.EntralinkedScreen import EntralinkedScreen
        screen = EntralinkedScreen()
        set_screen(screen)
        start_entralinked(exit_callback=screen._return_to_menu)

    def _open_eontimer(self):
        print("Opening EonTimer")
        from ui.EonTimerScreen import EonTimerScreen
        screen = EonTimerScreen()
        set_screen(screen)
        start_eontimer(exit_callback=screen._return_to_menu)

    def _activate_button(self, button):
        print(f"Selected: {button.text}")
        if button.callback:
            button.callback()
