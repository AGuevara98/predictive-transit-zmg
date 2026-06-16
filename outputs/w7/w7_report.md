# W7 Existing Route Audit -- Report

## Summary

- **Routes audited:** 247
- **Feasible routes:** 19
- **Routes flagged:** 231 (75 Low demand, 116 Indirect, 40 Redundant)

## Methodology

1. **GTFS loader:** Route geometries built from shapes.txt (EPSG:6372).
   Fallback to stop-sequence reconstruction if shape_id unavailable.
2. **Served AGEBs:** `ST_DWithin(ST_Centroid(ageb.geom), route_geom, 400m)`.
3. **W5 objective:** f1 demand-gain, f2 route length (efficiency), f3 equity.
4. **W5 constraints:** detour_ratio <= 1.8, stop spacing 300-1000m,    demand >= 500 trips/day, route_km <= 30km.
5. **Pareto ranking:** Non-dominated sort on (-f1, f2, -f3).
6. **Flags:**
   - Low demand: f1 < 0.2 AND total_score < 0.3
   - Indirect: detour_ratio > 1.5
   - Redundant: Jaccard overlap of served AGEBs >= 60% with higher-scoring route

## Score Distribution

- Mean total_score: 0.230
- Median total_score: 0.227
- Mean detour_ratio: 1511.612
- Mean f1_demand_gain: 0.012
- Mean f3_equity: 0.550

## Top 10 Routes by Score

| route_id | route_short_name | total_score | f1_demand_gain | f3_equity | pareto_rank | flag |
|---|---|---|---|---|---|---|
| T16B-C08-M | T16B-C08-Mesitas | 0.7 | 0.348 | 0.51 | 1 | nan |
| C131-V2 | C131-V2 | 0.368 | 0.022 | 0.543 | 1 | nan |
| T14B-C03-2 | T14B-C03-2 | 0.366 | 0.057 | 0.575 | 1 | nan |
| MC-A13 | MC-A13 | 0.365 | 0.003 | 0.566 | 1 | Indirect |
| MC-A03 | MC-A03 | 0.365 | 0.001 | 0.562 | 1 | nan |
| MC-A10 | MC-A10 | 0.362 | 0.005 | 0.586 | 1 | Indirect |
| MC-A06 | MC-A06 | 0.362 | 0.006 | 0.568 | 1 | Indirect |
| MC-A16 | MC-A16 | 0.362 | 0.013 | 0.563 | 1 | Indirect |
| MC-A05 | MC-A05 | 0.361 | 0.001 | 0.545 | 1 | nan |
| T02-A02 | T02-A02 | 0.358 | 0.051 | 0.578 | 1 | nan |

## Bottom 10 Routes by Score

| route_id | route_short_name | total_score | f1_demand_gain | f3_equity | pareto_rank | flag |
|---|---|---|---|---|---|---|
| C129 | C129 | 0.134 | 0.005 | 0.516 | 10 | Redundant |
| T04A-1 | T04A-1 | 0.135 | 0.002 | 0.533 | 12 | Low demand |
| LM-V03 | LM-V03 | 0.136 | 0.003 | 0.531 | 10 | Low demand |
| T11B | T11B | 0.136 | 0.002 | 0.537 | 12 | Low demand |
| C128 | C128 | 0.137 | 0.003 | 0.532 | 9 | Indirect |
| T13A | T13A | 0.137 | 0.016 | 0.482 | 10 | Low demand |
| C98 | C98 | 0.137 | 0.003 | 0.538 | 10 | Indirect |
| T04A-2 | T04A-2 | 0.137 | 0.004 | 0.533 | 8 | Indirect |
| C14-V1 | C14-V1 | 0.138 | 0.005 | 0.53 | 9 | Indirect |
| C130 | C130 | 0.138 | 0.006 | 0.526 | 10 | Redundant |

## Flagged Routes

