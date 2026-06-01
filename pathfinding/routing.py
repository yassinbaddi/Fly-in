from __future__ import annotations

import heapq
from collections import defaultdict

from models.zone import Node
from models.drone import Drone, WAIT_X

WAIT_NODE = Node("w", "w", WAIT_X, WAIT_X)


class Pathfinder:
    def __init__(self, drones: list[Drone], nodes: list[Node]) -> None:
        self.node_map = {node.name: node for node in nodes}
        self.start    = nodes[0].name
        self.end      = nodes[-1].name
        self.reserved = defaultdict(int)

        for drone in drones:
            path = self._find_path()
            self._reserve(path)
            drone.path = [
                WAIT_NODE if b == a else self.node_map[b]
                for (a, _), (b, _) in zip(path, path[1:])
            ]
            

    def _find_path(self) -> list[tuple[str, int]]:
        heap   = [(0.0, 0, self.start)]
        best   = {(self.start, 0): 0.0}
        parent = {}

        while heap:
            cost, time, node = heapq.heappop(heap)

            if cost > best.get((node, time), float("inf")):
                continue
            if node == self.end:
                path, state = [], (node, time)
                while state in parent:
                    path.append(state)
                    state = parent[state]
                path.append(state)
                path.reverse()
                return path

            for neighbor, dt, edge_cost in self._edges(node, time):
                state = (neighbor, time + dt)
                new_cost = cost + edge_cost

                if new_cost < best.get(state, float("inf")):
                    best[state]   = new_cost
                    parent[state] = (node, time)
                    heapq.heappush(heap, (new_cost, time + dt, neighbor))

        raise ValueError(f"No path found: {self.start} -> {self.end}")

    def _edges(self, current: str, time: int) -> list[tuple[str, int, float]]:
        node  = self.node_map[current]
        edges = [(current, 1, 1.0)]

        for neighbor, capacity in node.connections:
            n    = self.node_map[neighbor]
            link = frozenset((current, neighbor))

            if n.zone == "blocked":
                continue

            dur = 2 if n.zone == "restricted" else 1

            if any(self.reserved[(time + dt, link)] >= capacity for dt in range(dur)):
                continue
            if neighbor != self.end and self.reserved[(time + dur, neighbor)] >= n.max_drone:
                continue

            edges.append((neighbor, dur, 2.0 if n.zone == "restricted" else n.cost))

        return edges

    def _reserve(self, path: list[tuple[str, int]]) -> None:
        for (a, t), (b, t2) in zip(path, path[1:]):
            if b == a:
                for step in range(t + 1, t2 + 1):
                    self.reserved[(step, a)] += 1
            else:
                for dt in range(t2 - t):
                    self.reserved[(t + dt, frozenset((a, b)))] += 1
                if b != self.end:
                    self.reserved[(t2, b)] += 1