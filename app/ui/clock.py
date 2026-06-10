import datetime
import math
import pygame

from ui.theme import THEME


def normalize_color(color):
    if isinstance(color, str):
        color = color.strip()
        if color.startswith("#"):
            color = color.lstrip("#")
            if len(color) == 3:
                color = "".join(ch * 2 for ch in color)
            if len(color) == 6:
                return tuple(int(color[index:index + 2], 16) for index in (0, 2, 4))
        return (255, 255, 255)

    if isinstance(color, (list, tuple)):
        return tuple(int(component) for component in color)

    return (255, 255, 255)


def get_clock_display_strings(now=None):
    now = now or datetime.datetime.now()
    time_text = now.strftime("%I:%M:%S %p")
    date_text = now.strftime("%a %m/%d/%Y")
    return time_text, date_text


def get_clock_text_positions(rect, time_surface, date_surface):
    text_width = max(time_surface.get_width(), date_surface.get_width())
    text_height = time_surface.get_height() + date_surface.get_height() + 4
    text_x = max(rect.left - text_width - 8, 0)
    text_y = max(rect.centery - text_height // 2, 0)
    return text_x, text_y


def draw_clock(surface, rect=None, color=None):
    color = color or normalize_color(THEME.get("text", (255, 255, 255)))

    if rect is None:
        rect = pygame.Rect(surface.get_width() - 120, surface.get_height() - 130, 92, 92)

    center = rect.center
    radius = max(6, min(rect.width, rect.height) // 2 - 6)

    pygame.draw.circle(surface, color, center, radius, 2)

    for tick in range(12):
        angle = math.radians(90 - tick * 30)
        inner_x = center[0] + math.cos(angle) * (radius * 0.72)
        inner_y = center[1] - math.sin(angle) * (radius * 0.72)
        outer_x = center[0] + math.cos(angle) * (radius * 0.88)
        outer_y = center[1] - math.sin(angle) * (radius * 0.88)
        pygame.draw.line(surface, color, (int(inner_x), int(inner_y)), (int(outer_x), int(outer_y)), 1)

    now = datetime.datetime.now()
    hour_angle = math.radians(90 - ((now.hour % 12) * 30 + (now.minute / 2)))
    minute_angle = math.radians(90 - (now.minute * 6 + now.second / 10))
    second_angle = math.radians(90 - (now.second * 6))

    hour_end = (
        center[0] + math.cos(hour_angle) * (radius * 0.45),
        center[1] - math.sin(hour_angle) * (radius * 0.45),
    )
    minute_end = (
        center[0] + math.cos(minute_angle) * (radius * 0.68),
        center[1] - math.sin(minute_angle) * (radius * 0.68),
    )
    second_end = (
        center[0] + math.cos(second_angle) * (radius * 0.76),
        center[1] - math.sin(second_angle) * (radius * 0.76),
    )

    pygame.draw.line(surface, color, center, hour_end, 3)
    pygame.draw.line(surface, color, center, minute_end, 2)
    pygame.draw.line(surface, color, center, second_end, 1)
    pygame.draw.circle(surface, color, center, 4)

    time_text, date_text = get_clock_display_strings(now)
    base_font = pygame.font.SysFont(None, 16)
    time_surface = base_font.render(time_text, True, color)
    date_surface = base_font.render(date_text, True, color)

    text_x, text_y = get_clock_text_positions(rect, time_surface, date_surface)
    surface.blit(time_surface, (text_x, text_y))
    surface.blit(date_surface, (text_x, text_y + time_surface.get_height() + 2))

    return time_text, date_text