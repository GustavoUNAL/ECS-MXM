# Mas X Menos CRA 27

Insumos del Operador de Red para el estudio de conexión.

| Parámetro | Valor |
|-----------|-------|
| Circuito | 20-507 |
| OR | ESSA |
| Estado | Insumos + plantilla LaTeX (contenido por adaptar) |

## Datos (`data/`)

- `Datos Circuito 20 507.xlsx` — parámetros del circuito
- `FD_20 507.pdf` — diagrama / FD del circuito
- `20 507.pdf` — archivo adicional del OR

## LaTeX

Plantilla en `latex/` (copiada de `template/`). Compilar:

```bash
cd latex
tectonic main.tex --outdir=. -r 2
```

## Simulación PowerFactory

Carpeta `simulation/scripts/validar_modelo_pf.py`:

1. Abrir el proyecto PF del circuito 20-507.
2. Ajustar `PROJECT_NAME` y `POC_NAME` en el script.
3. Ejecutar desde PowerFactory.
4. Revisar `simulation/results/validacion_pf.txt`.
