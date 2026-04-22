# --------- Stage 1: Build ---------
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (better caching)
COPY requirements.txt .

# Install dependencies into a separate location
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --------- Stage 2: Runtime ---------
FROM python:3.12-slim

WORKDIR /app

# Install only runtime dependencies (NOT dev)
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy project code
COPY . .

EXPOSE 8001

CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8001", "--workers", "3"]