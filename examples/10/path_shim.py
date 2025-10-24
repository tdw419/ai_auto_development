#!/usr/bin/env python3
"""
Path shim to make timezone utilities available for legacy CLI scripts.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _inject_repo_paths() -> None:
    """Insert plausible repository roots so imports resolve."""
    candidates = [
        Path(__file__).resolve().parents[2],  # repo root when run from examples/10
        Path(__file__).resolve().parents[1],  # examples directory
        Path.cwd(),
    ]

    env_override = os.environ.get("VISTA_UTILS_PATH")
    if env_override:
        candidates.insert(0, Path(env_override))

    for root in candidates:
        utils_dir = root / "examples" / "11" / "utils"
        if utils_dir.exists():
            sys.path.insert(0, str(utils_dir.parent))  # add examples/11
            sys.path.insert(0, str(utils_dir.parent.parent))  # add repo root
            return


def _import_time_utils():
    """Try importing timezone utilities, falling back if unavailable."""
    try:
        from utils.time_utils import get_current_utc_time, to_iso_format  # type: ignore
        return get_current_utc_time, to_iso_format
    except Exception:
        _inject_repo_paths()
        try:
            from utils.time_utils import get_current_utc_time, to_iso_format  # type: ignore
            return get_current_utc_time, to_iso_format
        except Exception:
            return _fallback_now, _fallback_iso


def _fallback_now() -> datetime:
    """Fallback UTC provider if utils cannot be imported."""
    return datetime.now(timezone.utc)


def _fallback_iso(dt: datetime) -> str:
    """Fallback ISO formatting."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


get_current_utc_time, to_iso_format = _import_time_utils()


__all__ = ["get_current_utc_time", "to_iso_format"]
