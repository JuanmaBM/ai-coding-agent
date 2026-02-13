# Security

## LLM Hallucination Control

AI-generated code can contain errors, hallucinated imports, or unintended changes. The agent mitigates these risks through several mechanisms:

### Repository Isolation

- Each task operates on a **fresh shallow clone** (`--depth 1`) of the repository.
- The workspace is an **ephemeral `emptyDir`** volume that is destroyed after each task.
- The worker never modifies the original repository directly; all changes go through a PR for human review.

### Aider Guardrails

- Aider operates within the cloned repository and only modifies files it can see.
- Aider validates syntax before committing changes.
- Generated changes are always submitted as a **Pull Request**, never merged automatically.

### Human Review

- Every change requires human review before merging.
- The Refine Mode allows reviewers to request additional changes via `/refine` commands.
- Labels (`ai-agent`, `quickfix`) clearly mark agent-generated PRs.

## Access Control

### GitHub Token

The agent uses a GitHub Personal Access Token (PAT) with the minimum required scope:

| Scope | Permission | Usage |
|---|---|---|
| `repo` | Full control of private repos | Clone, push branches, create PRs, post comments |

**Best practices:**
- Rotate tokens every 90 days.
- Use a dedicated bot account, not a personal account.
- For production, use a GitHub App with fine-grained permissions instead of a PAT.

### Secrets Management

All sensitive credentials are stored as Kubernetes Secrets and injected as environment variables:

| Secret | Contents | Used By |
|---|---|---|
| `github-credentials` | GitHub PAT | Worker (git push, GitHub API) |
| `rabbitmq-credentials` | Username/password | Worker (queue connection) |
| `keda-rabbitmq-secret` | AMQP connection URL | KEDA (queue monitoring) |

Secrets are never:
- Hardcoded in source code
- Logged in application output
- Stored in ConfigMaps

### Network Security

- Workers communicate with RabbitMQ and Ollama via **ClusterIP** services (internal only).
- The GitHub API is accessed over HTTPS.
- Git operations use token-authenticated HTTPS (not SSH).

## Ephemeral Workspaces

Each task creates a temporary directory under `/tmp/workspace/` for git operations:

```
/tmp/workspace/repo-{issue_id}/
├── .git/
├── src/
└── ...
```

This directory is:
- Created at the start of the task.
- Deleted in a `finally` block, even if the task fails.
- Backed by an `emptyDir` volume with a 5Gi size limit.
- Never shared between tasks or pods.

## Threat Model

| Threat | Mitigation |
|---|---|
| LLM generates malicious code | Human review required before merge |
| Token leaked in logs | Tokens injected as env vars, not logged |
| Worker compromise | Ephemeral pods, minimal permissions, no persistent state |
| Queue poisoning | Message validation with Pydantic models |
| Denial of service | KEDA `maxReplicaCount: 10` limits pod scaling |

