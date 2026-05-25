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
        self.nodes: list[Node] = []
        self.drones: list[Drone] = []
        self._seen_names: set[str] = set()
        # self._seen_positions: set[tuple[int, int]] = set()
        self._seen_connections: set[frozenset[str]] = set()
        self._parse(file_obj)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_line(raw: str) -> str:
        """Strip inline comments (outside brackets) and whitespace."""
        depth = 0
        for i, ch in enumerate(raw):
            if ch == "[":
                depth += 1
            elif ch == "]" and depth > 0:
                depth -= 1
            elif ch == "#" and depth == 0:
                return raw[:i].strip()
        return raw.strip()

    @staticmethod
    def _extract_attrs(text: str, lineno: int) -> tuple[str, str]:
        """Split 'body [key=val ...]' → (body, attrs_string)."""
        if "[" not in text:
            return text.strip(), ""
        before, _, after = text.partition("[")
        if "]" not in after:
            raise ValueError(f"line {lineno}: missing closing ']'")
        inside, _, trailing = after.partition("]")
        if trailing.strip():
            raise ValueError(
                f"line {lineno}: unexpected content after ']': {trailing.strip()!r}"
            )
        return before.strip(), inside.strip()

    @staticmethod
    def _parse_kv(raw: str, allowed: set[str], lineno: int) -> dict[str, str]:
        """Parse 'key=val key2=val2' into a dict."""
        result: dict[str, str] = {}
        if not raw:
            return result
        for token in raw.split():
            if "=" not in token:
                raise ValueError(
                    f"line {lineno}: expected key=value, got {token!r}"
                )
            key, _, val = token.partition("=")
            if not key or not val:
                raise ValueError(
                    f"line {lineno}: empty key or value in {token!r}"
                )
            if key not in allowed:
                raise ValueError(
                    f"line {lineno}: unknown attribute {key!r}"
                )
            if key in result:
                raise ValueError(
                    f"line {lineno}: duplicated attribute {key!r}"
                )
            result[key] = val
        return result

    @staticmethod
    def _to_int(value: str, name: str, lineno: int) -> int:
        """Convert string to int with a clear error."""
        try:
            return int(value)
        except ValueError:
            raise ValueError(
                f"line {lineno}: {name} must be an integer, got {value!r}"
            )

    # ------------------------------------------------------------------
    # Main parser
    # ------------------------------------------------------------------

    def _parse(self, f: TextIO) -> None:
        nb_drones: int | None = None
        start_node: Node | None = None
        end_node: Node | None = None
        in_connections = False

        for lineno, raw in enumerate(f, 1):
            line = self._clean_line(raw)
            if not line:
                continue

            if ":" not in line:
                raise ValueError(
                    f"line {lineno}: expected 'keyword: ...', got {line!r}"
                )

            keyword, _, rest = line.partition(":")
            keyword = keyword.strip()
            rest = rest.strip()

            # -- nb_drones --
            if keyword == "nb_drones":
                if nb_drones is not None:
                    raise ValueError(f"line {lineno}: duplicated nb_drones")
                if self.nodes:
                    raise ValueError(
                        f"line {lineno}: nb_drones must appear before any hub"
                    )
                nb_drones = self._to_int(rest, "nb_drones", lineno)
                if nb_drones <= 0:
                    raise ValueError(
                        f"line {lineno}: nb_drones must be positive, got {nb_drones}"
                    )
                continue

            if nb_drones is None:
                raise ValueError(
                    f"line {lineno}: nb_drones must be the first "
                    f"non-comment line, got {keyword!r}"
                )

            # -- hub --
            if keyword in HUB_TYPES:
                if in_connections:
                    raise ValueError(
                        f"line {lineno}: hubs must appear before connections"
                    )
                node = self._parse_hub(keyword, rest, lineno)
                self.nodes.append(node)

                if keyword == "start_hub":
                    if start_node is not None:
                        raise ValueError(
                            f"line {lineno}: duplicated start_hub"
                        )
                    start_node = node
                elif keyword == "end_hub":
                    if end_node is not None:
                        raise ValueError(
                            f"line {lineno}: duplicated end_hub"
                        )
                    end_node = node
                continue

            # -- connection --
            if keyword == "connection":
                in_connections = True
                self._parse_connection(rest, lineno)
                continue

            raise ValueError(
                f"line {lineno}: unknown keyword {keyword!r}"
            )

        # -- final checks --
        if nb_drones is None:
            raise ValueError("missing nb_drones declaration")
        if start_node is None:
            raise ValueError("missing start_hub")
        if end_node is None:
            raise ValueError("missing end_hub")

        # Pathfinder expects start at index 0 and end at index -1
        middle = [n for n in self.nodes if n is not start_node and n is not end_node]
        self.nodes = [start_node] + middle + [end_node]
        self.drones = [Drone(i, start_node) for i in range(1, nb_drones + 1)]

    # ------------------------------------------------------------------
    # Hub
    # ------------------------------------------------------------------

    def _parse_hub(self, kind: str, rest: str, lineno: int) -> Node:
        body, raw_attrs = self._extract_attrs(rest, lineno)
        parts = body.split()

        if len(parts) < 1:
            raise ValueError(f"line {lineno}: missing hub name")
        if len(parts) < 3:
            raise ValueError(
                f"line {lineno}: hub {parts[0]!r} needs 'name x y', "
                f"got only {len(parts)} token(s)"
            )
        if len(parts) > 3:
            raise ValueError(
                f"line {lineno}: unexpected extra tokens after coordinates: "
                f"{' '.join(parts[3:])!r}"
            )

        name, raw_x, raw_y = parts
        x = self._to_int(raw_x, f"hub {name!r} x-coordinate", lineno)
        y = self._to_int(raw_y, f"hub {name!r} y-coordinate", lineno)

        if name in self._seen_names:
            raise ValueError(f"line {lineno}: duplicated hub name {name!r}")
        # if (x, y) in self._seen_positions:
        #     raise ValueError(
        #         f"line {lineno}: position ({x}, {y}) already used by another hub"
        #     )

        attrs = self._parse_kv(raw_attrs, HUB_ATTRS, lineno)

        zone = attrs.get("zone", "normal")
        if zone not in VALID_ZONES:
            raise ValueError(
                f"line {lineno}: invalid zone {zone!r}, "
                f"expected one of {sorted(VALID_ZONES)}"
            )

        color = attrs.get("color")

        max_drones = 1
        if "max_drones" in attrs:
            max_drones = self._to_int(attrs["max_drones"], "max_drones", lineno)
            if max_drones <= 0:
                raise ValueError(
                    f"line {lineno}: max_drones must be positive, got {max_drones}"
                )

        self._seen_names.add(name)
        # self._seen_positions.add((x, y))

        return Node(kind, name, x, y, zone, color, max_drones)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _parse_connection(self, rest: str, lineno: int) -> None:
        body, raw_attrs = self._extract_attrs(rest, lineno)

        if "-" not in body:
            raise ValueError(
                f"line {lineno}: connection must be 'src-dst', got {body!r}"
            )

        parts = body.split("-")
        if len(parts) != 2:
            raise ValueError(
                f"line {lineno}: connection must have exactly one '-', "
                f"got {body!r}"
            )

        src, dst = parts[0].strip(), parts[1].strip()

        if not src:
            raise ValueError(f"line {lineno}: missing source hub name")
        if not dst:
            raise ValueError(f"line {lineno}: missing destination hub name")

        node_map = {n.name: n for n in self.nodes}

        if src not in node_map:
            raise ValueError(f"line {lineno}: unknown hub {src!r}")
        if dst not in node_map:
            raise ValueError(f"line {lineno}: unknown hub {dst!r}")

        edge = frozenset((src, dst))
        if edge in self._seen_connections:
            raise ValueError(
                f"line {lineno}: connection {src}-{dst} already exists"
            )

        attrs = self._parse_kv(raw_attrs, CONN_ATTRS, lineno)

        capacity = 1
        if "max_link_capacity" in attrs:
            capacity = self._to_int(
                attrs["max_link_capacity"], "max_link_capacity", lineno
            )
            if capacity <= 0:
                raise ValueError(
                    f"line {lineno}: max_link_capacity must be positive, "
                    f"got {capacity}"
                )

        self._seen_connections.add(edge)
        node_map[src].connections.append((dst, capacity))
        node_map[dst].connections.append((src, capacity))