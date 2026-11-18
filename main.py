
import os
import sys
import shutil
import queue
import threading
import platform
import customtkinter as ctk
import yt_dlp

from tkinter import filedialog, messagebox

# -----------------------------------
# APPLICATION SETTINGS
# -----------------------------------

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Media Downloader")
app.geometry("550x440")
app.resizable(False, False)

events = queue.Queue()

output_folder = os.path.join(
    os.path.expanduser("~"),
    "Downloads"
)

os.makedirs(output_folder, exist_ok=True)

# -----------------------------------
# OPERATING SYSTEM & FFMPEG
# -----------------------------------

def resource_path(filename):
    base_path = getattr(
        sys,
        "_MEIPASS",
        os.path.dirname(os.path.abspath(__file__))
    )
    return os.path.join(base_path, filename)


def find_ffmpeg():
    system = platform.system()

    if system == "Windows":
        executable = "ffmpeg.exe"
    else:
        executable = "ffmpeg"

    bundled = resource_path(executable)

    if os.path.isfile(bundled):
        return bundled

    installed = shutil.which(executable)

    if installed:
        return installed

    return None


# -----------------------------------
# FOLDER SELECTION
# -----------------------------------

def choose_folder():
    global output_folder

    folder = filedialog.askdirectory()

    if folder:
        output_folder = folder
        folder_label.configure(text=folder)


# -----------------------------------
# DOWNLOAD PROGRESS
# -----------------------------------

def progress_hook(data):
    status = data.get("status")

    if status == "downloading":
        total = (
            data.get("total_bytes")
            or data.get("total_bytes_estimate")
        )

        downloaded = data.get("downloaded_bytes", 0)

        if total:
            progress = min(downloaded / total, 1)
            events.put(("progress", progress))

    elif status == "finished":
        events.put(("status", "Processing file..."))


# -----------------------------------
# DOWNLOAD ENGINE
# -----------------------------------

def download_worker(url, file_format, folder):
    try:
        ffmpeg_path = find_ffmpeg()

        if not ffmpeg_path:
            raise RuntimeError(
                "FFmpeg was not found.\n\n"
                "Install FFmpeg or bundle it with the application."
            )

        options = {
            "outtmpl": os.path.join(
                folder,
                "%(title).180B.%(ext)s"
            ),
            "noplaylist": True,
            "progress_hooks": [progress_hook],
            "ffmpeg_location": ffmpeg_path,
            "windowsfilenames": True,
            "quiet": True,
            "no_warnings": True,
        }

        if file_format == "MP3":
            options["format"] = "bestaudio/best"

            options["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]

        elif file_format == "MP4":
            options["format"] = "bv*+ba/b"
            options["merge_output_format"] = "mp4"

            options["postprocessors"] = [{
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }]

        events.put(("status", "Connecting..."))

        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([url])

        events.put(("done", "Download complete!"))

    except Exception as error:
        events.put(("error", str(error)))


# -----------------------------------
# START DOWNLOAD
# -----------------------------------

def start_download():
    url = url_entry.get().strip()
    file_format = format_menu.get()

    if not url.startswith(("https://", "http://")):
        messagebox.showerror(
            "Invalid URL",
            "Please enter a valid YouTube URL."
        )
        return

    if not os.path.isdir(output_folder):
        messagebox.showerror(
            "Invalid Folder",
            "The selected download folder does not exist."
        )
        return

    download_button.configure(state="disabled")
    progress_bar.set(0)
    status_label.configure(text="Starting download...")

    threading.Thread(
        target=download_worker,
        args=(url, file_format, output_folder),
        daemon=True
    ).start()


# -----------------------------------
# UPDATE GUI SAFELY
# -----------------------------------

def process_events():
    try:
        while True:
            event, value = events.get_nowait()

            if event == "progress":
                progress_bar.set(value)
                status_label.configure(
                    text=f"Downloading: {value:.0%}"
                )

            elif event == "status":
                status_label.configure(text=value)

            elif event == "done":
                progress_bar.set(1)
                status_label.configure(text=value)
                download_button.configure(state="normal")

            elif event == "error":
                status_label.configure(text="Download failed")
                download_button.configure(state="normal")

                messagebox.showerror(
                    "Download Error",
                    value
                )

    except queue.Empty:
        pass

    app.after(100, process_events)


# -----------------------------------
# USER INTERFACE
# -----------------------------------

title_label = ctk.CTkLabel(
    app,
    text="Media Downloader",
    font=("Arial", 26, "bold")
)
title_label.pack(pady=(25, 5))

subtitle_label = ctk.CTkLabel(
    app,
    text="YouTube to MP3 / MP4",
    text_color="gray"
)
subtitle_label.pack(pady=(0, 20))

url_entry = ctk.CTkEntry(
    app,
    width=450,
    height=38,
    placeholder_text="Paste YouTube link here..."
)
url_entry.pack(pady=10)

format_menu = ctk.CTkOptionMenu(
    app,
    values=["MP3", "MP4"],
    width=200
)
format_menu.set("MP3")
format_menu.pack(pady=10)

folder_button = ctk.CTkButton(
    app,
    text="Choose Download Folder",
    command=choose_folder
)
folder_button.pack(pady=10)

folder_label = ctk.CTkLabel(
    app,
    text=output_folder,
    wraplength=450,
    text_color="gray"
)
folder_label.pack(pady=5)

progress_bar = ctk.CTkProgressBar(
    app,
    width=450
)
progress_bar.set(0)
progress_bar.pack(pady=(20, 10))

status_label = ctk.CTkLabel(
    app,
    text="Ready"
)
status_label.pack(pady=5)

download_button = ctk.CTkButton(
    app,
    text="Download",
    width=200,
    height=40,
    command=start_download
)
download_button.pack(pady=15)

# -----------------------------------
# RUN APPLICATION
# -----------------------------------

app.after(100, process_events)
app.mainloop()
