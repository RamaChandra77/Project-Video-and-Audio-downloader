import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import threading
import os
import time
from yt_dlp import YoutubeDL
import json
import queue

class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video/Audio Downloader")
        self.root.configure(bg="#2c3e50")  # Set the background color of the window

        self.history_file = "download_history.json"
        self.load_history()

        self.paused = threading.Event()
        self.paused.set()  # Start in the "not paused" state

        self.queue = queue.Queue()

        # Menu button
        self.menu_button = tk.Menubutton(root, text="Menu", relief=tk.RAISED, bg="#3498db", fg="white")
        self.menu_button.menu = tk.Menu(self.menu_button, tearoff=0, bg="#3498db", fg="white")
        self.menu_button["menu"] = self.menu_button.menu
        self.menu_button.menu.add_command(label="History", command=self.show_history)
        self.menu_button.pack(pady=5)

        self.url_label = tk.Label(root, text="Enter URL:", bg="#2c3e50", fg="white", font=("Helvetica", 12))
        self.url_label.pack(pady=10)

        self.url_entry = tk.Entry(root, width=50, font=("Helvetica", 12))
        self.url_entry.pack(pady=5)

        self.option_label = tk.Label(root, text="Choose an option:", bg="#2c3e50", fg="white", font=("Helvetica", 12))
        self.option_label.pack(pady=10)

        self.option_var = tk.StringVar(root, "video")
        self.option_video = tk.Radiobutton(root, text="Video", variable=self.option_var, value="video", bg="#2c3e50", fg="white", selectcolor="#3498db", font=("Helvetica", 12))
        self.option_video.pack()
        self.option_audio = tk.Radiobutton(root, text="Audio (MP3)", variable=self.option_var, value="audio", bg="#2c3e50", fg="white", selectcolor="#3498db", font=("Helvetica", 12))
        self.option_audio.pack()

        self.download_button = tk.Button(root, text="Download", command=self.download_thread, bg="#2ecc71", fg="white", activebackground="#27ae60", font=("Helvetica", 12))
        self.download_button.pack(pady=10)

        self.pause_button = tk.Button(root, text="Pause", command=self.pause_download, state=tk.DISABLED, bg="#e74c3c", fg="white", activebackground="#c0392b", font=("Helvetica", 12))
        self.pause_button.pack(pady=5)

        self.resume_button = tk.Button(root, text="Resume", command=self.resume_download, state=tk.DISABLED, bg="#f39c12", fg="white", activebackground="#e67e22", font=("Helvetica", 12))
        self.resume_button.pack(pady=5)

        self.progress_label = tk.Label(root, text="", bg="#2c3e50", fg="white", font=("Helvetica", 12))
        self.progress_label.pack(pady=10)

        self.speed_label = tk.Label(root, text="", bg="#2c3e50", fg="white", font=("Helvetica", 12))
        self.speed_label.pack(pady=10)

        self.progress = tk.DoubleVar(root)
        self.progressbar = ttk.Progressbar(root, variable=self.progress, length=300, mode='determinate')
        self.progressbar.pack(pady=10)

        self.root.after(100, self.process_queue)

    def load_history(self):
        try:
            with open(self.history_file, "r") as file:
                self.history = json.load(file)
        except FileNotFoundError:
            self.history = []

    def save_history(self):
        with open(self.history_file, "w") as file:
            json.dump(self.history, file, indent=4)

    def show_history(self):
        history_window = tk.Toplevel(self.root)
        history_window.title("Download History")
        history_window.configure(bg="#2c3e50")

        if not self.history:
            tk.Label(history_window, text="No downloads yet.", bg="#2c3e50", fg="white", font=("Helvetica", 12)).pack(pady=10)
        else:
            for index, entry in enumerate(self.history, start=1):
                history_entry = f"{index}. {entry['type']} - {entry['title']} ({entry['url']}): {entry['path']}"
                tk.Button(history_window, text=history_entry, command=lambda p=entry['path']: self.open_download_folder(p), bg="#3498db", fg="white", activebackground="#2980b9", font=("Helvetica", 12)).pack(pady=2)

    def open_download_folder(self, path):
        os.startfile(os.path.dirname(path))

    def download_thread(self):
        url = self.url_entry.get().strip()
        option = self.option_var.get()

        if not url:
            messagebox.showwarning("Error", "Please enter a valid URL.")
            return

        self.download_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.resume_button.config(state=tk.DISABLED)

        threading.Thread(target=self.download, args=(url, option)).start()

    def download(self, url, option):
        self.progress.set(0)
        self.progressbar.update()
        self.start_time = time.time()

        try:
            if option == 'video':
                download_path, title = self.download_video(url)
                if download_path:
                    self.history.append({"type": "Video", "title": title, "url": url, "path": download_path})
                    self.save_history()
                    self.queue.put(("complete", download_path))
            elif option == 'audio':
                download_path, title = self.download_audio(url)
                if download_path:
                    self.history.append({"type": "Audio", "title": title, "url": url, "path": download_path})
                    self.save_history()
                    self.queue.put(("complete", download_path))
            else:
                self.queue.put(("error", "Invalid option selected."))
        except Exception as e:
            self.queue.put(("error", str(e)))

    def download_video(self, url):
        ydl_opts = {
            'format': 'best',
            'progress_hooks': [self.progress_hook],
        }
        download_path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
        if not download_path:
            return None, None

        ydl_opts['outtmpl'] = download_path
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Unknown title')
        return download_path, title

    def download_audio(self, url):
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'progress_hooks': [self.progress_hook],
        }
        download_dir = filedialog.askdirectory(title="Select download directory")
        if not download_dir:
            return None, None

        ydl_opts['outtmpl'] = os.path.join(download_dir, 'audio.%(ext)s')
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Unknown title')
        return os.path.join(download_dir, 'audio.mp3'), title

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            downloaded = d['downloaded_bytes']
            total = d['total_bytes']
            percentage = downloaded / total * 100
            self.queue.put(("progress", percentage))

            time_elapsed = time.time() - self.start_time
            if time_elapsed > 0:
                speed = downloaded / time_elapsed
                speed_in_kb = speed / 1024
                if speed_in_kb > 1024:
                    speed_in_mb = speed_in_kb / 1024
                    self.queue.put(("speed", f"Speed: {speed_in_mb:.2f} MB/s"))
                else:
                    self.queue.put(("speed", f"Speed: {speed_in_kb:.2f} KB/s"))

            # Check if paused
            self.paused.wait()

        elif d['status'] == 'finished':
            self.queue.put(("progress", 100))

    def pause_download(self):
        self.paused.clear()
        self.pause_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.NORMAL)

    def resume_download(self):
        self.paused.set()
        self.pause_button.config(state=tk.NORMAL)
        self.resume_button.config(state=tk.DISABLED)

    def process_queue(self):
        try:
            while True:
                msg, value = self.queue.get_nowait()
                if msg == "progress":
                    self.progress.set(value)
                    self.progressbar.update()
                elif msg == "speed":
                    self.speed_label.config(text=value)
                elif msg == "complete":
                    if messagebox.askyesno("Download Complete", f"Download complete. Do you want to open the folder?"):
                        os.startfile(os.path.dirname(value))
                    self.download_button.config(state=tk.NORMAL)
                    self.pause_button.config(state=tk.DISABLED)
                    self.resume_button.config(state=tk.DISABLED)
                elif msg == "error":
                    messagebox.showerror("Error", value)
                    self.download_button.config(state=tk.NORMAL)
                    self.pause_button.config(state=tk.DISABLED)
                    self.resume_button.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = DownloaderApp(root)
    root.mainloop()

