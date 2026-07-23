
## 1. Tablas activas del pipeline W1–W9

### `features.ageb_trip_ends`
Origen: **W1** (`src/w1_trip_generation.py` crea `productions`/`attractions`;
`src/w1_demand_surface.py` actualiza `vehicle_rate`/`transit_propensity`/`transit_demand`).
Un registro por AGEB con generación de viajes y demanda de transporte público.

|      Columna         |    Tipo            | Descripción | Unidad |
|---                   |---                 |---          |---|
| `cve_ageb`           | `VARCHAR(15)` (PK) | Clave del AGEB (Área Geoestadística Básica, INEGI) | — |
| `productions`        | `NUMERIC` | Viajes producidos (generados) por el AGEB, estimados a partir de población | viajes/día |
| `attractions`        | `NUMERIC` | Viajes atraídos por el AGEB (empleo/actividad económica), reescalados para que la suma total iguale a `productions` | viajes/día |
| `vehicle_rate`       | `NUMERIC` | Tasa de motorización/uso de vehículo privado del AGEB | proporción [0,1] |
| `transit_propensity` | `NUMERIC` | Propensión a usar transporte público = `1 - vehicle_rate` | proporción [0,1] |
| `transit_demand`     | `NUMERIC` | Demanda total de transporte = demanda total del AGEB × `transit_propensity` | viajes/día |

### `features.ageb_od_matrix`
Origen: **W1** (`src/w1_gravity_model.py`). Matriz origen-destino dispersa

|      Columna      |            Tipo              | Descripción                                          | Unidad |
|---                |---                           |---                                                   |---     |
| `origin_cve_ageb` | `VARCHAR(15)` (PK compuesta) | AGEB de origen                                       | —      |
| `dest_cve_ageb`   | `VARCHAR(15)` (PK compuesta) | AGEB de destino                                      | —      |
| `dist_m`          | `NUMERIC`                    | Distancia entre centroides origen-destino            | metros |
| `modeled_flow`    | `NUMERIC`                    | Flujo de viajes modelado entre el par origen-destino | viajes/día |

### `features.w2_calibration`
Origen: **W2** (`src/w2_gravity_calibration.py`). Un registro por corrida de
calibración del parámetro β del modelo de gravedad contra las líneas de
deseo observadas de la encuesta EOD 2022.

|      Columna      |        Tipo        |                    Descripción                           |       Unidad       |
|---                |---                 |---                                                       |---                 |
| `run_ts`          | `TIMESTAMPTZ` (PK) | Marca de tiempo de la corrida (default `NOW()`)          | timestamp          |
| `beta_w1`         | `NUMERIC`          | Valor a priori de β usado en W1 (2.0)                    | adimensional       |
| `beta_calibrated` | `NUMERIC`          | Valor de β ajustado por `scipy.optimize.minimize_scalar` | adimensional       |
| `n_pairs`         | `INTEGER`          | Número de pares de zonas EOD usados en el ajuste         | conteo             |
| `rmse_log`        | `NUMERIC`          | Raíz del error cuadrático medio en escala logarítmica    | adimensional       |
| `r2`              | `NUMERIC`          | Coeficiente de determinación del ajuste                  | adimensional [0,1] |
| `notes`           | `TEXT`             | Notas libres sobre la corrida                            | —                  |

### `features.ageb_accessibility` (versión vigente, W3)
Origen: **W3** (`src/w3_accessibility.py`)

|        Columna        |               Tipo                   |                            Descripción                              |       Unidad        |
|---                    |---                                   |---                                                                  |---                  |
| `cve_ageb`            | `TEXT` (PK, FK → `base.ageb.cvegeo`) | Clave del AGEB                                                      | —                   |
| `n_boarding_stops`    | `INTEGER`                            | Número de paradas GTFS abordables a ≤400 m del AGEB                 | conteo              |
| `accessibility_score` | `NUMERIC`                            | Empleo (proxy) alcanzable en ≤45 min de viaje en transporte público | empleos alcanzables |
| `accessibility_n`     | `NUMERIC`                            | `accessibility_score` normalizado (log1p + min-max)                 | proporción [0,1]    |

### `features.ageb_coverage_gap`
Origen: **W3** (`src/w3_coverage_gap.py`). Índice de brecha de cobertura:
combina demanda de W1 con accesibilidad de W3.

