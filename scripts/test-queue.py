#!/usr/bin/env python3
"""Publish test messages to RabbitMQ for KEDA scaling validation"""

import argparse
import json
import pika
import sys
import structlog
import time  # Import the time module

logger = structlog.get_logger()

def publish_test_messages(
    host: str = "localhost",
    port: int = 5672,
    username: str = "admin",
    password: str = "password",
    queue: str = "agent-tasks",
    count: int = 1,
    delay: float = 0
):
    """Publish test messages to RabbitMQ."""
    credentials = pika.PlainCredentials(username, password)
    parameters = pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=credentials,
        virtual_host="/"
    )
    
    try:
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        channel.queue_declare(queue=queue, durable=True)
        
        for i in range(count):
            message = {
                "repo_url": f"https://github.com/test/repo-{i}",
                "issue_id": i + 1,
                "mode": "plan",
                "trigger_user": "test-script"
            }
            
            print(f"📤 Publishing test message {i+1}/{count}...")
            channel.basic_publish(
                exchange="",
                routing_key=queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            
            if delay > 0:
                time.sleep(delay)
        
        connection.close()
        
        print(f"✅ {count} messages published!")
        print(f"\n📊 Monitor with:")
        print(f"   kubectl get pods -n ai-agent -w")
    
    except pika.exceptions.AMQPConnectionError as e:
        print(f"❌ Failed to connect to RabbitMQ: {e}", file=sys.stderr)
        print(f"\n💡 Tip: Make sure RabbitMQ is running and accessible at {host}:{port}")
        print(f"   For Minikube, you may need to port-forward:")
        print(f"   kubectl port-forward -n ai-agent svc/rabbitmq 5672:5672")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    logger.info("Script created by agent code")
    parser = argparse.ArgumentParser(
        description="Publish test messages to RabbitMQ for KEDA scaling validation"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="RabbitMQ host (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5672,
        help="RabbitMQ port (default: 5672)"
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="RabbitMQ username (default: admin)"
    )
    parser.add_argument(
        "--password",
        default="password",
        help="RabbitMQ password (default: password)"
    )
    parser.add_argument(
        "--queue",
        default="agent-tasks",
        help="Queue name (default: agent-tasks)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of messages to publish (default: 1)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0,
        help="Delay in seconds between messages (default: 0)"
    )
    
    args = parser.parse_args()
    
    publish_test_messages(
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        queue=args.queue,
        count=args.count,
        delay=args.delay
    )


if __name__ == "__main__":
    main()
