# -----------------------------
# 1) Base Python environment
# -----------------------------
FROM python:3.10-slim

# -----------------------------
# 2) Install system dependencies
# -----------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# 3) App folder
# -----------------------------
WORKDIR /app

# -----------------------------
# 4) Copy requirements & install
# -----------------------------
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# -----------------------------
# 5) Copy entire project
# -----------------------------
COPY . .

# -----------------------------
# 6) Expose Render port
# -----------------------------
EXPOSE 10000

# -----------------------------
# 7) Start app
# -----------------------------
CMD ["python", "server.py"]
