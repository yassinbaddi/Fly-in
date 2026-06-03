from __future__ import annotations
import heapq

from models.zone import Node
from models.drone import Drone, WAIT_X

WAIT_NODE = Node("w", "w", WAIT_X, WAIT_X)
MAX_TIME = 300


class Pathfinder:
    def __init__(self, drones: list[Drone], nodes: list[Node]) -> None:
        self.node_map = {n.name: n for n in nodes}
        self.start = nodes[0].name
        self.end = nodes[-1].name

        self.busy_nodes = set()
        self.busy_connection = set()

        for drone in drones:
            path = self._find_path()
            self._reserve(path)

            drone.path = [
                WAIT_NODE if a == b else self.node_map[b]
                for (a, _), (b, _) in zip(path, path[1:])
            ]

    def _find_path(self):
        heap: list[tuple[float, int, str]] = [(0, 0, self.start)]
        best = {}

        parent = {}

        while heap:
            cost, time, node = heapq.heappop(heap)

            if (node, time) in best and best[(node, time)] < cost:
                continue
            best[(node, time)] = cost

            if node == self.end:
                state = (node, time)
                path = [state]
                while state in parent:
                    state = parent[state]
                    path.append(state)
                path.reverse()
                return path

            if time >= MAX_TIME:
                continue

            for nxt, dt, edge_cost in self._connection(node, time):
                state = (nxt, time + dt)
                new_cost = cost + edge_cost

                if new_cost < best.get(state, float("inf")):
                    best[state] = new_cost
                    parent[state] = (node, time)
                    heapq.heappush(heap, (new_cost, time + dt, nxt))

        raise ValueError("No path found")

    def _connection(self, current, time):
        node = self.node_map[current]

        connection = [(current, 1, 1.0)]

        for neighbor, _ in node.connections:
            n = self.node_map[neighbor]

            if n.zone == "blocked":
                continue

            dur = 2 if n.zone == "restricted" else 1
            cost = 2.0 if dur == 2 else n.cost

            link = tuple(sorted((current, neighbor)))

            blocked = False

            for i in range(dur):
                if (time + i, link) in self.busy_connection:
                    blocked = True
                    break

            if blocked:
                continue

            if neighbor != self.end and (time + dur, neighbor) in self.busy_nodes:
                continue

            connection.append((neighbor, dur, cost))

        return connection

    def _reserve(self, path):
        for (a, t1), (b, t2) in zip(path, path[1:]):
            if a == b:
                self.busy_nodes.add((t1, a))
            else:
                link = (a, b)
                for t in range(t1, t2):
                    self.busy_connection.add((t, link))
                if b != self.end:
                    self.busy_nodes.add((t2, b))