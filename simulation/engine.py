import sys
from typing import Callable
from models.zone import Node
from models.drone import Drone


RESET = "\033[0m"
COLORS = [
    "\033[31m",  # red
    "\033[33m",  # yellow
    "\033[32m",  # green
    "\033[36m",  # cyan
    "\033[34m",  # blue
    "\033[35m",  # magenta
]


def color_for(i: int) -> str:
    return COLORS[i % len(COLORS)]


ART = r"""
    ___       ___       ___            ___       ___   
   /\  \     /\__\     /\__\          /\  \     /\__\  
  /::\  \   /:/  /    |::L__L        _\:\  \   /:| _|_ 
 /::\:\__\ /:/__/     |:::\__\      /\/::\__\ /::|/\__\
 \/\:\/__/ \:\  \     /:;;/__/      \::/\/__/ \/|::/  /
    \/__/   \:\__\    \/__/          \:\__\     |:/  / 
             \/__/                    \/__/     \/__/  
"""


def print_banner() -> None:
    """Print rainbow ASCII art once at start."""
    color_index = 0

    for line in ART.splitlines():
        for ch in line:
            if ch.strip():
                sys.stdout.write(
                    color_for(color_index) + ch + RESET
                )
                color_index += 1
            else:
                sys.stdout.write(ch)

        sys.stdout.write("\n")



Snapshot = dict[int, dict[str, object]]
StepCallback = Callable[[int, Snapshot], None]


class Simulation:
    """Drone simulation with colored terminal output + banner."""

    def __init__(self, drones: list[Drone], nodes: list[Node]) -> None:
        self.drones = drones
        self.nodes = nodes

    def run(self, on_step: StepCallback | None = None) -> int:
        print_banner()

        prev: dict[int, Node] = {d.id: d.current_zone for d in self.drones}
        turns = 0

        while not all(d.is_arrived for d in self.drones):
            turns += 1

            for d in self.drones:
                if not d.is_arrived:
                    d.action()

            parts: list[str] = []

            for d in self.drones:
                curr = d.current_zone
                col = color_for(d.id)

                if d.restricted_buffer > 0 and d.path:
                    parts.append(
                        f"{col}D{d.id}-{prev[d.id].name}->{d.path[0].name}{RESET}"
                    )

                elif curr is not prev[d.id]:
                    parts.append(
                        f"{col}D{d.id}-{curr.name}{RESET}"
                    )

                prev[d.id] = curr

            print(" ".join(parts))

            if on_step:
                snapshot: Snapshot = {
                    d.id: {
                        "zone": d.current_zone.name,
                        "arrived": d.is_arrived,
                        "buffer": d.restricted_buffer,
                    }
                    for d in self.drones
                }
                on_step(turns, snapshot)

        return turns