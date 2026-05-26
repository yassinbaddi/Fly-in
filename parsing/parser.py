"""Map file parser."""
from __future__ import annotations

from typing import TextIO

from models.zone import Node
from models.drone import Drone


VALID_ZONES = {"normal", "restricted", "priority", "blocked"}
HUB_TYPES = {"start_hub", "hub", "end_hub"}
HUB_ATTRS = {"zone", "color", "max_drones"}
CONN_ATTRS = {"max_link_capacity"}


class Parser:
    """Parse a map file into nodes and drones."""

    def __init__(self, file_obj: TextIO) -> None:
        """Initialize parser and start parsing the file."""
        self.nodes: list[Node] = []
        self.drones: list[Drone] = []
        self._seen_names: set[str] = set()
        self._seen_positions: set[tuple[int, int]] = set()
        self._seen_connections: set[frozenset[str]] = set()
        self._parse(file_obj)

    @staticmethod
    def _extract_attrs(text: str, nu_line: int) -> tuple[str, str]:
        """Split 'body [key=val ...]' → (body, attrs_string)."""
        if "[" not in text:
            return text.strip(), ""
        before, _, after = text.partition("[")
        if "]" not in after:
            raise ValueError(f"line {nu_line}: missing closing ']'")
        inside, _, trailing = after.partition("]")
        if trailing.strip():
            raise ValueError(
                f"line {nu_line}: unexpected content after ']': "
                f"{trailing.strip()!r}"
            )
        return before.strip(), inside.strip()

    @staticmethod
    def _parse_metadata(
        raw: str,
        allowed: set[str],
        nu_line: int
            ) -> dict[str, str]:
        """Parse 'key=val key2=val2' into a dict."""
        result: dict[str, str] = {}
        if not raw:
            return result
        for token in raw.split():
            if "=" not in token:
                raise ValueError(
                    f"line {nu_line}: expected key=value, got {token!r}"
                )
            key, _, val = token.partition("=")
            if not key or not val:
                raise ValueError(
                    f"line {nu_line}: empty key or value in {token!r}"
                )
            if key not in allowed:
                raise ValueError(
                    f"line {nu_line}: unknown attribute {key!r}"
                )
            if key in result:
                raise ValueError(
                    f"line {nu_line}: duplicated attribute {key!r}"
                )
            result[key] = val
        return result

    @staticmethod
    def _to_int(value: str, name: str, nu_line: int) -> int:
        """Convert string to int with a clear error."""
        try:
            return int(value)
        except ValueError:
            raise ValueError(
                f"line {nu_line}: {name} must be an integer, got {value!r}"
            )

    # ===== Main parser =====

    def _parse(self, f: TextIO) -> None:
        """Parse the full input file."""
        nb_drones: int | None = None
        start_node: Node | None = None
        end_node: Node | None = None
        in_connections = False

        for nu_line, raw in enumerate(f, 1):
            line = raw.split("#", 1)[0].strip()

            if not line:
                continue

            if ":" not in line:
                raise ValueError(
                    f"line {nu_line}: expected 'keyword: ...', got {line!r}"
                )

            keyword, _, rest = line.partition(":")
            keyword = keyword.strip()
            rest = rest.strip()

            # -- nb_drones --
            if keyword == "nb_drones":
                if nb_drones is not None:
                    raise ValueError(f"line {nu_line}: duplicated nb_drones")
                if self.nodes:
                    raise ValueError(
                        f"line {nu_line}: nb_drones must be the first"
                    )
                nb_drones = self._to_int(rest, "nb_drones", nu_line)
                if nb_drones <= 0:
                    raise ValueError(
                        f"line {nu_line}: nb_drones must be positive,"
                        f"got {nb_drones}"
                    )
                continue

            # -- hub --
            if keyword in HUB_TYPES:
                if in_connections:
                    raise ValueError(
                        f"line {nu_line}: hubs must appear before connections"
                    )
                node = self._parse_hub(keyword, rest, nu_line)
                self.nodes.append(node)

                if keyword == "start_hub":
                    if start_node is not None:
                        raise ValueError(
                            f"line {nu_line}: duplicated start_hub"
                        )
                    start_node = node
                elif keyword == "end_hub":
                    if end_node is not None:
                        raise ValueError(
                            f"line {nu_line}: duplicated end_hub"
                        )
                    end_node = node
                continue

            # -- connection --
            if keyword == "connection":
                in_connections = True
                self._parse_connection(rest, nu_line)
                continue

            raise ValueError(
                f"line {nu_line}: unknown keyword {keyword!r}"
            )

        if nb_drones is None:
            raise ValueError("missing nb_drones declaration")
        if start_node is None:
            raise ValueError("missing start_hub")
        if end_node is None:
            raise ValueError("missing end_hub")

        middle = []
        for n in self.nodes:
            if n is not start_node and n is not end_node:
                middle.append(n)
        self.nodes = [start_node] + middle + [end_node]
        self.drones = [Drone(i, start_node) for i in range(1, nb_drones + 1)]

    # --- Hub ---
    def _parse_hub(self, kind: str, rest: str, nu_line: int) -> Node:
        """Parse a hub definition line."""
        body, raw_attrs = self._extract_attrs(rest, nu_line)

        parts = body.split()

        if len(parts) < 1:
            raise ValueError(f"line {nu_line}: missing hub name")
        if len(parts) < 3:
            raise ValueError(
                f"line {nu_line}: hub {parts[0]!r} needs 'name x y', "
                f"got only {len(parts)} token(s)"
            )
        if len(parts) > 3:
            raise ValueError(
                f"line {nu_line}: unexpected extra tokens after coordinates: "
                f"{' '.join(parts[3:])!r}"
            )

        name, raw_x, raw_y = parts
        x = self._to_int(raw_x, f"hub {name!r} x-coordinate", nu_line)
        y = self._to_int(raw_y, f"hub {name!r} y-coordinate", nu_line)

        if name in self._seen_names:
            raise ValueError(f"line {nu_line}: duplicated hub name {name!r}")
        if (x, y) in self._seen_positions:
            raise ValueError(
                f"line {nu_line}: position ({x}, {y}) "
                f"already used by another hub"
            )

        attrs = self._parse_metadata(raw_attrs, HUB_ATTRS, nu_line)

        zone = attrs.get("zone", "normal")
        if zone not in VALID_ZONES:
            raise ValueError(
                f"line {nu_line}: invalid zone {zone!r}, "
                f"expected one of {sorted(VALID_ZONES)}"
            )

        color = attrs.get("color")

        max_drones = 1
        if "max_drones" in attrs:
            v = attrs["max_drones"]
            max_drones = self._to_int(v, "max_drones", nu_line)
            if max_drones <= 0:
                raise ValueError(
                    f"line {nu_line}: max_drones must be positive, "
                    f"got {max_drones}"
                )

        self._seen_names.add(name)
        self._seen_positions.add((x, y))

        return Node(kind, name, x, y, zone, color, max_drones)

    # --- Connection ---

    def _parse_connection(self, rest: str, nu_line: int) -> None:
        """Parse a connection between two hubs."""
        body, raw_attrs = self._extract_attrs(rest, nu_line)

        if "-" not in body:
            raise ValueError(
                f"line {nu_line}: connection must be 'src-dst', got {body!r}"
            )

        parts = body.split("-")
        if len(parts) != 2:
            raise ValueError(
                f"line {nu_line}: connection must have exactly one '-', "
                f"got {body!r}"
            )

        src, dst = parts[0].strip(), parts[1].strip()

        if not src:
            raise ValueError(f"line {nu_line}: missing source hub name")
        if not dst:
            raise ValueError(f"line {nu_line}: missing destination hub name")

        node_map = {n.name: n for n in self.nodes}

        if src not in node_map:
            raise ValueError(f"line {nu_line}: unknown hub {src!r}")
        if dst not in node_map:
            raise ValueError(f"line {nu_line}: unknown hub {dst!r}")

        edge = frozenset((src, dst))
        if edge in self._seen_connections:
            raise ValueError(
                f"line {nu_line}: connection {src}-{dst} already exists"
            )

        attrs = self._parse_metadata(raw_attrs, CONN_ATTRS, nu_line)

        capacity = 1
        if "max_link_capacity" in attrs:
            capacity = self._to_int(
                attrs["max_link_capacity"], "max_link_capacity", nu_line
            )
            if capacity <= 0:
                raise ValueError(
                    f"line {nu_line}: max_link_capacity must be positive, "
                    f"got {capacity}"
                )

        self._seen_connections.add(edge)
        node_map[src].connections.append((dst, capacity))
        node_map[dst].connections.append((src, capacity))
