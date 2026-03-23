# Vagrant Development Setup

Quick guide to run FutureProof in a disposable Vagrant VM with your data and secrets.

## Prerequisites

- [Vagrant](https://www.vagrantup.com/download)
- [VirtualBox](https://www.virtualbox.org/wiki/Downloads) (or another provider)

## Quick Start

### 1. Configure Your Secrets

Copy the example config and add your API keys:

```bash
mkdir -p ~/.fu7ur3pr00f
cp .env.example ~/.fu7ur3pr00f/.env
nano ~/.fu7ur3pr00f/.env  # Edit with your keys
```

Minimum required:
- `FUTUREPROOF_PROXY_KEY=fp-...` (get free tokens at https://fu7ur3pr00f.dev/signup)
- OR `OPENAI_API_KEY=sk-...`

### 2. Add Your Career Data

Place your data files in `data/raw/`:

```
data/raw/
├── linkedin_export.csv      # LinkedIn profile export
├── cliffordstrengths.pdf    # CliftonStrengths assessment (optional)
└── ...
```

### 3. Start the VM

**Recommended: Use the helper script**

```bash
scripts/vagrant_dev_setup.sh setup
```

This will:
- Boot an Ubuntu 24.04 VM
- Install all dependencies (Python, system libs, GitHub MCP server)
- Set up the virtual environment
- Install the project
- Mount your `~/.fu7ur3pr00f` config directory

**Alternative: Use Vagrant directly**

```bash
cd vagrant
vagrant up --provision
vagrant ssh
```

### 4. SSH and Run

```bash
scripts/vagrant_dev_setup.sh ssh
```

Inside the VM:

```bash
cd /workspace
source .venv/bin/activate
fu7ur3pr00f
```

## Commands

| Command | Description |
|---------|-------------|
| `scripts/vagrant_dev_setup.sh up` | Start VM and provision |
| `scripts/vagrant_dev_setup.sh ssh` | SSH into running VM |
| `scripts/vagrant_dev_setup.sh halt` | Stop VM (save state) |
| `scripts/vagrant_dev_setup.sh destroy` | Destroy VM and free resources |
| `scripts/vagrant_dev_setup.sh status` | Show VM status |

## File Locations

| Inside VM | Description |
|-----------|-------------|
| `/workspace` | Project root (synced from host) |
| `/workspace/data/raw` | Your career data files |
| `/home/vagrant/.fu7ur3pr00f/.env` | Your secrets (synced from host) |
| `/workspace/.venv` | Python virtual environment |

## Tips

### Re-provision after code changes

If you modify the code on the host, it's immediately available in the VM (synced folder). Just re-install:

```bash
vagrant ssh
cd /workspace
source .venv/bin/activate
pip install -e .
```

### Clean slate

To completely reset:

```bash
scripts/vagrant_dev_setup.sh destroy
scripts/vagrant_dev_setup.sh up
```

### Use Debian instead of Ubuntu

```bash
scripts/vagrant_dev_setup.sh up --box debian12
```

### Increase VM resources

Edit `vagrant/Vagrantfile.dev`:

```ruby
config.vm.provider "virtualbox" do |vb|
  vb.memory = 8192  # More RAM
  vb.cpus = 4       # More CPU cores
end
```

## Troubleshooting

### "VM not found"

Run `vagrant up --provision` to create it.

### "Port already in use"

Run `vagrant destroy` and `vagrant up` to recreate with a new port.

### "No module named 'fu7ur3pr00f'"

Re-install the package:

```bash
cd /workspace
source .venv/bin/activate
pip install -e .
```

### GitHub MCP server not found

Install manually inside the VM:

```bash
curl -fsSL https://github.com/github/github-mcp-server/releases/latest/download/github-mcp-server_Linux_x86_64.tar.gz | \
  sudo tar xzf - -C /usr/local/bin github-mcp-server
```

### Permission denied on synced folders

Fix ownership inside the VM:

```bash
sudo chown -R vagrant:vagrant /workspace
```
