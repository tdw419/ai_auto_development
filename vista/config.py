import os
CONFIG = {
    "DB_PATH": os.getenv("VISTA_DB_PATH", "vista_memory.db"),
    "LOG_PATH": os.getenv("VISTA_LOG_PATH", "./logs/verdicts.jsonl"),
    "ALLOW_NET": os.getenv("VISTA_ALLOW_NET", "false").lower() == "true",
    "DEFAULT_P95_MS": int(os.getenv("VISTA_DEFAULT_P95_MS", "250")),
}
