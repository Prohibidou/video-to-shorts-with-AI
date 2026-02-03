"""Script para importar clips existentes a la base de datos."""
from database import save_video, save_short
import json

# Leer segments.json
with open('segments.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

url = data['video_url']
segments = data['segments']

# Guardar video
video_id = save_video(url, 'San Ignacio de Antioquia', None)
print(f'Video guardado ID: {video_id}, URL: {url}')

# Guardar cada short
for i, seg in enumerate(segments, 1):
    name = seg['name']
    filename = f'clip_{i:02d}_{name}.mp4'
    short_id = save_short(
        video_id=video_id,
        title=name.replace('_', ' '),
        summary=f'Clip {i}',
        script='',
        start_time=seg['start'],
        end_time=seg['end'],
        output_filename=filename
    )
    print(f'  Short {i}: {name} ({seg["start"]} - {seg["end"]})')

print('\n✅ Datos importados correctamente!')
