# Local Development Guide

## Quick Setup

```bash
# 1. Start services
chmod +x scripts/setup-local.sh scripts/cleanup-local.sh
./scripts/setup-local.sh

# 2. Setup worker
cd worker
python -m venv .venv
source .venv/bin/activate

# Install as editable package (this fixes all import issues!)
pip install -e .

# Or if you prefer requirements.txt:
# pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your GitHub token

# 3. Run worker
python main.py

# 4. Test (in another terminal)
cd scripts
python test-iteration3.py --repo-url https://github.com/user/repo --issue-id 1
```

## Cleanup

```bash
./scripts/cleanup-local.sh
```

