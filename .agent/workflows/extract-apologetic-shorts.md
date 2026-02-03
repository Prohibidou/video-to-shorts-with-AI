---
description: Extract apologetic shorts from YouTube URL following PROMPT_AND_EXPLANATION.txt
---
// turbo-all

Este workflow ejecuta el proceso completo de extracción de Shorts apologéticos siguiendo las instrucciones definidas en PROMPT_AND_EXPLANATION.txt.

**Objetivo:** Analizar un video de YouTube y extraer los segmentos más impactantes para convertir evangélicos/protestantes a católicos, con ganchos potentes en los primeros 2 segundos.

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

3. **Generar Extended** (después de crear shorts):
python generate_extended.py

## Notas
- No se requiere intervención manual en ningún paso
- Los clips generados están optimizados para YouTube Shorts (vertical 9:16)
- Subtítulos hardcoded con estilo bold
- Modelo Whisper 'small' para mejor calidad de transcripción

