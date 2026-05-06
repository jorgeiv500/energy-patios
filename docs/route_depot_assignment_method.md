# Route-depot assignment method

This document records the reproducible public-data method used to replace the previous capacity-only allocation of electric buses to depots.

## Objective

Estimate a defensible depot-hour charging demand table when no public bus-level assignment exists for:

- bus to depot;
- route to depot;
- block or duty to bus;
- observed SOC and charging events.

The method does not claim telemetry-level truth. It creates a transparent route-depot proxy that can be audited, improved, and reported with confidence flags.

## Public-source search result

A targeted search by depot did not locate additional public route-depot-bus assignment tables. The search covered TransMilenio, IDU, Secretaria Distrital de Planeacion, alternative indexed and non-indexed PDFs, blogs, press releases, and administrative documents. Available sources mostly describe depot construction, fleet arrivals, operating plans, efficient-kilometre records, manuals, or general infrastructure. The only located document with a specific route-by-depot table remains the Carboquimica technical support document.

This negative search result is part of the method. It justifies treating route-depot-bus assignment as a reproducible inference instead of as an observed input, and it prevents the paper from overclaiming data availability.

## Data used

| Source | Local file | Role |
| --- | --- | --- |
| Flota vinculada SITP | `data/raw/transmilenio/flota/flota_vinculada_20260504.csv` | Electric fleet by concessionaire, zone, component, vehicle type. |
| PATIOS SITP | `data/raw/transmilenio/patios/patios_sitp.geojson` | Electric depot IDs, names, geometry, reported capacity. |
| SITP validations | `data/raw/transmilenio/validaciones/validacion_zonal_marzo_2026.xlsx` | Weekday operator-route-interval activity profile. |
| GTFS static | `data/raw/transmilenio/gtfs_static/GTFS-2026-04-29.zip` | Route-code matching audit. |
| Enel X Fontibon III anchor | `data/raw/enel/enelx_172_buses_quinto_patio.html` | Public support for Fontibon III/Escritorio and 13.6 MVA grid-capacity anchor. |

## Algorithm

1. Filter `Flota vinculada SITP` to `combustible == ELECTRICO`.
2. Normalize concessionaire names into stable `operator_family` labels.
3. Group pure-electric fleet by `operator_family`, original concessionaire, `zona`, and `componente`.
4. Assign each operator-zone group to an electric depot using a documented rule and confidence level.
5. Estimate daily energy per group from bus-type kWh/km and daily-km proxies.
6. Read March 2026 zonal validations by operator, route, and 15-minute interval.
7. Aggregate validations to weekday average route-hour profiles.
8. Allocate each operator-zone depot energy to routes using the operator's route validation share.
9. Build depot-route-hour energy profiles using validation-derived route-hour shares.
10. Aggregate to `depot_hour_demand.csv`, including `charge_allowed` and `service_intensity_index`.

## Depot assignment rules

| Zone/operator evidence | Depot | Confidence | Rule |
| --- | --- | --- | --- |
| SUBA CENTRO I | PZ001 Las Mercedes | High | Zone name to depot. |
| PERDOMO I | PZ006 Perdomo I | High | Zone name to depot. |
| PERDOMO II | PZ052 Perdomo | High | Zone name to depot. |
| USME I | PZ041 Usme | High | Zone name to depot. |
| USME II | PZ050 Usme II | High | Zone name to depot. |
| FONTIBON III | PZ049 Escritorio IV | High | Public Enel X Fontibon III/Escritorio anchor. |
| FONTIBON I | PZ039 El Refugio | Medium | Fontibon-zone proxy. |
| FONTIBON II | PZ040 Aeropuerto | Medium | Fontibon-zone proxy. |
| FONTIBON IV | PZ047 Venecia | Medium | Fontibon-zone proxy. |
| FONTIBON V | PZ048 Venecia | Medium | Fontibon-zone proxy. |
| Bosa electric ETIB records | PZ052 Perdomo | Low | Nearest southwest electric-depot proxy. |
| Kennedy electric Masivo Capital record | PZ040 Aeropuerto | Low | Nearest western electric-depot proxy. |

## Generated audit tables

| Output | Meaning |
| --- | --- |
| `data/processed/operator_zone_depot_assignment.csv` | One row per electric operator-zone group assigned to a depot. |
| `data/processed/route_depot_assignment.csv` | Operator route shares expanded to assigned depots. |
| `data/processed/depot_route_hour_profile.csv` | Route-hour operational energy proxy by depot. |
| `data/processed/assignment_validation_summary.csv` | Aggregate checks: assigned buses, confidence counts, GTFS match rate, validation-profile coverage. |
| `data/processed/depot_hour_demand.csv` | Optimizer input table with daily energy, unmanaged charging, service intensity, and charging availability. |

## Current validation checks

- 1,517 pure-electric fleet records are assigned.
- 319,269.75 kWh/day of proxy bus energy is conserved after assignment.
- 854 buses are assigned with high-confidence rules, 631 with medium-confidence rules, and 32 with low-confidence rules.
- 311 route-depot assignment rows are generated.
- 77.17% of route assignment rows match the current GTFS by route ID or route short name.
- 100% of depot-route-hour rows use validation profiles rather than the fallback operation profile.

## Remaining limitation for the paper

The assignment is no longer a depot-capacity allocation. It is a reproducible public-data inference using operator-zone fleet records and validation profiles. It should still be described as a public-data assignment proxy because public data do not expose real bus-to-depot telemetry, route blocks, or actual charging events for all depots. To remove the proxy label, the study would need an official operator or TransMilenio table linking depot, bus ID, route, block or trip, and date of validity.
