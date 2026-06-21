-- ==============================================================================
-- 1. SCHEMA INITIALIZATION
-- ==============================================================================
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS base;
CREATE SCHEMA IF NOT EXISTS features;

CREATE EXTENSION IF NOT EXISTS postgis_raster;

-- ==============================================================================
-- 2. RAW DATA PREPARATION (DENUE)
-- ==============================================================================
DROP TABLE IF EXISTS raw.denue;

CREATE TABLE raw.denue AS
SELECT
    denue_id::int AS denue_id,
    clee,
    nombre_unidad,
    razon_social,
    scian_codigo,
    scian_nombre,
    estrato_personal,
    cve_ent,
    cve_mun,
    cve_loc,
    ageb_id,
    manzana_id,
    latitud::double precision AS latitud,
    longitud::double precision AS longitud,
    fecha_alta
FROM raw.denue_staging;

ALTER TABLE raw.denue ADD COLUMN geom geometry(Point, 4326);

UPDATE raw.denue 
SET geom = ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)
WHERE longitud IS NOT NULL AND latitud IS NOT NULL;

CREATE INDEX IF NOT EXISTS denue_raw_geom_idx ON raw.denue USING GIST (geom);
ANALYZE raw.denue;

DROP TABLE IF EXISTS raw.denue_staging;

-- ==============================================================================
-- 3. BASE TABLES (Projected to EPSG:6372 & Normalized)
-- ==============================================================================

-- AGEB
DROP TABLE IF EXISTS base.ageb CASCADE;
CREATE TABLE base.ageb AS
SELECT
    *,
    ST_Transform(geom, 6372) AS geom_6372
FROM raw.ageb
WHERE cve_ent = '14'
  AND cve_ageb NOT LIKE '%A%'
  AND cve_mun IN ('039','044','051','070','097','098','101','120','002','124');

ALTER TABLE base.ageb DROP COLUMN geom;
ALTER TABLE base.ageb RENAME COLUMN geom_6372 TO geom;

ALTER TABLE base.ageb ADD PRIMARY KEY (cvegeo);
CREATE INDEX base_ageb_gix ON base.ageb USING GIST (geom);
ANALYZE base.ageb;

-- GTFS Stops
DROP TABLE IF EXISTS base.gtfs_stops CASCADE;
CREATE TABLE base.gtfs_stops AS
SELECT
    stop_id,
    stop_name,
    ST_Transform(geom, 6372)::geometry(Point, 6372) AS geom
FROM raw.gtfs_stops
WHERE geom IS NOT NULL;

CREATE INDEX base_gtfs_stops_gix ON base.gtfs_stops USING GIST (geom);
ANALYZE base.gtfs_stops;

-- Linea 4
DROP TABLE IF EXISTS base.linea4 CASCADE;
CREATE TABLE base.linea4 AS
SELECT
    r.*,
    (
        CASE
            WHEN ST_GeometryType(r.geom) IN ('ST_LineString','ST_MultiLineString') THEN
                ST_Multi(ST_LineMerge(ST_Transform(r.geom, 6372)))::geometry(MultiLineString, 6372)
            WHEN ST_GeometryType(r.geom) IN ('ST_Polygon','ST_MultiPolygon') THEN
                ST_Multi(ST_Boundary(ST_Transform(r.geom, 6372)))::geometry(MultiLineString, 6372)
            WHEN ST_GeometryType(r.geom) = 'ST_MultiPoint' THEN
                (
                    SELECT ST_Multi(ST_MakeLine((dp).geom ORDER BY (dp).path[1]))::geometry(MultiLineString, 6372)
                    FROM ST_DumpPoints(ST_Transform(r.geom, 6372)) dp
                )
            ELSE NULL
        END
    ) AS geom_6372
FROM raw.linea4 r;

ALTER TABLE base.linea4 DROP COLUMN geom;
ALTER TABLE base.linea4 RENAME COLUMN geom_6372 TO geom;
DELETE FROM base.linea4 WHERE geom IS NULL;

CREATE INDEX linea4_gix ON base.linea4 USING GIST (geom);
ANALYZE base.linea4;

