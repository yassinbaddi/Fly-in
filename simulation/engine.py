
from __future__ import annotations
from typing import Callable
from models.zone import Node
from models.drone import Drone

Snapshot = dict[int, dict[str, object]]
StepCallback = Callable[[int, Snapshot], None]


class Simulation:
    """Run the simulation and print output each turn."""

    def __init__(self, drones: list[Drone], nodes: list[Node]) -> None:
        """Store drones and nodes."""
        self.drones = drones
        self.nodes = nodes

    def run(self, on_step: StepCallback | None = None) -> int:
        """Run until all drones arrive. Returns total turns."""
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
                if d.restricted_buffer > 0 and d.path:
                    parts.append(
                        f"D{d.id}-{prev[d.id].name}-{d.path[0].name}"
                    )
                elif curr is not prev[d.id]:
                    parts.append(f"D{d.id}-{curr.name}")
                prev[d.id] = curr

            # Per spec, print empty lines if no output is generated for a turn
            print(" ".join(parts))

            if on_step is not None:
                snapshot: Snapshot = {
                    d.id: {
                        "zone":    d.current_zone.name,
                        "arrived": d.is_arrived,
                        "buffer":  d.restricted_buffer,
                    }
                    for d in self.drones
                }
                on_step(turns, snapshot)

        return turns