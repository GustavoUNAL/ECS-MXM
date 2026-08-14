# -*- coding: utf-8 -*-
"""Compara diagrama CTO_10_502 vs OR (lineas base) vs modelo PF."""
from pathlib import Path
import re

_ROOT = Path(__file__).resolve().parents[1]  # GUARIN/simulation
_GUARIN = _ROOT.parent
BASE = _GUARIN / "data" / "lineas_base.txt"
PF = _ROOT / "results" / "lineas_parametros.csv"
OUT = _ROOT / "results" / "comparacion_cto_10_502.txt"

# --- Nodos del diagrama (extraidos del mensaje del usuario) ---
DIAG_ORIGEN = {"CONUCO_13.8"}

DIAG_PRIMARIAS = {
    "1067001", "1067184", "1067028", "1067141", "1067125", "1065971", "1101251",
    "1067192", "1101277", "1067214", "1067206", "1101447", "1101404", "1101307",
    "1067036", "1103253", "1103385", "1154541", "1154401", "1067052", "1067117",
    "1067109", "1103458", "1154214", "1067133", "1067087", "1067079", "1154311",
    "2567831", "1067010", "4249372", "1101340", "1101293", "1102982", "1101421",
    "1102974", "1067176", "1101374", "2214156", "1154613", "1154087", "1154435",
    "2479567", "1101480", "1103318", "1101471", "1101455", "3453260", "1026666",
    "1157019", "1155997", "1155881", "5604524", "1155822", "4938216", "9219013",
    "8795266", "1155776", "1154176", "4916671", "3272966", "8338973", "1155679",
    "1101315", "1103407", "1103229", "1154591", "1101391", "1101382", "1155911",
    "2789141", "2789132", "2765837", "1069471", "1154281", "1154290", "1154494",
    "1155946",
}

DIAG_SECUNDARIOS = {
    "1154605", "1667262", "1103725", "1667238", "1154524", "1103245", "1103351",
    "1154532", "1155652", "1103393", "1103431", "1155377", "1155351", "1155245",
    "4637861", "4637852", "3272869", "3272761", "1155971", "3272664", "5605032",
    "9500774", "3453367", "3453464", "3453561", "1155253", "1155270", "1618741",
    "1618750", "9500766", "9500758", "8339694", "8339155", "1067044", "1618733",
    "1154192", "1154206", "1155741", "2765829", "2765811", "1155342", "5605024",
    "1155857", "1155849", "2567814", "1045288", "4249356", "1283235", "1069454",
    "1101331", "3769721", "4249348", "1154249", "4249330", "1026682", "8339708",
    "1154508", "2214148", "2214130", "1069446", "1069438", "1101412", "1154303",
    "1154141", "1154273", "1154257", "1102958", "1154443", "1067150", "1101358",
    "1155750", "1069683", "1069527", "1069519", "1069501", "1069497", "1155806",
    "1155792", "1154478", "1154451", "1154133", "1154150", "1154583", "1154575",
    "1154117", "1154222", "1154125", "1154079", "1103211", "1155938", "1154109",
    "1154231", "3272567", "1103326", "1154371", "1103300", "1103296", "1155334",
    "1101323", "4637844", "1154397", "1154389", "1069489", "1154354", "1154346",
}

DIAG_NODES = DIAG_ORIGEN | DIAG_PRIMARIAS | DIAG_SECUNDARIOS

# Lineas mencionadas en el diagrama (IDs de ElmLne, no nodos)
DIAG_LINES = {
    # CU_2_XLPE
    "9967", "15351", "9944", "5148", "9840", "9839", "15350", "9990", "11384",
    "9137", "9141", "40905", "9253", "9320", "9783", "15349", "15348", "9945",
    "9946", "9950", "9966", "9949", "10833", "11383", "11381", "825166", "9989",
    "11284", "47594", "11287", "791042", "11342", "825167", "9301", "10943",
    "714206", "9264", "10945", "764757", "10944", "741064", "10834", "807675",
    "830657", "830655", "830654", "807674", "807673", "26712", "10836", "11385",
    "812083", "791044", "720194", "720191", "764760", "725659", "807672", "764759",
    "720190", "812081", "9843", "9844", "812082", "26711", "10835", "812080",
    "9266", "725649", "791043", "764758", "725650", "791045", "9265", "47595",
    "11288", "11285", "9299", "11344", "40907", "40906", "9351", "9345", "9257",
    "10942", "10979", "9811", "720189", "9785", "11343", "26713", "714209",
    "21783", "714525", "720193", "714208", "9277", "714207", "720192", "9302",
    "725660", "21782", "9140", "9142", "9323", "11290", "9276", "9300", "9321",
    "11286", "47596", "11289", "9322", "9139", "9143", "9343", "9344", "9256",
    "9267", "9254", "9352", "11382", "9258", "9268", "828945", "9824", "807671",
    "828942", "9823", "9842", "9822", "10941", "10978", "830653", "47597", "9841",
    "806799", "9784",
    # CU_350
    "804306",
    # CU_4/0
    "828948", "828934",
    # CU_1/0
    "21781",
    # ACSR_4/0
    "5105", "5128", "5127", "5108", "5109", "5111", "5113", "5118", "5117",
    "5112", "5130", "5120", "5106", "5110",
    # ACSR_2/0
    "5156", "5154", "5147", "5143", "5280", "5157", "5136", "5132", "5142",
    "5153", "5140",
    # ACSR_1/0
    "5304", "5281", "5285", "5291", "5282", "5297", "5373", "5295", "5287",
    "5289", "5290", "5283", "5288", "5296", "5298", "5300", "5292",
    # ECO
    "5145",
    # ACSR_2
    "717306", "717305",
}


