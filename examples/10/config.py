"""
Configuration for Multi-Agent Verification Loop System
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class LMStudioConfig:
    """LM Studio API configuration"""
    base_url: str = "http://localhost:1234/v1"
    model: str = "local-model"
    timeout: int = 300
    
    # Generation parameters
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float = 0.9


@dataclass
class EmbedderConfig:
    """Embedding model configuration"""
    model_name: str = "text-embedding-qwen3-embedding-0.6b"
    base_url: str = "http://localhost:1234/v1"
    embedding_dim: int = 768


@dataclass
class AgentConfig:
    """Agent behavior configuration"""
    
    # Builder settings
    builder_max_duration_minutes: int = 20
    builder_token_limit: int = 4000
    
    # Verifier settings
    verifier_max_duration_minutes: int = 10
    verifier_run_tests: bool = True
    verifier_run_lint: bool = True
    verifier_run_coherence_check: bool = True
    
    # Scheduler settings
    max_retries: int = 2
    escalation_threshold: int = 3  # Escalate after N consecutive failures
    token_budget: int = 100000  # Total token budget per task


@dataclass
class DatabaseConfig:
    """LanceDB configuration"""
    db_path: str = "./data/lancedb"
    cleanup_days: int = 30  # Archive data older than this


@dataclass
class SystemConfig:
    """Complete system configuration"""
    
    # Component configs
    llm: LMStudioConfig = None
    embedder: EmbedderConfig = None
    agent: AgentConfig = None
    database: DatabaseConfig = None
    
    # Repository settings
    repo_path: str = "."
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "./logs/agent_system.log"
    
    # Feature flags
    use_mock_llm: bool = False  # Use mock LLM for testing
    use_mock_tests: bool = False  # Use mock test runner
    
    def __post_init__(self):
        """Initialize sub-configs if not provided"""
        if self.llm is None:
            self.llm = LMStudioConfig()
        if self.embedder is None:
            self.embedder = EmbedderConfig()
        if self.agent is None:
            self.agent = AgentConfig()
        if self.database is None:
            self.database = DatabaseConfig()


def load_config_from_file(config_path: str) -> SystemConfig:
    """
    Load configuration from JSON or YAML file
    
    Args:
        config_path: Path to config file
        
    Returns:
        SystemConfig object
    """
    import json
    from pathlib import Path
    
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file) as f:
        if config_path.endswith('.json'):
            data = json.load(f)
        elif config_path.endswith(('.yaml', '.yml')):
            import yaml
            data = yaml.safe_load(f)
        else:
            raise ValueError("Config file must be .json or .yaml")
    
    # Build nested configs
    config = SystemConfig()
    
    if 'llm' in data:
        config.llm = LMStudioConfig(**data['llm'])
    
    if 'embedder' in data:
        config.embedder = EmbedderConfig(**data['embedder'])
    
    if 'agent' in data:
        config.agent = AgentConfig(**data['agent'])
    
    if 'database' in data:
        config.database = DatabaseConfig(**data['database'])
    
    # Top-level settings
    for key in ['repo_path', 'log_level', 'log_file', 'use_mock_llm', 'use_mock_tests']:
        if key in data:
            setattr(config, key, data[key])
    
    return config


def get_default_config() -> SystemConfig:
    """Get default configuration"""
    return SystemConfig()


# Example config dictionary for reference
EXAMPLE_CONFIG = {
    "llm": {
        "base_url": "http://localhost:1234/v1",
        "model": "local-model",
        "timeout": 300,
        "temperature": 0.7,
        "max_tokens": 4000
    },
    "embedder": {
        "model_name": "text-embedding-qwen3-embedding-0.6b",
        "base_url": "http://localhost:1234/v1",
        "embedding_dim": 768
    },
    "agent": {
        "builder_max_duration_minutes": 20,
        "verifier_max_duration_minutes": 10,
        "max_retries": 2,
        "token_budget": 100000
    },
    "database": {
        "db_path": "./data/lancedb",
        "cleanup_days": 30
    },
    "repo_path": ".",
    "log_level": "INFO",
    "use_mock_llm": False,
    "use_mock_tests": False
}
