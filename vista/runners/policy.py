"""
Security policies for code execution across all runners.
"""

# Patterns that will cause immediate rejection
DENY_PATTERNS = [
    "rm -rf /", "sudo ", "wget http", "curl http", "ssh ",
    "eval(", "exec(", "__import__('os')", "open('/etc/'",
    "open('/proc/'", "import os.system", "subprocess.call",
    "import socket", "import urllib.request", "import requests",
    "import http.client", "import ftplib", "import telnetlib"
]

# Network access control
ALLOW_NET = False

# Resource limits
MAX_MEMORY_MB = 512
MAX_CPUS = 1.0
MAX_EXECUTION_TIME = 120  # seconds

# File system restrictions
READONLY_FS = True
ALLOWED_PATHS = ["/tmp", "/workspace"]

def check_policy_violation(code: str) -> list[str]:
    """
    Check code against security policies.

    Returns:
        List of violation messages, empty if safe
    """
    violations = []
    code_lower = code.lower()

    for pattern in DENY_PATTERNS:
        if pattern in code_lower:
            violations.append(f"Denied pattern: {pattern}")

    return violations
