from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import instaloader
import yt_dlp
import os, re, uuid, requests, time

app = Flask(__name__, static_folder="static")
CORS(app)

DOWNLOADS = "static/downloads"
os.makedirs(DOWNLOADS, exist_ok=True)

progress = {"percent": "0%", "speed": "", "eta": ""}

# ---------------------------------------------
# STATIC FILE SERVE
# ---------------------------------------------
@app.route('/<path:path>')
def serve_static_file(path):
    return send_file(path)

# ---------------------------------------------
# HOME ROUTE
# ---------------------------------------------
@app.route("/")
def home():
    return send_file("index.html")

# ---------------------------------------------
# HELPERS
# ---------------------------------------------
def safe_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "", name).strip()

def hook(d):
    if d.get("status") == "downloading":
        progress["percent"] = d.get("_percent_str", "0%").strip()
        progress["speed"] = d.get("_speed_str", "")
        progress["eta"] = str(d.get("eta", ""))

def extract_shortcode(url: str):
    m = re.findall(r"/(reel|p|tv)/([^/?]+)", url)
    return m[0][1] if m else None

def get_instaloader():
    username = "aniketwebdev.dev"
    session_file = f"session-{username}"
    if not os.path.exists(session_file):
        return None

    L = instaloader.Instaloader(download_video_thumbnails=False)
    try:
        L.load_session_from_file(username, session_file)
        return L
    except:
        return None

# -----------------------------------------------------------
# YOUTUBE COOKIE ENABLED yt-dlp OPTIONS
# -----------------------------------------------------------
def yt_options(extra=None):
    base = {
        "cookiefile": "youtube_cookies.txt",   # <-- MOST IMPORTANT LINE
        "skip_download": True,
    }
    if extra:
        base.update(extra)
    return base

# -----------------------------------------------------------
# ANALYZE (YOUTUBE, TIKTOK, FB, ETC)
# -----------------------------------------------------------
@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        url = request.json.get("url", "").strip()

        opts = {
            "cookiefile": "www.youtube.com_cookies.txt",  # RIGHT COOKIE
            "skip_download": True,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []

        for f in info.get("formats", []):
            ext = f.get("ext")
            if ext != "mp4":
                continue

            height = f.get("height")

            # fallback if height missing
            if not height:
                res = f.get("resolution")  # e.g. "1920x1080"
                if res and "x" in res:
                    height = res.split("x")[1]

            if not height:
                continue

            label = f"{height}p"
            filesize = f.get("filesize") or f.get("filesize_approx")

            formats.append({
                "format_id": f.get("format_id"),
                "label": label,
                "ext": "mp4",
                "filesize": filesize
            })

        print("Formats found:", len(formats))

        return jsonify({
            "title": info.get("title", "Video"),
            "thumbnail": info.get("thumbnail", ""),
            "formats": formats
        })

    except Exception as e:
        print("ANALYZE ERROR:", e)
        return jsonify({"error": "Analyze failed"}), 500


# -----------------------------------------------------------
# DOWNLOAD VIDEO
# -----------------------------------------------------------
@app.route("/download/video", methods=["POST"])
def download_video():
    try:
        data = request.json
        url = data["url"]
        format_id = data["format_id"]

        info_simple = yt_dlp.YoutubeDL(yt_options()).extract_info(url, download=False)
        title = safe_filename(info_simple["title"])

        out_tmpl = os.path.join(DOWNLOADS, f"{title}.%(ext)s")
        progress.update({"percent": "0%", "speed": "", "eta": ""})

        opts = yt_options({
            "format": format_id,
            "outtmpl": out_tmpl,
            "progress_hooks": [hook]
        })

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url)

        return jsonify({"file": ydl.prepare_filename(info)})
    except Exception as e:
        print("VIDEO ERROR:", e)
        return jsonify({"error": "Video download failed"}), 500

# -----------------------------------------------------------
# DOWNLOAD MP3
# -----------------------------------------------------------
@app.route("/download/audio", methods=["POST"])
def download_audio():
    try:
        url = request.json["url"]

        info_simple = yt_dlp.YoutubeDL(yt_options()).extract_info(url, download=False)
        title = safe_filename(info_simple["title"])

        out_tmpl = os.path.join(DOWNLOADS, f"{title}.%(ext)s")
        progress.update({"percent": "0%", "speed": "", "eta": ""})

        opts = yt_options({
            "format": "bestaudio",
            "outtmpl": out_tmpl,
            "progress_hooks": [hook],
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            }]
        })

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url)

        file_out = ydl.prepare_filename(info).replace(".webm", ".mp3")
        return jsonify({"file": file_out})

    except Exception as e:
        print("AUDIO ERROR:", e)
        return jsonify({"error": "Audio download failed"}), 500

# -----------------------------------------------------------
# PROGRESS
# -----------------------------------------------------------
@app.route("/progress")
def prog():
    return jsonify(progress)

# -----------------------------------------------------------
# SERVE DOWNLOADED FILE
# -----------------------------------------------------------
@app.route("/file")
def file():
    path = request.args.get("path", "")

    if not path.startswith(DOWNLOADS):
        return jsonify({"error": "Invalid"}), 400

    if not os.path.exists(path):
        return jsonify({"error": "Not found"}), 404

    return send_file(path, as_attachment=True)

# -----------------------------------------------------------
# LOCAL RUN
# -----------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
