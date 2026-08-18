# ECS-MXM

Estudios de Conexión Simplificados — Proyectos solares **MAS X MENOS** (COPOWER LTDA).

## Estructura del monorepo

```
.
├── template/              # Plantilla LaTeX base
├── archive/               # ZIPs originales del OR
├── sdl/                   # Bases PowerFactory (.pfd) por circuito
├── GUARIN/                # Proyecto completo — 10-502
├── CRA27/                 # Insumos — 20-507
└── COLOMBIA/              # Insumos — 58-512
```

## Esquema por sitio

```
<SITIO>/
├── data/                  # Excel OR + unifilar + docs del proyecto
├── extracted/             # Datos extraídos a texto (Guarín)
├── analysis/              # Informe interactivo + scripts (Guarín)
│   ├── scripts/
│   ├── output/            # JSON, CSV, tablas
│   └── web/               # topologia_interactiva.html
├── simulation/            # Scripts PowerFactory + resultados de scripts/
├── docs/                  # Notas de modelado
└── latex/                 # Fuentes PDF del estudio
```

## Proyectos

| Sitio | Circuito | OR | Estado |
|-------|----------|-----|--------|
| [GUARIN](GUARIN/) | 10-502 (SE Conucos, 13,8 kV) | ESSA | Estudio listo + análisis interactivo |
| [COLOMBIA](COLOMBIA/) | 58-512 | ESSA | Insumos + plantilla LaTeX |
| [CRA27](CRA27/) | 20-507 | ESSA | Insumos + plantilla LaTeX |

### Guarín — referencia

| Parámetro | Valor |
|-----------|-------|
| POC | Nodo 3272966 |
| Capacidad | 141,6 kWp / 120 kW AC |
| PDF estudio | `GUARIN/Estudio_Conexion_MAS_X_MENOS.pdf` |
| Informe web | `GUARIN/analysis/web/topologia_interactiva.html` |

## Análisis completo (Guarín)

1. **Insumos** — `GUARIN/data/` (Excel + PDF OR)
2. **Análisis OR** — `python GUARIN/analysis/scripts/generar_informe_circuito.py`
3. **Vista interactiva** — abrir `GUARIN/analysis/web/topologia_interactiva.html`
4. **Simulación PF** — `GUARIN/simulation/scripts/` (ver [simulation/README](GUARIN/simulation/README.md))
5. **Informe PDF** — `cd GUARIN/latex && tectonic main.tex`

## Compilar PDF (Guarín)

```bash
cd GUARIN/latex
tectonic main.tex --outdir=. -r 2
```

## Regenerar figuras

```bash
pip install matplotlib openpyxl numpy
python GUARIN/latex/scripts/generar_figuras.py
```

## Simulación PowerFactory

| Sitio | Script validación |
|-------|-------------------|
| GUARIN | `GUARIN/simulation/scripts/validar_red/validar_modelo_pf.py` |
| COLOMBIA | `COLOMBIA/simulation/scripts/validar_modelo_pf.py` |
| CRA27 | `CRA27/simulation/scripts/validar_modelo_pf.py` |

Bases SDL: carpeta [`sdl/`](sdl/).

Elaborado por COPOWER LTDA — Bucaramanga, Santander — 2026
