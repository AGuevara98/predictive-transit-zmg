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
    "ID"::int AS denue_id,
    "Clee" AS clee,
    "Nombre de la Unidad Económica" AS nombre_unidad,
    "Razón social" AS razon_social,
    "Código de la clase de actividad SCIAN" AS scian_codigo,
    "Nombre de clase de la actividad" AS scian_nombre,
    "Descripcion estrato personal ocupado" AS estrato_personal,
    "Clave entidad" AS cve_ent,
    "Clave municipio" AS cve_mun,
    "Clave localidad" AS cve_loc,
    "Área geoestadística básica " AS ageb_id,
    "Manzana" AS manzana_id,
    "Latitud"::double precision AS latitud,
    "Longitud"::double precision AS longitud,
    "Fecha de incorporación al DENUE" AS fecha_alta
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
    ST_Transform(geom, 6372) AS geom
FROM raw.ageb
WHERE "CVE_ENT" = '14'
  AND "CVE_AGEB" NOT LIKE '%A%'
  AND "CVE_MUN" IN ('039','044','051','070','097','098','101','120','009','124');

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
        WHEN d.estrato_personal = '251 y más personas' THEN 300
        ELSE 0 END) AS employment_proxy
FROM base.ageb a
LEFT JOIN raw.denue d ON ST_Intersects(a.geom, ST_Transform(d.geom, 6372))
WHERE (d.scian_codigo IS NULL OR 
      (LEFT(d.scian_codigo::text, 2) IN ('31','32','33','43','46','54','55','61','62','71') 
       OR d.scian_codigo::text LIKE '561%' 
       OR d.scian_codigo::text LIKE '722%' 
       OR d.scian_codigo::text LIKE '931%')
      AND d.estrato_personal NOT IN ('0 a 5 personas', '6 a 10 personas'))
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
DROP TABLE IF EXISTS features.ageb_topography CASCADE;
CREATE TABLE features.ageb_topography AS
SELECT 
    a.cvegeo AS ageb_id,
    (ST_SummaryStats(ST_Slope(ST_Union(ST_Clip(r.rast, a.geom)), 1, '32BF'))).mean AS slope_mean
FROM base.ageb a
JOIN raw.dem r ON ST_Intersects(r.rast, a.geom)
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
    topo.slope_mean
FROM base.ageb a
JOIN features.ageb_accessibility acc ON a.cvegeo = acc.ageb_id
JOIN features.ageb_employment emp ON a.cvegeo = emp.ageb_id
JOIN features.ageb_topography topo ON a.cvegeo = topo.ageb_id
LEFT JOIN features.ageb_route_supply rs ON a.cvegeo = rs.ageb_id;

ANALYZE features.master_suitability;