| route_id | route_short_name | total_score | detour_ratio | flag | overlap_route_id |
|---|---|---|---|---|---|
| C129 | C129 | 0.134 | 1.203 | Redundant | C128A-V1 |
| T04A-1 | T04A-1 | 0.135 | 1.455 | Low demand | nan |
| LM-V03 | LM-V03 | 0.136 | 1.291 | Low demand | nan |
| T11B | T11B | 0.136 | 1.485 | Low demand | nan |
| C128 | C128 | 0.137 | 1.686 | Indirect | nan |
| T13A | T13A | 0.137 | 1.417 | Low demand | nan |
| C98 | C98 | 0.137 | 1.95 | Indirect | nan |
| T04A-2 | T04A-2 | 0.137 | 1.6 | Indirect | nan |
| C14-V1 | C14-V1 | 0.138 | 1.514 | Indirect | nan |
| C130 | C130 | 0.138 | 1.6 | Redundant | C125-V1 |
| C108 | C108 | 0.138 | 82767.584 | Indirect | nan |
| LM-V01 | LM-V01 | 0.139 | 1.574 | Redundant | C125-V1 |
| T17-C01 | T17-C01 | 0.139 | 1.684 | Indirect | nan |
| C135 | C135 | 0.139 | 2.244 | Indirect | nan |
| C93 | C93 | 0.14 | 2.419 | Indirect | nan |
| C124 | C124 | 0.14 | 1.642 | Indirect | nan |
| C53 | C53 | 0.14 | 1.682 | Indirect | nan |
| MP-T01 | MP-T01 | 0.142 | 3.176 | Indirect | nan |
| C125-V2 | C125-V2 | 0.143 | 1.578 | Redundant | C125-V1 |
| C125-V1 | C125-V1 | 0.143 | 1.621 | Indirect | nan |
| C136 | C136 | 0.144 | 1.927 | Indirect | nan |
| LM-V02 | LM-V02 | 0.144 | 1.104 | Low demand | nan |
| C64 | C64 | 0.144 | 1.473 | Low demand | nan |
| C120 | C120 | 0.145 | 1.451 | Low demand | nan |
| C54 | C54 | 0.146 | 1.449 | Low demand | nan |
| T07 | T07 | 0.146 | 1.645 | Indirect | nan |
| C111-V1 | C111-V1 | 0.146 | 1.587 | Redundant | C111-V3 |
| MP-A05-1 | MP-A05-1 | 0.148 | 47097.905 | Indirect | nan |
| C127-V1 | C127-V1 | 0.149 | 1.48 | Low demand | nan |
| MP-C01 | MP-C01 | 0.149 | 2.012 | Indirect | nan |
| MP-C02 | MP-C02 | 0.15 | 1.737 | Indirect | nan |
| C126-V1 | C126-V1 | 0.151 | 1.859 | Redundant | LM-C01 |
| LM-C01 | LM-C01 | 0.151 | 1.859 | Indirect | nan |
| C102 | C102 | 0.151 | 1.864 | Indirect | nan |
| C46-V2 | C46-V2 | 0.152 | 1.554 | Indirect | nan |
| C71 | C71 | 0.153 | 1.648 | Indirect | nan |
| C111-V3 | C111-V3 | 0.153 | 1.492 | Redundant | C67-V1 |
| C67-V1 | C67-V1 | 0.154 | 1.656 | Indirect | nan |
| C117 | C117 | 0.155 | 1.541 | Indirect | nan |
| C15 | C15 | 0.156 | 1.429 | Low demand | nan |
| C104 | C104 | 0.156 | 27561.838 | Indirect | nan |
| T18-1-T | T18-1-Terranova | 0.157 | 27837.614 | Redundant | T18-2-L |
| T15 | T15 | 0.159 | 1.739 | Indirect | nan |
| C27 | C27 | 0.159 | 2.065 | Indirect | nan |
| C133-V1 | C133-V1 | 0.16 | 27293.671 | Indirect | nan |
| T18-2-T | T18-2-Terranova | 0.161 | 27385.464 | Redundant | T18-2-L |
| T18-1-L | T18-1-Lopez | 0.163 | 27178.814 | Redundant | T18-2-L |
| C41-V1 | C41-V1 | 0.164 | 1.72 | Indirect | nan |
| C65 | C65 | 0.164 | 1.383 | Low demand | nan |
| T18-2-L | T18-2-Lopez | 0.165 | 26887.106 | Indirect | nan |
| C103 | C103 | 0.166 | 2.533 | Indirect | nan |
| C105 | C105 | 0.166 | 2.528 | Indirect | nan |
| C80-V1 | C80-V1 | 0.167 | 1.907 | Indirect | nan |
| T17 | T17 | 0.168 | 1.308 | Low demand | nan |
| T09-O | T09-Oblatos | 0.17 | 26442.577 | Indirect | nan |
| T14B | T14B | 0.17 | 102.075 | Indirect | nan |
| C67-V2 | C67-V2 | 0.173 | 1.629 | Indirect | nan |
| ST_L1 | L1 | 0.174 | 1.372 | Redundant | C109 |
| C110-V2 | C110-V2 | 0.175 | 1.105 | Redundant | C109 |
| C116-B | C116-B | 0.175 | 1.67 | Indirect | nan |
| C17 | C17 | 0.175 | 2.059 | Indirect | nan |
| MP-A06 | MP-A06 | 0.176 | 1.26 | Low demand | nan |
| MP-C03 | MP-C03 | 0.176 | 1.561 | Redundant | MP-T03 |
| T16B | T16B | 0.177 | 1.377 | Low demand | nan |
| C101 | C101 | 0.179 | 1.61 | Indirect | nan |
| C123-V1 | C123-V1 | 0.18 | 1.27 | Low demand | nan |
| T04B-1 | T04B-1 | 0.182 | 1.295 | Low demand | nan |
| C128A-V1 | C128A-V1 | 0.182 | 1.381 | Low demand | nan |
| C19 | C19 | 0.183 | 1.764 | Indirect | nan |
| C14-V2 | C14-V2 | 0.185 | 1.595 | Indirect | nan |
| C28 | C28 | 0.185 | 1.639 | Indirect | nan |
| C39-V2 | C39-V2 | 0.189 | 1.348 | Redundant | C39-V1 |
| C89 | C89 | 0.189 | 1.927 | Redundant | C88-V2 |
| C46-V1 | C46-V1 | 0.19 | 1.389 | Low demand | nan |
| C66-V2 | C66-V2 | 0.19 | 1.638 | Indirect | nan |
| MP-T02 | MP-T02 | 0.192 | 1.385 | Low demand | nan |
| C122 | C122 | 0.193 | 2.241 | Indirect | nan |
| C38-V2 | C38-V2 | 0.193 | 1.701 | Redundant | C39-V1 |
| C06 | C06 | 0.193 | 1.95 | Indirect | nan |
| C99 | C99 | 0.194 | 2.23 | Indirect | nan |
| C76-V1 | C76-V1 | 0.195 | 1.625 | Redundant | C76-V2 |
| C37-V1 | C37-V1 | 0.195 | 2.042 | Redundant | C37-V2 |
| C38-V1 | C38-V1 | 0.196 | 1.509 | Redundant | C39-V1 |
| C58-V2 | C58-V2 | 0.196 | 1.606 | Indirect | nan |
| C20-V1 | C20-V1 | 0.197 | 1.667 | Indirect | nan |
| C106 | C106 | 0.199 | 2.104 | Indirect | nan |
| C112 | C112 | 0.199 | 1.429 | Low demand | nan |
| C70 | C70 | 0.201 | 2.604 | Indirect | nan |
| C41-V2 | C41-V2 | 0.202 | 1.579 | Indirect | nan |
| C37-V2 | C37-V2 | 0.202 | 1.989 | Indirect | nan |
| C66-V1 | C66-V1 | 0.202 | 1.29 | Low demand | nan |
| C79 | C79 | 0.202 | 1.738 | Indirect | nan |
| C116-A | C116-A | 0.203 | 1.744 | Indirect | nan |
| C39-V1 | C39-V1 | 0.203 | 1.307 | Low demand | nan |
| C26 | C26 | 0.204 | 1.46 | Low demand | nan |
| C110-V1 | C110-V1 | 0.205 | 1.548 | Indirect | nan |
| C134 | C134 | 0.209 | 1.14 | Low demand | nan |
| C73 | C73 | 0.211 | 4.369 | Indirect | nan |
| C138 | C138 | 0.213 | 33990.5 | Indirect | nan |
| C118 | C118 | 0.213 | 1.423 | Low demand | nan |
| C76-V2 | C76-V2 | 0.214 | 1.484 | Low demand | nan |
| C60 | C60 | 0.214 | 1.646 | Redundant | C58-V1 |
| C88-V2 | C88-V2 | 0.215 | 1.358 | Low demand | nan |
| T04B-3 | T04B-3 | 0.215 | 1.288 | Low demand | nan |
| C111-V2 | C111-V2 | 0.216 | 1.176 | Low demand | nan |
| C05 | C05 | 0.217 | 1.449 | Low demand | nan |
| C43-V1 | C43-V1 | 0.217 | 2.595 | Indirect | nan |
| T07-C02 | T07-C02 | 0.217 | 1.735 | Indirect | nan |
| C132 | C132 | 0.218 | 3.059 | Indirect | nan |
| T11A-C03 | T11A-C03 | 0.218 | 1.53 | Redundant | T11A-C02 |
| C07-V2 | C07-V2 | 0.22 | 1.368 | Low demand | nan |
| MC-A19 | MC-A19 | 0.222 | 1.554 | Indirect | nan |
| T03 | T03 | 0.222 | 1.574 | Indirect | nan |
| T11A-C02 | T11A-C02 | 0.222 | 1.486 | Low demand | nan |
| MT_L3 | L3 | 0.222 | 1.084 | Low demand | nan |
| C121-B | C121-B | 0.223 | 1.909 | Indirect | nan |
| C97-V2 | C97-V2 | 0.223 | 1.445 | Low demand | nan |
| C35 | C35 | 0.223 | 1.633 | Indirect | nan |
| C33 | C33 | 0.223 | 2.063 | Indirect | nan |
| MP-A04 | MP-A04 | 0.224 | 1.619 | Indirect | nan |
| C31 | C31 | 0.224 | 1.893 | Indirect | nan |
| C62 | C62 | 0.226 | 1.336 | Low demand | nan |
| C74 | C74 | 0.226 | 1.482 | Low demand | nan |
| C03 | C03 | 0.227 | 1.426 | Low demand | nan |
| T11A-C01 | T11A-C01 | 0.227 | 1.396 | Redundant | T11A |
| C123-V2 | C123-V2 | 0.228 | 1.58 | Redundant | C107 |
| LM-V05 | LM-V05 | 0.228 | 2.04 | Indirect | nan |
| MP-A02 | MP-A02 | 0.228 | 1.669 | Indirect | nan |
| C115 | C115 | 0.228 | 1.675 | Indirect | nan |
| C58-V1 | C58-V1 | 0.231 | 1.234 | Low demand | nan |
| C07-V1 | C07-V1 | 0.233 | 1.437 | Low demand | nan |
| T08 | T08 | 0.235 | 1.707 | Indirect | nan |
| C95 | C95 | 0.235 | 1.632 | Indirect | nan |
| C90 | C90 | 0.235 | 1.341 | Redundant | C92 |
| T04B-2 | T04B-2 | 0.235 | 1.303 | Low demand | nan |
| C42 | C42 | 0.236 | 1.711 | Indirect | nan |
| T11A | T11A | 0.236 | 1.313 | Low demand | nan |
| C97-V1 | C97-V1 | 0.237 | 1.424 | Low demand | nan |
| MP-T03 | MP-T03 | 0.237 | 1.222 | Low demand | nan |
| C43-V3 | C43-V3 | 0.237 | 1.636 | Redundant | C43-V2 |
| T09-B | T09-Belisario | 0.237 | 18436.515 | Indirect | nan |
| C107 | C107 | 0.238 | 1.597 | Indirect | nan |
| C34 | C34 | 0.239 | 1.33 | Low demand | nan |
| C43-V2 | C43-V2 | 0.239 | 1.616 | Indirect | nan |
| T06 | T06 | 0.239 | 1.238 | Low demand | nan |
| C113-V1 | C113-V1 | 0.24 | 1.513 | Indirect | nan |
| MP-A01 | MP-A01 | 0.241 | 1.429 | Low demand | nan |
| C80-V2 | C80-V2 | 0.242 | 1.434 | Redundant | C100 |
| T16B-C07-V | T16B-C07-Vistas | 0.244 | 1.261 | Redundant | T16B-C06 |
| C96-V2 | C96-V2 | 0.245 | 1.294 | Low demand | nan |
| C113-V2 | C113-V2 | 0.245 | 1.534 | Indirect | nan |
| T10 | T10 | 0.245 | 1.203 | Redundant | T10-C01 |
| T02 | T02 | 0.247 | 1.319 | Low demand | nan |
| C86 | C86 | 0.247 | 1.674 | Indirect | nan |
| T04B-4 | T04B-4 | 0.248 | 1.541 | Indirect | nan |
| T16B-C08-P | T16B-C08-Piedrera | 0.248 | 1.286 | Low demand | nan |
| C69 | C69 | 0.248 | 2.968 | Indirect | nan |
| T10-C02 | T10-C02 | 0.25 | 1.473 | Redundant | T10-C01 |
| C29-V2 | C29-V2 | 0.25 | 2.118 | Indirect | nan |
| C40 | C40 | 0.251 | 1.483 | Low demand | nan |
| T10-C01 | T10-C01 | 0.251 | 1.461 | Low demand | nan |
| C50-V2 | C50-V2 | 0.251 | 1.926 | Redundant | C50-V1 |
| C114-V1 | C114-V1 | 0.252 | 1.482 | Redundant | C114-V2 |
| ST_L4 | L4 | 0.252 | 1.456 | Low demand | nan |
| T10-C03 | T10-C03 | 0.252 | 1.387 | Low demand | nan |
| C36 | C36 | 0.255 | 1.451 | Low demand | nan |
| C50-V1 | C50-V1 | 0.255 | 1.862 | Indirect | nan |
| MT_L1 | L1 | 0.256 | 1.054 | Low demand | nan |
| C133-V2 | C133-V2 | 0.256 | 1.251 | Low demand | nan |
| C02 | C02 | 0.258 | 1.18 | Low demand | nan |
| T16B-C06 | T16B-C06 | 0.258 | 1.515 | Indirect | nan |
| C18 | C18 | 0.258 | 1.376 | Low demand | nan |
| T04A-C01 | T04A-C01 | 0.259 | 1.186 | Low demand | nan |
| LM-V04 | LM-V04 | 0.26 | 1.353 | Low demand | nan |
| MC-L1 | MC-L1 | 0.261 | 1.066 | Redundant | MC-L1E |
| C09 | C09 | 0.261 | 1.541 | Redundant | LM-C02 |
| LM-C02 | LM-C02 | 0.261 | 1.541 | Indirect | nan |
| MC-L1E | MC-L1E | 0.261 | 1.066 | Low demand | nan |
| C21 | C21 | 0.261 | 3.028 | Redundant | C16 |
| C100 | C100 | 0.262 | 1.359 | Low demand | nan |
| C01 | C01 | 0.263 | 1.324 | Low demand | nan |
| C13-V1 | C13-V1 | 0.263 | 1.69 | Indirect | nan |
| C16 | C16 | 0.263 | 2.996 | Indirect | nan |
| T08-C01 | T08-C01 | 0.265 | 1.664 | Indirect | nan |
| MP-A07 | MP-A07 | 0.265 | 2.21 | Indirect | nan |
| C32-V1 | C32-V1 | 0.267 | 1.904 | Redundant | C32-V2 |
| C49-V1 | C49-V1 | 0.267 | 2.043 | Redundant | C49-V2 |
| C94 | C94 | 0.268 | 1.984 | Redundant | C92 |
| MC-A21 | MC-A21 | 0.268 | 1.377 | Low demand | nan |
| C47-V2 | C47-V2 | 0.268 | 1.33 | Low demand | nan |
| C22 | C22 | 0.268 | 2.051 | Indirect | nan |
| C30 | C30 | 0.268 | 1.611 | Indirect | nan |
| MC-A20 | MC-A20 | 0.269 | 1.321 | Low demand | nan |
| C51-V2 | C51-V2 | 0.271 | 2.098 | Indirect | nan |
| C114-V2 | C114-V2 | 0.274 | 1.319 | Low demand | nan |
| C32-V2 | C32-V2 | 0.275 | 1.848 | Indirect | nan |
| C77 | C77 | 0.275 | 1.411 | Low demand | nan |
| C25 | C25 | 0.278 | 1.078 | Low demand | nan |
| MP-A03 | MP-A03 | 0.279 | 3.364 | Indirect | nan |
| C10 | C10 | 0.28 | 1.453 | Redundant | LM-C03 |
| LM-C03 | LM-C03 | 0.28 | 1.453 | Low demand | nan |
| C08 | C08 | 0.281 | 1.931 | Indirect | nan |
| C92 | C92 | 0.282 | 1.28 | Low demand | nan |
| T01 | T01 | 0.283 | 1.607 | Indirect | nan |
| C12-V1 | C12-V1 | 0.283 | 1.556 | Indirect | nan |
| C85 | C85 | 0.284 | 1.164 | Low demand | nan |
| C109 | C109 | 0.284 | 1.148 | Low demand | nan |
| C04 | C04 | 0.285 | 2.03 | Indirect | nan |
| C75 | C75 | 0.286 | 1.449 | Low demand | nan |
| C49-V2 | C49-V2 | 0.291 | 1.706 | Indirect | nan |
| C23 | C23 | 0.292 | 1.684 | Indirect | nan |
| MC-A08 | MC-A08 | 0.294 | 1.542 | Indirect | nan |
| C29-V1 | C29-V1 | 0.294 | 1.469 | Low demand | nan |
| C47-V1 | C47-V1 | 0.306 | 1.562 | Indirect | nan |
| C61 | C61 | 0.309 | 1.838 | Indirect | nan |
| C83 | C83 | 0.311 | 1.244 | Redundant | C48 |
| C13-V3 | C13-V3 | 0.312 | 3.023 | Indirect | nan |
| C13-V2 | C13-V2 | 0.312 | 1.683 | Indirect | nan |
| MC-A09 | MC-A09 | 0.315 | 1.557 | Indirect | nan |
| ST_L2 | L2 | 0.319 | 1.972 | Indirect | nan |
| T14B-C03-1 | T14B-C03-1 | 0.32 | 1.236 | Redundant | T14B-C03-2 |
| C44 | C44 | 0.327 | 1.783 | Indirect | nan |
| C78-V1 | C78-V1 | 0.334 | 2.138 | Indirect | nan |
| T16B-C07-C | T16B-C07-Ceibas | 0.339 | 1.581 | Indirect | nan |
| MC-A17 | MC-A17 | 0.344 | 2.144 | Indirect | nan |
| MC-A07 | MC-A07 | 0.346 | 2.638 | Indirect | nan |
| MC-A15 | MC-A15 | 0.355 | 1.614 | Indirect | nan |
| MC-A16 | MC-A16 | 0.362 | 4.812 | Indirect | nan |
| MC-A06 | MC-A06 | 0.362 | 1.693 | Indirect | nan |
| MC-A10 | MC-A10 | 0.362 | 1.691 | Indirect | nan |
| MC-A13 | MC-A13 | 0.365 | 2.165 | Indirect | nan |

