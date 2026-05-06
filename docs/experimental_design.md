# Diseno experimental

## Unidad de analisis

La unidad principal es `patio-hora`. Cada patio tiene demanda electrica flexible derivada de actividad de buses, potencial PV de cubiertas, opcion de bateria estacionaria y limite de importacion desde red.

## Escenarios

| Escenario | Descripcion |
| --- | --- |
| S0 | Carga no gestionada, sin PV ni BESS |
| S1 | Carga inteligente, sin PV ni BESS |
| S2 | Carga inteligente + PV en cubierta de patio |
| S3 | Carga inteligente + BESS sin PV |
| S4 | Carga inteligente + PV + BESS |
| S5 | PV en patio + cubiertas cercanas |
| S6 | PV + BESS con conexion restringida |
| S7 | Expansion de flota 2026-2035 |
| S8 | Factor de emision alto |
| S9 | Precio electrico alto |

Escenarios de cubierta:

| Escenario | Area PV permitida |
| --- | --- |
| R0 | Sin PV |
| R1 | Solo cubiertas internas del patio |
| R2 | Patio con factor conservador de disponibilidad |
| R3 | Patio con factor medio de disponibilidad |
| R4 | Patio + entorno cercano |
| R5 | Maximo tecnico con sensibilidad de disponibilidad |

## Modelo MILP base

Implementacion prevista: el modelo se formulara en Pyomo y, para instancias grandes, se resolvera mediante NEOS Server cuando se requieran solvers remotos academicos. En el paper deben citarse Pyomo y NEOS, y cada corrida debe registrar:

- version de Pyomo;
- solver usado en NEOS o localmente;
- fecha de corrida;
- tolerancia de optimalidad;
- limite de tiempo;
- estado de terminacion;
- gap reportado;
- tiempo de solucion;
- maquina local o servicio remoto;
- si la instancia se resolvio localmente, via NEOS o en ambos para verificacion.

Regla editorial: no subir a NEOS datos confidenciales. En este proyecto los insumos previstos son publicos o derivados reproducibles, pero se debe mantener fuera cualquier dato privado que se consiga por convenio.

Indices:

- `d`: patio.
- `t`: hora.
- `b`: bloque operativo o clase de bus cuando aplique.

Parametros principales:

- `E_req[d,t]`: energia requerida por buses que deben estar listos al final de una ventana.
- `P_ch_max[d]`: potencia maxima de cargadores.
- `G_max[d]`: capacidad maxima de conexion a red.
- `PV_avail[d,t]`: produccion PV disponible.
- `eta_ch`, `eta_dis`: eficiencias BESS.
- `C_grid[t]`: precio horario de importacion.
- `EF[t]`: factor horario o promedio de emisiones.
- `A_roof[d]`: area de cubierta disponible.
- `Capex_pv`, `Capex_bess`, `Capex_grid`: costos anualizados.

Variables:

- `p_grid[d,t] >= 0`: importacion de red.
- `p_export[d,t] >= 0`: exportacion o vertimiento permitido segun escenario.
- `p_bus[d,t] >= 0`: potencia dedicada a cargar buses.
- `p_bess_ch[d,t] >= 0`: carga BESS.
- `p_bess_dis[d,t] >= 0`: descarga BESS.
- `soc[d,t]`: estado de carga BESS.
- `pv_cap[d]`: capacidad PV instalada.
- `bess_e_cap[d]`, `bess_p_cap[d]`: energia y potencia BESS.
- `grid_cap[d]`: capacidad de conexion seleccionada cuando sea variable.

Funcion objetivo:

Minimizar costo total anualizado:

```text
sum_t,d C_grid[t] * p_grid[d,t]
+ sum_d Capex_pv * pv_cap[d]
+ sum_d Capex_bess_E * bess_e_cap[d]
+ sum_d Capex_bess_P * bess_p_cap[d]
+ sum_d Capex_grid * grid_cap[d]
+ penalizaciones por energia no servida, si se habilitan
```

Restricciones clave:

- Balance por patio-hora:

```text
p_grid + pv_used + p_bess_dis = p_bus + p_bess_ch + p_export
```

- Limite de conexion:

```text
p_grid[d,t] <= grid_cap[d]
```

- PV instalado y disponible:

```text
pv_cap[d] <= A_roof[d] * kWp_per_m2
pv_used[d,t] + p_export[d,t] <= PV_profile[t] * pv_cap[d]
```

- Dinamica BESS:

```text
soc[d,t] = soc[d,t-1] + eta_ch*p_bess_ch[d,t] - p_bess_dis[d,t]/eta_dis
0 <= soc[d,t] <= bess_e_cap[d]
p_bess_ch[d,t] <= bess_p_cap[d]
p_bess_dis[d,t] <= bess_p_cap[d]
```

- Servicio de buses:

```text
sum_{t in window(w)} p_bus[d,t] * eta_charger >= E_req_window[d,w]
```

## Indicadores de salida

- Pico de importacion por patio y sistema.
- Energia importada, energia PV usada, PV vertida y energia BESS ciclada.
- Capacidad PV y BESS optima.
- Costo total anualizado y costo por km/bus.
- Emisiones operativas y emisiones evitadas.
- Factor de carga de conexion.
- Reduccion de simultaneidad de picos.

## Figuras esperadas

- Mapa de patios y potencial PV.
- Perfil horario S0-S4 para patios representativos.
- Barras de pico/costo/emisiones por escenario.
- Curva de sensibilidad a capacidad de conexion.
- Frontera PV-BESS-grid para escenarios R0-R5.
