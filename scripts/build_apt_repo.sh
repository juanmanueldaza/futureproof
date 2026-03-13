#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: scripts/build_apt_repo.sh path/to/package.deb"
  exit 1
fi

deb_path="$1"
if [[ ! -f "${deb_path}" ]]; then
  echo "Deb package not found: ${deb_path}"
  exit 1
fi

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
repo_dir="${REPO_DIR:-${root_dir}/dist/apt}"
dist_name="${APT_DIST:-stable}"
component="${APT_COMPONENT:-main}"
arch="amd64"

rm -rf "${repo_dir}"
mkdir -p "${repo_dir}/pool/${component}/f/fu7ur3pr00f"
mkdir -p "${repo_dir}/dists/${dist_name}/${component}/binary-${arch}"

cat > "${repo_dir}/index.html" <<'EOF'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>fu7ur3pr00f apt repo</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 2rem; }
      code { background: #f4f4f4; padding: 0.1rem 0.25rem; border-radius: 4px; }
      pre { background: #f4f4f4; padding: 0.75rem; border-radius: 6px; overflow-x: auto; }
    </style>
  </head>
  <body>
    <h1>fu7ur3pr00f apt repo</h1>
    <p>This GitHub Pages site hosts the apt repository for fu7ur3pr00f.</p>
    <pre><code>curl -fsSL https://juanmanueldaza.github.io/fu7ur3pr00f/fu7ur3pr00f-archive-keyring.gpg | \
  sudo tee /usr/share/keyrings/fu7ur3pr00f-archive-keyring.gpg >/dev/null

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/fu7ur3pr00f-archive-keyring.gpg] \
https://juanmanueldaza.github.io/fu7ur3pr00f stable main" | \
  sudo tee /etc/apt/sources.list.d/fu7ur3pr00f.list >/dev/null</code></pre>
    <p>Repository metadata lives under <code>dists/stable</code>.</p>
  </body>
</html>
EOF

touch "${repo_dir}/.nojekyll"

cp "${deb_path}" "${repo_dir}/pool/${component}/f/fu7ur3pr00f/"

pushd "${repo_dir}" >/dev/null
dpkg-scanpackages --arch "${arch}" "pool/${component}" > "dists/${dist_name}/${component}/binary-${arch}/Packages"
gzip -kf "dists/${dist_name}/${component}/binary-${arch}/Packages"
apt-ftparchive \
  -o "APT::FTPArchive::Release::Origin=fu7ur3pr00f" \
  -o "APT::FTPArchive::Release::Label=fu7ur3pr00f" \
  -o "APT::FTPArchive::Release::Suite=${dist_name}" \
  -o "APT::FTPArchive::Release::Codename=${dist_name}" \
  -o "APT::FTPArchive::Release::Architectures=${arch}" \
  -o "APT::FTPArchive::Release::Components=${component}" \
  release "dists/${dist_name}" > "dists/${dist_name}/Release"
popd >/dev/null

if [[ -z "${APT_GPG_PRIVATE_KEY:-}" || -z "${APT_GPG_PASSPHRASE:-}" ]]; then
  echo "APT_GPG_PRIVATE_KEY and APT_GPG_PASSPHRASE are required for signing."
  exit 1
fi

gpg_home="${repo_dir}/.gnupg"
mkdir -p "${gpg_home}"
chmod 700 "${gpg_home}"
export GNUPGHOME="${gpg_home}"

echo "${APT_GPG_PRIVATE_KEY}" | gpg --batch --import >/dev/null

key_id="${APT_GPG_KEY_ID:-}"
if [[ -z "${key_id}" ]]; then
  key_id="$(gpg --list-secret-keys --with-colons | awk -F: '/^sec/ {print $5; exit}')"
fi
if [[ -z "${key_id}" ]]; then
  echo "Failed to detect GPG key id."
  exit 1
fi

gpg --batch --pinentry-mode loopback --passphrase "${APT_GPG_PASSPHRASE}" \
  --default-key "${key_id}" --clearsign \
  -o "${repo_dir}/dists/${dist_name}/InRelease" \
  "${repo_dir}/dists/${dist_name}/Release"

gpg --batch --pinentry-mode loopback --passphrase "${APT_GPG_PASSPHRASE}" \
  --default-key "${key_id}" --detach-sign \
  -o "${repo_dir}/dists/${dist_name}/Release.gpg" \
  "${repo_dir}/dists/${dist_name}/Release"

gpg --batch --yes --armor --export "${key_id}" | gpg --batch --yes --dearmor \
  -o "${repo_dir}/fu7ur3pr00f-archive-keyring.gpg"

echo "Built apt repo at ${repo_dir}"
