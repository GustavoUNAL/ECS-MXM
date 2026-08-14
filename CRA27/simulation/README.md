# Simulación PowerFactory — CRA 27 (20-507)

## Scripts

| Script | Uso |
|--------|-----|
| `scripts/validar_modelo_pf.py` | Validación inventarios + flujo de carga (+ CC si hay POC) |

## Cómo ejecutar

1. Crear/abrir el proyecto PF (p. ej. `Mas X Menos CRA27`).
2. Ajustar en el script: `PROJECT_NAME` y `POC_NAME`.
3. Cuando el POC esté definido, poner `RUN_SHORT_CIRCUIT = True`.
4. Ejecutar desde PowerFactory → revisar `results/validacion_pf.txt`.

## Referencia OR

- Líneas esperadas: **401**
- Cargas esperadas: **102**
- Datos: `../data/Datos Circuito 20 507.xlsx`
