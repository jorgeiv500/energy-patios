# Inventario de datos

Este inventario documenta las fuentes externas usadas para construir los insumos
procesados del experimento. Los archivos crudos no se redistribuyen en GitHub; el
paquete reproducible incluye las tablas ligeras derivadas en `data/processed/`.

| Fuente | Archivo local | Uso | Estado | Limitacion principal |
| --- | --- | --- | --- | --- |
| GTFS estatico SITP `2026-04-29` | `data/raw/transmilenio/gtfs_static/GTFS-2026-04-29.zip` | Viajes, rutas, horarios y distancias proxy | Descargado | No asigna por si solo todos los viajes a patio |
| Patios SITP | `data/raw/transmilenio/patios/patios_sitp.geojson` | Geometria y localizacion de patios | Descargado | Requiere auditoria de atributos y CRS |
| Patios SITP CSV | `data/raw/transmilenio/patios/patios_sitp.csv` | Tabla auxiliar de patios | Descargado | Puede diferir de GeoJSON |
| Flota vinculada SITP `2026-05-04` | `data/raw/transmilenio/flota/flota_vinculada_20260504.csv` | Tipo de bus, operador, tecnologia y escala | Descargado | Campos deben homologarse con patios/rutas |
| Diccionario flota | `data/raw/transmilenio/flota/diccionario_flota_vinculada_sitp.xlsx` | Definicion de columnas | Descargado | Formato Excel |
| Validacion troncal marzo 2026 | `data/raw/transmilenio/validaciones/validacion_troncal_marzo_2026.xlsx` | Perfil de demanda de pasajeros por franja | Descargado | No es carga energetica directa |
| Validacion zonal marzo 2026 | `data/raw/transmilenio/validaciones/validacion_zonal_marzo_2026.xlsx` | Perfil de demanda de pasajeros por franja | Descargado | No es carga energetica directa |
| Salidas abril 2026 | `data/raw/transmilenio/salidas/salidas_15min_abril_2026.xlsx` | Perfil operativo cada 15 minutos | Descargado | Requiere limpieza de hojas |
| Construcciones IDECA/Catastro 03.26 | `data/raw/ideca/construccion_bogota_2026_03_gpkg.zip` | Cubiertas proxy para potencial PV | Descargado | Archivo grande; requiere filtrado espacial |
| NASA POWER Bogota 2025 | `data/raw/solar/nasa_power_bogota_hourly_2025.csv` | Radiacion y temperatura horaria | Descargado | Punto unico para toda la ciudad |
| PVGIS Bogota 1 kW 2020 | `data/raw/pvgis/pvgis_bogota_pv_1kw_2020.json` | Produccion PV normalizada | Descargado | Serie historica de un ano base |
| XM precio bolsa 2025 | `data/raw/xm/precio_bolsa_nacional_2025.csv` | Senal horaria de costo | Descargado | Precio bolsa no equivale siempre a tarifa final del patio |
| XM precio bolsa 2026 | `data/raw/xm/precio_bolsa_nacional_2026_jan_may04.csv` | Senal horaria reciente de costo | Descargado | Cobertura hasta 2026-05-04 |
| UPME factor emision 2024 | `data/raw/upme/soporte_calculo_factor_emision_2024_upme.pdf` | Escenarios de emisiones | Descargado | Se debe extraer valor metodologicamente |
| UPME Resolucion 1198 de 2024 | `data/raw/upme/resolucion_upme_1198_2024.html` | Factor de emision 2023 actualizado para sensibilidad | Descargado | Es HTML normativo, no serie horaria |
| ICCT buses cero emisiones Colombia | `data/raw/icct/charging_infrastructure_zero_emission_buses_bogota_2023.pdf` | Contexto de infraestructura | Descargado | Fuente secundaria, no dato operacional |
| Enel movilidad electrica Bogota | `data/raw/enel/enel_bogota_electric_mobility_2024.html` | Contexto local | Descargado | Fuente narrativa |
| Enel X patios eBuses | `data/raw/enel/enelx_patios_ebuses_bogota.html` | Patios electricos, cargadores y contexto local | Descargado | Notas de prensa, no base operacional |
| Enel X Fontibon III | `data/raw/enel/enelx_172_buses_quinto_patio.html` | 13.6 MVA, 81 cargadores, 150 kW y tiempos 2--4 h | Descargado | Solo un patio |
| Andesco dos electropatios | `data/raw/andesco/enel_codensa_401_buses_dos_patios.html` | Referencias de 13 y 18 MVA | Descargado | Fuente periodistica-sectorial |
| MGM Green Movil | `data/raw/mgm/patio_electrico_green_movil.html` | Referencia de 20 MVA para patio grande | Descargado | Caso de exito, no ficha regulatoria |
| TransMilenio Carboquimica | `data/raw/transmilenio/technical/parametros_tecnicos_patio_carboquimica.pdf` | Ejemplo de documento tecnico ruta-patio | Descargado | No representa todos los patios |
| UNEP buses electricos ALyC | `data/raw/unep/documento_pnuma_transporte_electrico_2022.pdf` | Rangos reales de operacion y contexto regional | Descargado | Fuente regional, requiere parametrizacion |
| WRI/TUMI ciudades sostenibles | `data/raw/wri_tumi/transporte_publico_ciudades_sostenibles_2024.pdf` | kWh/km y baterias por tipologia de bus | Descargado | Presentacion, no articulo revisado por pares |
| IRENA costos renovables 2023 | `data/raw/irena/irena_renewable_power_generation_costs_2023_executive_summary.pdf` | CAPEX PV y BESS para escenarios | Descargado | Costos globales, no especificos Colombia |
| Mercado no regulado Colombia | `data/raw/market/*.html` | Contexto de tarifas y demanda desconectable | Descargado | Fuentes comerciales, usar solo como apoyo contextual |

## Fuentes que requieren seguimiento

- GTFS realtime: los endpoints `.pb` probados devolvieron 404 el 2026-05-04/05. El pipeline debe dejar URLs parametrizables para capturas futuras.
- UPME 2023 en `www1.upme.gov.co`: el host no resolvio DNS. Se conserva UPME 2024 descargado desde `docs.upme.gov.co`.
- C40/ICCT pipeline de autobuses electricos en America Latina: el PDF publico devolvio 403 a descarga automatizada. Se conserva como fuente manual si se necesita costo de infraestructura por bus.
