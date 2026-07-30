# Estudio de Conexión Simplificado - Proyecto Solar MAS X MENOS

## Descripción

Este es un proyecto LaTeX completo para el **Estudio de Conexión Simplificado del Supermercado MAS X MENOS Guarín** - Proyecto Solar Fotovoltaico de 141.6 kWp.

El documento contiene:
- Portada profesional
- Tabla de contenidos
- Listas de figuras y tablas
- 6 capítulos principales
- Anexos
- Bibliografía

## Estructura del Proyecto

```
proyecto/
├── main.tex                    # Archivo principal
├── secciones/
│   ├── 01_introduccion.tex    # Introducción y resumen
│   ├── 02_antecedentes.tex    # Antecedentes y alcance
│   ├── 03_informacion_general.tex  # Información del proyecto
│   ├── 04_metodologia.tex     # Metodología de análisis
│   ├── 05_resultados.tex      # Resultados y análisis
│   └── 06_recomendaciones.tex # Recomendaciones y conclusiones
├── anexos/
│   └── anexo_A.tex            # Anexo técnico
└── README.md                   # Este archivo
```

## Contenido de Capítulos

### Capítulo 1: Introducción
- Introducción general al proyecto
- Resumen ejecutivo
- Contexto normativo

### Capítulo 2: Antecedentes y Alcance
- Contexto del sistema eléctrico colombiano
- Justificación del proyecto
- Objetivos generales y específicos

### Capítulo 3: Información General
- Ubicación geográfica
- Parámetros técnicos de inversores y paneles
- Cálculo de energía producida
- Especificaciones del transformador
- Parámetros del nodo de conexión

### Capítulo 4: Metodología
- Análisis de flujo de carga
- Análisis de cortocircuito
- Criterios de evaluación
- Normas aplicables

### Capítulo 5: Resultados
- Análisis de tensiones
- Cargabilidad de líneas
- Cargabilidad de transformadores
- Cortocircuito monofásico y trifásico
- Protecciones
- Cálculo de pérdidas

### Capítulo 6: Recomendaciones y Conclusiones
- Conclusiones principales
- Recomendaciones técnicas
- Validación en campo

## Cómo Usar en Overleaf

### Opción 1: Subir como Proyecto ZIP
1. Descarga todos los archivos del repositorio
2. Crea una carpeta llamada `estudio-solar-mxm`
3. Coloca todos los archivos en esa carpeta respetando la estructura
4. Comprime la carpeta como `estudio-solar-mxm.zip`
5. Entra a [Overleaf.com](https://www.overleaf.com/)
6. Haz clic en "New Project" → "Upload Project"
7. Sube el archivo ZIP
8. Abre el proyecto y compila con `main.tex`

### Opción 2: Crear Manualmente en Overleaf
1. Crea un nuevo proyecto en blanco en Overleaf
2. Copia el contenido de cada archivo `.tex` en Overleaf
3. Respeta la estructura de carpetas:
   - `/secciones/` para los capítulos
   - `/anexos/` para los anexos
4. Establece `main.tex` como archivo principal
5. Compila el proyecto

## Requisitos

- **Compilador:** pdfLaTeX o XeLaTeX
- **Paquetes LaTeX:** Los más comunes (instalados por defecto en Overleaf)
- **Idioma:** Español (babel)
- **Codificación:** UTF-8

## Personalizaciones Disponibles

### Cambiar Portada
Edita `main.tex` en la sección de PORTADA si deseas:
- Modificar el título
- Cambiar fechas
- Actualizar autores
- Modificar colores

### Cambiar Márgenes
En `main.tex`, línea de geometría:
```latex
\usepackage[margin=2cm]{geometry}
```

### Cambiar Espaciado
```latex
\setstretch{1.15}  % Cambiar a 1.0, 1.5, 2.0, etc.
```

### Cambiar Colores
```latex
\definecolor{darkblue}{rgb}{0.0, 0.0, 0.5}
\definecolor{lightgray}{rgb}{0.95, 0.95, 0.95}
```

## Caracteres Especiales

El proyecto está configurado para manejar correctamente:
- Acentos españoles (á, é, í, ó, ú)
- Caracteres especiales (ñ, ü)
- Símbolos técnicos (°, %, kW, kWp)
- Unidades del SI (kV, A, Ω)

## Tablas de Contenidos

Las siguientes se generan automáticamente:
- Tabla de Contenidos
- Lista de Figuras
- Lista de Tablas

Para actualizar, haz clic derecho en Overleaf → "Recompile"

## Referencias y Bibliografía

Las referencias están incluidas al final del documento en formato básico. Para agregar más referencias:

```latex
\bibitem{key} Autor, A. (Año). \textit{Título del trabajo}. Editorial.
```

## Compilación

En Overleaf:
1. Asegúrate que `main.tex` está seleccionado como archivo principal
2. Haz clic en "Recompile"
3. Espera a que compile (usualmente 30-60 segundos)
4. El PDF se mostrará en la parte derecha

## Solución de Problemas

### Error: "File not found"
- Verifica que los archivos estén en las carpetas correctas
- Comprueba la ruta en los `\include{}` comando

### Caracteres extraños
- Asegúrate de usar UTF-8 en Overleaf
- Cambia de pdfLaTeX a XeLaTeX en Menu → Settings

### Tablas desalineadas
- Aumenta el ancho con `\setlength{\LTpost}{}`
- Usa `\tiny`, `\small` para reducir tamaño de fuente

### Página en blanco al principio
- Es normal, la portada genera una página en blanco
- Puedes eliminar `\newpage` si no lo deseas

## Exportación

Para descargar el PDF final:
1. Haz clic en "Download PDF"
2. Se descargará el archivo compilado
3. Puedes guardarlo como `Estudio_Conexion_MAS_X_MENOS.pdf`

Para descargar el proyecto completo:
1. Haz clic en Menu → Download Source
2. Se descargará un ZIP con todos los archivos

## Actualizaciones Futuras

Para actualizar el documento:
1. Abre el proyecto en Overleaf
2. Edita los archivos `.tex` según sea necesario
3. Recompila automáticamente
4. Descarga el PDF actualizado

## Notas Importantes

- Este documento es un ejemplo técnico profesional
- Contiene datos ficticios para demostración
- Reemplaza los datos reales antes de usar en producción
- Respeta los formatos y estructuras establecidos

## Información de Contacto

Documento: Estudio de Conexión Simplificado
Proyecto: Solar MAS X MENOS 141.6 kWp
Ubicación: Bucaramanga, Santander - Colombia
Empresa: COPOWER LTDA
Fecha: Julio de 2026

## Licencia

Este template de LaTeX puede ser usado libremente para fines educativos y profesionales.

---

**Última actualización:** 29 de Julio de 2026
**Version:** 1.0
