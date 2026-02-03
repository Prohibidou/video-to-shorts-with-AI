"""
Servidor web para gestionar shorts con UI visual.
Filtra por video (URL) específico.

Ejecutar: python shorts_ui.py
Abrir: http://localhost:5000
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
from database import (
    get_all_shorts, get_all_videos, approve_short, reject_short,
    update_short_status, get_shorts_by_video,
    get_extended_videos_by_short, get_long_videos_by_short,
    update_extended_video_status, update_long_video_status
)

PORT = 5000

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shorts Manager</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }
        h1 {
            text-align: center;
            margin-bottom: 20px;
            font-size: 2.5rem;
            background: linear-gradient(90deg, #e94560, #ff6b6b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .video-selector {
            max-width: 800px;
            margin: 0 auto 30px;
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .video-selector label {
            display: block;
            margin-bottom: 10px;
            font-size: 1.1rem;
            opacity: 0.8;
        }
        .video-selector select {
            width: 100%;
            padding: 15px;
            font-size: 1rem;
            border-radius: 8px;
            border: none;
            background: rgba(255,255,255,0.1);
            color: white;
            cursor: pointer;
        }
        .video-selector select option {
            background: #1a1a2e;
            color: white;
        }
        .no-video {
            text-align: center;
            padding: 60px;
            opacity: 0.6;
            font-size: 1.2rem;
        }
        .stats {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255,255,255,0.1);
            padding: 15px 30px;
            border-radius: 12px;
            text-align: center;
        }
        .stat-card h3 { font-size: 2rem; }
        .stat-card p { opacity: 0.7; }
        .stat-card.pending h3 { color: #fbbf24; }
        .stat-card.approved h3 { color: #4ade80; }
        .stat-card.rejected h3 { color: #f87171; }
        .shorts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }
        .short-card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .short-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 40px rgba(233, 69, 96, 0.2);
        }
        .short-card.approved { border-left: 4px solid #4ade80; }
        .short-card.rejected { border-left: 4px solid #f87171; opacity: 0.6; }
        .short-card.pending { border-left: 4px solid #fbbf24; }
        .short-title {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 10px;
        }
        .short-meta {
            font-size: 0.9rem;
            opacity: 0.7;
            margin-bottom: 15px;
        }
        .short-meta span {
            background: rgba(255,255,255,0.1);
            padding: 3px 8px;
            border-radius: 4px;
            margin-right: 8px;
            display: inline-block;
            margin-bottom: 5px;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 15px;
        }
        .status-badge.pending { background: #fbbf24; color: #000; }
        .status-badge.approved { background: #4ade80; color: #000; }
        .status-badge.rejected { background: #f87171; color: #000; }
        .actions {
            display: flex;
            gap: 10px;
        }
        .btn {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.3s;
        }
        .btn-approve {
            background: linear-gradient(135deg, #4ade80, #22c55e);
            color: #000;
        }
        .btn-reject {
            background: linear-gradient(135deg, #f87171, #ef4444);
            color: #fff;
        }
        .btn:hover { transform: scale(1.05); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        
        /* Modal styles */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal-overlay.active { display: flex; }
        .modal-content {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 16px;
            padding: 30px;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .modal-header h2 { margin: 0; }
        .modal-close {
            background: #f87171;
            border: none;
            color: white;
            width: 36px; height: 36px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 1.2rem;
        }
        .video-list { display: flex; flex-direction: column; gap: 15px; }
        .video-item {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 12px;
            border-left: 4px solid #8b5cf6;
        }
        .video-item.long { border-left-color: #ec4899; }
        .video-item h4 { margin: 0 0 8px 0; }
        .video-item p { margin: 5px 0; opacity: 0.8; font-size: 0.9rem; }
        .no-videos { text-align: center; padding: 30px; opacity: 0.6; }
    </style>
</head>
<body>
    <h1>🎬 Shorts Manager</h1>
    
    <div class="video-selector">
        <label>📺 Selecciona un video:</label>
        <select id="video-select" onchange="selectVideo()">
            <option value="">-- Selecciona un video --</option>
        </select>
    </div>
    
    <div id="content">
        <div class="no-video">
            👆 Selecciona un video arriba para ver sus shorts
        </div>
    </div>
    
    <!-- Modal para Extended/Long videos -->
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
        
        async function loadVideos() {
            try {
                console.log('Loading videos...');
                const res = await fetch('/api/videos');
                videos = await res.json();
                console.log('Videos loaded:', videos);
                
                const select = document.getElementById('video-select');
                videos.forEach(v => {
                    const opt = document.createElement('option');
                    opt.value = v.id;
                    const title = v.title || 'Sin título';
                    opt.textContent = title + ' — ' + v.url;
                    select.appendChild(opt);
                });
                console.log('Dropdown populated');
            } catch (err) {
                console.error('Error loading videos:', err);
            }
        }
        
        async function selectVideo() {
            const select = document.getElementById('video-select');
            selectedVideoId = select.value;
            
            if (!selectedVideoId) {
                document.getElementById('content').innerHTML = `
                    <div class="no-video">👆 Selecciona un video arriba para ver sus shorts</div>
                `;
                return;
            }
            
            // Obtener URL y carpeta del video seleccionado
            const selectedVideo = videos.find(v => v.id == selectedVideoId);
            selectedVideoUrl = selectedVideo ? selectedVideo.url : '';
            selectedClipsFolder = selectedVideo ? (selectedVideo.clips_folder || '') : '';
            
            const res = await fetch(`/api/videos/${selectedVideoId}/shorts`);
            shorts = await res.json();
            renderContent();
        }
        
        let selectedVideoUrl = '';
        let selectedClipsFolder = '';
        
        function renderContent() {
            const pending = shorts.filter(s => (s.status || 'pending') === 'pending').length;
            const approved = shorts.filter(s => s.status === 'approved').length;
            const rejected = shorts.filter(s => s.status === 'rejected').length;
            
            const folderButton = selectedClipsFolder ? 
                `<button onclick="openFolder()" 
                    style="display: inline-block; padding: 12px 24px; background: linear-gradient(135deg, #3b82f6, #1d4ed8); 
                           color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; margin-left: 10px;">
                    📁 Abrir carpeta de clips
                </button>` : '';
            
            let html = `
                <div style="text-align: center; margin-bottom: 20px;">
                    <a href="${selectedVideoUrl}" target="_blank" 
                       style="display: inline-block; padding: 12px 24px; background: linear-gradient(135deg, #ff0000, #cc0000); 
                              color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">
                        ▶️ Ver video en YouTube
                    </a>
                    ${folderButton}
                </div>
                <div class="stats">
                    <div class="stat-card pending"><h3>${pending}</h3><p>Pendientes</p></div>
                    <div class="stat-card approved"><h3>${approved}</h3><p>Aprobados</p></div>
                    <div class="stat-card rejected"><h3>${rejected}</h3><p>Rechazados</p></div>
                </div>
                <div class="shorts-grid">
            `;
            
            if (shorts.length === 0) {
                html += `<div class="no-video">No hay shorts para este video</div>`;
            } else {
                shorts.forEach((s, idx) => {
                    const status = s.status || 'pending';
                    html += `
                        <div class="short-card ${status}">
                            <div class="short-title">${s.title || 'Sin título'}</div>
                            <div class="short-meta">
                                <span>⏱ ${s.start_time} → ${s.end_time}</span>
                            </div>
                            <div class="status-badge ${status}">${status.toUpperCase()}</div>
                            
                            <div style="display: flex; gap: 5px; margin-bottom: 10px; flex-wrap: wrap;">
                                <button onclick="showExtendedVideos(${s.id})" 
                                    style="padding: 6px 10px; background: #8b5cf6; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
                                    📂 Extended (3min)
                                </button>
                                <button onclick="showLongVideos(${s.id})" 
                                    style="padding: 6px 10px; background: #ec4899; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
                                    🎬 Long (10min+)
                                </button>
                            </div>
                            
                            <div class="actions">
                                <button class="btn btn-approve" onclick="setStatus(${s.id}, 'approved')" 
                                    ${status === 'approved' ? 'disabled' : ''}>✓ Aprobar</button>
                                <button class="btn btn-reject" onclick="setStatus(${s.id}, 'rejected')"
                                    ${status === 'rejected' ? 'disabled' : ''}>✗ Rechazar</button>
                            </div>
                        </div>
                    `;
                });
            }
            
            html += '</div>';
            document.getElementById('content').innerHTML = html;
        }
        
        async function setStatus(id, status) {
            await fetch(`/api/shorts/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            });
            selectVideo(); // Recargar
        }
        
        async function openFolder() {
            if (selectedClipsFolder) {
                await fetch('/api/open-folder', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({folder: selectedClipsFolder})
                });
            }
        }
        
        async function openShortFolder(folderPath) {
            await fetch('/api/open-folder', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({folder: folderPath})
            });
        }
        
        async function openShortFolderByIdx(idx, subfolder) {
            const s = shorts[idx];
            if (s && s.folder_path) {
                let folder = s.folder_path;
                if (subfolder) {
                    folder = folder + '/' + subfolder;
                }
                await fetch('/api/open-folder', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({folder: folder})
                });
            }
        }
        
        async function showExtendedVideos(shortId) {
            currentShortId = shortId;
            currentModalType = 'extended';
            const res = await fetch(`/api/shorts/${shortId}/extended`);
            const videos = await res.json();
            showVideoModal('Extended Videos (3min)', videos, 'extended');
        }
        
        async function showLongVideos(shortId) {
            currentShortId = shortId;
            currentModalType = 'long';
            const res = await fetch(`/api/shorts/${shortId}/long`);
            const videos = await res.json();
            showVideoModal('Long Videos (10min+)', videos, 'long');
        }
        
        function showVideoModal(title, videos, type) {
            document.getElementById('modal-title').textContent = title;
            const body = document.getElementById('modal-body');
            
            if (videos.length === 0) {
                body.innerHTML = '<div class="no-videos">No hay videos de este tipo. Ejecuta:<br><code style="background: rgba(255,255,255,0.1); padding: 5px 10px; border-radius: 4px; margin-top: 10px; display: inline-block;">' + (type === 'extended' ? 'python generate_extended.py' : 'python generate_long.py') + '</code></div>';
            } else {
                body.innerHTML = videos.map(v => {
                    const status = v.status || 'pending';
                    const videoPath = v.output_filename || '';
                    const encodedPath = encodeURIComponent(videoPath);
                    const folderPath = videoPath ? videoPath.substring(0, videoPath.lastIndexOf('\\\\') || videoPath.lastIndexOf('/')) : '';
                    
                    return `
                    <div class="video-item ${type}" id="video-${type}-${v.id}">
                        <h4>${v.title || 'Sin título'}</h4>
                        ${videoPath ? `
                        <video width="100%" style="max-height: 300px; border-radius: 8px; margin: 10px 0;" controls>
                            <source src="/video/${encodedPath}" type="video/mp4">
                            Tu navegador no soporta video HTML5
                        </video>
                        ` : ''}
                        <p><strong>Archivo:</strong> ${videoPath || 'N/A'}</p>
                        <p><strong>Duración:</strong> ${v.duration_seconds ? Math.floor(v.duration_seconds/60) + ' min' : 'N/A'}</p>
                        <div class="status-badge ${status}" style="display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; margin-bottom: 10px; background: ${status === 'approved' ? '#4ade80' : status === 'rejected' ? '#f87171' : '#fbbf24'}; color: #000;">${status.toUpperCase()}</div>
                        ${v.summary ? '<p>' + v.summary + '</p>' : ''}
                        <div style="display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap;">
                            <button onclick="setVideoStatus('${type}', ${v.id}, 'approved')" 
                                style="flex: 1; min-width: 100px; padding: 8px; background: linear-gradient(135deg, #4ade80, #22c55e); color: #000; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;" 
                                ${status === 'approved' ? 'disabled style="opacity:0.5"' : ''}>✓ Aprobar</button>
                            <button onclick="setVideoStatus('${type}', ${v.id}, 'rejected')" 
                                style="flex: 1; min-width: 100px; padding: 8px; background: linear-gradient(135deg, #f87171, #ef4444); color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;" 
                                ${status === 'rejected' ? 'disabled style="opacity:0.5"' : ''}>✗ Rechazar</button>
                            ${folderPath ? `<button onclick="openFolder('${folderPath.replace(/\\\\/g, '\\\\\\\\')}')" 
                                style="flex: 1; min-width: 100px; padding: 8px; background: linear-gradient(135deg, #8b5cf6, #7c3aed); color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">📁 Carpeta</button>` : ''}
                        </div>
                    </div>
                `}).join('');
            }
            
            document.getElementById('modal').classList.add('active');
        }
        
        function closeModal(event) {
            if (!event || event.target.id === 'modal') {
                document.getElementById('modal').classList.remove('active');
            }
        }
        
        let currentModalType = '';
        let currentShortId = null;
        
        async function setVideoStatus(type, videoId, status) {
            const endpoint = type === 'extended' ? '/api/extended' : '/api/long';
            await fetch(`${endpoint}/${videoId}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            });
            // Recargar modal
            if (type === 'extended') {
                showExtendedVideos(currentShortId);
            } else {
                showLongVideos(currentShortId);
            }
        }
        
        // Expose functions to global scope for HTML onchange handlers
        window.selectVideo = selectVideo;
        window.setStatus = setStatus;
        window.openFolder = openFolder;
        window.openShortFolder = openShortFolder;
        window.openShortFolderByIdx = openShortFolderByIdx;
        window.showExtendedVideos = showExtendedVideos;
        window.showLongVideos = showLongVideos;
        window.closeModal = closeModal;
        window.setVideoStatus = setVideoStatus;
        
        loadVideos();
    </script>
</body>
</html>'''


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
            videos = get_all_videos()
            self.wfile.write(json.dumps(videos).encode())
        elif self.path.startswith('/api/videos/') and '/shorts' in self.path:
            video_id = int(self.path.split('/')[3])
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            shorts = get_shorts_by_video(video_id)
            self.wfile.write(json.dumps(shorts).encode())
        elif self.path == '/api/shorts':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            shorts = get_all_shorts()
            self.wfile.write(json.dumps(shorts).encode())
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
        elif self.path.startswith('/video/'):
            # Serve video files from local filesystem
            import os
            import urllib.parse
            video_path = urllib.parse.unquote(self.path[7:])  # Remove '/video/'
            
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
            
            if folder:
                import subprocess
                import os
                if os.path.exists(folder):
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
    print(f"🚀 Servidor iniciado en http://localhost:{PORT}")
    print("   Abre el navegador para gestionar tus shorts")
    print("   Ctrl+C para detener")
    
    server = HTTPServer(('localhost', PORT), ShortsHandler)
    try:
        import webbrowser
        webbrowser.open(f'http://localhost:{PORT}')
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Servidor detenido")