-- Linea 4 Merged
DROP TABLE IF EXISTS base.linea4_merged CASCADE;
CREATE TABLE base.linea4_merged AS
SELECT
    'L4'::text AS route_id,
    'Linea 4'::text AS route_name,
    'geojson'::text AS source,
    'metro'::text AS mode,
    ST_Multi(ST_LineMerge(ST_UnaryUnion(ST_Collect(geom))))::geometry(MultiLineString, 6372) AS geom
FROM base.linea4;

CREATE INDEX linea4_merged_gix ON base.linea4_merged USING GIST (geom);
ANALYZE base.linea4_merged;

-- GTFS Shapes Lines
DROP TABLE IF EXISTS base.gtfs_shapes_lines CASCADE;
WITH pts AS (
    SELECT
        shape_id,
        shape_pt_sequence::int AS seq,
        ST_SetSRID(ST_MakePoint(shape_pt_lon::double precision, shape_pt_lat::double precision), 4326) AS geom_4326
    FROM raw.gtfs_shapes
    WHERE shape_pt_lon IS NOT NULL AND shape_pt_lat IS NOT NULL AND shape_pt_sequence IS NOT NULL
),
lines AS (
    SELECT
        shape_id,
        ST_MakeLine(geom_4326 ORDER BY seq) AS geom_4326
    FROM pts
    GROUP BY shape_id
)
SELECT
    shape_id,
    ST_Transform(geom_4326, 6372)::geometry(LineString, 6372) AS geom
INTO base.gtfs_shapes_lines
FROM lines;

CREATE INDEX gtfs_shapes_lines_gix ON base.gtfs_shapes_lines USING GIST (geom);
ANALYZE base.gtfs_shapes_lines;

-- GTFS Route Lines
DROP TABLE IF EXISTS base.gtfs_route_lines CASCADE;
CREATE TABLE base.gtfs_route_lines AS
SELECT DISTINCT
    r.route_id,
    COALESCE(NULLIF(r.route_short_name,''), r.route_long_name, r.route_id) AS route_name,
    t.shape_id,
    l.geom
FROM raw.gtfs_trips t
JOIN raw.gtfs_routes r ON r.route_id = t.route_id
JOIN base.gtfs_shapes_lines l ON l.shape_id = t.shape_id;

CREATE INDEX gtfs_route_lines_gix ON base.gtfs_route_lines USING GIST (geom);
ANALYZE base.gtfs_route_lines;

-- Normalized Routes
DROP TABLE IF EXISTS base.routes_gtfs_norm CASCADE;
CREATE TABLE base.routes_gtfs_norm AS
SELECT
    r.route_id,
    COALESCE(r.route_short_name, r.route_long_name) AS route_name,
    'metro_or_bus'::text AS mode,
    'gtfs'::text AS source,
    l.geom
FROM base.gtfs_route_lines l
JOIN raw.gtfs_routes r ON r.route_id = l.route_id;

CREATE INDEX routes_gtfs_norm_gix ON base.routes_gtfs_norm USING GIST (geom);
ANALYZE base.routes_gtfs_norm;

-- Unified Transit Routes
DROP TABLE IF EXISTS base.transit_routes CASCADE;
CREATE TABLE base.transit_routes AS
SELECT route_id, route_name, source, mode, geom::geometry(Geometry, 6372) AS geom
FROM base.routes_gtfs_norm
UNION ALL
SELECT route_id, route_name, source, mode, geom::geometry(Geometry, 6372) AS geom
FROM base.linea4_merged;

CREATE INDEX transit_routes_gix ON base.transit_routes USING GIST (geom);
ANALYZE base.transit_routes;

-- ==============================================================================
-- 4. FEATURES TABLES (Aggregations and Metrics)
-- ==============================================================================