## Modification Proposals

- **C01** (retire): Route has low demand-gain (f1=0.005, score=0.263) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C02** (retire): Route has low demand-gain (f1=0.005, score=0.258) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C03** (retire): Route has low demand-gain (f1=0.002, score=0.227) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C04** (shortcut): Route detour_ratio=2.03 > 1.5. Current route_km=12.7km; estimated shortcut=6.9km (straight_line_km=6.3km x 1.1).
  - Current score: 0.285 -> Proposed score: 0.333
- **C05** (retire): Route has low demand-gain (f1=0.003, score=0.217) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C06** (shortcut): Route detour_ratio=1.95 > 1.5. Current route_km=23.8km; estimated shortcut=13.4km (straight_line_km=12.2km x 1.1).
  - Current score: 0.193 -> Proposed score: 0.280
- **C07-V1** (retire): Route has low demand-gain (f1=0.003, score=0.233) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C07-V2** (retire): Route has low demand-gain (f1=0.002, score=0.220) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C08** (shortcut): Route detour_ratio=1.93 > 1.5. Current route_km=13.2km; estimated shortcut=7.5km (straight_line_km=6.8km x 1.1).
  - Current score: 0.281 -> Proposed score: 0.329
- **C09** (merge): Route overlaps 100.0% of served AGEBs with LM-C02 (Jaccard=1.00). Consolidation improves frequency without expanding coverage.
  - Paired with: LM-C02
