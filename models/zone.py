from __future__ import annotations


class Node:
    """One hub on the map."""
    VALID_ZONES = ["normal", "blocked", "restricted", "priority"]
    ZONE_COSTS: dict[str, float] = {
        "normal": 1.0,
        "restricted": 1.0,
        "blocked": 1_000_000.0,
        "priority": 0.99999,
    }

    def __init__(
        self,
        map_definition: str,
        name: str,
        x: int,
        y: int,
        zone: str = "normal",
        color: str | None = None,
        max_drone: int = 1,
    ) -> None:
        """Create a node."""
        if "-" in name or " " in name:
            raise ValueError(f"Invalid node name: '{name}'")
        if zone not in self.VALID_ZONES:
            raise ValueError(f"Invalid zone '{zone}'")
        if max_drone <= 0:
            raise ValueError("max_drone must be > 0")

        self.map_definition = map_definition
        self.name = name
        self.x = x
        self.y = y
        self.zone = zone
        self.color = color
        self.max_drone = max_drone
        self.cost: float = self.ZONE_COSTS[zone]
        self.connections: list[tuple[str, int]] = []

        if map_definition in ("start_hub", "end_hub", "w"):
            self.max_drone = 999_999

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Node({self.name!r}, zone={self.zone!r}, "
            f"pos=({self.x},{self.y}))"
        )