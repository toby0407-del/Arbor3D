# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS build
WORKDIR /opt/arbor3d/app
COPY app/package.json app/package-lock.json ./
RUN npm ci
COPY app/ ./
ARG VITE_AZURE_ENTRA_TENANT_ID=
ARG VITE_AZURE_ENTRA_CLIENT_ID=
ARG VITE_AZURE_ENTRA_API_SCOPE=
RUN npm run build
RUN npm prune --omit=dev

FROM node:22-bookworm-slim AS web
ENV NODE_ENV=production PORT=8080 HOST=0.0.0.0 \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg \
    PATH=/opt/venv/bin:$PATH ARBOR_AI_PROVIDER=local \
    ARBOR_RAG_KNOWLEDGE=/opt/arbor3d/agents/knowledge
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv zip fonts-noto-cjk tini \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv
COPY docker/requirements-web.txt /tmp/requirements-web.txt
RUN pip install --no-cache-dir --upgrade pip==25.3 \
    && pip install --no-cache-dir -r /tmp/requirements-web.txt
WORKDIR /opt/arbor3d/app
COPY --from=build --chown=node:node /opt/arbor3d/app/node_modules ./node_modules
COPY --from=build --chown=node:node /opt/arbor3d/app/dist ./dist
COPY --from=build --chown=node:node /opt/arbor3d/app/dist-server ./dist-server
COPY --from=build --chown=node:node /opt/arbor3d/app/public ./public
COPY --from=build --chown=node:node /opt/arbor3d/app/scripts ./scripts
COPY --from=build --chown=node:node /opt/arbor3d/app/package.json ./package.json
COPY --chown=node:node agents/knowledge /opt/arbor3d/agents/knowledge
RUN mkdir -p inbox .runtime /data /home/node/.cache && chown -R node:node inbox .runtime /data /home/node/.cache
USER node
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD node -e "fetch('http://127.0.0.1:8080/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["node", "dist-server/productionServer.js"]

FROM web AS full
USER root
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
# CPU wheels avoid downloading CUDA libraries on machines without a GPU runtime.
RUN pip install --no-cache-dir torch==2.6.0+cpu torchvision==0.21.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu
COPY docker/requirements-full.txt /tmp/requirements-full.txt
RUN pip install --no-cache-dir -r /tmp/requirements-full.txt
COPY --chown=node:node *.py /opt/arbor3d/
COPY --chown=node:node scripts /opt/arbor3d/scripts
COPY --chown=node:node dbh_seg /opt/arbor3d/dbh_seg
COPY --chown=node:node park_inventory /opt/arbor3d/park_inventory
COPY --chown=node:node geo_utils /opt/arbor3d/geo_utils
COPY --chown=node:node gaussian_prune /opt/arbor3d/gaussian_prune
COPY --chown=node:node semantic_seg /opt/arbor3d/semantic_seg
COPY --chown=node:node yolo_seg /opt/arbor3d/yolo_seg
ENV ARBOR3D_ROOT=/opt/arbor3d ARBOR3D_DATA_ROOT=/data
USER node
# Default docker build includes the complete measurement pipeline.
