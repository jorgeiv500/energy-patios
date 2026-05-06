# Energy Patios Bogota

Proyecto reproducible para estudiar la optimizacion de carga de buses electricos, PV en cubiertas y almacenamiento bajo restricciones de capacidad de red en patios del SITP/TransMilenio en Bogota.

El objetivo cientifico es preparar un articulo para Elsevier Energy:

> Rooftop-aware optimization of electric bus depot charging, photovoltaic generation, and battery storage under grid-capacity constraints: Evidence from Bogota's large-scale e-bus system

## Alcance Del Repositorio

Este repositorio contiene solo el paquete necesario para reproducir el experimento: codigo, configuracion, datos procesados ligeros, salidas CSV de referencia y documentacion minima de datos/metodo. El manuscrito, figuras editoriales, archivos de submission, notas de revision y datos crudos de terceros no se versionan en GitHub.

## Estructura

- `CITATION.cff`: metadatos de citacion para GitHub y el DOI archivado.
- `.zenodo.json`: metadatos para archivar un release de GitHub en Zenodo.
- `REPRODUCIBILITY.md`: instrucciones de reproduccion, publicacion en GitHub y DOI.
- `data/processed/`: datos procesados ligeros requeridos para correr el experimento.
- `docs/`: inventario de datos, diseno experimental, metodo de asignacion ruta-patio y protocolo de solver.
- `scripts/`: descargas, chequeos, construccion de insumos y ejecucion experimental.
- `src/`: codigo de preprocesamiento, modelos y experimentos.
- `results/tables/`: salidas CSV de referencia para verificar la reproduccion.

## Datos base ya incorporados

- Datos procesados de demanda depot-hora, parametros de patios, escenarios, precios/emisiones, potencial PV por depot y asignacion ruta-patio.
- Salidas CSV centrales de la matriz optimizada y sensibilidades tecnicas.
- Los datos crudos de terceros se documentan en `docs/data_inventory.md`, pero no se redistribuyen aqui.

## Repositorio reproducible y DOI

El paquete reproducible esta publicado en GitHub y archivado con DOI:

- GitHub: `https://github.com/jorgeiv500/energy-patios`
- Release: `v1.0.0-energy-submission`
- Zenodo record: `https://zenodo.org/records/20045572`
- DOI versionado: `https://doi.org/10.5281/zenodo.20045572`
- DOI de concepto para todas las versiones: `https://doi.org/10.5281/zenodo.20045571`

La ruta editorial recomendada para futuras versiones sigue siendo GitHub + DOI archivado:

1. Publicar este proyecto como repositorio GitHub, por ejemplo `https://github.com/jorgeiv500/energy-patios`.
2. Crear un release `v1.0.0-energy-submission`.
3. Archivar ese release en Zenodo o Mendeley Data para obtener un DOI persistente.
4. Registrar el DOI en `CITATION.cff` y en la declaracion de disponibilidad de datos del manuscrito local.

GitHub debe funcionar como repositorio operativo; Zenodo o Mendeley Data debe funcionar como snapshot citable de la version exacta usada en el articulo.

## Flujo recomendado

1. Ejecutar `python scripts/check_data.py` para auditar los insumos procesados y las salidas de referencia incluidas.
2. Usar los insumos ligeros ya incluidos en `data/processed/`, o reconstruirlos desde datos crudos locales con `scripts/build_experiment_inputs.py` si se descargan las fuentes originales.
3. Correr la matriz experimental con `scripts/run_full_experiment.py`.
4. Comparar las salidas generadas con los CSV de referencia en `results/tables/`.

## Experimento multi-patio

Construir insumos procesados:

```bash
python scripts/build_experiment_inputs.py
```

Este paso es opcional para quien solo quiera reproducir el experimento ya procesado. La construccion de insumos usa flota electrica por operador-zona, asignacion zona-patio con confianza documentada y perfiles operador-ruta-hora desde validaciones SITP. La metodologia queda auditada en `docs/route_depot_assignment_method.md` y en las tablas `data/processed/operator_zone_depot_assignment.csv`, `data/processed/route_depot_assignment.csv`, `data/processed/depot_route_hour_profile.csv` y `data/processed/assignment_validation_summary.csv`.

Ejecutar la matriz completa optimizada S0-S9/R0-R5 sobre todos los patios electricos:

```bash
python scripts/run_full_experiment.py --solver appsi_highs --capacity-mode optimized
```

Ejecutar una sensibilidad tecnica, forzando la capacidad maxima de cada escenario:

```bash
python scripts/run_full_experiment.py --solver appsi_highs --capacity-mode technical --scenario S0,S1,S2,S3,S4,S6 --roof R0,R1,R2,R3,R4,R5
```

Para NEOS/CPLEX conviene correr subconjuntos:

```bash
NEOS_EMAIL=your_email@example.com python scripts/run_full_experiment.py --solver-manager neos --solver cplex --scenario S8 --roof R3 --depot PZ050
```

## Reinstalacion de dependencias

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Descarga reproducible

```bash
python scripts/download_data.py
```

El script descarga fuentes crudas publicas necesarias para reconstruir insumos, no archivos editoriales ni del manuscrito. Por defecto no reemplaza archivos existentes. Use `--force` para redescargar. Para auditar tambien las fuentes crudas locales:

```bash
python scripts/check_data.py --raw
```
