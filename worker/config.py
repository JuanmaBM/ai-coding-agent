"""Configuration management for the AI Agent Worker."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # RabbitMQ Configuration
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "admin"
    rabbitmq_password: str = "password"
    rabbitmq_vhost: str = "/"
    rabbitmq_queue: str = "agent-tasks"
    rabbitmq_graceful_timeout: int = 300

    # Worker Configuration
    log_level: str = "INFO"

    # Git Configuration
    git_clone_depth: int = 1
    workspace_dir: str = "/tmp/workspace"

    # GitHub Configuration
    github_token: str = ""

    # LLM Configuration
    llm_provider: str = "ollama"
    llm_model: str = "qwen2.5-coder:1.5b"
    ollama_base_url: str = "http://localhost:11434"

    @property
    def rabbitmq_url(self) -> str:
        """Construct RabbitMQ connection URL."""
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/{self.rabbitmq_vhost}"
        )


# Global settings instance
settings = Settings()
