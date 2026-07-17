#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
NODE_MAJOR="${NODE_MAJOR:-24}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BOOTSTRAP_ONLY="${BOOTSTRAP_ONLY:-0}"
SKIP_ENV_CHECK="${SKIP_ENV_CHECK:-0}"

RUNTIME_BASE_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}/theNanGuos"
UV_RUNTIME_DIR="$RUNTIME_BASE_DIR/uv"
NODE_RUNTIME_DIR="$RUNTIME_BASE_DIR/node"

BACKEND_PID=""
FRONTEND_PID=""
TEMP_DIR=""

log() {
  printf '[theNanGuos] %s\n' "$*"
}

warn() {
  printf '[theNanGuos] 警告: %s\n' "$*" >&2
}

die() {
  printf '[theNanGuos] 错误: %s\n' "$*" >&2
  exit 1
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

run_as_root() {
  if (( EUID == 0 )); then
    "$@"
  elif has_command sudo; then
    sudo "$@"
  else
    die "安装系统依赖需要 root 权限；请使用 root 账户运行，或先安装 sudo。"
  fi
}

detect_package_manager() {
  local package_manager
  for package_manager in apt-get dnf yum pacman zypper apk; do
    if has_command "$package_manager"; then
      printf '%s\n' "$package_manager"
      return 0
    fi
  done
  return 1
}

install_ffmpeg_with_rpm_manager() {
  local package_manager="$1"

  if run_as_root "$package_manager" install -y ffmpeg-free; then
    return 0
  fi
  if run_as_root "$package_manager" install -y ffmpeg; then
    return 0
  fi
  die "$package_manager 的已启用软件源不提供 ffmpeg；请为当前发行版启用包含 ffmpeg 的官方或可信软件源后重试。"
}

install_system_dependencies() {
  local package_manager

  if (has_command curl || has_command wget) \
    && has_command tar \
    && has_command xz \
    && has_command sha256sum \
    && has_command ffmpeg \
    && has_command ffprobe; then
    return 0
  fi

  package_manager="$(detect_package_manager)" \
    || die "无法识别包管理器。支持 apt-get、dnf、yum、pacman、zypper 和 apk。"

  log "使用 $package_manager 安装下载、解压、校验和音频工具..."
  case "$package_manager" in
    apt-get)
      run_as_root apt-get update
      run_as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y \
        ca-certificates curl tar xz-utils coreutils ffmpeg
      ;;
    dnf)
      run_as_root dnf install -y ca-certificates curl tar xz coreutils
      if ! has_command ffmpeg || ! has_command ffprobe; then
        install_ffmpeg_with_rpm_manager dnf
      fi
      ;;
    yum)
      run_as_root yum install -y ca-certificates curl tar xz coreutils
      if ! has_command ffmpeg || ! has_command ffprobe; then
        install_ffmpeg_with_rpm_manager yum
      fi
      ;;
    pacman)
      run_as_root pacman -Sy --needed --noconfirm \
        ca-certificates curl tar xz coreutils ffmpeg
      ;;
    zypper)
      run_as_root zypper --non-interactive refresh
      run_as_root zypper --non-interactive install \
        ca-certificates curl tar xz coreutils ffmpeg
      ;;
    apk)
      run_as_root apk update
      run_as_root apk add ca-certificates curl tar xz coreutils ffmpeg
      ;;
  esac

  (has_command curl || has_command wget) \
    || die "系统依赖安装后仍找不到 curl 或 wget。"
  has_command tar || die "系统依赖安装后仍找不到 tar。"
  has_command xz || die "系统依赖安装后仍找不到 xz。"
  has_command sha256sum || die "系统依赖安装后仍找不到 sha256sum。"
  has_command ffmpeg || die "系统依赖安装后仍找不到 ffmpeg。"
  has_command ffprobe || die "系统依赖安装后仍找不到 ffprobe。"
}

