"""
W2.1 — EOD 2022 Data Ingestion
================================
Reads zip files from data/encuesta_origen_destino/ and loads:
  - Zone polygons  -> raw.eod_zones
  - Desire lines   -> raw.eod_desire_lines

The EOD 2022 ZMGDL dataset from IIEG is inspected at runtime to determine
file formats (shapefiles, GeoJSON, CSV, Excel). Each zip is introspected
before attempting to read so format assumptions are validated, not assumed.

Spatial outputs are projected to EPSG:6372 before DB write.
"""
import sys
import io
import zipfile
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import MultiPolygon
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI, CRS_CANONICAL

ENGINE = create_engine(PG_URI)

DATA_DIR = Path(__file__).parent.parent / "data" / "encuesta_origen_destino"

# Zip file names (exact, as discovered in the data directory)
ZIP_ZONES      = "Zonificación de la Encuesta Origen-Destino.zip"
ZIP_PROD       = "Viajes totales producidos por zona.zip"
ZIP_ATTR       = "Viajes totales atraídos por zona.zip"
ZIP_DESIRE_LO  = "Líneas de deseo dentro del rango de 5,000 a 10,000 viajes.zip"
ZIP_DESIRE_HI  = "Líneas de deseo dentro del rango de 10,000 a 47,555 viajes.zip"


# ---------------------------------------------------------------------------
# Zip introspection helpers
# ---------------------------------------------------------------------------

def list_zip(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path) as zf:
        return zf.namelist()


def _extensions(names: list[str]) -> set[str]:
    return {Path(n).suffix.lower() for n in names if "." in n}


def _has(names: list[str], ext: str) -> bool:
    return any(n.lower().endswith(ext) for n in names)


def read_bytes_from_zip(zip_path: Path, member: str) -> bytes:
    with zipfile.ZipFile(zip_path) as zf:
        return zf.read(member)


# ---------------------------------------------------------------------------
# Format-agnostic readers
# ---------------------------------------------------------------------------

def read_geodataframe_from_zip(zip_path: Path) -> Optional[gpd.GeoDataFrame]:
    """
    Try to read a spatial layer from a zip. Supports:
      - Shapefile (.shp)
      - GeoJSON (.geojson / .json)
      - KML (.kml)

    Returns None if no recognised spatial format found.
    """
    if not zip_path.exists():
        print(f"  [WARN] Zip not found: {zip_path.name} -- skipping")
        return None

    names = list_zip(zip_path)
    print(f"  [INFO] {zip_path.name}: {names}")

    # Shapefile -- use /vsizip/ path (works with pyogrio)
    if _has(names, ".shp"):
        try:
            gdf = gpd.read_file(f"/vsizip/{zip_path}")
            print(f"    [OK] Shapefile read: {len(gdf)} features, CRS={gdf.crs}")
            return gdf
        except Exception as e:
            print(f"    [WARN] Shapefile read failed ({e}); trying member-by-member")
            # Fallback: extract .shp member and try fiona with in-memory
            shp_members = [n for n in names if n.lower().endswith(".shp")]
            if not shp_members:
                print("    [ERR] No .shp member to fall back to")
                return None
            try:
                import fiona
                with zipfile.ZipFile(zip_path) as zf:
                    # Extract all shapefile components to a tmp dir
                    import tempfile, os
                    with tempfile.TemporaryDirectory() as tmp:
                        for n in names:
                            if Path(n).suffix.lower() in {".shp", ".dbf", ".shx", ".prj", ".cpg"}:
                                dest = Path(tmp) / Path(n).name
                                dest.write_bytes(zf.read(n))
                        shp_path = Path(tmp) / Path(shp_members[0]).name
                        gdf = gpd.read_file(str(shp_path))
                        print(f"    [OK] Shapefile (extracted) read: {len(gdf)} features")
                        return gdf
            except Exception as e2:
                print(f"    [ERR] Shapefile fallback failed: {e2}")
                return None

    # GeoJSON
    for name in names:
        if Path(name).suffix.lower() in {".geojson", ".json"}:
            try:
                raw = read_bytes_from_zip(zip_path, name)
                gdf = gpd.read_file(io.BytesIO(raw))
                print(f"    [OK] GeoJSON read: {len(gdf)} features, CRS={gdf.crs}")
                return gdf
            except Exception as e:
                print(f"    [WARN] GeoJSON read failed for {name}: {e}")

    # KML
    for name in names:
        if name.lower().endswith(".kml"):
            try:
                raw = read_bytes_from_zip(zip_path, name)
                gdf = gpd.read_file(io.BytesIO(raw), driver="KML")
                print(f"    [OK] KML read: {len(gdf)} features, CRS={gdf.crs}")
                return gdf
            except Exception as e:
                print(f"    [WARN] KML read failed for {name}: {e}")

    print(f"  [WARN] No recognised spatial format in {zip_path.name} -- extensions: {_extensions(names)}")
    return None


