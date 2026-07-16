import pytest
import networkx as nx
from shapely.geometry import LineString

from src.w6_graph import build_corridor_path


def make_linear_graph():
    """
    4-node linear MultiDiGraph.
    Nodes: 0=(0,0), 1=(1000,0), 2=(2000,0), 3=(3000,0)
    Edges (bidirectional): 0-1 (1000m), 1-2 (1000m), 2-3 (1000m)
    """
    G = nx.MultiDiGraph()
    for i, (x, y) in enumerate([(0.0, 0.0), (1000.0, 0.0), (2000.0, 0.0), (3000.0, 0.0)]):
        G.add_node(i, x=x, y=y)
    for u, v in [(0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 2)]:
        G.add_edge(u, v, length=1000.0)
    return G


def make_y_graph():
    """
    Y-shaped graph: 3 terminals (0, 2, 4) with hub at node 1.
    Node coords: 0=(0,1000), 1=(0,0), 2=(1500,0), 3=(500,-1200), 4=(0,-1200)
    """
    G = nx.MultiDiGraph()
    coords = {0: (0.0, 1000.0), 1: (0.0, 0.0), 2: (1500.0, 0.0),
              3: (500.0, -1200.0), 4: (0.0, -1200.0)}
    for n, (x, y) in coords.items():
        G.add_node(n, x=x, y=y)
    edges = [
        (0, 1, 1000.0), (1, 0, 1000.0),
        (1, 2, 1500.0), (2, 1, 1500.0),
        (1, 4, 1200.0), (4, 1, 1200.0),
        (4, 3, 500.0),  (3, 4, 500.0),
    ]
    for u, v, w in edges:
        G.add_edge(u, v, length=w)
    return G


def test_two_terminal_path_returns_linestring():
    G = make_linear_graph()
    geom, route_km = build_corridor_path(G, [0, 3])
    assert isinstance(geom, LineString)
    assert not geom.is_empty


def test_two_terminal_route_km_correct():
    G = make_linear_graph()
    _, route_km = build_corridor_path(G, [0, 3])
    assert route_km == pytest.approx(3.0, rel=1e-3)


def test_three_terminal_mst_covers_all():
    G = make_y_graph()
    geom, route_km = build_corridor_path(G, [0, 2, 4])
    assert geom is not None
    assert not geom.is_empty
    assert route_km > 0.0


def test_single_terminal_returns_none():
    G = make_linear_graph()
    geom, route_km = build_corridor_path(G, [0])
    assert geom is None
    assert route_km == 0.0


def test_disconnected_terminals_returns_none():
    G = nx.MultiDiGraph()
    G.add_node(0, x=0.0, y=0.0)
    G.add_node(1, x=1000.0, y=0.0)
    # No edges
    geom, route_km = build_corridor_path(G, [0, 1])
    assert geom is None


def test_duplicate_terminal_treated_as_single():
    G = make_linear_graph()
    # [0, 0, 3] deduplicates to [0, 3]
    geom, route_km = build_corridor_path(G, [0, 0, 3])
    assert geom is not None


# --- Path-shaper regression: no phantom jumps ----------------------------------
import numpy as np
from src.w6_graph import corridor_path_tsp, corridor_trunk_diameter


def _max_segment_m(geom):
    xy = np.array(geom.coords)
    if len(xy) < 2:
        return 0.0
    return float(np.hypot(np.diff(xy[:, 0]), np.diff(xy[:, 1])).max())


def _node_coords(geom):
    return {(round(x, 3), round(y, 3)) for x, y in geom.coords}


def test_tsp_path_has_no_phantom_jumps():
    # The Y-graph's longest real edge is 1500m; a flattened MST would jump between
    # branches (>1500m straight). The TSP path must never exceed the real edge length.
    G = make_y_graph()
    geom, km = corridor_path_tsp(G, [0, 2, 4])
    assert geom is not None and km > 0
    assert _max_segment_m(geom) <= 1500.0 + 1e-6


def test_tsp_path_visits_all_terminals():
    G = make_y_graph()
    geom, _ = corridor_path_tsp(G, [0, 2, 4])
    pts = _node_coords(geom)
    for term in [(0.0, 1000.0), (1500.0, 0.0), (0.0, -1200.0)]:
        assert term in pts


def test_trunk_diameter_has_no_phantom_jumps():
    G = make_y_graph()
    geom, km = corridor_trunk_diameter(G, [0, 2, 4])
    assert geom is not None and km > 0
    assert _max_segment_m(geom) <= 1500.0 + 1e-6


def test_trunk_diameter_spans_two_farthest_terminals():
    # Diameter of the Y is terminal 0 (top) to terminal 2 (right arm), the longest
    # leaf-to-leaf path; the short arm to terminal 4 may be dropped.
    G = make_y_graph()
    geom, _ = corridor_trunk_diameter(G, [0, 2, 4])
    pts = _node_coords(geom)
    assert (0.0, 1000.0) in pts and (1500.0, 0.0) in pts
