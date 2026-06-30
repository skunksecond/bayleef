import math
from pathlib import Path
import os
import pygame

from eontimer import Console, DEFAULT_VALUES, NativeEonTimer, TimerMode
from ui.layout import HEADER, MAIN, NAV
from ui.screen import Screen
from ui.set_screen import set_screen
from ui.theme import THEME
from ui.widgets import Button, TextBox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

FIELD_LABELS = {
    "pre_timer": "Pre-timer (ms)",
    "target_frame": "Target frame",
    "gen3_calibration": "Calibration (ms)",
    "frame_hit": "Frame hit",
    "target_delay": "Target delay",
    "target_second": "Target second",
    "calibrated_delay": "Calibrated delay",
    "calibrated_second": "Calibrated second",
    "calibration": "Calibration",
    "entralink_calibration": "Entralink calibration",
    "target_advances": "Target advances",
    "frame_calibration": "Frame calibration",
    "delay_hit": "Delay hit",
    "second_hit": "Second hit",
    "advances_hit": "Advances hit",
}

MODE_FIELDS = {
    TimerMode.GEN3_STANDARD: ("pre_timer", "target_frame", "gen3_calibration", "frame_hit"),
    TimerMode.GEN3_VARIABLE: ("pre_timer", "target_frame", "gen3_calibration", "frame_hit"),
    TimerMode.GEN4: (
        "calibrated_delay", "calibrated_second", "target_delay", "target_second", "delay_hit"
    ),
    TimerMode.GEN5_STANDARD: ("target_second", "calibration", "second_hit"),
    TimerMode.GEN5_CGEAR: ("target_delay", "target_second", "calibration", "delay_hit"),
    TimerMode.GEN5_ENTRALINK: (
        "target_delay", "target_second", "calibration", "entralink_calibration",
        "delay_hit", "second_hit",
    ),
    TimerMode.GEN5_ENTRALINK_PLUS: (
        "target_delay", "target_second", "target_advances", "calibration",
        "entralink_calibration", "frame_calibration", "delay_hit", "second_hit", "advances_hit",
    ),
}

GENERATION_MODES = {
    "Gen 3": (TimerMode.GEN3_STANDARD, TimerMode.GEN3_VARIABLE),
    "Gen 4": (TimerMode.GEN4,),
    "Gen 5": (
        TimerMode.GEN5_STANDARD,
        TimerMode.GEN5_CGEAR,
        TimerMode.GEN5_ENTRALINK,
        TimerMode.GEN5_ENTRALINK_PLUS,
    ),
}

OPTIONAL_FIELDS = {"frame_hit", "delay_hit", "second_hit", "advances_hit"}