def read_tabular_from_zip(zip_path: Path) -> Optional[pd.DataFrame]:
    """
    Try to read a tabular file from a zip. Supports CSV and Excel (.xlsx/.xls).
    Returns the first successful read or None.
    """
    if not zip_path.exists():
        print(f"  [WARN] Zip not found: {zip_path.name} -- skipping")
        return None

    names = list_zip(zip_path)
    print(f"  [INFO] {zip_path.name}: {names}")

    # Excel first (more structured, less encoding grief)
    for name in names:
        if Path(name).suffix.lower() in {".xlsx", ".xls"}:
            try:
                raw = read_bytes_from_zip(zip_path, name)
                df = pd.read_excel(io.BytesIO(raw))
                print(f"    [OK] Excel read: {len(df)} rows, cols={list(df.columns)}")
                return df
            except Exception as e:
                print(f"    [WARN] Excel read failed for {name}: {e}")

    # CSV fallbacks -- try UTF-8 then latin-1
    for name in names:
        if name.lower().endswith(".csv"):
            for enc in ["utf-8-sig", "utf-8", "latin-1"]:
                try:
                    raw = read_bytes_from_zip(zip_path, name)
                    df = pd.read_csv(io.BytesIO(raw), encoding=enc)
                    print(f"    [OK] CSV ({enc}) read: {len(df)} rows, cols={list(df.columns)}")
                    return df
                except Exception:
                    continue
            print(f"    [WARN] CSV {name} could not be decoded")

    print(f"  [WARN] No tabular file found in {zip_path.name} -- extensions: {_extensions(names)}")
    return None


# ---------------------------------------------------------------------------
# Column normalisation helpers
# ---------------------------------------------------------------------------

def _find_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """Return the first column name (case-insensitive) matching any candidate."""
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def _to_numeric_col(df: pd.DataFrame, col: str) -> pd.Series:
    """Coerce a column to numeric, stripping thousands separators and commas."""
    s = df[col].astype(str).str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(s, errors="coerce").fillna(0)


# ---------------------------------------------------------------------------
# Zone polygon ingestion (W2.1a)
# ---------------------------------------------------------------------------

