import os
import sqlite3
from dataclasses import dataclass

import pygame

from ui.layout import HEADER, MAIN, NAV
from ui.screen import Screen
from ui.set_screen import set_screen
from ui.theme import THEME
from ui.widgets import Button, TextBox


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)
DATA_PATH = os.path.join(APP_DIR, "data", "pokedex.sqlite")
SPRITES_DIR = os.path.join(APP_DIR, "assets", "pokemon")
TYPE_ICON_DIR = os.path.join(APP_DIR, "assets", "types")

GENERATION_ORDER = [
    ("generation-i", "Gen I"),
    ("generation-ii", "Gen II"),
    ("generation-iii", "Gen III"),
    ("generation-iv", "Gen IV"),
    ("generation-v", "Gen V"),
    ("generation-vi", "Gen VI"),
    ("generation-vii", "Gen VII"),
    ("generation-viii", "Gen VIII"),
    ("generation-ix", "Gen IX"),
]

STAT_ORDER = [
    ("hp", "HP", (127, 184, 255)),
    ("attack", "Atk", (255, 170, 120)),
    ("defense", "Def", (255, 220, 120)),
    ("special-attack", "SpA", (151, 203, 255)),
    ("special-defense", "SpD", (165, 224, 154)),
    ("speed", "Spe", (255, 158, 183)),
]

