from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import instaloader
import yt_dlp
import os, re, uuid, requests, time

app = Flask(__name__, static_folder="static")
CORS(app)

# -------------------------
# DIRECTORIES
# -------------------------
DOWNLOADS = "static/downloads"
os.makedirs(DOWNLOADS, exist_ok=True)

progress = {"percent": "0%", "speed": "", "eta": ""}


# -------------------------
# HOME ROUTE (SERVE HTML)
# -------------------------
@app.route("/")
def home():
    return send_file("index.html")


# -------------------------
# HELPERS
# -------------------------
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
    session_path = os.path.abspath(session_file)

    L = instaloader.Instaloader(download_video_thumbnails=False)

    try:
        L.load_session_from_file(username, session_path)
        return L
    except:
        return None


# -------------------------
# INSTAGRAM ANALYZE
# -------------------------
@app.route("/instagram/analyze", methods=["POST"])
def insta_analyze():
    try:
        url = request.json.get("url", "").strip()

        shortcode = extract_shortcode(url)
        if not shortcode:
            return jsonify({"error": "Invalid Instagram URL"}), 400

        L = get_instaloader()
        if not L:
            return jsonify({"error": "Instagram session missing"}), 400

        post = instaloader.Post.from_shortcode(L.context, shortcode)

        return jsonify({
            "status": "success",
            "thumbnail": "",
            "caption": post.caption or ""
        })
    except:
        return jsonify({"error": "Instagram analyze failed"}), 500


# -------------------------
# INSTAGRAM DOWNLOAD
# -------------------------
@app.route("/instagram/download", methods=["POST"])
def insta_download():
    try:
        url = request.json.get("url", "").strip()

        shortcode = extract_shortcode(url)
        if not shortcode:
            return jsonify({"error": "Invalid Instagram URL"}), 400

        L = get_instaloader()
        if not L:
            return jsonify({"error": "Session missing"}), 400

        post = instaloader.Post.from_shortcode(L.context, shortcode)

        filename = f"{uuid.uuid4()}.mp4"
        path = os.path.join(DOWNLOADS, filename)

        r = requests.get(post.video_url, stream=True)
        with open(path, "wb") as f:
            for chunk in r.iter_content(2048):
                f.write(chunk)

        return jsonify({"files": [path]})
    except:
        return jsonify({"error": "Instagram download failed"}), 500


# -------------------------
# GENERIC ANALYZE (YT, FB, X, etc.)
# -------------------------
@app.route("/analyze", methods=["POST"])
def analyze_generic():
    try:
        url = request.json.get("url", "").strip()

        with yt_dlp.YoutubeDL({"skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        for f in info.get("formats", []):
            label = f.get("format_note") or f.get("resolution")
            if not label:
                continue
            formats.append({
                "format_id": f.get("format_id"),
                "label": label,
                "ext": f.get("ext"),
                "filesize": f.get("filesize"),
                "filesize_approx": f.get("filesize_approx"),
            })

        return jsonify({
            "title": info.get("title", "Video"),
            "thumbnail": info.get("thumbnail", ""),
            "formats": formats
        })

    except Exception as e:
        print(e)
        return jsonify({"error": "Analyze failed"}), 500


# -------------------------
# VIDEO DOWNLOAD
# -------------------------
@app.route("/download/video", methods=["POST"])
def download_video():
    try:
        data = request.json
        url = data.get("url")
        format_id = data.get("format_id")

        info_simple = yt_dlp.YoutubeDL().extract_info(url, download=False)
        title = safe_filename(info_simple.get("title", "video"))
        out_tmpl = os.path.join(DOWNLOADS, f"{title}.%(ext)s")

        progress.update({"percent": "0%", "speed": "", "eta": ""})

        opts = {
            "format": format_id,
            "outtmpl": out_tmpl,
            "progress_hooks": [hook],
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url)

        file_path = ydl.prepare_filename(info)

        return jsonify({"file": file_path})
    except:
        return jsonify({"error": "Video download failed"}), 500


# -------------------------
# AUDIO DOWNLOAD
# -------------------------
@app.route("/download/audio", methods=["POST"])
def download_audio():
    try:
        url = request.json.get("url")

        info_simple = yt_dlp.YoutubeDL().extract_info(url, download=False)
        title = safe_filename(info_simple.get("title", "audio"))
        out_tmpl = os.path.join(DOWNLOADS, f"{title}.%(ext)s")

        progress.update({"percent": "0%", "speed": "", "eta": ""})

        opts = {
            "format": "bestaudio",
            "outtmpl": out_tmpl,
            "progress_hooks": [hook],
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url)

        out_file = ydl.prepare_filename(info).replace(".webm", ".mp3")

        return jsonify({"file": out_file})
    except:
        return jsonify({"error": "Audio download failed"}), 500


# -------------------------
# PROGRESS API
# -------------------------
@app.route("/progress")
def progress_api():
    return jsonify(progress)


# -------------------------
# SERVE DOWNLOADED FILE
# -------------------------
@app.route("/file")
def serve_file():
    path = request.args.get("path")

    if not path or not os.path.abspath(path).startswith(os.path.abspath(DOWNLOADS)):
        return jsonify({"error": "Invalid"}), 400

    if not os.path.exists(path):
        return jsonify({"error": "Not found"}), 404

    return send_file(path, as_attachment=True)


# -------------------------
# RUN LOCAL
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)