def ingest_zones(productions_df: Optional[pd.DataFrame],
                 attractions_df: Optional[pd.DataFrame]) -> gpd.GeoDataFrame:
    """
    Load EOD survey zones. Geometry from ZIP_ZONES shapefile; productions/
    attractions joined from tabular zips.
    """
    print("\n[Step 1] Loading EOD zone polygons...")
    gdf = read_geodataframe_from_zip(DATA_DIR / ZIP_ZONES)
    if gdf is None or gdf.empty:
        raise RuntimeError(
            f"Could not read zone polygons from {ZIP_ZONES}. "
            "Ensure the file is in data/encuesta_origen_destino/ and is a valid shapefile."
        )

    # Reproject to canonical CRS
    if gdf.crs is None:
        print("  [WARN] Zone CRS is unknown; assuming EPSG:4326 (WGS84)")
        gdf = gdf.set_crs("EPSG:4326")
    gdf = gdf.to_crs(CRS_CANONICAL)

    # Identify zone_id and zone_name columns
    id_col   = _find_col(gdf, ["numero_de_", "zona", "zone_id", "id_zona", "id", "CVE_ZONA", "FID", "OBJECTID"])
    name_col = _find_col(gdf, ["nombre_de_", "nombre", "nom_zona", "name", "zone_name", "NOM_ZONA"])

    if id_col is None:
        print("  [WARN] Could not identify zone_id column; using row index as zone_id")
        gdf["zone_id"] = gdf.index.astype(str)
    else:
        gdf["zone_id"] = gdf[id_col].astype(str).str.strip()

    gdf["zone_name"] = gdf[name_col].astype(str).str.strip() if name_col else ""

    # Force geometry to MultiPolygon for consistent storage type
    def to_multi(geom):
        from shapely.geometry import Polygon
        if geom is None:
            return None
        if isinstance(geom, Polygon):
            return MultiPolygon([geom])
        return geom

    gdf["geom"] = gdf.geometry.apply(to_multi)

    print(f"  [OK] {len(gdf)} zones loaded, CRS={gdf.crs}")

    # Join productions
    gdf["productions"] = np.nan
    gdf["attractions"] = np.nan

    if productions_df is not None:
        prod_id  = _find_col(productions_df, ["numero_de_", "zona", "zone_id", "id_zona", "id", "CVE_ZONA"])
        prod_val = _find_col(productions_df, ["viajes_ori", "viajes", "trips", "producidos", "total", "viajes_prod"])
        if prod_id and prod_val:
            productions_df = productions_df.copy()
            productions_df["zone_id"] = productions_df[prod_id].astype(str).str.strip()
            productions_df["_prod"]   = _to_numeric_col(productions_df, prod_val)
            gdf = gdf.merge(
                productions_df[["zone_id", "_prod"]],
                on="zone_id", how="left"
            )
            gdf["productions"] = gdf["_prod"].fillna(0)
            gdf = gdf.drop(columns=["_prod"])
            print(f"  [OK] Productions joined ({gdf['productions'].notna().sum()} zones matched)")
        else:
            print(f"  [WARN] Could not identify productions columns in {ZIP_PROD} "
                  f"(found: {list(productions_df.columns)})")
    else:
        print(f"  [WARN] Productions tabular file not available; productions column will be NULL")

    if attractions_df is not None:
        attr_id  = _find_col(attractions_df, ["numero_de_", "zona", "zone_id", "id_zona", "id", "CVE_ZONA"])
        attr_val = _find_col(attractions_df, ["viajes_atr", "viajes", "trips", "atraidos", "total"])
        if attr_id and attr_val:
            attractions_df = attractions_df.copy()
            attractions_df["zone_id"] = attractions_df[attr_id].astype(str).str.strip()
            attractions_df["_attr"]   = _to_numeric_col(attractions_df, attr_val)
            gdf = gdf.merge(
                attractions_df[["zone_id", "_attr"]],
                on="zone_id", how="left"
            )
            gdf["attractions"] = gdf["_attr"].fillna(0)
            gdf = gdf.drop(columns=["_attr"])
            print(f"  [OK] Attractions joined ({gdf['attractions'].notna().sum()} zones matched)")
        else:
            print(f"  [WARN] Could not identify attractions columns in {ZIP_ATTR} "
                  f"(found: {list(attractions_df.columns)})")
    else:
        print(f"  [WARN] Attractions tabular file not available; attractions column will be NULL")

    return gdf[["zone_id", "zone_name", "productions", "attractions", "geom"]]


# ---------------------------------------------------------------------------
# Desire-line ingestion (W2.1b)
# ---------------------------------------------------------------------------

