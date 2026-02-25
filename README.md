# AI Coding Agent

An autonomous AI agent that resolves GitHub issues by analyzing code, generating fixes, and creating pull requests automatically.

## Overview

The AI Coding Agent is an event-driven system built on Kubernetes that processes GitHub issues. It uses [Aider](https://aider.chat) as the code generation engine, which supports any LLM provider (OpenAI, Anthropic, local models via Ollama, etc.).

For optimal results, a sufficiently powerful LLM is recommended (e.g., Claude 3.5 Sonnet, GPT-4o, DeepSeek Coder V2). Ollama with local models is supported for development and testing environments.

For deployment instructions, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). For architecture details, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Modes

### QuickFix Mode

Automatically generates code and creates a PR for the issue.

**Workflow:**
1. Agent receives the issue via RabbitMQ.
2. Clones the repository.
3. Uses Aider + LLM to generate the code fix.
4. Commits, pushes, and opens a Pull Request.
5. Posts a comment on the issue linking to the PR.

### Refine Mode

Allows reviewers to request changes on an agent-created PR using a `/refine` command.

**Trigger:** A reviewer comments `/refine <description of changes>` on any PR.

**Workflow:**
1. The webhook sends a `refine` task to RabbitMQ with the PR branch, comment ID, and refinement request.
2. Worker shallow-clones the repository directly on the PR branch.
3. Aider + LLM applies the requested changes to the existing code.
4. Pushes the updated commits to the same PR branch.
5. Adds a 🚀 reaction to the `/refine` comment to confirm completion.

**Required message fields:** `repo_url`, `pr_number`, `pr_branch`, `refine_request`, `comment_id`.

**Example `/refine` comment:**
```
/refine Add input validation to the create_user endpoint and return 400 on invalid email
```

## Architecture

The architecture is **stateless** and **event-driven**.

```mermaid
graph TD
    A[GitHub Issue] -->|QuickFix trigger| B[RabbitMQ Queue]
    G[PR /refine comment] -->|Refine trigger| B
    B -->|KEDA scales 0→N| C[Worker Pod]
    C -->|Clone| D[Repository]
    C -->|Aider| E[LLM Provider]
    C -->|Create PR / Push| F[GitHub API]
```

### Design Principles

1. **Stateless Workers** — Pods do not retain state between jobs.
2. **Scale to Zero** — KEDA scales the worker pool to zero when the queue is empty.
3. **Robust Delivery** — RabbitMQ ACK/NACK ensures no tasks are lost if a pod crashes.
4. **Ephemeral Storage** — Workers use `emptyDir` for temporary git operations.

## Technology Stack

| Component | Choice | Justification |
|---|---|---|
| **Language** | Python 3.11+ | AI ecosystem (FastStream, Pydantic, Aider) |
| **Message Broker** | RabbitMQ | Delivery guarantees (ACK/NACK), persistence |
| **Queue Library** | FastStream | Async AMQP abstraction, portable across brokers |
| **Orchestration** | Kubernetes + KEDA | Auto-scaling based on queue depth |
| **Code Generation** | Aider | AI pair programming tool, edits files directly |
| **LLM** | Any (OpenAI, Anthropic, Ollama, etc.) | Aider supports multiple providers. Use powerful models for best results |
| **Git** | GitPython + subprocess | Repository cloning, branching, pushing |
| **GitHub API** | PyGithub | Issue/PR management |

## Project Structure

```
ai-coding-agent/
├── pyproject.toml              # Python package definition
├── Dockerfile                  # Container image
├── Makefile                    # Build automation
├── install.sh                  # K8s automated deployment
├── docs/
│   └── DEPLOYMENT.md           # Deployment & dev guide
├── k8s/                        # Kubernetes manifests
│   ├── base/
│   └── secrets/
├── scripts/                    # Utility scripts
│   ├── setup-local.sh
│   ├── cleanup-local.sh
│   └── test-iteration3.py
└── src/worker/                 # Application code
    ├── main.py                 # FastStream entrypoint & routing
    ├── config.py               # Configuration (env vars)
    ├── models.py               # Pydantic message models
    ├── llm_client.py           # Aider + Ollama integration
    ├── git/
    │   ├── git_client.py       # Git provider factory
    │   ├── git_handler.py      # Git operations (clone, branch, push)
    │   └── github_client.py    # GitHub API client
    └── modes/
        ├── quickfix_mode.py    # QuickFix workflow orchestrator
        └── refine_mode.py      # Refine workflow orchestrator
```

## Worker Execution Flow

### QuickFix Mode

1. **Consume** — Worker claims a message from RabbitMQ.
2. **Clone** — Shallow clone (`depth=1`) of the target repository on `main`.
3. **Fetch Issue** — Read issue details from GitHub API.
4. **Branch** — Create a new branch `ai-agent/quickfix-issue-{id}`.
5. **Generate Code** — Aider analyzes the repo and generates changes using the configured LLM.
6. **Push** — Commit and push changes to the new branch.
7. **Create PR** — Open a pull request with the fix.
8. **Comment** — Post a comment on the issue linking to the PR.
9. **Cleanup** — Delete temporary workspace.
10. **ACK** — Acknowledge message to RabbitMQ.

### Refine Mode

1. **Consume** — Worker claims a refinement message from RabbitMQ.
2. **Clone** — Shallow clone (`depth=1`) directly on the PR branch.
3. **Refine Code** — Aider applies the requested changes using the LLM.
4. **Push** — Push new commits to the existing PR branch.
5. **React** — Add a 🚀 reaction to the `/refine` comment to signal completion.
6. **Cleanup** — Delete temporary workspace.
7. **ACK** — Acknowledge message to RabbitMQ.

## Security

- **Secrets** are injected via Kubernetes Secrets (GitHub token, RabbitMQ credentials).
- **Token Scope** is limited to `repo` (contents + issues + PRs).
- **Ephemeral workspaces** are deleted after each task.
- **Human review** is always required before merging agent-generated PRs.

For details on hallucination control, access control, and threat model, see [docs/SECURITY.md](docs/SECURITY.md).

## LLM Configuration

The agent supports any LLM provider through Aider: OpenAI, Anthropic, Ollama, and more. See [docs/LLM_CONFIGURATION.md](docs/LLM_CONFIGURATION.md) for setup instructions and recommended models.

## Roadmap

- [x] Kubernetes infrastructure (RabbitMQ, KEDA, auto-scaling)
- [x] Worker with FastStream message consumer
- [x] Git operations (clone, branch, commit, push)
- [x] GitHub API integration (issues, PRs, comments)
- [x] LLM integration via Aider + Ollama
- [x] QuickFix Mode (end-to-end)
- [x] Refine Mode (`/refine` command on PRs)
- [ ] GitHub webhook integration (automatic issue detection)
- [ ] CI/CD pipeline
- [ ] Helm chart

## License

See [LICENSE](LICENSE) for details.