-- Economic Activity
DROP TABLE IF EXISTS features.ageb_economic_activity CASCADE;
CREATE TABLE features.ageb_economic_activity AS
WITH filtered_denue AS (
    SELECT 
        scian_codigo::text AS scian_code,
        CASE 
            WHEN estrato_personal = '11 a 30 personas' THEN 20
            WHEN estrato_personal = '31 a 50 personas' THEN 40
            WHEN estrato_personal = '51 a 100 personas' THEN 75
            WHEN estrato_personal = '101 a 250 personas' THEN 175
            WHEN estrato_personal = '251 y más personas' THEN 500
            ELSE 0 
        END AS employment_proxy,
        ST_Transform(geom, 6372) AS geom
    FROM raw.denue
    WHERE estrato_personal NOT IN ('0 a 5 personas', '6 a 10 personas')
)
SELECT
    a.cvegeo AS ageb_id,
    COUNT(d.*) AS denue_units_total,
    SUM(COALESCE(d.employment_proxy, 0)) AS jobs_proxy_sum,
    COUNT(*) FILTER (WHERE d.scian_code LIKE '31%' OR d.scian_code LIKE '32%' OR d.scian_code LIKE '33%') AS denue_manufacturing,
    COUNT(*) FILTER (WHERE d.scian_code LIKE '46%') AS denue_retail,
    COUNT(*) FILTER (WHERE d.scian_code LIKE '61%') AS denue_education,
    COUNT(*) FILTER (WHERE d.scian_code LIKE '62%') AS denue_health,
    COUNT(*) FILTER (WHERE d.scian_code LIKE '931%') AS denue_government
FROM base.ageb a
LEFT JOIN filtered_denue d ON ST_Intersects(a.geom, d.geom)
GROUP BY a.cvegeo;

ALTER TABLE features.ageb_economic_activity ADD PRIMARY KEY (ageb_id);
ANALYZE features.ageb_economic_activity;

-- Employment
DROP TABLE IF EXISTS features.ageb_employment CASCADE;
CREATE TABLE features.ageb_employment AS
SELECT 
    a.cvegeo AS ageb_id,
    COUNT(d.denue_id) AS total_establishments,
    SUM(CASE 
        WHEN d.estrato_personal = '11 a 30 personas' THEN 20
        WHEN d.estrato_personal = '31 a 50 personas' THEN 40
        WHEN d.estrato_personal = '51 a 100 personas' THEN 75
        WHEN d.estrato_personal = '101 a 250 personas' THEN 175
        WHEN d.estrato_personal = '251 y más personas' THEN 500
        ELSE 0 END) AS employment_proxy
FROM base.ageb a
LEFT JOIN raw.denue d ON ST_Intersects(a.geom, ST_Transform(d.geom, 6372))
WHERE d.estrato_personal NOT IN ('0 a 5 personas', '6 a 10 personas')
GROUP BY a.cvegeo;

CREATE INDEX idx_ageb_emp_id ON features.ageb_employment (ageb_id);
ANALYZE features.ageb_employment;

-- Accessibility
DROP TABLE IF EXISTS features.ageb_accessibility CASCADE;
CREATE TABLE features.ageb_accessibility AS
SELECT
    a.cvegeo AS ageb_id,
    COUNT(s.*) FILTER (WHERE ST_DWithin(a.geom, s.geom, 400)) AS stops_400m,
    COUNT(s.*) FILTER (WHERE ST_DWithin(a.geom, s.geom, 800)) AS stops_800m,
    MIN(ST_Distance(a.geom, s.geom)) AS min_stop_dist_m
FROM base.ageb a
LEFT JOIN base.gtfs_stops s ON ST_DWithin(a.geom, s.geom, 2000)
GROUP BY a.cvegeo;

CREATE INDEX ageb_accessibility_ageb_id_idx ON features.ageb_accessibility (ageb_id);
ANALYZE features.ageb_accessibility;

-- Topography
-- raw.dem is loaded via `raster2pgsql -s 6365` (the DEM's true geographic
-- CRS per gdalinfo; raster2pgsql tags SRID, it never reprojects). Transform
-- the AGEB polygon (1,852 rows) into 6365 for the join/clip instead of
-- transforming the raster (940k+ tiles). The "&&" overlap test is required
-- alongside ST_Intersects -- raster2pgsql's GIST index is built on
-- ST_ConvexHull(rast), and the planner only uses it via the && operator;
-- ST_Intersects alone falls back to a full sequential scan of every tile.
-- The clipped/unioned result is small, so transforming it to 6372 afterward
-- for the slope calc is cheap.
DROP TABLE IF EXISTS features.ageb_topography CASCADE;
CREATE TABLE features.ageb_topography AS
SELECT
    a.cvegeo AS ageb_id,
    (ST_SummaryStats(
        ST_Slope(
            ST_Transform(ST_Union(ST_Clip(r.rast, ST_Transform(a.geom, 6365))), 6372),
            1,
            '32BF'
        )
    )).mean AS slope_mean
FROM base.ageb a
JOIN raw.dem r
  ON r.rast && ST_Transform(a.geom, 6365)
 AND ST_Intersects(r.rast, ST_Transform(a.geom, 6365))