def _read_desire_lines_from_zip(zip_path: Path) -> Optional[pd.DataFrame]:
    """
    EOD desire lines are published as either:
      a) Shapefiles with FROM_ZONE, TO_ZONE, TRIPS attributes, or
      b) Excel/CSV tables with zone-pair columns.
    Try spatial first, fall back to tabular.
    """
    if not zip_path.exists():
        print(f"  [WARN] {zip_path.name} not found -- skipping")
        return None

    names = list_zip(zip_path)
    print(f"  [INFO] {zip_path.name}: {names}")

    # Try spatial (desire lines are published as line shapefiles)
    if _has(names, ".shp") or any(n.lower().endswith((".geojson", ".json", ".kml")) for n in names):
        # Identify the Line layer name explicitly to avoid multi-layer ambiguity
        line_layers = [Path(n).stem for n in names if n.lower().endswith("line.shp")]
        layer_name = line_layers[0] if line_layers else None
        try:
            vsi_path = f"/vsizip/{zip_path}"
            gdf = gpd.read_file(vsi_path, layer=layer_name) if layer_name else gpd.read_file(vsi_path)
            print(f"    [OK] Shapefile read: {len(gdf)} features, CRS={gdf.crs}")
        except Exception as e:
            print(f"    [WARN] Shapefile read failed: {e}")
            gdf = None
        if gdf is not None and not gdf.empty:
            # Identify origin, destination, flow columns (actual DBF names first, then fuzzy)
            orig_col = _find_col(gdf, ["zona_de_or", "origen", "origin", "zona_ori", "from_zone",
                                       "id_origen", "zona_o", "CVE_ORI", "O_ZONA"])
            dest_col = _find_col(gdf, ["zona_de_de", "destino", "dest", "zona_des", "to_zone",
                                       "id_destino", "zona_d", "CVE_DES", "D_ZONA"])
            flow_col = _find_col(gdf, ["total_de_v", "viajes", "trips", "flujo", "flow", "total",
                                       "TOTAL_VIAJ", "viajes_tot"])
            if orig_col and dest_col and flow_col:
                df = pd.DataFrame({
                    "origin_zone"  : gdf[orig_col].astype(str).str.strip(),
                    "dest_zone"    : gdf[dest_col].astype(str).str.strip(),
                    "observed_flow": _to_numeric_col(gdf, flow_col),
                })
                df = df[df["observed_flow"] > 0]
                print(f"    [OK] {len(df)} desire-line pairs from {zip_path.name}")
                return df
            else:
                print(f"    [WARN] Spatial desire-line layer missing expected columns "
                      f"(orig={orig_col}, dest={dest_col}, flow={flow_col}). "
                      f"Falling back to tabular read.")

    # Tabular fallback
    df_raw = read_tabular_from_zip(zip_path)
    if df_raw is None:
        return None

    orig_col = _find_col(df_raw, ["origen", "origin", "zona_ori", "from_zone", "zona_o", "O_ZONA"])
    dest_col = _find_col(df_raw, ["destino", "dest", "zona_des", "to_zone", "zona_d", "D_ZONA"])
    flow_col = _find_col(df_raw, ["viajes", "trips", "total", "flujo", "TOTAL_VIAJ", "viajes_tot"])

    if not (orig_col and dest_col and flow_col):
        print(f"  [WARN] Could not identify OD columns in {zip_path.name} "
              f"(cols: {list(df_raw.columns)}) -- skipping")
        return None

    df = pd.DataFrame({
        "origin_zone"  : df_raw[orig_col].astype(str).str.strip(),
        "dest_zone"    : df_raw[dest_col].astype(str).str.strip(),
        "observed_flow": _to_numeric_col(df_raw, flow_col),
    })
    df = df[df["observed_flow"] > 0]
    print(f"  [OK] {len(df)} desire-line pairs from {zip_path.name} (tabular)")
    return df


def ingest_desire_lines() -> pd.DataFrame:
    print("\n[Step 2] Loading EOD desire lines...")
    parts = []
    for zip_name in (ZIP_DESIRE_LO, ZIP_DESIRE_HI):
        part = _read_desire_lines_from_zip(DATA_DIR / zip_name)
        if part is not None and not part.empty:
            parts.append(part)

    if not parts:
        raise RuntimeError(
            "Could not read any desire-line data. "
            "Check that the desire-line zips are present and in a supported format."
        )

    dl = pd.concat(parts, ignore_index=True)

    # Deduplicate -- if both zips cover same pairs, keep the higher-flow one
    dl = (
        dl.sort_values("observed_flow", ascending=False)
          .drop_duplicates(subset=["origin_zone", "dest_zone"], keep="first")
    )
    # Drop self-flows (zones traveling to themselves are artifacts)
    dl = dl[dl["origin_zone"] != dl["dest_zone"]]

    print(f"  [OK] {len(dl)} unique OD pairs after dedup; "
          f"total observed flow = {dl['observed_flow'].sum():,.0f}")
    return dl.reset_index(drop=True)


