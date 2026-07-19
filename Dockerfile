# AgentCrew MCN Docker Image
# Multi-stage build: lightweight runtime, optional Playwright support.
#
# Usage:
#   docker build -t agentcrew-mcn .
#   docker run -it --env-file .env agentcrew-mcn write generate -t "Python async"
#
# With Playwright (Zhihu support):
#   docker build --target playwright -t agentcrew-mcn .

# ── Base stage: install dependencies ────────────────────────────
FROM python:3.12-slim AS base

WORKDIR /app

# System deps for ChromaDB
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p data

ENTRYPOINT ["python", "-m", "cli.main"]


# ── CLI stage (default): lightweight, no browser ─────────────────
FROM base AS cli

LABEL org.opencontainers.image.description="AgentCrew MCN — AI multi-agent content marketing automation"
LABEL org.opencontainers.image.source="https://github.com/super-rick/agentcrew-mcn"

CMD ["--help"]


# ── Playwright stage: includes browser for Zhihu automation ─────
FROM base AS playwright

RUN pip install --no-cache-dir playwright \
    && playwright install --with-deps chromium \
    && playwright install-deps chromium

LABEL org.opencontainers.image.description="AgentCrew MCN with Playwright (Zhihu support)"


# ── Dashboard stage: Streamlit web UI ────────────────────────────
FROM base AS dashboard

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "dashboard/app.py", \
    "--server.address=0.0.0.0", "--server.port=8501"]