TYPE_CHART = {
    "normal": {"rock": 0.5, "ghost": 0, "steel": 0.5},
    "fire": {
        "fire": 0.5,
        "water": 0.5,
        "grass": 2,
        "ice": 2,
        "bug": 2,
        "rock": 0.5,
        "dragon": 0.5,
        "steel": 2,
    },
    "water": {"fire": 2, "water": 0.5, "grass": 0.5, "ground": 2, "rock": 2, "dragon": 0.5},
    "electric": {"water": 2, "electric": 0.5, "grass": 0.5, "ground": 0, "flying": 2, "dragon": 0.5},
    "grass": {
        "fire": 0.5,
        "water": 2,
        "grass": 0.5,
        "poison": 0.5,
        "ground": 2,
        "flying": 0.5,
        "bug": 0.5,
        "rock": 2,
        "dragon": 0.5,
        "steel": 0.5,
    },
    "ice": {"fire": 0.5, "water": 0.5, "grass": 2, "ground": 2, "flying": 2, "dragon": 2, "steel": 0.5, "ice": 0.5},
    "fighting": {
        "normal": 2,
        "ice": 2,
        "poison": 0.5,
        "flying": 0.5,
        "psychic": 0.5,
        "bug": 0.5,
        "rock": 2,
        "ghost": 0,
        "dark": 2,
        "steel": 2,
        "fairy": 0.5,
    },
    "poison": {"grass": 2, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0, "fairy": 2},
    "ground": {"fire": 2, "electric": 2, "grass": 0.5, "poison": 2, "flying": 0, "bug": 0.5, "rock": 2, "steel": 2},
    "flying": {"electric": 0.5, "grass": 2, "fighting": 2, "bug": 2, "rock": 0.5, "steel": 0.5},
    "psychic": {"fighting": 2, "poison": 2, "psychic": 0.5, "dark": 0, "steel": 0.5},
    "bug": {"fire": 0.5, "grass": 2, "fighting": 0.5, "poison": 0.5, "flying": 0.5, "psychic": 2, "ghost": 0.5, "dark": 2, "steel": 0.5, "fairy": 0.5},
    "rock": {"fire": 2, "ice": 2, "fighting": 0.5, "ground": 0.5, "flying": 2, "bug": 2, "steel": 0.5},
    "ghost": {"normal": 0, "psychic": 2, "ghost": 2, "dark": 0.5},
    "dragon": {"dragon": 2, "steel": 0.5, "fairy": 0},
    "dark": {"fighting": 0.5, "psychic": 2, "ghost": 2, "dark": 0.5, "fairy": 0.5},
    "steel": {"fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2, "rock": 2, "steel": 0.5, "fairy": 2},
    "fairy": {"fire": 0.5, "fighting": 2, "poison": 0.5, "dragon": 2, "dark": 2, "steel": 0.5},
}

TYPE_COLORS = {
    "normal": (168, 167, 122),
    "fire": (238, 129, 48),
    "water": (99, 144, 240),
    "electric": (247, 208, 44),
    "grass": (122, 199, 76),
    "ice": (150, 217, 214),
    "fighting": (194, 46, 40),
    "poison": (163, 62, 161),
    "ground": (226, 191, 101),
    "flying": (169, 143, 243),
    "psychic": (249, 85, 135),
    "bug": (166, 185, 26),
    "rock": (182, 161, 54),
    "ghost": (115, 87, 151),
    "dragon": (111, 53, 252),
    "dark": (112, 87, 70),
    "steel": (183, 183, 206),
    "fairy": (214, 133, 173),
}

SUMMARY_PANEL_HEIGHT = 224
STATS_PANEL_HEIGHT = 208
EV_PANEL_HEIGHT = 96
TRAITS_PANEL_HEIGHT = 164
EFFECTIVENESS_PANEL_MIN_HEIGHT = 170
EVOLUTION_PANEL_HEIGHT = 134
MOVES_PANEL_HEIGHT = 220


def theme_color(name: str) -> pygame.Color:
    return pygame.Color(THEME[name])


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def blend(color_a, color_b, factor: float) -> tuple[int, int, int]:
    factor = max(0.0, min(1.0, factor))
    return tuple(
        int(color_a[index] + (color_b[index] - color_a[index]) * factor)
        for index in range(3)
    )


def prettify_slug(value: str | None) -> str:
    if not value:
        return "Unknown"
    return value.replace("-", " ").replace("_", " ").title()


def format_height(dm: int | None) -> str:
    if dm is None:
        return "Unknown"
    return f"{dm / 10:.1f} m"


def format_weight(hg: int | None) -> str:
    if hg is None:
        return "Unknown"
    return f"{hg / 10:.1f} kg"


def form_sprite_suffix(species_name: str, form_name: str) -> str:
    prefix = f"{species_name}-"
    if form_name.startswith(prefix):
        return form_name[len(prefix):]
    return form_name


def fit_text(text: str, font: pygame.font.Font, width: int) -> str:
    if font.size(text)[0] <= width:
        return text

    clipped = text
    while clipped and font.size(clipped + "...")[0] > width:
        clipped = clipped[:-1]
    return (clipped + "...") if clipped else "..."


def wrap_text_lines(text: str, font, width: int) -> list[str]:
    words = text.split()
    if not words:
        return []

    lines = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if font.size(candidate)[0] <= width:
            current = candidate
            continue

        if current:
            lines.append(current)
        current = word

    if current:
        lines.append(current)
    return lines


def draw_wrapped_text(surface, text: str, font, color, rect, line_gap=4) -> int:
    lines = wrap_text_lines(text, font, rect.width)
    if not lines:
        return rect.top

    y = rect.y
    line_height = font.get_height() + line_gap
    for line in lines:
        if y + line_height > rect.bottom:
            break
        text_surface = font.render(line, True, color)
        surface.blit(text_surface, (rect.x, y))
        y += line_height

    return y


def draw_scrolling_text(
    surface,
    text: str,
    font,
    color,
    rect,
    ticks_ms: int,
    speed_px_per_sec: float = 34.0,
    pause_ms: int = 700,
):
    text_surface = font.render(text, True, color)
    if text_surface.get_width() <= rect.width:
        surface.blit(text_surface, (rect.x, rect.y + (rect.height - text_surface.get_height()) // 2))
        return

    overflow = text_surface.get_width() - rect.width
    travel_ms = max(1, int((overflow / speed_px_per_sec) * 1000))
    cycle_ms = pause_ms * 2 + travel_ms * 2
    phase = ticks_ms % cycle_ms

    if phase < pause_ms:
        offset = 0
    elif phase < pause_ms + travel_ms:
        offset = overflow * (phase - pause_ms) / travel_ms
    elif phase < pause_ms + travel_ms + pause_ms:
        offset = overflow
    else:
        offset = overflow * (1 - (phase - pause_ms - travel_ms - pause_ms) / travel_ms)

    clip_before = surface.get_clip()
    surface.set_clip(rect)
    surface.blit(text_surface, (rect.x - int(offset), rect.y + (rect.height - text_surface.get_height()) // 2))
    surface.set_clip(clip_before)


@dataclass
class PokemonListItem:
    pokemon_id: int
    species_id: int
    dex_number: int
    name: str
    species_name: str
    form_name: str | None
    is_default: bool


class PokedexScreen(Screen):
    target_fps = 20

    def __init__(self):
        self.conn = sqlite3.connect(DATA_PATH)
        self.conn.row_factory = sqlite3.Row

        self.header_font = pygame.font.SysFont("Consolas", 21, bold=True)
        self.title_font = pygame.font.SysFont("Consolas", 32, bold=True)
        self.section_font = pygame.font.SysFont("Consolas", 18, bold=True)
        self.body_font = pygame.font.SysFont("Consolas", 16)
        self.small_font = pygame.font.SysFont("Consolas", 14)
        self.tiny_font = pygame.font.SysFont("Consolas", 12)

        logo_path = os.path.join(SCRIPT_DIR, "logo", THEME["logo"])
        self.header_image = None
        if os.path.exists(logo_path):
            logo = pygame.image.load(logo_path).convert_alpha()
            self.header_image = pygame.transform.smoothscale(logo, (162, 50))

        self.background = theme_color("primary")
        self.panel_bg = blend(theme_color("primary")[:3], (255, 255, 255), 0.16)
        self.panel_bg_alt = blend(theme_color("nav")[:3], (255, 255, 255), 0.12)
        self.panel_border = blend(theme_color("outline")[:3], (255, 255, 255), 0.28)
        self.panel_header_bg = blend(theme_color("header")[:3], (255, 255, 255), 0.24)
        self.text_color = theme_color("text")
        self.subtle_text = blend(theme_color("text")[:3], (0, 0, 0), 0.25)
        self.track_color = blend(theme_color("nav")[:3], (255, 255, 255), 0.18)
        self.thumb_color = blend(theme_color("button_select")[:3], (255, 255, 255), 0.2)
        self.highlight = theme_color("button_select")

        self.search_box = TextBox(
            pygame.Rect(NAV.x + 8, NAV.y + 8, NAV.width - 16, 34),
            placeholder="Search name or #",
            font=self.body_font,
            bg_color=self.panel_bg_alt,
            fg_color=self.text_color,
            border_color=self.panel_border,
            active_color=self.highlight,
            max_length=24,
        )
        self.search_box.activate()

        self.back_button = Button(
            pygame.Rect(HEADER.right - 160, HEADER.y + 8, 146, 34),
            "Main Menu",
            callback=self._return_to_menu,
            font=self.small_font,
            bg_color=self.panel_bg_alt,
            fg_color=self.text_color,
            selected_color=self.highlight,
            padding_x=10,
            padding_y=8,
        )
        self.generation_button = Button(
            pygame.Rect(HEADER.right - 320, HEADER.y + 8, 146, 34),
            "Change Gen",
            callback=self._toggle_generation_menu,
            font=self.small_font,
            bg_color=self.panel_bg_alt,
            fg_color=self.text_color,
            selected_color=self.highlight,
            padding_x=10,
            padding_y=8,
        )

        self.all_pokemon = self._load_pokemon_list()
        self.filtered_pokemon = list(self.all_pokemon)
        self.selected_pokemon_id = self.filtered_pokemon[0].pokemon_id if self.filtered_pokemon else None
        self.nav_scroll = 0
        self.main_scroll = 0
        self.generation_index = 8
        self.generation_menu_open = False
        self.main_content_height = 0
        self.entry_scroll = 0
        self.evolution_scroll = 0
        self.move_scrolls = {"level-up": 0, "machine": 0}
        self.entry_scroll_meta = {"content_height": 0, "viewport_height": 0}
        self.evolution_scroll_meta = {"content_height": 0, "viewport_height": 0}
        self.move_scroll_meta = {
            "level-up": {"content_height": 0, "viewport_height": 0},
            "machine": {"content_height": 0, "viewport_height": 0},
        }
        self.detail_cache = {}
        self.sprite_cache = {}
        self.type_icon_cache = {}
        self._main_content_cache = None
        self._main_content_cache_key = None
        self._last_tick = pygame.time.get_ticks()
        self._sync_selection()

    def update(self):
        now = pygame.time.get_ticks()
        delta_ms = now - self._last_tick
        self._last_tick = now
        self.search_box.update(delta_ms)

    def handle_event(self, event):
        if self.generation_menu_open:
            if self._handle_generation_menu_event(event):
                return

        self.back_button.handle_event(event)
        self.generation_button.handle_event(event)

        search_changed = False
        if self.search_box.handle_event(event):
            search_changed = event.type == pygame.KEYDOWN and event.key != pygame.K_RETURN
            if event.type == pygame.MOUSEBUTTONDOWN:
                return

        if search_changed:
            self._apply_filter()
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._return_to_menu()
                return
            if event.key == pygame.K_F1:
                self._toggle_generation_menu()
                return
            if event.key == pygame.K_DOWN:
                self._move_selection(1)
                return
            if event.key == pygame.K_UP:
                self._move_selection(-1)
                return
            if event.key == pygame.K_PAGEDOWN:
                self.main_scroll += 60
                return
            if event.key == pygame.K_PAGEUP:
                self.main_scroll -= 60
                return
            if event.key == pygame.K_LEFT:
                self._scroll_move_panel("level-up", -28)
                return
            if event.key == pygame.K_RIGHT:
                self._scroll_move_panel("machine", -28)
                return
            if event.key == pygame.K_RETURN and self.search_box.active and self.filtered_pokemon:
                self.selected_pokemon_id = self.filtered_pokemon[0].pokemon_id
                self._reset_detail_scrolls()
                self.main_scroll = 0
                self._sync_selection()
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._nav_list_rect().collidepoint(event.pos):
                self._handle_nav_click(event.pos)
                return

        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            if self._nav_list_rect().collidepoint(mouse_pos):
                max_scroll = self._nav_max_scroll()
                self.nav_scroll = clamp(self.nav_scroll - event.y * 22, 0, max_scroll)
                return
            if self._entry_scroll_rect().collidepoint(mouse_pos):
                self._scroll_entry_panel(-event.y * 28)
                return
            if self._evolution_scroll_rect().collidepoint(mouse_pos):
                self._scroll_evolution_panel(-event.y * 28)
                return
            for method in ("level-up", "machine"):
                if self._move_scroll_rect(method).collidepoint(mouse_pos):
                    self._scroll_move_panel(method, -event.y * 28)
                    return
            if self._main_view_rect().collidepoint(mouse_pos):
                max_scroll = max(0, self.main_content_height - self._main_view_rect().height)
                self.main_scroll = clamp(self.main_scroll - event.y * 28, 0, max_scroll)
                return

        self.main_scroll = max(0, self.main_scroll)

    def draw(self, surface):
        self._draw_header(surface)
        self._draw_nav(surface)
        self._draw_main(surface)
        if self.generation_menu_open:
            self._draw_generation_menu(surface)

    def _draw_header(self, surface):
        if self.header_image is not None:
            surface.blit(self.header_image, (HEADER.left + 14, HEADER.top))
        else:
            title = self.header_font.render("Bayleef", True, self.text_color)
            surface.blit(title, (HEADER.left + 18, HEADER.top + 14))

        current_generation = GENERATION_ORDER[self.generation_index][1]
        badge_text = self.small_font.render(current_generation, True, self.text_color)
        badge_rect = badge_text.get_rect(midleft=(HEADER.left + 190, HEADER.centery))
        surface.blit(badge_text, badge_rect)

        self.generation_button.draw(surface)
        self.back_button.draw(surface)

    def _draw_nav(self, surface):
        self.search_box.draw(surface)

        list_rect = self._nav_list_rect()
        pygame.draw.rect(surface, self.panel_bg_alt, list_rect, border_radius=8)
        pygame.draw.rect(surface, self.panel_border, list_rect, 2, border_radius=8)

        clip_before = surface.get_clip()
        surface.set_clip(list_rect.inflate(-6, -6))

        y = list_rect.y + 6 - self.nav_scroll
        for item in self.filtered_pokemon:
            item_rect = pygame.Rect(list_rect.x + 6, y, list_rect.width - 24, 58)
            if item_rect.bottom >= list_rect.y and item_rect.top <= list_rect.bottom:
                self._draw_nav_item(surface, item, item_rect)
            y += 62

        surface.set_clip(clip_before)
        self._draw_scrollbar(
            surface,
            pygame.Rect(list_rect.right - 12, list_rect.y + 6, 8, list_rect.height - 12),
            self.nav_scroll,
            self._nav_content_height(),
            list_rect.height - 12,
        )

    def _draw_nav_item(self, surface, item: PokemonListItem, rect: pygame.Rect):
        is_selected = item.pokemon_id == self.selected_pokemon_id
        fill = self.highlight if is_selected else self.panel_bg
        border = blend(self.highlight[:3], (0, 0, 0), 0.4) if is_selected else self.panel_border
        pygame.draw.rect(surface, fill, rect, border_radius=6)
        pygame.draw.rect(surface, border, rect, 2, border_radius=6)

        sprite_rect = pygame.Rect(rect.x + 6, rect.y + 6, 46, 46)
        pygame.draw.rect(surface, blend(fill[:3], (255, 255, 255), 0.22), sprite_rect, border_radius=4)
        sprite = self._get_sprite(
            item.dex_number,
            species_name=item.species_name,
            form_name=item.form_name,
        )
        if sprite is not None:
            surface.blit(sprite, sprite.get_rect(center=sprite_rect.center))
        else:
            fallback = self.small_font.render(f"#{item.dex_number:04d}", True, self.text_color)
            surface.blit(fallback, fallback.get_rect(center=sprite_rect.center))

        display_name = item.form_name if item.form_name else item.species_name
        name_rect = pygame.Rect(rect.x + 60, rect.y + 8, rect.width - 68, 18)
        detail_label = "Base Form" if item.is_default else prettify_slug(item.form_name)
        number_text = fit_text(
            f"#{item.dex_number:04d}  {detail_label}",
            self.tiny_font,
            rect.width - 68,
        )
        number_surface = self.tiny_font.render(number_text, True, self.subtle_text)
        draw_scrolling_text(
            surface,
            prettify_slug(display_name),
            self.body_font,
            self.text_color,
            name_rect,
            pygame.time.get_ticks(),
        )
        surface.blit(number_surface, (rect.x + 60, rect.y + 34))

    def _draw_main(self, surface):
        view_rect = self._main_view_rect()
        pygame.draw.rect(surface, self.panel_bg_alt, view_rect, border_radius=8)
        pygame.draw.rect(surface, self.panel_border, view_rect, 2, border_radius=8)

        content_width = view_rect.width - 18
        content_surface, content_height = self._build_main_content(content_width)
        self.main_content_height = content_height
        max_scroll = max(0, content_height - (view_rect.height - 12))
        self.main_scroll = clamp(self.main_scroll, 0, max_scroll)

        clip_before = surface.get_clip()
        inner_rect = pygame.Rect(view_rect.x + 6, view_rect.y + 6, content_width, view_rect.height - 12)
        surface.set_clip(inner_rect)
        surface.blit(content_surface, (inner_rect.x, inner_rect.y - self.main_scroll))
        surface.set_clip(clip_before)

        self._draw_scrollbar(
            surface,
            pygame.Rect(view_rect.right - 12, view_rect.y + 6, 8, view_rect.height - 12),
            self.main_scroll,
            content_height,
            view_rect.height - 12,
        )

    def _build_main_content(self, width: int):
        selected = self._selected_item()
        animation_step = 0
        if selected is not None:
            details = self._load_pokemon_details(
                selected.pokemon_id,
                GENERATION_ORDER[self.generation_index][0],
            )
            title_width = max(1, width - 344)
            if self.title_font.size(details["display_name"])[0] > title_width:
                animation_step = pygame.time.get_ticks() // 100

        cache_key = (
            width,
            self.selected_pokemon_id,
            self.generation_index,
            self.entry_scroll,
            self.evolution_scroll,
            self.move_scrolls["level-up"],
            self.move_scrolls["machine"],
            animation_step,
        )
        if cache_key != self._main_content_cache_key:
            self._main_content_cache = self._render_main_content(width)
            self._main_content_cache_key = cache_key
        return self._main_content_cache

    def _render_main_content(self, width: int):
        selected = self._selected_item()
        if selected is None:
            surface = pygame.Surface((width, 140), pygame.SRCALPHA)
            message = self.title_font.render("No Pokemon found", True, self.text_color)
            surface.blit(message, (18, 18))
            return surface, 140

        details = self._load_pokemon_details(selected.pokemon_id, GENERATION_ORDER[self.generation_index][0])
        effectiveness_height = self._effectiveness_panel_height(width, details)
        content_height = (
            SUMMARY_PANEL_HEIGHT
            + STATS_PANEL_HEIGHT
            + EV_PANEL_HEIGHT
            + TRAITS_PANEL_HEIGHT
            + effectiveness_height
            + EVOLUTION_PANEL_HEIGHT
            + MOVES_PANEL_HEIGHT
            + 80
        )
        surface = pygame.Surface((width, content_height), pygame.SRCALPHA)
        y = 0

        y = self._draw_summary_panel(surface, pygame.Rect(0, y, width, SUMMARY_PANEL_HEIGHT), details) + 10
        y = self._draw_stats_panel(surface, pygame.Rect(0, y, width, STATS_PANEL_HEIGHT), details) + 10
        y = self._draw_ev_yield_panel(surface, pygame.Rect(0, y, width, EV_PANEL_HEIGHT), details) + 10
        y = self._draw_traits_panel(surface, pygame.Rect(0, y, width, TRAITS_PANEL_HEIGHT), details) + 10
        y = self._draw_effectiveness_panel(surface, pygame.Rect(0, y, width, effectiveness_height), details) + 10
        y = self._draw_evolution_panel(surface, pygame.Rect(0, y, width, EVOLUTION_PANEL_HEIGHT), details) + 10
        y = self._draw_moves_panel(surface, pygame.Rect(0, y, width, MOVES_PANEL_HEIGHT), details) + 10

        return surface.subsurface(pygame.Rect(0, 0, width, y)).copy(), y

    def _draw_summary_panel(self, surface, rect, details):
        self._draw_panel(surface, rect, "Infobox")

        left_card = pygame.Rect(rect.x + 12, rect.y + 36, 180, 176)
        right_card = pygame.Rect(left_card.right + 10, left_card.y, rect.width - left_card.width - 34, 176)
        self._draw_inner_box(surface, left_card)
        self._draw_inner_box(surface, right_card)

        sprite = self._get_sprite(
            details["dex_number"],
            species_name=details["species_name"],
            form_name=details["form_name"],
            size=(116, 116),
        )
        sprite_rect = pygame.Rect(left_card.x + 8, left_card.y + 10, left_card.width - 16, 92)
        if sprite is not None:
            surface.blit(sprite, sprite.get_rect(center=sprite_rect.center))
        else:
            fallback = self.section_font.render(f"#{details['dex_number']:04d}", True, self.text_color)
            surface.blit(fallback, fallback.get_rect(center=sprite_rect.center))

        type_y = left_card.bottom - 30
        type_x = left_card.x + 10
        for type_name in details["types"]:
            icon = self._get_type_icon(type_name)
            if icon is not None:
                surface.blit(icon, (type_x, type_y))
                type_x += icon.get_width() + 6
            else:
                type_text = self.small_font.render(prettify_slug(type_name), True, self.text_color)
                surface.blit(type_text, (type_x, type_y + 6))
                type_x += type_text.get_width() + 8

        title_width = right_card.width - 130
        title_rect = pygame.Rect(right_card.x + 10, right_card.y + 10, title_width, self.title_font.get_height())
        dex_surface = self.title_font.render(f"#{details['dex_number']:04d}", True, self.text_color)
        draw_scrolling_text(
            surface,
            details["display_name"],
            self.title_font,
            self.text_color,
            title_rect,
            pygame.time.get_ticks(),
            speed_px_per_sec=42.0,
            pause_ms=850,
        )
        surface.blit(dex_surface, dex_surface.get_rect(topright=(right_card.right - 10, right_card.y + 10)))

        if details["form_name"]:
            base_surface = self.small_font.render(
                fit_text(f"Species: {prettify_slug(details['species_name'])}", self.small_font, title_width),
                True,
                self.subtle_text,
            )
            surface.blit(base_surface, (right_card.x + 12, right_card.y + 40))
            generation_y = right_card.y + 62
        else:
            generation_y = right_card.y + 48

        selected_generation = GENERATION_ORDER[self.generation_index][1]
        entry_generation = details["entry_generation_label"]
        generation_text = f"{selected_generation} entry"
        if entry_generation != selected_generation:
            generation_text = f"{selected_generation} entry (using {entry_generation})"
        gen_surface = self.small_font.render(
            fit_text(generation_text, self.small_font, right_card.width - 20),
            True,
            self.subtle_text,
        )
        surface.blit(gen_surface, (right_card.x + 12, generation_y))

        entry_box = pygame.Rect(right_card.x + 10, generation_y + 22, right_card.width - 20, right_card.bottom - (generation_y + 22) - 10)
        self._draw_inner_box(surface, entry_box)
        self._draw_entry_list(surface, entry_box, details["entries"])

        return rect.bottom

    def _draw_stats_panel(self, surface, rect, details):
        self._draw_panel(surface, rect, "Base Stats")

        bar_left = rect.x + 12
        bar_width = rect.width - 24
        y = rect.y + 42
        total = 0

        for stat_key, label, color in STAT_ORDER:
            stat_value = details["stats"].get(stat_key, 0)
            total += stat_value
            row_rect = pygame.Rect(bar_left, y, bar_width, 20)
            self._draw_stat_row(surface, row_rect, label, stat_value, color)
            y += 24

        total_rect = pygame.Rect(bar_left, y + 6, bar_width, 26)
        self._draw_inner_box(surface, total_rect)
        total_label = self.section_font.render("BST", True, self.text_color)
        total_value = self.section_font.render(str(total), True, self.text_color)
        surface.blit(total_label, (total_rect.x + 10, total_rect.y + 4))
        surface.blit(total_value, total_value.get_rect(topright=(total_rect.right - 10, total_rect.y + 4)))
        return rect.bottom

    def _draw_traits_panel(self, surface, rect, details):
        self._draw_panel(surface, rect, "Training and Breeding")
        left = rect.x + 12
        top = rect.y + 42

        left_lines = [
            ("Height", format_height(details["height_dm"])),
            ("Weight", format_weight(details["weight_hg"])),
            ("Base Exp", str(details["base_experience"] or "Unknown")),
            ("Growth", prettify_slug(details["growth_rate"])),
        ]
        right_lines = [
            ("Catch Rate", str(details["capture_rate"] or "Unknown")),
            ("Friendship", str(details["base_friendship"] or "Unknown")),
            ("Hatch", str(details["hatch_counter"] or "Unknown")),
            ("Egg Groups", ", ".join(prettify_slug(name) for name in details["egg_groups"]) or "Unknown"),
        ]

        self._draw_key_value_column(surface, pygame.Rect(left, top, 248, 70), left_lines)
        self._draw_key_value_column(surface, pygame.Rect(left + 260, top, rect.width - 284, 70), right_lines)

        tags = []
        if details["is_baby"]:
            tags.append("Baby")
        if details["is_legendary"]:
            tags.append("Legendary")
        if details["is_mythical"]:
            tags.append("Mythical")
        if not tags:
            tags.append("Standard")

        ability_text = ", ".join(
            f"{prettify_slug(entry['name'])}{' (Hidden)' if entry['hidden'] else ''}"
            for entry in details["abilities"]
        ) or "Unknown"
        ability_rect = pygame.Rect(left, top + 74, rect.width - 24, 52)
        ability_label = self.small_font.render("Abilities", True, self.subtle_text)
        surface.blit(ability_label, (ability_rect.x, ability_rect.y))
        draw_wrapped_text(
            surface,
            ability_text,
            self.small_font,
            self.text_color,
            pygame.Rect(ability_rect.x + 78, ability_rect.y, ability_rect.width - 78, ability_rect.height),
            line_gap=0,
        )

        badge_x = left
        badge_y = rect.bottom - 34
        for tag in tags:
            badge_rect = pygame.Rect(badge_x, badge_y, max(74, self.small_font.size(tag)[0] + 18), 24)
            pygame.draw.rect(surface, self.highlight, badge_rect, border_radius=5)
            pygame.draw.rect(surface, blend(self.highlight[:3], (0, 0, 0), 0.45), badge_rect, 2, border_radius=5)
            tag_surface = self.small_font.render(tag, True, self.text_color)
            surface.blit(tag_surface, tag_surface.get_rect(center=badge_rect.center))
            badge_x += badge_rect.width + 8

        return rect.bottom

    def _draw_ev_yield_panel(self, surface, rect, details):
        self._draw_panel(surface, rect, "EV Yield")
        total = sum(details["ev_yields"].values())
        total_surface = self.section_font.render(f"Total: {total}", True, self.text_color)
        surface.blit(total_surface, total_surface.get_rect(center=(rect.centerx, rect.y + 42)))

        labels = [
            ("hp", "HP", (160, 235, 90)),
            ("attack", "Atk", (255, 222, 95)),
            ("defense", "Def", (255, 170, 92)),
            ("special-attack", "Sp.Atk", (99, 206, 242)),
            ("special-defense", "Sp.Def", (122, 141, 232)),
            ("speed", "Speed", (211, 97, 215)),
        ]
        gap = 6
        box_width = (rect.width - 24 - gap * 5) // 6
        x = rect.x + 12
        for stat_key, label, color in labels:
            box = pygame.Rect(x, rect.y + 54, box_width, 30)
            pygame.draw.rect(surface, color, box, border_radius=9)
            pygame.draw.rect(surface, blend(color, (0, 0, 0), 0.35), box, 1, border_radius=9)
            value = str(details["ev_yields"].get(stat_key, 0))
            value_surface = self.small_font.render(value, True, (25, 25, 25))
            label_surface = self.small_font.render(label, True, (25, 25, 25))
            surface.blit(value_surface, value_surface.get_rect(center=(box.centerx, box.y + 10)))
            surface.blit(label_surface, label_surface.get_rect(center=(box.centerx, box.y + 22)))
            x += box_width + gap
        return rect.bottom

    def _draw_effectiveness_panel(self, surface, rect, details):
        self._draw_panel(surface, rect, "Type Matchups")
        rows = self._effectiveness_rows(details)
        y = rect.y + 36
        pill_rect_width = rect.width - 170
        for label, items in rows:
            row_height = max(42, self._measure_type_pills_height(pill_rect_width, items) + 10)
            row_rect = pygame.Rect(rect.x + 8, y, rect.width - 16, row_height)
            pygame.draw.rect(surface, blend(self.panel_bg[:3], (255, 255, 255), 0.14), row_rect, border_radius=10)
            pygame.draw.rect(surface, self.panel_border, row_rect, 1, border_radius=10)
            label_surface = self.small_font.render(label + ":", True, self.text_color)
            surface.blit(label_surface, (row_rect.x + 10, row_rect.y + 10))
            self._draw_type_pills(surface, pygame.Rect(row_rect.x + 145, row_rect.y + 5, row_rect.width - 154, row_rect.height - 10), items)
            y += row_height + 4
        return rect.bottom

    def _draw_evolution_panel(self, surface, rect, details):
        self._draw_panel(surface, rect, "Evolution")
        entries = details["evolution_lines"] or ["No evolution data available."]
        box = pygame.Rect(rect.x + 12, rect.y + 42, rect.width - 24, rect.height - 54)
        self._draw_inner_box(surface, box)
        inner_rect = box.inflate(-8, -8)
        viewport_rect = pygame.Rect(inner_rect.x, inner_rect.y, inner_rect.width - 10, inner_rect.height)
        line_height = self.small_font.get_height() + 4
        content_height = max(viewport_rect.height, len(entries) * line_height)
        self.evolution_scroll_meta = {
            "content_height": content_height,
            "viewport_height": viewport_rect.height,
        }
        self.evolution_scroll = clamp(self.evolution_scroll, 0, max(0, content_height - viewport_rect.height))
        clip_before = surface.get_clip()
        surface.set_clip(viewport_rect)
        y = viewport_rect.y - self.evolution_scroll
        for entry in entries:
            line_rect = pygame.Rect(viewport_rect.x, y, viewport_rect.width, self.small_font.get_height())
            draw_wrapped_text(surface, entry, self.small_font, self.text_color, line_rect, line_gap=0)
            y += line_height
        surface.set_clip(clip_before)
        self._draw_scrollbar(
            surface,
            pygame.Rect(box.right - 12, box.y + 6, 8, box.height - 12),
            self.evolution_scroll,
            content_height,
            viewport_rect.height,
        )
        return rect.bottom

    def _draw_moves_panel(self, surface, rect, details):
        self._draw_panel(surface, rect, "Moves by Generation")
        move_generation_text = details["move_generation_label"]
        selected_generation_text = GENERATION_ORDER[self.generation_index][1]
        if move_generation_text != selected_generation_text:
            note = self.tiny_font.render(
                f"Using {move_generation_text} move data",
                True,
                self.subtle_text,
            )
            surface.blit(note, (rect.right - note.get_width() - 10, rect.y + 6))

        level_up = details["moves"]["level-up"]
        machine = details["moves"]["machine"]
        sections = [
            ("Level-up", level_up, rect.x + 12),
            ("Machine", machine, rect.x + rect.width // 2 + 4),
        ]

        for title, rows, left in sections:
            box = pygame.Rect(left, rect.y + 42, rect.width // 2 - 16, rect.height - 54)
            self._draw_inner_box(surface, box)
            title_surface = self.small_font.render(title, True, self.text_color)
            surface.blit(title_surface, (box.x + 8, box.y + 6))

            y = box.y + 30
            if not rows:
                empty_surface = self.small_font.render("No data in this gen", True, self.subtle_text)
                surface.blit(empty_surface, (box.x + 8, y))
                continue

            self._draw_move_list(
                surface,
                box,
                "level-up" if title == "Level-up" else "machine",
                rows,
            )

        return rect.bottom

    def _draw_entry_list(self, surface, rect, entries):
        inner_rect = rect.inflate(-8, -8)
        viewport_rect = pygame.Rect(inner_rect.x, inner_rect.y, inner_rect.width - 10, inner_rect.height)
        line_height = self.small_font.get_height() + 1
        entry_layouts = []
        content_height = 0
        for entry in entries:
            lines = wrap_text_lines(entry["flavor_text"], self.small_font, viewport_rect.width)
            lines = lines or [""]
            row_height = 18 + len(lines) * line_height + 8
            entry_layouts.append((entry, lines, row_height))
            content_height += row_height
        content_height = max(viewport_rect.height, content_height)
        self.entry_scroll_meta = {
            "content_height": content_height,
            "viewport_height": viewport_rect.height,
        }
        self.entry_scroll = clamp(
            self.entry_scroll,
            0,
            max(0, content_height - viewport_rect.height),
        )

        clip_before = surface.get_clip()
        surface.set_clip(viewport_rect)
        y = viewport_rect.y - self.entry_scroll
        for entry, lines, row_height in entry_layouts:
            row_rect = pygame.Rect(viewport_rect.x, y, viewport_rect.width, row_height - 4)
            row_label = self.tiny_font.render(
                fit_text(prettify_slug(entry["version_name"]), self.tiny_font, row_rect.width),
                True,
                self.subtle_text,
            )
            surface.blit(row_label, (row_rect.x, row_rect.y))
            text_y = row_rect.y + 16
            for line in lines:
                if text_y + self.small_font.get_height() > viewport_rect.bottom:
                    break
                line_surface = self.small_font.render(line, True, self.text_color)
                surface.blit(line_surface, (row_rect.x, text_y))
                text_y += line_height
            y += row_height
        surface.set_clip(clip_before)
        self._draw_scrollbar(
            surface,
            pygame.Rect(rect.right - 12, rect.y + 6, 8, rect.height - 12),
            self.entry_scroll,
            content_height,
            viewport_rect.height,
        )

    def _draw_move_list(self, surface, box, method, rows):
        inner_rect = box.inflate(-8, -8)
        viewport_rect = pygame.Rect(inner_rect.x, inner_rect.y + 18, inner_rect.width - 10, inner_rect.height - 18)
        content_height = max(viewport_rect.height, len(rows) * 18)
        self.move_scroll_meta[method] = {
            "content_height": content_height,
            "viewport_height": viewport_rect.height,
        }
        self.move_scrolls[method] = clamp(
            self.move_scrolls[method],
            0,
            max(0, content_height - viewport_rect.height),
        )

        clip_before = surface.get_clip()
        surface.set_clip(viewport_rect)
        y = viewport_rect.y - self.move_scrolls[method]
        for row in rows:
            move_name = prettify_slug(row["move_name"])
            if method == "level-up":
                text = f"Lv {row['level']:>2}  {move_name}"
            else:
                text = move_name
            move_surface = self.small_font.render(
                fit_text(text, self.small_font, viewport_rect.width),
                True,
                self.text_color,
            )
            surface.blit(move_surface, (viewport_rect.x, y))
            y += 18
        surface.set_clip(clip_before)
        self._draw_scrollbar(
            surface,
            pygame.Rect(box.right - 12, box.y + 24, 8, box.height - 30),
            self.move_scrolls[method],
            content_height,
            viewport_rect.height,
        )

    def _draw_type_pills(self, surface, rect, items):
        if not items:
            empty = self.small_font.render("-", True, self.subtle_text)
            surface.blit(empty, (rect.x, rect.y + (rect.height - empty.get_height()) // 2))
            return

        clip_before = surface.get_clip()
        surface.set_clip(rect)
        x = rect.x
        y = rect.y
        row_height = 26
        gap_x = 6
        gap_y = 5
        for type_name, multiplier in items:
            label = prettify_slug(type_name)
            label_width = self.small_font.size(label)[0]
            badge_width = self.tiny_font.size(multiplier)[0] + 16
            pill_width = label_width + badge_width + 26
            if x + pill_width > rect.right and x > rect.x:
                x = rect.x
                y += row_height + gap_y
            pill_rect = pygame.Rect(x, y, pill_width, row_height)
            fill = TYPE_COLORS.get(type_name, self.panel_header_bg)
            pygame.draw.rect(surface, fill, pill_rect, border_radius=13)
            pygame.draw.rect(surface, blend(fill, (0, 0, 0), 0.4), pill_rect, 1, border_radius=13)
            text_surface = self.small_font.render(label, True, (250, 250, 250))
            surface.blit(text_surface, (pill_rect.x + 12, pill_rect.y + 5))
            badge_rect = pygame.Rect(pill_rect.right - badge_width - 6, pill_rect.y + 3, badge_width, pill_rect.height - 6)
            pygame.draw.rect(surface, (250, 250, 250), badge_rect, border_radius=10)
            pygame.draw.rect(surface, blend(fill, (0, 0, 0), 0.4), badge_rect, 1, border_radius=10)
            badge_surface = self.tiny_font.render(multiplier, True, (30, 30, 30))
            surface.blit(badge_surface, badge_surface.get_rect(center=badge_rect.center))
            x += pill_width + gap_x
        surface.set_clip(clip_before)

    def _measure_type_pills_height(self, width: int, items) -> int:
        if not items:
            return self.small_font.get_height()

        x = 0
        y = 0
        row_height = 26
        gap_x = 6
        gap_y = 5
        for type_name, multiplier in items:
            label = prettify_slug(type_name)
            label_width = self.small_font.size(label)[0]
            badge_width = self.tiny_font.size(multiplier)[0] + 16
            pill_width = label_width + badge_width + 26
            if x + pill_width > width and x > 0:
                x = 0
                y += row_height + gap_y
            x += pill_width + gap_x
        return y + row_height

    def _effectiveness_rows(self, details):
        groups = self._type_effectiveness_groups(details["types"])
        return [
            ("Damaged normally by", [(name, "1x") for name in groups["1x"]]),
            ("Weak to", [(name, "4x") for name in groups["4x"]] + [(name, "2x") for name in groups["2x"]]),
            ("Immune to", [(name, "0x") for name in groups["0x"]]),
            ("Resistant to", [(name, "1/4x") for name in groups["1/4x"]] + [(name, "1/2x") for name in groups["1/2x"]]),
        ]

    def _effectiveness_panel_height(self, width: int, details) -> int:
        total_height = 44
        pill_rect_width = width - 170
        for _, items in self._effectiveness_rows(details):
            total_height += max(42, self._measure_type_pills_height(pill_rect_width, items) + 10) + 4
        return max(EFFECTIVENESS_PANEL_MIN_HEIGHT, total_height + 6)

    def _draw_panel(self, surface, rect, title: str):
        pygame.draw.rect(surface, self.panel_bg, rect, border_radius=8)
        pygame.draw.rect(surface, self.panel_border, rect, 2, border_radius=8)
        header_rect = pygame.Rect(rect.x, rect.y, rect.width, 26)
        pygame.draw.rect(surface, self.panel_header_bg, header_rect, border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.line(surface, self.panel_border, (rect.x, rect.y + 26), (rect.right, rect.y + 26), 2)
        title_surface = self.section_font.render(title, True, self.text_color)
        surface.blit(title_surface, (rect.x + 10, rect.y + 4))

    def _draw_inner_box(self, surface, rect):
        pygame.draw.rect(surface, blend(self.panel_bg[:3], (255, 255, 255), 0.08), rect, border_radius=6)
        pygame.draw.rect(surface, self.panel_border, rect, 1, border_radius=6)

    def _draw_key_value_column(self, surface, rect, rows):
        label_width = 86
        y = rect.y
        for label, value in rows:
            label_surface = self.small_font.render(label, True, self.subtle_text)
            value_surface = self.small_font.render(fit_text(value, self.small_font, rect.width - label_width), True, self.text_color)
            surface.blit(label_surface, (rect.x, y))
            surface.blit(value_surface, (rect.x + label_width, y))
            y += 18

    def _draw_stat_row(self, surface, rect, label, value, color):
        bar_rect = pygame.Rect(rect.x + 86, rect.y + 2, rect.width - 134, rect.height - 4)
        pygame.draw.rect(surface, self.panel_bg_alt, bar_rect, border_radius=4)
        fill_width = int(bar_rect.width * min(value, 255) / 255)
        if fill_width > 0:
            pygame.draw.rect(surface, color, pygame.Rect(bar_rect.x, bar_rect.y, fill_width, bar_rect.height), border_radius=4)
        pygame.draw.rect(surface, self.panel_border, bar_rect, 1, border_radius=4)

        label_surface = self.small_font.render(label, True, self.text_color)
        value_surface = self.small_font.render(str(value), True, self.text_color)
        surface.blit(label_surface, (rect.x, rect.y + 2))
        surface.blit(value_surface, (rect.x + 56, rect.y + 2))

    def _draw_scrollbar(self, surface, rect, offset, content_height, viewport_height):
        pygame.draw.rect(surface, self.track_color, rect, border_radius=4)
        if content_height <= viewport_height or content_height <= 0:
            pygame.draw.rect(surface, self.thumb_color, rect, border_radius=4)
            return

        thumb_height = max(22, int(rect.height * viewport_height / content_height))
        max_offset = max(1, content_height - viewport_height)
        travel = rect.height - thumb_height
        thumb_y = rect.y + int(travel * offset / max_offset)
        thumb_rect = pygame.Rect(rect.x, thumb_y, rect.width, thumb_height)
        pygame.draw.rect(surface, self.thumb_color, thumb_rect, border_radius=4)

    def _draw_generation_menu(self, surface):
        overlay = pygame.Surface((MAIN.width, MAIN.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surface.blit(overlay, MAIN.topleft)

        menu_rect = pygame.Rect(MAIN.x + 155, MAIN.y + 42, 290, 306)
        pygame.draw.rect(surface, self.panel_bg, menu_rect, border_radius=10)
        pygame.draw.rect(surface, self.panel_border, menu_rect, 2, border_radius=10)
        title = self.section_font.render("Choose Generation", True, self.text_color)
        surface.blit(title, title.get_rect(center=(menu_rect.centerx, menu_rect.y + 22)))

        y = menu_rect.y + 48
        for index, (_, label) in enumerate(GENERATION_ORDER):
            row_rect = pygame.Rect(menu_rect.x + 18, y, menu_rect.width - 36, 24)
            is_selected = index == self.generation_index
            fill = self.highlight if is_selected else self.panel_bg_alt
            pygame.draw.rect(surface, fill, row_rect, border_radius=5)
            pygame.draw.rect(surface, self.panel_border, row_rect, 1, border_radius=5)
            text = self.small_font.render(label, True, self.text_color)
            surface.blit(text, text.get_rect(center=row_rect.center))
            y += 28

    def _handle_generation_menu_event(self, event):
        menu_rect = pygame.Rect(MAIN.x + 155, MAIN.y + 42, 290, 306)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.generation_menu_open = False
                return True
            if event.key == pygame.K_DOWN:
                self.generation_index = (self.generation_index + 1) % len(GENERATION_ORDER)
                self._reset_detail_scrolls()
                self.main_scroll = 0
                return True
            if event.key == pygame.K_UP:
                self.generation_index = (self.generation_index - 1) % len(GENERATION_ORDER)
                self._reset_detail_scrolls()
                self.main_scroll = 0
                return True
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.generation_menu_open = False
                self._reset_detail_scrolls()
                self.main_scroll = 0
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not menu_rect.collidepoint(event.pos):
                self.generation_menu_open = False
                return True

            y = menu_rect.y + 48
            for index, _ in enumerate(GENERATION_ORDER):
                row_rect = pygame.Rect(menu_rect.x + 18, y, menu_rect.width - 36, 24)
                if row_rect.collidepoint(event.pos):
                    self.generation_index = index
                    self.generation_menu_open = False
                    self._reset_detail_scrolls()
                    self.main_scroll = 0
                    return True
                y += 28
        return False

    def _toggle_generation_menu(self):
        self.generation_menu_open = not self.generation_menu_open

    def _apply_filter(self):
        query = self.search_box.text.strip().lower()
        if not query:
            self.filtered_pokemon = list(self.all_pokemon)
        else:
            self.filtered_pokemon = [
                item
                for item in self.all_pokemon
                if (
                    query in item.name.lower()
                    or str(item.dex_number).startswith(query)
                    or f"{item.dex_number:04d}".startswith(query)
                )
            ]

        self.nav_scroll = 0
        self._sync_selection()

    def _move_selection(self, delta):
        if not self.filtered_pokemon:
            return

        current_index = 0
        for index, item in enumerate(self.filtered_pokemon):
            if item.pokemon_id == self.selected_pokemon_id:
                current_index = index
                break

        current_index = clamp(current_index + delta, 0, len(self.filtered_pokemon) - 1)
        self.selected_pokemon_id = self.filtered_pokemon[current_index].pokemon_id
        self._reset_detail_scrolls()
        self.main_scroll = 0
        self._ensure_selected_visible()

    def _sync_selection(self):
        if not self.filtered_pokemon:
            self.selected_pokemon_id = None
            self.main_scroll = 0
            return

        valid_ids = {item.pokemon_id for item in self.filtered_pokemon}
        if self.selected_pokemon_id not in valid_ids:
            self.selected_pokemon_id = self.filtered_pokemon[0].pokemon_id
            self._reset_detail_scrolls()
            self.main_scroll = 0
        self._ensure_selected_visible()

    def _ensure_selected_visible(self):
        if not self.filtered_pokemon or self.selected_pokemon_id is None:
            return

        item_height = 62
        visible_height = self._nav_list_rect().height - 12
        selected_index = 0
        for index, item in enumerate(self.filtered_pokemon):
            if item.pokemon_id == self.selected_pokemon_id:
                selected_index = index
                break

        top = selected_index * item_height
        bottom = top + item_height
        if top < self.nav_scroll:
            self.nav_scroll = top
        elif bottom > self.nav_scroll + visible_height:
            self.nav_scroll = bottom - visible_height

        self.nav_scroll = clamp(self.nav_scroll, 0, self._nav_max_scroll())

    def _handle_nav_click(self, position):
        list_rect = self._nav_list_rect()
        relative_y = position[1] - list_rect.y - 6 + self.nav_scroll
        index = relative_y // 62
        if 0 <= index < len(self.filtered_pokemon):
            self.selected_pokemon_id = self.filtered_pokemon[index].pokemon_id
            self._reset_detail_scrolls()
            self.main_scroll = 0
            self._ensure_selected_visible()

    def _selected_item(self):
        for item in self.all_pokemon:
            if item.pokemon_id == self.selected_pokemon_id:
                return item
        return None

    def _load_pokemon_list(self):
        rows = self.conn.execute(
            """
            SELECT
                id,
                species_id,
                COALESCE(national_dex_id, species_id) AS dex_number,
                name,
                species_name,
                form_name,
                is_default
            FROM pokemon
            ORDER BY COALESCE(national_dex_id, species_id), is_default DESC, id
            """
        ).fetchall()
        return [
            PokemonListItem(
                pokemon_id=row["id"],
                species_id=row["species_id"],
                dex_number=row["dex_number"],
                name=row["name"],
                species_name=row["species_name"],
                form_name=row["form_name"],
                is_default=bool(row["is_default"]),
            )
            for row in rows
        ]

    def _load_pokemon_details(self, pokemon_id: int, generation_name: str):
        cache_key = (pokemon_id, generation_name)
        if cache_key in self.detail_cache:
            return self.detail_cache[cache_key]

        core = self.conn.execute(
            """
            SELECT
                id,
                name,
                species_id,
                species_name,
                form_name,
                is_default,
                COALESCE(national_dex_id, species_id) AS dex_number,
                height_dm,
                weight_hg,
                base_experience,
                growth_rate,
                base_friendship,
                hatch_counter,
                capture_rate,
                is_baby,
                is_legendary,
                is_mythical
            FROM pokemon
            WHERE id = ?
            """,
            (pokemon_id,),
        ).fetchone()

        types = [
            row["type_name"]
            for row in self.conn.execute(
                "SELECT type_name FROM pokemon_types WHERE pokemon_id = ? ORDER BY slot",
                (pokemon_id,),
            ).fetchall()
        ]
        abilities = [
            {
                "name": row["ability_name"],
                "hidden": bool(row["is_hidden"]),
            }
            for row in self.conn.execute(
                "SELECT ability_name, is_hidden FROM pokemon_abilities WHERE pokemon_id = ? ORDER BY slot",
                (pokemon_id,),
            ).fetchall()
        ]
        stats = {
            row["stat_name"]: row["base_stat"]
            for row in self.conn.execute(
                "SELECT stat_name, base_stat FROM pokemon_stats WHERE pokemon_id = ?",
                (pokemon_id,),
            ).fetchall()
        }
        ev_yields = {
            row["stat_name"]: row["ev_yield"]
            for row in self.conn.execute(
                "SELECT stat_name, ev_yield FROM pokemon_stats WHERE pokemon_id = ?",
                (pokemon_id,),
            ).fetchall()
        }
        egg_groups = [
            row["egg_group_name"]
            for row in self.conn.execute(
                "SELECT egg_group_name FROM egg_groups WHERE pokemon_id = ? ORDER BY egg_group_name",
                (pokemon_id,),
            ).fetchall()
        ]

        selected_generation_rank = {name: index for index, (name, _) in enumerate(GENERATION_ORDER)}
        available_entries = self.conn.execute(
            """
            SELECT generation_name, version_name, flavor_text
            FROM pokedex_entries
            WHERE species_id = ?
            """,
            (core["species_id"],),
        ).fetchall()
        grouped_entries = {}
        for row in available_entries:
            grouped_entries.setdefault(row["generation_name"], []).append(row)

        entry_generation = generation_name
        entries = grouped_entries.get(generation_name, [])
        if not entries:
            generation_index = selected_generation_rank[generation_name]
            for fallback_name, _ in reversed(GENERATION_ORDER[: generation_index + 1]):
                if grouped_entries.get(fallback_name):
                    entry_generation = fallback_name
                    entries = grouped_entries[fallback_name]
                    break

        flavor_text = entries[0]["flavor_text"] if entries else "No Pokedex text is stored for this generation."
        versions = [prettify_slug(row["version_name"]) for row in entries[:4]]
        entry_rows = [
            {"version_name": row["version_name"], "flavor_text": row["flavor_text"]}
            for row in entries
        ]

        move_rows = self.conn.execute(
            """
            SELECT move_name, learn_method, MIN(level_learned_at) AS level
            FROM pokemon_moves
            WHERE pokemon_id = ? AND generation_name = ?
            GROUP BY move_name, learn_method
            ORDER BY learn_method, level, move_name
            """,
            (pokemon_id, generation_name),
        ).fetchall()
        move_generation = generation_name
        if not move_rows:
            generation_index = selected_generation_rank[generation_name]
            for fallback_name, _ in reversed(GENERATION_ORDER[: generation_index + 1]):
                move_rows = self.conn.execute(
                    """
                    SELECT move_name, learn_method, MIN(level_learned_at) AS level
                    FROM pokemon_moves
                    WHERE pokemon_id = ? AND generation_name = ?
                    GROUP BY move_name, learn_method
                    ORDER BY learn_method, level, move_name
                    """,
                    (pokemon_id, fallback_name),
                ).fetchall()
                if move_rows:
                    move_generation = fallback_name
                    break

        moves = {"level-up": [], "machine": []}
        for row in move_rows:
            move = {
                "move_name": row["move_name"],
                "level": row["level"],
            }
            moves.setdefault(row["learn_method"], []).append(move)

        chain_rows = self.conn.execute(
            """
            SELECT from_species_name, to_species_name, trigger_name, min_level, item_name, time_of_day
            FROM evolution_edges
            WHERE chain_id = (
                SELECT chain_id
                FROM evolution_edges
                WHERE from_species_id = ?
                LIMIT 1
            )
            ORDER BY from_species_id, to_species_id, id
            """,
            (core["species_id"],),
        ).fetchall()
        evolution_lines = []
        for row in chain_rows:
            trigger = prettify_slug(row["trigger_name"])
            requirement = trigger
            if row["min_level"]:
                requirement += f" Lv {row['min_level']}"
            if row["item_name"]:
                requirement += f" with {prettify_slug(row['item_name'])}"
            if row["time_of_day"]:
                requirement += f" at {prettify_slug(row['time_of_day'])}"
            evolution_lines.append(
                f"{prettify_slug(row['from_species_name'])} -> {prettify_slug(row['to_species_name'])} ({requirement})"
            )

        details = {
            "display_name": prettify_slug(core["form_name"] or core["species_name"]),
            "species_name": core["species_name"],
            "form_name": core["form_name"],
            "is_default": bool(core["is_default"]),
            "dex_number": core["dex_number"],
            "height_dm": core["height_dm"],
            "weight_hg": core["weight_hg"],
            "base_experience": core["base_experience"],
            "growth_rate": core["growth_rate"],
            "base_friendship": core["base_friendship"],
            "hatch_counter": core["hatch_counter"],
            "capture_rate": core["capture_rate"],
            "is_baby": bool(core["is_baby"]),
            "is_legendary": bool(core["is_legendary"]),
            "is_mythical": bool(core["is_mythical"]),
            "types": types,
            "abilities": abilities,
            "stats": stats,
            "ev_yields": ev_yields,
            "egg_groups": egg_groups,
            "flavor_text": flavor_text,
            "versions": versions,
            "entries": entry_rows,
            "entry_generation_label": dict(GENERATION_ORDER).get(entry_generation, prettify_slug(entry_generation)),
            "move_generation_label": dict(GENERATION_ORDER).get(move_generation, prettify_slug(move_generation)),
            "moves": moves,
            "evolution_lines": evolution_lines,
        }
        self.detail_cache[cache_key] = details
        return details

    def _get_sprite(
        self,
        dex_number: int,
        species_name: str | None = None,
        form_name: str | None = None,
        size=(40, 40),
    ):
        cache_key = (dex_number, species_name, form_name, size)
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        candidates = []
        if form_name:
            normalized_form = form_name.replace("_", "-").lower()
            candidates.append(os.path.join(SPRITES_DIR, f"{dex_number:04d}-{normalized_form}.png"))
            if species_name:
                suffix = form_sprite_suffix(
                    species_name.replace("_", "-").lower(),
                    normalized_form,
                )
                candidates.append(os.path.join(SPRITES_DIR, f"{dex_number:04d}-{suffix}.png"))
        candidates.append(os.path.join(SPRITES_DIR, f"{dex_number:04d}.png"))

        sprite_path = None
        for candidate in candidates:
            if os.path.exists(candidate):
                sprite_path = candidate
                break

        if sprite_path is None:
            self.sprite_cache[cache_key] = None
            return None

        image = pygame.image.load(sprite_path).convert_alpha()
        image = pygame.transform.smoothscale(image, size)
        self.sprite_cache[cache_key] = image
        return image

    def _get_type_icon(self, type_name: str):
        cache_key = type_name
        if cache_key in self.type_icon_cache:
            return self.type_icon_cache[cache_key]

        path = os.path.join(TYPE_ICON_DIR, f"type_{type_name.upper()}.png")
        if not os.path.exists(path):
            self.type_icon_cache[cache_key] = None
            return None

        image = pygame.image.load(path).convert_alpha()
        target_height = 22
        scale = target_height / image.get_height()
        target_width = max(18, int(image.get_width() * scale))
        image = pygame.transform.smoothscale(image, (target_width, target_height))
        self.type_icon_cache[cache_key] = image
        return image

    def _type_effectiveness_groups(self, defending_types: list[str]):
        multipliers = {}
        for attack_type in TYPE_CHART:
            multiplier = 1.0
            for defending_type in defending_types:
                multiplier *= TYPE_CHART.get(attack_type, {}).get(defending_type, 1.0)
            multipliers[attack_type] = multiplier

        groups = {"4x": [], "2x": [], "1/2x": [], "1/4x": [], "0x": []}
        for type_name, multiplier in multipliers.items():
            if multiplier == 4:
                groups["4x"].append(type_name)
            elif multiplier == 2:
                groups["2x"].append(type_name)
            elif multiplier == 1:
                groups.setdefault("1x", []).append(type_name)
            elif multiplier == 0.5:
                groups["1/2x"].append(type_name)
            elif multiplier == 0.25:
                groups["1/4x"].append(type_name)
            elif multiplier == 0:
                groups["0x"].append(type_name)
        groups.setdefault("1x", [])
        return groups

    def _nav_list_rect(self):
        return pygame.Rect(NAV.x + 8, NAV.y + 50, NAV.width - 16, NAV.height - 58)

    def _main_view_rect(self):
        return pygame.Rect(MAIN.x + 8, MAIN.y + 8, MAIN.width - 16, MAIN.height - 16)

    def _nav_content_height(self):
        return max(0, len(self.filtered_pokemon) * 62 + 6)

    def _nav_max_scroll(self):
        return max(0, self._nav_content_height() - (self._nav_list_rect().height - 12))

    def _reset_detail_scrolls(self):
        self.entry_scroll = 0
        self.evolution_scroll = 0
        self.move_scrolls = {"level-up": 0, "machine": 0}

    def _entry_scroll_rect(self):
        view_rect = self._main_view_rect()
        content_x = view_rect.x + 6
        content_y = view_rect.y + 6 - self.main_scroll
        right_card = pygame.Rect(content_x + 202, content_y + 36, view_rect.width - 244, 176)
        top_offset = 62 if self._selected_item() and self._load_pokemon_details(self.selected_pokemon_id, GENERATION_ORDER[self.generation_index][0])["form_name"] else 48
        return pygame.Rect(right_card.x + 10, right_card.y + top_offset + 22, right_card.width - 20, right_card.bottom - (right_card.y + top_offset + 22) - 10)

    def _move_scroll_rect(self, method):
        view_rect = self._main_view_rect()
        content_x = view_rect.x + 6
        content_y = view_rect.y + 6 - self.main_scroll
        selected = self._selected_item()
        details = self._load_pokemon_details(selected.pokemon_id, GENERATION_ORDER[self.generation_index][0]) if selected else {"types": []}
        effectiveness_height = self._effectiveness_panel_height(view_rect.width - 18, details)
        moves_rect_y = SUMMARY_PANEL_HEIGHT + 10 + STATS_PANEL_HEIGHT + 10 + EV_PANEL_HEIGHT + 10 + TRAITS_PANEL_HEIGHT + 10 + effectiveness_height + 10 + EVOLUTION_PANEL_HEIGHT + 10
        moves_rect = pygame.Rect(content_x, content_y + moves_rect_y, view_rect.width - 18, 220)
        if method == "level-up":
            box = pygame.Rect(moves_rect.x + 12, moves_rect.y + 42, moves_rect.width // 2 - 16, moves_rect.height - 54)
        else:
            box = pygame.Rect(moves_rect.x + moves_rect.width // 2 + 4, moves_rect.y + 42, moves_rect.width // 2 - 16, moves_rect.height - 54)
        return pygame.Rect(box.x, box.y + 18, box.width - 10, box.height - 18)

    def _evolution_scroll_rect(self):
        view_rect = self._main_view_rect()
        content_x = view_rect.x + 6
        content_y = view_rect.y + 6 - self.main_scroll
        selected = self._selected_item()
        details = self._load_pokemon_details(selected.pokemon_id, GENERATION_ORDER[self.generation_index][0]) if selected else {"types": []}
        effectiveness_height = self._effectiveness_panel_height(view_rect.width - 18, details)
        evolution_y = SUMMARY_PANEL_HEIGHT + 10 + STATS_PANEL_HEIGHT + 10 + EV_PANEL_HEIGHT + 10 + TRAITS_PANEL_HEIGHT + 10 + effectiveness_height + 10
        rect = pygame.Rect(content_x, content_y + evolution_y, view_rect.width - 18, EVOLUTION_PANEL_HEIGHT)
        box = pygame.Rect(rect.x + 12, rect.y + 42, rect.width - 24, rect.height - 54)
        inner_rect = box.inflate(-8, -8)
        return pygame.Rect(inner_rect.x, inner_rect.y, inner_rect.width - 10, inner_rect.height)

    def _scroll_entry_panel(self, delta):
        meta = self.entry_scroll_meta
        max_scroll = max(0, meta["content_height"] - meta["viewport_height"])
        self.entry_scroll = clamp(self.entry_scroll + delta, 0, max_scroll)

    def _scroll_move_panel(self, method, delta):
        meta = self.move_scroll_meta[method]
        max_scroll = max(0, meta["content_height"] - meta["viewport_height"])
        self.move_scrolls[method] = clamp(self.move_scrolls[method] + delta, 0, max_scroll)

    def _scroll_evolution_panel(self, delta):
        meta = self.evolution_scroll_meta
        max_scroll = max(0, meta["content_height"] - meta["viewport_height"])
        self.evolution_scroll = clamp(self.evolution_scroll + delta, 0, max_scroll)

    def _return_to_menu(self):
        from ui.menu import MainMenu

        set_screen(MainMenu())
