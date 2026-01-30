---
description: Extract apologetic shorts from YouTube URL following PROMPT_AND_EXPLANATION.txt
---
// turbo-all

Este workflow ejecuta el proceso completo de extracción de Shorts apologéticos siguiendo las instrucciones definidas en PROMPT_AND_EXPLANATION.txt.

**Objetivo:** Analizar un video de YouTube y extraer los segmentos más impactantes para convertir evangélicos/protestantes a católicos, con ganchos potentes en los primeros 2 segundos.

## Pasos del Workflow

1. **Preparación**: Lee el contexto del prompt apologético
```
Contexto cargado desde PROMPT_AND_EXPLANATION.txt:
- Target: Evangélicos/Protestantes
- Criterio: Incomodidad teológica (disonancia cognitiva)
- Gancho: Primeros 2 segundos deben captar atención
- Palabras clave prioritarias: herejía, protestante, iglesia primitiva, eucaristía, infierno, salvación
```

2. **Ejecutar pipeline completo**:
python auto_extract.py "{{URL_DEL_VIDEO}}"

Esto ejecutará automáticamente:
- Descarga de subtítulos
- Análisis de contenido con filtro apologético
- Selección de los 8 mejores segmentos según criterios del prompt
- Extracción y procesamiento de clips con subtítulos en español
- Reemplazo automático de "protestante/protestantes" → "protestantes (Evangelicos)"

## Notas
- No se requiere intervención manual en ningún paso
- Los clips generados están optimizados para YouTube Shorts (vertical 9:16)
- Subtítulos hardcoded con estilo bold
- Modelo Whisper 'small' para mejor calidad de transcripción