GROUP BY a.cvegeo;

CREATE INDEX idx_ageb_topo_id ON features.ageb_topography (ageb_id);
ANALYZE features.ageb_topography;

-- Route Supply
DROP TABLE IF EXISTS features.ageb_route_supply CASCADE;
CREATE TABLE features.ageb_route_supply AS
SELECT
    a.cvegeo AS ageb_id,
    SUM(ST_Length(ST_Intersection(r.geom, ST_Buffer(a.geom, 800)))) / 1000.0 AS route_km_within_800m
FROM base.ageb a
JOIN base.transit_routes r ON ST_Intersects(r.geom, ST_Buffer(a.geom, 800))
GROUP BY a.cvegeo;

CREATE INDEX idx_ageb_route_supply_id ON features.ageb_route_supply (ageb_id);
ANALYZE features.ageb_route_supply;

-- Features Transport
DROP TABLE IF EXISTS features.ageb_features_transport CASCADE;
CREATE TABLE features.ageb_features_transport AS
SELECT
    a.cvegeo AS ageb_id,
    acc.stops_400m,
    acc.stops_800m,
    acc.min_stop_dist_m,
    COALESCE(rs.route_km_within_800m, 0) AS route_km_within_800m
FROM base.ageb a
LEFT JOIN features.ageb_accessibility acc ON acc.ageb_id = a.cvegeo
LEFT JOIN features.ageb_route_supply rs ON rs.ageb_id = a.cvegeo;

CREATE INDEX ageb_features_transport_ageb_id_idx ON features.ageb_features_transport (ageb_id);
ANALYZE features.ageb_features_transport;

-- Master Suitability
DROP TABLE IF EXISTS features.master_suitability CASCADE;
CREATE TABLE features.master_suitability AS
SELECT 
    a.cvegeo AS ageb_id,
    acc.stops_400m,
    acc.stops_800m,
    acc.min_stop_dist_m,
    emp.employment_proxy,
    COALESCE(rs.route_km_within_800m, 0) AS route_km_800m,
    COALESCE(topo.slope_mean, 0) AS slope_mean
FROM base.ageb a
JOIN features.ageb_accessibility acc ON a.cvegeo = acc.ageb_id
JOIN features.ageb_employment emp ON a.cvegeo = emp.ageb_id
LEFT JOIN features.ageb_topography topo ON a.cvegeo = topo.ageb_id
LEFT JOIN features.ageb_route_supply rs ON a.cvegeo = rs.ageb_id;

ANALYZE features.master_suitability;

-- NPP feature table (post-W0: no v_ntl_median; populated by src/build_nppv_features.py)
CREATE TABLE IF NOT EXISTS features.nppv_features (
    cve_ageb                 VARCHAR(15) PRIMARY KEY,
    n_intersections          NUMERIC,
    n_intersection_density   NUMERIC,
    n_street_density         NUMERIC,
    p_poi_density            NUMERIC,
    p_employment_proxy       NUMERIC,
    p_retail_density         NUMERIC,
    p_service_density        NUMERIC,
    p_land_use_mix           NUMERIC,
    pe_population             NUMERIC,
    pe_pop_density            NUMERIC,
    pe_dep_ratio              NUMERIC,
    pe_youth_share            NUMERIC,
    pe_marginacion            NUMERIC,
    pe_rezago                 NUMERIC,
    v_ridership_annual        NUMERIC,
    n_intersections_n         NUMERIC,
    n_intersection_density_n  NUMERIC,
    n_street_density_n        NUMERIC,
    p_poi_density_n           NUMERIC,
    p_employment_proxy_n      NUMERIC,
    p_retail_density_n        NUMERIC,
    p_service_density_n       NUMERIC,
    p_land_use_mix_n          NUMERIC,
    pe_population_n           NUMERIC,
    pe_pop_density_n           NUMERIC,
    pe_dep_ratio_n             NUMERIC,
    pe_youth_share_n           NUMERIC,
    pe_marginacion_n           NUMERIC,
    pe_rezago_n                NUMERIC,
    v_ridership_annual_n      NUMERIC,
    geom                      geometry(MultiPolygon, 6372)
);
CREATE INDEX IF NOT EXISTS idx_nppv_features_geom ON features.nppv_features USING gist(geom);