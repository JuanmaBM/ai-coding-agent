"""AI Agent Worker - With Git & LLM Integration (Iteration 3)."""

import asyncio
import structlog
from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitQueue

from worker.config import settings
from worker.git.git_client import GitClient
from worker.git.git_handler import GitHandler
from worker.llm_client import LLMClient
from worker.models import TaskMessage, TaskMode

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

# Initialize RabbitMQ broker with graceful timeout
broker = RabbitBroker(
    settings.rabbitmq_url,
    graceful_timeout=settings.rabbitmq_graceful_timeout,
)
app = FastStream(broker)

# Declare queue as durable to match existing queue
queue = RabbitQueue(name=settings.rabbitmq_queue, durable=True)

# Initialize shared handlers
git_handler = GitHandler()
git_client = GitClient()
llm_client = LLMClient()


@broker.subscriber(queue)
async def process_task(message: TaskMessage) -> None:
    """
    Process incoming tasks from RabbitMQ queue.

    Routes tasks to appropriate mode handler.

    Args:
        message: Task message containing repo_url, issue_id, mode, and trigger_user
    """
    log = logger.bind(
        repo_url=str(message.repo_url),
        issue_id=message.issue_id,
        mode=message.mode.value,
        trigger_user=message.trigger_user,
    )

    log.info("task_received", msg="Starting task processing")

    try:
        # Route to appropriate mode
        if message.mode == TaskMode.QUICKFIX:
            from worker.modes.quickfix_mode import QuickFixMode

            quickfix_mode = QuickFixMode(
                git_handler=git_handler,
                git_client=git_client,
                llm_client=llm_client,
            )
            await quickfix_mode.execute(message)

        elif message.mode == TaskMode.REFINE:
            log.warning("mode_not_implemented", msg="Refine mode not yet implemented")

        else:
            log.error("unknown_mode", msg="Unknown task mode", mode=message.mode)
            raise ValueError(f"Unknown mode: {message.mode}")

        log.info("task_completed", msg="Task processed successfully")

    except Exception as e:
        log.error("task_failed", msg="Task processing failed", error=str(e), exc_info=True)
        raise


@app.on_startup
async def on_startup():
    """Log startup information."""
    logger.info(
        "worker_starting",
        msg="AI Agent Worker starting",
        rabbitmq_host=settings.rabbitmq_host,
        queue=settings.rabbitmq_queue,
        log_level=settings.log_level,
    )


@app.on_shutdown
async def on_shutdown():
    """Log shutdown information."""
    logger.info("worker_shutdown", msg="AI Agent Worker shutting down")


if __name__ == "__main__":
    asyncio.run(app.run())
