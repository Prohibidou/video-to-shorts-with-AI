import sqlite3

conn = sqlite3.connect('shorts_tracker.db')
conn.execute("UPDATE videos SET title = 'San Ignacio de Antioquía - Carta a los efesios cap 1 - Notas apologéticas' WHERE url = 'https://www.youtube.com/watch?v=JxAdV9YVbsY'")
conn.commit()
conn.close()
print("✅ Título actualizado")
