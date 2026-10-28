# FROM nousresearch/hermes-agent:latest
FROM nousresearch/hermes-agent:v0.22.5@sha256:9c5561579f3ffdf333401797094ac3a743738d6c25d40f4331c7bf77b694238d

# The offline field-trip builder needs --embed-resources (pandoc >= 2.19);
# distro pandoc can be older, so install a pinned upstream release.
ARG PANDOC_VERSION=3.10

USER root
WORKDIR /workspace

COPY pyproject.toml /workspace/pyproject.toml

# The base image already provides curl, git, ffmpeg, Chromium, Node, and
# Python. uv is installed but not on PATH, so link the packaged binary.
# DuckDuckGo search, local Whisper,
# and Edge TTS are recorded extras: a pip install into the sealed venv is
# dropped on startup.
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      file \
      imagemagick \
      inkscape \
      libopus0 \
      poppler-utils; \
    rm -rf /var/lib/apt/lists/*; \
    arch="$(dpkg --print-architecture)"; \
    curl -fsSL "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-linux-${arch}.tar.gz" \
      | tar -xz -C /opt; \
    ln -sf "/opt/pandoc-${PANDOC_VERSION}/bin/pandoc" /usr/local/bin/pandoc; \
    rm -rf /opt/hermes/.venv; \
    PYTHONPATH=/opt/hermes /usr/local/bin/python3 -m pm.build_env \
      --source /opt/hermes --python /usr/local/bin/python3 \
      --cache /opt/hermes/uv-cache \
      --out /opt/hermes/.venv --no-install-project --sealed --record-selection \
      --extra all --extra messaging --extra otlp --extra anthropic --extra bedrock \
      --extra azure-identity --extra matrix --extra google-chat \
      --extra ddgs --extra stt-whisper --extra edge-tts; \
    uv_bin="$(PYTHONPATH=/opt/hermes /usr/local/bin/python3 -c 'from pm.install import uv_launcher; print(uv_launcher("uv"))')"; \
    uvx_bin="$(PYTHONPATH=/opt/hermes /usr/local/bin/python3 -c 'from pm.install import uv_launcher; print(uv_launcher("uvx"))')"; \
    ln -sfn "$uv_bin" /usr/local/bin/uv; \
    ln -sfn "$uvx_bin" /usr/local/bin/uvx; \
    uv venv /workspace/.venv --python /opt/hermes/.venv/bin/python; \
    uv pip install --python /workspace/.venv/bin/python -e /workspace; \
    chown -R hermes:hermes /workspace/.venv

# build_env replaces the sealed venv. The image launcher is a symlink into
# libexec, and the project is found through a path file, not an installed copy.
RUN set -eux; \
    ln -sfn ../../libexec/hermes /opt/hermes/.venv/bin/hermes; \
    ln -sfn ../../libexec/hermes-acp /opt/hermes/.venv/bin/hermes-acp; \
    ln -sfn ../../libexec/hermes-agent /opt/hermes/.venv/bin/hermes-agent; \
    site="$(/opt/hermes/.venv/bin/python -c 'import site; print(site.getsitepackages()[0])')"; \
    rel="$(/opt/hermes/.venv/bin/python -c 'import os, sys; print(os.path.relpath("/opt/hermes", sys.argv[1]))' "$site")"; \
    printf '%s\n' "$rel" > "$site/hermes-agent.pth"; \
    chmod a+r /opt/hermes/tools/facts.json

COPY --chown=hermes:hermes . /workspace
COPY --chown=hermes:hermes runtime/hermes/plugins/image_gen/gemini /opt/hermes/plugins/image_gen/gemini

RUN set -eux; \
    mkdir -p /workspace/curricula /workspace/lesson-logs /workspace/tablet-slides /workspace/generated-images /workspace/dashboards /workspace/field-trips /workspace/.backups /workspace/.logs /workspace/.state /workspace/.scratch; \
    chown -R hermes:hermes /workspace/curricula /workspace/lesson-logs /workspace/tablet-slides /workspace/generated-images /workspace/dashboards /workspace/field-trips /workspace/.backups /workspace/.logs /workspace/.state /workspace/.scratch

ENV PATH="/workspace/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED="1"
