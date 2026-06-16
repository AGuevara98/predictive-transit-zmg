"""City-specific configuration for Monterrey, Nuevo Leon (W9 transferability study).

This module defines all constants for ZM Monterrey. Import this instead of
config.py when running the pipeline for Monterrey.

DO NOT modify config.py. This file is intentionally self-contained.
"""

# =============================================================================
# City Identity
# =============================================================================
CITY_NAME = "Monterrey"
CITY_KEY  = "mty"          # Short key used in file/schema names

# =============================================================================
# INEGI Geographic Codes
# =============================================================================
CVE_ENT = "19"             # Nuevo Leon state code

# ZM Monterrey municipalities per CONAPO 2020 delimitation
# Format: zero-padded 3-digit CVE_MUN strings
ZM_MUNICIPALITIES = [
    "006",  # Apodaca
    "010",  # Cadereyta Jimenez
    "018",  # Garcia
    "019",  # San Pedro Garza Garcia
    "021",  # General Escobedo
    "026",  # Guadalupe
    "031",  # Juarez
    "039",  # Monterrey
    "042",  # Salinas Victoria
    "046",  # San Nicolas de los Garza
    "048",  # Santa Catarina
    "049",  # Santiago
]

# =============================================================================
# Bounding Box (WGS84 lon/lat)
# =============================================================================
BBOX_LON_MIN = -100.65
BBOX_LON_MAX = -99.85
BBOX_LAT_MIN = 25.40
BBOX_LAT_MAX = 26.00

# Structured bbox dict (mirrors ZMG_BBOX format in config.py)
MTY_BBOX = {
    "xmin": BBOX_LON_MIN,
    "ymin": BBOX_LAT_MIN,
    "xmax": BBOX_LON_MAX,
    "ymax": BBOX_LAT_MAX,
}

# =============================================================================
# Spatial Configuration
# =============================================================================
# EPSG:6372 is valid for all Mexico -- same as ZMG
CRS_CANONICAL = "EPSG:6372"

# AGEB filter: only urbanized AGEBs in NL state; exclude alpha-suffix manzana rows
AGEB_FILTER_CVE_ENT = "19"

# =============================================================================
# Database Schema
# =============================================================================
# All Monterrey tables go in features_mty schema to avoid collision with ZMG
DB_SCHEMA_PREFIX = "mty"

# =============================================================================
# OSM Road Network Cache
# =============================================================================
OSM_NETWORK_CACHE = "data/osm_mty_drive.graphml"

# =============================================================================
# Trip Generation Parameters (same formula as ZMG, Tier-1 only)
# Reference: INEGI MOTIV / ENIGH travel surveys
# =============================================================================
TRIPS_PER_PERSON_DAY = 2.5   # Average motorized trips per person per day
YOUTH_MULTIPLIER     = 0.10  # Youth share adjustment factor

# Attraction weights (same as w1_trip_generation.py ZMG values)
EMPLOY_WEIGHT  = 1.8
POI_WEIGHT     = 0.5
RETAIL_WEIGHT  = 0.8

# =============================================================================
# Gravity Model Parameters
# =============================================================================
# Use ZMG prior beta=2.0; calibrate against EOD if available (W2 equivalent)
GRAVITY_BETA       = 2.0
GRAVITY_MAX_ITER   = 300
GRAVITY_TOL        = 1e-5
GRAVITY_FLOW_THRESHOLD = 0.5   # Minimum flow to store in OD matrix

# =============================================================================
# CPV2020 Column Names
# These are confirmed from src/w1_trip_generation.py and src/w1_demand_surface.py
# The CPV2020 schema is identical across all Mexican states.
# =============================================================================
# Census ID columns
COL_ENTIDAD = "ENTIDAD"
COL_MUN     = "MUN"
COL_LOC     = "LOC"
COL_AGEB    = "AGEB"
COL_MZA     = "MZA"   # Filter: MZA == "000" selects AGEB-level rows

