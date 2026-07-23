# W9 W7 Existing Route Audit -- Toluca

Transfer analogue of ZMG's `run_w7.py`, CSV-based. All routes are route_type=3 bus (Gobierno del Estado de Mexico -- Toluca y Area Metropolitana); the audit is mode-agnostic.

## Summary

- **Routes audited:** 622
- **Feasible (W5 constraints):** 0
- **Routes flagged:** 612 (93 Low demand, 88 Indirect, 431 Redundant)
- **Modification proposals:** 612

> **Feasibility note:** median GTFS stop spacing is 43m and 100% of routes sit below the W5 300m minimum. Where the feasible count is low (0/622 here), the binding constraint is this sub-300m stop density in the source feed, not route directness or length -- the audit flags (Low demand / Indirect / Redundant) and W5 scores are the primary signal and are independent of the feasibility gate.

## Score Distribution

- Mean total_score: 0.127  |  median: 0.118
- Mean detour_ratio: 1.506
- Mean f1_demand_gain: 0.010  |  mean f3_equity: 0.179

## Top 10 Routes by Score

| route_id | route_short_name | total_score | f1_demand_gain | detour_ratio | flag |
|---|---|---|---|---|---|
| 18841007 | Primero de Mayo | 0.488 | 0.18 | 1.329 | nan |
| 18840953 | Primero de Mayo | 0.487 | 0.18 | 1.315 | Redundant |
| 19369484 | TBD | 0.395 | 0.061 | 1.141 | nan |
| 19369516 | TBD | 0.386 | 0.049 | 1.722 | Indirect |
| 19369508 | TBD | 0.385 | 0.049 | 1.745 | Redundant |
| 19369478 | TBD | 0.365 | 0.065 | 1.315 | nan |
| 19369476 | TBD | 0.364 | 0.065 | 1.31 | Redundant |
| 18739386 | Temoayenses | 0.356 | 0.036 | 1.2 | nan |
| 18739441 | Temoayenses | 0.356 | 0.036 | 1.2 | Redundant |
| 19369544 | TBD | 0.35 | 0.053 | 1.226 | nan |

## Flagged Routes

