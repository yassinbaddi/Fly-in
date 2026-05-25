from __future__ import annotations
import heapq
from models.zone import Node
from models.drone import Drone
from models.drone import WAIT_X


def _wait_node() -> Node:
    """Return a virtual one-turn wait node."""
    return Node("w", "w", WAIT_X, WAIT_X)


class Pathfinder:
    """Assign collision-free space-time paths to every drone."""

    def __init__(self, drones: list[Drone], nodes: list[Node]) -> None:
        """Run pathfinding immediately."""
        self.drones = drones
        self.nodes = nodes
        self._assign_paths()

    def _assign_paths(self) -> None:
        """Assign a collision-free path to each drone in turn using Space-Time Dijkstra."""
        start = self.nodes[0]
        end = self.nodes[-1]
        node_map = {n.name: n for n in self.nodes}

        # Global reservation tables
        node_reservations: dict[int, dict[str, int]] = {}
        link_reservations: dict[int, dict[frozenset[str], int]] = {}

        def get_node_res(t: int, name: str) -> int:
            return node_reservations.get(t, {}).get(name, 0)

        def get_link_res(t: int, u: str, v: str) -> int:
            return link_reservations.get(t, {}).get(frozenset([u, v]), 0)

        def reserve_node(t: int, name: str) -> None:
            node_reservations.setdefault(t, {})
            node_reservations[t][name] = node_reservations[t].get(name, 0) + 1

        def reserve_link(t: int, u: str, v: str) -> None:
            key = frozenset([u, v])
            link_reservations.setdefault(t, {})
            link_reservations[t][key] = link_reservations[t].get(key, 0) + 1

        for drone in self.drones:
            # Heap contains: (cost, time, current_node_name, path_of_states)
            heap: list[tuple[float, int, str, list[tuple[str, int]]]] = []
            heapq.heappush(heap, (0.0, 0, start.name, [(start.name, 0)]))

            visited: dict[tuple[str, int], float] = {(start.name, 0): 0.0}
            best_path: list[tuple[str, int]] | None = None

            max_search_time = 300

            while heap:
                cost, t, u, path_states = heapq.heappop(heap)

                if cost > visited.get((u, t), float("inf")):
                    continue

                if u == end.name:
                    best_path = path_states
                    break

                if t >= max_search_time:
                    continue

                u_node = node_map[u]

                # Transition 1: Wait in place at u
                if u == start.name or get_node_res(t + 1, u) < u_node.max_drone:
                    new_cost = cost + 1.0
                    if new_cost < visited.get((u, t + 1), float("inf")):
                        visited[(u, t + 1)] = new_cost
                        heapq.heappush(heap, (new_cost, t + 1, u, path_states + [(u, t + 1)]))

                # Transitions 2 & 3: Move to neighbors
                for v_name, cap in u_node.connections:
                    v_node = node_map[v_name]
                    if v_node.zone == "blocked":
                        continue

                    if get_link_res(t, u, v_name) >= cap:
                        continue

                    if v_node.zone == "restricted":
                        # Multi-turn movement: takes 2 turns (arrives at t+2)
                        if get_link_res(t + 1, u, v_name) >= cap:
                            continue
                        if v_name != end.name and get_node_res(t + 2, v_name) >= v_node.max_drone:
                            continue

                        new_cost = cost + 2.0
                        if new_cost < visited.get((v_name, t + 2), float("inf")):
                            visited[(v_name, t + 2)] = new_cost
                            heapq.heappush(heap, (new_cost, t + 2, v_name, path_states + [(v_name, t + 2)]))
                    else:
                        # Normal / Priority: takes 1 turn (arrives at t+1)
                        if v_name != end.name and get_node_res(t + 1, v_name) >= v_node.max_drone:
                            continue

                        new_cost = cost + v_node.cost
                        if new_cost < visited.get((v_name, t + 1), float("inf")):
                            visited[(v_name, t + 1)] = new_cost
                            heapq.heappush(heap, (new_cost, t + 1, v_name, path_states + [(v_name, t + 1)]))

            if best_path is None:
                raise ValueError(f"No collision-free path found for drone {drone.id}")

            # Reserve path in global tracking tables
            for i in range(len(best_path) - 1):
                u, tu = best_path[i]
                v, tv = best_path[i + 1]

                if v == u:
                    for step in range(tu + 1, tv + 1):
                        if u != start.name:
                            reserve_node(step, u)
                else:
                    v_node = node_map[v]
                    if v_node.zone == "restricted":
                        reserve_link(tu, u, v)
                        reserve_link(tu + 1, u, v)
                        if v != end.name:
                            reserve_node(tv, v)
                    else:
                        reserve_link(tu, u, v)
                        if v != end.name:
                            reserve_node(tv, v)

            # Convert space-time sequence to standard path list
            drone_path_nodes: list[Node] = []
            for i in range(len(best_path) - 1):
                u, tu = best_path[i]
                v, tv = best_path[i + 1]
                if v == u:
                    drone_path_nodes.append(_wait_node())
                else:
                    drone_path_nodes.append(node_map[v])

            drone.path = drone_path_nodes