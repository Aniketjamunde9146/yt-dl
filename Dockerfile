# -----------------------------
# 1) Base Python image
# -----------------------------
FROM python:3.10-slim

# -----------------------------
# 2) System dependencies
# -----------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    npm \
    curl && \
    rm -rf /var/lib/apt/lists/*

# -----------------------------
# 3) Create app directory
# -----------------------------
WORKDIR /app

# -----------------------------
# 4) Copy requirements + install
# -----------------------------
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# -----------------------------
# 5) Copy entire app
# -----------------------------
COPY . /app/

# -----------------------------
# 6) Expose port (Render uses 10000 automatically)
# -----------------------------
EXPOSE 10000

# -----------------------------
# 7) Start command
# -----------------------------
CMD ["python", "server.py"]
