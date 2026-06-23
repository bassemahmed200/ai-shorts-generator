FROM python:3.11-slim

# Install system dependencies including ffmpeg and fonts
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fonts-liberation \
    libass-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create storage directories
RUN mkdir -p storage/downloads storage/audio storage/clips storage/subtitles storage/transcripts

# Expose port
EXPOSE $PORT

# Run the application with dynamic port
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
