import json, os, time
from typing import Dict, Any

def append_jsonl(filepath: str, data: Dict[str, Any]):
    """
    Append JSON object to JSONL file with timestamp.

    Args:
        filepath: Path to JSONL file
        data: Dictionary to log
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Add metadata
    log_entry = {
        **data,
        "_timestamp": time.time(),
        "_iso_time": __import__('datetime').datetime.utcnow().isoformat() + "Z"
    }

    # Append to file
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, separators=(",", ":")) + "\n")

def read_jsonl(filepath: str) -> list[Dict[str, Any]]:
    """
    Read JSONL file and return list of objects.

    Args:
        filepath: Path to JSONL file

    Returns:
        List of logged objects
    """
    if not os.path.exists(filepath):
        return []

    entries = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries
