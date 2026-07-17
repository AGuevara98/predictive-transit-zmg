"""City-specific configuration for Toluca, Estado de Mexico (W9 transferability).

ZM Toluca (Zona Metropolitana del Valle de Toluca), CONAPO 2020 delimitation:
16 municipios, ~2.3M inhabitants -- a LARGE metro comparable in scale to ZMG
(10 munis) and MTY (12 munis). Chosen as a Monterrey replacement because it has
a usable, official GTFS feed (unlike MTY); see docs/w9_gtfs_scouting_findings.md.

Copy of the w9_city_config.py (Monterrey) template with the identity, municipio
list, bbox, and data-source URLs swapped. DO NOT modify config.py.
"""

# =============================================================================
# City Identity
# =============================================================================
CITY_NAME = "Toluca"
CITY_KEY  = "tol"

# =============================================================================
# INEGI Geographic Codes
# =============================================================================
CVE_ENT = "15"             # Estado de Mexico state code

# ZM Toluca municipios per CONAPO 2020 delimitation (Decreto 159, 2016 -> 16 munis).
# Zero-padded 3-digit CVE_MUN. NOTE: Edomex has 125 municipios, so this filter MUST
# be exact -- make_city_census_extract.py asserts exactly 16 distinct munis matched.
ZM_MUNICIPALITIES = [
    "005",  # Almoloya de Juarez
    "018",  # Calimaya
    "022",  # Chapultepec
    "051",  # Lerma
    "054",  # Metepec
    "055",  # Mexicaltzingo
    "062",  # Ocoyoacac
    "067",  # Otzolotepec
    "072",  # Rayon
    "076",  # San Antonio la Isla
    "087",  # Temoaya
    "089",  # Tenango del Valle
    "090",  # San Mateo Atenco
    "106",  # Toluca
    "115",  # Xonacatlan
    "118",  # Zinacantepec
]

# =============================================================================
# Bounding Box (WGS84 lon/lat) -- generous cover of the Valle de Toluca.
# Only used for the random-centroid fallback / OSM bbox; the real AGEB centroids
# come from the shapefile, so precision here is low-stakes for Tier-1.
# =============================================================================
BBOX_LON_MIN = -99.95
BBOX_LON_MAX = -99.35
BBOX_LAT_MIN = 18.90
BBOX_LAT_MAX = 19.60

TOL_BBOX = {
    "xmin": BBOX_LON_MIN, "ymin": BBOX_LAT_MIN,
    "xmax": BBOX_LON_MAX, "ymax": BBOX_LAT_MAX,
}

# =============================================================================
# Spatial / Schema
# =============================================================================
CRS_CANONICAL = "EPSG:6372"
AGEB_FILTER_CVE_ENT = "15"
DB_SCHEMA_PREFIX = "tol"
OSM_NETWORK_CACHE = "data/osm_tol_drive.graphml"

# =============================================================================
# Trip Generation (identical formula to ZMG/MTY, Tier-1 only)
# =============================================================================
TRIPS_PER_PERSON_DAY = 2.5
YOUTH_MULTIPLIER     = 0.10
EMPLOY_WEIGHT  = 1.8
POI_WEIGHT     = 0.5
RETAIL_WEIGHT  = 0.8

# =============================================================================
# Gravity Model -- use the CURRENT ZMG-calibrated prior beta=1.2005 (adopted
# 2026-06-25; MTY's config predates it and still uses 2.0). No EOD for Toluca,
# so this is the transferred prior; the demand-surface transfer signal
# (vehicle_rate / transit_propensity) is beta-independent regardless.
# =============================================================================
GRAVITY_BETA       = 1.2005
GRAVITY_MAX_ITER   = 300
GRAVITY_TOL        = 1e-5
GRAVITY_FLOW_THRESHOLD = 0.5

# =============================================================================
# CPV2020 Column Names (identical schema across all Mexican states)
# =============================================================================
COL_ENTIDAD = "ENTIDAD"
COL_MUN     = "MUN"
COL_LOC     = "LOC"
COL_AGEB    = "AGEB"
COL_MZA     = "MZA"

POP_COL        = "POBTOT"
YOUTH_COL_LOW  = "P_15A17"
YOUTH_COL_HIGH = "P_18A24"
YOUTH_COL_COMBINED = "P_15A29"
VEHICLES_COL       = "VPH_AUTOM"
OCCUPIED_HOUSING_COL = "VIVPAR_HAB"

# =============================================================================
# CPV2020 Data Path for Estado de Mexico (state 15).
# INEGI reorganized the direct-download URLs (the old pattern now 404s); get the
# ZIP from the interactive portal: https://www.inegi.org.mx/programas/ccpv/2020/#Microdatos
#   Microdatos > AGEB y manzana urbana > Mexico (state 15) > CSV
# then slim it with scripts/data_prep/make_city_census_extract.py --city tol.
# =============================================================================
CENSUS_ZIP_URL = "https://www.inegi.org.mx/programas/ccpv/2020/#Microdatos"
CENSUS_DIR_NAME = "ageb_mza_urbana_15_cpv2020_csv/ageb_mza_urbana_15_cpv2020"
CENSUS_CSV_NAME = "conjunto_de_datos_ageb_urbana_15_cpv2020.csv"

# =============================================================================
# Transit Operator / GTFS (VERIFIED available -- see w9_gtfs_scouting_findings.md)
# =============================================================================
TRANSIT_OPERATOR = "Gobierno del Estado de Mexico -- Toluca y Area Metropolitana"
GTFS_ZIP_URL = "https://datos.movimex.gob.mx/gtfs/toluca.gtfs.zip"  # host cert expired -> curl -k
GTFS_DIR = "data/gtfs_tol"
GTFS_SOURCE_NOTE = (
    "Official GTFS, Mobility Database src #2865. The gov host serves an EXPIRED "
    "TLS certificate -- download with `curl -k`. Validated 2026-07-17: 60,295 stops, "
    "334,104 stop_times, 622 routes, shapes + frequencies + fares."
)

# =============================================================================
# Accessibility / Coverage-Gap / NPP (identical thresholds to ZMG W3/W4)
# =============================================================================
ACCESSIBILITY_BUFFER_STOP   = 400
ACCESSIBILITY_BUFFER_LONG   = 800
TRAVEL_TIME_BUDGET_MIN      = 45
WALK_SPEED_M_PER_MIN        = 80
HIGH_GAP_DEMAND_QUINTILE = 4
HIGH_GAP_ACCESS_QUINTILE = 2

NODE_FEATURES   = ["n_intersections_n", "n_intersection_density_n", "n_street_density_n"]
PLACE_FEATURES  = [
    "p_poi_density_n", "p_employment_proxy_n", "p_retail_density_n",
    "p_service_density_n", "p_land_use_mix_n",
]
PEOPLE_FEATURES = [
    "pe_population_n", "pe_pop_density_n", "pe_marginacion_n",
    "pe_rezago_n", "pe_dep_ratio_n", "pe_youth_share_n",
]
ALL_NPP_FEATURES = NODE_FEATURES + PLACE_FEATURES + PEOPLE_FEATURES
EQUITY_ALPHA = 0.20