- **C10** (merge): Route overlaps 100.0% of served AGEBs with LM-C03 (Jaccard=1.00). Consolidation improves frequency without expanding coverage.
  - Paired with: LM-C03
- **C100** (retire): Route has low demand-gain (f1=0.020, score=0.262) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C101** (shortcut): Route detour_ratio=1.61 > 1.5. Current route_km=25.1km; estimated shortcut=17.1km (straight_line_km=15.6km x 1.1).
  - Current score: 0.179 -> Proposed score: 0.245
- **C102** (shortcut): Route detour_ratio=1.86 > 1.5. Current route_km=47.6km; estimated shortcut=28.1km (straight_line_km=25.5km x 1.1).
  - Current score: 0.151 -> Proposed score: 0.168
- **C103** (shortcut): Route detour_ratio=2.53 > 1.5. Current route_km=39.3km; estimated shortcut=17.1km (straight_line_km=15.5km x 1.1).
  - Current score: 0.166 -> Proposed score: 0.273
- **C104** (shortcut): Route detour_ratio=27561.84 > 1.5. Current route_km=27.6km; estimated shortcut=0.0km (straight_line_km=0.0km x 1.1).
  - Current score: 0.156 -> Proposed score: 0.385
- **C105** (shortcut): Route detour_ratio=2.53 > 1.5. Current route_km=26.7km; estimated shortcut=11.6km (straight_line_km=10.6km x 1.1).
  - Current score: 0.166 -> Proposed score: 0.292
- **C106** (shortcut): Route detour_ratio=2.10 > 1.5. Current route_km=24.5km; estimated shortcut=12.8km (straight_line_km=11.7km x 1.1).
  - Current score: 0.199 -> Proposed score: 0.296
- **C107** (shortcut): Route detour_ratio=1.60 > 1.5. Current route_km=18.7km; estimated shortcut=12.9km (straight_line_km=11.7km x 1.1).
  - Current score: 0.238 -> Proposed score: 0.286
- **C108** (shortcut): Route detour_ratio=82767.58 > 1.5. Current route_km=82.8km; estimated shortcut=0.0km (straight_line_km=0.0km x 1.1).
  - Current score: 0.138 -> Proposed score: 0.388
- **C109** (retire): Route has low demand-gain (f1=0.002, score=0.284) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C110-V1** (shortcut): Route detour_ratio=1.55 > 1.5. Current route_km=21.8km; estimated shortcut=15.5km (straight_line_km=14.1km x 1.1).
  - Current score: 0.205 -> Proposed score: 0.258
- **C110-V2** (merge): Route overlaps 67.7% of served AGEBs with C109 (Jaccard=0.68). Consolidation improves frequency without expanding coverage.
  - Paired with: C109
- **C111-V1** (merge): Route overlaps 62.0% of served AGEBs with C111-V3 (Jaccard=0.62). Consolidation improves frequency without expanding coverage.
  - Paired with: C111-V3
- **C111-V2** (retire): Route has low demand-gain (f1=0.034, score=0.216) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C111-V3** (merge): Route overlaps 69.4% of served AGEBs with C67-V1 (Jaccard=0.69). Consolidation improves frequency without expanding coverage.
  - Paired with: C67-V1
- **C112** (retire): Route has low demand-gain (f1=0.062, score=0.199) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C113-V1** (shortcut): Route detour_ratio=1.51 > 1.5. Current route_km=19.9km; estimated shortcut=14.5km (straight_line_km=13.2km x 1.1).
  - Current score: 0.240 -> Proposed score: 0.285
- **C113-V2** (shortcut): Route detour_ratio=1.53 > 1.5. Current route_km=20.2km; estimated shortcut=14.5km (straight_line_km=13.2km x 1.1).
  - Current score: 0.245 -> Proposed score: 0.293
- **C114-V1** (merge): Route overlaps 63.0% of served AGEBs with C114-V2 (Jaccard=0.63). Consolidation improves frequency without expanding coverage.
  - Paired with: C114-V2
- **C114-V2** (retire): Route has low demand-gain (f1=0.023, score=0.274) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C115** (shortcut): Route detour_ratio=1.68 > 1.5. Current route_km=21.4km; estimated shortcut=14.1km (straight_line_km=12.8km x 1.1).
  - Current score: 0.228 -> Proposed score: 0.290
- **C116-A** (shortcut): Route detour_ratio=1.74 > 1.5. Current route_km=31.3km; estimated shortcut=19.8km (straight_line_km=18.0km x 1.1).
  - Current score: 0.203 -> Proposed score: 0.288
- **C116-B** (shortcut): Route detour_ratio=1.67 > 1.5. Current route_km=30.0km; estimated shortcut=19.8km (straight_line_km=18.0km x 1.1).
  - Current score: 0.175 -> Proposed score: 0.261
- **C117** (shortcut): Route detour_ratio=1.54 > 1.5. Current route_km=30.6km; estimated shortcut=21.9km (straight_line_km=19.9km x 1.1).
  - Current score: 0.155 -> Proposed score: 0.223
- **C118** (retire): Route has low demand-gain (f1=0.002, score=0.213) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C120** (retire): Route has low demand-gain (f1=0.001, score=0.145) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C121-B** (shortcut): Route detour_ratio=1.91 > 1.5. Current route_km=19.8km; estimated shortcut=11.4km (straight_line_km=10.4km x 1.1).
  - Current score: 0.223 -> Proposed score: 0.293
- **C122** (shortcut): Route detour_ratio=2.24 > 1.5. Current route_km=24.3km; estimated shortcut=11.9km (straight_line_km=10.9km x 1.1).
  - Current score: 0.193 -> Proposed score: 0.296
- **C123-V1** (retire): Route has low demand-gain (f1=0.003, score=0.180) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C123-V2** (merge): Route overlaps 61.2% of served AGEBs with C107 (Jaccard=0.61). Consolidation improves frequency without expanding coverage.
  - Paired with: C107
- **C124** (shortcut): Route detour_ratio=1.64 > 1.5. Current route_km=30.2km; estimated shortcut=20.2km (straight_line_km=18.4km x 1.1).
  - Current score: 0.140 -> Proposed score: 0.222
- **C125-V1** (shortcut): Route detour_ratio=1.62 > 1.5. Current route_km=39.6km; estimated shortcut=26.9km (straight_line_km=24.4km x 1.1).
  - Current score: 0.143 -> Proposed score: 0.169
- **C125-V2** (merge): Route overlaps 71.2% of served AGEBs with C125-V1 (Jaccard=0.71). Consolidation improves frequency without expanding coverage.
  - Paired with: C125-V1
- **C126-V1** (merge): Route overlaps 100.0% of served AGEBs with LM-C01 (Jaccard=1.00). Consolidation improves frequency without expanding coverage.
  - Paired with: LM-C01
- **C127-V1** (retire): Route has low demand-gain (f1=0.002, score=0.149) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C128** (shortcut): Route detour_ratio=1.69 > 1.5. Current route_km=35.0km; estimated shortcut=22.8km (straight_line_km=20.8km x 1.1).
  - Current score: 0.137 -> Proposed score: 0.196
- **C128A-V1** (retire): Route has low demand-gain (f1=0.007, score=0.182) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C129** (merge): Route overlaps 61.0% of served AGEBs with C128A-V1 (Jaccard=0.61). Consolidation improves frequency without expanding coverage.
  - Paired with: C128A-V1
- **C12-V1** (shortcut): Route detour_ratio=1.56 > 1.5. Current route_km=13.5km; estimated shortcut=9.6km (straight_line_km=8.7km x 1.1).
  - Current score: 0.283 -> Proposed score: 0.316
- **C130** (merge): Route overlaps 86.3% of served AGEBs with C125-V1 (Jaccard=0.86). Consolidation improves frequency without expanding coverage.
  - Paired with: C125-V1
- **C132** (shortcut): Route detour_ratio=3.06 > 1.5. Current route_km=24.3km; estimated shortcut=8.8km (straight_line_km=8.0km x 1.1).
  - Current score: 0.218 -> Proposed score: 0.348
