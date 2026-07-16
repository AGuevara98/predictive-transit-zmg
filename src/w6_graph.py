"""
W6 OSM graph utilities: load/project the ZMG drive network, snap anchor
centroids to OSM nodes, and build an MST-based Steiner-approximation corridor
path between terminal nodes.
"""
import sys
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx
from shapely.geometry import LineString

from config import CRS_CANONICAL, ZMG_BBOX

OSM_CACHE = Path("data/osm_zmg_drive.graphml")


def load_or_download_osm(
    cache_path: Path = OSM_CACHE,
    bbox: Optional[Tuple[float, float, float, float]] = None,
) -> nx.MultiDiGraph:
    import osmnx as ox
    if cache_path.exists():
        print(f"  [OK] Loading OSM graph from cache: {cache_path}")
        return ox.load_graphml(filepath=str(cache_path))
    if bbox is None:
        bbox = (ZMG_BBOX["xmin"], ZMG_BBOX["ymin"], ZMG_BBOX["xmax"], ZMG_BBOX["ymax"])
    print("  [..] Downloading ZMG drive graph from OSM (may take 3-5 min)...")
    G = ox.graph_from_bbox(bbox=bbox, network_type="drive")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(G, filepath=str(cache_path))
    print(f"  [OK] OSM graph cached to {cache_path}")
    return G


