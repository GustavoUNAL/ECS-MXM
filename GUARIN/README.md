# Mas X Menos Guarín

Estudio de Conexión Simplificado — **141,6 kWp / 120 kW AC**.

| Parámetro | Valor |
|-----------|-------|
| Circuito | 10-502 (SE Conucos, 13,8 kV) |
| POC | Nodo 3272966 |
| OR | ESSA |

## Contenido

- `Estudio_Conexion_MAS_X_MENOS.pdf` — PDF final
- `latex/` — fuentes LaTeX, figuras, scripts de análisis
- `data/` — Excel OR + unifilar + subestación
- `extracted/` — datos en texto + coordinación de protecciones
- `simulation/` — scripts PowerFactory y comparaciones
- `docs/lineas_por_crear.md` — plan de alineación modelo ↔ diagrama

## Compilar

```bash
cd latex
tectonic main.tex --outdir=. -r 2
```

## Simulación PowerFactory

Script principal: `simulation/scripts/validar_modelo_pf.py`

1. Abrir en PF el proyecto `Mas X Menos Guarin`.
2. Ejecutar el script desde PowerFactory.
3. Revisar `simulation/results/validacion_pf.txt`.

También: `exportar_parametros_lineas.py`, `_cmp_*.py`, `test_crear_linea.py` (ver `simulation/README.md`).
