# Installation Guide

Installing `vista-time-utils` is straightforward and dependency-free.

## Requirements

- Python **3.8** or newer
- `pip` 20.0 or newer (recommended)

## Install from PyPI

```bash
pip install vista-time-utils
```

## Install from Source

Clone the repository and install in editable mode:

```bash
git clone https://github.com/tdw419/ai_auto_development.git
cd ai_auto_development
pip install -e ".[dev]"
```

## Optional Extras

| Extra | Description | Command |
|-------|-------------|---------|
| `dev` | Testing, formatting, type checking | `pip install "vista-time-utils[dev]"` |
| `docs` *(planned)* | Documentation tooling | `pip install "vista-time-utils[docs]"` |

## Verifying Installation

```bash
python -c "from vista_time import get_current_utc_time; print(get_current_utc_time())"
```
