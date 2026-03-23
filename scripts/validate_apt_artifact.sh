#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/validate_apt_artifact.sh path/to/package.deb

Builds a temporary signed apt repository from the provided package and validates
install/reinstall/remove flows inside disposable Debian-family containers.

Environment:
  APT_VALIDATION_IMAGES   Space-separated container images
                          (default: "ubuntu:24.04 debian:12")
USAGE
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for apt artifact validation." >&2
  exit 1
fi

deb_path="$1"
if [[ ! -f "${deb_path}" ]]; then
  echo "Deb package not found: ${deb_path}" >&2
  exit 1
fi

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
images_string="${APT_VALIDATION_IMAGES:-ubuntu:24.04 debian:12}"
read -r -a validation_images <<<"${images_string}"

temp_root="$(mktemp -d)"
repo_dir="${temp_root}/repo"
server_log="${temp_root}/http-server.log"
server_pid=""

cleanup() {
  if [[ -n "${server_pid}" ]] && kill -0 "${server_pid}" >/dev/null 2>&1; then
    kill "${server_pid}" >/dev/null 2>&1 || true
    wait "${server_pid}" >/dev/null 2>&1 || true
  fi
  rm -rf "${temp_root}"
}
trap cleanup EXIT

server_port="$(
  python3 - <<'PY'
import socket

sock = socket.socket()
sock.bind(("127.0.0.1", 0))
print(sock.getsockname()[1])
sock.close()
PY
)"

APT_GPG_ALLOW_EPHEMERAL=1 REPO_DIR="${repo_dir}" \
  "${root_dir}/scripts/build_apt_repo.sh" "${deb_path}"

python3 -m http.server "${server_port}" --bind 127.0.0.1 --directory "${repo_dir}" \
  >"${server_log}" 2>&1 &
server_pid="$!"
sleep 1

if ! kill -0 "${server_pid}" >/dev/null 2>&1; then
  echo "Failed to start local apt repo server. Log follows:" >&2
  cat "${server_log}" >&2
  exit 1
fi

for image in "${validation_images[@]}"; do
  echo "Validating apt install flow in ${image}"
  docker run --rm --network host \
    -e DEBIAN_FRONTEND=noninteractive \
    -v "${repo_dir}:/repo:ro" \
    "${image}" \
    bash -lc "
      set -euo pipefail
      apt-get update
      apt-get install -y ca-certificates gnupg
      install -Dm644 /repo/fu7ur3pr00f-archive-keyring.gpg \
        /usr/share/keyrings/fu7ur3pr00f-archive-keyring.gpg
      cat > /etc/apt/sources.list.d/fu7ur3pr00f.list <<'EOF'
deb [arch=amd64 signed-by=/usr/share/keyrings/fu7ur3pr00f-archive-keyring.gpg] http://127.0.0.1:${server_port} stable main
EOF
      apt-get update
      apt-get install -y fu7ur3pr00f
      fu7ur3pr00f --version
      apt-get install --reinstall -y fu7ur3pr00f
      fu7ur3pr00f --version
      apt-get remove -y fu7ur3pr00f
      apt-get purge -y fu7ur3pr00f
      if command -v fu7ur3pr00f >/dev/null 2>&1; then
        echo 'fu7ur3pr00f still present after purge' >&2
        exit 1
      fi
    "
done

echo "Apt artifact validation passed."
