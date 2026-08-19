# Simulación PowerFactory — Guarín (10-502)



Base SDL: [`../../sdl/10-502.pfd`](../../sdl/10-502.pfd)



**Salidas:** [`resultados de scripts/`](resultados%20de%20scripts/) — misma estructura que `scripts/`.



## Estructura



```

scripts/

├── _lib/pf_or_insumos.py       # rutas, Excel OR, utilidades PF

├── construir_red/              # alinear modelo con insumos OR

├── validar_red/                # comparar y validar sin modificar PF

└── flujo_carga/                # 6 escenarios LF (09/12/15 h)



resultados de scripts/

├── construir_red/

├── validar_red/

└── flujo_carga/

```



## Scripts



| Carpeta | Script | Donde ejecutar | Salida |

|---------|--------|------------------|--------|

| `construir_red/` | `exportar_parametros_lineas.py` | PowerFactory | `construir_red/lineas_parametros.csv` |

| `construir_red/` | `sync_nodos_or_a_pf.py` | PowerFactory | `construir_red/sync_nodos_or_pf.txt` |

| `construir_red/` | `sync_lineas_or_a_pf.py` | PowerFactory | `construir_red/sync_lineas_or_pf.txt` |

| `validar_red/` | `comparar_nodos_or_pf.py` | Python | `validar_red/comparacion_nodos.txt` |

| `validar_red/` | `comparar_lineas_or_pf.py` | Python | `validar_red/comparacion_lineas.txt` |

| `validar_red/` | `comparar_diagrama_or_pf.py` | Python | `validar_red/comparacion_diagrama.txt` |

| `validar_red/` | `validar_modelo_pf.py` | PowerFactory | `validar_red/validacion_pf.txt` |

| `flujo_carga/` | `calibrar_demanda_or.py` | PowerFactory | `flujo_carga/calibrar_demanda_or.txt` |

| `flujo_carga/` | `exportar_flujo_carga.py` | PowerFactory | `flujo_carga/` |

| `cortocircuito/` | `exportar_cortocircuito.py` | PowerFactory | `cortocircuito/` |

| `protecciones/` | `exportar_coordinacion.py` | Python | `protecciones/` |



## Flujo: construir y validar la red



1. **PF** — `construir_red/exportar_parametros_lineas.py`

2. **Python** — `validar_red/comparar_nodos_or_pf.py`, `comparar_lineas_or_pf.py`, `comparar_diagrama_or_pf.py`

3. **PF** — `construir_red/sync_nodos_or_a_pf.py` (`DRY_RUN=True` primero, luego `False`)

4. Repetir export + comparar hasta cuadrar nodos y líneas



## Flujo de carga



Objetivo de cabecera (Excel OR, 19/03/2024, **sin** SSFV, línea `804306`):

- 09:00 → 61,05 A · 1,459 MVA
- 12:00 → 70,41 A · 1,683 MVA (pico)
- 15:00 → 68,55 A · 1,638 MVA

1. PF: proyecto `Mas X Menos Guarin`, SSFV 1/2 CPW
2. PF: `flujo_carga/exportar_flujo_carga.py` (`AJUSTAR_A_OR=True` calibra I de cabecera al Excel)
3. Revisar `resultados de scripts/flujo_carga/reporte.txt` — en `SIN_SSFV`, `err_I_pct` debe quedar dentro de ±1 %
4. Opcional: `flujo_carga/calibrar_demanda_or.py` (`DRY_RUN=True` primero, luego `False`) para persistir escalas en Operation Scenarios



## Cortocircuito y protecciones

1. **PF** — `exportar_cortocircuito.py` (wrapper ComPython) → `resultados de scripts/cortocircuito/`
2. **Python** — `scripts/protecciones/exportar_coordinacion.py`
3. **Python** — `latex/scripts/exportar_tablas_estudio.py` → `latex/generated/*.tex` y `latex/figuras/fig_*.png`



## Validación del modelo



PF: `validar_red/validar_modelo_pf.py` → `validar_red/validacion_pf.txt`



Conteos esperados (Excel OR): **215** líneas · **51** cargas · POC **3272966**