class EonTimerScreen(Screen):
    target_fps = 60

    def __init__(self):
        self.timer = NativeEonTimer()
        self.mode = TimerMode.GEN5_STANDARD
        self._generation_values = {
            generation: dict(DEFAULT_VALUES) for generation in GENERATION_MODES
        }
        self._generation_values["Gen 4"]["target_delay"] = 600
        self.values = self._generation_values[self.mode.generation]
        self.fields = {}
        self.focus_index = 0
        self.status = "Set a target, then start the timer."
        self.flash_until = 0
        self._was_completed = False

        self.title_font = pygame.font.SysFont("Consolas", 26, bold=True)
        self.timer_font = pygame.font.SysFont("Consolas", 58, bold=True)
        self.body_font = pygame.font.SysFont("Consolas", 16)
        self.small_font = pygame.font.SysFont("Consolas", 13)
        self.button_font = pygame.font.SysFont("Consolas", 15, bold=True)

        
        logo_path = os.path.join(SCRIPT_DIR, "logo", THEME["logo"])
        self.header_image = None
        if os.path.exists(logo_path):
            logo = pygame.image.load(logo_path).convert_alpha()
            self.header_image = pygame.transform.smoothscale(logo, (162, 50))

        self.back_button = Button(
            pygame.Rect(HEADER.right - 130, HEADER.y + 8, 116, 34),
            "Main Menu", self._return_to_menu, self.button_font, padding_y=7,
        )
        self.mode_button = Button(
            pygame.Rect(HEADER.right - 300, HEADER.y + 8, 156, 34),
            self.mode.label, self._cycle_mode, self.button_font, padding_y=7,
        )
        self.generation_buttons = []
        for index, generation in enumerate(GENERATION_MODES):
            button = Button(
                pygame.Rect(NAV.x + 14, NAV.y + 18 + index * 56, NAV.width - 28, 42),
                generation,
                lambda value=generation: self._select_generation(value),
                self.button_font,
                padding_y=8,
            )
            self.generation_buttons.append(button)
        self.console_button = Button(
            pygame.Rect(NAV.x + 14, NAV.y + 210, NAV.width - 28, 42),
            self.timer.console.label, self._cycle_console, self.small_font, padding_y=8,
        )
        self.start_button = Button(
            pygame.Rect(MAIN.right - 260, MAIN.bottom - 56, 114, 38),
            "Start", self._toggle_timer, self.button_font, padding_y=8,
        )
        self.calibrate_button = Button(
            pygame.Rect(MAIN.right - 134, MAIN.bottom - 56, 114, 38),
            "Calibrate", self._calibrate, self.button_font, padding_y=8,
        )
        self.target_button = Button(
            pygame.Rect(MAIN.right - 260, MAIN.bottom - 102, 240, 36),
            "Set variable target", self._set_variable_target, self.button_font, padding_y=7,
        )

        self._sound = self._load_sound()
        self._rebuild_fields()

    def _load_sound(self):
        sound_path = (
            Path(__file__).resolve().parents[1]
            / "third_party" / "EonTimerpython" / "eon_timer" / "resources" / "sounds" / "beep.wav"
        )
        try:
            if pygame.mixer.get_init() and sound_path.is_file():
                return pygame.mixer.Sound(str(sound_path))
        except pygame.error:
            pass
        return None

    def _rebuild_fields(self):
        for name, field in self.fields.items():
            self._store_field(name, field)
        self.fields = {}
        x = MAIN.left + 20
        for index, name in enumerate(MODE_FIELDS[self.mode]):
            y = MAIN.top + 55 + index * 34
            value = self.values.get(name)
            text = "" if value is None else self._format_value(value)
            self.fields[name] = TextBox(
                pygame.Rect(x + 155, y, 125, 27),
                text=text,
                placeholder="optional" if name in OPTIONAL_FIELDS else "0",
                font=self.body_font,
                bg_color=THEME["nav"],
                fg_color=THEME["text"],
                border_color=THEME["outline"],
                active_color=THEME["button_select"],
                max_length=14,
            )
        self.focus_index = min(self.focus_index, max(0, len(self.fields) - 1))
        self._focus_field(self.focus_index)
        self.mode_button.text = self.mode.label
        self._sync_generation_selection()

    @staticmethod
    def _format_value(value):
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    def _store_field(self, name, field):
        text = field.text.strip()
        if not text and name in OPTIONAL_FIELDS:
            self.values[name] = None
            return
        try:
            self.values[name] = float(text) if name in ("gen3_calibration", "frame_calibration") else int(text)
        except ValueError:
            pass

    def _read_values(self):
        parsed = dict(self.values)
        for name, field in self.fields.items():
            text = field.text.strip()
            if not text and name in OPTIONAL_FIELDS:
                parsed[name] = None
                continue
            if not text:
                raise ValueError(f"{FIELD_LABELS[name]} cannot be blank")
            try:
                parsed[name] = float(text) if name in ("gen3_calibration", "frame_calibration") else int(text)
            except ValueError as error:
                raise ValueError(f"{FIELD_LABELS[name]} must be a number") from error
        self.values.update(parsed)
        return parsed

    def handle_event(self, event):
        # These controls are mouse-driven; keyboard operation uses the explicit
        # shortcuts below. This prevents Enter in a TextBox from also activating
        # the visually selected generation button.
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.back_button.handle_event(event)
            self.mode_button.handle_event(event)
            for button in self.generation_buttons:
                button.handle_event(event)
            self.console_button.handle_event(event)
            self.start_button.handle_event(event)
            self.calibrate_button.handle_event(event)
            if self.mode == TimerMode.GEN3_VARIABLE:
                self.target_button.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._return_to_menu()
                return
            if event.key == pygame.K_TAB:
                delta = -1 if event.mod & pygame.KMOD_SHIFT else 1
                self._focus_field((self.focus_index + delta) % len(self.fields))
                return
            if event.key == pygame.K_F5:
                self._toggle_timer()
                return
            if event.key == pygame.K_F6:
                self._calibrate()
                return

        for index, field in enumerate(self.fields.values()):
            was_active = field.active
            if field.handle_event(event):
                if event.type == pygame.MOUSEBUTTONDOWN or not was_active:
                    self._focus_field(index)
                return

    def update(self):
        for field in self.fields.values():
            field.update(17)
        cues = self.timer.update()
        if cues:
            self.flash_until = pygame.time.get_ticks() + 110
            if self._sound is not None:
                for _ in range(cues):
                    self._sound.play()
        if self.timer.completed and not self._was_completed:
            self.status = "Timer complete. Enter your result to calibrate."
        self._was_completed = self.timer.completed
        self.start_button.text = "Stop" if self.timer.running else "Start"

    def draw(self, surface):
        text_color = pygame.Color(THEME["text"])
        highlight = pygame.Color(THEME["button_select"])
        if pygame.time.get_ticks() < self.flash_until:
            pygame.draw.rect(surface, highlight, MAIN)

        if self.header_image is not None:
            surface.blit(self.header_image, (HEADER.left + 14, HEADER.top))
        else:
            title = self.header_font.render("Bayleef", True, self.text_color)
            surface.blit(title, (HEADER.left + 18, HEADER.top + 14))
        
        self.back_button.draw(surface)
        self.mode_button.draw(surface)

        for button in self.generation_buttons:
            button.draw(surface)
        console_label = self.small_font.render("Console / frame rate", True, text_color)
        surface.blit(console_label, (NAV.x + 14, NAV.y + 190))
        self.console_button.draw(surface)
        help_lines = ("Tab: next field", "F5: start / stop", "F6: calibrate", "Esc: main menu")
        for index, line in enumerate(help_lines):
            label = self.small_font.render(line, True, text_color)
            surface.blit(label, (NAV.x + 18, NAV.y + 278 + index * 20))

        subtitle = self.body_font.render(f"{self.mode.generation} / {self.mode.label}", True, highlight)
        surface.blit(subtitle, (MAIN.left + 20, MAIN.top + 20))
        for name, field in self.fields.items():
            label = self.small_font.render(FIELD_LABELS[name], True, text_color)
            surface.blit(label, (MAIN.left + 20, field.rect.y + 6))
            field.draw(surface)

        self._draw_timer(surface, text_color, highlight)

    def _draw_timer(self, surface, text_color, highlight):
        panel = pygame.Rect(MAIN.right - 280, MAIN.top + 55, 260, 210)
        pygame.draw.rect(surface, THEME["nav"], panel, border_radius=8)
        pygame.draw.rect(surface, THEME["outline"], panel, 2, border_radius=8)

        remaining = self.timer.remaining_ms()
        time_text = self._format_time(remaining)
        rendered = self.timer_font.render(time_text, True, text_color)
        surface.blit(rendered, rendered.get_rect(center=(panel.centerx, panel.y + 67)))

        phase_total = len(self.timer.phases) or 1
        phase_number = self.timer.phase_index + 1 if self.timer.phases else 1
        phase_text = self.body_font.render(f"Phase {phase_number} of {phase_total}", True, highlight)
        surface.blit(phase_text, phase_text.get_rect(center=(panel.centerx, panel.y + 113)))

        if self.timer.phases and not math.isinf(self.timer.phases[self.timer.phase_index]):
            duration = self.timer.phases[self.timer.phase_index]
            ratio = 1.0 - min(1.0, remaining / duration)
        else:
            ratio = 0.0
        track = pygame.Rect(panel.x + 20, panel.y + 140, panel.width - 40, 14)
        pygame.draw.rect(surface, THEME["primary"], track, border_radius=5)
        fill = track.copy()
        fill.width = int(track.width * ratio)
        pygame.draw.rect(surface, highlight, fill, border_radius=5)

        status = self.small_font.render(self.status[:39], True, text_color)
        surface.blit(status, status.get_rect(center=(panel.centerx, panel.y + 181)))
        if self.mode == TimerMode.GEN3_VARIABLE:
            self.target_button.draw(surface)
        self.start_button.draw(surface)
        self.calibrate_button.draw(surface)

    @staticmethod
    def _format_time(milliseconds):
        if math.isinf(milliseconds):
            return "--.---"
        milliseconds = max(0, int(milliseconds))
        minutes, remainder = divmod(milliseconds, 60000)
        seconds, millis = divmod(remainder, 1000)
        if minutes:
            return f"{minutes}:{seconds:02d}.{millis:03d}"
        return f"{seconds}.{millis:03d}"

    def _focus_field(self, index):
        if not self.fields:
            return
        self.focus_index = index
        for field_index, field in enumerate(self.fields.values()):
            if field_index == index:
                field.activate()
            else:
                field.deactivate()

    def _select_generation(self, generation):
        if self.timer.running:
            return
        for name, field in self.fields.items():
            self._store_field(name, field)
        self.mode = GENERATION_MODES[generation][0]
        self.values = self._generation_values[generation]
        self.status = f"Selected {generation}."
        self._rebuild_fields()

    def _cycle_mode(self):
        if self.timer.running:
            return
        modes = GENERATION_MODES[self.mode.generation]
        self.mode = modes[(modes.index(self.mode) + 1) % len(modes)]
        self.status = f"Mode: {self.mode.label}."
        self._rebuild_fields()

    def _cycle_console(self):
        if self.timer.running:
            return
        consoles = list(Console)
        self.timer.console = consoles[(consoles.index(self.timer.console) + 1) % len(consoles)]
        self.console_button.text = self.timer.console.label
        self.status = f"Console: {self.timer.console.label}."

    def _sync_generation_selection(self):
        for button in self.generation_buttons:
            button.set_selected(button.text == self.mode.generation)

    def _toggle_timer(self):
        if self.timer.running:
            self.timer.stop()
            self.status = "Timer stopped."
            return
        try:
            values = self._read_values()
            self.timer.start(self.mode, values)
        except ValueError as error:
            self.status = str(error)
            return
        self.status = "Timer running..."

    def _set_variable_target(self):
        try:
            values = self._read_values()
        except ValueError as error:
            self.status = str(error)
            return
        if self.timer.set_variable_target(values["target_frame"], values["gen3_calibration"]):
            self.status = "Variable target set."
        else:
            self.status = "Start Variable Target mode first."

    def _calibrate(self):
        try:
            values = self._read_values()
            updates = self.timer.calibrate(self.mode, values)
        except ValueError as error:
            self.status = str(error)
            return
        if not updates:
            self.status = "Enter the result field(s) before calibrating."
            return
        for name, value in updates.items():
            self.values[name] = value
            if name in self.fields:
                self.fields[name].text = self._format_value(value)
        for name in OPTIONAL_FIELDS:
            self.values[name] = None
            if name in self.fields:
                self.fields[name].text = ""
        self.status = "Calibration updated."

    def _return_to_menu(self):
        self.timer.stop()
        from ui.menu import MainMenu
        set_screen(MainMenu())
