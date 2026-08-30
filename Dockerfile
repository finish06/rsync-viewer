# ---- Stage 1: build the React SPA (specs/insight-ui.md AC-025) ----
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
# --ignore-scripts: platform binaries (rolldown, oxlint) are optional deps that
# need no build; skipping scripts avoids fsevents' node-gyp compile on macOS.
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY frontend/ ./
# vite.config.ts writes to ../app/static/app; give it that path inside the stage
RUN mkdir -p /app/static && npm run build

# ---- Stage 2: Python runtime ----
FROM python:3.11-slim

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app ./app
COPY alembic.ini .
COPY alembic ./alembic
COPY CHANGELOG.md .
COPY entrypoint.sh .

# Built SPA assets, served by the /static mount and the /app shell route
COPY --from=frontend /app/static/app ./app/static/app

ENTRYPOINT ["/app/entrypoint.sh"]
# FORWARDED_ALLOW_IPS: IPs allowed to set X-Forwarded-* (default: loopback only).
# Set it to your reverse proxy's IP; wildcard trust is opt-in and discouraged.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips \"${FORWARDED_ALLOW_IPS:-127.0.0.1}\""]
