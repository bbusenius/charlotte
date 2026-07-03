FROM ghcr.io/openclaw/openclaw:latest

# Local single-user build. Pass your host IDs so files the agent writes to
# bind mounts stay host-owned:
#   docker build -f runtime/openclaw/Dockerfile \
#     --build-arg CHARLOTTE_UID="$(id -u)" --build-arg CHARLOTTE_GID="$(id -g)" \
#     -t charlotte-openclaw:local .
ARG CHARLOTTE_UID=1000
ARG CHARLOTTE_GID=1000

# Debian bookworm's apt pandoc is 2.17; the offline field-trip builder needs
# --embed-resources (pandoc >= 2.19), so install a pinned upstream release.
ARG PANDOC_VERSION=3.10

USER root

# The base image is node:24-bookworm-slim; Debian bookworm ships Python 3.11
# but the project requires >=3.12, so uv provisions a managed interpreter.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python

COPY pyproject.toml /workspace/pyproject.toml

RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      chromium \
      ffmpeg \
      fonts-dejavu \
      fonts-freefont-ttf \
      fonts-liberation \
      git \
      imagemagick \
      inkscape \
      libopus0 \
      libpango-1.0-0 \
      libpangoft2-1.0-0; \
    rm -rf /var/lib/apt/lists/*; \
    arch="$(dpkg --print-architecture)"; \
    curl -fsSL "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-linux-${arch}.tar.gz" \
      | tar -xz -C /opt; \
    ln -sf "/opt/pandoc-${PANDOC_VERSION}/bin/pandoc" /usr/local/bin/pandoc; \
    uv venv /workspace/.venv --python 3.12; \
    uv pip install --python /workspace/.venv/bin/python -e /workspace; \
    chmod -R a+rX /opt/uv-python; \
    npm install -g mcporter

COPY . /workspace

RUN set -eux; \
    mkdir -p \
      /workspace/curricula /workspace/tablet-slides /workspace/generated-images \
      /workspace/dashboards /workspace/field-trips /workspace/.backups /workspace/.logs \
      /workspace/.agent-state; \
    # OpenClaw's per-agent identity/memory files live in the host profile's
    # workspace-state dir, mounted at /workspace/.agent-state. Symlinks (not
    # per-file bind mounts) connect them: a directory mount keeps tracking
    # host edits, while single-file mounts go stale when an editor or
    # install(1) replaces the file's inode.
    for f in SOUL.md IDENTITY.md USER.md TOOLS.md MEMORY.md HEARTBEAT.md BOOT.md; do \
      ln -sf ".agent-state/$f" "/workspace/$f"; \
    done; \
    ln -sfn .agent-state/memory /workspace/memory; \
    ln -sfn .agent-state/canvas /workspace/canvas; \
    if [ "$CHARLOTTE_GID" != "$(getent group node | cut -d: -f3)" ]; then groupmod -o -g "$CHARLOTTE_GID" node; fi; \
    if [ "$CHARLOTTE_UID" != "$(id -u node)" ]; then usermod -o -u "$CHARLOTTE_UID" node; fi; \
    chown -R node:node /workspace /home/node

ENV PATH="/workspace/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED="1"

# Keep the base image's WORKDIR, ENTRYPOINT, and CMD so the default container
# command still starts the OpenClaw gateway. The agent's cwd is set by
# `agents.defaults.workspace` in openclaw.json, not by the image WORKDIR.
USER node