def base_id(node: str) -> str:
    n = node.strip()
    m = re.fullmatch(r"(\d+)([A-Za-z]+)", n)
    if m:
        return m.group(1)
    return n


def parse_file(path):
    text = path.read_text(encoding="utf-8-sig")
    lines_data = {}
    nodes = set()
    for ln in text.splitlines()[2:]:
        if not ln.strip():
            continue
        parts = ln.split("\t")
        if len(parts) < 5:
            continue
        name = parts[0].strip()
        ti = parts[3].strip()
        tj = parts[4].strip()
        typ = parts[6].strip() if len(parts) > 6 else ""
        lines_data[name] = {"ti": ti, "tj": tj, "type": typ}
        if ti:
            nodes.add(ti)
        if tj:
            nodes.add(tj)
    return lines_data, nodes


def sort_key(x):
    return (0, int(x)) if x.isdigit() else (1, x)


or_lines, or_nodes = parse_file(BASE)
pf_lines, pf_nodes = parse_file(PF)

or_roots = {base_id(n) for n in or_nodes}
pf_roots = {base_id(n) for n in pf_nodes}
# Alias conocidos
or_roots_ext = set(or_roots)
or_roots_ext.add("CONUCO_13.8")  # no esta como tal en OR
pf_roots_ext = set(pf_roots)
# mapear Terminal(1) / 10 502_Term como origen
if "Terminal(1)" in pf_roots or any("502" in n for n in pf_nodes):
    pass

# ---- NODOS ----
diag_in_or = sorted(DIAG_NODES & or_roots, key=sort_key)
diag_in_pf = sorted(DIAG_NODES & pf_roots, key=sort_key)
# CONUCO / Terminal
diag_missing_or = sorted(DIAG_NODES - or_roots - {"CONUCO_13.8"}, key=sort_key)
diag_missing_pf = sorted(DIAG_NODES - pf_roots - {"CONUCO_13.8"}, key=sort_key)

# Origen especial
origen_or = [n for n in or_nodes if "502" in n or "Term" in n]
origen_pf = [n for n in pf_nodes if "Terminal" in n or "502" in n]

or_not_in_diag = sorted(or_roots - DIAG_NODES - {"10 502_Term"}, key=sort_key)
pf_not_in_diag = sorted(pf_roots - DIAG_NODES - {"Terminal(1)"}, key=sort_key)

# ---- LINEAS ----
diag_lines = set(DIAG_LINES)
# 5148 aparece en dos tipos en el diagrama (error del texto); esta en OR como ACSR
in_or = sorted(diag_lines & set(or_lines), key=sort_key)
in_pf = sorted(diag_lines & set(pf_lines), key=sort_key)
missing_or = sorted(diag_lines - set(or_lines), key=sort_key)
missing_pf = sorted(diag_lines - set(pf_lines), key=sort_key)
or_extra = sorted(set(or_lines) - diag_lines, key=sort_key)
pf_extra = sorted(set(pf_lines) - diag_lines, key=sort_key)

# Clasificar lineas del diagrama faltantes en PF
por_crear_conocidas = {
    "9344", "825166", "825167", "828934", "828942", "828945", "828948",
    "830653", "830654", "830655", "830657",
}

