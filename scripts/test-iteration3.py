#!/usr/bin/env python3
"""Test script for Iteration 3 - Plan Mode."""

import argparse
import json
import pika
import sys


def publish_plan_mode_test(
    host: str = "localhost",
    port: int = 5672,
    username: str = "admin",
    password: str = "DevPassword123",
    queue: str = "agent-tasks",
    repo_url: str = None,
    issue_id: int = 1
):
    """Publish a Plan Mode test message to RabbitMQ."""
    if not repo_url:
        print("❌ Error: --repo-url is required")
        print("\nExample:")
        print("  python test-iteration3.py --repo-url https://github.com/JuanmaBM/ai-coding-agent --issue-id 1")
        sys.exit(1)
    
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
        
        message = {
            "repo_url": repo_url,
            "issue_id": issue_id,
            "mode": "quickfix",
            "trigger_user": "test-script"
        }
        
        print(f"📤 Publishing Plan Mode test message...")
        print(f"   Repository: {repo_url}")
        print(f"   Issue ID: {issue_id}")
        print()
        
        channel.basic_publish(
            exchange="",
            routing_key=queue,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        connection.close()
        
        print(f"✅ Message published!")
        print(f"\n📊 Monitor with:")
        print(f"   kubectl get pods -n ai-agent -w")
        print(f"   kubectl logs -f -n ai-agent -l app=ai-agent-worker")
        
    except pika.exceptions.AMQPConnectionError as e:
        print(f"❌ Failed to connect to RabbitMQ: {e}", file=sys.stderr)
        print(f"\n💡 Tip: Port-forward RabbitMQ first:")
        print(f"   kubectl port-forward -n ai-agent svc/rabbitmq 5672:5672")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Test Iteration 3 - Plan Mode")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5672)
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="DevPassword123")
    parser.add_argument("--queue", default="agent-tasks")
    parser.add_argument("--repo-url", required=True, help="GitHub repository URL")
    parser.add_argument("--issue-id", type=int, default=1, help="Issue number")
    
    args = parser.parse_args()
    
    publish_plan_mode_test(
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        queue=args.queue,
        repo_url=args.repo_url,
        issue_id=args.issue_id
    )


if __name__ == "__main__":
    main()

