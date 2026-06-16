"""
W9.4 -- OSM Drive Network Download for ZM Monterrey
=====================================================
Downloads the OpenStreetMap drivable road network for the 12 municipalities
of Zona Metropolitana de Monterrey and caches it to data/osm_mty_drive.graphml.

If the file already exists, the download is skipped.

Usage:
    python src/w9_osm_download.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.w9_city_config import (
    CITY_NAME, OSM_NETWORK_CACHE,
    BBOX_LON_MIN, BBOX_LON_MAX, BBOX_LAT_MIN, BBOX_LAT_MAX,
)


def download_osm_graph(cache_path: Path) -> None:
    """Download OSM drive graph for ZM Monterrey via bounding box."""
    try:
        import osmnx as ox
    except ImportError:
        print("  [ERR] osmnx is not installed. Run: pip install osmnx")
        sys.exit(1)

    print(f"[Step 1] Downloading OSM drive network for {CITY_NAME}...")
    print(f"  Bounding box: lon [{BBOX_LON_MIN}, {BBOX_LON_MAX}], "
          f"lat [{BBOX_LAT_MIN}, {BBOX_LAT_MAX}]")

    try:
        graph = ox.graph_from_bbox(
            north=BBOX_LAT_MAX,
            south=BBOX_LAT_MIN,
            east=BBOX_LON_MAX,
            west=BBOX_LON_MIN,
            network_type="drive",
            retain_all=False,
            simplify=True,
        )
    except Exception as exc:
        print(f"  [ERR] Bounding-box download failed: {exc}")
        print("  Retrying with place-name queries per municipality...")
        graph = _download_by_place_names()

    n_nodes = len(graph.nodes)
    n_edges = len(graph.edges)
    print(f"  [OK] Graph: {n_nodes:,} nodes, {n_edges:,} edges")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, str(cache_path))
    print(f"  [OK] Saved -> {cache_path}")


def _download_by_place_names():
    """Fallback: compose graph from individual municipality place-name queries."""
    import osmnx as ox

    place_names = [
        "Apodaca, Nuevo Leon, Mexico",
        "Cadereyta Jimenez, Nuevo Leon, Mexico",
        "Garcia, Nuevo Leon, Mexico",
        "San Pedro Garza Garcia, Nuevo Leon, Mexico",
        "General Escobedo, Nuevo Leon, Mexico",
        "Guadalupe, Nuevo Leon, Mexico",
        "Juarez, Nuevo Leon, Mexico",
        "Monterrey, Nuevo Leon, Mexico",
        "Salinas Victoria, Nuevo Leon, Mexico",
        "San Nicolas de los Garza, Nuevo Leon, Mexico",
        "Santa Catarina, Nuevo Leon, Mexico",
        "Santiago, Nuevo Leon, Mexico",
    ]

    graphs = []
    for place in place_names:
        try:
            g = ox.graph_from_place(place, network_type="drive", simplify=True)
            print(f"  [OK] Downloaded: {place}")
            graphs.append(g)
        except Exception as exc:
            print(f"  [WARN] Could not download {place}: {exc}")

    if not graphs:
        raise RuntimeError("All place-name downloads failed. Check network connectivity.")

    import networkx as nx
    combined = nx.compose_all(graphs)
    return combined


def main():
    project_root = Path(__file__).parent.parent
    cache_path = project_root / OSM_NETWORK_CACHE

    print("\n" + "=" * 70)
    print(f"W9.4 -- OSM DRIVE NETWORK DOWNLOAD ({CITY_NAME.upper()})")
    print("=" * 70)

    if cache_path.exists():
        size_mb = cache_path.stat().st_size / (1024 * 1024)
        print(f"[Step 1] Cache already exists: {cache_path} ({size_mb:.1f} MB)")
        print("  [OK] Skipping download. Delete the file to force a re-download.")

        # Load and print stats
        try:
            import osmnx as ox
            graph = ox.load_graphml(str(cache_path))
            print(f"  [OK] Graph: {len(graph.nodes):,} nodes, {len(graph.edges):,} edges")
        except Exception as exc:
            print(f"  [WARN] Could not load cached graph for stats: {exc}")
        return

    download_osm_graph(cache_path)

    print("\n" + "=" * 70)
    print("W9.4 OSM DOWNLOAD COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
