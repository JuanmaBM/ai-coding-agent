# LLM Configuration

The AI Coding Agent uses [Aider](https://aider.chat) as the code generation engine. Aider supports multiple LLM providers, so you can choose the best model for your needs.

## Supported Providers

### OpenAI

```bash
export OPENAI_API_KEY=sk-...
export LLM_MODEL=gpt-4o
```

### Anthropic (Claude)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export LLM_MODEL=claude-3-5-sonnet-20241022
```

### Ollama (Local)

For development and testing without API costs:

```bash
# Start Ollama
ollama serve

# Pull a model
ollama pull qwen2.5-coder:14b

# Configure
export OLLAMA_BASE_URL=http://localhost:11434
export LLM_MODEL=qwen2.5-coder:14b
```

### Other Providers

Aider supports many other providers (Azure OpenAI, Google Gemini, AWS Bedrock, etc.). See [Aider LLM documentation](https://aider.chat/docs/llms.html) for the full list.

## Recommended Models

| Use Case | Model | Provider | Notes |
|---|---|---|---|
| **Production** | Claude 3.5 Sonnet | Anthropic | Best code generation quality |
| **Production** | GPT-4o | OpenAI | Strong all-around performance |
| **Budget** | DeepSeek Coder V2 | DeepSeek | Good quality, lower cost |
| **Local Dev** | qwen2.5-coder:14b | Ollama | No API costs, requires ~10GB RAM |
| **Local Dev (light)** | qwen2.5-coder:1.5b | Ollama | Faster, lower RAM, lower quality |

## Performance Considerations

### Model Size vs Quality

- **Larger models** (14B+ parameters) produce better code but are slower and require more resources.
- **Smaller models** (1.5B-7B) are faster but may generate incorrect or incomplete code.
- For production use, **always use the most capable model you can afford**.

### Context Window

Aider manages the context window automatically by:
- Building a repository map of the codebase.
- Selecting relevant files based on the prompt.
- Fitting as much context as possible within the model's token limit.

Larger context windows (128K+ tokens) allow Aider to work with bigger codebases.

### Timeouts

LLM generation can be slow, especially with local models. The worker is configured with:

- **httpx timeout**: 900 seconds (15 minutes) for API calls
- **Kubernetes terminationGracePeriodSeconds**: 1800 seconds (30 minutes)
- **FastStream graceful_timeout**: Configured via `RABBITMQ_GRACEFUL_TIMEOUT`

Adjust these values based on your model's generation speed.

## Configuration in Kubernetes

For Kubernetes deployments, LLM configuration is managed via:

### ConfigMap (`k8s/base/configmap.yaml`)

```yaml
data:
  LLM_PROVIDER: "ollama"
  LLM_MODEL: "qwen2.5-coder:14b"
  OLLAMA_BASE_URL: "http://ollama.ai-agent.svc.cluster.local:11434"
```

### Secrets (for API keys)

```bash
# For OpenAI
kubectl create secret generic llm-api-key \
  --from-literal=OPENAI_API_KEY=sk-... \
  -n ai-agent

# For Anthropic
kubectl create secret generic llm-api-key \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-... \
  -n ai-agent
```