- **C133-V1** (shortcut): Route detour_ratio=27293.67 > 1.5. Current route_km=27.3km; estimated shortcut=0.0km (straight_line_km=0.0km x 1.1).
  - Current score: 0.160 -> Proposed score: 0.388
- **C133-V2** (retire): Route has low demand-gain (f1=0.006, score=0.256) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C134** (retire): Route has low demand-gain (f1=0.002, score=0.209) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C135** (shortcut): Route detour_ratio=2.24 > 1.5. Current route_km=34.8km; estimated shortcut=17.1km (straight_line_km=15.5km x 1.1).
  - Current score: 0.139 -> Proposed score: 0.247
- **C136** (shortcut): Route detour_ratio=1.93 > 1.5. Current route_km=35.4km; estimated shortcut=20.2km (straight_line_km=18.4km x 1.1).
  - Current score: 0.144 -> Proposed score: 0.225
- **C138** (shortcut): Route detour_ratio=33990.50 > 1.5. Current route_km=34.0km; estimated shortcut=0.0km (straight_line_km=0.0km x 1.1).
  - Current score: 0.213 -> Proposed score: 0.463
- **C13-V1** (shortcut): Route detour_ratio=1.69 > 1.5. Current route_km=16.6km; estimated shortcut=10.8km (straight_line_km=9.8km x 1.1).
  - Current score: 0.263 -> Proposed score: 0.311
- **C13-V2** (shortcut): Route detour_ratio=1.68 > 1.5. Current route_km=9.6km; estimated shortcut=6.3km (straight_line_km=5.7km x 1.1).
  - Current score: 0.312 -> Proposed score: 0.340
- **C13-V3** (shortcut): Route detour_ratio=3.02 > 1.5. Current route_km=10.2km; estimated shortcut=3.7km (straight_line_km=3.4km x 1.1).
  - Current score: 0.312 -> Proposed score: 0.366
- **C14-V1** (shortcut): Route detour_ratio=1.51 > 1.5. Current route_km=36.8km; estimated shortcut=26.8km (straight_line_km=24.3km x 1.1).
  - Current score: 0.138 -> Proposed score: 0.165
- **C14-V2** (shortcut): Route detour_ratio=1.59 > 1.5. Current route_km=24.6km; estimated shortcut=17.0km (straight_line_km=15.4km x 1.1).
  - Current score: 0.185 -> Proposed score: 0.249
- **C15** (retire): Route has low demand-gain (f1=0.017, score=0.156) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C16** (shortcut): Route detour_ratio=3.00 > 1.5. Current route_km=15.4km; estimated shortcut=5.6km (straight_line_km=5.1km x 1.1).
  - Current score: 0.263 -> Proposed score: 0.344
- **C17** (shortcut): Route detour_ratio=2.06 > 1.5. Current route_km=25.9km; estimated shortcut=13.8km (straight_line_km=12.6km x 1.1).
  - Current score: 0.175 -> Proposed score: 0.276
- **C18** (retire): Route has low demand-gain (f1=0.002, score=0.258) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C19** (shortcut): Route detour_ratio=1.76 > 1.5. Current route_km=25.0km; estimated shortcut=15.6km (straight_line_km=14.1km x 1.1).
  - Current score: 0.183 -> Proposed score: 0.261
- **C20-V1** (shortcut): Route detour_ratio=1.67 > 1.5. Current route_km=23.4km; estimated shortcut=15.4km (straight_line_km=14.0km x 1.1).
  - Current score: 0.197 -> Proposed score: 0.263
- **C21** (merge): Route overlaps 97.7% of served AGEBs with C16 (Jaccard=0.98). Consolidation improves frequency without expanding coverage.
  - Paired with: C16
- **C22** (shortcut): Route detour_ratio=2.05 > 1.5. Current route_km=15.5km; estimated shortcut=8.3km (straight_line_km=7.5km x 1.1).
  - Current score: 0.268 -> Proposed score: 0.328
- **C23** (shortcut): Route detour_ratio=1.68 > 1.5. Current route_km=11.9km; estimated shortcut=7.8km (straight_line_km=7.1km x 1.1).
  - Current score: 0.292 -> Proposed score: 0.326
- **C25** (retire): Route has low demand-gain (f1=0.005, score=0.278) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C26** (retire): Route has low demand-gain (f1=0.001, score=0.204) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C27** (shortcut): Route detour_ratio=2.06 > 1.5. Current route_km=27.8km; estimated shortcut=14.8km (straight_line_km=13.5km x 1.1).
  - Current score: 0.159 -> Proposed score: 0.267
- **C28** (shortcut): Route detour_ratio=1.64 > 1.5. Current route_km=24.7km; estimated shortcut=16.6km (straight_line_km=15.1km x 1.1).
  - Current score: 0.185 -> Proposed score: 0.253
- **C29-V1** (retire): Route has low demand-gain (f1=0.001, score=0.294) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C29-V2** (shortcut): Route detour_ratio=2.12 > 1.5. Current route_km=18.9km; estimated shortcut=9.8km (straight_line_km=8.9km x 1.1).
  - Current score: 0.250 -> Proposed score: 0.326
- **C30** (shortcut): Route detour_ratio=1.61 > 1.5. Current route_km=14.3km; estimated shortcut=9.8km (straight_line_km=8.9km x 1.1).
  - Current score: 0.268 -> Proposed score: 0.306
- **C31** (shortcut): Route detour_ratio=1.89 > 1.5. Current route_km=20.0km; estimated shortcut=11.6km (straight_line_km=10.5km x 1.1).
  - Current score: 0.224 -> Proposed score: 0.294
- **C32-V1** (merge): Route overlaps 72.7% of served AGEBs with C32-V2 (Jaccard=0.73). Consolidation improves frequency without expanding coverage.
  - Paired with: C32-V2
- **C32-V2** (shortcut): Route detour_ratio=1.85 > 1.5. Current route_km=14.6km; estimated shortcut=8.7km (straight_line_km=7.9km x 1.1).
  - Current score: 0.275 -> Proposed score: 0.324
- **C33** (shortcut): Route detour_ratio=2.06 > 1.5. Current route_km=20.7km; estimated shortcut=11.1km (straight_line_km=10.1km x 1.1).
  - Current score: 0.223 -> Proposed score: 0.304
- **C34** (retire): Route has low demand-gain (f1=0.002, score=0.239) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C35** (shortcut): Route detour_ratio=1.63 > 1.5. Current route_km=21.4km; estimated shortcut=14.4km (straight_line_km=13.1km x 1.1).
  - Current score: 0.223 -> Proposed score: 0.281
- **C36** (retire): Route has low demand-gain (f1=0.007, score=0.255) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C37-V1** (merge): Route overlaps 80.7% of served AGEBs with C37-V2 (Jaccard=0.81). Consolidation improves frequency without expanding coverage.
  - Paired with: C37-V2
- **C37-V2** (shortcut): Route detour_ratio=1.99 > 1.5. Current route_km=23.4km; estimated shortcut=12.9km (straight_line_km=11.8km x 1.1).
  - Current score: 0.202 -> Proposed score: 0.290
- **C38-V1** (merge): Route overlaps 78.8% of served AGEBs with C39-V1 (Jaccard=0.79). Consolidation improves frequency without expanding coverage.
  - Paired with: C39-V1
- **C38-V2** (merge): Route overlaps 72.1% of served AGEBs with C39-V1 (Jaccard=0.72). Consolidation improves frequency without expanding coverage.
  - Paired with: C39-V1
- **C39-V1** (retire): Route has low demand-gain (f1=0.003, score=0.203) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C39-V2** (merge): Route overlaps 93.4% of served AGEBs with C39-V1 (Jaccard=0.93). Consolidation improves frequency without expanding coverage.
  - Paired with: C39-V1
- **C40** (retire): Route has low demand-gain (f1=0.018, score=0.251) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C41-V1** (shortcut): Route detour_ratio=1.72 > 1.5. Current route_km=28.1km; estimated shortcut=18.0km (straight_line_km=16.3km x 1.1).
  - Current score: 0.164 -> Proposed score: 0.248
