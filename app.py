# app.py

from flask import Flask, render_template, request, send_from_directory, url_for
import yt_dlp
from pathlib import Path
import os
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
                        file_path TEXT,
                        format TEXT,
                        url TEXT
                    )''')
    conn.commit()
    conn.close()

init_db()

# Fungsi untuk menyimpan metadata
def save_metadata(title, uploader, file_path, file_format, url):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO downloads (title, uploader, file_path, format, url) 
                      VALUES (?, ?, ?, ?, ?)''', (title, uploader, file_path, file_format, url))
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
    folder_path = base_download_folder / "Videos"
    create_folder(folder_path)

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': f'{folder_path}/%(uploader)s/%(title)s.%(ext)s'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            title = info_dict.get('title', 'UnknownTitle')
            uploader = info_dict.get('uploader', 'UnknownUploader')
            ext = info_dict.get('ext', 'mp4')
            file_path = f"Videos/{uploader}.{title}.{ext}"

            save_metadata(title, uploader, file_path, "video", url)
            return file_path
    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        raise

# Mengunduh audio
def download_audio(url):
    folder_path = base_download_folder / "Audios"
    create_folder(folder_path)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{folder_path}/%(uploader)s/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            title = info_dict.get('title', 'UnknownTitle')
            uploader = info_dict.get('uploader', 'UnknownUploader')
            ext = 'mp3'
            file_path = f"Audios/{uploader}.{title}.{ext}"

            save_metadata(title, uploader, file_path, "audio", url)
            return file_path
    except Exception as e:
        logging.error(f"Error downloading audio: {e}")
        raise

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