# Population columns
POP_COL        = "POBTOT"       # Total population
YOUTH_COL_LOW  = "P_15A17"      # Population 15-17 years
YOUTH_COL_HIGH = "P_18A24"      # Population 18-24 years
# Note: w1_trip_generation.py checks for P_15A29 first, then falls back to
# P_15A17 + P_18A24. Use the same fallback logic for Monterrey.
YOUTH_COL_COMBINED = "P_15A29"  # Combined 15-29 if available

# Housing and vehicle columns (for demand surface weighting)
VEHICLES_COL       = "VPH_AUTOM"    # Dwellings with automobile
OCCUPIED_HOUSING_COL = "VIVPAR_HAB" # Occupied private dwellings

# =============================================================================
# CPV2020 Data Path for Nuevo Leon
# =============================================================================
# Download from:
# https://www.inegi.org.mx/contenidos/programas/ccpv/2020/microdatos/ageb_manzana/
#   ageb_mza_urbana_19_cpv2020_csv.zip
#
# Expected directory structure after extraction:
#   data/ageb_mza_urbana_19_cpv2020/
#     conjunto_de_datos/
#       ageb_mza_urbana_19_cpv2020.csv
#     diccionario_de_datos/
#       ...
CENSUS_ZIP_URL = (
    "https://www.inegi.org.mx/contenidos/programas/ccpv/2020/microdatos/"
    "ageb_manzana/ageb_mza_urbana_19_cpv2020_csv.zip"
)
CENSUS_DIR_NAME = "ageb_mza_urbana_19_cpv2020_csv/ageb_mza_urbana_19_cpv2020"
CENSUS_CSV_NAME = "conjunto_de_datos_ageb_urbana_19_cpv2020.csv"

# =============================================================================
# Transit Operator
# =============================================================================
TRANSIT_OPERATOR = "Metrorrey + Transmetro BRT"
# GTFS sources (may require manual download or API key):
# - https://transitfeeds.com/l/491-monterrey-mexico (historical)
# - transmetro.monterrey.gob.mx (official, check availability)
GTFS_SOURCE_NOTE = (
    "GTFS feed availability: check transmetro.monterrey.gob.mx "
    "or the Mexican open data portal datos.gob.mx"
)

# =============================================================================
# Accessibility Parameters (same thresholds as ZMG W3)
# =============================================================================
ACCESSIBILITY_BUFFER_STOP   = 400   # metres: AGEB-to-stop walk catchment
ACCESSIBILITY_BUFFER_LONG   = 800   # metres: secondary catchment
TRAVEL_TIME_BUDGET_MIN      = 45    # minutes: cumulative-opportunities budget
WALK_SPEED_M_PER_MIN        = 80    # metres/minute walking speed

# =============================================================================
# Coverage-Gap Index Parameters (same as ZMG W3)
# =============================================================================
# gap_category thresholds (demand_quintile >= HIGH_DEMAND_Q and access_quintile <= LOW_ACCESS_Q)
HIGH_GAP_DEMAND_QUINTILE = 4
HIGH_GAP_ACCESS_QUINTILE = 2

# =============================================================================
# NPP-V Indicator Dimensions (same 14 features as ZMG W4; Vitality dropped)
# =============================================================================
NODE_FEATURES   = ["n_intersections_n", "n_intersection_density_n", "n_street_density_n"]
PLACE_FEATURES  = [
    "p_poi_density_n", "p_employment_proxy_n", "p_retail_density_n",
    "p_service_density_n", "p_land_use_mix_n",
]
PEOPLE_FEATURES = [
    "pe_population_n", "pe_pop_density_n", "pe_marginacion_n",
    "pe_rezago_n", "pe_dep_ratio_n", "pe_youth_share_n",
]
ALL_NPP_FEATURES = NODE_FEATURES + PLACE_FEATURES + PEOPLE_FEATURES  # 14 total

# Equity term weight in final_score (same as ZMG W4 default)
EQUITY_ALPHA = 0.20  # final_score = (1 - EQUITY_ALPHA) * npp_score + EQUITY_ALPHA * equity_score
