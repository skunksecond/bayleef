import os

import pygame

from ui.layout import FOOTER, HEADER, MAIN, NAV
from ui.screen import Screen
from ui.set_screen import set_screen
from ui.theme import THEME
from ui.widgets import Button


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def theme_color(name):
    return pygame.Color(THEME[name])


def blend(color_a, color_b, factor):
    return tuple(
        int(color_a[index] + (color_b[index] - color_a[index]) * factor)
        for index in range(3)
    )


class SettingsScreen(Screen):
    SECTIONS = ("Network", "Display", "Power", "System")

    def __init__(self):
        self.selected_section = 0
        self.selected_setting = 0

        self.wifi_enabled = True
        self.hotspot_enabled = False
        self.brightness = 70
        self.blank_timeout = 5
        self.low_power_mode = False

        self.title_font = pygame.font.SysFont("Consolas", 27, bold=True)
        self.section_font = pygame.font.SysFont("Consolas", 20, bold=True)
        self.body_font = pygame.font.SysFont("Consolas", 17)
        self.small_font = pygame.font.SysFont("Consolas", 14)
        self.tiny_font = pygame.font.SysFont("Consolas", 12)

        primary = theme_color("primary")
        nav = theme_color("nav")
        outline = theme_color("outline")
        text = theme_color("text")
        self.text_color = text
        self.subtle_text = blend(text[:3], primary[:3], 0.38)
        self.panel_bg = blend(primary[:3], (255, 255, 255), 0.10)
        self.row_bg = blend(nav[:3], (255, 255, 255), 0.10)
        self.border = blend(outline[:3], (255, 255, 255), 0.24)
        self.highlight = theme_color("button_select")

        self.back_button = Button(
            pygame.Rect(HEADER.right - 150, HEADER.y + 8, 136, 34),
            "Main Menu",
            callback=self._return_to_menu,
            font=self.small_font,
            bg_color=self.row_bg,
            fg_color=self.text_color,
            selected_color=self.highlight,
            padding_x=8,
            padding_y=6,
        )

    def update(self):
        pass

    def handle_event(self, event):
        self.back_button.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._return_to_menu()
            elif event.key == pygame.K_UP:
                self.selected_section = (self.selected_section - 1) % len(self.SECTIONS)
                self.selected_setting = 0
            elif event.key == pygame.K_DOWN:
                self.selected_section = (self.selected_section + 1) % len(self.SECTIONS)
                self.selected_setting = 0
            elif event.key == pygame.K_TAB:
                count = len(self._settings())
                self.selected_setting = (self.selected_setting + 1) % count
            elif event.key == pygame.K_LEFT:
                self._change_selected(-1)
            elif event.key == pygame.K_RIGHT:
                self._change_selected(1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_selected()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, rect in enumerate(self._section_rects()):
                if rect.collidepoint(event.pos):
                    self.selected_section = index
                    self.selected_setting = 0
                    return

            for index, rect in enumerate(self._setting_rects()):
                if rect.collidepoint(event.pos):
                    self.selected_setting = index
                    self._activate_selected()
                    return

    def draw(self, surface):
        self._draw_header(surface)
        self._draw_sections(surface)
        self._draw_settings(surface)

        hint = self.tiny_font.render(
            "Up/Down section  |  Tab setting  |  Left/Right adjust  |  Esc back",
            True,
            self.subtle_text,
        )
        surface.blit(hint, (FOOTER.x + 12, FOOTER.y + 13))

    def _draw_header(self, surface):
        logo_path = os.path.join(SCRIPT_DIR, "logo", THEME["logo"])
        if os.path.exists(logo_path):
            logo = pygame.image.load(logo_path)
            logo = pygame.transform.smoothscale(logo, (162, 50))
            surface.blit(logo, (HEADER.left + 14, HEADER.top))

        title = self.section_font.render("Device Settings", True, self.text_color)
        surface.blit(title, (HEADER.left + 200, HEADER.top + 14))
        self.back_button.draw(surface)

    def _draw_sections(self, surface):
        heading = self.small_font.render("SETTINGS", True, self.subtle_text)
        surface.blit(heading, (NAV.x + 18, NAV.y + 18))

        descriptions = {
            "Network": "Wi-Fi and hotspot",
            "Display": "Screen and timeout",
            "Power": "Battery and power",
            "System": "Device information",
        }

        for index, (name, rect) in enumerate(zip(self.SECTIONS, self._section_rects())):
            selected = index == self.selected_section
            fill = self.highlight if selected else self.row_bg
            border = self.highlight if selected else self.border
            pygame.draw.rect(surface, fill, rect, border_radius=7)
            pygame.draw.rect(surface, border, rect, 2, border_radius=7)

            title = self.body_font.render(name, True, self.text_color)
            detail = self.tiny_font.render(descriptions[name], True, self.text_color if selected else self.subtle_text)
            surface.blit(title, (rect.x + 12, rect.y + 8))
            surface.blit(detail, (rect.x + 12, rect.y + 31))

    def _draw_settings(self, surface):
        content_rect = pygame.Rect(MAIN.x + 12, MAIN.y + 12, MAIN.width - 24, MAIN.height - 24)
        pygame.draw.rect(surface, self.panel_bg, content_rect, border_radius=9)
        pygame.draw.rect(surface, self.border, content_rect, 2, border_radius=9)

        section = self.SECTIONS[self.selected_section]
        title = self.title_font.render(section, True, self.text_color)
        surface.blit(title, (content_rect.x + 18, content_rect.y + 14))

        badge = self.tiny_font.render("PLACEHOLDER DATA", True, self.text_color)
        badge_rect = badge.get_rect(topright=(content_rect.right - 14, content_rect.y + 20))
        badge_bg = badge_rect.inflate(14, 8)
        pygame.draw.rect(surface, self.row_bg, badge_bg, border_radius=5)
        pygame.draw.rect(surface, self.border, badge_bg, 1, border_radius=5)
        surface.blit(badge, badge_rect)

        for index, (setting, rect) in enumerate(zip(self._settings(), self._setting_rects())):
            selected = index == self.selected_setting
            fill = blend(self.row_bg, self.highlight[:3], 0.18) if selected else self.row_bg
            border = self.highlight if selected else self.border
            pygame.draw.rect(surface, fill, rect, border_radius=7)
            pygame.draw.rect(surface, border, rect, 2 if selected else 1, border_radius=7)

            label = self.body_font.render(setting["label"], True, self.text_color)
            detail = self.small_font.render(setting["detail"], True, self.subtle_text)
            surface.blit(label, (rect.x + 12, rect.y + 8))
            surface.blit(detail, (rect.x + 12, rect.y + 32))

            value = self.body_font.render(setting["value"], True, self.text_color)
            value_rect = value.get_rect(midright=(rect.right - 14, rect.centery))
            surface.blit(value, value_rect)

            if setting["kind"] == "slider":
                self._draw_slider(surface, rect, setting["percent"])

    def _draw_slider(self, surface, rect, percent):
        track = pygame.Rect(rect.right - 158, rect.bottom - 13, 142, 5)
        pygame.draw.rect(surface, self.border, track, border_radius=3)
        filled = track.copy()
        filled.width = int(track.width * percent / 100)
        pygame.draw.rect(surface, self.highlight, filled, border_radius=3)

    def _settings(self):
        section = self.SECTIONS[self.selected_section]
        if section == "Network":
            return [
                self._item("Wi-Fi", "Wireless radio status", "On" if self.wifi_enabled else "Off", "toggle"),
                self._item("Network", "Connected access point", "BayleefNet", "info"),
                self._item("IP address", "Local network address", "192.168.1.42", "info"),
                self._item("Hotspot", "Share a setup network", "On" if self.hotspot_enabled else "Off", "toggle"),
            ]
        if section == "Display":
            return [
                self._item("Brightness", "LCD backlight level", f"{self.brightness}%", "slider", self.brightness),
                self._item("Screen blank", "Turn display off when idle", f"{self.blank_timeout} min", "choice"),
                self._item("Rotation", "Display orientation", "Landscape", "info"),
                self._item("Night mode", "Reduce brightness after sunset", "Off", "info"),
            ]
        if section == "Power":
            return [
                self._item("Battery", "UPS or battery HAT status", "Not detected", "info"),
                self._item("Charge", "Estimated remaining capacity", "--%", "info"),
                self._item("Low power mode", "Reduce background activity", "On" if self.low_power_mode else "Off", "toggle"),
                self._item("Auto shutdown", "Shut down at low charge", "10%", "info"),
            ]
        return [
            self._item("Hostname", "Name used on the network", "bayleef-pi", "info"),
            self._item("CPU temperature", "Current processor temperature", "42.0 C", "info"),
            self._item("Storage", "microSD space available", "11.8 GB free", "info"),
            self._item("Software", "Installed application version", "v0.1.0", "info"),
        ]

    def _item(self, label, detail, value, kind, percent=0):
        return {
            "label": label,
            "detail": detail,
            "value": value,
            "kind": kind,
            "percent": percent,
        }

    def _change_selected(self, delta):
        section = self.SECTIONS[self.selected_section]
        setting = self._settings()[self.selected_setting]
        if setting["kind"] == "toggle":
            self._activate_selected()
        elif section == "Display" and setting["label"] == "Brightness":
            self.brightness = max(10, min(100, self.brightness + delta * 10))
        elif section == "Display" and setting["label"] == "Screen blank":
            options = [1, 2, 5, 10, 15, 30]
            index = options.index(self.blank_timeout)
            self.blank_timeout = options[(index + delta) % len(options)]

    def _activate_selected(self):
        section = self.SECTIONS[self.selected_section]
        label = self._settings()[self.selected_setting]["label"]
        if section == "Network" and label == "Wi-Fi":
            self.wifi_enabled = not self.wifi_enabled
        elif section == "Network" and label == "Hotspot":
            self.hotspot_enabled = not self.hotspot_enabled
        elif section == "Power" and label == "Low power mode":
            self.low_power_mode = not self.low_power_mode

    def _section_rects(self):
        return [
            pygame.Rect(NAV.x + 10, NAV.y + 46 + index * 76, NAV.width - 20, 60)
            for index in range(len(self.SECTIONS))
        ]

    def _setting_rects(self):
        return [
            pygame.Rect(MAIN.x + 30, MAIN.y + 64 + index * 72, MAIN.width - 60, 60)
            for index in range(len(self._settings()))
        ]

    def _return_to_menu(self):
        from ui.menu import MainMenu

        set_screen(MainMenu())