download_file() {
  local url="$1"
  local destination="$2"

  if has_command curl; then
    curl -fL --retry 3 --connect-timeout 20 --output "$destination" "$url"
  elif has_command wget; then
    wget --tries=3 --timeout=20 -O "$destination" "$url"
  else
    die "下载 $url 需要 curl 或 wget。"
  fi
}

install_uv() {
  if [[ -x "$UV_RUNTIME_DIR/uv" ]]; then
    export PATH="$UV_RUNTIME_DIR:$PATH"
  fi

  if has_command uv; then
    log "使用现有 uv: $(uv --version)"
    return 0
  fi

  mkdir -p "$UV_RUNTIME_DIR"
  log "安装 uv..."
  if has_command curl; then
    curl -LsSf https://astral.sh/uv/install.sh \
      | env UV_UNMANAGED_INSTALL="$UV_RUNTIME_DIR" sh
  elif has_command wget; then
    wget -qO- https://astral.sh/uv/install.sh \
      | env UV_UNMANAGED_INSTALL="$UV_RUNTIME_DIR" sh
  else
    die "安装 uv 需要 curl 或 wget。"
  fi

  export PATH="$UV_RUNTIME_DIR:$PATH"
  has_command uv || die "uv 安装完成，但在 $UV_RUNTIME_DIR 中找不到可执行文件。"
  log "uv 安装完成: $(uv --version)"
}

node_version_supported() {
  local version="${1#v}"
  local major minor patch

  IFS=. read -r major minor patch <<< "$version"
  [[ "$major" =~ ^[0-9]+$ && "$minor" =~ ^[0-9]+$ ]] || return 1

  if (( major == 20 && minor >= 19 )); then
    return 0
  fi
  if (( major == 22 && minor >= 12 )); then
    return 0
  fi
  (( major > 22 ))
}

is_musl_linux() {
  local ldd_output=""

  [[ -f /etc/alpine-release ]] && return 0
  if has_command ldd; then
    ldd_output="$(ldd --version 2>&1 || true)"
  fi
  [[ "$ldd_output" == *musl* ]]
}

node_download_arch() {
  local machine
  machine="$(uname -m)"

  case "$machine" in
    x86_64 | amd64)
      printf 'x64\n'
      ;;
    aarch64 | arm64)
      printf 'arm64\n'
      ;;
    ppc64le)
      printf 'ppc64le\n'
      ;;
    s390x)
      printf 's390x\n'
      ;;
    *)
      die "Node.js 官方 Linux 二进制不支持当前架构: $machine"
      ;;
  esac
}

ensure_temp_dir() {
  if [[ -z "$TEMP_DIR" ]]; then
    TEMP_DIR="$(mktemp -d /tmp/theNanGuos.XXXXXX)"
  fi
}

cleanup_temp_dir() {
  if [[ -n "$TEMP_DIR" && "$TEMP_DIR" == /tmp/theNanGuos.* && -d "$TEMP_DIR" ]]; then
    rm -rf -- "$TEMP_DIR"
  fi
  TEMP_DIR=""
}

activate_node_install() {
  local install_dir="$1"
  local current_link="$NODE_RUNTIME_DIR/current"

  if [[ -e "$current_link" && ! -L "$current_link" ]]; then
    die "Node.js 运行时路径 $current_link 已存在且不是符号链接，请移走该路径后重试。"
  fi

  ln -sfn "$install_dir" "$current_link"
  export PATH="$current_link/bin:$PATH"
}

