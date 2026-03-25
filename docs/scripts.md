# Scripts Reference

All scripts are in `scripts/`. Most are bash and executable.

---

## Quick Reference

| Script | Purpose | Type |
|--------|---------|------|
| [`setup.sh`](#setupsh--one-time-configuration) | Azure/config setup | User-facing |
| [`fresh_install_check.sh`](#fresh_install_checksh--validate-pipx-installation) | Validate pipx install | User-facing |
| [`clean_dev_artifacts.sh`](#clean_dev_artifactssh--clean-build-artifacts) | Clean build artifacts | Dev |
| [`run_tests.py`](#run_testspy--test-runner) | Run test suite | Dev |
| [`setup_precommit.sh`](#setup_precommitsh--install-pre-commit-hooks) | Install pre-commit hooks | Dev |
| [`build_deb.sh`](#build_debsh--build-deb-package) | Build .deb package | CI/Build |
| [`build_apt_repo.sh`](#build_apt_reposh--build-apt-repository) | Build apt repository | CI/Build |
| [`validate_apt_artifact.sh`](#validate_apt_artifactsh--test-deb-in-containers) | Test .deb in Docker | CI/Test |
| [`run_vagrant_apt_smoke.sh`](#run_vagrant_apt_smokesh--test-apt-packages-in-vms) | Test in Vagrant VMs | CI/Test |
| [`vagrant_dev_setup.sh`](#vagrant_dev_setupsh--development-vm-manager) | Dev VM manager | Dev |
| [`vagrant_apt_smoke.sh`](#vagrant_apt_smokesh--vagrant-provision-script) | Vagrant provision script | Internal |
| [`vagrant_test_multi.sh`](#vagrant_test_multish--multi-agent-vagrant-test) | Multi-agent Vagrant test | CI/Test |

---

## User-Facing Scripts

### `setup.sh` — One-time configuration

Configures Azure OpenAI automatically and copies career data.

```bash
./scripts/setup.sh
```

**What it does:**
1. Checks Azure CLI login (runs device code flow if needed)
2. Finds Azure OpenAI resource in your subscription
3. Extracts API key and endpoint
4. Lists deployments and picks appropriate models
5. Writes `~/.fu7ur3pr00f/.env` with secure permissions (0600)
6. Copies career data from `data/raw/` to `~/.fu7ur3pr00f/data/raw/`
7. Tests the connection

**Requirements:**
- Azure CLI installed
- Logged in to Azure
- Azure OpenAI resource with deployments

---

### `fresh_install_check.sh` — Validate pipx installation

Tests a clean pipx install in an isolated environment.

```bash
./scripts/fresh_install_check.sh --source local --config-from .env
./scripts/fresh_install_check.sh --source pypi --config-from .env
```

**Options:**
| Option | Description |
|--------|-------------|
| `--source local` | Install from current directory (default) |
| `--source pypi` | Install from PyPI |
| `--config-from PATH` | Copy `.env` file to isolated HOME |
| `--keep` | Don't delete temp directory after test |

**What it does:**
1. Creates temp HOME directory
2. Installs fu7ur3pr00f via pipx
3. Copies glab config if present
4. Runs diagnostics module
5. Cleans up (unless `--keep`)

---

## Development Scripts

### `run_tests.py` — Test runner

Python script to run the test suite.

```bash
python scripts/run_tests.py
```

Equivalent to `pytest tests/ -q` but with additional output formatting.

---

### `setup_precommit.sh` — Install pre-commit hooks

Installs pre-commit and sets up git hooks.

```bash
./scripts/setup_precommit.sh
```

**What it does:**
1. Installs `pre-commit` via pip
2. Runs `pre-commit install` to register git hooks
3. Optionally runs `pre-commit run --all-files` to validate existing code

The pre-commit configuration in `.pre-commit-config.yaml` runs ruff lint and format checks on every commit.

---

### `clean_dev_artifacts.sh` — Clean build artifacts

Removes Python cache, build directories, and transient data.

```bash
./scripts/clean_dev_artifacts.sh
```

**What it removes:**
- `dist/`, `build/`
- `__pycache__/` directories
- `*.pyc` files
- `data/cache/` (market data cache)

---

## Build Scripts

### `build_deb.sh` — Build .deb package

Creates a self-contained Debian package with bundled Python runtime.

```bash
./scripts/build_deb.sh
```

**Environment variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `VERSION` | From `pyproject.toml` | Package version |
| `DIST_DIR` | `dist/deb` | Output directory |

**What it does:**
1. Creates build virtualenv
2. Builds wheel with hatchling
3. Downloads python-build-standalone (Python 3.13)
4. Installs wheel into bundled Python
5. Bundles github-mcp-server
6. Prunes unnecessary files (tests, pip, tcl/tk)
7. Creates wrapper script at `/usr/bin/fu7ur3pr00f`
8. Builds .deb with dpkg-deb

**Output:** `dist/deb/fu7ur3pr00f_<version>_amd64.deb`

**Requirements:** Python 3.13, `python3-venv`, `python3.13-venv`, `dpkg-deb`, `jq`, `curl`

---

### `build_apt_repo.sh` — Build apt repository

Creates a signed apt repository from a .deb package.

```bash
./scripts/build_apt_repo.sh path/to/package.deb
```

**Environment variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `REPO_DIR` | `dist/apt` | Repository output directory |
| `APT_DIST` | `stable` | Distribution name |
| `APT_COMPONENT` | `main` | Component name |
| `APT_GPG_PRIVATE_KEY` | — | GPG private key for signing |
| `APT_GPG_PASSPHRASE` | — | GPG passphrase |
| `APT_GPG_ALLOW_EPHEMERAL` | `0` | Allow temp key for testing |

**Output:**
```
dist/apt/
├── dists/stable/
│   ├── Release
│   ├── Release.gpg
│   ├── InRelease
│   └── main/binary-amd64/
├── pool/main/f/fu7ur3pr00f/
│   └── fu7ur3pr00f_<version>_amd64.deb
└── fu7ur3pr00f-archive-keyring.gpg
```

---

## Test Scripts

### `validate_apt_artifact.sh` — Test .deb in containers

Validates a .deb package installs/uninstalls cleanly in Docker containers.

```bash
./scripts/validate_apt_artifact.sh path/to/package.deb
```

**Environment variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `APT_VALIDATION_IMAGES` | `ubuntu:24.04 debian:12` | Container images to test |

**What it does:**
1. Builds temp apt repo with `build_apt_repo.sh`
2. Starts local HTTP server
3. Runs Docker container for each image
4. Tests: install → version → reinstall → version → remove → purge
5. Verifies no files remain after purge
6. Cleans up

**Requirements:** Docker, `apt-ftparchive`, `dpkg-scanpackages`, `gpg`

---

### `run_vagrant_apt_smoke.sh` — Test apt packages in VMs

Runs apt install/reinstall/remove/purge tests in disposable Vagrant VMs.

```bash
./scripts/run_vagrant_apt_smoke.sh ubuntu2404
./scripts/run_vagrant_apt_smoke.sh debian12
./scripts/run_vagrant_apt_smoke.sh all
./scripts/run_vagrant_apt_smoke.sh debian12 --keep
```

**Options:**
| Option | Description |
|--------|-------------|
| `ubuntu2404` | Test on Ubuntu 24.04 LTS |
| `debian12` | Test on Debian 12 (Bookworm) |
| `all` | Test on both boxes |
| `--keep` | Don't destroy VM after test |

**Requirements:** Vagrant + VirtualBox

---

### `vagrant_test_multi.sh` — Multi-agent Vagrant test

Runs integration tests for the multi-agent system inside a Vagrant VM.

```bash
./scripts/vagrant_test_multi.sh
```

Tests that the `/multi` command and specialist agents (Coach, Learning, Jobs, Code, Founder) initialize and respond correctly in an isolated environment.

---

## Internal Scripts

### `vagrant_dev_setup.sh` — Development VM manager

Manages a development Vagrant environment with your data and secrets.

```bash
./scripts/vagrant_dev_setup.sh up
./scripts/vagrant_dev_setup.sh ssh
./scripts/vagrant_dev_setup.sh halt
./scripts/vagrant_dev_setup.sh destroy
./scripts/vagrant_dev_setup.sh status
./scripts/vagrant_dev_setup.sh logs
./scripts/vagrant_dev_setup.sh setup
```

**Commands:**
| Command | Description |
|---------|-------------|
| `up` | Start VM and provision |
| `ssh` | SSH into running VM |
| `halt` | Stop VM (save state) |
| `destroy` | Destroy VM |
| `status` | Show VM status |
| `logs` | Show provisioning logs |
| `setup` | Copy data/.env and start VM |

**Options:**
| Option | Description |
|--------|-------------|
| `--box ubuntu2404` | Use Ubuntu 24.04 (default) |
| `--box debian12` | Use Debian 12 |

**File locations in VM:**
- Code: `/workspace`
- Data: `/workspace/data/raw`
- Config: `/home/vagrant/.fu7ur3pr00f/.env`
- Venv: `/workspace/.venv`

---

### `vagrant_apt_smoke.sh` — Vagrant provision script

Provisioning script run inside Vagrant VMs by `run_vagrant_apt_smoke.sh`.

**Not meant to be run directly.** Called by Vagrant with these env vars:

| Variable | Value |
|----------|-------|
| `PACKAGE_NAME` | `fu7ur3pr00f` |
| `REPO_BASE_URL` | `https://juanmanueldaza.github.io/fu7ur3pr00f` |
| `REPO_DIST` | `stable` |
| `REPO_COMPONENT` | `main` |
| `LOG_PATH` | `/home/vagrant/fu7ur3pr00f-apt-smoke.log` |

---

## Quick Reference by Task

| Task | Command |
|------|---------|
| Run tests | `pytest tests/ -q` or `python scripts/run_tests.py` |
| Set up pre-commit | `./scripts/setup_precommit.sh` |
| First-time Azure setup | `./scripts/setup.sh` |
| Validate pipx install | `./scripts/fresh_install_check.sh --source local --config-from .env` |
| Test apt package | `./scripts/validate_apt_artifact.sh dist/deb/fu7ur3pr00f_*.deb` |
| Test in VMs | `./scripts/run_vagrant_apt_smoke.sh all` |
| Dev VM | `./scripts/vagrant_dev_setup.sh setup` |
| Build .deb | `./scripts/build_deb.sh` |
| Build apt repo | `./scripts/build_apt_repo.sh dist/deb/fu7ur3pr00f_*.deb` |
| Clean artifacts | `./scripts/clean_dev_artifacts.sh` |

---

## See Also

- [Development Guide](development.md)
- `vagrant/README.md` — Vagrant details
