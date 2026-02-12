"""
Web server for managing shorts with visual UI.
Shows ALL shorts from the database (including deleted files).

Run: python shorts_ui.py
Open: http://localhost:5000
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
from pathlib import Path
from database import (
    get_all_shorts, get_all_videos, approve_short, reject_short,
    update_short_status, get_shorts_by_video,
    get_extended_videos_by_short, get_long_videos_by_short,
    update_extended_video_status, update_long_video_status,
    get_connection
)

PORT = 5000


def check_file_exists(short: dict) -> bool:
    """Check if a short's file still exists on disk."""
    folder_path = short.get('folder_path', '')
    output_file = short.get('output_filename', '')
    
    if folder_path and os.path.exists(folder_path):
        return True
    if output_file and os.path.exists(output_file):
        return True
    if output_file:
        clips_path = Path("output/clips")
        if clips_path.exists():
            found = list(clips_path.rglob(output_file))
            if found:
                return True
    return False


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shorts Manager</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
            background: #0a0a0f;
            min-height: 100vh;
            color: #e2e8f0;
        }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(233, 69, 96, 0.1));
            border-bottom: 1px solid rgba(255,255,255,0.06);
            padding: 24px 40px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .header h1 {
            font-size: 1.8rem;
            font-weight: 800;
            background: linear-gradient(135deg, #a78bfa, #e94560);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }
        
        /* Layout */
        .layout {
            display: flex;
            min-height: calc(100vh - 80px);
        }
        
        /* Sidebar */
        .sidebar {
            width: 320px;
            min-width: 320px;
            background: rgba(255,255,255,0.02);
            border-right: 1px solid rgba(255,255,255,0.06);
            padding: 24px;
            overflow-y: auto;
        }
        .sidebar h2 {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: #64748b;
            margin-bottom: 16px;
            font-weight: 600;
        }
        .video-card {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .video-card:hover {
            background: rgba(139, 92, 246, 0.08);
            border-color: rgba(139, 92, 246, 0.3);
        }
        .video-card.active {
            background: rgba(139, 92, 246, 0.12);
            border-color: #8b5cf6;
        }
        .video-card .title {
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 6px;
            line-height: 1.3;
        }
        .video-card .url {
            font-size: 0.75rem;
            color: #64748b;
            word-break: break-all;
        }
        .video-card .count {
            display: inline-block;
            background: rgba(139, 92, 246, 0.2);
            color: #a78bfa;
            font-size: 0.75rem;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 10px;
            margin-top: 8px;
        }
        
        /* Main content */
        .main {
            flex: 1;
            padding: 32px 40px;
            overflow-y: auto;
        }
        
        /* Stats row */
        .stats-row {
            display: flex;
            gap: 16px;
            margin-bottom: 32px;
        }
        .stat-pill {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            border-radius: 100px;
            font-size: 0.9rem;
            font-weight: 600;
        }
        .stat-pill.approved { background: rgba(74, 222, 128, 0.1); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.2); }
        .stat-pill.rejected { background: rgba(248, 113, 113, 0.1); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.2); }
        .stat-pill.pending { background: rgba(251, 191, 36, 0.1); color: #fbbf24; border: 1px solid rgba(251, 191, 36, 0.2); }
        .stat-pill .num { font-size: 1.1rem; font-weight: 800; }
        
        /* Short cards */
        .shorts-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .short-card {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 14px;
            overflow: hidden;
            transition: all 0.2s;
        }
        .short-card:hover {
            border-color: rgba(255,255,255,0.12);
        }
        .short-card.approved { border-left: 3px solid #4ade80; }
        .short-card.rejected { border-left: 3px solid #f87171; }
        .short-card.pending { border-left: 3px solid #fbbf24; }
        
        /* Card header (always visible) */
        .card-header {
            display: flex;
            align-items: center;
            padding: 18px 20px;
            cursor: pointer;
            gap: 16px;
            user-select: none;
        }
        .card-header:hover {
            background: rgba(255,255,255,0.02);
        }
        .expand-arrow {
            font-size: 0.8rem;
            color: #64748b;
            transition: transform 0.2s;
            flex-shrink: 0;
        }
        .short-card.expanded .expand-arrow {
            transform: rotate(90deg);
        }
        .card-info { flex: 1; min-width: 0; }
        .card-title {
            font-size: 1.05rem;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .card-meta {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            align-items: center;
        }
        .meta-tag {
            font-size: 0.8rem;
            color: #94a3b8;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .hook-preview {
            font-size: 0.85rem;
            color: #c084fc;
            font-style: italic;
            margin-top: 6px;
            display: -webkit-box;
            -webkit-line-clamp: 1;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .status-badge {
            padding: 4px 14px;
            border-radius: 100px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            flex-shrink: 0;
        }
        .status-badge.approved { background: rgba(74, 222, 128, 0.15); color: #4ade80; }
        .status-badge.rejected { background: rgba(248, 113, 113, 0.15); color: #f87171; }
        .status-badge.pending { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
        .file-indicator {
            font-size: 0.75rem;
            flex-shrink: 0;
        }
        
        /* Card actions (always visible) */
        .card-actions {
            display: flex;
            gap: 6px;
            flex-shrink: 0;
        }
        .btn-sm {
            padding: 6px 14px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 600;
            transition: all 0.15s;
        }
        .btn-sm:hover { transform: scale(1.05); }
        .btn-sm:disabled { opacity: 0.3; cursor: not-allowed; transform: none; }
        .btn-approve { background: #4ade80; color: #000; }
        .btn-reject { background: #f87171; color: #fff; }
        
        /* Card detail panel (expandable) */
        .card-detail {
            display: none;
            border-top: 1px solid rgba(255,255,255,0.06);
            padding: 24px;
            background: rgba(0,0,0,0.2);
        }
        .short-card.expanded .card-detail {
            display: block;
        }
        
        .detail-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 24px;
        }
        .detail-section {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 10px;
            padding: 16px;
        }
        .detail-section.full-width {
            grid-column: 1 / -1;
        }
        .detail-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #64748b;
            margin-bottom: 8px;
            font-weight: 600;
        }
        .detail-value {
            font-size: 0.95rem;
            line-height: 1.6;
        }
        .detail-value.hook {
            color: #c084fc;
            font-size: 1.1rem;
            font-weight: 600;
            font-style: italic;
        }
        .detail-value.script {
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.88rem;
            white-space: pre-wrap;
            max-height: 400px;
            overflow-y: auto;
            padding-right: 10px;
            color: #cbd5e1;
            line-height: 1.7;
        }
        .detail-value.script::-webkit-scrollbar {
            width: 6px;
        }
        .detail-value.script::-webkit-scrollbar-track {
            background: rgba(255,255,255,0.03);
            border-radius: 3px;
        }
        .detail-value.script::-webkit-scrollbar-thumb {
            background: rgba(255,255,255,0.15);
            border-radius: 3px;
        }
        .detail-value.reason {
            color: #94a3b8;
            font-size: 0.9rem;
        }
        
        /* Empty state */
        .empty-state {
            text-align: center;
            padding: 80px 20px;
            color: #64748b;
        }
        .empty-state .icon { font-size: 3rem; margin-bottom: 16px; }
        .empty-state h3 { font-size: 1.2rem; margin-bottom: 8px; color: #94a3b8; }
        
        /* YouTube link */
        .youtube-link {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: white;
            text-decoration: none;
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.9rem;
            margin-bottom: 24px;
            transition: transform 0.15s;
        }
        .youtube-link:hover { transform: scale(1.03); }
        
        /* Video actions bar */
        .video-actions {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }
        
        .folder-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 10px 20px;
            background: rgba(139, 92, 246, 0.15);
            color: #a78bfa;
            border: 1px solid rgba(139, 92, 246, 0.3);
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.15s;
        }
        .folder-btn:hover { background: rgba(139, 92, 246, 0.25); }

        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.85);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            backdrop-filter: blur(4px);
        }
        .modal-overlay.active { display: flex; }
        .modal-content {
            background: #12121a;
            border-radius: 16px;
            padding: 30px;
            max-width: 800px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .modal-close {
            background: rgba(248,113,113,0.2);
            border: 1px solid rgba(248,113,113,0.3);
            color: #f87171;
            width: 36px; height: 36px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 1.2rem;
            transition: all 0.15s;
        }
        .modal-close:hover { background: rgba(248,113,113,0.4); }
        .video-list { display: flex; flex-direction: column; gap: 15px; }
        .video-item {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 12px;
            border-left: 4px solid #8b5cf6;
        }
        .video-item.long { border-left-color: #ec4899; }
        .video-item h4 { margin: 0 0 8px 0; }
        .video-item p { margin: 5px 0; opacity: 0.8; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎬 Shorts Manager</h1>
    </div>
    
    <div class="layout">
        <div class="sidebar">
            <h2>📺 Videos</h2>
            <div id="video-list"></div>
        </div>
        
        <div class="main" id="main-content">
            <div class="empty-state">
                <div class="icon">👈</div>
                <h3>Seleccioná un video</h3>
                <p>Elegí un video de la barra lateral para ver sus shorts</p>
            </div>
        </div>
    </div>
    
    <!-- Modal for Extended/Long videos -->
    <div id="modal" class="modal-overlay" onclick="closeModal(event)">
        <div class="modal-content" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h2 id="modal-title">Videos</h2>
                <button class="modal-close" onclick="closeModal()">✕</button>
            </div>
            <div id="modal-body" class="video-list"></div>
        </div>
    </div>
    
    <script>
        let videos = [];
        let shorts = [];
        let selectedVideoId = null;
        let selectedVideoUrl = '';
        let selectedClipsFolder = '';
        let currentShortId = null;
        let currentModalType = '';
        
        async function loadVideos() {
            try {
                const res = await fetch('/api/videos');
                videos = await res.json();
                
                const list = document.getElementById('video-list');
                if (videos.length === 0) {
                    list.innerHTML = '<div class="empty-state"><p>No videos in database</p></div>';
                    return;
                }
                
                list.innerHTML = videos.map(v => {
                    const title = v.title || 'Untitled';
                    return `
                        <div class="video-card" id="vc-${v.id}" onclick="selectVideo(${v.id})">
                            <div class="title">${escapeHtml(title)}</div>
                            <div class="url">${escapeHtml(v.url)}</div>
                            <span class="count" id="vc-count-${v.id}">Loading...</span>
                        </div>
                    `;
                }).join('');
                
                // Load counts for each video
                for (const v of videos) {
                    const res = await fetch('/api/videos/' + v.id + '/shorts');
                    const s = await res.json();
                    const el = document.getElementById('vc-count-' + v.id);
                    if (el) el.textContent = s.length + ' short' + (s.length !== 1 ? 's' : '');
                }
            } catch (err) {
                console.error('Error loading videos:', err);
            }
        }
        
        async function selectVideo(videoId) {
            selectedVideoId = videoId;
            
            // Update sidebar active state
            document.querySelectorAll('.video-card').forEach(c => c.classList.remove('active'));
            const card = document.getElementById('vc-' + videoId);
            if (card) card.classList.add('active');
            
            const selectedVideo = videos.find(v => v.id == videoId);
            selectedVideoUrl = selectedVideo ? selectedVideo.url : '';
            selectedClipsFolder = selectedVideo ? (selectedVideo.clips_folder || '') : '';
            
            const res = await fetch('/api/videos/' + videoId + '/shorts');
            shorts = await res.json();
            renderContent();
        }
        
        function renderContent() {
            const pending = shorts.filter(s => (s.status || 'pending') === 'pending').length;
            const approved = shorts.filter(s => s.status === 'approved').length;
            const rejected = shorts.filter(s => s.status === 'rejected').length;
            
            let html = `
                <div class="video-actions">
                    <a href="${selectedVideoUrl}" target="_blank" class="youtube-link">
                        ▶️ Ver en YouTube
                    </a>
                    ${selectedClipsFolder ? `
                        <button onclick="openFolder('${escapeJs(selectedClipsFolder)}')" class="folder-btn">
                            📁 Abrir carpeta
                        </button>
                    ` : ''}
                </div>
                
                <div class="stats-row">
                    <div class="stat-pill approved"><span class="num">${approved}</span> Aprobados</div>
                    <div class="stat-pill rejected"><span class="num">${rejected}</span> Rechazados</div>
                    <div class="stat-pill pending"><span class="num">${pending}</span> Pendientes</div>
                </div>
                
                <div class="shorts-list">
            `;
            
            if (shorts.length === 0) {
                html += '<div class="empty-state"><div class="icon">📭</div><h3>No hay shorts para este video</h3></div>';
            } else {
                shorts.forEach((s, idx) => {
                    const status = s.status || 'pending';
                    const hookPreview = s.hook_text ? escapeHtml(s.hook_text) : '';
                    const fileExists = s.file_exists;
                    const fileIcon = fileExists ? '📁' : '⚠️';
                    const fileLabel = fileExists ? 'Archivo existe' : 'Archivo eliminado';
                    
                    html += `
                        <div class="short-card ${status}" id="sc-${idx}">
                            <div class="card-header" onclick="toggleCard(${idx})">
                                <span class="expand-arrow">▶</span>
                                <div class="card-info">
                                    <div class="card-title">${escapeHtml(s.title || 'Sin título')}</div>
                                    <div class="card-meta">
                                        <span class="meta-tag">⏱ ${s.start_time} → ${s.end_time}</span>
                                        <span class="meta-tag">${fileIcon} ${fileLabel}</span>
                                        <span class="meta-tag">📅 ${s.created_at ? s.created_at.split('T')[0] : 'N/A'}</span>
                                    </div>
                                    ${hookPreview ? `<div class="hook-preview">🎣 "${hookPreview}"</div>` : ''}
                                </div>
                                <span class="status-badge ${status}">${status}</span>
                                <div class="card-actions" onclick="event.stopPropagation()">
                                    <a href="/short/${s.id}" target="_blank" class="btn-sm" 
                                        style="background:rgba(139,92,246,0.3);color:#c4b5fd;text-decoration:none;display:inline-flex;align-items:center;">📄</a>
                                    <button class="btn-sm btn-approve" onclick="setStatus(${s.id}, 'approved')" 
                                        ${status === 'approved' ? 'disabled' : ''}>✓</button>
                                    <button class="btn-sm btn-reject" onclick="setStatus(${s.id}, 'rejected')"
                                        ${status === 'rejected' ? 'disabled' : ''}>✗</button>
                                </div>
                            </div>
                            <div class="card-detail">
                                <div class="detail-grid">
                                    ${s.hook_text ? `
                                    <div class="detail-section full-width">
                                        <div class="detail-label">🎣 Hook</div>
                                        <div class="detail-value hook">"${escapeHtml(s.hook_text)}"</div>
                                    </div>
                                    ` : ''}
                                    
                                    ${s.summary ? `
                                    <div class="detail-section full-width">
                                        <div class="detail-label">📝 Resumen</div>
                                        <div class="detail-value">${escapeHtml(s.summary)}</div>
                                    </div>
                                    ` : ''}
                                    
                                    <div class="detail-section">
                                        <div class="detail-label">⏱ Timestamps</div>
                                        <div class="detail-value">${s.start_time} → ${s.end_time}</div>
                                    </div>
                                    
                                    <div class="detail-section">
                                        <div class="detail-label">📋 Estado</div>
                                        <div class="detail-value">
                                            <span class="status-badge ${status}" style="font-size: 0.85rem;">${status.toUpperCase()}</span>
                                        </div>
                                    </div>
                                    
                                    <div class="detail-section">
                                        <div class="detail-label">📁 Archivo</div>
                                        <div class="detail-value" style="font-size: 0.8rem; word-break: break-all;">
                                            ${fileIcon} ${escapeHtml(s.output_filename || s.folder_path || 'N/A')}<br>
                                            <span style="color: ${fileExists ? '#4ade80' : '#f87171'};">${fileLabel}</span>
                                        </div>
                                    </div>
                                    
                                    <div class="detail-section">
                                        <div class="detail-label">📅 Creado</div>
                                        <div class="detail-value">${s.created_at || 'N/A'}</div>
                                    </div>
                                    
                                    ${s.selection_reason ? `
                                    <div class="detail-section full-width">
                                        <div class="detail-label">🧠 Razón de selección</div>
                                        <div class="detail-value reason">${escapeHtml(s.selection_reason)}</div>
                                    </div>
                                    ` : ''}
                                    
                                    <div class="detail-section full-width">
                                        <div class="detail-label">📜 Script completo</div>
                                        <div class="detail-value script">${escapeHtml(s.script || 'No hay script disponible')}</div>
                                    </div>
                                </div>
                                
                                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                                    <button onclick="showExtendedVideos(${s.id})" 
                                        style="padding: 8px 16px; background: rgba(139,92,246,0.15); color: #a78bfa; border: 1px solid rgba(139,92,246,0.3); border-radius: 8px; cursor: pointer; font-size: 0.85rem; font-weight: 600;">
                                        📂 Extended (3min)
                                    </button>
                                    <button onclick="showLongVideos(${s.id})" 
                                        style="padding: 8px 16px; background: rgba(236,72,153,0.15); color: #f472b6; border: 1px solid rgba(236,72,153,0.3); border-radius: 8px; cursor: pointer; font-size: 0.85rem; font-weight: 600;">
                                        🎬 Long (10min+)
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                });
            }
            
            html += '</div>';
            document.getElementById('main-content').innerHTML = html;
        }
        
        function toggleCard(idx) {
            const card = document.getElementById('sc-' + idx);
            if (card) card.classList.toggle('expanded');
        }
        
        async function setStatus(id, status) {
            await fetch('/api/shorts/' + id + '/status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            });
            selectVideo(selectedVideoId);
        }
        
        async function openFolder(folderPath) {
            await fetch('/api/open-folder', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({folder: folderPath})
            });
        }
        
        async function showExtendedVideos(shortId) {
            currentShortId = shortId;
            currentModalType = 'extended';
            const res = await fetch('/api/shorts/' + shortId + '/extended');
            const vids = await res.json();
            showVideoModal('Extended Videos (3min)', vids, 'extended');
        }
        
        async function showLongVideos(shortId) {
            currentShortId = shortId;
            currentModalType = 'long';
            const res = await fetch('/api/shorts/' + shortId + '/long');
            const vids = await res.json();
            showVideoModal('Long Videos (10min+)', vids, 'long');
        }
        
        function showVideoModal(title, vids, type) {
            document.getElementById('modal-title').textContent = title;
            const body = document.getElementById('modal-body');
            
            if (vids.length === 0) {
                const cmd = type === 'extended' ? 'python generate_extended.py' : 'python generate_long.py';
                body.innerHTML = `<div style="text-align:center;padding:30px;opacity:0.6;">
                    No videos of this type.<br>
                    <code style="background:rgba(255,255,255,0.1);padding:5px 10px;border-radius:4px;margin-top:10px;display:inline-block;">${cmd}</code>
                </div>`;
            } else {
                body.innerHTML = vids.map(v => {
                    const status = v.status || 'pending';
                    const videoPath = v.output_filename || '';
                    const encodedPath = encodeURIComponent(videoPath);
                    return `
                    <div class="video-item ${type}">
                        <h4>${escapeHtml(v.title || 'Untitled')}</h4>
                        ${videoPath ? `
                        <video width="100%" style="max-height:300px;border-radius:8px;margin:10px 0;" controls>
                            <source src="/video/${encodedPath}" type="video/mp4">
                        </video>` : ''}
                        <p><strong>Duration:</strong> ${v.duration_seconds ? Math.floor(v.duration_seconds/60) + ' min' : 'N/A'}</p>
                        <div class="status-badge ${status}" style="display:inline-block;margin:8px 0;">${status.toUpperCase()}</div>
                        ${v.summary ? '<p>' + escapeHtml(v.summary) + '</p>' : ''}
                        <div style="display:flex;gap:10px;margin-top:10px;">
                            <button onclick="setVideoStatus('${type}',${v.id},'approved')" 
                                class="btn-sm btn-approve" style="flex:1;padding:8px;" ${status==='approved'?'disabled':''}>✓ Approve</button>
                            <button onclick="setVideoStatus('${type}',${v.id},'rejected')" 
                                class="btn-sm btn-reject" style="flex:1;padding:8px;" ${status==='rejected'?'disabled':''}>✗ Reject</button>
                        </div>
                    </div>`;
                }).join('');
            }
            
            document.getElementById('modal').classList.add('active');
        }
        
        function closeModal(event) {
            if (!event || event.target.id === 'modal') {
                document.getElementById('modal').classList.remove('active');
            }
        }
        
        async function setVideoStatus(type, videoId, status) {
            const endpoint = type === 'extended' ? '/api/extended' : '/api/long';
            await fetch(endpoint + '/' + videoId + '/status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            });
            if (type === 'extended') showExtendedVideos(currentShortId);
            else showLongVideos(currentShortId);
        }
        
        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        }
        
        function escapeJs(str) {
            if (!str) return '';
            return str.replace(/\\\\/g, '\\\\\\\\').replace(/'/g, "\\\\'");
        }
        
        // Expose to global scope
        window.selectVideo = selectVideo;
        window.setStatus = setStatus;
        window.openFolder = openFolder;
        window.showExtendedVideos = showExtendedVideos;
        window.showLongVideos = showLongVideos;
        window.closeModal = closeModal;
        window.setVideoStatus = setVideoStatus;
        window.toggleCard = toggleCard;
        
        loadVideos();
    </script>
</body>
</html>'''


DETAIL_PAGE_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Short #{short_id} - Detail</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
            background: #0a0a0f;
            min-height: 100vh;
            color: #e2e8f0;
        }
        .back-bar {
            padding: 16px 40px;
            background: rgba(255,255,255,0.02);
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }
        .back-bar a {
            color: #a78bfa;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
        }
        .back-bar a:hover { text-decoration: underline; }
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 24px;
        }
        .status-badge {
            display: inline-block;
            padding: 6px 18px;
            border-radius: 100px;
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .status-badge.approved { background: rgba(74,222,128,0.15); color: #4ade80; }
        .status-badge.rejected { background: rgba(248,113,113,0.15); color: #f87171; }
        .status-badge.pending { background: rgba(251,191,36,0.15); color: #fbbf24; }
        .title-row {
            display: flex;
            align-items: flex-start;
            gap: 16px;
            margin-bottom: 32px;
        }
        .title-row h1 {
            flex: 1;
            font-size: 1.6rem;
            font-weight: 800;
            line-height: 1.3;
            background: linear-gradient(135deg, #e2e8f0, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .section {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 14px;
            padding: 24px;
            margin-bottom: 20px;
        }
        .section-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            color: #64748b;
            margin-bottom: 12px;
            font-weight: 700;
        }
        .hook-text {
            font-size: 1.2rem;
            font-weight: 600;
            color: #c084fc;
            font-style: italic;
            line-height: 1.5;
        }
        .meta-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .meta-item .label {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #64748b;
            margin-bottom: 6px;
            font-weight: 600;
        }
        .meta-item .value {
            font-size: 1rem;
            color: #e2e8f0;
        }
        .script-text {
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.9rem;
            white-space: pre-wrap;
            line-height: 1.8;
            color: #cbd5e1;
            max-height: 600px;
            overflow-y: auto;
            padding-right: 12px;
        }
        .script-text::-webkit-scrollbar { width: 6px; }
        .script-text::-webkit-scrollbar-track { background: rgba(255,255,255,0.03); border-radius: 3px; }
        .script-text::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 3px; }
        .reason-text {
            color: #94a3b8;
            font-size: 0.95rem;
            line-height: 1.7;
        }
        .file-path {
            font-size: 0.85rem;
            word-break: break-all;
            color: #94a3b8;
        }
        .id-tag {
            font-size: 0.85rem;
            color: #64748b;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="back-bar">
        <a href="/" >← Volver a Shorts Manager</a>
    </div>
    <div class="container" id="content">
        <div style="text-align:center;padding:60px;color:#64748b;">Cargando...</div>
    </div>
    <script>
        async function loadShort() {
            const shortId = SHORT_ID_PLACEHOLDER;
            const res = await fetch('/api/short/' + shortId);
            if (!res.ok) { document.getElementById('content').innerHTML = '<p>Short no encontrado</p>'; return; }
            const s = await res.json();
            const status = s.status || 'pending';
            
            let html = `
                <div class="title-row">
                    <h1>${esc(s.title || 'Sin título')}</h1>
                    <span class="status-badge ${status}">${status.toUpperCase()}</span>
                    <span class="id-tag">ID: ${s.id}</span>
                </div>
            `;
            
            if (s.hook_text) {
                html += `
                <div class="section">
                    <div class="section-label">🎣 Hook</div>
                    <div class="hook-text">"${esc(s.hook_text)}"</div>
                </div>`;
            }
            
            html += `
                <div class="section">
                    <div class="meta-grid">
                        <div class="meta-item">
                            <div class="label">⏱ Timestamps</div>
                            <div class="value">${s.start_time} → ${s.end_time}</div>
                        </div>
                        <div class="meta-item">
                            <div class="label">📅 Creado</div>
                            <div class="value">${s.created_at || 'N/A'}</div>
                        </div>
                        <div class="meta-item">
                            <div class="label">📁 Archivo</div>
                            <div class="value file-path">${esc(s.output_filename || 'N/A')}</div>
                        </div>
                        <div class="meta-item">
                            <div class="label">📂 Carpeta</div>
                            <div class="value file-path">${esc(s.folder_path || 'N/A')}</div>
                        </div>
                    </div>
                </div>`;
            
            if (s.summary) {
                html += `
                <div class="section">
                    <div class="section-label">📝 Resumen</div>
                    <div>${esc(s.summary)}</div>
                </div>`;
            }
            
            if (s.selection_reason) {
                html += `
                <div class="section">
                    <div class="section-label">🧠 Razón de selección</div>
                    <div class="reason-text">${esc(s.selection_reason)}</div>
                </div>`;
            }
            
            html += `
                <div class="section">
                    <div class="section-label">📜 Script completo</div>
                    <div class="script-text">${esc(s.script || 'No hay script disponible')}</div>
                </div>`;
            
            document.getElementById('content').innerHTML = html;
            document.title = 'Short #' + s.id + ' - ' + (s.title || 'Detail');
        }
        
        function esc(str) {
            if (!str) return '';
            return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        }
        
        loadShort();
    </script>
</body>
</html>
'''


class ShortsHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode())
        elif self.path == '/api/videos':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            vids = get_all_videos()
            self.wfile.write(json.dumps(vids).encode())
        elif self.path.startswith('/api/videos/') and '/shorts' in self.path:
            video_id = int(self.path.split('/')[3])
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            # Return ALL shorts (including deleted files) with file_exists flag
            all_shorts = get_shorts_by_video(video_id)
            for s in all_shorts:
                s['file_exists'] = check_file_exists(s)
            self.wfile.write(json.dumps(all_shorts).encode())
        elif self.path == '/api/shorts':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            all_shorts = get_all_shorts()
            for s in all_shorts:
                s['file_exists'] = check_file_exists(s)
            self.wfile.write(json.dumps(all_shorts).encode())
        elif self.path.startswith('/api/shorts/') and '/extended' in self.path:
            short_id = int(self.path.split('/')[3])
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            extended = get_extended_videos_by_short(short_id)
            self.wfile.write(json.dumps(extended).encode())
        elif self.path.startswith('/api/shorts/') and '/long' in self.path:
            short_id = int(self.path.split('/')[3])
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            long_videos = get_long_videos_by_short(short_id)
            self.wfile.write(json.dumps(long_videos).encode())
        elif self.path.startswith('/short/'):
            try:
                short_id = int(self.path.split('/')[2])
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                page = DETAIL_PAGE_TEMPLATE.replace('SHORT_ID_PLACEHOLDER', str(short_id))
                self.wfile.write(page.encode())
            except:
                self.send_error(404)
        elif self.path.startswith('/api/short/'):
            try:
                short_id = int(self.path.split('/')[3])
                conn = get_connection()
                conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM shorts WHERE id = ?', (short_id,))
                short = cursor.fetchone()
                conn.close()
                if short:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(short).encode())
                else:
                    self.send_error(404, 'Short not found')
            except Exception as e:
                self.send_error(500, str(e))
        elif self.path.startswith('/video/'):
            import urllib.parse
            video_path = urllib.parse.unquote(self.path[7:])
            
            if os.path.exists(video_path) and video_path.endswith('.mp4'):
                self.send_response(200)
                self.send_header('Content-type', 'video/mp4')
                self.send_header('Accept-Ranges', 'bytes')
                file_size = os.path.getsize(video_path)
                self.send_header('Content-Length', str(file_size))
                self.end_headers()
                
                with open(video_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, 'Video not found')
        else:
            self.send_error(404)
    
    def do_POST(self):
        if '/api/shorts/' in self.path and '/status' in self.path:
            short_id = int(self.path.split('/')[3])
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            update_short_status(short_id, data['status'])
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
        elif self.path == '/api/open-folder':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            folder = data.get('folder', '')
            
            if folder and os.path.exists(folder):
                import subprocess
                subprocess.Popen(['explorer', folder])
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
        elif self.path.startswith('/api/extended/') and '/status' in self.path:
            video_id = int(self.path.split('/')[3])
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            update_extended_video_status(video_id, data['status'])
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
        elif self.path.startswith('/api/long/') and '/status' in self.path:
            video_id = int(self.path.split('/')[3])
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            update_long_video_status(video_id, data['status'])
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
        else:
            self.send_error(404)
    
    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    print(f"\n🚀 Server started at http://localhost:{PORT}")
    print("   Open your browser to manage your shorts")
    print("   Ctrl+C to stop")
    
    server = HTTPServer(('localhost', PORT), ShortsHandler)
    try:
        import webbrowser
        webbrowser.open(f'http://localhost:{PORT}')
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
