# Simulación PowerFactory — Guarín (10-502)

## Scripts

| Script | Uso |
|--------|-----|
| `scripts/validar_modelo_pf.py` | Validación inventarios + LF + CC en POC 3272966 |
| `scripts/exportar_flujo_carga.py` | **Exporta LF** 09/12/15 × sin/con FV (`SSFV 1/2 CPW`) |
| `scripts/exportar_parametros_lineas.py` | Exporta líneas a CSV |
| `scripts/_cmp_*.py` | Compara diagrama / OR / modelo |
| `scripts/test_crear_linea.py` | Prueba creación de tramo |

## Flujo de carga (exportar)

1. Abrir proyecto `Mas X Menos Guarin` en PF.
2. Confirmar ElmPvsys **`SSFV 1 CPW`** y **`SSFV 2 CPW`**.
3. Ejecutar `scripts/exportar_flujo_carga.py` (recargar el script en PF si lo actualizaste).
4. Revisar `results/flujo_carga/`:
   - `resumen.csv`, `deltas.csv`, `tensiones.csv`, `lineas.csv`, `trafos.csv`, `perdidas.csv`, `reporte.txt`

> **Nota:** la salida usa ruta absoluta del repo (PF a veces corre desde `Temp`).

Control FV: `outserv=1` = sin FV · `outserv=0` = con FV. Escala de cargas a 09:00 / 12:00 / 15:00 respecto a 12:00.

## Cómo ejecutar la validación

1. Abrir PowerFactory 2024 y el proyecto `Mas X Menos Guarin`.
2. En **Scripts → Python**, ejecutar `validar_modelo_pf.py`.
3. Revisar `results/validacion_pf.txt`.