install_node_from_official_binary() {
  local node_arch shasums_file archive_name expected_checksum
  local archive_file actual_checksum version install_dir

  node_arch="$(node_download_arch)"
  ensure_temp_dir
  shasums_file="$TEMP_DIR/SHASUMS256.txt"

  log "查询 Node.js ${NODE_MAJOR}.x LTS 官方版本..."
  download_file \
    "https://nodejs.org/dist/latest-v${NODE_MAJOR}.x/SHASUMS256.txt" \
    "$shasums_file"

  archive_name=""
  expected_checksum=""
  while read -r checksum filename; do
    case "$filename" in
      node-v*-linux-"$node_arch".tar.xz)
        expected_checksum="$checksum"
        archive_name="$filename"
        break
        ;;
    esac
  done < "$shasums_file"

  [[ -n "$archive_name" && -n "$expected_checksum" ]] \
    || die "Node.js ${NODE_MAJOR}.x 没有适用于 linux-$node_arch 的官方二进制。"

  version="${archive_name#node-}"
  version="${version%-linux-"$node_arch".tar.xz}"
  install_dir="$NODE_RUNTIME_DIR/$version-linux-$node_arch"
  if [[ -x "$install_dir/bin/node" && -x "$install_dir/bin/npm" ]]; then
    activate_node_install "$install_dir"
    return 0
  fi

  archive_file="$TEMP_DIR/$archive_name"
  download_file \
    "https://nodejs.org/dist/latest-v${NODE_MAJOR}.x/$archive_name" \
    "$archive_file"

  actual_checksum="$(sha256sum "$archive_file")"
  actual_checksum="${actual_checksum%% *}"
  [[ "$actual_checksum" == "$expected_checksum" ]] \
    || die "Node.js 下载文件 SHA-256 校验失败。"

  mkdir -p "$install_dir"
  tar -xJf "$archive_file" -C "$install_dir" --strip-components=1

  activate_node_install "$install_dir"
  has_command node && has_command npm \
    || die "Node.js 解压完成，但找不到 node 或 npm。"
}

install_node_on_musl() {
  local package_manager
  package_manager="$(detect_package_manager)" \
    || die "musl Linux 需要通过发行版包管理器安装 Node.js。"

  case "$package_manager" in
    apk)
      run_as_root apk update
      run_as_root apk add nodejs npm
      ;;
    *)
      die "当前 musl Linux 暂不支持自动安装 Node.js；请安装 Node.js 22.12+ 或 24 LTS。"
      ;;
  esac
}

install_node() {
  local existing_version=""

  if [[ -x "$NODE_RUNTIME_DIR/current/bin/node" \
    && -x "$NODE_RUNTIME_DIR/current/bin/npm" ]]; then
    export PATH="$NODE_RUNTIME_DIR/current/bin:$PATH"
  fi

  if has_command node && has_command npm; then
    existing_version="$(node --version)"
    if node_version_supported "$existing_version"; then
      log "使用现有 Node.js: $existing_version"
      return 0
    fi
    warn "现有 Node.js $existing_version 不满足前端要求，将安装 Node.js ${NODE_MAJOR}.x。"
  fi

  if is_musl_linux; then
    install_node_on_musl
  else
    install_node_from_official_binary
  fi

  existing_version="$(node --version)"
  node_version_supported "$existing_version" \
    || die "Node.js $existing_version 不满足要求：需要 20.19+、22.12+ 或更高版本。"
  log "Node.js 安装完成: $existing_version，npm $(npm --version)"
}

env_key_is_configured() {
  local target_key="$1"
  local configured_value="${!target_key-}"
  local line

  if [[ -z "$configured_value" && -f "$ROOT_DIR/.env" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
      line="${line%$'\r'}"
      case "$line" in
        "$target_key="*)
          configured_value="${line#*=}"
          break
          ;;
      esac
    done < "$ROOT_DIR/.env"
  fi

  configured_value="${configured_value#\"}"
  configured_value="${configured_value%\"}"
  configured_value="${configured_value#\'}"
  configured_value="${configured_value%\'}"

  case "$configured_value" in
    "" | your-* | *your-*-endpoint* | changeme | CHANGE_ME)
      return 1
      ;;
  esac
  return 0
}

