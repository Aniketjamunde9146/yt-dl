// ===================== BASIC CONFIG =====================
const api = window.location.origin;

// Allowed resolutions
const ALLOWED_QUALITIES = ["144p", "240p", "360p", "480p", "720p", "1080p"];

// ===================== DOM ELEMENTS =====================
const urlInput = document.getElementById("urlInput");
const resultsSection = document.getElementById("results");
const thumbEl = document.getElementById("thumb");
const titleEl = document.getElementById("title");
const mp4List = document.getElementById("mp4List");

const progressArea = document.getElementById("progressArea");
const progressText = document.getElementById("progressText");
const barFill = document.getElementById("barFill");

const platformBadge = document.getElementById("platformBadge");

const successBox = document.getElementById("successBox");
const errorBox = document.getElementById("errorBox");

let progressTimer = null;
window.currentURL = null;

// ===================== PLATFORM DETECTION =====================
function detectPlatform(url) {
    if (!url) return "Auto";
    const u = url.toLowerCase();

    if (u.includes("youtube.com") || u.includes("youtu.be")) return "YouTube";
    if (u.includes("instagram.com")) return "Instagram";
    if (u.includes("tiktok.com")) return "TikTok";
    if (u.includes("facebook.com") || u.includes("fb.watch")) return "Facebook";
    if (u.includes("twitter.com") || u.includes("x.com")) return "Twitter/X";
    if (u.includes("reddit.com")) return "Reddit";
    if (u.includes("vimeo.com")) return "Vimeo";

    return "Unknown";
}

function updatePlatformBadge(name) {
    if (!platformBadge) return;
    platformBadge.textContent = "Platform: " + name;
}

// ===================== UI HELPERS =====================
function showSuccess(msg = "✔ Done") {
    if (!successBox) return;
    successBox.textContent = msg;
    successBox.style.display = "block";
    setTimeout(() => {
        successBox.style.display = "none";
    }, 2000);
}

function showError(msg) {
    if (!errorBox) return;
    errorBox.textContent = msg;
    errorBox.style.display = "block";
    setTimeout(() => {
        errorBox.style.display = "none";
    }, 2600);
}

function showResults() {
    if (resultsSection) resultsSection.style.display = "block";
}

function hideResults() {
    if (resultsSection) resultsSection.style.display = "none";
}

// ===================== CLIPBOARD PASTE =====================
async function pasteFromClipboard() {
    try {
        if (!navigator.clipboard || !navigator.clipboard.readText) {
            return showError("Clipboard not supported in this browser.");
        }
        const text = await navigator.clipboard.readText();
        if (!text) return showError("Clipboard is empty.");
        urlInput.value = text.trim();
        showSuccess("Link pasted.");
    } catch (e) {
        showError("Failed to read clipboard.");
    }
}

// Make it global (button calls it)
window.pasteFromClipboard = pasteFromClipboard;

// ===================== SIZE HELPER =====================
function toMB(bytes) {
    if (!bytes) return "Unknown size";
    return (bytes / 1024 / 1024).toFixed(1) + " MB";
}

// ===================== BUILD QUALITY LIST =====================
function buildQualityList(formats) {
    mp4List.innerHTML = "";

    // Keep best file for each allowed quality
    const bestByQuality = {};

    (formats || []).forEach(f => {
        if (f.ext !== "mp4") return;

        const label = f.label || "";
        const match = label.match(/(\d{3,4}p)/);
        if (!match) return;

        const q = match[1]; // e.g., "720p"
        if (!ALLOWED_QUALITIES.includes(q)) return;

        if (!bestByQuality[q] || (f.filesize || 0) > (bestByQuality[q].filesize || 0)) {
            bestByQuality[q] = f;
        }
    });

    ALLOWED_QUALITIES.forEach(q => {
        const f = bestByQuality[q];
        if (!f) return;

        mp4List.innerHTML += `
            <div class="quality-btn">
                <div>
                    <div class="quality-label">${q}</div>
                    <div class="quality-meta">${toMB(f.filesize)}</div>
                </div>
                <button class="quality-download-btn" onclick="downloadVideo('${f.format_id}')">
                    Download
                </button>
            </div>
        `;
    });

    if (!mp4List.innerHTML.trim()) {
        mp4List.innerHTML = `<div class="quality-meta">No standard 144p–1080p formats found for this video.</div>`;
    }
}

