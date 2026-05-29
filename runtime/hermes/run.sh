#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../.." && pwd)"
env_file="$repo_root/.env"

read_env_value() {
  local key="$1"
  local file="$2"
  local line value

  if [ ! -f "$file" ]; then
    return 0
  fi

  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      "$key="*)
        value="${line#"$key="}"
        if [[ "$value" == \"*\" && "$value" == *\" ]]; then
          value="${value:1:${#value}-2}"
        elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
          value="${value:1:${#value}-2}"
        fi
        printf '%s' "$value"
        return 0
        ;;
    esac
  done < "$file"
}

detect_lan_ip() {
  local ip_address

  if command -v ip >/dev/null 2>&1; then
    ip_address="$(ip -o -4 addr show scope global up 2>/dev/null | awk '
      function ignored_iface(iface) {
        return iface ~ /^(docker|br-|veth|virbr|tun|tap|wg|tailscale|zt|cni|podman|nerdctl)/
      }
      function private_ip(ip) {
        return ip ~ /^192[.]168[.]/ || ip ~ /^10[.]/ || ip ~ /^172[.](1[6-9]|2[0-9]|3[0-1])[.]/
      }
      function preferred_iface(iface) {
        return iface ~ /^(wl|en|eth)/
      }
      {
        iface = $2
        split($4, addr, "/")
        ip = addr[1]
        if (ignored_iface(iface) || !private_ip(ip)) {
          next
        }
        if (preferred_iface(iface)) {
          candidate = ""
          print ip
          exit
        }
        if (candidate == "") {
          candidate = ip
        }
      }
      END {
        if (candidate != "") {
          print candidate
        }
      }
    ')"
    if [ -n "$ip_address" ]; then
      printf '%s' "$ip_address"
      return 0
    fi

    ip_address="$(ip route get 1.1.1.1 2>/dev/null | awk '
      {
        for (i = 1; i <= NF; i++) {
          if ($i == "dev") {
            dev = $(i + 1)
          } else if ($i == "src") {
            src = $(i + 1)
          }
        }
      }
      END {
        if (src != "" && dev !~ /^(docker|br-|veth|virbr|tun|tap|wg|tailscale|zt|cni|podman|nerdctl)/) {
          print src
        }
      }
    ')"
    if [ -n "$ip_address" ]; then
      printf '%s' "$ip_address"
      return 0
    fi
  fi

  if command -v hostname >/dev/null 2>&1; then
    ip_address="$(hostname -I 2>/dev/null | awk '
      {
        for (i = 1; i <= NF; i++) {
          if ($i ~ /^192[.]168[.]/) {
            candidate = ""
            print $i
            exit
          }
          if (candidate == "" && $i ~ /^10[.]/) {
            candidate = $i
          }
          if (candidate == "" && $i ~ /^172[.](1[6-9]|2[0-9]|3[0-1])[.]/) {
            candidate = $i
          }
        }
      }
      END {
        if (candidate != "") {
          print candidate
        }
      }
    ')"
    if [ -n "$ip_address" ]; then
      printf '%s' "$ip_address"
      return 0
    fi
  fi

  return 1
}

detect_timezone() {
  local tz
  tz="$(timedatectl show --property=Timezone --value 2>/dev/null)"
  if [ -n "$tz" ]; then
    printf '%s' "$tz"
    return 0
  fi
  if [ -f /etc/timezone ]; then
    tz="$(tr -d '[:space:]' < /etc/timezone 2>/dev/null)"
    if [ -n "$tz" ]; then
      printf '%s' "$tz"
      return 0
    fi
  fi
  if [ -L /etc/localtime ]; then
    tz="$(readlink /etc/localtime 2>/dev/null | sed 's|.*/zoneinfo/||')"
    if [ -n "$tz" ]; then
      printf '%s' "$tz"
      return 0
    fi
  fi
  return 1
}

enabled_value() {
  case "$1" in
    1|true|TRUE|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

start_info_page() {
  local container_name="charlotte-info-page"
  local log_dir="$repo_root/.logs/charlotte-info"
  local url="http://$info_host:$info_port"
  local page_args

  page_args=(
    --detach
    --name "$container_name"
    --restart unless-stopped
    -p "$info_port:$info_port"
    -e "HERMES_UID=$(id -u)"
    -e "HERMES_GID=$(id -g)"
    -v "$repo_root/apps/charlotte:/workspace/apps/charlotte:ro"
  )

  docker rm -f "$container_name" >/dev/null 2>&1 || true
  if ! docker run "${page_args[@]}" "$image" \
    .venv/bin/python -m http.server "$info_port" --bind 0.0.0.0 --directory apps/charlotte/static >/dev/null; then
    echo "Charlotte info page container failed to start; continuing without it." >&2
    return 0
  fi

  mkdir -p "$log_dir"
  printf '%s\n' "$url" > "$log_dir/url.txt"
  echo "Charlotte info page URL: $url"
  echo "Saved current info page URL to $log_dir/url.txt"

  # Print a scannable QR on the host terminal so the tablet camera can open the
  # URL without anyone retyping the IP. Renders inside the info-page container,
  # where qrcode is installed; silently skips on any failure so it never blocks
  # the launch.
  echo
  docker exec "$container_name" \
    .venv/bin/python scripts/qr_url.py "$url" 2>/dev/null || true
}

env_image="$(read_env_value CHARLOTTE_HERMES_IMAGE "$env_file")"
env_hermes_home="$(read_env_value CHARLOTTE_HERMES_HOME "$env_file")"
env_home_mounts="$(read_env_value CHARLOTTE_HOME_MOUNTS "$env_file")"
env_info_page="$(read_env_value CHARLOTTE_INFO_PAGE "$env_file")"
env_info_host="$(read_env_value CHARLOTTE_INFO_HOST "$env_file")"
env_info_port="$(read_env_value CHARLOTTE_INFO_PORT "$env_file")"
env_tz="$(read_env_value CHARLOTTE_TZ "$env_file")"

image="${CHARLOTTE_HERMES_IMAGE:-${env_image:-charlotte-hermes:local}}"
hermes_home="${CHARLOTTE_HERMES_HOME:-${env_hermes_home:-$HOME/.hermes-charlotte}}"
home_mounts="${CHARLOTTE_HOME_MOUNTS:-${env_home_mounts:-}}"
info_page="${CHARLOTTE_INFO_PAGE:-${env_info_page:-1}}"
info_host="${CHARLOTTE_INFO_HOST:-${env_info_host:-}}"
info_port="${CHARLOTTE_INFO_PORT:-${env_info_port:-8788}}"
tz="${CHARLOTTE_TZ:-${env_tz:-}}"
if [ -z "$tz" ]; then
  tz="$(detect_timezone || true)"
fi

mkdir -p "$hermes_home" "$hermes_home/home"
if [ ! -f "$hermes_home/config.yaml" ]; then
  install -m 600 "$script_dir/config.yaml.example" "$hermes_home/config.yaml"
fi

if [ ! -f "$repo_root/students.yaml" ]; then
  echo "Missing required students.yaml at $repo_root/students.yaml" >&2
  exit 1
fi

mkdir -p \
  "$repo_root/curricula" \
  "$repo_root/tablet-slides" \
  "$repo_root/field-trips" \
  "$repo_root/generated-images" \
  "$repo_root/.backups" \
  "$repo_root/.logs"

if enabled_value "$info_page"; then
  if [ -z "$info_host" ]; then
    info_host="$(detect_lan_ip || true)"
  fi
  if [ -z "$info_host" ]; then
    echo "CHARLOTTE_INFO_PAGE is enabled, but the current LAN IP could not be detected." >&2
    echo "Set CHARLOTTE_INFO_HOST in .env to the address the tablet should use." >&2
    echo "Continuing without the Charlotte info page." >&2
  else
    start_info_page
  fi
fi

docker_args=(--rm)
if [ -t 0 ] && [ -t 1 ]; then
  docker_args+=(-it)
fi

if [ -f "$env_file" ]; then
  docker_args+=(--env-file "$env_file")
fi

docker_args+=(
  -e "HERMES_UID=$(id -u)"
  -e "HERMES_GID=$(id -g)"
)

if [ -n "$tz" ]; then
  docker_args+=(-e "TZ=$tz")
fi

docker_args+=(
  -v "$hermes_home:/opt/data"
  -v "$repo_root/students.yaml:/workspace/students.yaml:ro"
  -v "$repo_root/curricula:/workspace/curricula"
  -v "$repo_root/tablet-slides:/workspace/tablet-slides"
  -v "$repo_root/field-trips:/workspace/field-trips"
  -v "$repo_root/generated-images:/workspace/generated-images"
  -v "$repo_root/.backups:/workspace/.backups"
  -v "$repo_root/.logs:/workspace/.logs"
)

if [ -f "$repo_root/runtime.yaml" ]; then
  docker_args+=(-v "$repo_root/runtime.yaml:/workspace/runtime.yaml:ro")
fi

if [ -n "$home_mounts" ]; then
  IFS=':' read -r -a home_mount_entries <<< "$home_mounts"
  for home_mount in "${home_mount_entries[@]}"; do
    if [ -z "$home_mount" ]; then
      continue
    fi
    case "$home_mount" in
      /*)
        echo "CHARLOTTE_HOME_MOUNTS entries must be relative to \$HOME, got: $home_mount" >&2
        exit 1
        ;;
      ..|../*|*/..|*/../*)
        echo "CHARLOTTE_HOME_MOUNTS entries cannot contain '..', got: $home_mount" >&2
        exit 1
        ;;
    esac

    host_mount="$HOME/$home_mount"
    container_mount="/opt/data/$home_mount"
    container_home_mount="/opt/data/home/$home_mount"
    if [ ! -d "$host_mount" ]; then
      echo "Configured CHARLOTTE_HOME_MOUNTS path does not exist or is not a directory: $host_mount" >&2
      exit 1
    fi
    docker_args+=(
      -v "$host_mount:$container_mount"
      -v "$host_mount:$container_home_mount"
    )
  done
fi

if [ "$#" -eq 0 ]; then
  set -- chat
fi

exec docker run "${docker_args[@]}" "$image" "$@"
