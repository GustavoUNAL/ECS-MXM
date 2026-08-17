# Mas X Menos Guarín

Estudio de Conexión Simplificado — **141,6 kWp / 120 kW AC** · circuito **10-502** · POC **3272966**.

## Árbol del proyecto

```
GUARIN/
├── Estudio_Conexion_MAS_X_MENOS.pdf   # Entregable final
├── data/                              # Insumos OR + docs proyecto → README
├── extracted/                         # Texto extraído (demanda, protección, POC…)
├── analysis/                          # Informe interactivo → README
│   ├── scripts/                       # generar_informe, analizar_excel…
│   ├── output/                        # JSON, CSV, tablas comparativas
│   └── web/                           # topologia_interactiva.html ← abrir aquí
├── simulation/                        # PowerFactory → README
├── docs/                              # Notas (p. ej. lineas_por_crear.md)
└── latex/                             # Fuentes del PDF del estudio
```

## Inicio rápido

| Objetivo | Dónde |
|----------|--------|
| Ver topología + informe + estados | `analysis/web/topologia_interactiva.html` |
| Regenerar datos del informe | `python analysis/scripts/generar_informe_circuito.py` |
| Comparar Excel ↔ PDF ↔ PF | `simulation/results/comparacion_*.txt` |
| Flujo de carga 6 escenarios | `simulation/scripts/exportar_flujo_carga.py` |
| Compilar estudio PDF | `cd latex && tectonic main.tex` |

## Parámetros clave

| Parámetro | Valor |
|-----------|-------|
| Circuito | 10-502 (SE Conucos, 13,8 kV) |
| OR | ESSA |
| Modelo OR | 215 líneas · 184 nodos · 51 cargas |
| Horas estudio | 09:00 · 12:00 · 15:00 (demanda 19/03/2024) |

Ver [analysis/README.md](analysis/README.md) y [simulation/README.md](simulation/README.md) para el flujo detallado.
