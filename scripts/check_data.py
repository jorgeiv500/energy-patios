#!/usr/bin/env python3
"""Lightweight data audit for the reproducibility package."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PROCESSED_EXPECTED = (
    "data/processed/assignment_validation_summary.csv",
    "data/processed/depot_hour_demand.csv",
    "data/processed/depot_parameters.csv",
    "data/processed/depot_route_hour_profile.csv",
    "data/processed/electric_depots.geojson",
    "data/processed/operator_zone_depot_assignment.csv",
    "data/processed/price_emission_hourly.csv",
    "data/processed/roof_potential_by_depot.csv",
    "data/processed/route_depot_assignment.csv",
    "data/processed/scenario_parameters.csv",
)

REFERENCE_EXPECTED = (
    "results/tables/full_depot_dispatch_local_appsi_highs_optimized_all_all_all.csv",
    "results/tables/full_depot_dispatch_local_appsi_highs_technical_S0-S1-S2-S3-S4-S6_R0-R1-R2-R3-R4-R5_all.csv",
    "results/tables/full_depot_dispatch_neos_cplex_optimized_S8_R3_PZ050.csv",
    "results/tables/full_scenario_summary_local_appsi_highs_optimized_all_all_all.csv",
    "results/tables/full_scenario_summary_local_appsi_highs_technical_S0-S1-S2-S3-S4-S6_R0-R1-R2-R3-R4-R5_all.csv",
    "results/tables/full_scenario_summary_neos_cplex_optimized_S8_R3_PZ050.csv",
)

RAW_EXPECTED = (
    "data/raw/transmilenio/gtfs_static/GTFS-2026-04-29.zip",
    "data/raw/transmilenio/patios/patios_sitp.geojson",
    "data/raw/transmilenio/patios/patios_sitp.csv",
    "data/raw/transmilenio/flota/flota_vinculada_20260504.csv",
    "data/raw/transmilenio/flota/diccionario_flota_vinculada_sitp.xlsx",
    "data/raw/transmilenio/validaciones/validacion_troncal_marzo_2026.xlsx",
    "data/raw/transmilenio/validaciones/validacion_zonal_marzo_2026.xlsx",
    "data/raw/transmilenio/salidas/salidas_15min_abril_2026.xlsx",
    "data/raw/ideca/construccion_bogota_2026_03_gpkg.zip",
    "data/raw/solar/nasa_power_bogota_hourly_2025.csv",
    "data/raw/pvgis/pvgis_bogota_pv_1kw_2020.json",
    "data/raw/xm/precio_bolsa_nacional_2025.csv",
    "data/raw/xm/precio_bolsa_nacional_2026_jan_may04.csv",
    "data/raw/upme/soporte_calculo_factor_emision_2024_upme.pdf",
    "data/raw/upme/resolucion_upme_1198_2024.html",
    "data/raw/icct/charging_infrastructure_zero_emission_buses_bogota_2023.pdf",
    "data/raw/enel/enel_bogota_electric_mobility_2024.html",
    "data/raw/enel/enelx_patios_ebuses_bogota.html",
    "data/raw/enel/enelx_172_buses_quinto_patio.html",
    "data/raw/andesco/enel_codensa_401_buses_dos_patios.html",
    "data/raw/mgm/patio_electrico_green_movil.html",
    "data/raw/transmilenio/technical/parametros_tecnicos_patio_carboquimica.pdf",
    "data/raw/unep/documento_pnuma_transporte_electrico_2022.pdf",
    "data/raw/wri_tumi/transporte_publico_ciudades_sostenibles_2024.pdf",
    "data/raw/irena/irena_renewable_power_generation_costs_2023_executive_summary.pdf",
)


def size_label(path: Path) -> str:
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.reader(handle)) - 1


def count_geojson_features(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    features = data.get("features", [])
    return len(features) if isinstance(features, list) else 0


def audit_expected(paths: tuple[str, ...], label: str) -> bool:
    print(f"\n[{label}]")
    ok = True
    for rel in paths:
        path = ROOT / rel
        if path.exists() and path.stat().st_size > 0:
            detail = size_label(path)
            if path.suffix.lower() == ".csv":
                detail += f", {count_csv_rows(path)} rows"
            elif path.suffix.lower() == ".geojson":
                detail += f", {count_geojson_features(path)} features"
            print(f"OK      {rel}  {detail}")
        else:
            print(f"MISSING {rel}")
            ok = False
    return ok


def inspect_gtfs() -> None:
    path = ROOT / "data/raw/transmilenio/gtfs_static/GTFS-2026-04-29.zip"
    if not path.exists():
        return
    with zipfile.ZipFile(path) as zf:
        names = sorted(zf.namelist())
    print("GTFS files:", ", ".join(names[:20]))


def inspect_tables() -> None:
    for rel in (
        "data/raw/transmilenio/patios/patios_sitp.csv",
        "data/raw/transmilenio/flota/flota_vinculada_20260504.csv",
        "data/raw/xm/precio_bolsa_nacional_2025.csv",
        "data/raw/xm/precio_bolsa_nacional_2026_jan_may04.csv",
    ):
        path = ROOT / rel
        if path.exists():
            print(f"ROWS    {rel}  {count_csv_rows(path)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw",
        action="store_true",
        help="also audit optional third-party raw files used to rebuild processed inputs",
    )
    args = parser.parse_args()

    ok = True
    ok &= audit_expected(PROCESSED_EXPECTED, "included processed inputs")
    ok &= audit_expected(REFERENCE_EXPECTED, "included reference outputs")

    if args.raw:
        ok &= audit_expected(RAW_EXPECTED, "optional raw reconstruction sources")
        inspect_gtfs()
        inspect_tables()

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
