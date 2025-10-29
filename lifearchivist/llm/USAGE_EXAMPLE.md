# LLM Provider System - Usage Examples

## Complete Workflow: From Credentials to Generation

### 1. Store Provider Credentials

```python
from redis.asyncio import Redis
from lifearchivist.storage.credential_service import CredentialService
from lifearchivist.llm import ProviderType
from lifearchivist.llm.provider_config import OpenAIConfig, OllamaConfig

# Initialize credential service
redis = Redis.from_url("redis://localhost:6379")
credential_service = CredentialService(redis)

# Store OpenAI credentials
openai_config = OpenAIConfig(
    api_key="sk-...",
    organization="org-...",  # Optional
)

await credential_service.add_provider(
    provider_id="my-openai",
    provider_type=ProviderType.OPENAI,
    config=openai_config,
    is_default=True,
)

# Store Ollama credentials (local, no API key needed)
ollama_config = OllamaConfig(
    base_url="http://localhost:11434",
    timeout_seconds=300,
)

await credential_service.add_provider(
    provider_id="my-ollama",
    provider_type=ProviderType.OLLAMA,
    config=ollama_config,
)
```

### 2. Load Providers and Initialize Manager

```python
from lifearchivist.llm import ProviderManagerFactory

# Option A: Load all stored providers automatically (RECOMMENDED)
manager = await ProviderManagerFactory.create_with_stored_providers(
    credential_service=credential_service,
    redis_client=redis,
    enable_cost_tracking=True,
    enable_health_monitoring=True,
)

# Option B: Manual loading
from lifearchivist.llm import ProviderLoader

manager = ProviderManagerFactory.create(redis_client=redis)
await manager.initialize()

loader = ProviderLoader(credential_service)
result = await loader.load_provider("my-openai")
if result.is_success():
    provider = result.unwrap()
    await manager.add_provider(provider, set_as_default=True)
```

### 3. Generate Text

```python
from lifearchivist.llm import LLMMessage

# Simple generation
messages = [
    LLMMessage(role="system", content="You are a helpful assistant."),
    LLMMessage(role="user", content="What is the capital of France?"),
]

result = await manager.generate(
    messages=messages,
    model="gpt-4o-mini",  # Uses default provider
    temperature=0.7,
    max_tokens=500,
)

if result.is_success():
    response = result.unwrap()
    print(f"Response: {response.content}")
    print(f"Tokens used: {response.tokens_used}")
    print(f"Cost: ${response.cost_usd:.4f}")
```

### 4. Streaming Generation

```python
async for chunk in manager.generate_stream(
    messages=messages,
    model="gpt-4o-mini",
    temperature=0.7,
):
    print(chunk.content, end="", flush=True)
    
    if chunk.is_final:
        print(f"\n\nTotal tokens: {chunk.tokens_used}")
```

### 5. Use Specific Provider

```python
# Explicitly use Ollama instead of default
result = await manager.generate(
    messages=messages,
    model="llama3.2:1b",
    provider_id="my-ollama",  # Explicit provider
    temperature=0.7,
)
```

### 6. List Available Models

```python
# List models from default provider
result = await manager.list_models()
if result.is_success():
    models = result.unwrap()
    for model in models:
        print(f"{model.id}: {model.context_window} tokens")
        print(f"  Cost: ${model.cost_per_1k_input:.4f}/1K input")

# List models from specific provider
result = await manager.list_models(provider_id="my-ollama")
```

### 7. Cost Tracking

```python
from lifearchivist.llm import Budget

# Set budget
budget = Budget(
    limit_usd=10.0,
    period="daily",
    user_id="default",
    alert_threshold=0.8,
)
manager.cost_tracker.set_budget(budget)

# Get cost summary
result = await manager.cost_tracker.get_summary(user_id="default")
if result.is_success():
    summary = result.unwrap()
    print(f"Total cost: ${summary.total_cost:.2f}")
    print(f"Total requests: {summary.total_requests}")
    print(f"By provider: {summary.by_provider}")
```

### 8. Provider Management

```python
# List all providers
providers = manager.list_providers()
for p in providers:
    print(f"{p['id']}: {p['type']} (default: {p['is_default']})")

# Change default provider
manager.set_default_provider("my-ollama")

# Remove provider
await manager.remove_provider("my-openai")
```

### 9. Cleanup

```python
# Shutdown manager (cleans up all providers)
await manager.shutdown()

# Or use context manager (automatic cleanup)
async with manager:
    # Use manager
    result = await manager.generate(...)
# Automatically cleaned up
```

## Application Startup Pattern

```python
# In your application startup (e.g., FastAPI lifespan)
from contextlib import asynccontextmanager
from fastapi import FastAPI
from redis.asyncio import Redis
from lifearchivist.storage.credential_service import CredentialService
from lifearchivist.llm import ProviderManagerFactory

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    redis = Redis.from_url("redis://localhost:6379")
    credential_service = CredentialService(redis)
    
    # Create and initialize manager with stored providers
    manager = await ProviderManagerFactory.create_with_stored_providers(
        credential_service=credential_service,
        redis_client=redis,
    )
    
    # Store in app state
    app.state.llm_manager = manager
    
    yield
    
    # Shutdown
    await manager.shutdown()
    await redis.close()

app = FastAPI(lifespan=lifespan)

# Use in endpoints
@app.post("/api/chat")
async def chat(request: ChatRequest):
    manager = request.app.state.llm_manager
    result = await manager.generate(...)
    return result.unwrap()
```

## Error Handling

```python
from lifearchivist.utils.result import Result

result = await manager.generate(messages=messages, model="gpt-4o-mini")

if result.is_success():
    response = result.unwrap()
    # Use response
else:
    # Handle error
    print(f"Error: {result.error}")
    print(f"Type: {result.error_type}")
    print(f"Status: {result.status_code}")
    print(f"Context: {result.context}")
```

## Adding New Provider at Runtime

```python
from lifearchivist.llm.provider_config import AnthropicConfig

# Create config
config = AnthropicConfig(
    api_key="sk-ant-...",
)

# Store credentials
await credential_service.add_provider(
    provider_id="my-anthropic",
    provider_type=ProviderType.ANTHROPIC,
    config=config,
)

# Load and add to manager
loader = ProviderLoader(credential_service)
result = await loader.load_provider("my-anthropic")
if result.is_success():
    provider = result.unwrap()
    await manager.add_provider(provider)
```

## Validation Before Saving

```python
from lifearchivist.llm import ProviderLoader

loader = ProviderLoader(credential_service)

# Validate config before saving
config_dict = {
    "api_key": "sk-...",
    "base_url": "https://api.openai.com/v1",
}

result = loader.validate_config(ProviderType.OPENAI, config_dict)
if result.is_success():
    # Config is valid, safe to save
    config = result.unwrap()
    await credential_service.add_provider(...)
else:
    # Invalid config
    print(f"Validation failed: {result.error}")
```
