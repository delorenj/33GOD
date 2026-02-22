# Heartbeat Consumer Development

## Setup

```bash
cd ~/code/33GOD/heartbeat-consumer
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Code Quality

```bash
# Linting
ruff check heartbeat_consumer/
ruff format heartbeat_consumer/

# Type checking
mypy heartbeat_consumer/

# Tests
pytest tests/
```

## Building

```bash
python -m build
```
