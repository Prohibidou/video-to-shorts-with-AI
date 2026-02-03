"""
Script para gestionar shorts: aprobar, rechazar, ver pendientes.
Uso:
    python manage_shorts.py list          # Ver todos los shorts pendientes
    python manage_shorts.py approve 1     # Aprobar short ID 1
    python manage_shorts.py reject 2      # Rechazar short ID 2
    python manage_shorts.py approved      # Ver shorts aprobados
"""
import sys
from database import (
    get_pending_shorts, get_approved_shorts, 
    approve_short, reject_short, get_all_shorts
)

def list_pending():
    """Muestra shorts pendientes de revisión."""
    shorts = get_pending_shorts()
    if not shorts:
        print("✅ No hay shorts pendientes de revisión")
        return
    
    print(f"\n📋 SHORTS PENDIENTES ({len(shorts)}):")
    print("-" * 60)
    for s in shorts:
        print(f"  ID: {s['id']} | {s['title']}")
        print(f"      {s['start']} → {s['end']} | {s['filename']}")
        print()

def list_approved():
    """Muestra shorts aprobados para YouTube."""
    shorts = get_approved_shorts()
    if not shorts:
        print("⚠️ No hay shorts aprobados aún")
        return
    
    print(f"\n✅ SHORTS APROBADOS PARA YOUTUBE ({len(shorts)}):")
    print("-" * 60)
    for s in shorts:
        print(f"  ID: {s['id']} | {s['title']} | {s['filename']}")

def do_approve(short_id):
    """Aprueba un short."""
    approve_short(int(short_id))
    print(f"✅ Short ID {short_id} APROBADO para YouTube")

def do_reject(short_id):
    """Rechaza un short."""
    reject_short(int(short_id))
    print(f"❌ Short ID {short_id} RECHAZADO")

def show_all():
    """Muestra todos los shorts con su estado."""
    shorts = get_all_shorts()
    print(f"\n📊 TODOS LOS SHORTS ({len(shorts)}):")
    print("-" * 70)
    for s in shorts:
        status_icon = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(s.get('status', 'pending'), "❓")
        print(f"  {status_icon} ID: {s['id']} | {s['title']} | {s['start_time']} → {s['end_time']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "list":
        list_pending()
    elif cmd == "approved":
        list_approved()
    elif cmd == "all":
        show_all()
    elif cmd == "approve" and len(sys.argv) > 2:
        do_approve(sys.argv[2])
    elif cmd == "reject" and len(sys.argv) > 2:
        do_reject(sys.argv[2])
    else:
        print("Comando no reconocido. Usa: list, approved, all, approve <id>, reject <id>")