ensure_environment_config() {
  local missing_keys=()

  [[ "$SKIP_ENV_CHECK" == "1" ]] && return 0

  if [[ ! -f "$ROOT_DIR/.env" ]] \
    && [[ -z "${OPENAI_API_KEY:-}" || -z "${OPENAI_BASE_URL:-}" ]]; then
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    die "已根据 .env.example 创建 .env。请填写 OPENAI_API_KEY 和 OPENAI_BASE_URL，然后重新运行 ./start.sh。"
  fi

  env_key_is_configured OPENAI_API_KEY || missing_keys+=("OPENAI_API_KEY")
  env_key_is_configured OPENAI_BASE_URL || missing_keys+=("OPENAI_BASE_URL")
  if (( ${#missing_keys[@]} > 0 )); then
    die ".env 或当前环境中缺少有效配置: ${missing_keys[*]}"
  fi
}

sync_project_dependencies() {
  log "安装 Python $PYTHON_VERSION 并同步后端依赖..."
  uv python install "$PYTHON_VERSION"
  uv sync --locked --python "$PYTHON_VERSION"

  if [[ ! -f "$FRONTEND_DIR/package-lock.json" ]]; then
    die "缺少 frontend/package-lock.json，无法执行确定性前端安装。"
  fi

  if [[ ! -d "$FRONTEND_DIR/node_modules" \
    || "$FRONTEND_DIR/package-lock.json" -nt "$FRONTEND_DIR/node_modules/.package-lock.json" \
    || "$FRONTEND_DIR/package.json" -nt "$FRONTEND_DIR/node_modules/.package-lock.json" ]]; then
    log "根据 package-lock.json 安装前端依赖..."
    npm --prefix "$FRONTEND_DIR" ci
  else
    log "前端依赖已是最新状态。"
  fi

  mkdir -p "$ROOT_DIR/data" "$ROOT_DIR/works" "$ROOT_DIR/_logs"
}

stop_process() {
  local process_id="$1"
  if [[ -n "$process_id" ]] && kill -0 "$process_id" 2>/dev/null; then
    kill "$process_id" 2>/dev/null || true
    wait "$process_id" 2>/dev/null || true
  fi
}

cleanup() {
  local exit_status=$?
  trap - EXIT INT TERM
  stop_process "$FRONTEND_PID"
  stop_process "$BACKEND_PID"
  cleanup_temp_dir
  exit "$exit_status"
}

start_services() {
  local service_status

  log "启动后端: http://$BACKEND_HOST:$BACKEND_PORT"
  uv run uvicorn app.api:app --reload \
    --host "$BACKEND_HOST" \
    --port "$BACKEND_PORT" &
  BACKEND_PID="$!"

  log "启动前端: http://$FRONTEND_HOST:$FRONTEND_PORT"
  VITE_API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-http://$BACKEND_HOST:$BACKEND_PORT}" \
    npm --prefix "$FRONTEND_DIR" run dev -- \
    --host "$FRONTEND_HOST" \
    --port "$FRONTEND_PORT" &
  FRONTEND_PID="$!"

  log "开发服务已启动。按 Ctrl+C 停止。"
  set +e
  wait -n
  service_status=$?
  set -e

  if (( service_status != 0 )); then
    die "后端或前端异常退出，状态码为 $service_status。"
  fi
}

main() {
  [[ "$(uname -s)" == "Linux" ]] || die "start.sh 仅支持 Linux。"
  [[ -f "$ROOT_DIR/pyproject.toml" ]] || die "找不到项目根目录中的 pyproject.toml。"
  [[ -f "$FRONTEND_DIR/package.json" ]] || die "找不到 frontend/package.json。"
  [[ -f "$ROOT_DIR/.env.example" ]] || die "找不到项目根目录中的 .env.example。"

  trap cleanup EXIT INT TERM
  install_system_dependencies
  install_uv
  install_node
  cleanup_temp_dir
  sync_project_dependencies

  if [[ "$BOOTSTRAP_ONLY" == "1" ]]; then
    log "系统与项目依赖准备完成。"
    return 0
  fi

  ensure_environment_config
  cd "$ROOT_DIR"
  start_services
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
