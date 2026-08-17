# Análisis interactivo — Guarín 10-502

Capa de análisis entre **insumos OR** (`../data/`) y **simulación PF** (`../simulation/`).

## Estructura

```
analysis/
├── scripts/          # Generadores Python
├── output/           # JSON, CSV, tablas (artefactos generados)
└── web/              # Informe HTML interactivo (abrir en navegador)
```

## Uso rápido

```powershell
cd GUARIN/analysis/scripts
pip install openpyxl pymupdf   # o usar .venv del repo

python analizar_excel_circuito.py      # → output/analisis_excel_10502.json
python generar_informe_circuito.py     # → output/informe_circuito.json + web/informe_circuito.js
```

Abrir **`web/topologia_interactiva.html`** en el navegador (doble clic o Live Server).

## Scripts

| Script | Entrada | Salida |
|--------|---------|--------|
| `analizar_excel_circuito.py` | `data/Datos Circuito 10 502 - 2026.xlsx` | `output/analisis_excel_10502.json` |
| `generar_informe_circuito.py` | Excel + `data/CTO 10 502.pdf` | `output/informe_circuito.json`, `web/informe_circuito.js` |
| `actualizar_topologia_html.py` | `output/escenarios_operacion.json` | parches en `web/topologia_interactiva.html` |
| `quitar_resultados_pf_html.py` | — | quita bloques PF del HTML (solo insumos OR) |

Rutas centralizadas en `scripts/paths.py`.

## Flujo de análisis completo

```
data/ (Excel + PDF OR)
    │
    ├─► analysis/scripts ──► output/ + web/     Informe interactivo
    │
    └─► simulation/scripts ──► results/         Flujo de carga PF
            │
            └─► latex/scripts ──► latex/figuras/ ──► PDF estudio
```

Tras exportar PF, actualizar `output/escenarios_operacion.json` y `web/escenarios_operacion.js` si cambian los resultados (ver `simulation/README.md`).
