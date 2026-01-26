#!/usr/bin/env python3
"""
Test script to publish messages to RabbitMQ and validate KEDA scaling.

Usage:
    python test-queue.py --count 5 --delay 2
"""

import argparse
import json
import time
import pika
import sys


def publish_test_messages(
    host: str = "localhost",
    port: int = 5672,
    username: str = "admin",
    password: str = "password",
    queue: str = "agent-tasks",
    count: int = 1,
    delay: float = 0
):
    """
    Publish test messages to RabbitMQ queue.
    
    Args:
        host: RabbitMQ host
        port: RabbitMQ port
        username: RabbitMQ username
        password: RabbitMQ password
        queue: Queue name
        count: Number of messages to send
        delay: Delay in seconds between messages
    """
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
        
        # Declare queue (idempotent)
        channel.queue_declare(queue=queue, durable=True)
        
        print(f"📤 Publishing {count} message(s) to queue '{queue}'...\n")
        
        for i in range(count):
            message = {
                "repo_url": "https://github.com/example/test-repo",
                "issue_id": 42 + i,
                "mode": "plan",
                "trigger_user": "test-script"
            }
            
            channel.basic_publish(
                exchange="",
                routing_key=queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type="application/json"
                )
            )
            
            print(f"✅ Message {i+1}/{count} published: issue_id={message['issue_id']}")
            
            if delay > 0 and i < count - 1:
                time.sleep(delay)
        
        connection.close()
        print(f"\n🎉 Successfully published {count} message(s)!")
        print(f"\n📊 Monitor KEDA scaling with:")
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

