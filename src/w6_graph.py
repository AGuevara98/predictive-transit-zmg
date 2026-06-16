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