- **C41-V2** (shortcut): Route detour_ratio=1.58 > 1.5. Current route_km=25.8km; estimated shortcut=18.0km (straight_line_km=16.3km x 1.1).
  - Current score: 0.202 -> Proposed score: 0.267
- **C42** (shortcut): Route detour_ratio=1.71 > 1.5. Current route_km=18.1km; estimated shortcut=11.6km (straight_line_km=10.6km x 1.1).
  - Current score: 0.236 -> Proposed score: 0.290
- **C43-V1** (shortcut): Route detour_ratio=2.60 > 1.5. Current route_km=20.2km; estimated shortcut=8.6km (straight_line_km=7.8km x 1.1).
  - Current score: 0.217 -> Proposed score: 0.314
- **C43-V2** (shortcut): Route detour_ratio=1.62 > 1.5. Current route_km=18.2km; estimated shortcut=12.4km (straight_line_km=11.2km x 1.1).
  - Current score: 0.239 -> Proposed score: 0.287
- **C43-V3** (merge): Route overlaps 74.5% of served AGEBs with C43-V2 (Jaccard=0.74). Consolidation improves frequency without expanding coverage.
  - Paired with: C43-V2
- **C44** (shortcut): Route detour_ratio=1.78 > 1.5. Current route_km=8.2km; estimated shortcut=5.1km (straight_line_km=4.6km x 1.1).
  - Current score: 0.327 -> Proposed score: 0.353
- **C46-V1** (retire): Route has low demand-gain (f1=0.002, score=0.190) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C46-V2** (shortcut): Route detour_ratio=1.55 > 1.5. Current route_km=28.3km; estimated shortcut=20.0km (straight_line_km=18.2km x 1.1).
  - Current score: 0.152 -> Proposed score: 0.221
- **C47-V1** (shortcut): Route detour_ratio=1.56 > 1.5. Current route_km=13.3km; estimated shortcut=9.3km (straight_line_km=8.5km x 1.1).
  - Current score: 0.306 -> Proposed score: 0.339
- **C47-V2** (retire): Route has low demand-gain (f1=0.018, score=0.268) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C49-V1** (merge): Route overlaps 90.3% of served AGEBs with C49-V2 (Jaccard=0.90). Consolidation improves frequency without expanding coverage.
  - Paired with: C49-V2
- **C49-V2** (shortcut): Route detour_ratio=1.71 > 1.5. Current route_km=11.8km; estimated shortcut=7.6km (straight_line_km=6.9km x 1.1).
  - Current score: 0.291 -> Proposed score: 0.326
- **C50-V1** (shortcut): Route detour_ratio=1.86 > 1.5. Current route_km=20.4km; estimated shortcut=12.1km (straight_line_km=11.0km x 1.1).
  - Current score: 0.255 -> Proposed score: 0.325
- **C50-V2** (merge): Route overlaps 86.8% of served AGEBs with C50-V1 (Jaccard=0.87). Consolidation improves frequency without expanding coverage.
  - Paired with: C50-V1
- **C51-V2** (shortcut): Route detour_ratio=2.10 > 1.5. Current route_km=14.5km; estimated shortcut=7.6km (straight_line_km=6.9km x 1.1).
  - Current score: 0.271 -> Proposed score: 0.328
- **C53** (shortcut): Route detour_ratio=1.68 > 1.5. Current route_km=35.8km; estimated shortcut=23.4km (straight_line_km=21.3km x 1.1).
  - Current score: 0.140 -> Proposed score: 0.195
- **C54** (retire): Route has low demand-gain (f1=0.002, score=0.146) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C58-V1** (retire): Route has low demand-gain (f1=0.014, score=0.231) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C58-V2** (shortcut): Route detour_ratio=1.61 > 1.5. Current route_km=26.3km; estimated shortcut=18.0km (straight_line_km=16.4km x 1.1).
  - Current score: 0.196 -> Proposed score: 0.265
- **C60** (merge): Route overlaps 67.3% of served AGEBs with C58-V1 (Jaccard=0.67). Consolidation improves frequency without expanding coverage.
  - Paired with: C58-V1
- **C61** (shortcut): Route detour_ratio=1.84 > 1.5. Current route_km=11.6km; estimated shortcut=7.0km (straight_line_km=6.3km x 1.1).
  - Current score: 0.309 -> Proposed score: 0.348
- **C62** (retire): Route has low demand-gain (f1=0.002, score=0.226) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C64** (retire): Route has low demand-gain (f1=0.005, score=0.144) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C65** (retire): Route has low demand-gain (f1=0.002, score=0.164) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C66-V1** (retire): Route has low demand-gain (f1=0.001, score=0.202) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C66-V2** (shortcut): Route detour_ratio=1.64 > 1.5. Current route_km=24.3km; estimated shortcut=16.3km (straight_line_km=14.8km x 1.1).
  - Current score: 0.190 -> Proposed score: 0.256
- **C67-V1** (shortcut): Route detour_ratio=1.66 > 1.5. Current route_km=32.3km; estimated shortcut=21.5km (straight_line_km=19.5km x 1.1).
  - Current score: 0.154 -> Proposed score: 0.225
- **C67-V2** (shortcut): Route detour_ratio=1.63 > 1.5. Current route_km=31.8km; estimated shortcut=21.5km (straight_line_km=19.5km x 1.1).
  - Current score: 0.173 -> Proposed score: 0.244
- **C69** (shortcut): Route detour_ratio=2.97 > 1.5. Current route_km=17.8km; estimated shortcut=6.6km (straight_line_km=6.0km x 1.1).
  - Current score: 0.248 -> Proposed score: 0.342
- **C70** (shortcut): Route detour_ratio=2.60 > 1.5. Current route_km=22.5km; estimated shortcut=9.5km (straight_line_km=8.6km x 1.1).
  - Current score: 0.201 -> Proposed score: 0.310
- **C71** (shortcut): Route detour_ratio=1.65 > 1.5. Current route_km=28.2km; estimated shortcut=18.8km (straight_line_km=17.1km x 1.1).
  - Current score: 0.153 -> Proposed score: 0.231
- **C73** (shortcut): Route detour_ratio=4.37 > 1.5. Current route_km=21.2km; estimated shortcut=5.3km (straight_line_km=4.9km x 1.1).
  - Current score: 0.211 -> Proposed score: 0.343
- **C74** (retire): Route has low demand-gain (f1=0.001, score=0.226) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C75** (retire): Route has low demand-gain (f1=0.001, score=0.286) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C76-V1** (merge): Route overlaps 86.5% of served AGEBs with C76-V2 (Jaccard=0.86). Consolidation improves frequency without expanding coverage.
  - Paired with: C76-V2
- **C76-V2** (retire): Route has low demand-gain (f1=0.025, score=0.214) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C77** (retire): Route has low demand-gain (f1=0.041, score=0.275) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C78-V1** (shortcut): Route detour_ratio=2.14 > 1.5. Current route_km=17.1km; estimated shortcut=8.8km (straight_line_km=8.0km x 1.1).
  - Current score: 0.334 -> Proposed score: 0.403
- **C79** (shortcut): Route detour_ratio=1.74 > 1.5. Current route_km=22.3km; estimated shortcut=14.1km (straight_line_km=12.8km x 1.1).
  - Current score: 0.202 -> Proposed score: 0.271
- **C80-V1** (shortcut): Route detour_ratio=1.91 > 1.5. Current route_km=28.1km; estimated shortcut=16.2km (straight_line_km=14.7km x 1.1).
  - Current score: 0.167 -> Proposed score: 0.266
- **C80-V2** (merge): Route overlaps 100.0% of served AGEBs with C100 (Jaccard=1.00). Consolidation improves frequency without expanding coverage.
  - Paired with: C100
- **C83** (merge): Route overlaps 72.0% of served AGEBs with C48 (Jaccard=0.72). Consolidation improves frequency without expanding coverage.
  - Paired with: C48
- **C85** (retire): Route has low demand-gain (f1=0.002, score=0.284) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C86** (shortcut): Route detour_ratio=1.67 > 1.5. Current route_km=21.7km; estimated shortcut=14.3km (straight_line_km=13.0km x 1.1).
  - Current score: 0.247 -> Proposed score: 0.310
- **C88-V2** (retire): Route has low demand-gain (f1=0.005, score=0.215) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C89** (merge): Route overlaps 82.8% of served AGEBs with C88-V2 (Jaccard=0.83). Consolidation improves frequency without expanding coverage.
  - Paired with: C88-V2