def project_to_6372(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    import osmnx as ox
    return ox.project_graph(G, to_crs=CRS_CANONICAL)


def snap_to_osm_nodes(
    G_proj: nx.MultiDiGraph,
    cx_list: List[float],
    cy_list: List[float],
) -> List[int]:
    import osmnx as ox
    return list(ox.distance.nearest_nodes(G_proj, X=cx_list, Y=cy_list))


def build_corridor_path(
    G_proj: nx.MultiDiGraph,
    terminal_nodes: List[int],
) -> Tuple[Optional[LineString], float]:
    """
    MST-based Steiner approximation (Kou-Markowsky-Berman):
      1. Deduplicate terminals.
      2. Compute pairwise shortest-path lengths + node sequences between terminals.
      3. Build complete graph of terminals weighted by SP distances.
      4. MST of that graph.
      5. Expand each MST edge back to the actual OSM node sequence.
      6. Concatenate sequences into a LineString; accumulate length.

    Returns (LineString_EPSG6372, route_km) or (None, 0.0) if infeasible.
    """
    unique_terminals = list(dict.fromkeys(terminal_nodes))
    if len(unique_terminals) < 2:
        return None, 0.0

    dist_matrix: dict = {}
    path_matrix: dict = {}
    for i, u in enumerate(unique_terminals):
        for v in unique_terminals[i + 1:]:
            try:
                length = nx.shortest_path_length(G_proj, u, v, weight="length")
                path = nx.shortest_path(G_proj, u, v, weight="length")
                dist_matrix[(u, v)] = length
                path_matrix[(u, v)] = path
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass

    if not dist_matrix:
        return None, 0.0

    H = nx.Graph()
    for (u, v), d in dist_matrix.items():
        H.add_edge(u, v, weight=d)

    if H.number_of_edges() == 0:
        return None, 0.0

    mst = nx.minimum_spanning_tree(H, weight="weight")

    all_node_sequences: List[List[int]] = []
    for u, v in mst.edges():
        key = (u, v) if (u, v) in path_matrix else (v, u)
        if key not in path_matrix:
            continue
        seq = path_matrix[key]
        if u != key[0]:
            seq = seq[::-1]
        all_node_sequences.append(seq)

    if not all_node_sequences:
        return None, 0.0

    all_coords: List[Tuple[float, float]] = []
    total_length_m = 0.0
    for seq in all_node_sequences:
        coords = [(G_proj.nodes[n]["x"], G_proj.nodes[n]["y"]) for n in seq]
        if all_coords:
            all_coords.extend(coords[1:])
        else:
            all_coords.extend(coords)
        for a, b in zip(seq[:-1], seq[1:]):
            edges = G_proj[a][b]
            total_length_m += min(data.get("length", 0.0) for data in edges.values())

    if len(all_coords) < 2:
        return None, 0.0

    return LineString(all_coords), total_length_m / 1000.0


# --- Path-shaped corridor generation (replaces the MST-tree flatten) ------------
# build_corridor_path above flattens a branching MST into ONE LineString by
# concatenating tree edges in arbitrary order, which inserts straight phantom jumps
# between non-adjacent branches (observed: an 11.5km line across a river with no road)
# and self-intersecting loops. The two shapers below produce a single OPEN PATH whose
# consecutive road-segments always share an endpoint, so no phantom jump is possible.

def _terminal_sp_matrices(G_proj, terminal_nodes):
    """Pairwise shortest road paths between unique terminals.

    Returns (unique_terminals, dist_matrix, path_matrix) where dist/path are keyed by
    the (u, v) pair as first encountered (look up via _seq_between / _dist).
    """
    uniq = list(dict.fromkeys(terminal_nodes))
    dist, path = {}, {}
    for i, u in enumerate(uniq):
        for v in uniq[i + 1:]:
            try:
                path[(u, v)] = nx.shortest_path(G_proj, u, v, weight="length")
                dist[(u, v)] = nx.shortest_path_length(G_proj, u, v, weight="length")
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass
    return uniq, dist, path


def _dist(dist, a, b):
    if a == b:
        return 0.0
    return dist.get((a, b), dist.get((b, a), float("inf")))


def _seq_between(path, a, b):
    if (a, b) in path:
        return path[(a, b)]
    if (b, a) in path:
        return path[(b, a)][::-1]
    return None


def _stitch(G_proj, order, path, dist):
    """Concatenate the road paths between consecutive terminals in `order`.

    Consecutive segments share the joining terminal, so coords are appended with the
    shared node dropped -- a continuous single polyline with no straight jumps. Length
    sums the precomputed shortest-path distances between consecutive terminals (not
    per-edge adjacency: a reversed segment has no directed edge on a one-way graph).
    """
    full_nodes = []
    length_m = 0.0
    for a, b in zip(order[:-1], order[1:]):
        seq = _seq_between(path, a, b)
        if seq is None:
            return None, 0.0
        full_nodes.extend(seq if not full_nodes else seq[1:])
        length_m += _dist(dist, a, b)
    if len(full_nodes) < 2:
        return None, 0.0
    coords = [(G_proj.nodes[n]["x"], G_proj.nodes[n]["y"]) for n in full_nodes]
    return LineString(coords), length_m / 1000.0


def _open_tsp_order(uniq, dist):
    """Order terminals as an open path: nearest-neighbour seed + 2-opt on road dist."""
    if len(uniq) <= 2:
        return list(uniq)

    def tour_len(order):
        return sum(_dist(dist, a, b) for a, b in zip(order[:-1], order[1:]))

    best, best_len = None, float("inf")
    for start in uniq:                       # NN from every start, keep the best seed
        unvis = set(uniq); unvis.discard(start); order = [start]; cur = start
        while unvis:
            nxt = min(unvis, key=lambda n: _dist(dist, cur, n))
            order.append(nxt); unvis.discard(nxt); cur = nxt
        L = tour_len(order)
        if L < best_len:
            best, best_len = order, L
    improved = True
    while improved:                          # 2-opt on the open path
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                cand = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                cl = tour_len(cand)
                if cl < best_len - 1e-6:
                    best, best_len, improved = cand, cl, True
    return best


def corridor_path_tsp(G_proj, terminal_nodes):
    """Shaper A: open path visiting ALL anchors (nearest-neighbour + 2-opt).

    Returns (LineString_EPSG6372, route_km) -- one ridable end-to-end alignment, every
    anchor on the line, no phantom jumps. Can zigzag if anchors are scattered.
    """
    uniq, dist, path = _terminal_sp_matrices(G_proj, terminal_nodes)
    if len(uniq) < 2 or not dist:
        return None, 0.0
    return _stitch(G_proj, _open_tsp_order(uniq, dist), path, dist)


def anchor_span_km(G_proj, terminal_nodes):
    """Straight-line (Euclidean) minimum spanning length of the terminals, in km.

    The theoretical floor to connect a corridor's demand anchors. Used as the
    denominator for ANCHOR-DIRECTNESS (route_km / anchor_span_km) -- "does the route
    waste distance connecting its demand?" -- which is the right feasibility gate for a
    demand-coverage corridor that legitimately curves, unlike endpoint detour (which
    assumes a straight trunk). Computed over the terminal set the corridor is built to
    connect (0.0 for <2 reachable terminals).
    """
    import numpy as np
    from scipy.sparse.csgraph import minimum_spanning_tree
    from scipy.spatial.distance import pdist, squareform

    uniq = list(dict.fromkeys(terminal_nodes))
    coords = np.array(
        [(G_proj.nodes[n]["x"], G_proj.nodes[n]["y"]) for n in uniq if n in G_proj.nodes],
        dtype=float,
    )
    if len(coords) < 2:
        return 0.0
    return float(minimum_spanning_tree(squareform(pdist(coords))).sum()) / 1000.0


def corridor_trunk_diameter(G_proj, terminal_nodes):
    """Shaper B: the MST's longest leaf-to-leaf path (tree diameter) as a single trunk.

    Returns (LineString_EPSG6372, route_km). Clean spine; drops off-trunk anchors.
    """
    uniq, dist, path = _terminal_sp_matrices(G_proj, terminal_nodes)
    if len(uniq) < 2 or not dist:
        return None, 0.0
    H = nx.Graph()
    for (u, v), d in dist.items():
        H.add_edge(u, v, weight=d)
    if H.number_of_edges() == 0:
        return None, 0.0
    mst = nx.minimum_spanning_tree(H, weight="weight")

    def farthest(src):
        lengths = nx.shortest_path_length(mst, src, weight="weight")
        end = max(lengths, key=lengths.get)
        return end, lengths[end]

    a, _ = farthest(next(iter(mst.nodes)))
    b, _ = farthest(a)                        # double sweep -> diameter endpoints
    trunk = nx.shortest_path(mst, a, b, weight="weight")   # terminal-node sequence
    return _stitch(G_proj, trunk, path, dist)
