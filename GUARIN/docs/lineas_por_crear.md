Ruta práctica para que el modelo PF quede **igual al diagrama CTO_10_502**:

---

### Fase 0 — Criterio de “idéntico”
1. Mismos **nodos** (buses raíz del diagrama).
2. Mismas **líneas** (IDs del diagrama) con mismos extremos y tipos.
3. Sin líneas/nodos **extra** que el diagrama no muestre (o renombrar equivalentes).
4. Origen: `CONUCO_13.8` = `Terminal(1)` / `10 502_Term`.

---

### Fase 1 — Crear nodos que faltan en PF (4)
Tensión **13.8 kV**, en la red `Red`:

| Nodo | Para qué |
|------|----------|
| **4637844** | Ramal 830653–830654 |
| **4637852** | 830654–830655 |
| **4637861** | 830655–830657 |
| **4916671** | Extremo de 830657 |

Sin estos nodos no puedes cerrar ese ramal.

---

### Fase 2 — Decidir qué hacer con líneas “duplicadas” en PF
Antes de crear, evita dobles caminos:

| En PF hoy | Equivalente diagrama/OR | Acción sugerida |
|-----------|-------------------------|-----------------|
| 10396 | 825166 | Borrar o renombrar → 825166 |
| 10397 | 825167 | Borrar o renombrar → 825167 |
| 26921 | 828934 | Borrar/renombrar + tipo → CU_4/0 |
| 26920 | 828942 | Idem |
| 5303 | 828945 | Idem |
| 5305 | 828948 | Idem |

Si las dejas y además creas las del OR, queda topología distinta al diagrama.

---

### Fase 3 — Crear las 11 líneas del diagrama que faltan
En este orden (primero nodos ya existentes, luego el ramal nuevo):

1. **9344** — `1154575` ↔ `1154583` — 0,0186 km — `3F_15_CU_2_XLPE`  
   *(ya tienes `test_crear_linea.py` para esta)*
2. **825166** — `1101277` ↔ `1103431` — 0,0165 — CU_2  
3. **825167** — `1103431` ↔ `1103458` — 0,0299 — CU_2  
4. **828934** — `1101447` ↔ `1101455` — 0,0493 — `3F_15_CU_4/0_XLPE`  
5. **828942** — `1101455` ↔ `1101471` — 0,0652 — CU_4/0  
6. **828945** — `1101471` ↔ `1101480` — 0,0708 — CU_4/0  
7. **828948** — `1101480` ↔ `2479567` — 0,0493 — CU_4/0  
8. **830653** — `1101382` ↔ `4637844` — 0,0165 — CU_2  
9. **830654** — `4637844` ↔ `4637852` — 0,0092 — CU_2  
10. **830655** — `4637852` ↔ `4637861` — 0,0205 — CU_2  
11. **830657** — `4637861` ↔ `4916671` — 0,0114 — CU_2  

Usar buses del modelo **sin** sufijo A/B/C (`1101277`, no `1101277B`).

---

### Fase 4 — Limpiar lo que el diagrama no muestra
Tras Fase 3, revisar líneas que están en PF y **no** en el diagrama (p. ej. `5129`, `5158`, `9138`, `9274`, `9275`, `9341`, `9342`, `9991`, extras 10396…).

- Si son **puentes internos** (0,0012 km) o tramos de detalle OR → el diagrama no los pide: quítalos solo si quieres 1:1 gráfico; si el estudio OR los necesita, déjalos y acepta “diagrama ⊂ modelo”.
- Si quieres **idéntico al diagrama**, elimina (o saca de servicio) todo lo no listado en el CTO.

---

### Fase 5 — Homologar nombres (opcional pero útil)
- Renombrar `Terminal(1)` → `CONUCO_13.8` (o `10 502_Term`).
- No hace falta crear cubículos `…A/…B` salvo que el estudio de cortocircuito/protección lo exija; el diagrama trabaja a nivel bus.

---

### Fase 6 — Validar
1. Re-exportar con `exportar_parametros_lineas.py`.
2. Comparar otra vez diagrama ↔ PF (nodos y líneas).
3. Meta: **0 nodos faltantes**, **0 líneas del diagrama faltantes**, **0 extras no deseados**.
4. Flujo de carga en el alimentador 10 502 y revisar que no haya islas (sobre todo el ramal 4637844).

---

### Orden de trabajo resumido
```
Crear 4 nodos
    → Resolver duplicados (10396/10397/26920… vs 825166/8289xx)
        → Crear 11 líneas (test 9344 primero)
            → Limpiar extras no diagramados
                → Renombrar origen
                    → Re-exportar y comparar
```

Cuando confirmes que el test de **9344** quedó bien, el siguiente paso natural es un script que haga Fase 1 + Fase 3 en bloque.