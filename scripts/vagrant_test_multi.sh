#!/usr/bin/env bash
set -euo pipefail

# Test multi-agent system in Vagrant VM
# Usage: scripts/vagrant_test_multi.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

# Check if Vagrant is running
if ! vagrant status | grep -q "running"; then
    error "VM is not running. Start it first:"
    echo "  scripts/vagrant_dev_setup.sh up"
    exit 1
fi

log "Testing multi-agent system in Vagrant VM..."

# Run tests inside VM
vagrant ssh -c "
    set -e
    cd /workspace
    
    log 'Activating virtual environment...'
    source .venv/bin/activate
    
    log 'Running multi-agent tests...'
    python3 -m pytest tests/agents/specialists/test_agents.py -v
    
    log 'Running benchmarks...'
    python3 -m pytest tests/benchmarks/test_multi_agent.py -v
    
    log 'All tests passed!'
"

log "Multi-agent system test complete!"