| route_id | route_short_name | total_score | detour_ratio | flag | overlap_route_id |
|---|---|---|---|---|---|
| 19369927 | TBD | 0.0 | 1.622 | Indirect | nan |
| 19369436 | TBD | 0.0 | 1.428 | Low demand | nan |
| 18869496 | Primero de Mayo | 0.0 | 2.028 | Indirect | nan |
| 18870209 | Primero de Mayo | 0.0 | 1.385 | Low demand | nan |
| 18874454 | Primero de Mayo | 0.0 | 1.401 | Low demand | nan |
| 18874490 | Primero de Mayo | 0.0 | 1.346 | Low demand | nan |
| 19369293 | TBD | 0.0 | 1.405 | Low demand | nan |
| 19369292 | TBD | 0.0 | 1.4 | Low demand | nan |
| 19369272 | TBD | 0.0 | 1.236 | Low demand | nan |
| 19369288 | TBD | 0.0 | 1.593 | Indirect | nan |
| 19369271 | TBD | 0.0 | 1.671 | Indirect | nan |
| 19369265 | TBD | 0.0 | 1.253 | Low demand | nan |
| 18869482 | Primero de Mayo | 0.0 | 1.705 | Indirect | nan |
| 19369264 | TBD | 0.0 | 1.429 | Low demand | nan |
| 18869210 | Primero de Mayo | 0.0 | 1.267 | Low demand | nan |
| 18869229 | Primero de Mayo | 0.0 | 1.263 | Low demand | nan |
| 18840656 | Primero de Mayo | 0.0 | 1.508 | Indirect | nan |
| 18840816 | Primero de Mayo | 0.0 | 1.495 | Low demand | nan |
| 18334498 | Estrella | 0.0 | 1.204 | Low demand | nan |
| 18841318 | Primero de Mayo | 0.0 | 1.459 | Low demand | nan |
| 18841100 | Primero de Mayo | 0.0 | 1.1 | Low demand | nan |
| 18841117 | Primero de Mayo | 0.0 | 1.4 | Low demand | nan |
| 18841014 | Primero de Mayo | 0.0 | 1.198 | Low demand | nan |
| 18841071 | Primero de Mayo | 0.0 | 1.301 | Low demand | nan |
| 18841309 | Primero de Mayo | 0.0 | 1.85 | Indirect | nan |
| 18841218 | Primero de Mayo | 0.0 | 1.316 | Low demand | nan |
| 18841308 | Primero de Mayo | 0.0 | 1.318 | Low demand | nan |
| 18841295 | Primero de Mayo | 0.0 | 1.835 | Indirect | nan |
| 19369253 | TBD | 0.0 | 2.394 | Indirect | nan |
| 19369243 | TBD | 0.0 | 2.384 | Indirect | nan |
| 19369195 | TBD | 0.0 | 1.628 | Indirect | nan |
| 19369199 | TBD | 0.0 | 1.318 | Low demand | nan |
| 19369257 | TBD | 0.0 | 2.155 | Indirect | nan |
| 19369256 | TBD | 0.0 | 1.667 | Indirect | nan |
| 19369255 | TBD | 0.0 | 1.899 | Indirect | nan |
| 19369254 | TBD | 0.0 | 1.704 | Indirect | nan |
| 19369229 | TBD | 0.0 | 1.646 | Indirect | nan |
| 19369219 | TBD | 0.0 | 1.585 | Indirect | nan |
| 19367448 | TBD | 0.0 | 1.425 | Low demand | nan |
| 19367449 | TBD | 0.0 | 1.486 | Low demand | nan |
| 19369241 | TBD | 0.0 | 2.642 | Indirect | nan |
| 19369238 | TBD | 0.0 | 2.652 | Indirect | nan |
| 19369180 | TBD | 0.0 | 1.62 | Indirect | nan |
| 18739443 | Temoayenses | 0.0 | 1.151 | Low demand | nan |
| 19369172 | TBD | 0.0 | 1.317 | Low demand | nan |
| 19367696 | TBD | 0.0 | 1.618 | Indirect | nan |
| 19367488 | TBD | 0.0 | 2.481 | Indirect | nan |
| 19367460 | TBD | 0.0 | 2.481 | Indirect | nan |
| 18268117 | Estrella | 0.0 | 1.167 | Low demand | nan |
| 18739445 | Temoayenses | 0.0 | 1.141 | Low demand | nan |
| 19366979 | TBD | 0.036 | 1.196 | Redundant | 18212752 |
| 19366908 | TBD | 0.036 | 1.18 | Redundant | 18212752 |
| 18878072 | Primero de Mayo | 0.036 | 1.186 | Redundant | 18212752 |
| 19367456 | TBD | 0.036 | 1.319 | Redundant | 18212752 |
| 19367206 | TBD | 0.036 | 1.471 | Redundant | 18212752 |
| 19367458 | TBD | 0.036 | 1.329 | Redundant | 18212752 |
| 19369426 | TBD | 0.036 | 1.207 | Redundant | 18212752 |
| 19369449 | TBD | 0.036 | 1.237 | Redundant | 18212752 |
| 19367447 | TBD | 0.036 | 1.477 | Redundant | 18212752 |
| 18841355 | Primero de Mayo | 0.036 | 1.198 | Redundant | 18212752 |
| 18878186 | Corsarios | 0.038 | 1.68 | Redundant | 18704763 |
| 18756218 | Tlachaloya | 0.038 | 1.614 | Redundant | 18796291 |
| 18766356 | INTER | 0.038 | 1.495 | Redundant | 18796291 |
| 18878179 | Corsarios | 0.038 | 1.629 | Redundant | 18796291 |
| 18739516 | R E D | 0.039 | 1.43 | Redundant | 18794052 |
| 18739673 | R E D | 0.039 | 1.328 | Redundant | 18794052 |
| 18739503 | R E D | 0.039 | 1.318 | Redundant | 18794052 |
| 18739624 | R E D | 0.039 | 1.276 | Redundant | 18796291 |
| 18756216 | Tlachaloya | 0.039 | 1.685 | Redundant | 18796291 |
| 18739483 | R E D | 0.039 | 1.279 | Redundant | 18796291 |
| 18739535 | R E D | 0.039 | 1.396 | Redundant | 18796291 |
| 18878176 | Corsarios | 0.039 | 1.685 | Redundant | 18796291 |
| 18766349 | INTER | 0.039 | 1.481 | Redundant | 18796291 |
| 18765971 | Tlachaloya | 0.039 | 1.642 | Redundant | 18796291 |
| 18704711 | Flecha Blanca | 0.039 | 1.278 | Redundant | 18796291 |
| 18937710 | Corsarios | 0.04 | 1.657 | Redundant | 18796291 |
| 18878194 | Corsarios | 0.041 | 1.359 | Redundant | 18704763 |
| 18878198 | Corsarios | 0.042 | 1.303 | Redundant | 18796291 |
| 19363047 | TBD | 0.043 | 1.305 | Redundant | 18212752 |
| 18782127 | Flecha de Oro | 0.044 | 1.612 | Redundant | 18794052 |
| 18765983 | Tlachaloya | 0.045 | 1.566 | Redundant | 18796291 |
| 18769664 | Xinantécatl | 0.045 | 1.649 | Redundant | 18769578 |
| 18269212 | Estrella | 0.046 | 1.538 | Redundant | 18334522 |
| 18266131 | Estrella | 0.047 | 1.474 | Redundant | 18334522 |
| 18268203 | Flecha Blanca | 0.047 | 1.395 | Redundant | 18704763 |
| 18268136 | Estrella | 0.048 | 1.398 | Redundant | 18334536 |
| 18878167 | Corsarios | 0.049 | 1.561 | Redundant | 18704763 |
| 18769798 | Flecha de Oro | 0.049 | 1.311 | Redundant | 18794052 |
| 19366753 | TBD | 0.05 | 1.273 | Redundant | 18212752 |
| 18265983 | Estrella | 0.05 | 1.611 | Redundant | 18266208 |
| 18766358 | Cuatro Caminos | 0.05 | 1.332 | Redundant | 18794052 |
| 18796179 | Crucero | 0.05 | 1.346 | Redundant | 18794052 |
| 18268140 | Estrella | 0.05 | 1.315 | Redundant | 18794052 |
| 18769580 | Cuatro Caminos | 0.05 | 1.351 | Redundant | 18794052 |
| 18878271 | Multiservicios | 0.05 | 1.497 | Redundant | 18768324 |
| 18878282 | Multiservicios | 0.05 | 1.286 | Redundant | 18768324 |
| 18268072 | Estrella | 0.05 | 1.56 | Redundant | 18266208 |
| 18266067 | Estrella | 0.05 | 1.716 | Redundant | 18266208 |
| 18266011 | Estrella | 0.05 | 1.647 | Redundant | 18266208 |
| 18796342 | Crucero | 0.05 | 1.327 | Redundant | 18794052 |
| 18766357 | Cuatro Caminos | 0.05 | 1.311 | Redundant | 18794052 |
| 18291971 | Estrella | 0.05 | 1.524 | Redundant | 18334522 |
| 18268107 | Estrella | 0.05 | 1.709 | Redundant | 18334522 |
| 18334536 | Estrella | 0.05 | 1.441 | Low demand | nan |
| 18756034 | R E D | 0.051 | 2.037 | Redundant | 18704763 |
| 18756221 | Tlachaloya | 0.051 | 1.543 | Redundant | 18796291 |
| 18878187 | Corsarios | 0.051 | 1.501 | Redundant | 18796291 |
| 18796212 | Flecha de Oro | 0.052 | 1.297 | Redundant | 18794052 |
| 18769548 | Xinantécatl | 0.052 | 1.453 | Redundant | 18769524 |
| 18878173 | Corsarios | 0.053 | 1.54 | Redundant | 18796291 |
| 18709058 | TEO | 0.053 | 1.376 | Redundant | 18291954 |
| 18796305 | INTER | 0.053 | 1.619 | Indirect | nan |
| 18739528 | R E D | 0.053 | 2.048 | Redundant | 18796291 |
| 18494515 | Estrella | 0.053 | 1.289 | Redundant | 18794052 |
| 18769687 | Flecha de Oro | 0.053 | 1.287 | Redundant | 18794052 |
| 18756038 | Tlachaloya | 0.053 | 1.512 | Redundant | 18796291 |
| 18766368 | Cuatro Caminos | 0.053 | 1.594 | Redundant | 18268510 |
| 18268133 | Estrella | 0.054 | 1.386 | Redundant | 18334502 |
| 18769705 | Flecha de Oro | 0.054 | 1.264 | Redundant | 18794052 |
| 18756212 | INTER | 0.054 | 1.315 | Redundant | 18796291 |
| 18268037 | Estrella | 0.054 | 1.664 | Redundant | 18266208 |
| 18769707 | Flecha de Oro | 0.054 | 1.285 | Redundant | 18794052 |
| 18292226 | TEO | 0.054 | 1.246 | Redundant | 18768818 |
| 18265943 | Estrella | 0.054 | 1.36 | Redundant | 18266208 |
| 18864603 | Satélite | 0.055 | 1.342 | Redundant | 18864665 |
| 18769577 | Xinantécatl | 0.055 | 1.452 | Redundant | 18769527 |
| 19369435 | TBD | 0.055 | 1.595 | Redundant | 18704763 |
| 18292006 | Estrella | 0.055 | 1.608 | Redundant | 18334522 |
| 18864836 | Bicentenario | 0.055 | 1.899 | Redundant | 18878134 |
| 19355139 | Estrella | 0.055 | 1.646 | Redundant | 18266208 |
| 18266070 | Estrella | 0.056 | 1.718 | Redundant | 18266208 |
| 18794130 | Crucero | 0.056 | 1.478 | Redundant | 18794052 |
| 18864804 | Bicentenario | 0.057 | 2.012 | Redundant | 18878134 |
| 18766382 | Cuatro Caminos | 0.057 | 1.917 | Redundant | 18794052 |
| 18769863 | Flecha de Oro | 0.057 | 1.317 | Redundant | 18794052 |
| 19369432 | TBD | 0.057 | 1.615 | Redundant | 18796291 |
| 18769713 | Xinantécatl | 0.057 | 1.624 | Redundant | 18769527 |
| 18268144 | Estrella | 0.057 | 1.588 | Redundant | 18334522 |
| 18796301 | INTER | 0.057 | 1.551 | Redundant | 18796314 |
| 18878193 | Corsarios | 0.057 | 1.445 | Redundant | 18796291 |
| 19358564 | TBD | 0.057 | 1.511 | Redundant | 18334522 |
| 18291954 | TEO | 0.058 | 1.313 | Low demand | nan |
| 18766370 | Cuatro Caminos | 0.058 | 1.917 | Redundant | 18794052 |
| 18756184 | INTER | 0.058 | 1.307 | Redundant | 18796291 |
| 18292017 | Estrella | 0.058 | 1.672 | Redundant | 18334522 |
| 18766373 | Tlachaloya | 0.058 | 1.481 | Redundant | 18796291 |
| 18769861 | Flecha de Oro | 0.058 | 1.359 | Redundant | 18582498 |
| 18769649 | Xinantécatl | 0.059 | 1.594 | Redundant | 18768818 |
| 18291963 | Estrella | 0.059 | 1.23 | Redundant | 18266002 |
| 18796314 | INTER | 0.059 | 1.545 | Indirect | nan |
| 18766369 | Cuatro Caminos | 0.059 | 1.358 | Redundant | 18794052 |
| 18769693 | Flecha de Oro | 0.06 | 1.332 | Redundant | 18794052 |
| 18796267 | Crucero | 0.06 | 1.859 | Redundant | 18268510 |
| 18511109 | Estrella | 0.06 | 1.557 | Redundant | 18510108 |
| 18796208 | Flecha de Oro | 0.06 | 1.269 | Redundant | 18794052 |
| 18291925 | Del Valle | 0.06 | 1.21 | Redundant | 18709064 |
| 19369569 | TBD | 0.06 | 1.275 | Redundant | 18212752 |
| 19369681 | TBD | 0.06 | 1.275 | Redundant | 18212752 |
| 18766376 | Cuatro Caminos | 0.06 | 1.341 | Redundant | 18794052 |
| 18796251 | Crucero | 0.06 | 1.93 | Redundant | 18268510 |
| 19369250 | TBD | 0.06 | 1.923 | Redundant | 18212752 |
| 18769686 | Flecha de Oro | 0.06 | 1.313 | Redundant | 18794052 |
| 18756044 | Tlachaloya | 0.061 | 1.451 | Redundant | 18704763 |
| 18769849 | Flecha de Oro | 0.061 | 1.388 | Redundant | 18794052 |
| 18709212 | TEO | 0.061 | 1.251 | Redundant | 18768823 |
| 18291846 | Del Valle | 0.061 | 1.236 | Redundant | 18292060 |
| 18796182 | Flecha de Oro | 0.061 | 1.349 | Redundant | 18718061 |
| 19370105 | Flecha de Oro | 0.061 | 1.371 | Redundant | 18794052 |
| 19370138 | Crucero | 0.062 | 1.503 | Redundant | 18737050 |
| 18268510 | Estrella | 0.062 | 1.578 | Redundant | 18268365 |
| 18782104 | Flecha de Oro | 0.063 | 1.515 | Redundant | 18794052 |
| 18779546 | Crucero | 0.063 | 1.425 | Redundant | 18718061 |
| 18786516 | Crucero | 0.063 | 1.606 | Redundant | 18794052 |
| 18510029 | Estrella | 0.063 | 1.669 | Redundant | 18794052 |
| 18291941 | Flecha Blanca | 0.064 | 1.308 | Redundant | 18794052 |
| 18786512 | Crucero | 0.064 | 1.585 | Redundant | 18794052 |
| 18268152 | Estrella | 0.065 | 1.704 | Redundant | 18794052 |
| 18796270 | INTER | 0.065 | 1.9 | Indirect | nan |
| 19361995 | TBD | 0.065 | 1.442 | Redundant | 18266208 |
| 18510108 | Estrella | 0.065 | 1.928 | Redundant | 18334522 |
| 18739303 | Temoayenses | 0.065 | 1.347 | Redundant | 18794052 |
| 18268019 | Estrella | 0.066 | 1.469 | Redundant | 18334552 |
| 18268365 | Estrella | 0.066 | 1.806 | Redundant | 18266208 |
| 18739384 | Temoayenses | 0.066 | 1.196 | Redundant | 18794052 |
| 18796282 | INTER | 0.066 | 1.463 | Redundant | 18291977 |
| 18739561 | Temoayenses | 0.067 | 1.188 | Redundant | 18794052 |
| 18739380 | Temoayenses | 0.067 | 1.197 | Redundant | 18739431 |
| 18292060 | Del Valle | 0.067 | 1.195 | Redundant | 18292175 |
| 18739537 | Temoayenses | 0.068 | 1.197 | Redundant | 18739431 |
| 18702473 | Del Valle | 0.068 | 1.173 | Redundant | 18769589 |
| 18292175 | TEO | 0.068 | 1.105 | Redundant | 18709204 |
| 18334552 | Estrella | 0.069 | 1.375 | Low demand | nan |
| 18827321 | TEO | 0.069 | 1.762 | Redundant | 18827318 |
| 19369532 | TBD | 0.069 | 1.257 | Redundant | 18212752 |
| 18858644 | Primero de Mayo | 0.069 | 1.24 | Redundant | 18212752 |
| 18737153 | Temoayenses | 0.069 | 1.33 | Redundant | 18794052 |
| 18769840 | Flecha de Oro | 0.069 | 1.29 | Redundant | 18794052 |
| 18782420 | Flecha de Oro | 0.07 | 1.35 | Redundant | 18794052 |
| 18782088 | TEO | 0.07 | 1.424 | Redundant | 18212752 |
| 18782097 | TEO | 0.07 | 1.438 | Redundant | 18212752 |
| 18268559 | Flecha Blanca | 0.071 | 1.602 | Redundant | 18794052 |
| 18709204 | TEO | 0.071 | 1.094 | Redundant | 18769589 |
| 18840408 | S T U T | 0.071 | 1.547 | Indirect | nan |
| 18839951 | S T U T | 0.071 | 1.712 | Redundant | 18839794 |
| 18782137 | Flecha de Oro | 0.071 | 1.33 | Redundant | 18781310 |
| 18841064 | Primero de Mayo | 0.072 | 1.208 | Redundant | 18212752 |
| 18785813 | Flecha de Oro | 0.073 | 1.938 | Redundant | 18794052 |
| 18796224 | Flecha de Oro | 0.075 | 1.262 | Redundant | 18718061 |
| 18739416 | Temoayenses | 0.075 | 1.397 | Redundant | 18739431 |
| 18769875 | Flecha de Oro | 0.075 | 1.259 | Redundant | 18718061 |
| 18769593 | Xinantécatl | 0.076 | 1.613 | Indirect | nan |
| 18841019 | Primero de Mayo | 0.076 | 1.19 | Redundant | 18212752 |
| 18739385 | Temoayenses | 0.076 | 1.386 | Redundant | 18739431 |
| 18766365 | Cuatro Caminos | 0.077 | 1.991 | Redundant | 18794052 |
| 18739433 | Temoayenses | 0.078 | 1.172 | Redundant | 18739431 |
| 18266002 | Estrella | 0.078 | 1.136 | Low demand | nan |
| 18781310 | Cuatro Caminos | 0.078 | 1.967 | Redundant | 18794052 |
| 18739397 | Temoayenses | 0.079 | 1.175 | Redundant | 18739431 |
| 18769647 | Xinantécatl | 0.079 | 1.896 | Redundant | 18840584 |
| 18878181 | Corsarios | 0.08 | 1.263 | Redundant | 18768324 |
| 18878169 | Corsarios | 0.08 | 1.247 | Redundant | 18768324 |
| 18739519 | Temoayenses | 0.08 | 1.259 | Redundant | 18794052 |
| 18266023 | Estrella | 0.081 | 1.302 | Redundant | 18266208 |
| 18704717 | Flecha Blanca | 0.081 | 1.22 | Redundant | 18796291 |
| 18878205 | Colón | 0.081 | 2.251 | Redundant | 18934075 |
| 18769588 | Xinantécatl | 0.082 | 1.928 | Redundant | 18840584 |
| 18878166 | TEO | 0.082 | 1.648 | Redundant | 18878155 |
| 18878247 | TEO | 0.082 | 1.672 | Redundant | 18878155 |
| 18732693 | ATSUZI | 0.082 | 1.625 | Redundant | 18732687 |
| 18739470 | Temoayenses | 0.083 | 1.206 | Redundant | 18739431 |
| 18796193 | Flecha de Oro | 0.083 | 1.871 | Redundant | 18794052 |
| 18858636 | Primero de Mayo | 0.084 | 1.166 | Redundant | 18212752 |
| 18739457 | Temoayenses | 0.084 | 1.162 | Redundant | 18739431 |
| 18840054 | S T U T | 0.085 | 1.507 | Indirect | nan |
| 19369517 | TBD | 0.085 | 1.422 | Redundant | 18582498 |
| 18739502 | Temoayenses | 0.086 | 1.249 | Redundant | 18739431 |
| 19369214 | TBD | 0.086 | 1.708 | Redundant | 18878155 |
| 18878164 | TEO | 0.086 | 1.295 | Redundant | 18878155 |
| 19369233 | TBD | 0.086 | 1.714 | Redundant | 18878155 |
| 19369185 | TBD | 0.086 | 1.666 | Redundant | 18878155 |
| 18878236 | TEO | 0.086 | 1.284 | Redundant | 18878155 |
| 19369181 | TBD | 0.086 | 1.641 | Redundant | 18878155 |
| 18291977 | TEO | 0.087 | 1.192 | Redundant | 18768818 |
| 18796202 | Flecha de Oro | 0.087 | 1.292 | Redundant | 18794052 |
| 18768918 | Xinantécatl | 0.087 | 2.141 | Redundant | 18768889 |
| 18709064 | TEO | 0.087 | 1.207 | Redundant | 18768823 |
| 18827318 | TEO | 0.088 | 1.68 | Indirect | nan |
| 18739505 | Triángulo | 0.089 | 1.619 | Redundant | 18212742 |
| 18739465 | Triángulo | 0.09 | 1.665 | Redundant | 18212742 |
| 18869220 | Primero de Mayo | 0.09 | 1.292 | Redundant | 18878155 |
| 18869447 | Primero de Mayo | 0.09 | 1.292 | Redundant | 18878155 |
| 18839904 | S T U T | 0.091 | 1.58 | Redundant | 18840079 |
| 18732690 | ATSUZI | 0.091 | 1.809 | Redundant | 18796309 |
| 18739379 | Temoayenses | 0.091 | 1.214 | Redundant | 18739431 |
| 18739365 | Temoayenses | 0.093 | 1.217 | Redundant | 18739431 |
| 18781288 | INTER | 0.093 | 1.558 | Redundant | 18796291 |
| 18839598 | S T U T | 0.094 | 1.59 | Redundant | 18796207 |
| 18934075 | Colón | 0.095 | 2.165 | Indirect | nan |
| 18840864 | S T U T | 0.095 | 1.627 | Redundant | 18796207 |
| 18732694 | ATSUZI | 0.096 | 1.69 | Redundant | 18732687 |
| 18840621 | S T U T | 0.096 | 1.651 | Redundant | 18796213 |
| 18840028 | S T U T | 0.096 | 1.529 | Redundant | 18796213 |
| 18878252 | TBD | 0.096 | 1.409 | Redundant | 18870090 |
| 18781276 | INTER | 0.096 | 1.473 | Redundant | 18796291 |
| 18878160 | Tollocan | 0.097 | 1.589 | Redundant | 18875061 |
| 18796194 | Flecha de Oro | 0.097 | 1.261 | Redundant | 18794052 |
| 18739518 | Triángulo | 0.098 | 1.553 | Redundant | 18212742 |
| 18878224 | TBD | 0.099 | 1.386 | Redundant | 18870090 |
| 18782085 | TEO | 0.099 | 1.187 | Redundant | 18878155 |
| 18732701 | ATSUZI | 0.1 | 1.742 | Redundant | 18732704 |
| 18732696 | ATSUZI | 0.1 | 1.712 | Redundant | 18736934 |
| 18840079 | S T U T | 0.101 | 1.532 | Indirect | nan |
| 18769581 | Xinantécatl | 0.101 | 1.112 | Redundant | 18768818 |
| 18704775 | Flecha Blanca | 0.101 | 1.51 | Redundant | 18796291 |
| 18739475 | Triángulo | 0.102 | 1.595 | Redundant | 18212742 |
| 18739547 | R E D | 0.102 | 1.992 | Redundant | 18266201 |
| 18769589 | Xinantécatl | 0.103 | 1.126 | Redundant | 18768823 |
| 18864665 | Satélite | 0.103 | 1.54 | Indirect | nan |
| 18769675 | Xinantécatl | 0.104 | 1.264 | Redundant | 18769641 |
| 19369234 | TBD | 0.104 | 1.937 | Redundant | 18212752 |
| 18732687 | ATSUZI | 0.105 | 1.725 | Indirect | nan |
| 18796254 | TBD | 0.106 | 1.415 | Redundant | 18796261 |
| 19369279 | TBD | 0.106 | 1.222 | Redundant | 18212752 |
| 18739462 | Temoayenses | 0.106 | 1.176 | Redundant | 18739431 |
| 18739446 | Temoayenses | 0.106 | 1.176 | Redundant | 18739431 |
| 18291974 | Estrella | 0.107 | 1.192 | Redundant | 18334522 |
| 18739474 | TBD | 0.107 | 1.39 | Redundant | 18739557 |
| 18796252 | Cultural | 0.108 | 1.682 | Redundant | 18827386 |
| 18819389 | CTTSA | 0.108 | 1.446 | Low demand | nan |
| 18769803 | Xinantécatl | 0.109 | 1.196 | Redundant | 18769524 |
| 18839794 | S T U T | 0.109 | 1.475 | Redundant | 18823543 |
| 19369286 | TBD | 0.109 | 1.197 | Redundant | 18212752 |
| 18796253 | INTER | 0.111 | 1.384 | Low demand | nan |
| 18874432 | 8 de Noviembre | 0.111 | 1.768 | Redundant | 18823543 |
| 18739557 | TBD | 0.111 | 1.354 | Low demand | nan |
| 18739558 | R E D | 0.112 | 1.995 | Redundant | 18292016 |
| 18769866 | Xinantécatl | 0.112 | 1.238 | Low demand | nan |
| 18768889 | Xinantécatl | 0.112 | 1.996 | Indirect | nan |
| 18796268 | CTTSA | 0.113 | 1.423 | Low demand | nan |
| 18737087 | ATSUZI | 0.113 | 2.265 | Redundant | 18736695 |
| 18739527 | Triángulo | 0.114 | 1.646 | Redundant | 18739473 |
| 18878234 | Colón | 0.114 | 2.113 | Indirect | nan |
| 18796261 | TBD | 0.114 | 1.395 | Low demand | nan |
| 18840405 | 8 de Noviembre | 0.114 | 1.717 | Redundant | 18958354 |
| 19357066 | TBD | 0.115 | 1.455 | Redundant | 18212752 |
| 18735566 | ATSUZI | 0.115 | 1.624 | Indirect | nan |
| 18739338 | Temoayenses | 0.115 | 1.146 | Redundant | 18739431 |
| 18739350 | Temoayenses | 0.115 | 1.146 | Redundant | 18739431 |
| 19347286 | TBD | 0.118 | 1.442 | Redundant | 18212752 |
| 18284841 | Flecha Blanca | 0.118 | 1.467 | Redundant | 18794052 |
| 18212821 | Triángulo | 0.118 | 1.543 | Redundant | 18212752 |
| 18770036 | TEO | 0.119 | 1.192 | Redundant | 18212752 |
| 18212806 | Triángulo | 0.119 | 1.373 | Redundant | 18212802 |
| 18878212 | Colón | 0.119 | 1.983 | Indirect | nan |
| 18212798 | Triángulo | 0.119 | 1.533 | Redundant | 18212752 |
| 18704763 | Flecha Blanca | 0.119 | 1.271 | Redundant | 18796291 |
| 18878159 | TEO | 0.119 | 1.207 | Redundant | 18212752 |
| 18878211 | Gacela | 0.12 | 1.741 | Redundant | 18878213 |
| 18769626 | Xinantécatl | 0.12 | 1.4 | Redundant | 18769641 |
| 18769578 | Xinantécatl | 0.12 | 1.259 | Low demand | nan |
| 18878155 | TEO | 0.12 | 1.194 | Redundant | 18212752 |
| 18735575 | ATSUZI | 0.122 | 1.651 | Indirect | nan |
| 18796283 | Cultural | 0.122 | 1.554 | Redundant | 18827386 |
| 18265967 | Estrella | 0.123 | 1.289 | Redundant | 18334522 |
| 18732704 | ATSUZI | 0.124 | 1.65 | Indirect | nan |
| 18768446 | Xinantécatl | 0.124 | 1.126 | Redundant | 18768818 |
| 18878213 | Gacela | 0.126 | 1.71 | Indirect | nan |
| 18823559 | A U T | 0.127 | 2.506 | Redundant | 18823899 |
| 18212734 | Triángulo | 0.127 | 1.521 | Redundant | 18212752 |
| 18878138 | Tollocan | 0.127 | 1.382 | Redundant | 18878110 |
| 18212742 | Triángulo | 0.127 | 1.511 | Redundant | 18212752 |
| 18766391 | TEO | 0.127 | 1.696 | Redundant | 18766389 |
| 18266201 | Estrella | 0.128 | 1.707 | Redundant | 18266208 |
| 18334502 | Estrella | 0.128 | 1.27 | Redundant | 18334522 |
| 18735536 | ATSUZI | 0.128 | 1.627 | Redundant | 18334522 |
| 18796243 | INTER | 0.129 | 1.921 | Redundant | 18796223 |
| 18768458 | Xinantécatl | 0.129 | 1.104 | Redundant | 18768823 |
| 18769524 | Xinantécatl | 0.13 | 1.243 | Redundant | 18768818 |
| 18769641 | Xinantécatl | 0.13 | 1.342 | Low demand | nan |
| 18769670 | Xinantécatl | 0.13 | 1.11 | Redundant | 18768823 |
| 18266208 | Estrella | 0.131 | 1.607 | Redundant | 18334522 |
| 18709021 | Ala de Oro | 0.131 | 1.618 | Redundant | 18878117 |
| 18709213 | Ala de Oro | 0.131 | 1.615 | Redundant | 18878117 |
| 18878146 | Tollocan | 0.131 | 1.749 | Redundant | 18878137 |
| 18910283 | Gacela | 0.131 | 2.011 | Redundant | 18878134 |
| 18735497 | ATSUZI | 0.131 | 1.619 | Redundant | 18334522 |
| 18769689 | Xinantécatl | 0.131 | 1.096 | Low demand | nan |
| 18739473 | Triángulo | 0.132 | 1.56 | Indirect | nan |
| 18735446 | Triángulo | 0.133 | 1.258 | Redundant | 18735441 |
| 18212802 | Triángulo | 0.133 | 1.27 | Low demand | nan |
| 18766389 | TEO | 0.133 | 1.665 | Indirect | nan |
| 18736999 | ATSUZI | 0.133 | 1.557 | Redundant | 18878117 |
| 18737050 | ATSUZI | 0.134 | 1.554 | Redundant | 18878117 |
| 18292016 | Estrella | 0.135 | 1.711 | Redundant | 18334522 |
| 18827377 | TEO | 0.135 | 1.461 | Redundant | 18827386 |
| 18735441 | Triángulo | 0.135 | 1.246 | Low demand | nan |
| 18823770 | Rápidos | 0.135 | 2.129 | Redundant | 18839833 |
| 18878258 | Gacela | 0.136 | 1.989 | Redundant | 18878134 |
| 18769629 | Xinantécatl | 0.136 | 1.932 | Redundant | 18769698 |
| 18840917 | Primero de Mayo | 0.137 | 1.306 | Redundant | 18212752 |
| 18736641 | ATSUZI | 0.137 | 1.609 | Indirect | nan |
| 18869991 | Tollocan | 0.137 | 1.495 | Redundant | 18870090 |
| 18718061 | Ala de Oro | 0.137 | 1.818 | Redundant | 18878117 |
| 18839833 | Rápidos | 0.138 | 2.22 | Indirect | nan |
| 18796237 | Urbana | 0.138 | 2.089 | Redundant | 18796219 |
| 18334522 | Estrella | 0.138 | 1.546 | Indirect | nan |
| 18875061 | Tollocan | 0.139 | 1.504 | Redundant | 18878110 |
| 18827386 | TEO | 0.139 | 1.444 | Low demand | nan |
| 18815999 | Pegaso | 0.139 | 1.545 | Redundant | 18796213 |
| 18796211 | Cultural | 0.14 | 1.844 | Indirect | nan |
| 18958354 | TEO | 0.14 | 1.524 | Redundant | 18823543 |
| 18736695 | ATSUZI | 0.14 | 1.812 | Indirect | nan |
| 18823356 | Pegaso | 0.14 | 1.586 | Redundant | 18796207 |
| 18769527 | Xinantécatl | 0.14 | 1.288 | Redundant | 18768823 |
| 18768818 | Xinantécatl | 0.141 | 1.185 | Low demand | nan |
| 18870090 | Tollocan | 0.141 | 1.565 | Redundant | 18796220 |
| 18769698 | Xinantécatl | 0.142 | 1.833 | Indirect | nan |
| 18870262 | Colón | 0.142 | 1.505 | Redundant | 18840226 |
| 18768813 | Xinantécatl | 0.143 | 1.414 | Low demand | nan |
| 18796219 | Urbana | 0.144 | 2.019 | Redundant | 18839402 |
| 18732703 | ATSUZI | 0.144 | 1.541 | Redundant | 18736622 |
| 18827414 | TEO | 0.145 | 1.51 | Redundant | 18878202 |
| 18878137 | Tollocan | 0.145 | 1.574 | Indirect | nan |
| 18870163 | Bicentenario | 0.146 | 1.71 | Redundant | 18878134 |
| 18768791 | Xinantécatl | 0.146 | 2.003 | Redundant | 18768725 |
| 18841006 | Primero de Mayo | 0.146 | 1.275 | Low demand | nan |
| 18878279 | Gacela | 0.147 | 1.664 | Redundant | 18878134 |
| 18878268 | Gacela | 0.148 | 1.657 | Redundant | 18878134 |
| 18796207 | R E D | 0.148 | 1.576 | Redundant | 18796213 |
| 18268545 | Flecha Blanca | 0.149 | 1.274 | Redundant | 18709005 |
| 18796373 | TBD | 0.149 | 2.589 | Indirect | nan |
| 18878191 | Tollocan | 0.149 | 1.355 | Redundant | 18878123 |
| 18823543 | TEO | 0.149 | 1.477 | Redundant | 18796220 |
| 18838435 | 8 de Noviembre | 0.149 | 1.46 | Redundant | 18874306 |
| 18878123 | Tollocan | 0.149 | 1.358 | Low demand | nan |
| 18869176 | Bicentenario | 0.15 | 1.645 | Redundant | 18878134 |
| 18796309 | R E D | 0.15 | 1.706 | Redundant | 18825286 |
| 18796222 | Cultural | 0.15 | 1.745 | Redundant | 18796308 |
| 18878108 | Tollocan | 0.151 | 1.384 | Redundant | 18878114 |
| 18768823 | Xinantécatl | 0.151 | 1.174 | Low demand | nan |
| 18768725 | Xinantécatl | 0.152 | 1.934 | Indirect | nan |
| 18768803 | Xinantécatl | 0.152 | 1.312 | Low demand | nan |
| 18739435 | Temoayenses | 0.152 | 1.404 | Redundant | 18794052 |
| 18874306 | 8 de Noviembre | 0.152 | 1.464 | Low demand | nan |
| 18739431 | Temoayenses | 0.153 | 1.408 | Redundant | 18794052 |
| 18825286 | R E D | 0.153 | 1.728 | Indirect | nan |
| 18878204 | Colón | 0.153 | 1.616 | Redundant | 18878202 |
| 18796213 | R E D | 0.153 | 1.484 | Low demand | nan |
| 18704821 | Flecha Blanca | 0.154 | 1.267 | Redundant | 18709005 |
| 19369425 | TBD | 0.154 | 1.763 | Redundant | 19369474 |
| 18796234 | INTER | 0.154 | 1.833 | Redundant | 18796246 |
| 18827432 | TEO | 0.154 | 1.379 | Redundant | 18878202 |
| 18796238 | Cultural | 0.155 | 1.705 | Redundant | 18878202 |
| 18582498 | Ala de Oro | 0.155 | 1.705 | Redundant | 18878117 |
| 18878152 | Tollocan | 0.155 | 1.436 | Redundant | 18878225 |
| 18878036 | Tollocan | 0.156 | 1.29 | Redundant | 18874864 |
| 18796220 | Cultural | 0.157 | 1.732 | Redundant | 18878202 |
| 18292021 | Flecha Blanca | 0.157 | 1.607 | Redundant | 18709039 |
| 18823899 | A U T | 0.157 | 2.028 | Indirect | nan |
| 18878114 | Tollocan | 0.158 | 1.328 | Low demand | nan |
| 18878225 | Tollocan | 0.158 | 1.416 | Low demand | nan |
| 18735597 | ATSUZI | 0.158 | 1.268 | Redundant | 18736934 |
| 18840447 | S T U T | 0.159 | 1.585 | Redundant | 18840449 |
| 18708785 | Flecha Blanca | 0.159 | 1.632 | Redundant | 18709039 |
| 18796223 | R E D | 0.159 | 2.046 | Indirect | nan |
| 18736638 | ATSUZI | 0.16 | 1.395 | Low demand | nan |
| 18796292 | Urbana | 0.16 | 1.826 | Redundant | 18796264 |
| 18768312 | TEO | 0.16 | 1.588 | Redundant | 18874884 |
| 18840449 | S T U T | 0.161 | 1.529 | Indirect | nan |
| 18768314 | TEO | 0.161 | 1.571 | Redundant | 18874884 |
| 18878202 | Colón | 0.161 | 1.531 | Indirect | nan |
| 18796227 | Urbana | 0.162 | 1.952 | Redundant | 18291951 |
| 18869177 | Colón | 0.163 | 1.348 | Redundant | 19369474 |
| 18796264 | Urbana | 0.163 | 1.772 | Indirect | nan |
| 18841150 | Satélite | 0.163 | 1.646 | Indirect | nan |
| 18874864 | Tollocan | 0.164 | 1.216 | Low demand | nan |
| 18840584 | S T U T | 0.164 | 2.132 | Redundant | 18840622 |
| 18875182 | Colón | 0.166 | 1.364 | Low demand | nan |
| 18878110 | Tollocan | 0.167 | 1.277 | Low demand | nan |
| 18878161 | Tollocan | 0.167 | 1.277 | Redundant | 18878110 |
| 18827294 | 8 de Noviembre | 0.167 | 1.34 | Low demand | nan |
| 18796248 | Urbana | 0.167 | 1.836 | Indirect | nan |
| 18840622 | S T U T | 0.168 | 2.297 | Indirect | nan |
| 18212744 | Triángulo | 0.168 | 1.148 | Redundant | 18874884 |
| 18878216 | Colón | 0.168 | 1.253 | Redundant | 18840241 |
| 18735457 | Triángulo | 0.17 | 1.76 | Redundant | 18212716 |
| 18796241 | CTTSA | 0.171 | 1.585 | Redundant | 18709005 |
| 18864539 | Satélite | 0.173 | 1.538 | Redundant | 18212712 |
| 18722171 | Ala de Oro | 0.173 | 1.668 | Redundant | 18732705 |
| 18704854 | Flecha Blanca | 0.173 | 1.597 | Redundant | 18289706 |
| 18796372 | Pegaso | 0.173 | 1.396 | Redundant | 18796407 |
| 18709052 | Flecha Blanca | 0.173 | 1.595 | Redundant | 18289706 |
| 18709057 | Flecha Blanca | 0.174 | 1.732 | Redundant | 18782084 |
| 18291951 | Flecha Blanca | 0.174 | 2.331 | Redundant | 18708963 |
| 19369474 | TBD | 0.174 | 1.475 | Low demand | nan |
| 18212752 | Triángulo | 0.174 | 1.138 | Redundant | 18874884 |
| 18736622 | ATSUZI | 0.174 | 1.163 | Low demand | nan |
| 18178778 | Triángulo | 0.174 | 1.436 | Redundant | 18212712 |
| 18827306 | 8 de Noviembre | 0.175 | 1.257 | Low demand | nan |
| 18796407 | Pegaso | 0.175 | 1.366 | Low demand | nan |
| 18869183 | TEO | 0.175 | 1.693 | Redundant | 18874884 |
| 18765988 | Triángulo | 0.176 | 1.608 | Redundant | 18765996 |
| 18718069 | Ala de Oro | 0.176 | 1.672 | Redundant | 18732705 |
| 18766381 | Temoayenses | 0.177 | 1.724 | Redundant | 18782084 |
| 18874884 | TEO | 0.177 | 1.663 | Indirect | nan |
| 18291959 | Flecha Blanca | 0.178 | 1.78 | Redundant | 18782084 |
| 18291998 | Flecha Blanca | 0.179 | 1.703 | Redundant | 18709005 |
| 18796291 | INTER | 0.179 | 1.752 | Redundant | 18796294 |
| 18782084 | Temoayenses | 0.179 | 1.593 | Indirect | nan |
| 18874474 | Primero de Mayo | 0.179 | 2.126 | Redundant | 18869328 |
| 18739425 | Triángulo | 0.179 | 1.452 | Redundant | 18212736 |
| 18796308 | CTTSA | 0.18 | 1.719 | Redundant | 18823412 |
| 18769725 | Xinantécatl | 0.18 | 1.379 | Redundant | 18769885 |
| 19072412 | TBD | 0.18 | 1.469 | Low demand | nan |
| 18840226 | S T U T | 0.181 | 1.645 | Redundant | 18840241 |
| 18796327 | Rápidos | 0.181 | 1.634 | Redundant | 18823515 |
| 18839402 | S T U T | 0.182 | 1.552 | Redundant | 18839451 |
| 18825516 | 8 de Noviembre | 0.182 | 1.416 | Redundant | 18825302 |
| 18769885 | Xinantécatl | 0.182 | 1.339 | Low demand | nan |
| 18796244 | CTTSA | 0.182 | 1.594 | Redundant | 18709005 |
| 18878126 | Tollocan | 0.182 | 1.461 | Redundant | 18870107 |
| 18736934 | ATSUZI | 0.183 | 1.695 | Redundant | 18737003 |
| 19370079 | TBD | 0.184 | 1.337 | Redundant | 19369434 |
| 18839451 | S T U T | 0.184 | 1.574 | Indirect | nan |
| 18796312 | A U T | 0.186 | 1.37 | Redundant | 18796325 |
| 18825302 | 8 de Noviembre | 0.186 | 1.336 | Low demand | nan |
| 18840585 | S T U T | 0.186 | 1.842 | Redundant | 18840589 |
| 19369434 | TBD | 0.187 | 1.328 | Redundant | 18878117 |
| 18768395 | Xinantécatl | 0.188 | 1.451 | Redundant | 18768324 |
| 18709218 | Ala de Oro | 0.188 | 1.199 | Redundant | 18878117 |
| 18796325 | A U T | 0.189 | 1.389 | Low demand | nan |
| 18823412 | CTTSA | 0.189 | 1.636 | Indirect | nan |
| 18737003 | ATSUZI | 0.189 | 1.725 | Indirect | nan |
| 18794052 | Crucero | 0.189 | 1.49 | Redundant | 18736642 |
| 18840589 | S T U T | 0.189 | 1.853 | Indirect | nan |
| 18765996 | Triángulo | 0.189 | 1.453 | Low demand | nan |
| 18718067 | Ala de Oro | 0.19 | 1.182 | Redundant | 18878117 |
| 18878134 | Tollocan | 0.19 | 1.985 | Indirect | nan |
| 18823515 | Rápidos | 0.192 | 1.501 | Indirect | nan |
| 18870107 | Tollocan | 0.192 | 1.317 | Low demand | nan |
| 18212712 | Triángulo | 0.192 | 1.252 | Low demand | nan |
| 18840853 | S T U T | 0.192 | 1.487 | Redundant | 18840623 |
| 18840623 | S T U T | 0.193 | 1.477 | Low demand | nan |
| 18869328 | Primero de Mayo | 0.193 | 2.124 | Indirect | nan |
| 18840448 | S T U T | 0.194 | 1.473 | Redundant | 18796214 |
| 19369768 | TBD | 0.194 | 1.264 | Redundant | 19369540 |
| 19369540 | TBD | 0.195 | 1.279 | Low demand | nan |
| 18823464 | Pegaso | 0.196 | 1.323 | Redundant | 18819586 |
| 18266173 | Flecha Blanca | 0.197 | 1.785 | Redundant | 18266214 |
| 18878171 | Tollocan | 0.198 | 1.614 | Redundant | 18878183 |
| 18735466 | Triángulo | 0.198 | 1.441 | Redundant | 18212738 |
| 18819586 | Pegaso | 0.199 | 1.332 | Low demand | nan |
| 18766238 | Temoayenses | 0.199 | 1.088 | Redundant | 18878117 |
| 18766377 | Temoayenses | 0.199 | 1.087 | Redundant | 18878117 |
| 18765970 | Triángulo | 0.199 | 1.67 | Redundant | 18739571 |
| 19369467 | TBD | 0.2 | 1.613 | Redundant | 19369298 |
| 18739458 | Triángulo | 0.201 | 1.337 | Redundant | 18739396 |
| 19369298 | TBD | 0.201 | 1.585 | Indirect | nan |
| 18732706 | ATSUZI | 0.202 | 1.69 | Redundant | 18732705 |
| 18840241 | S T U T | 0.203 | 1.243 | Low demand | nan |
| 18708963 | Flecha Blanca | 0.203 | 1.862 | Redundant | 18266214 |
| 18291869 | Flecha Blanca | 0.204 | 1.251 | Redundant | 18768324 |
| 18796332 | TBD | 0.204 | 1.798 | Indirect | nan |
| 18709039 | Flecha Blanca | 0.205 | 1.232 | Redundant | 18292019 |
| 18878183 | Tollocan | 0.205 | 1.485 | Low demand | nan |
| 18739383 | Triángulo | 0.206 | 1.283 | Low demand | nan |
| 18796250 | INTER | 0.206 | 2.21 | Indirect | nan |
| 18796246 | R E D | 0.206 | 1.702 | Indirect | nan |
| 18878119 | Tollocan | 0.207 | 1.09 | Redundant | 18878117 |
| 18739571 | Triángulo | 0.208 | 1.536 | Indirect | nan |
| 18878117 | Tollocan | 0.208 | 1.081 | Low demand | nan |
| 18704787 | Flecha Blanca | 0.209 | 1.171 | Redundant | 18768324 |
| 18736642 | ATSUZI | 0.209 | 1.515 | Redundant | 18732705 |
| 18292019 | Flecha Blanca | 0.21 | 1.165 | Redundant | 18768324 |
| 18840463 | S T U T | 0.21 | 1.307 | Redundant | 18796226 |
| 18732705 | ATSUZI | 0.211 | 1.645 | Indirect | nan |
| 18836846 | S T U T | 0.211 | 2.121 | Redundant | 18869212 |
| 18768324 | Xinantécatl | 0.213 | 1.217 | Low demand | nan |
| 18796294 | INTER | 0.216 | 1.48 | Low demand | nan |
| 18840370 | Bicentenario | 0.218 | 2.053 | Indirect | nan |
| 18796214 | R E D | 0.218 | 1.254 | Redundant | 18796226 |
| 18869212 | S T U T | 0.219 | 1.855 | Indirect | nan |
| 18796233 | INTER | 0.219 | 1.918 | Indirect | nan |
| 18739396 | Triángulo | 0.22 | 1.193 | Low demand | nan |
| 19072413 | TBD | 0.22 | 1.376 | Low demand | nan |
| 19109532 | TBD | 0.222 | 1.999 | Indirect | nan |
| 18212736 | Triángulo | 0.222 | 1.291 | Redundant | 18212710 |
| 18289699 | Flecha Blanca | 0.222 | 1.304 | Redundant | 18709005 |
| 18864927 | Primero de Mayo | 0.223 | 1.37 | Redundant | 18853746 |
| 18796226 | R E D | 0.223 | 1.277 | Low demand | nan |
| 18289706 | Flecha Blanca | 0.223 | 1.294 | Redundant | 18709005 |
| 18739358 | Triángulo | 0.224 | 1.192 | Redundant | 18739378 |
| 18266214 | Flecha Blanca | 0.224 | 1.423 | Low demand | nan |
| 18736621 | ATSUZI | 0.225 | 1.401 | Redundant | 18736662 |
| 18739378 | Triángulo | 0.226 | 1.122 | Low demand | nan |
| 18736703 | ATSUZI | 0.226 | 1.355 | Low demand | nan |
| 18212710 | Triángulo | 0.226 | 1.268 | Redundant | 18212738 |
| 18212738 | Triángulo | 0.228 | 1.15 | Low demand | nan |
| 18736662 | ATSUZI | 0.229 | 1.553 | Redundant | 18736672 |
| 18709005 | Flecha Blanca | 0.23 | 1.32 | Low demand | nan |
| 18212813 | Triángulo | 0.23 | 1.151 | Redundant | 18212846 |
| 18212716 | Triángulo | 0.23 | 1.107 | Low demand | nan |
| 18212846 | Triángulo | 0.232 | 1.153 | Low demand | nan |
| 18840877 | Primero de Mayo | 0.232 | 1.279 | Redundant | 18853746 |
| 18736640 | ATSUZI | 0.233 | 1.409 | Redundant | 18736672 |
| 18736672 | ATSUZI | 0.234 | 1.422 | Low demand | nan |
| 19109567 | TBD | 0.237 | 1.517 | Indirect | nan |
| 19072498 | TBD | 0.238 | 1.484 | Low demand | nan |
| 18796245 | Urbana | 0.243 | 1.785 | Indirect | nan |
| 18796247 | Urbana | 0.245 | 1.875 | Indirect | nan |
| 18869179 | Primero de Mayo | 0.25 | 1.347 | Redundant | 18853746 |
| 18840539 | Bicentenario | 0.252 | 1.572 | Indirect | nan |
| 18840916 | Primero de Mayo | 0.258 | 1.276 | Redundant | 18853746 |
| 18736690 | ATSUZI | 0.266 | 1.34 | Redundant | 18736694 |
| 18736694 | ATSUZI | 0.266 | 1.34 | Low demand | nan |
| 19369480 | TBD | 0.266 | 1.666 | Redundant | 18796201 |
| 19369475 | TBD | 0.269 | 1.573 | Redundant | 18796201 |
| 18796228 | Crucero | 0.271 | 1.624 | Redundant | 18796181 |
| 18796181 | Crucero | 0.271 | 1.611 | Indirect | nan |
| 19072448 | TBD | 0.282 | 2.062 | Redundant | 19345354 |
| 18840954 | Primero de Mayo | 0.283 | 1.182 | Redundant | 19369278 |
| 19369291 | TBD | 0.286 | 1.217 | Redundant | 19369278 |
| 18840950 | Primero de Mayo | 0.286 | 1.182 | Redundant | 19369278 |
| 19369278 | TBD | 0.287 | 1.213 | Low demand | nan |
| 19072410 | TBD | 0.296 | 1.209 | Low demand | nan |
| 19369503 | TBD | 0.3 | 1.164 | Redundant | 18494467 |
| 19369513 | TBD | 0.3 | 1.162 | Redundant | 18494467 |
| 18796215 | Crucero | 0.3 | 1.657 | Redundant | 18796201 |
| 19369489 | TBD | 0.301 | 1.457 | Redundant | 18739386 |
| 18796201 | Crucero | 0.302 | 1.684 | Indirect | nan |
| 19369492 | TBD | 0.303 | 1.446 | Redundant | 18739386 |
| 18739417 | Temoayenses | 0.305 | 1.396 | Redundant | 18739434 |
| 19369485 | TBD | 0.316 | 1.627 | Redundant | 18794003 |
| 18841338 | Primero de Mayo | 0.317 | 1.399 | Redundant | 18853746 |
| 18839607 | Crucero | 0.318 | 1.512 | Redundant | 18794003 |
| 18796176 | Crucero | 0.321 | 1.401 | Redundant | 18794003 |
| 19369488 | TBD | 0.321 | 1.475 | Redundant | 18794003 |
| 18268120 | Estrella | 0.323 | 1.206 | Redundant | 18494467 |
| 19369491 | TBD | 0.324 | 1.401 | Redundant | 18794003 |
| 19369514 | TBD | 0.324 | 1.419 | Redundant | 19369516 |
| 18793997 | Crucero | 0.328 | 1.407 | Redundant | 18794003 |
| 19370082 | TBD | 0.329 | 1.361 | Redundant | 19369516 |
| 19369486 | TBD | 0.33 | 1.433 | Redundant | 19369478 |
| 19369479 | TBD | 0.33 | 1.318 | Redundant | 18794003 |
| 19369473 | TBD | 0.332 | 1.789 | Redundant | 19369453 |
| 19369453 | TBD | 0.333 | 1.79 | Indirect | nan |
| 19369465 | TBD | 0.349 | 1.233 | Redundant | 19369544 |
| 18739441 | Temoayenses | 0.356 | 1.2 | Redundant | 18739386 |
| 19369476 | TBD | 0.364 | 1.31 | Redundant | 19369478 |
| 19369508 | TBD | 0.385 | 1.745 | Redundant | 19369516 |
| 19369516 | TBD | 0.386 | 1.722 | Indirect | nan |
| 18840953 | Primero de Mayo | 0.487 | 1.315 | Redundant | 18841007 |

## Method

1. GTFS route geometries from shapes.txt (EPSG:6372); straight_line_km = hull diameter.
2. Served AGEBs: centroid within 400m of route (geopandas sjoin).
3. W5 objective (f1 demand-gain, f2 length, f3 equity) + constraints (detour<=1.8, spacing 300-1000m, demand>=500/day, km<=30) + Pareto rank.
4. Flags: Low demand (f1<0.2 & score<0.3), Indirect (detour>1.5), Redundant (served-AGEB Jaccard>=0.60 with a higher-scoring route).