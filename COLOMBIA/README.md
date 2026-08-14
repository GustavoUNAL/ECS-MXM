# Mas X Menos Colombia

Insumos del Operador de Red para el estudio de conexión.

| Parámetro | Valor |
|-----------|-------|
| Circuito | 58-512 |
| OR | ESSA |
| Estado | Insumos + plantilla LaTeX (contenido por adaptar) |

## Datos (`data/`)

- `Datos Circuito 58 512.xlsx` — parámetros del circuito
- `CTO 58 512.pdf` — diagrama unifilar
- `58 512.pdf` — archivo adicional del OR

## LaTeX

Plantilla en `latex/` (copiada de `template/`). Compilar:

```bash
cd latex
tectonic main.tex --outdir=. -r 2
```

## Simulación PowerFactory

Carpeta `simulation/scripts/validar_modelo_pf.py`:

1. Abrir el proyecto PF del circuito 58-512.
2. Ajustar `PROJECT_NAME` y `POC_NAME` en el script.
3. Ejecutar desde PowerFactory.
4. Revisar `simulation/results/validacion_pf.txt`.
