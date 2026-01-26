"""AI Agent Worker - Hello World Implementation (Iteration 2)."""

import asyncio
import structlog
from faststream import FastStream
from faststream.rabbit import RabbitBroker

from config import settings
from models import TaskMessage

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Initialize RabbitMQ broker
broker = RabbitBroker(settings.rabbitmq_url)
app = FastStream(broker)


@broker.subscriber(settings.rabbitmq_queue)
async def process_task(message: TaskMessage) -> None:
    """
    Process incoming tasks from RabbitMQ queue.
    
    This is the "Hello World" implementation for Iteration 2.
    It simply logs the message details and simulates processing.
    
    Args:
        message: Task message containing repo_url, issue_id, mode, and trigger_user
    """
    log = logger.bind(
        repo_url=str(message.repo_url),
        issue_id=message.issue_id,
        mode=message.mode.value,
        trigger_user=message.trigger_user
    )
    
    log.info("task_received", msg="Starting task processing")
    
    try:
        # Simulate task processing
        log.info("processing", msg="Analyzing repository...")
        await asyncio.sleep(1)
        
        log.info("processing", msg="Generating solution...")
        await asyncio.sleep(1)
        
        log.info("processing", msg="Preparing output...")
        await asyncio.sleep(1)
        
        log.info(
            "task_completed",
            msg="Task processed successfully",
            duration_seconds=3
        )
        
        # Message is automatically ACK'd if no exception is raised
        
    except Exception as e:
        log.error(
            "task_failed",
            msg="Task processing failed",
            error=str(e),
            exc_info=True
        )
        # Re-raise to trigger NACK and requeue
        raise


@app.on_startup
async def on_startup():
    """Log startup information."""
    logger.info(
        "worker_starting",
        msg="AI Agent Worker starting",
        rabbitmq_host=settings.rabbitmq_host,
        queue=settings.rabbitmq_queue,
        log_level=settings.log_level
    )


@app.on_shutdown
async def on_shutdown():
    """Log shutdown information."""
    logger.info("worker_shutdown", msg="AI Agent Worker shutting down")


if __name__ == "__main__":
    # Run the FastStream application
    app.run()

