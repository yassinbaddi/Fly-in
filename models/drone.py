from __future__ import annotations
from models.zone import Node

WAIT_X = -1


class Drone:
    """A drone that follows a pre-assigned path."""

    def __init__(self, drone_id: int, start_zone: Node) -> None:
        """Create a drone at start_zone."""
        self.id = drone_id
        self.current_zone = start_zone
        self.is_arrived = False
        self.path: list[Node] = []
        self.restricted_buffer = 0

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Drone(id={self.id}, zone={self.current_zone.name!r}, "
            f"arrived={self.is_arrived})"
        )

    def action(self) -> None:
        """Advance one simulation turn."""
        if self.is_arrived or not self.path:
            return

        if self.restricted_buffer > 0:
            self.restricted_buffer -= 1
            if self.restricted_buffer == 0:
                self.current_zone = self.path.pop(0)
                if self.current_zone.map_definition == "end_hub":
                    self.is_arrived = True
            return

        if self.path[0].x == WAIT_X:
            self.path.pop(0)
            return

        if self.path[0].zone == "restricted":
            self.restricted_buffer = 1
            return

        self.current_zone = self.path.pop(0)
        if self.current_zone.map_definition == "end_hub":
            self.is_arrived = True