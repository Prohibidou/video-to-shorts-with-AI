"""
Database module for tracking videos and shorts.
Uses SQLite for local storage.
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

DATABASE_PATH = Path(__file__).parent / "shorts_tracker.db"


def get_connection():
    """Get database connection."""
    return sqlite3.connect(DATABASE_PATH)


def init_db():
    """Initialize database tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Video table - stores source video info
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            full_transcript TEXT,
            clips_folder TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Shorts table - stores each short with reference to source video
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shorts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER NOT NULL,
            title TEXT,
            summary TEXT,
            script TEXT,
            start_time TEXT,
            end_time TEXT,
            output_filename TEXT,
            folder_path TEXT,
            selection_reason TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (video_id) REFERENCES videos(id)
        )
    ''')
    
    # Extended videos (3 min) - related to a short
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS extended_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_id INTEGER NOT NULL,
            title TEXT,
            summary TEXT,
            script TEXT,
            duration_seconds INTEGER,
            output_filename TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (short_id) REFERENCES shorts(id)
        )
    ''')
    
    # Long videos (10+ min) - related to a short
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS long_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_id INTEGER NOT NULL,
            title TEXT,
            summary TEXT,
            script TEXT,
            duration_seconds INTEGER,
            output_filename TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (short_id) REFERENCES shorts(id)
        )
    ''')
    
    # Migrate existing table if columns are missing
    try:
        cursor.execute("ALTER TABLE shorts ADD COLUMN selection_reason TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE shorts ADD COLUMN status TEXT DEFAULT 'pending'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE videos ADD COLUMN clips_folder TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE shorts ADD COLUMN folder_path TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE shorts ADD COLUMN hook_text TEXT")
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized at: {DATABASE_PATH}")


def save_video(url: str, title: str = None, transcript: str = None, clips_folder: str = None) -> int:
    """
    Save or update a video in the database.
    Returns the video ID.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM videos WHERE url = ?", (url,))
    result = cursor.fetchone()
    
    if result:
        video_id = result[0]
        # Update fields if provided
        updates = []
        values = []
        if transcript:
            updates.append("full_transcript = ?")
            values.append(transcript)
        if title:
            updates.append("title = ?")
            values.append(title)
        if clips_folder:
            updates.append("clips_folder = ?")
            values.append(clips_folder)
        if updates:
            values.append(video_id)
            cursor.execute(f"UPDATE videos SET {', '.join(updates)} WHERE id = ?", values)
    else:
        cursor.execute(
            "INSERT INTO videos (url, title, full_transcript, clips_folder) VALUES (?, ?, ?, ?)",
            (url, title, transcript, clips_folder)
        )
        video_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return video_id


def save_short(
    video_id: int,
    title: str,
    summary: str,
    script: str,
    start_time: str,
    end_time: str,
    output_filename: str,
    selection_reason: str = None,
    folder_path: str = None,
    hook_text: str = None
) -> int:
    """
    Save a short to the database.
    
    Args:
        video_id: Source video ID
        title: Clip name
        summary: Brief summary
        script: ACTUAL audio transcription of the short
        start_time: Start timestamp (MM:SS)
        end_time: End timestamp (MM:SS)
        output_filename: .mp4 file
        selection_reason: Detailed explanation of why this clip was selected
                          (includes theological justification, apologetic impact, key quotes, etc.)
        folder_path: Folder where the short is saved
        hook_text: Visual hook text (if exists)
    
    Returns: Short ID
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO shorts (video_id, title, summary, script, start_time, end_time, 
                           output_filename, selection_reason, folder_path, hook_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (video_id, title, summary, script, start_time, end_time, 
          output_filename, selection_reason, folder_path, hook_text))
    
    short_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return short_id


def update_short_reason(short_id: int, selection_reason: str):
    """Update selection reason for an existing short."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE shorts SET selection_reason = ? WHERE id = ?", 
                   (selection_reason, short_id))
    conn.commit()
    conn.close()


def update_short_status(short_id: int, status: str):
    """
    Update status of a short.
    
    Valid statuses:
        - 'pending': Not yet reviewed
        - 'approved': Selected for YouTube upload
        - 'rejected': Not selected for upload
    """
    if status not in ('pending', 'approved', 'rejected'):
        raise ValueError(f"Invalid status: {status}. Use 'pending', 'approved', or 'rejected'")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE shorts SET status = ? WHERE id = ?", (status, short_id))
    conn.commit()
    conn.close()


def approve_short(short_id: int):
    """Mark a short as approved for YouTube upload."""
    update_short_status(short_id, 'approved')


def reject_short(short_id: int):
    """Mark a short as rejected (not for upload)."""
    update_short_status(short_id, 'rejected')


def update_extended_video_status(video_id: int, status: str):
    """Update status of an extended video."""
    if status not in ('pending', 'approved', 'rejected'):
        raise ValueError(f"Invalid status: {status}")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE extended_videos SET status = ? WHERE id = ?", (status, video_id))
    conn.commit()
    conn.close()


def update_long_video_status(video_id: int, status: str):
    """Update status of a long video."""
    if status not in ('pending', 'approved', 'rejected'):
        raise ValueError(f"Invalid status: {status}")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE long_videos SET status = ? WHERE id = ?", (status, video_id))
    conn.commit()
    conn.close()


def get_pending_shorts() -> list[dict]:
    """Get all shorts pending review."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, start_time, end_time, output_filename FROM shorts WHERE status = 'pending'")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "start": r[2], "end": r[3], "filename": r[4]} for r in rows]


def get_approved_shorts() -> list[dict]:
    """Get all shorts approved for YouTube."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, start_time, end_time, output_filename FROM shorts WHERE status = 'approved'")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "start": r[2], "end": r[3], "filename": r[4]} for r in rows]


def get_video_by_url(url: str) -> Optional[dict]:
    """Get video by URL."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM videos WHERE url = ?", (url,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "url": row[1],
            "title": row[2],
            "full_transcript": row[3],
            "created_at": row[4]
        }
    return None


def get_shorts_by_video(video_id: int) -> list[dict]:
    """Get all shorts for a video."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, video_id, title, summary, script, start_time, end_time, 
               output_filename, folder_path, selection_reason, status, created_at, hook_text
        FROM shorts WHERE video_id = ?
        ORDER BY id
    """, (video_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "id": row[0],
        "video_id": row[1],
        "title": row[2],
        "summary": row[3],
        "script": row[4],
        "start_time": row[5],
        "end_time": row[6],
        "output_filename": row[7],
        "folder_path": row[8],
        "selection_reason": row[9],
        "status": row[10],
        "created_at": row[11],
        "hook_text": row[12]
    } for row in rows]


def get_all_videos() -> list[dict]:
    """Get all videos in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, url, title, clips_folder, created_at FROM videos ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "id": row[0],
        "url": row[1],
        "title": row[2],
        "clips_folder": row[3],
        "created_at": row[4]
    } for row in rows]


def get_all_shorts() -> list[dict]:
    """Get all shorts with video info."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.*, v.url, v.title as video_title
        FROM shorts s
        JOIN videos v ON s.video_id = v.id
        ORDER BY s.created_at DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "id": row[0],
        "video_id": row[1],
        "title": row[2],
        "summary": row[3],
        "script": row[4],
        "start_time": row[5],
        "end_time": row[6],
        "output_filename": row[7],
        "selection_reason": row[8],
        "created_at": row[9],
        "video_url": row[10],
        "video_title": row[11]
    } for row in rows]


def save_extended_video(
    short_id: int,
    title: str = None,
    summary: str = None,
    script: str = None,
    duration_seconds: int = None,
    output_filename: str = None
) -> int:
    """Save an extended video (3 min) related to a short."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO extended_videos 
        (short_id, title, summary, script, duration_seconds, output_filename)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (short_id, title, summary, script, duration_seconds, output_filename))
    
    extended_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return extended_id


def save_long_video(
    short_id: int,
    title: str = None,
    summary: str = None,
    script: str = None,
    duration_seconds: int = None,
    output_filename: str = None
) -> int:
    """Save a long video (10+ min) related to a short."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO long_videos 
        (short_id, title, summary, script, duration_seconds, output_filename)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (short_id, title, summary, script, duration_seconds, output_filename))
    
    long_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return long_id


def get_extended_videos_by_short(short_id: int) -> list[dict]:
    """Get all extended videos for a short."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, short_id, title, summary, script, duration_seconds, 
               output_filename, status, created_at
        FROM extended_videos WHERE short_id = ?
        ORDER BY created_at
    ''', (short_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "id": row[0],
        "short_id": row[1],
        "title": row[2],
        "summary": row[3],
        "script": row[4],
        "duration_seconds": row[5],
        "output_filename": row[6],
        "status": row[7],
        "created_at": row[8]
    } for row in rows]


def get_long_videos_by_short(short_id: int) -> list[dict]:
    """Get all long videos for a short."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, short_id, title, summary, script, duration_seconds, 
               output_filename, status, created_at
        FROM long_videos WHERE short_id = ?
        ORDER BY created_at
    ''', (short_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "id": row[0],
        "short_id": row[1],
        "title": row[2],
        "summary": row[3],
        "script": row[4],
        "duration_seconds": row[5],
        "output_filename": row[6],
        "status": row[7],
        "created_at": row[8]
    } for row in rows]


def update_short_folder(short_id: int, folder_path: str):
    """Update the folder path for a short."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE shorts SET folder_path = ? WHERE id = ?", (folder_path, short_id))
    conn.commit()
    conn.close()


# Initialize database on import
init_db()
