FROM nousresearch/hermes-agent:latest

# The offline field-trip builder needs --embed-resources (pandoc >= 2.19);
# distro pandoc can be older, so install a pinned upstream release.
ARG PANDOC_VERSION=3.10

USER root
WORKDIR /workspace

COPY pyproject.toml /workspace/pyproject.toml

RUN set -eux; \
    if command -v apt-get >/dev/null 2>&1; then \
      apt-get update; \
      DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        chromium \
        curl \
        ffmpeg \
        git \
        imagemagick \
        inkscape \
        libopus0 \
        python3-pip \
        python3-venv; \
      rm -rf /var/lib/apt/lists/*; \
    fi; \
    arch="$(dpkg --print-architecture)"; \
    curl -fsSL "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-linux-${arch}.tar.gz" \
      | tar -xz -C /opt; \
    ln -sf "/opt/pandoc-${PANDOC_VERSION}/bin/pandoc" /usr/local/bin/pandoc; \
    uv pip install --python /opt/hermes/.venv/bin/python "faster-whisper>=1.1" "ddgs>=9.0" "edge-tts>=7.0"; \
    uv venv /workspace/.venv --python /opt/hermes/.venv/bin/python; \
    uv pip install --python /workspace/.venv/bin/python -e /workspace; \
    chown -R hermes:hermes /workspace/.venv

COPY --chown=hermes:hermes . /workspace

RUN set -eux; \
    mkdir -p /workspace/curricula /workspace/lesson-logs /workspace/tablet-slides /workspace/generated-images /workspace/dashboards /workspace/field-trips /workspace/.backups /workspace/.logs /workspace/.scratch; \
    chown -R hermes:hermes /workspace/curricula /workspace/lesson-logs /workspace/tablet-slides /workspace/generated-images /workspace/dashboards /workspace/field-trips /workspace/.backups /workspace/.logs /workspace/.scratch

ENV PATH="/workspace/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED="1"
