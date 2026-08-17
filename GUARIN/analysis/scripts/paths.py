"""Rutas comunes del análisis GUARIN (circuito 10-502)."""
from __future__ import annotations

from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ANALYSIS = SCRIPTS.parent
SITE = ANALYSIS.parent
REPO = SITE.parent

DATA = SITE / "data"
WEB = ANALYSIS / "web"
OUTPUT = ANALYSIS / "output"
SIMULATION = SITE / "simulation"
SIM_RESULTS = SIMULATION / "results"
LATEX = SITE / "latex"

EXCEL_OR = DATA / "Datos Circuito 10 502 - 2026.xlsx"
PDF_UNIFILAR = DATA / "CTO 10 502.pdf"
