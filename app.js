// ===================== BASIC CONFIG =====================
const api = window.location.origin;

// allowed resolutions
const ALLOWED_QUALITIES = ["144p", "240p", "360p", "480p", "720p", "1080p"];


// ===================== HISTORY SYSTEM =====================
function saveHistory(entry) {
    let history = JSON.parse(localStorage.getItem("awd_history") || "[]");

    history.unshift(entry);

    localStorage.setItem("awd_history", JSON.stringify(history));
}

function loadHistory() {
    const container = document.getElementById("historyList");
    const section = document.getElementById("historySection");

    let history = JSON.parse(localStorage.getItem("awd_history") || "[]");

    if (history.length === 0) {
        container.innerHTML = `<div style="color:#777;">No downloads yet.</div>`;
        section.style.display = "block";
        return;
    }

    container.innerHTML = "";

    history.forEach(item => {
        container.innerHTML += `
            <div class="quality-btn" style="flex-direction:column; align-items:flex-start;">
                <div><b>${item.title}</b></div>
                <div style="font-size:12px; color:#666;">${item.type} • ${item.time}</div>
                <button class="quality-download-btn" onclick="forceDownload('${api + "/file?path=" + encodeURIComponent(item.file)}')">
                    Download Again
                </button>
            </div>
        `;
    });

    section.style.display = "block";
}

function openHistory() {
    document.getElementById("results").style.display = "none";
    loadHistory();
}


// ===================== DOM ELEMENTS =====================
const urlInput = document.getElementById("urlInput");
const resultsSection = document.getElementById("results");
const thumbEl = document.getElementById("thumb");
const titleEl = document.getElementById("title");
const mp4List = document.getElementById("mp4List");
const progressArea = document.getElementById("progressArea");
const progressText = document.getElementById("progressText");
const barFill = document.getElementById("barFill");
const loadingBox = document.getElementById("loadingBox");
const skeletonBox = document.getElementById("skeletonBox");
const successBox = document.getElementById("successBox");
const errorBox = document.getElementById("errorBox");
const errorMsgEl = document.getElementById("errorMsg");
const platformBadge = document.getElementById("platformBadge");

let progressTimer = null;
window.currentURL = null;


// ===================== FORCE MOBILE DOWNLOAD =====================
function forceDownload(url) {
    const a = document.createElement("a");
    a.href = url;
    a.setAttribute("download", "");
    document.body.appendChild(a);
    a.click();
    a.remove();
}


// ===================== PLATFORM DETECTION =====================
function detectPlatform(url) {
    if (!url) return "Unknown";
    const u = url.toLowerCase();

    if (u.includes("instagram.com")) return "Instagram";
    if (u.includes("youtube.com") || u.includes("youtu.be")) return "YouTube";
    if (u.includes("tiktok.com")) return "TikTok";
    if (u.includes("facebook.com") || u.includes("fb.watch")) return "Facebook";
    if (u.includes("twitter.com") || u.includes("x.com")) return "Twitter/X";
    if (u.includes("reddit.com")) return "Reddit";
    if (u.includes("vimeo.com")) return "Vimeo";

    return "Unknown";
}

function updatePlatformBadge(name) {
    platformBadge.textContent = "Platform: " + name;
}


// ===================== UI HELPERS =====================
function showLoader() { loadingBox.style.display = "flex"; }
function hideLoader() { loadingBox.style.display = "none"; }
function showSkeleton() { skeletonBox.style.display = "block"; }
function hideSkeleton() { skeletonBox.style.display = "none"; }
function hideResults() { resultsSection.style.display = "none"; }

function showSuccess() {
    successBox.style.display = "block";
    setTimeout(() => successBox.style.display = "none", 2000);
}

function showError(msg) {
    errorMsgEl.textContent = msg;
    errorBox.style.display = "block";
    setTimeout(() => errorBox.style.display = "none", 2600);
}


// ===================== INSTAGRAM =====================
async function analyzeInstagram(url) {
    showLoader();
    hideResults();
    updatePlatformBadge("Instagram");

    try {
        const res = await fetch(api + "/instagram/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url })
        });

        const data = await res.json();
        hideLoader();

        if (data.error) return showError(data.error);

        thumbEl.style.display = "none";
        titleEl.innerText = data.caption || "Instagram Reel";

        mp4List.innerHTML = `
            <div class="quality-btn">
                <div>
                    <div class="quality-label">Download Reel (HD)</div>
                    <div class="quality-meta">Best Quality</div>
                </div>
                <button class="quality-download-btn" onclick="downloadInstagram('${url}')">
                    Download
                </button>
            </div>
        `;

        resultsSection.style.display = "block";
        showSuccess();
    } catch {
        hideLoader();
        showError("Instagram analyze failed.");
    }
}

