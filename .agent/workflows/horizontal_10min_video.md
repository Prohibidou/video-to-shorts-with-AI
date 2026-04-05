---
description: Crear un Video Apologético en Formato Horizontal 16:9 (~10 minutos) con Gancho Inicial Customizado
---
# Flujo de Trabajo para Videos Horizontales Apologéticos

Cuando el usuario invoque `/video_10min` o pida procesar un segmento largo horizontal con un hook en el inicio, **debes seguir al pie de la letra este workflow.**

## Pre-requisitos
El usuario debe indicar de qué segmento y video trata, y cuál es el "hook". Idealmente esta información ya está configurada previamente en un `config.json`, o la tienes en tu contexto (ej: segmento "San Justino", hook_start: 02:45). 

> [!WARNING]
> No cortes el final del video bruscamente. Asegúrate de pedirle al usuario si el final (ej: "no ha creído en vano") está correcto antes de recortarlo desde el source, extrae holgadamente unos segundos extras siempre.

## Paso 1: Extracción del Segmento (RAW)
Usa FFmpeg (`-c copy`) para extraer del `source_video.mp4` el segmento que abarque todo su discurso, **incluyendo el inicio y el final**. Guárdalo como `clip_X.mp4`. No lo renderices todavía.

## Paso 2: Subtítulos
Ejecuta el script de subtítulos sobre el RAW. 
```shell
python add_subtitles.py "ruta\del\clip_X.mp4" medium
```
Es fundamental este paso antes de quitar silencios para que los tiempos `.ass` concuerden con el RAW.

## Paso 3: Eliminación Dinámica de Silencios
Produce la versión super fluida del video principal, pasando el video que ya tiene subtítulos quemados:
```shell
python remove_silence.py "ruta\del\clip_X_sub.mp4"
```

## Paso 4: Calibrar la Cámara del Orador (Opcional pero Recomendado)
Si el orador está descentrado o tiene diseño nuevo, usa el calibrador en el video RAW para extraer un frame con rejilla. Muestra la imagen generada usando un Documento embebido (`Markdown`).
```shell
python generate_grid_overlay.py "ruta\del\clip_X.mp4" --time "00:00:20" --output "artifacts/grid_test.jpg"
```
Pregúntale al usuario sus coordenadas (W:H:X:Y) e instruyéndolo sobre la rejilla. 

## Paso 5: Generar el Layout Visual del Hook y Ensamblar!
Toma la respuesta del usuario (por ejemplo `760:490:1100:590`). Si no responde y es el mismo presentador del "Descenso de Cristo", usa por defecto `760:490:1100:590`. 
Deberás ejecutar el script constructor maestro:

```shell
python build_10min_hook.py ^
  --raw-video "ruta\del\clip_X.mp4" ^
  --ass-file "ruta\del\clip_X.ass" ^
  --sub-fluid-video "ruta\del\clip_X_sub_fluid.mp4" ^
  --screenshot "C:\Users\veram\OneDrive\Documentos\k.png" ^
  --hook-start "MarcaTiempoDeHook" ^
  --hook-end "MarcaTiempoDeHookFin" ^
  --crop-coords "760:490:1100:590" ^
  --output "ruta\del\VideoDefinitivo.mp4"
```

> [!NOTE] 
> Asegúrate de especificar las marcas de inicio `--hook-start` y fin en formato de segundos absolutos (ej. `154.0` para el equivalente de `02:34`) relativos a ese `clip_X.mp4`.

## Paso 6: Verificación Final
Informa al usuario de la métrica final (MB) y la ubicación. Pide su aprobación total.
