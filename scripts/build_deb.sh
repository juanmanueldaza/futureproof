#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dist_dir="${DIST_DIR:-${root_dir}/dist/deb}"
work_dir="${dist_dir}/work"
pkg_dir="${dist_dir}/pkg"
arch="amd64"
trap 'echo "Build failed at line ${LINENO}." >&2' ERR

version="${VERSION:-}"
if [[ -z "${version}" ]]; then
  version="$(python3 - <<'PY'
from pathlib import Path
import tomllib

pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
data = tomllib.loads(pyproject)
print(data["project"]["version"])
PY
)"
fi

mkdir -p "${dist_dir}"
rm -rf "${work_dir}" "${pkg_dir}"
mkdir -p "${work_dir}" "${pkg_dir}"

deb_root="${pkg_dir}/fu7ur3pr00f_${version}_${arch}"
mkdir -p "${deb_root}/DEBIAN" "${deb_root}/usr/bin" "${deb_root}/opt/fu7ur3pr00f" \
  "${deb_root}/usr/share/doc/fu7ur3pr00f"

export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-120}"
export PIP_RETRIES="${PIP_RETRIES:-5}"

build_venv="${work_dir}/build-venv"
echo "Setting up build virtualenv at ${build_venv}"
if ! python3 -m venv "${build_venv}" >/dev/null 2>&1; then
  echo "Failed to create build virtualenv. Ensure python3-venv is installed." >&2
  exit 1
fi

pip_log="${work_dir}/pip-install.log"
echo "Installing build tools"
if ! "${build_venv}/bin/pip" install --upgrade pip build hatchling getpybs >"${pip_log}" 2>&1; then
  echo "pip install failed. Last 200 lines:"
  tail -n 200 "${pip_log}"
  exit 1
fi

build_log="${work_dir}/build.log"
echo "Building wheel"
if ! "${build_venv}/bin/python" -m build --wheel --no-isolation -v >"${build_log}" 2>&1; then
  echo "Wheel build failed. Last 200 lines:"
  tail -n 200 "${build_log}"
  exit 1
fi

wheel_path="$(ls -1 "${root_dir}/dist"/fu7ur3pr00f-"${version}"-py3-none-any.whl | head -n1)"
if [[ ! -f "${wheel_path}" ]]; then
  echo "Wheel not found for version ${version}"
  exit 1
fi

pybs_dir="${work_dir}/python-build-standalone"
mkdir -p "${pybs_dir}"
pybs_log="${work_dir}/getpybs.log"
echo "Downloading python-build-standalone"
if ! "${build_venv}/bin/getpybs" \
  --python-version 3.13 \
  --architecture x86_64-unknown-linux-gnu \
  --content-type install_only_stripped \
  --dest "${pybs_dir}" >"${pybs_log}" 2>&1; then
  echo "getpybs failed. Last 200 lines:"
  tail -n 200 "${pybs_log}"
  exit 1
fi

pybs_tarball="$(find "${pybs_dir}" -maxdepth 2 -type f -name "python-3.13*install_only_stripped*.tar.*" | head -n1)"
if [[ -z "${pybs_tarball}" ]]; then
  pybs_tarball="$(find "${pybs_dir}" -maxdepth 3 -type f -name "*.tar.*" | head -n1)"
fi
if [[ -z "${pybs_tarball}" ]]; then
  echo "Python build tarball not found in ${pybs_dir}"
  exit 1
fi

python_dir="${work_dir}/python"
mkdir -p "${python_dir}"
case "${pybs_tarball}" in
  *.tar.zst)
    tar --use-compress-program=unzstd -xf "${pybs_tarball}" -C "${python_dir}"
    ;;
  *.tar.gz|*.tgz)
    tar -xzf "${pybs_tarball}" -C "${python_dir}"
    ;;
  *.tar.xz)
    tar -xJf "${pybs_tarball}" -C "${python_dir}"
    ;;
  *)
    tar -xf "${pybs_tarball}" -C "${python_dir}"
    ;;
esac

python_bin="$(find "${python_dir}" -type f -regex ".*/bin/python\\(3\\(\\.[0-9]+\\)?\\)?$" | head -n1)"
if [[ -z "${python_bin}" ]]; then
  echo "Python binary not found in ${python_dir}"
  find "${python_dir}" -maxdepth 3 -type f -path "*/bin/*" | head -n 50
  exit 1