|        Columna        |                 Tipo                 |                                  Descripción                                     | Unidad              |
|---                    |---                                   |---                                                                               |---                  |
| `cve_ageb`            | `TEXT` (PK, FK → `base.ageb.cvegeo`) | Clave del AGEB                                                                   | —                   |
| `transit_demand`      | `NUMERIC`                            | Copia de `ageb_trip_ends.transit_demand`                                         | viajes/día          |
| `accessibility_score` | `NUMERIC`                           | Copia de `ageb_accessibility.accessibility_score`                                 | empleos alcanzables |
| `coverage_gap_raw`    | `NUMERIC`                          | `transit_demand / (accessibility_score + 1.0)`                                        | adimensional     |
| `coverage_gap_n`      | `NUMERIC`                         | `coverage_gap_raw` normalizado (log1p + min-max)                                       | proporción [0,1] |
| `demand_quantile`     | `INTEGER`                        | Quintil de demanda (1–5)                                                                      | quintil    |
| `access_quantile`     | `INTEGER`                        | Quintil de accesibilidad (1–5)                                                                | quintil    |
| `gap_category`        | `TEXT`                           | `'High-gap'` (demanda≥Q4 y acceso≤Q2), `'Low-gap'` (demanda≤Q2 y acceso≥Q4), o `'Medium-gap'` | categórico |

### `features.nppv_features`
Origen: **W0 / build inicial** (`src/build_nppv_features.py`, auto-reparado
por `ensure_nppv_features()` en `src/db_preflight.py`).

|        Columna           |        Tipo        |                           Descripción                              |        Unidad        |      Dimensión       |
|---                       |---                 |---                                                                 |---                   |---                   |
| `cve_ageb`               | `VARCHAR(15)` (PK) | Clave del AGEB                                                     | —                    | —                    |
| `n_intersections`        | `NUMERIC`          | Intersecciones viales (≥3 calles) por área                         | intersecciones/km²   | NODE (red vial)      |
| `n_intersection_density` | `NUMERIC`          | Intersecciones de 4+ vías por área                                 | intersecciones/km²   | NODE                 |
| `n_street_density`       | `NUMERIC`          | Longitud de calles por área                                        | m/km²                | NODE                 |
| `p_poi_density`          | `NUMERIC`          | Densidad de puntos de interés (DENUE)                              | POIs/km²             | PLACE (uso de suelo) |
| `p_employment_proxy`     | `NUMERIC`          | Empleo proxy total (por estrato de personal ocupado, DENUE)        | empleos (proxy)      | PLACE                |
| `p_retail_density`       | `NUMERIC`          | Densidad de establecimientos comerciales (sector 46)               | establecimientos/km² | PLACE                |
| `p_service_density`      | `NUMERIC`          | Densidad de establecimientos de salud/educación/gobierno           | establecimientos/km² | PLACE                |
| `p_land_use_mix`         | `NUMERIC`          | Entropía de Shannon de la mezcla de usos de suelo (sectores DENUE) | nats (entropía) [0,∞)|PLACE                 |
| `pe_population`          | `NUMERIC`          | Población total (censo 2020)                                       | personas             | PEOPLE               |
| `pe_pop_density`         | `NUMERIC`          | Densidad poblacional                                               | personas/km²         | PEOPLE               |
| `pe_dep_ratio`           | `NUMERIC`          | Razón de dependencia = (pob. 0-14 + 65+) / pob. 15-64, tope 5.0    | razón                |PEOPLE                |
| `pe_youth_share`         | `NUMERIC`          | Proporción de población de 15-29 años                              | proporción [0,1]     | PEOPLE               |
| `pe_marginacion`         | `NUMERIC`          | Índice de marginación urbana 2020 (`IM_2020`, CONAPO/INEGI)        | índice               | PEOPLE               |
| `pe_rezago`              | `NUMERIC`          | Índice de rezago social 2020 (`IRS_2020`)                          | índice               | PEOPLE               |
| `v_ridership_annual`     | `NUMERIC`          | Pasajeros anuales abordados 2023 a nivel municipio (solo municipio 39/GDL-SITEUR tiene dato; funciona como bandera binaria "tiene SITEUR") | pasajeros/año | VITALITY |
| `*_n` (×15, uno por cada columna anterior) | `NUMERIC` | Versión normalizada [0,1] de la columna cruda correspondiente | proporción [0,1] | —                    |
| `geom`                   | `geometry(MultiPolygon, 6372)` | Geometría del AGEB en EPSG:6372                        | —                    | —                    |


