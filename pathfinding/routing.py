from __future__ import annotations
import heapq
from collections import defaultdict
from dataclasses import dataclass, field
from models.zone import Node
from models.drone import Drone, WAIT_X

WAIT_NODE = Node("w", "w", WAIT_X, WAIT_X)
MAX_SEARCH_TIME = 300


@dataclass
class SearchState:
    cost: float
    time: int
    current_node: str
    path: list = field(default_factory=list)

    def __lt__(self, other):
        return self.cost < other.cost


class Pathfinder:
    def __init__(self, drones: list[Drone], nodes: list[Node]) -> None:
        self.node_map        = {node.name: node for node in nodes}
        self.start_node      = nodes[0].name
        self.end_node        = nodes[-1].name
        self.node_reservations = defaultdict(lambda: defaultdict(int))
        self.link_reservations = defaultdict(lambda: defaultdict(int))

        for drone in drones:
            best_path = self._find_path()
            self._reserve_path(best_path)
            drone.path = [
                WAIT_NODE if next_node == current_node else self.node_map[next_node]
                for (current_node, _), (next_node, _) in zip(best_path, best_path[1:])
            ]

    def _find_path(self) -> list[tuple[str, int]]:
        heap = [SearchState(0.0, 0, self.start_node, [(self.start_node, 0)])]
        best_cost = {(self.start_node, 0): 0.0}

        while heap:
            state = heapq.heappop(heap)

            if state.cost > best_cost.get((state.current_node, state.time), float("inf")):
                continue
            if state.current_node == self.end_node:
                return state.path
            if state.time >= MAX_SEARCH_TIME:
                continue

            for next_node, delta_time, move_cost in self._get_edges(state.current_node, state.time):
                new_cost     = state.cost + move_cost
                new_time     = state.time + delta_time
                new_path     = state.path + [(next_node, new_time)]

                if new_cost < best_cost.get((next_node, new_time), float("inf")):
                    best_cost[(next_node, new_time)] = new_cost
                    heapq.heappush(heap, SearchState(new_cost, new_time, next_node, new_path))

        raise ValueError(f"No path found: {self.start_node} → {self.end_node}")

    def _get_edges(self, current: str, time: int) -> list[tuple[str, int, float]]:
        current_node = self.node_map[current]

        can_wait = current == self.start_node or \
                   self.node_reservations[time+1][current] < current_node.max_drone
        wait_edge = [(current, 1, 1.0)] if can_wait else []

        def get_move_edge(neighbor: str, link_capacity: int) -> tuple | None:
            neighbor_node = self.node_map[neighbor]
            link_key      = frozenset([current, neighbor])

            if neighbor_node.zone == "blocked":
                return None
            if self.link_reservations[time][link_key] >= link_capacity:
                return None

            if neighbor_node.zone == "restricted":
                link_is_full_next  = self.link_reservations[time+1][link_key] >= link_capacity
                node_is_full       = neighbor != self.end_node and \
                                     self.node_reservations[time+2][neighbor] >= neighbor_node.max_drone
                if link_is_full_next or node_is_full:
                    return None
                return (neighbor, 2, 2.0)
            else:
                node_is_full = neighbor != self.end_node and \
                               self.node_reservations[time+1][neighbor] >= neighbor_node.max_drone
                if node_is_full:
                    return None
                return (neighbor, 1, neighbor_node.cost)

        move_edges = [
            edge
            for neighbor, capacity in current_node.connections
            if (edge := get_move_edge(neighbor, capacity))
        ]

        return wait_edge + move_edges

    def _reserve_path(self, path: list[tuple[str, int]]) -> None:
        for (current_node, current_time), (next_node, next_time) in zip(path, path[1:]):
            link_key = frozenset([current_node, next_node])

            if next_node == current_node:
                for step in range(current_time+1, next_time+1):
                    if current_node != self.start_node:
                        self.node_reservations[step][current_node] += 1

            elif self.node_map[next_node].zone == "restricted":
                self.link_reservations[current_time][link_key]   += 1
                self.link_reservations[current_time+1][link_key] += 1
                if next_node != self.end_node:
                    self.node_reservations[next_time][next_node] += 1

            else:
                self.link_reservations[current_time][link_key] += 1
                if next_node != self.end_node:
                    self.node_reservations[next_time][next_node] += 1