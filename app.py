from flask import Flask, render_template, request, send_from_directory, url_for
import yt_dlp
from pathlib import Path
import os
import logging
from urllib.parse import unquote

app = Flask(__name__)

# base_download_folder = Path(r"C:\Users\yusuf\Downloads\YouTubeDownloads")

# Folder dasar untuk menyimpan unduhan
base_download_folder = Path.home() / "Downloads" / "YouTubeDownloads"

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)

def create_folder(path):
    """Membuat folder jika belum ada."""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)

def sanitize_filename(filename):
    """Menghapus karakter yang tidak diinginkan seperti spasi atau simbol aneh."""
    return filename.replace('%20', ' ').replace('"', '').replace("'", '').strip()

def download_video(url):
    """Mengunduh video dan menyimpannya di folder 'Videos'."""
    folder_path = base_download_folder / "Videos"
    create_folder(folder_path)  # Pastikan folder dibuat
    
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': f'{folder_path}/%(uploader)s/%(title)s.%(ext)s',
        'noplaylist': False,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            uploader = info_dict.get('uploader', 'UnknownUploader')
            title = info_dict.get('title', 'UnknownTitle')
            ext = info_dict.get('ext', 'mp4')  # Default ke mp4 jika tidak diketahui
            file_path = folder_path / uploader / sanitize_filename(f"{title}.{ext}")
            logging.info(f"Video downloaded at: {file_path}")
            
            if not file_path.exists():
                logging.error(f"File not found after download: {file_path}")
                raise FileNotFoundError(f"Video file {file_path} does not exist.")
            
            return str(file_path.relative_to(base_download_folder))
    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        raise

def download_audio(url):
    """Mengunduh audio dan menyimpannya di folder 'Audios'."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{base_download_folder}/Audios/%(uploader)s/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': False,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            uploader = info_dict.get('uploader', 'UnknownUploader')
            title = info_dict.get('title', 'UnknownTitle')
            return f"Audios/{uploader}/{sanitize_filename(title)}.mp3"
    except Exception as e:
        logging.error(f"Error downloading audio: {e}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    """Mengunduh video/audio berdasarkan URL dan format yang dipilih."""
    url = request.form['url']
    format_type = request.form['format']
    file_name = None
    message = ""

    try:
        if format_type == 'video':
            file_name = download_video(url)
            logging.info(f"Video downloaded: {file_name}")
            message = "Video successfully downloaded!"
        elif format_type == 'audio':
            file_name = download_audio(url)
            message = "Audio successfully downloaded!"
        else:
            message = "Invalid format selected!"
    except Exception as e:
        message = f"An error occurred: {e}"

    # Kirim nama file yang diunduh ke template
    return render_template('index.html', message=message, file_name=file_name)

@app.route('/download_file/<path:filename>')
def download_file(filename):
    """Fungsi untuk mengunduh file dari server."""
    try:
        decoded_filename = sanitize_filename(unquote(filename))
        file_path = base_download_folder / Path(decoded_filename)
        logging.info(f"Decoded path: {decoded_filename}")

        if not file_path.exists():
            logging.error(f"File not found: {file_path}")
            return "File not found", 404
        
        return send_from_directory(file_path.parent, file_path.name, as_attachment=True)
    except Exception as e:
        logging.error(f"Error downloading file: {e}")
        return "An error occurred while trying to download the file.", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