### `features.nppv_w4_weights`
Origen: **W4** (`src/w4_prioritization.py`). Pesos CRITIC/EWM por indicador
usados para construir `npp_score`.

|      Columna      |        Tipo        |                                   Descripción                                    |      Unidad      |
|---                |---                 |---                                                                               |---               |
| `feature`         | `VARCHAR(50)` (PK) | Nombre de la columna normalizada de `nppv_features` (p. ej. `pe_population_n`)   | —                |
| `dimension`       | `VARCHAR(20)`      | Dimensión NPP-V a la que pertenece: `NODE`, `PLACE` o `PEOPLE`                   | categórico       |
| `critic_weight`   | `NUMERIC`          | Peso por método CRITIC (contraste × conflicto entre indicadores)                 | proporción [0,1] |
| `ewm_weight`      | `NUMERIC`          | Peso por método de entropía (EWM)                                                | proporción [0,1] |
| `ensemble_weight` | `NUMERIC`          | Peso final = combinación de `critic_weight` y `ewm_weight`, usado en `npp_score` | proporción [0,1] |

### `features.nppv_prioritization`
Origen: **W4** (`src/w4_prioritization.py`). Puntaje final de priorización
por AGEB (los 1,881 AGEBs de la ZMG).

|       Columna       |                 Tipo                 |                              Descripción                                        |      Unidad      |
|---                  |---                                   |---                                                                              |---               |
| `cve_ageb`          | `TEXT` (PK, FK → `base.ageb.cvegeo`) | Clave del AGEB                                                                  | —                |
| `npp_score`         | `NUMERIC`                            | Σ(indicador_n × `ensemble_weight`) sobre 14 indicadores NPP (excluye vitalidad) | proporción [0,1] |
| `equity_score`      | `NUMERIC`                            | Promedio de `pe_marginacion_n` y `pe_rezago_n`                                  | proporción [0,1] |
| `final_score`       | `NUMERIC`                            | `0.80 × npp_score + 0.20 × equity_score` (ALPHA=0.20, bono de equidad)          | proporción [0,1] |
| `priority_rank`     | `INTEGER`                            | Ranking del AGEB por `final_score` (1 = mayor prioridad)                        | ranking          |
| `priority_quintile` | `INTEGER`                            | Quintil de `final_score` (1–5)                                                  | quintil          |

### `features.route_candidates`
Origen: **W6** (`src/w6_anchors.py`, `w6_candidates.py`, `w6_graph.py`,
`w6_mode.py`, orquestado por `src/run_w6.py`). Corredores candidatos nuevos,
generados a partir de anclas de brecha (W3) sobre el grafo vial de OSM, con
puntajes multiobjetivo de W5.

|        Columna         |      Tipo     |                                             Descripción                                                   |      Unidad      |
|---                     |---            |---                                                                                                        |---               |
| `candidate_id`         | `TEXT` (PK)   | Identificador del corredor candidato                                                                      | —                |
| `corridor_group`       | `INTEGER`     | Grupo/clúster de anclas del que se generó el corredor                                                     | —                |
| `route_km`             | `FLOAT8`      | Longitud de la ruta candidata sobre el grafo vial                                                         | km               |
| `n_stops`              | `INTEGER`     | Número de paradas estimadas a lo largo del corredor                                                       | conteo           |
| `straight_line_km`     | `FLOAT8`      | Distancia en línea recta entre extremos del corredor                                                      | km               |
| `connects_to_existing` | `BOOLEAN`     | Si el corredor conecta con la red de transporte existente                                                 | booleano         |
| `n_served_agebs`       | `INTEGER`     | Número de AGEBs servidos por el corredor                                                                  | conteo          | 
| `total_demand`         | `FLOAT8`      | Demanda de transporte total captada (suma de `transit_demand` de AGEBs servidos)                          | viajes/día       |
| `f1_demand_gain`       | `FLOAT8`      | Objetivo 1: ganancia de accesibilidad ponderada por demanda, reescalada [0, factor de ganancia]           | proporción       |
| `f2_route_km`          | `FLOAT8`      | Objetivo 2: longitud de ruta (a minimizar)                                                                | km               |
| `f3_equity`            | `FLOAT8`      | Objetivo 3: promedio de `equity_score` de los AGEBs servidos                                              | proporción [0,1] |
| `composite_score`      | `FLOAT8`      | Puntaje compuesto (combina f1, f2 eficiencia, f3, penalización por transbordo)                                | adimensional |
| `total_score`          | `FLOAT8`      | Puntaje final usado para ordenar/priorizar candidatos                                                         | adimensional |
| `pareto_rank`          | `INTEGER`     | Rango de frente de Pareto (1 = no dominado) sobre f1/f2/f3                                                        | ranking  |
| `feasible`             | `BOOLEAN`     | Si el candidato cumple restricciones mínimas (p. ej. demanda diaria mínima 500 viajes/día, `route_km` máx. 30 km) | booleano |
| `mode_assignment`      | `TEXT`        | Modo asignado según `total_demand`: `bus`, `BRT` o `LRT` (umbrales configurables)                               | categórico |
| `geom`                 | `GEOMETRY(LineString, 6372)` | Geometría de la ruta candidata en EPSG:6372                                                      | —          |