async function downloadInstagram(url) {
    showLoader();
    updatePlatformBadge("Instagram");

    try {
        const res = await fetch(api + "/instagram/download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url })
        });

        const data = await res.json();
        hideLoader();

        if (data.error) return showError(data.error);

        let file = data.files[0];
        forceDownload(api + "/file?path=" + encodeURIComponent(file));

        saveHistory({
            title: "Instagram Reel",
            url,
            type: "Reel",
            time: new Date().toLocaleString(),
            file
        });

    } catch {
        hideLoader();
        showError("Instagram download failed.");
    }
}


// ===================== MAIN ANALYZE =====================
async function analyze() {
    const url = (urlInput.value || "").trim();

    if (!url) return showError("Paste a link first.");

    const platform = detectPlatform(url);
    updatePlatformBadge(platform);

    if (platform === "Instagram") return analyzeInstagram(url);

    showLoader();
    showSkeleton();
    hideResults();

    try {
        const res = await fetch(api + "/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url })
        });

        const data = await res.json();
        hideLoader();
        hideSkeleton();

        if (data.error) return showError(data.error);

        window.currentURL = url;

        thumbEl.style.display = "block";
        thumbEl.src = data.thumbnail;
        titleEl.textContent = data.title;

        buildQualityList(data.formats);

        resultsSection.style.display = "block";
        showSuccess();

    } catch {
        hideLoader();
        hideSkeleton();
        showError("Analyze failed.");
    }
}


// ===================== QUALITY LIST =====================
function toMB(bytes) {
    if (!bytes) return "Unknown";
    return (bytes / 1024 / 1024).toFixed(1) + " MB";
}

function buildQualityList(formats) {
    mp4List.innerHTML = "";

    const best = {};

    formats.forEach(f => {
        if (f.ext !== "mp4") return;

        // आता backend label आधीच "720p" असं देतो
        const match = (f.label || "").match(/(\d{3,4}p)/);
        if (!match) return;

        const q = match[1]; // e.g. "720p"

        if (!ALLOWED_QUALITIES.includes(q)) return;

        if (!best[q] || (f.filesize || 0) > (best[q].filesize || 0)) {
            best[q] = f;
        }
    });

    ALLOWED_QUALITIES.forEach(q => {
        if (best[q]) {
            let f = best[q];
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
        }
    });

    // जर काहीच quality मिळाली नाहीत तर user ला सांग
    if (!mp4List.innerHTML.trim()) {
        mp4List.innerHTML = `<div class="quality-meta">No standard 144p–1080p formats available for this video. Try another link.</div>`;
    }
}



// ===================== VIDEO DOWNLOAD =====================
async function downloadVideo(formatId) {
    if (!window.currentURL) return showError("Analyze first.");

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

        if (data.error) return showError(data.error);

        forceDownload(api + "/file?path=" + encodeURIComponent(data.file));

        saveHistory({
            title: titleEl.textContent,
            url: window.currentURL,
            type: "MP4",
            time: new Date().toLocaleString(),
            file: data.file
        });

    } catch {
        stopProgress();
        showError("Video download failed.");
    }
}


// ===================== AUDIO DOWNLOAD =====================
async function downloadAudio() {
    if (!window.currentURL) return showError("Analyze first.");

    startProgress("Audio");

    try {
        const res = await fetch(api + "/download/audio", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                url: window.currentURL
            })
        });

        const data = await res.json();
        stopProgress();

        if (data.error) return showError(data.error);

        forceDownload(api + "/file?path=" + encodeURIComponent(data.file));

        saveHistory({
            title: titleEl.textContent,
            url: window.currentURL,
            type: "MP3",
            time: new Date().toLocaleString(),
            file: data.file
        });

    } catch {
        stopProgress();
        showError("Audio download failed.");
    }
}


// ===================== PROGRESS BAR =====================
function startProgress(type) {
    progressArea.style.display = "block";
    progressText.textContent = `Starting ${type}…`;
    barFill.style.width = "0%";

    if (progressTimer) clearInterval(progressTimer);
    progressTimer = setInterval(updateProgress, 400);
}

function stopProgress() {
    if (progressTimer) clearInterval(progressTimer);
    progressTimer = null;
}

async function updateProgress() {
    try {
        const res = await fetch(api + "/progress");
        const p = await res.json();

        barFill.style.width = p.percent;
        progressText.textContent = `${p.percent} • ${p.speed} • ${p.eta}`;

        if (parseFloat(p.percent) >= 100) stopProgress();
    } catch {}
}


// ===================== ENTER KEY =====================
urlInput.addEventListener("keydown", e => {
    if (e.key === "Enter") analyze();
});
