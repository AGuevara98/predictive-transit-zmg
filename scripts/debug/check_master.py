import subprocess

cmd = [
    "wsl",
    "-d",
    "Ubuntu",
    "-e",
    "bash",
    "-lc",
    (
        "source /mnt/c/Users/aguev/Documents/Maestria_UDG/tesis/predictive-transit-zmg/config.sh; "
        "export PGPASSWORD=$DB_PASS; "
        "psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \"SELECT 'base.ageb' AS obj, COUNT(*) FROM base.ageb;\"; "
        "psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \"SELECT 'base.gtfs_stops' AS obj, COUNT(*) FROM base.gtfs_stops;\"; "
        "psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \"SELECT 'features.ageb_accessibility' AS obj, COUNT(*) FROM features.ageb_accessibility;\"; "
        "psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \"SELECT 'features.ageb_employment' AS obj, COUNT(*) FROM features.ageb_employment;\"; "
        "psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \"SELECT 'features.ageb_topography' AS obj, COUNT(*) FROM features.ageb_topography;\"; "
        "psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \"SELECT 'features.ageb_route_supply' AS obj, COUNT(*) FROM features.ageb_route_supply;\"; "
        "psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \"SELECT 'features.master_suitability' AS obj, COUNT(*) FROM features.master_suitability;\""
        "; psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \"SELECT 'master_suitability_with_left_topography' AS obj, COUNT(*) FROM base.ageb a JOIN features.ageb_accessibility acc ON a.cvegeo = acc.ageb_id JOIN features.ageb_employment emp ON a.cvegeo = emp.ageb_id LEFT JOIN features.ageb_topography topo ON a.cvegeo = topo.ageb_id;\""
    ),
]

result = subprocess.run(cmd, capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
print(f'RETURN_CODE={result.returncode}')
