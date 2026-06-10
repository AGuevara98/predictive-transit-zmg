#!/bin/bash
# Run read-only psql checks inside WSL
CONFIG=/mnt/c/Users/aguev/Documents/Maestria_UDG/tesis/predictive-transit-zmg/config.sh
[ -f "$CONFIG" ] && source "$CONFIG"
# Fallback defaults (should match config.py)
: ${DB_HOST:=localhost}
: ${DB_USER:=aguevara}
: ${DB_NAME:=gdl_metro}

psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 'station_npv_audit' AS obj, COUNT(*) FROM features.station_npv_audit;"
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 'v_critic_weights' AS obj, COUNT(*) FROM features.v_critic_weights;"
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 'training_labels' AS obj, COUNT(*) FROM features.training_labels;"

psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT COUNT(*) AS total, SUM((npv_score IS NULL)::int) AS null_npv_score FROM features.station_npv_audit;"
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT COUNT(*) AS total, SUM((stops_800m IS NULL)::int) AS null_stops_800m, SUM((min_stop_dist_m IS NULL)::int) AS null_min_stop_dist_m, SUM((employment_proxy IS NULL)::int) AS null_employment_proxy, SUM((route_km_800m IS NULL)::int) AS null_route_km_800m, SUM((slope_mean IS NULL)::int) AS null_slope_mean FROM features.master_suitability;"

psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT MIN(stops_800m) AS min, MAX(stops_800m) AS max, AVG(stops_800m) AS avg, STDDEV_POP(stops_800m) AS std FROM features.master_suitability;"
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT MIN(min_stop_dist_m) AS min, MAX(min_stop_dist_m) AS max, AVG(min_stop_dist_m) AS avg, STDDEV_POP(min_stop_dist_m) AS std FROM features.master_suitability;"
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT MIN(employment_proxy) AS min, MAX(employment_proxy) AS max, AVG(employment_proxy) AS avg, STDDEV_POP(employment_proxy) AS std FROM features.master_suitability;"

psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT SUM(weight) AS sum_weights, COUNT(*) AS n FROM features.v_critic_weights;"
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT * FROM features.v_critic_weights ORDER BY weight DESC LIMIT 10;"

psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT CORR(stops_800m::double precision, employment_proxy::double precision) AS corr_stops_emp, CORR(stops_800m::double precision, route_km_800m::double precision) AS corr_stops_route FROM features.master_suitability;"

psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT label, COUNT(*) FROM features.training_labels GROUP BY label ORDER BY label;"
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT COUNT(DISTINCT ageb_id) FROM features.training_labels;"
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT ageb_id, COUNT(*) FROM features.training_labels GROUP BY ageb_id HAVING COUNT(*) > 1 LIMIT 10;"

echo "--- CSV: outputs/phase1/training_labels.csv (head) ---"
sed -n '1,10p' /mnt/c/Users/aguev/Documents/Maestria_UDG/tesis/predictive-transit-zmg/outputs/phase1/training_labels.csv 2>/dev/null || echo 'file not found'

echo "--- CSV: outputs/phase1/critic_weights.csv (head) ---"
sed -n '1,10p' /mnt/c/Users/aguev/Documents/Maestria_UDG/tesis/predictive-transit-zmg/outputs/phase1/critic_weights.csv 2>/dev/null || echo 'file not found'

echo "--- Report existence ---"
[ -f /mnt/c/Users/aguev/Documents/Maestria_UDG/tesis/predictive-transit-zmg/outputs/phase1/report.html ] && echo 'report: yes' || echo 'report: no'
