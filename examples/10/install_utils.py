#!/usr/bin/env python3
"""Helper script to install timezone utilities for legacy examples."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SETUP_TEMPLATE = """from setuptools import setup

setup(
    name="vista-time-utils",
    version="1.0.0",
    packages=["utils"],
    package_dir={"": "../11"},
    python_requires=">=3.8",
)
"""


def ensure_setup_file(setup_path: Path) -> None:
    if setup_path.exists():
        return
    setup_path.write_text(SETUP_TEMPLATE)


def install_utils() -> bool:
    setup_path = Path(__file__).resolve().with_name("setup.py")
    ensure_setup_file(setup_path)
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(setup_path.parent)], check=True)
        print("✅ timezone utilities installed (editable mode)")
        return True
    except subprocess.CalledProcessError as exc:
        print(f"❌ Installation failed: {exc}")
        return False


if __name__ == "__main__":  # pragma: no cover
    success = install_utils()
    sys.exit(0 if success else 1)
