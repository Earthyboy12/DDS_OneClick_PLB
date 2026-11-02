FROM python:3.12-slim

# Install system dependencies including Thai fonts for 4K Studio figures
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-thai-tlwg \
    fontconfig \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files and reference database
COPY app ./app
COPY dds_reference ./dds_reference
COPY data_fixtures ./data_fixtures

# Environment variables
ENV PORT=8000
ENV MAX_UPLOAD_SIZE_MB=200
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
