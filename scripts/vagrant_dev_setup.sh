#!/usr/bin/env bash
set -euo pipefail

# Helper script to set up and run FutureProof in Vagrant
# Usage: scripts/vagrant_dev_setup.sh [ubuntu2404|debian12]

usage() {
  cat <<'USAGE'
Usage: scripts/vagrant_dev_setup.sh [COMMAND] [OPTIONS]

Commands:
  up        Start the Vagrant VM and provision
  ssh       SSH into the running VM
  halt      Stop the VM
  destroy   Destroy the VM and free resources
  status    Show VM status
  logs      Show provisioning logs
  setup     Copy your data and .env to the project, then start VM

Options:
  --box     Box to use: ubuntu2404 (default) or debian12
  --help    Show this help message

Examples:
  scripts/vagrant_dev_setup.sh up
  scripts/vagrant_dev_setup.sh setup
  scripts/vagrant_dev_setup.sh ssh
  scripts/vagrant_dev_setup.sh destroy
USAGE
}

command="${1:-help}"
shift || true

box="ubuntu2404"
vagrant_file="Vagrantfile.dev"

# Parse options
while [[ $# -gt 0 ]]; do
  case "$1" in
    --box)
      box="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
vagrant_dir="${repo_root}/vagrant"

cd "${vagrant_dir}"

case "${command}" in
  up)
    echo "Starting Vagrant VM (${box})..."
    VAGRANT_VAGRANTFILE="${vagrant_file}" vagrant up --provision
    echo ""
    echo "✓ VM is running. SSH with: scripts/vagrant_dev_setup.sh ssh"
    ;;

  ssh)
    if ! VAGRANT_VAGRANTFILE="${vagrant_file}" vagrant status | grep -q "running"; then
      echo "VM is not running. Start it with: scripts/vagrant_dev_setup.sh up" >&2
      exit 1
    fi
    echo "SSHing into VM..."
    VAGRANT_VAGRANTFILE="${vagrant_file}" vagrant ssh
    ;;

  halt)
    echo "Stopping VM..."
    VAGRANT_VAGRANTFILE="${vagrant_file}" vagrant halt
    ;;

  destroy)
    echo "Destroying VM..."
    VAGRANT_VAGRANTFILE="${vagrant_file}" vagrant destroy -f
    echo "✓ VM destroyed"
    ;;

  status)
    VAGRANT_VAGRANTFILE="${vagrant_file}" vagrant status
    ;;

  logs)
    VAGRANT_VAGRANTFILE="${vagrant_file}" vagrant ssh -c "cat /home/vagrant/fu7ur3pr00f-apt-smoke.log 2>/dev/null || echo 'No logs found'"
    ;;

  setup)
    echo "=== Setting up Vagrant development environment ==="
    echo ""

    # Check if .env exists locally
    local_env="${HOME}/.fu7ur3pr00f/.env"
    if [[ ! -f "${local_env}" ]]; then
      echo "⚠ No .env found at ${local_env}"
      echo ""
      echo "Please configure your secrets first:"
      echo "  1. Copy .env.example to ~/.fu7ur3pr00f/.env"
      echo "  2. Edit ~/.fu7ur3pr00f/.env with your API keys"
      echo ""
      echo "Example:"
      echo "  mkdir -p ~/.fu7ur3pr00f"
      echo "  cp ${repo_root}/.env.example ~/.fu7ur3pr00f/.env"
      echo "  nano ~/.fu7ur3pr00f/.env"
      echo ""
      read -p "Continue anyway? [y/N] " -n 1 -r
      echo
      if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
      fi
    fi

    # Check for data files
    data_raw="${repo_root}/data/raw"
    if [[ ! -d "${data_raw}" ]] || [[ -z "$(ls -A "${data_raw}" 2>/dev/null)" ]]; then
      echo "⚠ No data files found in ${data_raw}"
      echo ""
      echo "Place your career data files here:"
      echo "  - LinkedIn CSV export"
      echo "  - CliftonStrengths PDF"
      echo "  - Portfolio URLs (configured in .env)"
      echo ""
      read -p "Continue anyway? [y/N] " -n 1 -r
      echo
      if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
      fi
    fi

    # Start the VM
    echo "Starting VM..."
    vagrant up --provision -f "${vagrant_file}"

    echo ""
    echo "=============================================="
    echo "✓ Setup complete!"
    echo "=============================================="
    echo ""
    echo "Next steps:"
    echo "  1. SSH into the VM: scripts/vagrant_dev_setup.sh ssh"
    echo "  2. Inside VM, run: cd /workspace && source .venv/bin/activate"
    echo "  3. Start the agent: fu7ur3pr00f"
    echo ""
    echo "Your files:"
    echo "  - Code: /workspace"
    echo "  - Data: /workspace/data/raw"
    echo "  - Config: /home/vagrant/.fu7ur3pr00f/.env"
    echo ""
    ;;

  help|--help|-h)
    usage
    ;;

  *)
    echo "Unknown command: ${command}" >&2
    usage
    exit 1
    ;;
esac