# ---------------------------------------------------------------------------
# DB writers
# ---------------------------------------------------------------------------

def write_zones(gdf: gpd.GeoDataFrame):
    print("\n[Step 3] Writing zones to raw.eod_zones...")
    records = []
    for _, row in gdf.iterrows():
        geom_wkt = row["geom"].wkt if row["geom"] is not None else None
        records.append({
            "zone_id"    : row["zone_id"],
            "zone_name"  : str(row["zone_name"]) if row["zone_name"] else None,
            "productions": float(row["productions"]) if pd.notna(row["productions"]) else None,
            "attractions": float(row["attractions"]) if pd.notna(row["attractions"]) else None,
            "geom_wkt"   : geom_wkt,
        })

    with ENGINE.begin() as conn:
        conn.execute(text("DELETE FROM raw.eod_zones"))
        conn.execute(
            text("""
                INSERT INTO raw.eod_zones (zone_id, zone_name, productions, attractions, geom)
                VALUES (
                    :zone_id, :zone_name, :productions, :attractions,
                    CASE WHEN :geom_wkt IS NOT NULL
                         THEN ST_Multi(ST_GeomFromText(:geom_wkt, 6372))
                         ELSE NULL END
                )
            """),
            records,
        )
        conn.execute(text("ANALYZE raw.eod_zones"))

    print(f"  [OK] {len(records)} zones written to raw.eod_zones")


def write_desire_lines(dl: pd.DataFrame):
    print("\n[Step 4] Writing desire lines to raw.eod_desire_lines...")
    records = dl[["origin_zone", "dest_zone", "observed_flow"]].to_dict("records")

    with ENGINE.begin() as conn:
        conn.execute(text("DELETE FROM raw.eod_desire_lines"))
        conn.execute(
            text("""
                INSERT INTO raw.eod_desire_lines (origin_zone, dest_zone, observed_flow)
                VALUES (:origin_zone, :dest_zone, :observed_flow)
            """),
            records,
        )
        conn.execute(text("ANALYZE raw.eod_desire_lines"))

    print(f"  [OK] {len(records)} OD pairs written to raw.eod_desire_lines")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("\n" + "="*70)
    print("W2.1 -- EOD 2022 DATA INGESTION")
    print("="*70)

    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"EOD data directory not found: {DATA_DIR}\n"
            "Place EOD 2022 zip files in data/encuesta_origen_destino/"
        )

    # Productions and attractions are shapefiles (polygon attributes), not tabular files
    print("\n[Step 0] Pre-loading productions/attractions from shapefiles...")
    productions_df = read_geodataframe_from_zip(DATA_DIR / ZIP_PROD)
    attractions_df = read_geodataframe_from_zip(DATA_DIR / ZIP_ATTR)

    zones_gdf  = ingest_zones(productions_df, attractions_df)
    desire_df  = ingest_desire_lines()

    write_zones(zones_gdf)
    write_desire_lines(desire_df)

    print("\n" + "="*70)
    print("W2.1 EOD INGESTION COMPLETE")
    print("="*70)
    print(f"  raw.eod_zones        : {len(zones_gdf)} zones")
    print(f"  raw.eod_desire_lines : {len(desire_df)} OD pairs")
    n_matched_prod = zones_gdf["productions"].notna().sum()
    n_matched_attr = zones_gdf["attractions"].notna().sum()
    if n_matched_prod == 0:
        print("  [WARN] Productions column is entirely NULL -- calibration will use zone geometry only")
    if n_matched_attr == 0:
        print("  [WARN] Attractions column is entirely NULL -- calibration will use zone geometry only")


if __name__ == "__main__":
    main()
