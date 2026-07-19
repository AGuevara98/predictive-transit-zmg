"""City-specific configuration for Aguascalientes (W9 transferability).

ZM Aguascalientes, CONAPO 2020 delimitation: 3 municipios, ~1.1M inhabitants --
a COMPACT metro (smaller/simpler than ZMG's 10 munis or MTY's 12). Chosen as a
Monterrey replacement because its official statewide GTFS downloads cleanly over
HTTPS (frictionless); see docs/w9_gtfs_scouting_findings.md.

Copy of the w9_city_config.py (Monterrey) template. DO NOT modify config.py.
"""

# =============================================================================
# City Identity
# =============================================================================
CITY_NAME = "Aguascalientes"
CITY_KEY  = "ags"

# =============================================================================
# INEGI Geographic Codes
# =============================================================================
CVE_ENT = "01"             # Aguascalientes state code

# ZM Aguascalientes municipios per CONAPO 2020 delimitation (3 munis).
# make_city_census_extract.py asserts exactly 3 distinct munis matched.
ZM_MUNICIPALITIES = [
    "001",  # Aguascalientes
    "005",  # Jesus Maria
    "011",  # San Francisco de los Romo
]

# =============================================================================
# Bounding Box (WGS84 lon/lat) -- cover of the Aguascalientes conurbation.
# =============================================================================
BBOX_LON_MIN = -102.45
BBOX_LON_MAX = -102.05
BBOX_LAT_MIN = 21.75
BBOX_LAT_MAX = 22.15

AGS_BBOX = {
    "xmin": BBOX_LON_MIN, "ymin": BBOX_LAT_MIN,
    "xmax": BBOX_LON_MAX, "ymax": BBOX_LAT_MAX,
}

# =============================================================================
# Spatial / Schema
# =============================================================================
CRS_CANONICAL = "EPSG:6372"
AGEB_FILTER_CVE_ENT = "01"
DB_SCHEMA_PREFIX = "ags"
OSM_NETWORK_CACHE = "data/osm_ags_drive.graphml"

# =============================================================================
# Trip Generation (identical formula to ZMG/MTY, Tier-1 only)
# =============================================================================
TRIPS_PER_PERSON_DAY = 2.5
YOUTH_MULTIPLIER     = 0.10
EMPLOY_WEIGHT  = 1.8
POI_WEIGHT     = 0.5
RETAIL_WEIGHT  = 0.8

# =============================================================================
# Gravity Model -- ZMG-calibrated prior beta=1.2005 (see w9_city_config_tol.py note).
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
# CPV2020 Data Path for Aguascalientes (state 01).
# Get the ZIP from the interactive portal (direct URLs 404 now):
#   https://www.inegi.org.mx/programas/ccpv/2020/#Microdatos
#   Microdatos > AGEB y manzana urbana > Aguascalientes (state 01) > CSV
# then slim with scripts/data_prep/make_city_census_extract.py --city ags.
# =============================================================================
CENSUS_ZIP_URL = "https://www.inegi.org.mx/programas/ccpv/2020/#Microdatos"
CENSUS_DIR_NAME = "ageb_mza_urbana_01_cpv2020_csv/ageb_mza_urbana_01_cpv2020"
CENSUS_CSV_NAME = "conjunto_de_datos_ageb_urbana_01_cpv2020.csv"

# =============================================================================
# Transit Operator / GTFS (VERIFIED available -- see w9_gtfs_scouting_findings.md)
# =============================================================================
TRANSIT_OPERATOR = "Gobierno del Estado de Aguascalientes"
GTFS_ZIP_URL = "https://www.aguascalientes.gob.mx/portalgea/file/otros/gdeda-aguascalientes-mx.zip"
GTFS_DIR = "data/gtfs_ags"
GTFS_SOURCE_NOTE = (
    "Official statewide GTFS, Mobility Database src #3111, clean HTTPS. Validated "
    "2026-07-17: 1,507 stops, 8,388 stop_times, 184 trips, 48 routes, shapes + frequencies."
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
