#!/usr/bin/env python3
"""Build processed input tables for the depot energy experiments."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from energy_patios.scenarios import OPERATIONAL_SCENARIOS, ROOF_SCENARIOS, scenario_matrix  # noqa: E402


PROJECTED_CRS = "EPSG:9377"
POWER_DENSITY_KWP_PER_M2 = 0.20
CHARGER_KW = 150.0
CHARGERS_PER_BUS_PROXY = 503.0 / 1470.0
COP_PER_USD = 4000.0
CAPITAL_RECOVERY_FACTOR = 0.10


def normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.upper().split())


def operator_family(value: object) -> str:
    text = normalize_text(value)
    text = re.sub(r"^\(\d+\)\s*", "", text)
    text = text.replace(".", "").replace(",", "")
    if "MUEVE USME" in text:
        return "MUEVE USME"
    if "ZMO FONTIBON V" in text:
        return "ZMO FONTIBON V"
    if "ZMO FONTIBON III" in text:
        return "ZMO FONTIBON III"
    if "MUEVE FONTIBON" in text:
        return "MUEVE FONTIBON"
    if "E-SOMOS ALIMENTACION" in text or "E SOMOS ALIMENTACION" in text:
        return "E SOMOS ALIMENTACION"
    if "E-SOMOS FONTIBON" in text or "E SOMOS FONTIBON" in text:
        return "E SOMOS FONTIBON"
    if "GRAN AMERICAS FONTIBON" in text:
        return "GRAN AMERICAS FONTIBON"
    if "ESTE ES MI BUS" in text:
        return "ESTE ES MI BUS"
    if "OPERADORA DISTRITAL" in text:
        return "OPERADORA DISTRITAL DE TRANSPORTE"
    if "ETIB" in text or "EMPRESA DE TRANSPORTE INTEGRADO" in text:
        return "ETIB"
    if "MASIVO CAPITAL" in text:
        return "MASIVO CAPITAL"
    if "CONSORCIO EXPRESS" in text:
        return "CONSORCIO EXPRESS"
    if "SUMA" in text:
        return "SUMA"
    if "GMOVIL" in text or "G MOVIL" in text:
        return "GMOVIL"
    if "EMASIVO 16" in text:
        return "EMASIVO 16"
    if "EMASIVO 10" in text:
        return "EMASIVO 10"
    if "GRAN AMERICAS USME" in text:
        return "GRAN AMERICAS USME"
    return text


def zone_depot_rule(zone: object, op_family: object) -> tuple[str, str, str]:
    zone_norm = normalize_text(zone)
    op_norm = normalize_text(op_family)
    if "SUBA CENTRO I" in zone_norm:
        return "PZ001", "zone_name_to_las_mercedes", "high"
    if "PERDOMO I" in zone_norm and "PERDOMO II" not in zone_norm:
        return "PZ006", "zone_name_to_perdomo_i", "high"
    if "PERDOMO II" in zone_norm:
        return "PZ052", "zone_name_to_perdomo", "high"
    if "USME I" in zone_norm and "USME II" not in zone_norm:
        return "PZ041", "zone_name_to_usme", "high"
    if "USME II" in zone_norm:
        return "PZ050", "zone_name_to_usme_ii", "high"
    if zone_norm.startswith("FONTIBON V"):
        return "PZ048", "fontibon_v_to_venecia_ii_proxy", "medium"
    if zone_norm.startswith("FONTIBON IV"):
        return "PZ047", "fontibon_iv_to_venecia_proxy", "medium"
    if zone_norm.startswith("FONTIBON III"):
        return "PZ049", "public_anchor_fontibon_iii_escritorio_enelx", "high"
    if zone_norm.startswith("FONTIBON II"):
        return "PZ040", "fontibon_ii_to_aeropuerto_proxy", "medium"
    if zone_norm.startswith("FONTIBON I"):
        return "PZ039", "fontibon_i_to_el_refugio_proxy", "medium"
    if "BOSA" in zone_norm:
        return "PZ052", "nearest_southwest_electric_depot_proxy", "low"
    if "KENNEDY" in zone_norm or "MASIVO CAPITAL" in op_norm:
        return "PZ040", "nearest_western_electric_depot_proxy", "low"
    return "", "unassigned", "none"


def public_grid_anchor_kw(depot_id: str) -> float | None:
    if depot_id == "PZ049":
        return 13_600.0
    return None


def ensure_ideca_gpkg() -> Path:
    source = ROOT / "data" / "raw" / "ideca" / "construccion_bogota_2026_03_gpkg.zip"
    target = ROOT / "data" / "processed" / "ideca" / "CONST.gpkg"
    if target.exists() and target.stat().st_size > 0:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as zf:
        zf.extract("CONST.gpkg", target.parent)
    return target


def electric_fleet() -> pd.DataFrame:
    flota = pd.read_csv(ROOT / "data" / "raw" / "transmilenio" / "flota" / "flota_vinculada_20260504.csv")
    flota["combustible_norm"] = flota["combustible"].map(normalize_text)
    electric = flota[flota["combustible_norm"].eq("ELECTRICO")].copy()
    electric["operator_family"] = electric["concesionario_operacion"].map(operator_family)
    electric["zone_norm"] = electric["zona"].map(normalize_text)
    electric["km_day_proxy"] = electric.apply(bus_km_day_proxy, axis=1)
    electric["kwh_km_proxy"] = electric["descripcion_tipo"].map(bus_consumption_proxy)
    electric["daily_energy_kwh_proxy"] = electric["km_day_proxy"] * electric["kwh_km_proxy"]
    return electric


def bus_km_day_proxy(row: pd.Series) -> float:
    component = normalize_text(row.get("componente"))
    bus_type = normalize_text(row.get("descripcion_tipo"))
    if "TRONCAL" in component or "PADRON" in bus_type:
        return 230.0
    if "ALIMENT" in component:
        return 215.0
    return 190.0


def bus_consumption_proxy(value: object) -> float:
    bus_type = normalize_text(value)
    if "ARTICULADO" in bus_type:
        return 1.65
    if "PADRON" in bus_type:
        return 1.35
    if "80" in bus_type:
        return 1.20
    if "50" in bus_type:
        return 0.95
    return 1.10


def load_electric_depots() -> gpd.GeoDataFrame:
    patios = gpd.read_file(ROOT / "data" / "raw" / "transmilenio" / "patios" / "patios_sitp.geojson")
    patios["est_ener_norm"] = patios["est_ener"].map(normalize_text)
    mask = patios["est_ener_norm"].str.contains("ELECTRICO", na=False)
    electric = patios.loc[mask].copy()
    electric["cap_total"] = pd.to_numeric(electric["cap_total"], errors="coerce").fillna(0.0)
    electric["area_ha"] = pd.to_numeric(electric["area_ha"], errors="coerce").fillna(0.0)
    electric["latitud"] = pd.to_numeric(electric["latitud"], errors="coerce")
    electric["longitud"] = pd.to_numeric(electric["longitud"], errors="coerce")
    return electric


def build_operator_zone_depot_assignment(electric: gpd.GeoDataFrame, fleet: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        fleet.groupby(
            ["operator_family", "concesionario_operacion", "zone_norm", "zona", "componente"],
            dropna=False,
            as_index=False,
        )
        .agg(
            bus_count=("codigo_bus", "count"),
            daily_energy_kwh_base=("daily_energy_kwh_proxy", "sum"),
            km_day_proxy=("km_day_proxy", "mean"),
            kwh_km_proxy=("kwh_km_proxy", "mean"),
        )
        .sort_values(["zone_norm", "operator_family"])
    )

    rules = grouped.apply(lambda row: zone_depot_rule(row["zone_norm"], row["operator_family"]), axis=1)
    grouped[["depot_id", "assignment_method", "assignment_confidence"]] = pd.DataFrame(
        rules.tolist(), index=grouped.index
    )
    depot_lookup = electric[
        ["id_patio", "nom_patio", "servicio", "est_ener", "cap_total", "latitud", "longitud"]
    ].rename(
        columns={
            "id_patio": "depot_id",
            "nom_patio": "depot_name",
            "servicio": "depot_service",
            "est_ener": "energy_station_type",
            "cap_total": "capacity_buses_reported",
            "latitud": "lat",
            "longitud": "lon",
        }
    )
    grouped = grouped.merge(depot_lookup, on="depot_id", how="left")
    grouped["assignment_scope"] = "operator_zone_to_depot"
    grouped["source_note"] = (
        "Flota vinculada SITP pure-electric records grouped by operation concessionaire and zone; "
        "depot assigned using zone/depot names and public Fontibon III Enel X anchor where available."
    )
    return grouped


def build_depot_parameters(
    electric: gpd.GeoDataFrame,
    operator_zone_assignment: pd.DataFrame,
) -> pd.DataFrame:
    assigned = (
        operator_zone_assignment.groupby("depot_id", as_index=False)
        .agg(
            electric_bus_count_proxy=("bus_count", "sum"),
            daily_energy_kwh_base=("daily_energy_kwh_base", "sum"),
            assignment_confidence_min=("assignment_confidence", lambda values: ",".join(sorted(set(values)))),
        )
        .copy()
    )
    total_buses = max(float(assigned["electric_bus_count_proxy"].sum()), 1.0)

    rows = []
    for _, row in electric.sort_values("id_patio").iterrows():
        depot_id = row["id_patio"]
        assignment_row = assigned[assigned["depot_id"].eq(depot_id)]
        if assignment_row.empty:
            bus_count = 0.0
            daily_energy = 0.0
            confidence = "none"
        else:
            bus_count = float(assignment_row.iloc[0]["electric_bus_count_proxy"])
            daily_energy = float(assignment_row.iloc[0]["daily_energy_kwh_base"])
            confidence = assignment_row.iloc[0]["assignment_confidence_min"]

        charger_count = 0 if bus_count <= 0 else max(1, math.ceil(bus_count * CHARGERS_PER_BUS_PROXY))
        charger_cap_kw = charger_count * CHARGER_KW
        public_anchor = public_grid_anchor_kw(str(depot_id))
        grid_candidates = [daily_energy / 10.0, charger_cap_kw * 0.65]
        if public_anchor is not None:
            grid_candidates.append(public_anchor)
        grid_cap_kw = max(grid_candidates)
        bess_power_max = 0.0 if bus_count <= 0 else min(charger_cap_kw * 0.45, max(daily_energy / 5.0, 1.0))
        rows.append(
            {
                "depot_id": depot_id,
                "depot_name": row["nom_patio"],
                "service": row["servicio"],
                "energy_station_type": row["est_ener"],
                "lat": row["latitud"],
                "lon": row["longitud"],
                "area_ha": row["area_ha"],
                "capacity_buses_reported": row["cap_total"],
                "fleet_share_proxy": bus_count / total_buses,
                "electric_bus_count_proxy": bus_count,
                "daily_energy_kwh_base": daily_energy,
                "charger_count_proxy": charger_count,
                "charger_cap_kw": charger_cap_kw,
                "grid_cap_kw_base": grid_cap_kw,
                "grid_cap_kw_tight": grid_cap_kw * 0.45,
                "grid_cap_public_anchor_kw": public_anchor if public_anchor is not None else "",
                "bess_energy_cap_max_kwh": daily_energy * 0.35,
                "bess_power_cap_max_kw": bess_power_max,
                "assignment_confidence": confidence,
                "assignment_method": "operator_zone_depot_assignment_with_validation_route_profiles",
            }
        )
    return pd.DataFrame(rows)


def build_gtfs_service_profile() -> pd.DataFrame:
    gtfs_zip = ROOT / "data" / "raw" / "transmilenio" / "gtfs_static" / "GTFS-2026-04-29.zip"
    with zipfile.ZipFile(gtfs_zip) as zf:
        trips = pd.read_csv(zf.open("trips.txt"), usecols=["trip_id", "service_id"])
        calendar = pd.read_csv(zf.open("calendar.txt"))
        weekday_services = set(calendar.loc[calendar["monday"].eq(1), "service_id"].astype(str))
        trip_ids = set(trips.loc[trips["service_id"].astype(str).isin(weekday_services), "trip_id"].astype(str))
        first_departures = []
        for chunk in pd.read_csv(
            zf.open("stop_times.txt"),
            usecols=["trip_id", "departure_time", "stop_sequence"],
            chunksize=750_000,
        ):
            first = chunk[chunk["stop_sequence"].eq(1)]
            first = first[first["trip_id"].astype(str).isin(trip_ids)]
            first_departures.append(first[["departure_time"]])

    departures = pd.concat(first_departures, ignore_index=True)
    departures["hour"] = departures["departure_time"].map(parse_gtfs_hour)
    profile = departures.groupby("hour").size().reindex(range(24), fill_value=0).rename("service_departures")
    output = profile.reset_index()
    max_departures = max(float(output["service_departures"].max()), 1.0)
    output["service_intensity_index"] = output["service_departures"] / max_departures
    output["charge_allowed_proxy"] = output["hour"].map(default_charge_allowed) | output["service_intensity_index"].le(0.45)
    return output


def extract_gtfs_route_sets() -> tuple[set[str], set[str]]:
    gtfs_zip = ROOT / "data" / "raw" / "transmilenio" / "gtfs_static" / "GTFS-2026-04-29.zip"
    with zipfile.ZipFile(gtfs_zip) as zf:
        routes = pd.read_csv(zf.open("routes.txt"), dtype=str)
    route_ids = set(routes["route_id"].dropna().map(normalize_text))
    route_short_names = set(routes["route_short_name"].dropna().map(normalize_text))
    return route_ids, route_short_names


def route_code_from_label(value: object) -> str:
    text = normalize_text(value)
    match = re.match(r"^\(([^)]+)\)\s*", text)
    if match:
        return normalize_text(match.group(1))
    return text.split(" ", 1)[0] if text else ""


def route_label_without_code(value: object) -> str:
    text = normalize_text(value)
    return re.sub(r"^\([^)]+\)\s*", "", text).strip()


def parse_interval_hour(value: object) -> int | None:
    if pd.isna(value):
        return None
    if hasattr(value, "hour"):
        return int(value.hour) % 24
    text = str(value).strip()
    match = re.search(r"(\d{1,2}):", text)
    if match:
        return int(match.group(1)) % 24
    try:
        return int(float(text)) % 24
    except ValueError:
        return None


def load_validation_route_profiles() -> tuple[pd.DataFrame, pd.DataFrame]:
    path = ROOT / "data" / "raw" / "transmilenio" / "validaciones" / "validacion_zonal_marzo_2026.xlsx"
    validations = pd.read_excel(path, sheet_name="Resumen Operador Ruta Intervalo", header=6)
    date_columns = [
        column
        for column in validations.columns
        if not isinstance(column, str) and pd.Timestamp(column).weekday() < 5
    ]
    if not date_columns:
        raise RuntimeError("No weekday date columns found in validation workbook.")

    required = ["Operador", "Ruta Consolidada", "Intervalo"]
    validations = validations.dropna(subset=required).copy()
    validations["operator_family"] = validations["Operador"].map(operator_family)
    validations["route_code"] = validations["Ruta Consolidada"].map(route_code_from_label)
    validations["route_label"] = validations["Ruta Consolidada"].map(route_label_without_code)
    validations["hour"] = validations["Intervalo"].map(parse_interval_hour)
    validations = validations.dropna(subset=["hour"]).copy()
    validations["hour"] = validations["hour"].astype(int)
    validations["avg_validations"] = validations[date_columns].apply(pd.to_numeric, errors="coerce").mean(axis=1).fillna(0.0)

    route_hour = (
        validations.groupby(["operator_family", "route_code", "route_label", "hour"], as_index=False)[
            "avg_validations"
        ]
        .sum()
        .sort_values(["operator_family", "route_code", "hour"])
    )
    route_totals = (
        route_hour.groupby(["operator_family", "route_code", "route_label"], as_index=False)["avg_validations"]
        .sum()
        .rename(columns={"avg_validations": "route_total_validations"})
    )
    operator_totals = route_totals.groupby("operator_family")["route_total_validations"].transform("sum")
    route_totals["operator_total_validations"] = operator_totals
    operator_denominator = route_totals["operator_total_validations"].where(
        route_totals["operator_total_validations"].ne(0.0)
    )
    route_totals["route_share_operator"] = (
        route_totals["route_total_validations"] / operator_denominator
    ).fillna(0.0).astype(float)

    route_hour = route_hour.merge(route_totals, on=["operator_family", "route_code", "route_label"], how="left")
    route_denominator = route_hour["route_total_validations"].where(route_hour["route_total_validations"].ne(0.0))
    route_hour["route_hour_share"] = (route_hour["avg_validations"] / route_denominator).fillna(0.0).astype(float)

    route_ids, route_short_names = extract_gtfs_route_sets()
    route_totals["gtfs_route_id_match"] = route_totals["route_code"].isin(route_ids)
    route_totals["gtfs_short_name_match"] = route_totals["route_label"].isin(route_short_names) | route_totals[
        "route_code"
    ].isin(route_short_names)
    route_totals["gtfs_any_match"] = route_totals["gtfs_route_id_match"] | route_totals["gtfs_short_name_match"]
    return route_hour, route_totals


def default_operation_share(hour: int) -> float:
    weights = {
        4: 0.02,
        5: 0.04,
        6: 0.08,
        7: 0.10,
        8: 0.09,
        9: 0.06,
        10: 0.04,
        11: 0.04,
        12: 0.05,
        13: 0.05,
        14: 0.05,
        15: 0.06,
        16: 0.08,
        17: 0.10,
        18: 0.09,
        19: 0.06,
        20: 0.04,
        21: 0.03,
        22: 0.02,
    }
    total = sum(weights.values())
    return weights.get(hour, 0.0) / total


def build_route_depot_assignment(
    operator_zone_assignment: pd.DataFrame,
    route_totals: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    route_totals_by_operator = {
        operator: group.copy()
        for operator, group in route_totals.groupby("operator_family")
    }
    for _, assignment in operator_zone_assignment.iterrows():
        routes = route_totals_by_operator.get(str(assignment["operator_family"]), pd.DataFrame())
        if routes.empty:
            routes = pd.DataFrame(
                [
                    {
                        "operator_family": assignment["operator_family"],
                        "route_code": "UNMATCHED",
                        "route_label": "UNMATCHED",
                        "route_total_validations": 0.0,
                        "operator_total_validations": 0.0,
                        "route_share_operator": 1.0,
                        "gtfs_route_id_match": False,
                        "gtfs_short_name_match": False,
                        "gtfs_any_match": False,
                    }
                ]
            )
        for _, route in routes.iterrows():
            route_share = float(route["route_share_operator"])
            rows.append(
                {
                    "depot_id": assignment["depot_id"],
                    "depot_name": assignment["depot_name"],
                    "operator_family": assignment["operator_family"],
                    "concesionario_operacion": assignment["concesionario_operacion"],
                    "zone": assignment["zona"],
                    "zone_norm": assignment["zone_norm"],
                    "component": assignment["componente"],
                    "assignment_method": assignment["assignment_method"],
                    "assignment_confidence": assignment["assignment_confidence"],
                    "route_code": route["route_code"],
                    "route_label": route["route_label"],
                    "route_total_validations": route["route_total_validations"],
                    "operator_total_validations": route["operator_total_validations"],
                    "route_share_operator": route_share,
                    "route_bus_count_proxy": float(assignment["bus_count"]) * route_share,
                    "route_daily_energy_kwh_proxy": float(assignment["daily_energy_kwh_base"]) * route_share,
                    "gtfs_route_id_match": bool(route["gtfs_route_id_match"]),
                    "gtfs_short_name_match": bool(route["gtfs_short_name_match"]),
                    "gtfs_any_match": bool(route["gtfs_any_match"]),
                    "source_note": "Operator-route shares from March 2026 SITP zonal validation profiles.",
                }
            )
    return pd.DataFrame(rows)


def build_depot_route_hour_profile(
    route_assignments: pd.DataFrame,
    route_hour_profile: pd.DataFrame,
) -> pd.DataFrame:
    hour_lookup = {
        key: group.copy()
        for key, group in route_hour_profile.groupby(["operator_family", "route_code", "route_label"])
    }
    rows = []
    for _, assignment in route_assignments.iterrows():
        key = (assignment["operator_family"], assignment["route_code"], assignment["route_label"])
        hours = hour_lookup.get(key)
        if hours is None or hours.empty:
            iterable = [
                {
                    "hour": hour,
                    "avg_validations": 0.0,
                    "route_hour_share": default_operation_share(hour),
                    "hour_profile_source": "default_operation_profile_no_validation_match",
                }
                for hour in range(24)
            ]
        else:
            iterable = [
                {
                    "hour": int(hour_row["hour"]),
                    "avg_validations": float(hour_row["avg_validations"]),
                    "route_hour_share": float(hour_row["route_hour_share"]),
                    "hour_profile_source": "validation_operator_route_interval_profile",
                }
                for _, hour_row in hours.iterrows()
            ]
        for hour_row in iterable:
            hour_share = float(hour_row["route_hour_share"])
            rows.append(
                {
                    "depot_id": assignment["depot_id"],
                    "depot_name": assignment["depot_name"],
                    "operator_family": assignment["operator_family"],
                    "zone": assignment["zone"],
                    "component": assignment["component"],
                    "route_code": assignment["route_code"],
                    "route_label": assignment["route_label"],
                    "hour": int(hour_row["hour"]),
                    "route_hour_share": hour_share,
                    "route_avg_validations": float(hour_row["avg_validations"]),
                    "route_daily_energy_kwh_proxy": float(assignment["route_daily_energy_kwh_proxy"]),
                    "operation_energy_kwh_proxy": float(assignment["route_daily_energy_kwh_proxy"]) * hour_share,
                    "route_bus_count_proxy": float(assignment["route_bus_count_proxy"]),
                    "assignment_confidence": assignment["assignment_confidence"],
                    "gtfs_any_match": bool(assignment["gtfs_any_match"]),
                    "hour_profile_source": hour_row["hour_profile_source"],
                }
            )
    return pd.DataFrame(rows)


def build_assignment_validation_summary(
    *,
    fleet: pd.DataFrame,
    operator_zone_assignment: pd.DataFrame,
    route_assignments: pd.DataFrame,
    depot_route_hour_profile: pd.DataFrame,
    depots: pd.DataFrame,
) -> pd.DataFrame:
    assigned_buses = float(operator_zone_assignment["bus_count"].sum())
    confidence_bus_counts = (
        operator_zone_assignment.groupby("assignment_confidence")["bus_count"].sum().to_dict()
        if not operator_zone_assignment.empty
        else {}
    )
    gtfs_match_rate = (
        float(route_assignments["gtfs_any_match"].mean()) if not route_assignments.empty else 0.0
    )
    validation_profile_rate = (
        float(
            depot_route_hour_profile["hour_profile_source"]
            .eq("validation_operator_route_interval_profile")
            .mean()
        )
        if not depot_route_hour_profile.empty
        else 0.0
    )
    rows = [
        {
            "metric": "pure_electric_buses_source",
            "value": float(len(fleet)),
            "unit": "buses",
            "note": "Records with combustible == ELECTRICO in Flota vinculada SITP.",
        },
        {
            "metric": "assigned_electric_buses",
            "value": assigned_buses,
            "unit": "buses",
            "note": "Buses assigned through operator-zone to depot rules.",
        },
        {
            "metric": "assigned_daily_energy",
            "value": float(depots["daily_energy_kwh_base"].sum()),
            "unit": "kWh/day",
            "note": "Daily energy proxy after depot assignment.",
        },
        {
            "metric": "route_depot_assignment_rows",
            "value": float(len(route_assignments)),
            "unit": "rows",
            "note": "Operator-route shares expanded to assigned depots.",
        },
        {
            "metric": "gtfs_any_match_rate",
            "value": gtfs_match_rate,
            "unit": "share",
            "note": "Validation route rows matched to current GTFS route_id or route_short_name.",
        },
        {
            "metric": "validation_hour_profile_row_rate",
            "value": validation_profile_rate,
            "unit": "share",
            "note": "Depot-route-hour rows using validation profiles instead of fallback operation profile.",
        },
    ]
    for confidence, bus_count in sorted(confidence_bus_counts.items()):
        rows.append(
            {
                "metric": f"bus_count_assignment_confidence_{confidence}",
                "value": float(bus_count),
                "unit": "buses",
                "note": "Confidence from zone/depot mapping rule.",
            }
        )
    return pd.DataFrame(rows)


def parse_gtfs_hour(value: object) -> int:
    text = str(value)
    hour = int(text.split(":", 1)[0]) % 24
    return hour


def default_charge_allowed(hour: int) -> bool:
    return hour in {*range(0, 6), *range(10, 16), *range(18, 24)}


def unmanaged_weight(hour: int) -> float:
    weights = {
        0: 0.10,
        1: 0.10,
        2: 0.09,
        3: 0.08,
        4: 0.07,
        5: 0.04,
        18: 0.04,
        19: 0.08,
        20: 0.12,
        21: 0.13,
        22: 0.10,
        23: 0.05,
    }
    return weights.get(hour, 0.0)


def build_depot_hour_demand(depots: pd.DataFrame, depot_route_hour_profile: pd.DataFrame) -> pd.DataFrame:
    service_profile = (
        depot_route_hour_profile.groupby(["depot_id", "hour"], as_index=False)
        .agg(
            operation_energy_kwh_proxy=("operation_energy_kwh_proxy", "sum"),
            service_validations_proxy=("route_avg_validations", "sum"),
            route_count_proxy=("route_code", "nunique"),
            gtfs_matched_route_hour_rows=("gtfs_any_match", "sum"),
        )
        .copy()
    )
    rows = []
    for _, depot in depots.iterrows():
        depot_profile = service_profile[service_profile["depot_id"].eq(depot["depot_id"])].set_index("hour")
        max_operation = max(float(depot_profile["operation_energy_kwh_proxy"].max()) if not depot_profile.empty else 0.0, 1.0)
        for hour in range(24):
            if hour in depot_profile.index:
                hour_row = depot_profile.loc[hour]
                operation_energy = float(hour_row["operation_energy_kwh_proxy"])
                service_validations = float(hour_row["service_validations_proxy"])
                route_count = int(hour_row["route_count_proxy"])
                gtfs_rows = int(hour_row["gtfs_matched_route_hour_rows"])
            else:
                operation_energy = 0.0
                service_validations = 0.0
                route_count = 0
                gtfs_rows = 0
            service_intensity = operation_energy / max_operation
            rows.append(
                {
                    "depot_id": depot["depot_id"],
                    "hour": hour,
                    "daily_required_energy_kwh": depot["daily_energy_kwh_base"],
                    "unmanaged_demand_kwh": depot["daily_energy_kwh_base"] * unmanaged_weight(hour),
                    "charge_allowed": bool(default_charge_allowed(hour) or service_intensity <= 0.35),
                    "service_departures_system": 0,
                    "service_intensity_index": service_intensity,
                    "operation_energy_kwh_proxy": operation_energy,
                    "service_validations_proxy": service_validations,
                    "route_count_proxy": route_count,
                    "gtfs_matched_route_hour_rows": gtfs_rows,
                    "day_type": "weekday_proxy",
                    "demand_method": "operator_zone_route_validation_profile",
                }
            )
    return pd.DataFrame(rows)


def read_buildings_for_geometry(gpkg_path: Path, geometry_projected) -> gpd.GeoDataFrame:
    bbox = gpd.GeoSeries([geometry_projected], crs=PROJECTED_CRS).to_crs("EPSG:4326").total_bounds
    buildings = gpd.read_file(gpkg_path, bbox=tuple(bbox), columns=["CONCODIGO", "CONNPISOS", "geometry"])
    if buildings.empty:
        return buildings.to_crs(PROJECTED_CRS)
    return buildings.to_crs(PROJECTED_CRS)


def build_roof_potential(electric: gpd.GeoDataFrame, gpkg_path: Path) -> pd.DataFrame:
    electric_projected = electric.to_crs(PROJECTED_CRS)
    rows = []
    for _, depot in electric_projected.sort_values("id_patio").iterrows():
        print(f"processing rooftops for {depot['id_patio']} {depot['nom_patio']}")
        max_geometry = depot.geometry.buffer(2000)
        buildings = read_buildings_for_geometry(gpkg_path, max_geometry)
        if not buildings.empty:
            buildings = buildings[buildings.geometry.notna()].copy()
        depot_area_m2 = float(depot.geometry.area)
        carport_area_m2 = depot_area_m2 * 0.35
        for buffer_m in (0, 500, 1000, 2000):
            area_geometry = depot.geometry if buffer_m == 0 else depot.geometry.buffer(buffer_m)
            if buildings.empty:
                building_area_m2 = 0.0
                building_count = 0
            else:
                candidates = buildings[buildings.intersects(area_geometry)].copy()
                building_count = int(len(candidates))
                if candidates.empty:
                    building_area_m2 = 0.0
                else:
                    building_area_m2 = float(candidates.geometry.intersection(area_geometry).area.sum())

            internal_carport_m2 = carport_area_m2 if buffer_m == 0 else 0.0
            rows.append(
                {
                    "depot_id": depot["id_patio"],
                    "buffer_m": buffer_m,
                    "building_count": building_count,
                    "building_roof_area_m2": building_area_m2,
                    "internal_carport_area_m2": internal_carport_m2,
                    "pv_cap_conservative_kwp": building_area_m2 * 0.25 * POWER_DENSITY_KWP_PER_M2,
                    "pv_cap_medium_kwp": building_area_m2 * 0.40 * POWER_DENSITY_KWP_PER_M2,
                    "pv_cap_high_kwp": building_area_m2 * 0.55 * POWER_DENSITY_KWP_PER_M2,
                    "pv_cap_carport_kwp": (
                        building_area_m2 * 0.55 + internal_carport_m2 * 0.70
                    )
                    * POWER_DENSITY_KWP_PER_M2,
                    "roof_method": "ideca_building_footprints_intersected_with_depot_buffers",
                    "overlap_warning": "nearby_buffers_are_not_deduplicated_across_depots",
                }
            )
    return pd.DataFrame(rows)


def load_pvgis_profile() -> pd.DataFrame:
    path = ROOT / "data" / "raw" / "pvgis" / "pvgis_bogota_pv_1kw_2020.json"
    data = json.loads(path.read_text())
    hourly = pd.DataFrame(data["outputs"]["hourly"])
    hourly["timestamp"] = pd.to_datetime(hourly["time"], format="%Y%m%d:%H%M")
    hourly["hour"] = hourly["timestamp"].dt.hour
    profile = hourly.groupby("hour")["P"].mean().reindex(range(24), fill_value=0.0) / 1000.0
    return profile.rename("pv_kw_per_kwp").reset_index()


def load_xm_profile() -> pd.DataFrame:
    path = ROOT / "data" / "raw" / "xm" / "precio_bolsa_nacional_2025.csv"
    prices = pd.read_csv(path)
    records = []
    for hour in range(24):
        col = f"Values_Hour{hour + 1:02d}"
        for value in prices[col].dropna():
            records.append({"hour": hour, "price_cop_per_kwh": float(value)})
    return pd.DataFrame(records).groupby("hour", as_index=False)["price_cop_per_kwh"].mean()


def build_price_emission_hourly() -> pd.DataFrame:
    output = load_xm_profile().merge(load_pvgis_profile(), on="hour", how="left")
    output["price_high_cop_per_kwh"] = output["price_cop_per_kwh"] * 1.5
    output["emission_kg_per_kwh"] = 0.177
    output["emission_high_kg_per_kwh"] = 0.250
    output["source_note"] = "XM_2025_hourly_average_PVGIS_2020_hourly_average_UPME_2024_factor_sensitivity"
    return output


def build_scenario_parameters() -> pd.DataFrame:
    rows = []
    scenario_lookup = {scenario.code: scenario for scenario in OPERATIONAL_SCENARIOS}
    roof_lookup = {roof.code: roof for roof in ROOF_SCENARIOS}
    for scenario, roof in scenario_matrix():
        rows.append(
            {
                "scenario": scenario.code,
                "scenario_label": scenario.label,
                "roof_scenario": roof.code,
                "roof_label": roof.label,
                "smart_charging": scenario.smart_charging,
                "pv_enabled": scenario.pv,
                "bess_enabled": scenario.bess,
                "nearby_roofs": scenario.nearby_roofs,
                "constrained_grid": scenario.constrained_grid,
                "fleet_multiplier": 1.5 if scenario.fleet_growth else 1.0,
                "price_column": "price_high_cop_per_kwh" if scenario.high_price else "price_cop_per_kwh",
                "emission_column": "emission_high_kg_per_kwh" if scenario.high_emission_factor else "emission_kg_per_kwh",
                "grid_cap_column": "grid_cap_kw_tight" if scenario.constrained_grid else "grid_cap_kw_base",
                "roof_buffer_m": roof_buffer_for(roof.code),
                "roof_capacity_column": roof_capacity_column_for(roof.code),
                "demand_charge_cop_per_kw_day": 1000.0,
                "carbon_price_cop_per_kg": 400.0 if scenario.high_emission_factor else 0.0,
                "pv_capex_cop_per_kwp_day": dailyized_cost(758.0),
                "bess_energy_capex_cop_per_kwh_day": dailyized_cost(273.0),
                "bess_power_capex_cop_per_kw_day": dailyized_cost(120.0),
                "unserved_penalty_cop_per_kwh": 1_000_000.0,
            }
        )
    # Keep lookup variables referenced so static analyzers catch scenario changes.
    assert scenario_lookup and roof_lookup
    return pd.DataFrame(rows)


def roof_buffer_for(code: str) -> int:
    if code in {"R1", "R2", "R3"}:
        return 0
    if code == "R4":
        return 1000
    if code == "R5":
        return 2000
    return 0


def roof_capacity_column_for(code: str) -> str:
    return {
        "R0": "none",
        "R1": "pv_cap_conservative_kwp",
        "R2": "pv_cap_medium_kwp",
        "R3": "pv_cap_high_kwp",
        "R4": "pv_cap_medium_kwp",
        "R5": "pv_cap_high_kwp",
    }[code]


def dailyized_cost(capex_usd: float) -> float:
    return capex_usd * COP_PER_USD * CAPITAL_RECOVERY_FACTOR / 365.0


def write_outputs(
    *,
    depots: pd.DataFrame,
    depot_hour: pd.DataFrame,
    operator_zone_assignment: pd.DataFrame,
    route_assignment: pd.DataFrame,
    depot_route_hour_profile: pd.DataFrame,
    assignment_validation_summary: pd.DataFrame,
    roofs: pd.DataFrame,
    price_emission: pd.DataFrame,
    scenario_params: pd.DataFrame,
    electric_geo: gpd.GeoDataFrame,
) -> None:
    out = ROOT / "data" / "processed"
    out.mkdir(parents=True, exist_ok=True)
    depots.to_csv(out / "depot_parameters.csv", index=False)
    depot_hour.to_csv(out / "depot_hour_demand.csv", index=False)
    operator_zone_assignment.to_csv(out / "operator_zone_depot_assignment.csv", index=False)
    route_assignment.to_csv(out / "route_depot_assignment.csv", index=False)
    depot_route_hour_profile.to_csv(out / "depot_route_hour_profile.csv", index=False)
    assignment_validation_summary.to_csv(out / "assignment_validation_summary.csv", index=False)
    roofs.to_csv(out / "roof_potential_by_depot.csv", index=False)
    price_emission.to_csv(out / "price_emission_hourly.csv", index=False)
    scenario_params.to_csv(out / "scenario_parameters.csv", index=False)
    electric_geo.to_file(out / "electric_depots.geojson", driver="GeoJSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-roofs", action="store_true", help="Skip IDECA rooftop intersections.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    electric = load_electric_depots()
    fleet = electric_fleet()
    operator_zone_assignment = build_operator_zone_depot_assignment(electric, fleet)
    depots = build_depot_parameters(electric, operator_zone_assignment)
    route_hour_profile, route_totals = load_validation_route_profiles()
    route_assignment = build_route_depot_assignment(operator_zone_assignment, route_totals)
    depot_route_hour_profile = build_depot_route_hour_profile(route_assignment, route_hour_profile)
    depot_hour = build_depot_hour_demand(depots, depot_route_hour_profile)
    assignment_validation_summary = build_assignment_validation_summary(
        fleet=fleet,
        operator_zone_assignment=operator_zone_assignment,
        route_assignments=route_assignment,
        depot_route_hour_profile=depot_route_hour_profile,
        depots=depots,
    )
    if args.skip_roofs:
        roofs = pd.DataFrame(
            {
                "depot_id": depots["depot_id"].repeat(4).to_numpy(),
                "buffer_m": list((0, 500, 1000, 2000)) * len(depots),
                "building_count": 0,
                "building_roof_area_m2": 0.0,
                "internal_carport_area_m2": 0.0,
                "pv_cap_conservative_kwp": 0.0,
                "pv_cap_medium_kwp": 0.0,
                "pv_cap_high_kwp": 0.0,
                "pv_cap_carport_kwp": 0.0,
                "roof_method": "skipped",
                "overlap_warning": "skipped",
            }
        )
    else:
        roofs = build_roof_potential(electric, ensure_ideca_gpkg())
    price_emission = build_price_emission_hourly()
    scenario_params = build_scenario_parameters()
    write_outputs(
        depots=depots,
        depot_hour=depot_hour,
        operator_zone_assignment=operator_zone_assignment,
        route_assignment=route_assignment,
        depot_route_hour_profile=depot_route_hour_profile,
        assignment_validation_summary=assignment_validation_summary,
        roofs=roofs,
        price_emission=price_emission,
        scenario_params=scenario_params,
        electric_geo=electric,
    )
    print(f"electric depots: {len(depots)}")
    print(f"pure electric buses: {len(fleet)}")
    print(f"daily energy proxy kWh: {fleet['daily_energy_kwh_proxy'].sum():.1f}")
    print("wrote data/processed/depot_parameters.csv")
    print("wrote data/processed/depot_hour_demand.csv")
    print("wrote data/processed/operator_zone_depot_assignment.csv")
    print("wrote data/processed/route_depot_assignment.csv")
    print("wrote data/processed/depot_route_hour_profile.csv")
    print("wrote data/processed/assignment_validation_summary.csv")
    print("wrote data/processed/roof_potential_by_depot.csv")
    print("wrote data/processed/price_emission_hourly.csv")
    print("wrote data/processed/scenario_parameters.csv")


if __name__ == "__main__":
    main()
