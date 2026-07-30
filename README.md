# ECS-MXM

Estudio de Conexión Simplificado — Proyecto Solar **MAS X MENOS Guarín** (141,6 kWp).

## Contenido

- `Estudio_Conexion_MAS_X_MENOS.pdf` — PDF final del estudio
- `proyecto/` — fuentes LaTeX, figuras, scripts de análisis
- `GUARIN/data/` — datos del OR (Excel + unifilar del circuito 10-502)
- `GUARIN/extracted/` — datos extraídos a texto plano + coordinación de protecciones
- `files/` — fuentes originales del template

## Compilar el PDF

```bash
cd proyecto
tectonic main.tex --outdir=. -r 2
```

## Regenerar figuras

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install matplotlib openpyxl numpy
python proyecto/scripts/generar_figuras.py
```

## Datos del punto de conexión

| Parámetro | Valor |
|-----------|-------|
| Circuito | 10-502 (SE Conucos, 13,8 kV) |
| POC | Nodo 3272966 |
| Capacidad | 141,6 kWp / 120 kW AC |
| OR | ESSA |

Elaborado por COPOWER LTDA — Bucaramanga, Santander — 2026
