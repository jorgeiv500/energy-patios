#!/usr/bin/env python3
"""Download raw data used by the Energy Patios Bogota project."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import requests


ROOT = Path(__file__).resolve().parents[1]

FILES: tuple[tuple[str, str], ...] = (
    (
        "data/raw/transmilenio/gtfs_static/GTFS-2026-04-29.zip",
        "https://storage.googleapis.com/gtfs-estaticos/GTFS-2026-04-29.zip",
    ),
    (
        "data/raw/transmilenio/patios/patios_sitp.geojson",
        "https://datosabiertos-transmilenio.hub.arcgis.com/api/download/v1/items/1176a253e63a4de8a33332195a5d7b92/geojson?layers=1",
    ),
    (
        "data/raw/transmilenio/patios/patios_sitp.csv",
        "https://datosabiertos-transmilenio.hub.arcgis.com/api/download/v1/items/1176a253e63a4de8a33332195a5d7b92/csv?layers=1",
    ),
    (
        "data/raw/transmilenio/flota/flota_vinculada_20260504.csv",
        "https://storage.googleapis.com/validaciones_tmsa/FlotaVinculada/flota_vinculada_20260504-000000000000.csv",
    ),
    (
        "data/raw/transmilenio/flota/diccionario_flota_vinculada_sitp.xlsx",
        "https://datosabiertos.bogota.gov.co/dataset/7fb3cb57-761a-4f6b-8a25-99e6de9e1672/resource/351b5efe-0e94-40ba-b407-010700d8bf6a/download/diccionario-de-datos-flota-vinculada-sitp.xlsx",
    ),
    (
        "data/raw/transmilenio/validaciones/validacion_troncal_marzo_2026.xlsx",
        "https://storage.googleapis.com/validaciones_tmsa/ValidacionTroncal/2026/03%20TM%20Resumen%20de%20Validaciones%20Troncales%20al%2031%20de%20Marzo%20del%202026%20Intervalo%2015%20Mint.xlsx",
    ),
    (
        "data/raw/transmilenio/validaciones/validacion_zonal_marzo_2026.xlsx",
        "https://storage.googleapis.com/validaciones_tmsa/ValidacionZonal/2026/03%20TM%20Reporte%20de%20Validaciones%20Zonales%20Intervalo%20al%2031%20de%20Marzo%20del%202026.xlsx",
    ),
    (
        "data/raw/transmilenio/salidas/salidas_15min_abril_2026.xlsx",
        "https://storage.googleapis.com/validaciones_tmsa/Salidas/2026/Resumen_Salidas_Cada_15_minutos_Abril_2026.xlsx",
    ),
    (
        "data/raw/ideca/construccion_bogota_2026_03_gpkg.zip",
        "https://datosabiertos.bogota.gov.co/dataset/397ccbd8-e2c5-4700-b90e-b68d101ab0c5/resource/2e619105-f07a-45c9-944b-ecc8ee206ef1/download/const.gpkg.0326.zip",
    ),
    (
        "data/raw/solar/nasa_power_bogota_hourly_2025.csv",
        "https://power.larc.nasa.gov/api/temporal/hourly/point?parameters=ALLSKY_SFC_SW_DWN,T2M,WS10M&community=RE&longitude=-74.10&latitude=4.65&start=20250101&end=20251231&format=CSV&time-standard=LST",
    ),
    (
        "data/raw/pvgis/pvgis_bogota_pv_1kw_2020.json",
        "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc?lat=4.65&lon=-74.10&startyear=2020&endyear=2020&pvcalculation=1&peakpower=1&loss=14&outputformat=json",
    ),
    (
        "data/raw/upme/soporte_calculo_factor_emision_2024_upme.pdf",
        "https://docs.upme.gov.co/Normatividad/Soporte_calculo_Factor_de_Emision_2024.pdf",
    ),
    (
        "data/raw/icct/charging_infrastructure_zero_emission_buses_bogota_2023.pdf",
        "https://theicct.org/wp-content/uploads/2023/12/ID-53-%E2%80%93-Zero-emission-buses-in-Colombia_final.pdf",
    ),
    (
        "data/raw/enel/enel_bogota_electric_mobility_2024.html",
        "https://www.enelamericas.com/es/historias/a202411-movilidad-electrica-en-bogota-un-futuro-sostenible.html",
    ),
)


def stream_download(url: str, target: Path, force: bool = False) -> None:
    if target.exists() and target.stat().st_size > 0 and not force:
        print(f"skip {target.relative_to(ROOT)}")
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with tmp.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    tmp.replace(target)
    print(f"downloaded {target.relative_to(ROOT)}")


def download_files(files: Iterable[tuple[str, str]], force: bool) -> None:
    for rel_path, url in files:
        stream_download(url, ROOT / rel_path, force=force)


def download_xm(force: bool) -> None:
    try:
        from pydataxm.pydataxm import ReadDB
    except ImportError:
        print("skip XM: install pydataxm first")
        return

    out = ROOT / "data/raw/xm"
    out.mkdir(parents=True, exist_ok=True)
    jobs = (
        ("2025-01-01", "2025-12-31", "precio_bolsa_nacional_2025.csv"),
        ("2026-01-01", "2026-05-04", "precio_bolsa_nacional_2026_jan_may04.csv"),
    )
    client = ReadDB()
    for start, end, name in jobs:
        target = out / name
        if target.exists() and target.stat().st_size > 0 and not force:
            print(f"skip {target.relative_to(ROOT)}")
            continue
        df = client.request_data("PrecBolsNaci", "Sistema", start, end)
        df.to_csv(target, index=False)
        print(f"downloaded {target.relative_to(ROOT)} {df.shape}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="replace existing files")
    parser.add_argument("--skip-large", action="store_true", help="skip IDECA construction zip")
    parser.add_argument("--skip-xm", action="store_true", help="skip XM/SIMEM download")
    args = parser.parse_args()

    files = FILES
    if args.skip_large:
        files = tuple(item for item in FILES if "construccion_bogota" not in item[0])

    download_files(files, force=args.force)
    if not args.skip_xm:
        download_xm(force=args.force)


if __name__ == "__main__":
    main()