// ===================== ANALYZE =====================
async function analyze() {
    const url = (urlInput.value || "").trim();
    if (!url) return showError("Paste a video link first.");

    const platform = detectPlatform(url);
    updatePlatformBadge(platform);

    hideResults();

    try {
        const res = await fetch(api + "/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url })
        });

        const data = await res.json();

        if (!res.ok || data.error) {
            console.error("Analyze error:", data.error);
            return showError("Analyze failed. Try another link.");
        }

        window.currentURL = url;

        if (data.thumbnail) {
            thumbEl.src = data.thumbnail;
            thumbEl.style.display = "block";
        } else {
            thumbEl.style.display = "none";
        }

        titleEl.textContent = data.title || "Video";

        buildQualityList(data.formats || []);
        showResults();
        showSuccess("Analyze complete.");
    } catch (e) {
        console.error(e);
        showError("Analyze failed (network error).");
    }
}

// Make analyze available for inline onclick
window.analyze = analyze;

// ===================== FORCE DOWNLOAD (Mobile safe) =====================
function forceDownload(url) {
    const a = document.createElement("a");
    a.href = url;
    a.setAttribute("download", "");
    document.body.appendChild(a);
    a.click();
    a.remove();
}

// ===================== DOWNLOAD VIDEO =====================
async function downloadVideo(formatId) {
    if (!window.currentURL) return showError("Analyze the link first.");

    startProgress("Video");

    try {
        const res = await fetch(api + "/download/video", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                url: window.currentURL,
                format_id: formatId
            })
        });

        const data = await res.json();
        stopProgress();

        if (!res.ok || data.error) {
            console.error("Video download error:", data.error);
            return showError("Video download failed.");
        }

        const filePath = data.file;
        forceDownload(api + "/file?path=" + encodeURIComponent(filePath));
        showSuccess("Download ready.");
    } catch (e) {
        console.error(e);
        stopProgress();
        showError("Video download failed.");
    }
}

window.downloadVideo = downloadVideo;

// ===================== DOWNLOAD AUDIO (MP3) =====================
async function downloadAudio() {
    if (!window.currentURL) return showError("Analyze the link first.");

    startProgress("Audio");

    try {
        const res = await fetch(api + "/download/audio", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: window.currentURL })
        });

        const data = await res.json();
        stopProgress();

        if (!res.ok || data.error) {
            console.error("Audio download error:", data.error);
            return showError("MP3 download failed.");
        }

        const filePath = data.file;
        forceDownload(api + "/file?path=" + encodeURIComponent(filePath));
        showSuccess("MP3 ready.");
    } catch (e) {
        console.error(e);
        stopProgress();
        showError("MP3 download failed.");
    }
}

window.downloadAudio = downloadAudio;

// ===================== PROGRESS BAR =====================
function startProgress(type) {
    if (!progressArea) return;
    progressArea.style.display = "block";
    progressText.textContent = `Starting ${type}…`;
    barFill.style.width = "0%";

    if (progressTimer) clearInterval(progressTimer);
    progressTimer = setInterval(updateProgress, 500);
}

function stopProgress() {
    if (progressTimer) clearInterval(progressTimer);
    progressTimer = null;
}

async function updateProgress() {
    try {
        const res = await fetch(api + "/progress");
        const p = await res.json();

        const percentStr = p.percent || "0%";
        barFill.style.width = percentStr;
        progressText.textContent = `${percentStr} • ${p.speed || ""} • ${p.eta || ""}`;

        const numeric = parseFloat(percentStr.replace("%", "")) || 0;
        if (numeric >= 100) {
            stopProgress();
        }
    } catch (e) {
        console.error("Progress error:", e);
    }
}

// ===================== ENTER KEY =====================
urlInput.addEventListener("keydown", e => {
    if (e.key === "Enter") {
        analyze();
    }
});
