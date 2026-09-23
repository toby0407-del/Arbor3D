# Cloud DBH worker — full GPU image for Azure Container Apps / local Docker.
# Build from repo root:
#   docker build -f cloud_dbh/Dockerfile -t arbor3d-cloud-dbh:latest .
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ARBOR3D_CLOUD_WORK_DIR=/var/arbor3d/jobs \
    PIP_NO_CACHE_DIR=1

WORKDIR /opt/arbor3d

RUN apt-get update && apt-get install -y --no-install-recommends \
      libgl1 \
      libglib2.0-0 \
      libgomp1 \
      curl \
    && rm -rf /var/lib/apt/lists/*

# API layer first (fast rebuild when only FastAPI changes)
COPY cloud_dbh/requirements.txt /tmp/cloud_dbh-requirements.txt
RUN pip install -r /tmp/cloud_dbh-requirements.txt

# Full measurement stack (PyTorch / Open3D / YOLO). Large; expect multi-GB image.
COPY requirements.txt /tmp/arbor3d-requirements.txt
RUN pip install -r /tmp/arbor3d-requirements.txt

COPY . /opt/arbor3d

RUN mkdir -p /var/arbor3d/jobs \
    && useradd --create-home --uid 10001 arbor \
    && chown -R arbor:arbor /opt/arbor3d /var/arbor3d

USER arbor
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8080/health || exit 1

ENV PYTHONPATH=/opt/arbor3d
CMD ["uvicorn", "cloud_dbh.app:app", "--host", "0.0.0.0", "--port", "8080"]