### `features.route_audit`
Origen: **W7** (`src/w7_route_scorer.py`, `w7_modifications.py`,
orquestado por `src/run_w7.py`). Auditoría de rutas existentes de SITEUR con
banderas y propuestas de modificación.
  
|      Columna       |    Tipo     |                    Descripción                              |        Unidad        |
|---                 |---          |---                                                          |---                   |
| `route_id`         | `TEXT` (PK) | Identificador de la ruta GTFS/SITEUR                        | —                    |
| `route_short_name` | `TEXT`      | Nombre corto/comercial de la ruta                           | —                    |
| `route_km`         | `FLOAT8`    | Longitud real de la ruta                                    | km                   |
| `n_stops`          | `INT`       | Número de paradas de la ruta                                | conteo               |
| `straight_line_km` | `FLOAT8`    | Distancia en línea recta entre extremos de la ruta          | km                   |
| `detour_ratio`     | `FLOAT8`    | `route_km / straight_line_km` (qué tan directa es la ruta)   | razón               |
| `f1_demand_gain`   | `FLOAT8`    | Igual que en `route_candidates`: ganancia de demanda servida | proporción          |
| `f2_route_km`      | `FLOAT8`    | Longitud de ruta                                             | km                  |
| `f3_equity`        | `FLOAT8`    | Equidad promedio de AGEBs servidos                           | proporción [0,1]    |
| `total_score`      | `FLOAT8`    | Puntaje W5 total de la ruta existente                        | adimensional        |
| `pareto_rank`      | `INT`       | Rango de Pareto entre rutas existentes                       | ranking                                                            |
| `flag`             | `TEXT`      | Bandera de diagnóstico: `'Redundant'` (traslape alto con otra ruta), `'Indirect'` (`detour_ratio` > 1.5), `'Low demand'`, o `NULL` (sin bandera) | categórico |
| `modification_type` | `TEXT`    | Tipo de modificación propuesta: `'shortcut'` (ruta directa si es indirecta), `'merge'` (fusión si es redundante), etc. | categórico |
| `overlap_route_id`  | `TEXT`    | `route_id` de la ruta con la que se traslapa (si aplica, para `'Redundant'`/`'merge'`) | — |
| `geom`              | `GEOMETRY(LineString, 6372)` | Geometría de la ruta en EPSG:6372 | — |

---

## 2. Tablas legacy / Fase 2 (creadas por `DDL.sql`, retiradas)


### `features.ageb_economic_activity`
Agregación de actividad económica (DENUE) por AGEB.

|        Columna        | Tipo (inferido) |                                              Descripción                                            | Unidad          |
|---                    |---              |---                                                                                                  |---              |
| `ageb_id`             | `TEXT` (PK)     | Clave del AGEB (`base.ageb.cvegeo`)                                                                 | —               |
| `denue_units_total`   | `BIGINT`        | Total de unidades económicas DENUE intersectadas con el AGEB (excluye estratos 0-5 y 6-10 personas) | conteo          |
| `jobs_proxy_sum`      | `NUMERIC`       | Suma del proxy de empleo por estrato de personal ocupado                                            | empleos (proxy) |
| `denue_manufacturing` | `BIGINT`        | Unidades del sector manufactura (SCIAN 31-33)                                                       | conteo          |
| `denue_retail`        | `BIGINT`        | Unidades del sector comercio al por menor (SCIAN 46)                                                | conteo          |
| `denue_education`     | `BIGINT`        | Unidades del sector educación (SCIAN 61)                                                            | conteo          |
| `denue_health`        | `BIGINT`        | Unidades del sector salud (SCIAN 62)                                                                | conteo          |
| `denue_government`    | `BIGINT`        | Unidades de gobierno (SCIAN 931)                                                                    | conteo          |

