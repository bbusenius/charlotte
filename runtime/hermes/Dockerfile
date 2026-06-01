FROM nousresearch/hermes-agent:latest

USER root
WORKDIR /workspace

COPY pyproject.toml /workspace/pyproject.toml

RUN set -eux; \
    if command -v apt-get >/dev/null 2>&1; then \
      apt-get update; \
      DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        inkscape \
        libopus0 \
        python3-pip \
        python3-venv; \
      rm -rf /var/lib/apt/lists/*; \
    fi; \
    uv pip install --python /opt/hermes/.venv/bin/python "faster-whisper>=1.1" "ddgs>=9.0" "edge-tts>=7.0"; \
    uv venv /workspace/.venv --python /opt/hermes/.venv/bin/python; \
    uv pip install --python /workspace/.venv/bin/python -e /workspace; \
    chown -R hermes:hermes /workspace/.venv

COPY --chown=hermes:hermes . /workspace

RUN set -eux; \
    mkdir -p /workspace/curricula /workspace/tablet-slides /workspace/generated-images /workspace/dashboards /workspace/field-trips /workspace/.backups /workspace/.logs; \
    chown -R hermes:hermes /workspace/curricula /workspace/tablet-slides /workspace/generated-images /workspace/dashboards /workspace/field-trips /workspace/.backups /workspace/.logs

ENV PATH="/workspace/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED="1"
