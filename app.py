# app.py

from flask import Flask, render_template, request, send_from_directory, url_for
import yt_dlp
from pathlib import Path
import os
import json
import sqlite3
import logging

app = Flask(__name__)

# Folder dasar untuk menyimpan unduhan
base_download_folder = Path("downloads")
base_download_folder.mkdir(parents=True, exist_ok=True)

# Database file
db_file = base_download_folder / "metadata.db"

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)

# Inisialisasi database
def init_db():
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS downloads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT,
                        uploader TEXT,
                        playlist_title TEXT,
                        file_path TEXT,
                        format TEXT,
                        url TEXT
                    )''')
    conn.commit()
    conn.close()

init_db()

# Fungsi untuk menyimpan metadata
def save_metadata(title, uploader, playlist_title, file_path, file_format, url):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO downloads (title, uploader, playlist_title, file_path, format, url) 
                  VALUES (?, ?, ?, ?, ?, ?)''', (title, uploader, playlist_title, file_path, file_format, url))
    conn.commit()
    conn.close()


# Fungsi untuk mengambil metadata
def get_metadata():
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM downloads')
    data = cursor.fetchall()
    conn.close()
    return data

# Membuat folder jika belum ada
def create_folder(path):
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)

# Mengunduh video
def download_video(url):
    """Mengunduh video atau playlist video."""
    folder_path = base_download_folder / "Videos"
    create_folder(folder_path)

    try:
        # Ambil metadata terlebih dahulu tanpa mengunduh
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            is_playlist = 'entries' in info_dict and info_dict['entries'] is not None

            # Tentukan folder berdasarkan jenis (playlist atau tunggal)
            if is_playlist:  # Playlist
                playlist_title = info_dict.get('playlist_title') or info_dict['entries'][0].get('title', 'UnnamedPlaylist')
                video_folder = folder_path / playlist_title
            else:  # Video tunggal
                uploader = info_dict.get('uploader') or 'UnknownUploader'
                video_folder = folder_path / uploader

            create_folder(video_folder)

            # Atur ulang `outtmpl` untuk proses unduhan
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': f'{video_folder}/%(title)s.%(ext)s',
            }

            # Unduh video atau playlist
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
                result = ydl_download.extract_info(url, download=True)

            # Proses setiap video dalam playlist atau video tunggal
            if is_playlist:
                for entry in result['entries']:
                    if entry:
                        process_single_video(entry, video_folder, url, is_playlist=True)
            else:
                process_single_video(result, video_folder, url, is_playlist=False)

    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        raise


def process_single_video(info_dict, video_folder, url, is_playlist):
    """Memproses satu video dan menyimpan metadata."""
    title = info_dict.get('title', 'UnknownTitle')
    uploader = info_dict.get('uploader', 'UnknownUploader')
    playlist_title = info_dict.get('playlist_title', None) if is_playlist else None
    ext = info_dict.get('ext', 'mp4')

    # Buat path file untuk video
    file_path = video_folder / f"{title}.{ext}"

    # Simpan metadata ke database
    save_metadata(title, uploader, playlist_title or title, str(file_path), "video", url)

# Mengunduh audio
def download_audio(url):
    """Mengunduh audio atau playlist audio."""
    folder_path = base_download_folder / "Audios"
    create_folder(folder_path)

    try:
        # Ambil metadata terlebih dahulu tanpa mengunduh
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            is_playlist = 'entries' in info_dict and info_dict['entries'] is not None

            # Tentukan folder berdasarkan jenis (playlist atau tunggal)
            if is_playlist:  # Playlist
                playlist_title = info_dict.get('playlist_title') or info_dict['entries'][0].get('title', 'UnnamedPlaylist')
                audio_folder = folder_path / playlist_title
            else:  # Audio tunggal
                uploader = info_dict.get('uploader') or 'UnknownUploader'
                audio_folder = folder_path / uploader

            create_folder(audio_folder)

            # Atur ulang `outtmpl` untuk proses unduhan
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'{audio_folder}/%(title)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            }

            # Unduh audio atau playlist
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
                result = ydl_download.extract_info(url, download=True)

            # Proses setiap audio dalam playlist atau audio tunggal
            if is_playlist:
                for entry in result['entries']:
                    if entry:
                        process_single_audio(entry, audio_folder, url, is_playlist=True)
            else:
                process_single_audio(result, audio_folder, url, is_playlist=False)

    except Exception as e:
        logging.error(f"Error downloading audio: {e}")
        raise


def process_single_audio(info_dict, audio_folder, url, is_playlist):
    """Memproses satu audio dan menyimpan metadata."""
    title = info_dict.get('title', 'UnknownTitle')
    uploader = info_dict.get('uploader', 'UnknownUploader')
    playlist_title = info_dict.get('playlist_title', None) if is_playlist else None
    ext = 'mp3'

    # Buat path file untuk audio
    file_path = audio_folder / f"{title}.{ext}"

    # Simpan metadata ke database
    save_metadata(title, uploader, playlist_title or title, str(file_path), "audio", url)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.form['url']
    format_type = request.form['format']
    file_name = None
    message = ""

    try:
        if format_type == 'video':
            file_name = download_video(url)
            message = "Video successfully downloaded!"
        elif format_type == 'audio':
            file_name = download_audio(url)
            message = "Audio successfully downloaded!"
        else:
            message = "Invalid format selected!"
    except Exception as e:
        message = f"An error occurred: {e}"

    return render_template('index.html', message=message, file_name=file_name)

@app.route('/list_downloads')
def list_downloads():
    metadata = get_metadata()
    return render_template('list_downloads.html', downloads=metadata)

@app.route('/download_file/<path:filename>')
def download_file(filename):
    file_path = base_download_folder / filename

    if not file_path.exists():
        return "File not found", 404

    return send_from_directory(file_path.parent, file_path.name, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
