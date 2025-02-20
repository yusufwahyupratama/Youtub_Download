import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
import json
import os
import webbrowser
from datetime import datetime
import yt_dlp
from yt_dlp.utils import remove_terminal_sequences

class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.geometry("800x600")
        # Variabel untuk mode download, default MP3
        self.download_mode = tk.StringVar(value="MP3")
        self.setup_ui()
        self.history_file = "history.json"
        self.history_lock = threading.RLock()  # Menggunakan RLock agar reentrant
        self.load_history()

    def setup_ui(self):
        # Konfigurasi style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook.Tab", font=('Helvetica', 10, 'bold'))
        style.configure("TButton", padding=6, font=('Helvetica', 9))
        style.configure("TEntry", padding=6)
        
        # Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.download_tab = ttk.Frame(self.notebook)
        self.history_tab = ttk.Frame(self.notebook)
        self.youtube_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.download_tab, text="Download")
        self.notebook.add(self.history_tab, text="History")
        self.notebook.add(self.youtube_tab, text="YouTube")
        self.notebook.pack(expand=True, fill="both")

        self.setup_download_tab()
        self.setup_history_tab()
        self.setup_youtube_tab()

    def setup_download_tab(self):
        # Frame untuk input URL dan tombol unduh
        top_frame = ttk.Frame(self.download_tab)
        top_frame.pack(pady=10, padx=10, fill="x")
        
        ttk.Label(top_frame, text="YouTube URL:").pack(side="left")
        self.url_entry = ttk.Entry(top_frame, width=50)
        self.url_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        self.download_btn = ttk.Button(top_frame, text="Download", command=self.start_download)
        self.download_btn.pack(side="left", padx=5)
        
        # Tombol untuk mengganti mode unduhan
        self.mode_button = ttk.Button(top_frame, text="Mode: MP3 (Klik untuk ubah ke MP4)", command=self.toggle_mode)
        self.mode_button.pack(side="left", padx=5)

        # Panel Info Video
        self.info_panel = ttk.LabelFrame(self.download_tab, text="Video Info")
        self.info_panel.pack(pady=10, padx=10, fill="x")
        
        self.info_labels = {
            'type': ttk.Label(self.info_panel, text="Tipe: -"),
            'title': ttk.Label(self.info_panel, text="Judul: -"),
            'uploader': ttk.Label(self.info_panel, text="Uploader: -"),
            'duration': ttk.Label(self.info_panel, text="Durasi: -")
        }
        for label in self.info_labels.values():
            label.pack(anchor="w")

        # Bagian Progress
        self.progress_frame = ttk.LabelFrame(self.download_tab, text="Progress")
        self.progress_frame.pack(pady=10, padx=10, fill="x")
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", padx=5, pady=5)
        
        self.status_label = ttk.Label(self.progress_frame, text="Status: Menunggu...")
        self.status_label.pack()

        # Queue untuk update UI secara thread-safe
        self.queue = queue.Queue()
        self.check_queue()

    def setup_history_tab(self):
        # Frame untuk Treeview dan tombol hapus
        top_frame = ttk.Frame(self.history_tab)
        top_frame.pack(side="top", fill="both", expand=True)

        # Treeview untuk riwayat unduhan
        columns = ("#1", "#2", "#3", "#4")
        self.history_tree = ttk.Treeview(top_frame, columns=columns, show="headings")
        self.history_tree.heading("#1", text="Tanggal")
        self.history_tree.heading("#2", text="Judul")
        self.history_tree.heading("#3", text="Status")
        self.history_tree.heading("#4", text="URL")
        self.history_tree.column("#1", width=120)
        self.history_tree.column("#2", width=250)
        self.history_tree.column("#3", width=80)
        self.history_tree.column("#4", width=300)
        
        vsb = ttk.Scrollbar(self.history_tab, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=vsb.set)
        
        self.history_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Tombol hapus di bagian bawah Treeview
        btn_frame = ttk.Frame(self.history_tab)
        btn_frame.pack(fill="x", pady=5)
        delete_btn = ttk.Button(btn_frame, text="Hapus History", command=self.delete_selected_history)
        delete_btn.pack(side="left", padx=10)

    def setup_youtube_tab(self):
        label = ttk.Label(self.youtube_tab, text="Klik tombol di bawah untuk membuka YouTube di browser Anda.")
        label.pack(pady=10)
        open_youtube_btn = ttk.Button(self.youtube_tab, text="Buka YouTube", command=self.open_youtube)
        open_youtube_btn.pack(pady=10)

    def open_youtube(self):
        webbrowser.open("https://www.youtube.com")

    def toggle_mode(self):
        # Fungsi untuk berganti mode antara MP3 dan MP4
        if self.download_mode.get() == "MP3":
            self.download_mode.set("MP4")
            self.mode_button.config(text="Mode: MP4 (Klik untuk ubah ke MP3)")
        else:
            self.download_mode.set("MP3")
            self.mode_button.config(text="Mode: MP3 (Klik untuk ubah ke MP4)")

    def start_download(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("Error", "Masukkan URL YouTube terlebih dahulu!")
            return
        
        threading.Thread(target=self.download_video, args=(url,), daemon=True).start()
        self.download_btn.config(state="disabled")
        self.status_label.config(text="Mengambil informasi video...")

    def download_video(self, url):
        try:
            # Ekstrak informasi video/playlist
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
            
            # Siapkan konfigurasi berdasarkan mode yang dipilih
            if self.download_mode.get() == "MP3":
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'quiet': True,
                    'progress_hooks': [self.progress_hook],
                }
                mode_text = "Audio (MP3)"
            else:  # MP4 mode
                ydl_opts = {
                    'format': 'bv*+ba/b',
                    'merge_output_format': 'mp4',
                    'quiet': True,
                    'progress_hooks': [self.progress_hook],
                }
                mode_text = "Video (MP4)"
            
            # Update info panel dan status berdasarkan tipe (playlist atau video individu)
            if 'entries' in info:
                title = info.get('title', 'Playlist')
                self.queue.put(('update_info', {
                    'type': 'Playlist ' + mode_text,
                    'title': title,
                    'uploader': '-',
                    'duration': '-'
                }))
                self.queue.put(('update_status', f"Playlist terdeteksi: {title}"))
            else:
                uploader = info.get('uploader', 'Unknown Uploader')
                title = info.get('title', 'Unknown Title')
                duration = self.format_duration(info.get('duration', 0))
                self.queue.put(('update_info', {
                    'type': 'Video ' + mode_text,
                    'title': title,
                    'uploader': uploader,
                    'duration': duration,
                }))
                self.queue.put(('update_status', f"Video individu terdeteksi: {uploader} - {title}"))
            
            # Meminta user memilih folder penyimpanan
            save_dir = filedialog.askdirectory(title="Pilih Folder Penyimpanan")
            if not save_dir:
                self.queue.put(('error', "Download dibatalkan, folder tidak dipilih."))
                return
            
            # Menentukan template output file
            if 'entries' in info:
                # Jika playlist
                ydl_opts['outtmpl'] = os.path.join(save_dir, f"{info.get('title', 'Playlist')}/%(playlist_index)s - %(title)s.%(ext)s")
            else:
                # Jika video individu
                ydl_opts['outtmpl'] = os.path.join(save_dir, f"%(uploader)s - %(title)s.%(ext)s")
            
            # Proses unduhan
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.queue.put(('update_status', "Sedang memproses unduhan..."))
                ydl.download([url])
            
            self.queue.put(('complete', "Unduhan selesai!"))
            self.add_to_history(url, info.get('title', ''), "Berhasil")
        except yt_dlp.utils.DownloadError as e:
            self.queue.put(('error', f"Kesalahan unduhan: {e}"))
            self.add_to_history(url, "", "Gagal")
        except Exception as e:
            self.queue.put(('error', f"Terjadi kesalahan: {e}"))
            self.add_to_history(url, "", "Gagal")

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                percent_str = remove_terminal_sequences(d.get('_percent_str', '')).replace('%', '').strip()
                percent = float(percent_str)
                self.queue.put(('progress', percent))
                self.queue.put(('update_status', f"Mengunduh: {percent_str}% "))
            except Exception:
                self.queue.put(('update_status', "Mengunduh..."))
        elif d['status'] == 'finished':
            if self.download_mode.get() == "MP3":
                self.queue.put(('update_status', "Memproses konversi MP3..."))
            else:
                self.queue.put(('update_status', "Memproses penggabungan file..."))

    def check_queue(self):
        while not self.queue.empty():
            task = self.queue.get()
            if task[0] == 'progress':
                self.progress_bar["value"] = task[1]
            elif task[0] == 'update_status':
                self.status_label.config(text=task[1])
            elif task[0] == 'update_info':
                self.update_info_panel(task[1])
            elif task[0] == 'complete':
                messagebox.showinfo("Sukses", task[1])
                self.reset_ui()
            elif task[0] == 'error':
                messagebox.showerror("Error", task[1])
                self.reset_ui()
        self.root.after(100, self.check_queue)

    def update_info_panel(self, info):
        for key, label in self.info_labels.items():
            label.config(text=f"{key.capitalize()}: {info.get(key, '-')}")

    def reset_ui(self):
        self.progress_bar["value"] = 0
        self.download_btn.config(state="normal")
        self.url_entry.delete(0, "end")
        for key, label in self.info_labels.items():
            label.config(text=label.cget("text").split(":")[0] + ": -")

    def format_duration(self, seconds):
        return f"{seconds // 3600:02}:{(seconds % 3600) // 60:02}:{seconds % 60:02}"

    def load_history(self):
        with self.history_lock:
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                self.history = []
        self.update_history_tree()

    def add_to_history(self, url, title, status):
        self.history.insert(0, {'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                  'url': url, 'title': title, 'status': status})
        self.update_history_tree()
        self.save_history()

    def update_history_tree(self):
        self.history_tree.delete(*self.history_tree.get_children())
        for item in self.history:
            self.history_tree.insert("", "end", values=(item['date'], item['title'], item['status'], item['url']))

    def save_history(self):
        # Jadwalkan operasi penyimpanan di main thread untuk menghindari error
        self.root.after(0, self._save_history)

    def _save_history(self):
        with self.history_lock:
            try:
                with open(self.history_file, 'w', encoding='utf-8') as f:
                    json.dump(self.history, f, indent=4)
            except OSError as e:
                print(f"Error saat menyimpan history: {e}")

    def delete_selected_history(self):
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Pilih entri history yang ingin dihapus!")
            return

        for sel in selected:
            values = self.history_tree.item(sel, "values")
            self.history = [entry for entry in self.history 
                            if not (entry['date'] == values[0] and entry['title'] == values[1])]
        
        self.update_history_tree()
        self.save_history()
        messagebox.showinfo("Info", "Entri history telah dihapus.")

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()