---
description: Extract apologetic shorts from YouTube URL following PROMPT_AND_EXPLANATION.txt
---
// turbo-all

Este workflow ejecuta el proceso completo de extracción de Shorts apologéticos.

**Objetivo:** Analizar un video de YouTube y extraer los segmentos más impactantes para convertir evangélicos/protestantes a católicos.

---

## Análisis de Transcripción (SIN API externa)

**IMPORTANTE:** El análisis de la transcripción para determinar timestamps lo hace Claude directamente al leer la transcripción. **NO se necesita API key de Gemini ni ninguna API externa.**

Proceso:
1. Se descarga la transcripción del video (VTT/subtítulos)
2. Claude lee la transcripción completa
3. Claude identifica los segmentos más impactantes
4. Claude define los timestamps (start/end) para cada short
5. Se genera `segments.json` con las recomendaciones

---

## Reglas de Duración (IMPORTANTE)

### Shorts Originales: ~1 MINUTO
- **Duración objetivo:** 55-65 segundos (NO 40 segundos)
- **Antes de definir el end_time:** Verificar que el contenido adicional (hasta completar 1 min) siga profundizando el MISMO argumento
- **Si al extender a 1 minuto cambia de tema:** Mantener el corte natural antes del cambio de tema
- **Priorizar coherencia argumental sobre duración exacta**

### Extended Videos: ~3 MINUTOS
- Comienzan en el mismo timestamp que el short
- Duración: 3 minutos
- Formato vertical 9:16 igual que shorts
- Usar `generate_extended.py` después de crear los shorts

### Criterio de Extensión
Al analizar la transcripción para definir timestamps:
1. Identificar el ARGUMENTO CENTRAL del segmento
2. Leer la transcripción hasta 1 minuto desde el inicio
3. Verificar que TODO el contenido adicional PROFUNDIZA ese argumento
4. Si hay cambio de tema, cortar ANTES del cambio
5. El short debe tener un cierre natural, no cortado abruptamente

---

## Gancho Visual (Hook) - Primeros ~4 Segundos

Los shorts generados incluyen un **texto de gancho fijo** en los primeros ~4 segundos:
- **Texto grande y fijo** (no palabra por palabra) que resume la premisa
- **Visible desde el segundo 0** hasta que termina la frase del gancho (~4s)
- **Después del gancho**: subtítulos normales aparecen palabra por palabra
- El texto del gancho se extrae automáticamente de la transcripción

---

## Almacenamiento Local y Base de Datos

### Estructura de Carpetas
```
output/
├── source_video.mp4          # Video fuente descargado
└── clips/
    └── [Nombre_del_Video]/
        ├── 01_Titulo_Short_1/
        │   ├── clip_01_Titulo.mp4
        │   └── extended/
        │       └── clip_01_Titulo_EXTENDED.mp4
        ├── 02_Titulo_Short_2/
        │   ├── clip_02_Titulo.mp4
        │   └── extended/
        └── ...
```

### Base de Datos SQLite (`shorts_tracker.db`)
Tablas principales:
- **videos**: URL, título, carpeta de clips
- **shorts**: título, timestamps, estado (pending/approved/rejected), carpeta
- **extended_videos**: vinculados a shorts, duración 3 min
- **long_videos**: vinculados a shorts, duración 10+ min

### Scripts de Base de Datos
- `database.py`: Funciones CRUD para todas las entidades
- `import_clips.py`: Importar clips existentes a la BD
- `manage_shorts.py`: CLI para gestionar shorts

---

## UI Web para Gestión (`shorts_ui.py`)

Servidor web en `http://localhost:5000` para gestionar shorts visualmente.

### Funcionalidades:
- **Selector de video**: Dropdown para elegir video
- **Cards de shorts**: Muestra cada short con estado (pending/approved/rejected)
- **Modal Extended/Long**: Al hacer clic en botones, muestra lista de videos con botones Aprobar/Rechazar
- **Abrir carpeta**: Botón para abrir carpeta en Explorer

### Endpoints API:
```
GET  /api/videos                    - Lista videos
GET  /api/videos/{id}/shorts        - Shorts por video
GET  /api/shorts/{id}/extended      - Extended por short
GET  /api/shorts/{id}/long          - Long por short
POST /api/shorts/{id}/status        - Cambiar estado short
POST /api/extended/{id}/status      - Cambiar estado extended
POST /api/long/{id}/status          - Cambiar estado long
POST /api/open-folder               - Abrir carpeta en Explorer
```

### Iniciar UI:
```bash
python shorts_ui.py
# Abrir http://localhost:5000
```

---

## Pasos del Workflow Completo

1. **Preparación**: Lee el contexto del prompt apologético
```
Contexto desde PROMPT_AND_EXPLANATION.txt:
- Target: Evangélicos/Protestantes
- Criterio: Incomodidad teológica (disonancia cognitiva)
- Gancho: Primeros 2 segundos deben captar atención
- Palabras clave: herejía, protestante, iglesia primitiva, eucaristía, infierno, salvación
```

2. **Ejecutar pipeline completo**:
```bash
python auto_extract.py "{{URL_DEL_VIDEO}}"
```

Esto ejecutará automáticamente:
- Descarga de subtítulos
- Análisis de contenido con filtro apologético
- Selección de los 8 mejores segmentos
- Extracción de clips con subtítulos en español
- Reemplazo "protestante" → "protestantes (Evangelicos)"

3. **Generar Extended** (después de crear shorts):
```bash
python generate_extended.py
```

4. **Generar Long** (opcional, videos de 10 min):
```bash
python generate_long.py
```

5. **Gestionar en UI**:
```bash
python shorts_ui.py
# Abrir http://localhost:5000 para aprobar/rechazar
# Preview de videos directamente en el navegador
```

---

## Notas Finales
- Clips optimizados para YouTube Shorts (vertical 9:16)
- Subtítulos hardcoded con estilo bold
- **Modelo Whisper 'small' siempre** (NUNCA usar 'tiny' - calidad insuficiente)
- Videos se procesan uno a uno para evitar problemas de RAM
- El análisis lo hace Claude directamente, sin APIs externas
