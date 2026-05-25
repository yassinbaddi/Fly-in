from __future__ import annotations
from typing import Callable
from models.zone import Node
from models.drone import Drone

Snapshot = dict[int, dict[str, object]]
StepCallback = Callable[[int, Snapshot], None]

COLORS = [
    "\033[91m",
    "\033[92m",
    "\033[93m",
    "\033[94m",
    "\033[95m",
    "\033[96m",
]
RESET = "\033[0m"


def color_for(drone_id: int) -> str:
    return COLORS[drone_id % len(COLORS)]


class Simulation:
    """Run the simulation and print output each turn."""

    def __init__(self, drones: list[Drone], nodes: list[Node]) -> None:
        self.drones = drones
        self.nodes = nodes

    def run(self, on_step: StepCallback | None = None) -> int:
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

                color = color_for(d.id)

                if d.restricted_buffer > 0 and d.path:
                    parts.append(
                        f"{color}D{d.id}-{prev[d.id].name}-{d.path[0].name}{RESET}"
                    )

                elif curr is not prev[d.id]:
                    parts.append(
                        f"{color}D{d.id}-{curr.name}{RESET}"
                    )

                prev[d.id] = curr

            print(" ".join(parts))

            if on_step is not None:
                snapshot: Snapshot = {
                    d.id: {
                        "zone": curr.name,
                        "arrived": d.is_arrived,
                        "buffer": d.restricted_buffer,
                    }
                    for d in self.drones
                }
                on_step(turns, snapshot)

        return turns