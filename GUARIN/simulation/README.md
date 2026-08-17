# Simulación PowerFactory — Guarín (10-502)

Base SDL del circuito: [`../../sdl/10-502.pfd`](../../sdl/10-502.pfd)

## Scripts

| Script | Uso |
|--------|-----|
| `scripts/validar_modelo_pf.py` | Validación inventarios + LF + CC en POC 3272966 |
| `scripts/exportar_flujo_carga.py` | **Exporta LF** 09/12/15 × sin/con FV (`SSFV 1/2 CPW`) |
| `scripts/exportar_parametros_lineas.py` | Exporta líneas a CSV |
| `scripts/_cmp_*.py` | Compara diagrama / OR / modelo PF |
| `scripts/test_crear_linea.py` | Prueba creación de tramo |

## Resultados

```
results/
├── comparacion_nodos.txt      # OR vs PF
├── comparacion_lineas.txt     # 215 OR vs 191 PF · 30 por crear
├── comparacion_cto_10_502.txt # Diagrama PDF vs OR vs PF
├── lineas_parametros.csv      # Export desde PF
├── validacion_pf.txt          # (generar con validar_modelo_pf.py)
└── flujo_carga/               # 6 escenarios LF
    ├── resumen.csv
    ├── reporte.txt
    └── analisis_tensiones/    # Figuras intermedias (copiar a latex/figuras/)
```

## Flujo de carga

1. Abrir proyecto `Mas X Menos Guarin` en PF.
2. Confirmar ElmPvsys **`SSFV 1 CPW`** y **`SSFV 2 CPW`**.
3. Ejecutar `scripts/exportar_flujo_carga.py`.
4. Revisar `results/flujo_carga/`.

Control FV: `outserv=1` = sin FV · `outserv=0` = con FV.

## Enlace con análisis interactivo

Los resultados LF alimentan el informe web en [`../analysis/`](../analysis/README.md) (`escenarios_operacion.json` / `.js`).

## Validación del modelo

1. PowerFactory 2024 → proyecto `Mas X Menos Guarin`.
2. Ejecutar `validar_modelo_pf.py`.
3. Revisar `results/validacion_pf.txt`.

**Conteos esperados (Excel OR):** 215 líneas · 51 cargas · POC 3272966.
