# Simulación PowerFactory — Colombia (58-512)

## Scripts

| Script | Uso |
|--------|-----|
| `scripts/validar_modelo_pf.py` | Validación inventarios + flujo de carga (+ CC si hay POC) |

## Cómo ejecutar

1. Crear/abrir el proyecto PF (p. ej. `Mas X Menos Colombia`).
2. Ajustar en el script: `PROJECT_NAME` y `POC_NAME`.
3. Cuando el POC esté definido, poner `RUN_SHORT_CIRCUIT = True`.
4. Ejecutar desde PowerFactory → revisar `results/validacion_pf.txt`.

## Referencia OR

- Líneas esperadas: **165**
- Cargas esperadas: **62**
- Datos: `../data/Datos Circuito 58 512.xlsx`
