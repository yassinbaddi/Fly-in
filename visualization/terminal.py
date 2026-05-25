
"""Terminal colour map."""
from __future__ import annotations

COLOR_MAP: dict[str, str] = {
    "green":   "\033[32m", "red":     "\033[31m",
    "yellow":  "\033[33m", "blue":    "\033[34m",
    "orange":  "\033[38;5;208m", "purple": "\033[35m",
    "cyan":    "\033[36m", "magenta": "\033[35m",
    "white":   "\033[37m", "black":   "\033[90m",
    "brown":   "\033[38;5;130m", "gold":   "\033[38;5;220m",
    "lime":    "\033[38;5;154m", "gray":   "\033[90m",
    "grey":    "\033[90m",
}