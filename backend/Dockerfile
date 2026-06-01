FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY . .

# Expose port (Render sets PORT env variable)
ENV PORT=8000
EXPOSE 8000

# Start Uvicorn
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