lines_out = []
a = lines_out.append
a("=" * 70)
a("COMPARACION DIAGRAMA CTO_10_502 vs OR vs MODELO PF")
a("=" * 70)
a("")
a("=== NODOS ===")
a(f"Diagrama (listados):     {len(DIAG_NODES)}  (origen={len(DIAG_ORIGEN)}, primarias={len(DIAG_PRIMARIAS)}, secundarios={len(DIAG_SECUNDARIOS)})")
a(f"OR buses raiz:           {len(or_roots)}")
a(f"Modelo PF buses raiz:    {len(pf_roots)}")
a("")
a(f"Diagrama ∩ OR:           {len(diag_in_or)}")
a(f"Diagrama ∩ Modelo:       {len(diag_in_pf)}")
a(f"En diagrama, NO en OR:   {len(diag_missing_or)}")
a(f"En diagrama, NO en PF:   {len(diag_missing_pf)}")
a(f"En OR, NO en diagrama:   {len(or_not_in_diag)}")
a(f"En PF, NO en diagrama:   {len(pf_not_in_diag)}")
a("")
a("--- Origen CONUCO_13.8 ---")
a(f"En diagrama: CONUCO_13.8")
a(f"En OR (candidatos): {origen_or or 'ninguno con Term/502'}")
a(f"En PF (candidatos): {origen_pf or 'ninguno'}")
a("  -> Equivalencia tipica: CONUCO_13.8 ≈ 10 502_Term (OR) ≈ Terminal(1) (PF)")
a("")
a("--- Nodos del diagrama que FALTAN en OR ---")
if not diag_missing_or:
    a("(ninguno)")
else:
    for n in diag_missing_or:
        grp = "primaria" if n in DIAG_PRIMARIAS else "secundario"
        a(f"  {n}\t[{grp}]")
a("")
a("--- Nodos del diagrama que FALTAN en el modelo PF ---")
if not diag_missing_pf:
    a("(ninguno)")
else:
    for n in diag_missing_pf:
        grp = "primaria" if n in DIAG_PRIMARIAS else "secundario"
        en_or = "si en OR" if n in or_roots else "NO en OR"
        a(f"  {n}\t[{grp}]\t{en_or}")
a("")
a("--- Nodos en OR que NO estan en el diagrama ---")
for n in or_not_in_diag:
    a(f"  {n}")
a("")
a("--- Nodos en PF que NO estan en el diagrama ---")
for n in pf_not_in_diag:
    a(f"  {n}")
a("")
a("=" * 70)
a("=== LINEAS (IDs mencionados en el diagrama) ===")
a(f"IDs unicos en diagrama:  {len(diag_lines)}")
a(f"OR lineas:               {len(or_lines)}")
a(f"PF lineas:               {len(pf_lines)}")
a("")
a(f"Diagrama ∩ OR:           {len(in_or)}")
a(f"Diagrama ∩ PF:           {len(in_pf)}")
a(f"En diagrama, NO en OR:   {len(missing_or)}")
a(f"En diagrama, NO en PF:   {len(missing_pf)}")
a(f"En OR, NO en diagrama:   {len(or_extra)}")
a(f"En PF, NO en diagrama:   {len(pf_extra)}")
a("")
a("--- Lineas del diagrama que FALTAN en OR ---")
if not missing_or:
    a("(ninguna)")
else:
    for n in missing_or:
        a(f"  {n}")
a("")
a("--- Lineas del diagrama que FALTAN en PF ---")
if not missing_pf:
    a("(ninguna)")
else:
    for n in missing_pf:
        tag = " (ya identificada por crear)" if n in por_crear_conocidas else ""
        if n in or_lines:
            r = or_lines[n]
            a(f"  {n}\t{r['ti']} -> {r['tj']}\t{r['type']}{tag}")
        else:
            a(f"  {n}\t(no esta ni en OR){tag}")
a("")
a("--- Lineas en OR / PF que el diagrama NO menciona ---")
a(f"OR omitidas por diagrama: {len(or_extra)} -> {', '.join(or_extra)}")
a(f"PF omitidas por diagrama: {len(pf_extra)} -> {', '.join(pf_extra)}")
a("")
a("=" * 70)
a("=== VEREDICTO ===")
a(f"Cobertura nodos diagrama→OR: {len(diag_in_or)}/{len(DIAG_NODES)-1} (sin CONUCO)")
a(f"Cobertura nodos diagrama→PF: {len(diag_in_pf)}/{len(DIAG_NODES)-1} (sin CONUCO)")
a(f"Cobertura lineas diagrama→OR: {len(in_or)}/{len(diag_lines)}")
a(f"Cobertura lineas diagrama→PF: {len(in_pf)}/{len(diag_lines)}")

text = "\n".join(lines_out)
OUT.write_text(text, encoding="utf-8")
try:
    print(text)
except UnicodeEncodeError:
    print(text.encode("ascii", errors="replace").decode("ascii"))
print(f"\nEscrito: {OUT}")