fi

venv_dir="${deb_root}/opt/fu7ur3pr00f/venv"
"${python_bin}" -m venv "${venv_dir}"
"${venv_dir}/bin/pip" install --upgrade pip >/dev/null

wheel_dir="${deb_root}/opt/fu7ur3pr00f/wheels"
mkdir -p "${wheel_dir}"
cp "${wheel_path}" "${wheel_dir}/"

cat > "${deb_root}/usr/bin/fu7ur3pr00f" <<'EOF'
#!/usr/bin/env bash
exec /opt/fu7ur3pr00f/venv/bin/fu7ur3pr00f "$@"
EOF
chmod 755 "${deb_root}/usr/bin/fu7ur3pr00f"

github_api="https://api.github.com/repos/github/github-mcp-server/releases/latest"
github_headers=()
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  github_headers=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
fi
mcp_url="$(curl -sSL "${github_headers[@]}" "${github_api}" | jq -r '.assets[] | select(.name | test("linux.*(amd64|x86_64)"; "i")) | .browser_download_url' | head -n1)"
if [[ -z "${mcp_url}" ]]; then
  echo "Failed to find github-mcp-server linux amd64 asset"
  exit 1
fi

mcp_archive="${work_dir}/github-mcp-server-asset"
if ! curl -fSL "${mcp_url}" -o "${mcp_archive}"; then
  echo "Failed to download github-mcp-server asset"
  exit 1
fi

mcp_extract_dir="${work_dir}/github-mcp-server"
mkdir -p "${mcp_extract_dir}"
case "${mcp_url}" in
  *.tar.gz|*.tgz)
    tar -xzf "${mcp_archive}" -C "${mcp_extract_dir}"
    ;;
  *.tar.xz)
    tar -xJf "${mcp_archive}" -C "${mcp_extract_dir}"
    ;;
  *.zip)
    unzip -q "${mcp_archive}" -d "${mcp_extract_dir}"
    ;;
  *)
    tar -xf "${mcp_archive}" -C "${mcp_extract_dir}"
    ;;
esac

mcp_bin="$(find "${mcp_extract_dir}" -type f -name "github-mcp-server" | head -n1)"
if [[ -z "${mcp_bin}" ]]; then
  echo "github-mcp-server binary not found in archive"
  exit 1
fi
install -m 755 "${mcp_bin}" "${deb_root}/usr/bin/github-mcp-server"

cp "${root_dir}/README.md" "${deb_root}/usr/share/doc/fu7ur3pr00f/README.md"
cp "${root_dir}/LICENSE" "${deb_root}/usr/share/doc/fu7ur3pr00f/LICENSE"

cat > "${deb_root}/DEBIAN/control" <<EOF
Package: fu7ur3pr00f
Version: ${version}
Section: utils
Priority: optional
Architecture: ${arch}
Maintainer: Juan Manuel Daza <juanmanueldaza@users.noreply.github.com>
Depends: libc6, libstdc++6, libpango-1.0-0, libpangoft2-1.0-0, libcairo2, libfontconfig1, libgdk-pixbuf-2.0-0, poppler-utils, glab
Description: FutureProof career intelligence agent
 FutureProof is a local-first career intelligence agent that gathers
 professional data, analyzes career trajectories, and generates CVs.
EOF

cat > "${deb_root}/DEBIAN/postinst" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

venv="/opt/fu7ur3pr00f/venv"
wheel="$(ls /opt/fu7ur3pr00f/wheels/fu7ur3pr00f-*.whl | head -n1)"

if "${venv}/bin/python" - <<'PY'
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("fu7ur3pr00f") else 1)
PY
then
  exit 0
fi

"${venv}/bin/pip" install --upgrade pip >/dev/null
"${venv}/bin/pip" install "${wheel}"
EOF
chmod 755 "${deb_root}/DEBIAN/postinst"

dpkg-deb --build "${deb_root}" "${dist_dir}/fu7ur3pr00f_${version}_${arch}.deb" >/dev/null
echo "Built ${dist_dir}/fu7ur3pr00f_${version}_${arch}.deb"
