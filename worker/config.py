"""Configuration management for the AI Agent Worker."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # RabbitMQ Configuration
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "admin"
    rabbitmq_password: str = "password"
    rabbitmq_vhost: str = "/"
    rabbitmq_queue: str = "agent-tasks"
    
    # Worker Configuration
    log_level: str = "INFO"
    worker_timeout: int = 600  # 10 minutes
    
    # Git Configuration
    git_clone_depth: int = 1
    workspace_dir: str = "/tmp/workspace"
    
    @property
    def rabbitmq_url(self) -> str:
        """Construct RabbitMQ connection URL."""
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/{self.rabbitmq_vhost}"
        )


# Global settings instance
settings = Settings()

