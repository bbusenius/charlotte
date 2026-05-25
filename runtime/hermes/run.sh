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

env_image="$(read_env_value CHARLOTTE_HERMES_IMAGE "$env_file")"
env_hermes_home="$(read_env_value CHARLOTTE_HERMES_HOME "$env_file")"
env_home_mounts="$(read_env_value CHARLOTTE_HOME_MOUNTS "$env_file")"

image="${CHARLOTTE_HERMES_IMAGE:-${env_image:-charlotte-hermes:local}}"
hermes_home="${CHARLOTTE_HERMES_HOME:-${env_hermes_home:-$HOME/.hermes-charlotte}}"
home_mounts="${CHARLOTTE_HOME_MOUNTS:-${env_home_mounts:-}}"

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
