import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame
from ui.clock import get_clock_text_positions


pygame.init()
pygame.font.init()


def test_clock_text_positions_stay_left_of_rect():
    rect = pygame.Rect(100, 20, 32, 32)
    time_surface = pygame.font.SysFont(None, 12).render("12:34 PM", True, (255, 255, 255))
    date_surface = pygame.font.SysFont(None, 12).render("Mon 06/09/2026", True, (255, 255, 255))

    text_x, text_y = get_clock_text_positions(rect, time_surface, date_surface)

    assert text_x < rect.left
    assert text_y >= 0