- **C90** (merge): Route overlaps 100.0% of served AGEBs with C92 (Jaccard=1.00). Consolidation improves frequency without expanding coverage.
  - Paired with: C92
- **C92** (retire): Route has low demand-gain (f1=0.044, score=0.282) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C93** (shortcut): Route detour_ratio=2.42 > 1.5. Current route_km=33.1km; estimated shortcut=15.1km (straight_line_km=13.7km x 1.1).
  - Current score: 0.140 -> Proposed score: 0.264
- **C94** (merge): Route overlaps 100.0% of served AGEBs with C92 (Jaccard=1.00). Consolidation improves frequency without expanding coverage.
  - Paired with: C92
- **C95** (shortcut): Route detour_ratio=1.63 > 1.5. Current route_km=18.6km; estimated shortcut=12.6km (straight_line_km=11.4km x 1.1).
  - Current score: 0.235 -> Proposed score: 0.286
- **C96-V2** (retire): Route has low demand-gain (f1=0.002, score=0.245) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C97-V1** (retire): Route has low demand-gain (f1=0.022, score=0.237) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C97-V2** (retire): Route has low demand-gain (f1=0.019, score=0.223) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C99** (shortcut): Route detour_ratio=2.23 > 1.5. Current route_km=25.1km; estimated shortcut=12.4km (straight_line_km=11.3km x 1.1).
  - Current score: 0.194 -> Proposed score: 0.300
- **T01** (shortcut): Route detour_ratio=1.61 > 1.5. Current route_km=12.7km; estimated shortcut=8.7km (straight_line_km=7.9km x 1.1).
  - Current score: 0.283 -> Proposed score: 0.316
- **T02** (retire): Route has low demand-gain (f1=0.001, score=0.247) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T03** (shortcut): Route detour_ratio=1.57 > 1.5. Current route_km=23.0km; estimated shortcut=16.1km (straight_line_km=14.6km x 1.1).
  - Current score: 0.222 -> Proposed score: 0.280
- **T04A-1** (retire): Route has low demand-gain (f1=0.002, score=0.135) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T04A-2** (shortcut): Route detour_ratio=1.60 > 1.5. Current route_km=35.9km; estimated shortcut=24.7km (straight_line_km=22.5km x 1.1).
  - Current score: 0.137 -> Proposed score: 0.181
- **T04A-C01** (retire): Route has low demand-gain (f1=0.017, score=0.259) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T04B-1** (retire): Route has low demand-gain (f1=0.010, score=0.182) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T04B-2** (retire): Route has low demand-gain (f1=0.002, score=0.235) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T04B-3** (retire): Route has low demand-gain (f1=0.001, score=0.215) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T04B-4** (shortcut): Route detour_ratio=1.54 > 1.5. Current route_km=15.6km; estimated shortcut=11.1km (straight_line_km=10.1km x 1.1).
  - Current score: 0.248 -> Proposed score: 0.285
- **T06** (retire): Route has low demand-gain (f1=0.002, score=0.239) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T07** (shortcut): Route detour_ratio=1.65 > 1.5. Current route_km=29.3km; estimated shortcut=19.6km (straight_line_km=17.8km x 1.1).
  - Current score: 0.146 -> Proposed score: 0.227
- **T07-C02** (shortcut): Route detour_ratio=1.74 > 1.5. Current route_km=23.0km; estimated shortcut=14.6km (straight_line_km=13.3km x 1.1).
  - Current score: 0.217 -> Proposed score: 0.287
- **T08** (shortcut): Route detour_ratio=1.71 > 1.5. Current route_km=18.3km; estimated shortcut=11.8km (straight_line_km=10.7km x 1.1).
  - Current score: 0.235 -> Proposed score: 0.289
- **T08-C01** (shortcut): Route detour_ratio=1.66 > 1.5. Current route_km=14.4km; estimated shortcut=9.5km (straight_line_km=8.7km x 1.1).
  - Current score: 0.265 -> Proposed score: 0.305
- **T09-B** (shortcut): Route detour_ratio=18436.51 > 1.5. Current route_km=18.4km; estimated shortcut=0.0km (straight_line_km=0.0km x 1.1).
  - Current score: 0.237 -> Proposed score: 0.391
- **T09-O** (shortcut): Route detour_ratio=26442.58 > 1.5. Current route_km=26.4km; estimated shortcut=0.0km (straight_line_km=0.0km x 1.1).
  - Current score: 0.170 -> Proposed score: 0.390
- **T10** (merge): Route overlaps 66.7% of served AGEBs with T10-C01 (Jaccard=0.67). Consolidation improves frequency without expanding coverage.
  - Paired with: T10-C01
- **T10-C01** (retire): Route has low demand-gain (f1=0.001, score=0.251) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T10-C02** (merge): Route overlaps 73.2% of served AGEBs with T10-C01 (Jaccard=0.73). Consolidation improves frequency without expanding coverage.
  - Paired with: T10-C01
- **T10-C03** (retire): Route has low demand-gain (f1=0.011, score=0.252) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T11A** (retire): Route has low demand-gain (f1=0.001, score=0.236) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T11A-C01** (merge): Route overlaps 75.8% of served AGEBs with T11A (Jaccard=0.76). Consolidation improves frequency without expanding coverage.
  - Paired with: T11A
- **T11A-C02** (retire): Route has low demand-gain (f1=0.001, score=0.222) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T11A-C03** (merge): Route overlaps 64.9% of served AGEBs with T11A-C02 (Jaccard=0.65). Consolidation improves frequency without expanding coverage.
  - Paired with: T11A-C02
- **T11B** (retire): Route has low demand-gain (f1=0.002, score=0.136) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T13A** (retire): Route has low demand-gain (f1=0.016, score=0.137) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T14B** (shortcut): Route detour_ratio=102.08 > 1.5. Current route_km=1691.7km; estimated shortcut=18.2km (straight_line_km=16.6km x 1.1).
  - Current score: 0.170 -> Proposed score: 0.268
- **T14B-C03-1** (merge): Route overlaps 70.0% of served AGEBs with T14B-C03-2 (Jaccard=0.70). Consolidation improves frequency without expanding coverage.
  - Paired with: T14B-C03-2
- **T15** (shortcut): Route detour_ratio=1.74 > 1.5. Current route_km=28.4km; estimated shortcut=18.0km (straight_line_km=16.4km x 1.1).
  - Current score: 0.159 -> Proposed score: 0.246
- **T16B** (retire): Route has low demand-gain (f1=0.016, score=0.177) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T16B-C06** (shortcut): Route detour_ratio=1.51 > 1.5. Current route_km=20.8km; estimated shortcut=15.1km (straight_line_km=13.7km x 1.1).
  - Current score: 0.258 -> Proposed score: 0.305
- **T16B-C07-C** (shortcut): Route detour_ratio=1.58 > 1.5. Current route_km=3.4km; estimated shortcut=2.3km (straight_line_km=2.1km x 1.1).
  - Current score: 0.339 -> Proposed score: 0.348
- **T16B-C07-V** (merge): Route overlaps 61.7% of served AGEBs with T16B-C06 (Jaccard=0.62). Consolidation improves frequency without expanding coverage.
  - Paired with: T16B-C06
- **T16B-C08-P** (retire): Route has low demand-gain (f1=0.031, score=0.248) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T17** (retire): Route has low demand-gain (f1=0.001, score=0.168) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T17-C01** (shortcut): Route detour_ratio=1.68 > 1.5. Current route_km=40.2km; estimated shortcut=26.3km (straight_line_km=23.9km x 1.1).
  - Current score: 0.139 -> Proposed score: 0.170
- **T18-1-L** (merge): Route overlaps 94.1% of served AGEBs with T18-2-L (Jaccard=0.94). Consolidation improves frequency without expanding coverage.
  - Paired with: T18-2-L
- **T18-1-T** (merge): Route overlaps 79.7% of served AGEBs with T18-2-L (Jaccard=0.80). Consolidation improves frequency without expanding coverage.
  - Paired with: T18-2-L
- **T18-2-L** (shortcut): Route detour_ratio=26887.11 > 1.5. Current route_km=26.9km; estimated shortcut=0.0km (straight_line_km=0.0km x 1.1).
  - Current score: 0.165 -> Proposed score: 0.389