### `features.ageb_employment` 
|         Columna        | Tipo (inferido) |                    Descripción                  |      Unidad     |
|---                     |---              |---                                              |---              |
| `ageb_id`              | `TEXT`          | Clave del AGEB                                  | —               |
| `total_establishments` | `BIGINT`        | Total de establecimientos DENUE en el AGEB      | conteo          |
| `employment_proxy`     | `NUMERIC`       | Proxy de empleo por estrato de personal ocupado | empleos (proxy) |

### `features.ageb_accessibility` (versión `DDL.sql`, superada)
|      Columna      |   Tipo (inferido)  |            Descripción            | Unidad |
|---                |---                 |---                                |---     |
| `ageb_id`         | `TEXT`             | Clave del AGEB                    | —      |
| `stops_400m`      | `BIGINT`           | Número de paradas GTFS a ≤400 m   | conteo |
| `stops_800m`      | `BIGINT`           | Número de paradas GTFS a ≤800 m   | conteo |
| `min_stop_dist_m` | `DOUBLE PRECISION` | Distancia a la parada más cercana | metros |

### `features.ageb_topography`
|    Columna   |  Tipo (inferido)   |                         Descripción                         | Unidad |
|---           |---                 |---                                                          |---     |
| `ageb_id`    | `TEXT`             | Clave del AGEB                                              | —      |
| `slope_mean` | `DOUBLE PRECISION` | Pendiente media del terreno (DEM), calculada con `ST_Slope` | grados |


### `features.ageb_route_supply`
|          Columna       |  Tipo (inferido)   |                   Descripción                      | Unidad |
|---                     |---                 |---                                                 |---     |
| `ageb_id`              | `TEXT`             | Clave del AGEB                                     | —      |
| `route_km_within_800m` | `DOUBLE PRECISION` | Km de rutas de transporte dentro de 800 m del AGEB | km     |

### `features.ageb_features_transport`
Combina accesibilidad (versión legacy) y oferta de rutas.

|        Columna         |  Tipo (inferido)   |                 Descripción                | Unidad |
|---                     |---                 |---                                         |---     |
| `ageb_id`              | `TEXT`             | Clave del AGEB                             | —      |
| `stops_400m`           | `BIGINT`           | Ver `ageb_accessibility` (legacy)          | conteo |
| `stops_800m`           | `BIGINT`           | Ver `ageb_accessibility` (legacy)          | conteo |
| `min_stop_dist_m`      | `DOUBLE PRECISION` | Ver `ageb_accessibility` (legacy)          | metros |
| `route_km_within_800m` | `DOUBLE PRECISION` | Ver `ageb_route_supply` (0 si no hay dato) | km     |


### `features.master_suitability`
Tabla legacy que combinaba variables de accesibilidad, empleo, topografía y
oferta de rutas para el modelo binario de idoneidad `no_stop_features_v1`
(retirado).

|       Columna      |  Tipo (inferido)   |                 Descripción                |      Unidad     |
|---                 |---                 |---                                         |---              |
| `ageb_id`          | `TEXT`             | Clave del AGEB                             | —               |
| `stops_400m`       | `BIGINT`           | Ver `ageb_accessibility` (legacy)          | conteo          |
| `stops_800m`       | `BIGINT`           | Ver `ageb_accessibility` (legacy)          | conteo          |
| `min_stop_dist_m`  | `DOUBLE PRECISION` | Ver `ageb_accessibility` (legacy)          | metros          |
| `employment_proxy` | `NUMERIC`          | Ver `ageb_employment`                      | empleos (proxy) |
| `route_km_800m`    | `DOUBLE PRECISION` | Ver `ageb_route_supply` (0 si no hay dato) | km              |
| `slope_mean`       | `DOUBLE PRECISION` | Ver `ageb_topography` (0 si no hay dato)   | grados          |
