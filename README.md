# ECS-MXM

Estudios de Conexión Simplificados — Proyectos solares **MAS X MENOS** (COPOWER LTDA).

## Estructura

```
.
├── template/          # Plantilla LaTeX base (secciones vacías / de referencia)
├── archive/           # ZIPs originales de insumos del OR
├── GUARIN/            # Proyecto completo — Mas X Menos Guarín
├── COLOMBIA/          # Insumos — Mas X Menos Colombia (cto 58-512)
└── CRA27/             # Insumos — Mas X Menos CRA 27 (cto 20-507)
```

Cada proyecto de sitio sigue el mismo esquema:

```
<SITIO>/
├── data/              # Excel + unifilar / FD del Operador de Red
├── extracted/         # Datos extraídos a texto (cuando existan)
├── simulation/        # Scripts PF + resultados de comparación
├── docs/              # Notas de modelado
└── latex/             # Fuentes LaTeX, figuras, scripts de análisis
```

## Proyectos

| Sitio | Circuito | OR | Estado |
|-------|----------|-----|--------|
| [GUARIN](GUARIN/) | 10-502 (SE Conucos, 13,8 kV) | ESSA | Estudio listo (PDF + LaTeX) |
| [COLOMBIA](COLOMBIA/) | 58-512 | ESSA | Insumos + plantilla LaTeX |
| [CRA27](CRA27/) | 20-507 | ESSA | Insumos + plantilla LaTeX |

### Guarín — datos de conexión

| Parámetro | Valor |
|-----------|-------|
| POC | Nodo 3272966 |
| Capacidad | 141,6 kWp / 120 kW AC |
| PDF | `GUARIN/Estudio_Conexion_MAS_X_MENOS.pdf` |

## Compilar el PDF (Guarín)

Requiere [Tectonic](https://tectonic-typesetting.github.io/) o una distribución LaTeX (TeX Live / MiKTeX).

```bash
cd GUARIN/latex
tectonic main.tex --outdir=. -r 2
```

## Regenerar figuras (Guarín)

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate
pip install matplotlib openpyxl numpy
python GUARIN/latex/scripts/generar_figuras.py
```

## Simulación PowerFactory

Cada sitio tiene `simulation/scripts/validar_modelo_pf.py`:

| Sitio | Circuito | Script |
|-------|----------|--------|
| GUARIN | 10-502 | `GUARIN/simulation/scripts/validar_modelo_pf.py` |
| COLOMBIA | 58-512 | `COLOMBIA/simulation/scripts/validar_modelo_pf.py` |
| CRA27 | 20-507 | `CRA27/simulation/scripts/validar_modelo_pf.py` |

Ejecutar desde PowerFactory con el proyecto del sitio abierto. El reporte queda en `simulation/results/validacion_pf.txt`.

En Guarín también hay scripts de exportación/comparación de topología (`exportar_parametros_lineas.py`, `_cmp_*.py`).

## Nuevo estudio a partir del template

1. Copiar `template/` → `<SITIO>/latex/`
2. Colocar insumos del OR en `<SITIO>/data/`
3. Adaptar `main.tex` y secciones al circuito / POC
4. Generar figuras y recompilar

Elaborado por COPOWER LTDA — Bucaramanga, Santander — 2026