- **T18-2-T** (merge): Route overlaps 84.9% of served AGEBs with T18-2-L (Jaccard=0.85). Consolidation improves frequency without expanding coverage.
  - Paired with: T18-2-L
- **MC-A06** (shortcut): Route detour_ratio=1.69 > 1.5. Current route_km=4.4km; estimated shortcut=2.8km (straight_line_km=2.6km x 1.1).
  - Current score: 0.362 -> Proposed score: 0.375
- **MC-A07** (shortcut): Route detour_ratio=2.64 > 1.5. Current route_km=4.2km; estimated shortcut=1.7km (straight_line_km=1.6km x 1.1).
  - Current score: 0.346 -> Proposed score: 0.366
- **MC-A08** (shortcut): Route detour_ratio=1.54 > 1.5. Current route_km=11.8km; estimated shortcut=8.4km (straight_line_km=7.6km x 1.1).
  - Current score: 0.294 -> Proposed score: 0.322
- **MC-A09** (shortcut): Route detour_ratio=1.56 > 1.5. Current route_km=10.8km; estimated shortcut=7.7km (straight_line_km=7.0km x 1.1).
  - Current score: 0.315 -> Proposed score: 0.341
- **MC-A10** (shortcut): Route detour_ratio=1.69 > 1.5. Current route_km=4.6km; estimated shortcut=3.0km (straight_line_km=2.7km x 1.1).
  - Current score: 0.362 -> Proposed score: 0.376
- **MC-A13** (shortcut): Route detour_ratio=2.17 > 1.5. Current route_km=3.4km; estimated shortcut=1.7km (straight_line_km=1.6km x 1.1).
  - Current score: 0.365 -> Proposed score: 0.379
- **MC-A15** (shortcut): Route detour_ratio=1.61 > 1.5. Current route_km=4.6km; estimated shortcut=3.1km (straight_line_km=2.9km x 1.1).
  - Current score: 0.355 -> Proposed score: 0.367
- **MC-A16** (shortcut): Route detour_ratio=4.81 > 1.5. Current route_km=5.0km; estimated shortcut=1.1km (straight_line_km=1.0km x 1.1).
  - Current score: 0.362 -> Proposed score: 0.394
- **MC-A17** (shortcut): Route detour_ratio=2.14 > 1.5. Current route_km=4.0km; estimated shortcut=2.1km (straight_line_km=1.9km x 1.1).
  - Current score: 0.344 -> Proposed score: 0.360
- **MC-A19** (shortcut): Route detour_ratio=1.55 > 1.5. Current route_km=20.3km; estimated shortcut=14.4km (straight_line_km=13.1km x 1.1).
  - Current score: 0.222 -> Proposed score: 0.271
- **MC-A20** (retire): Route has low demand-gain (f1=0.005, score=0.269) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **MC-A21** (retire): Route has low demand-gain (f1=0.025, score=0.268) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **MP-A01** (retire): Route has low demand-gain (f1=0.001, score=0.241) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **MP-A02** (shortcut): Route detour_ratio=1.67 > 1.5. Current route_km=19.3km; estimated shortcut=12.7km (straight_line_km=11.6km x 1.1).
  - Current score: 0.228 -> Proposed score: 0.283
- **MP-A03** (shortcut): Route detour_ratio=3.36 > 1.5. Current route_km=13.1km; estimated shortcut=4.3km (straight_line_km=3.9km x 1.1).
  - Current score: 0.279 -> Proposed score: 0.352
- **MP-A04** (shortcut): Route detour_ratio=1.62 > 1.5. Current route_km=18.4km; estimated shortcut=12.5km (straight_line_km=11.4km x 1.1).
  - Current score: 0.224 -> Proposed score: 0.273
- **MP-A05-1** (shortcut): Route detour_ratio=47097.90 > 1.5. Current route_km=47.1km; estimated shortcut=0.0km (straight_line_km=0.0km x 1.1).
  - Current score: 0.148 -> Proposed score: 0.398
- **MP-A06** (retire): Route has low demand-gain (f1=0.002, score=0.176) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **MP-A07** (shortcut): Route detour_ratio=2.21 > 1.5. Current route_km=15.6km; estimated shortcut=7.8km (straight_line_km=7.1km x 1.1).
  - Current score: 0.265 -> Proposed score: 0.330
- **MP-C01** (shortcut): Route detour_ratio=2.01 > 1.5. Current route_km=32.9km; estimated shortcut=18.0km (straight_line_km=16.4km x 1.1).
  - Current score: 0.149 -> Proposed score: 0.249
- **MP-C02** (shortcut): Route detour_ratio=1.74 > 1.5. Current route_km=28.7km; estimated shortcut=18.2km (straight_line_km=16.6km x 1.1).
  - Current score: 0.150 -> Proposed score: 0.238
- **MP-C03** (merge): Route overlaps 64.8% of served AGEBs with MP-T03 (Jaccard=0.65). Consolidation improves frequency without expanding coverage.
  - Paired with: MP-T03
- **MC-L1** (merge): Route overlaps 100.0% of served AGEBs with MC-L1E (Jaccard=1.00). Consolidation improves frequency without expanding coverage.
  - Paired with: MC-L1E
- **MC-L1E** (retire): Route has low demand-gain (f1=0.003, score=0.261) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **MP-T01** (shortcut): Route detour_ratio=3.18 > 1.5. Current route_km=42.3km; estimated shortcut=14.7km (straight_line_km=13.3km x 1.1).
  - Current score: 0.142 -> Proposed score: 0.269
- **MP-T02** (retire): Route has low demand-gain (f1=0.001, score=0.192) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **MP-T03** (retire): Route has low demand-gain (f1=0.011, score=0.237) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C98** (shortcut): Route detour_ratio=1.95 > 1.5. Current route_km=45.3km; estimated shortcut=25.6km (straight_line_km=23.2km x 1.1).
  - Current score: 0.137 -> Proposed score: 0.174
- **MT_L3** (retire): Route has low demand-gain (f1=0.002, score=0.222) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **MT_L1** (retire): Route has low demand-gain (f1=0.001, score=0.256) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **ST_L1** (merge): Route overlaps 69.0% of served AGEBs with C109 (Jaccard=0.69). Consolidation improves frequency without expanding coverage.
  - Paired with: C109
- **ST_L2** (shortcut): Route detour_ratio=1.97 > 1.5. Current route_km=8.6km; estimated shortcut=4.8km (straight_line_km=4.4km x 1.1).
  - Current score: 0.319 -> Proposed score: 0.351
- **ST_L4** (retire): Route has low demand-gain (f1=0.022, score=0.252) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **LM-V03** (retire): Route has low demand-gain (f1=0.003, score=0.136) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **LM-V04** (retire): Route has low demand-gain (f1=0.006, score=0.260) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **LM-V05** (shortcut): Route detour_ratio=2.04 > 1.5. Current route_km=19.7km; estimated shortcut=10.6km (straight_line_km=9.6km x 1.1).
  - Current score: 0.228 -> Proposed score: 0.303
- **LM-V01** (merge): Route overlaps 87.7% of served AGEBs with C125-V1 (Jaccard=0.88). Consolidation improves frequency without expanding coverage.
  - Paired with: C125-V1
- **LM-V02** (retire): Route has low demand-gain (f1=0.003, score=0.144) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **LM-C01** (shortcut): Route detour_ratio=1.86 > 1.5. Current route_km=29.5km; estimated shortcut=17.5km (straight_line_km=15.9km x 1.1).
  - Current score: 0.151 -> Proposed score: 0.252
- **LM-C02** (shortcut): Route detour_ratio=1.54 > 1.5. Current route_km=15.1km; estimated shortcut=10.8km (straight_line_km=9.8km x 1.1).
  - Current score: 0.261 -> Proposed score: 0.297
- **LM-C03** (retire): Route has low demand-gain (f1=0.010, score=0.280) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.

## W5 Config Used

```
w_demand_gain=0.50, w_efficiency=0.25, w_equity=0.25
max_detour_ratio=1.8, min_stop_spacing=300m, max_stop_spacing=1000m
min_daily_demand=500 trips/day, max_route_km=30km
```