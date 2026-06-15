-- 002_w1_demand_tables.sql
-- W1 Demand Estimation Layer — output tables

-- Trip ends: one row per AGEB with productions, attractions, and transit demand
DROP TABLE IF EXISTS features.ageb_trip_ends CASCADE;
CREATE TABLE features.ageb_trip_ends (
    cve_ageb            VARCHAR(15) PRIMARY KEY,
    productions         NUMERIC,
    attractions         NUMERIC,
    vehicle_rate        NUMERIC,
    transit_propensity  NUMERIC,
    transit_demand      NUMERIC
);
COMMENT ON TABLE features.ageb_trip_ends IS
    'W1 trip-generation output: productions, attractions, and transit-propensity-weighted demand per AGEB';

-- OD matrix: sparse, one row per non-trivial AGEB pair (flow >= 0.5)
-- No FK constraints so DELETE/re-run in trip_ends does not cascade issues.
DROP TABLE IF EXISTS features.ageb_od_matrix CASCADE;
CREATE TABLE features.ageb_od_matrix (
    origin_cve_ageb  VARCHAR(15) NOT NULL,
    dest_cve_ageb    VARCHAR(15) NOT NULL,
    dist_m           NUMERIC,
    modeled_flow     NUMERIC,
    PRIMARY KEY (origin_cve_ageb, dest_cve_ageb)
);
COMMENT ON TABLE features.ageb_od_matrix IS
    'W1 doubly-constrained gravity model OD flows; sparse (flow >= 0.5 threshold)';

CREATE INDEX ageb_od_origin_idx ON features.ageb_od_matrix (origin_cve_ageb);
CREATE INDEX ageb_od_dest_idx   ON features.ageb_od_matrix (dest_cve_ageb);

ANALYZE features.ageb_trip_ends;
ANALYZE features.ageb_od_matrix;
