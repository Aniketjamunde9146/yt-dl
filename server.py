from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import yt_dlp
import instaloader
import os, re, uuid, time

app = Flask(__name__, static_folder="static", template_folder=".")
CORS(app)

# ------------------------------
# CONFIG
# ------------------------------
DOWNLOADS = "static/downloads"
os.makedirs(DOWNLOADS, exist_ok=True)

COOKIE_FILE = "youtube_cookies.txt"

progress = {"percent": "0%", "speed": "", "eta": ""}


# ------------------------------
# SAFE FILENAME
# ------------------------------
def safe_filename(name):
    return re.sub(r'[<>:"/\\|?*]', "", name).strip()


# ------------------------------
# YT-DLP OPTIONS
# ------------------------------
def yt_options(extra=None):
    base = {
        "quiet": True,
        "cookiefile": COOKIE_FILE,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }
    if extra:
        base.update(extra)
    return base


# ------------------------------
# INSTAGRAM LOADER (LOGIN SESSION)
# ------------------------------
def get_instaloader():
    username = "aniketwebdev.dev"
    session_file = f"session-{username}"

    if not os.path.exists(session_file):
        return None

    loader = instaloader.Instaloader(download_video_thumbnails=False)
    try:
        loader.load_session_from_file(username, session_file)
        return loader
    except:
        return None


# ------------------------------
# STATIC ROUTE
# ------------------------------
@app.route("/")
def home():
    return send_file("index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


# ------------------------------
# ANALYZE (YOUTUBE)
# ------------------------------
@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        url = request.json["url"].strip()

        with yt_dlp.YoutubeDL(yt_options()) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        for f in info.get("formats", []):
            if f.get("ext") != "mp4":
                continue

            height = f.get("height")
            if not height:
                continue

            formats.append({
                "format_id": f["format_id"],
                "label": f"{height}p",
                "ext": "mp4",
                "filesize": f.get("filesize") or f.get("filesize_approx"),
            })

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "formats": formats
        })

    except Exception as e:
        print("ANALYZE ERROR:", e)
        return jsonify({"error": "Analyze failed"}), 500


# ------------------------------
# YT PROGRESS HOOK
# ------------------------------
def hook(d):
    if d.get("status") == "downloading":
        progress["percent"] = d.get("_percent_str", "0%").strip()
        progress["speed"] = d.get("_speed_str", "")
        progress["eta"] = str(d.get("eta", ""))


# ------------------------------
# DOWNLOAD VIDEO
# ------------------------------
@app.route("/download/video", methods=["POST"])
def download_video():
    try:
        data = request.json
        url = data["url"]
        format_id = data["format_id"]

        info = yt_dlp.YoutubeDL(yt_options()).extract_info(url, download=False)
        title = safe_filename(info["title"])

        out_path = os.path.join(DOWNLOADS, f"{title}.%(ext)s")
        progress.update({"percent": "0%", "speed": "", "eta": ""})

        opts = yt_options({
            "format": format_id,
            "outtmpl": out_path,
            "skip_download": False,
            "progress_hooks": [hook],
        })

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url)

        file_path = ydl.prepare_filename(info)
        return jsonify({"file": file_path})

    except Exception as e:
        print("VIDEO DOWNLOAD ERROR:", e)
        return jsonify({"error": "Download failed"}), 500


# ------------------------------
# DOWNLOAD AUDIO (MP3)
# ------------------------------
@app.route("/download/audio", methods=["POST"])
def download_audio():
    try:
        url = request.json["url"]

        info = yt_dlp.YoutubeDL(yt_options()).extract_info(url, download=False)
        title = safe_filename(info["title"])

        out_path = os.path.join(DOWNLOADS, f"{title}.%(ext)s")
        progress.update({"percent": "0%", "speed": "", "eta": ""})

        opts = yt_options({
            "format": "bestaudio",
            "outtmpl": out_path,
            "skip_download": False,
            "progress_hooks": [hook],
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url)

        file_path = ydl.prepare_filename(info).replace(".webm", ".mp3")
        return jsonify({"file": file_path})

    except Exception as e:
        print("AUDIO ERROR:", e)
        return jsonify({"error": "MP3 failed"}), 500


# ------------------------------
# PROGRESS POLL
# ------------------------------
@app.route("/progress")
def progress_route():
    return jsonify(progress)


# ------------------------------
# SERVE DOWNLOADED FILE
# ------------------------------
@app.route("/file")
def serve_file():
    file_path = request.args.get("path", "")

    if not os.path.isfile(file_path):
        return jsonify({"error": "File not found"}), 404

    return send_file(file_path, as_attachment=True)


# ------------------------------
# RUN
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
