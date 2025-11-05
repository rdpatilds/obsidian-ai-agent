# Research Report: Obsidian Copilot OpenAI-Compatible API Integration

**Date**: 2025-11-05
**Research Focus**: Understanding Obsidian Copilot's OpenAI API integration requirements
**Repository Analyzed**: [logancyang/obsidian-copilot](https://github.com/logancyang/obsidian-copilot)

---

## Executive Summary

Obsidian Copilot uses **LangChain's ChatOpenAI** wrapper with the official **OpenAI Node.js SDK** to communicate with LLM providers. The plugin expects standard OpenAI-compatible endpoints and **automatically appends `/chat/completions`** to the configured baseURL. Message content supports both string and array formats, but the plugin normalizes array content to strings before downstream processing.

---

## 1. Message Content Format Discovery

### 1.1 Content Format Variations

The OpenAI Chat Completions API supports **two content formats**:

#### **Text-Only (String Format)**
```json
{
  "role": "user",
  "content": "Hello, how are you?"
}
```

#### **Multimodal (Array Format)**
```json
{
  "role": "user",
  "content": [
    {
      "type": "text",
      "text": "Describe this picture:"
    },
    {
      "type": "image_url",
      "image_url": {
        "url": "https://example.com/image.jpg"
      }
    }
  ]
}
```

### 1.2 Obsidian Copilot's Content Normalization

**Source**: `src/LLMProviders/ChatOpenRouter.ts`

The plugin **normalizes array content to strings** using the `extractDeltaContent()` method:

```typescript
if (Array.isArray(content)) {
  return content.map(part => {
    if (typeof part === "string") return part;
    if (part && typeof part === "object" && typeof part.text === "string")
      return part.text;
  }).join("");
}
```

**Key Findings**:
- Array content is flattened to plain text strings
- Only the `text` property is extracted from objects
- Image URLs are ignored during normalization
- **Implication**: Our implementation should support both formats but can normalize to strings

### 1.3 Message Construction Pattern

**Source**: `src/LLMProviders/chainRunner/LLMChainRunner.ts`

Messages follow a **layered architecture** through `constructMessages()`:

```typescript
// Layer 1: System message
const systemMessage = extractSystemMessage(contextEnvelope);

// Layer 2-3-5: User message (multimodal support)
const userMessage = mergeUserContent(contextEnvelope);

// Layer 4: Chat history
const chatHistory = loadHistoryFromMemory();

// Final structure
const messages = [systemMessage, ...chatHistory, userMessage];
```

**Pattern**: `[system, ...history, user]`

---

## 2. Endpoint Path Construction

### 2.1 OpenAI SDK Automatic Path Appending

**Source**: OpenAI SDK behavior (verified via LiteLLM and LM Studio documentation)

The OpenAI SDK **automatically appends `/chat/completions`** to the baseURL:

```typescript
const client = new OpenAI({
  apiKey: "sk-xxx",
  baseURL: "http://localhost:8123/v1"  // ← User configuration
});

// SDK makes request to:
// http://localhost:8123/v1/chat/completions
//                           ^^^^^^^^^^^^^^^^^^^ (automatically added)
```

### 2.2 User Configuration in Obsidian Copilot

**Source**: `src/LLMProviders/chatModelManager.ts`

```typescript
[ChatModelProviders.OPENAI]: {
  modelName: modelName,
  apiKey: await getDecryptedKey(customModel.apiKey || settings.openAIApiKey),
  configuration: {
    baseURL: customModel.baseUrl,  // ← From user settings
    fetch: customModel.enableCors ? safeFetch : undefined,
    organization: await getDecryptedKey(customModel.openAIOrgId || settings.openAIOrgId),
  }
}
```

**User Settings Model** (`src/aiParams.ts`):

```typescript
interface CustomModel {
  provider: string;
  baseUrl: string;  // ← Users enter this in settings UI
  apiKey: string;
  enableCors: boolean;
  // ...other fields
}
```

### 2.3 Recommended Configuration for Paddy

| User Enters in Obsidian Settings | Final URL Constructed by SDK |
|----------------------------------|------------------------------|
| `http://localhost:8123/v1`       | `http://localhost:8123/v1/chat/completions` |
| `http://localhost:8123`          | `http://localhost:8123/chat/completions` |

**Recommendation**:
- **Implement endpoint at**: `POST /v1/chat/completions`
- **Users configure**: `http://localhost:8123/v1` as baseURL
- **Alternative**: `POST /chat/completions` if users prefer `http://localhost:8123`

### 2.4 Critical Warning from Documentation

> "Do NOT add anything additional to the base url e.g. `/v1/embedding` because the OpenAI client automatically adds the relevant endpoints."
> — LiteLLM Documentation

Users should **NEVER** enter `http://localhost:8123/v1/chat/completions` in settings. The SDK will append the path, resulting in:
```
http://localhost:8123/v1/chat/completions/chat/completions ❌
```

---

## 3. Implementation Requirements

### 3.1 Request Schema

Based on OpenAI Chat Completions API and LangChain integration:

```python
from pydantic import BaseModel, Field
from typing import Literal, Union

class Message(BaseModel):
    """Single message in chat history."""
    role: Literal["system", "user", "assistant", "tool"]
    content: Union[str, list[dict[str, Any]]]  # Support both formats
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None

class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""
    model: str
    messages: list[Message]
    temperature: float | None = Field(default=1.0, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    stream: bool = False
    top_p: float | None = Field(default=1.0, ge=0, le=1)
    frequency_penalty: float | None = Field(default=0, ge=-2, le=2)
    presence_penalty: float | None = Field(default=0, ge=-2, le=2)
    stop: str | list[str] | None = None
    n: int = Field(default=1, ge=1)
```

### 3.2 Content Normalization Strategy

Since Obsidian Copilot normalizes array content to strings, we should implement a **Pydantic validator**:

```python
from pydantic import field_validator

class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Union[str, list[dict[str, Any]]]

    @field_validator("content")
    @classmethod
    def normalize_content(cls, v: Union[str, list]) -> str:
        """Normalize array content to string format."""
        if isinstance(v, str):
            return v

        # Extract text from array format
        text_parts = []
        for item in v:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                text_parts.append(item["text"])

        return " ".join(text_parts)
```

### 3.3 Response Schema

```python
class Choice(BaseModel):
    """Single completion choice."""
    index: int
    message: Message
    finish_reason: Literal["stop", "length", "tool_calls"] | None

class Usage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:29]}")
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[Choice]
    usage: Usage
```

### 3.4 Streaming Response Schema

For streaming endpoints, use **Server-Sent Events (SSE)** format:

```python
class ChoiceDelta(BaseModel):
    """Delta content for streaming."""
    index: int
    delta: dict[str, Any]  # {"role": "assistant", "content": "text"}
    finish_reason: Literal["stop", "length"] | None = None

class ChatCompletionChunk(BaseModel):
    """Streaming chunk."""
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChoiceDelta]
```

**SSE Format**:
```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1234567890,"model":"claude-sonnet-4-0","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: [DONE]
```

---

## 4. Pydantic AI Conversion Layer

### 4.1 Request Conversion

```python
from pydantic_ai import Agent

async def convert_to_pydantic_ai(
    request: ChatCompletionRequest
) -> tuple[str, list[dict]]:
    """Convert OpenAI request to Pydantic AI format.

    Returns:
        (user_prompt, chat_history)
    """
    messages = request.messages

    # Extract system message (if present)
    system_message = next(
        (m.content for m in messages if m.role == "system"),
        None
    )

    # Extract chat history (all messages except last user message)
    history = []
    for msg in messages[:-1]:
        if msg.role != "system":
            history.append({
                "role": msg.role,
                "content": msg.content if isinstance(msg.content, str) else normalize_content(msg.content)
            })

    # Last user message becomes the prompt
    user_prompt = messages[-1].content
    if isinstance(user_prompt, list):
        user_prompt = normalize_content(user_prompt)

    return user_prompt, history
```

### 4.2 Response Conversion

```python
from pydantic_ai import RunResult

async def convert_to_openai_response(
    result: RunResult,
    request: ChatCompletionRequest
) -> ChatCompletionResponse:
    """Convert Pydantic AI result to OpenAI format."""
    return ChatCompletionResponse(
        model=request.model,
        choices=[
            Choice(
                index=0,
                message=Message(
                    role="assistant",
                    content=result.output
                ),
                finish_reason="stop"
            )
        ],
        usage=Usage(
            prompt_tokens=result.usage().input_tokens,
            completion_tokens=result.usage().output_tokens,
            total_tokens=result.usage().total_tokens
        )
    )
```

---

## 5. Code Examples from Obsidian Copilot

### 5.1 Message Transformation

**File**: `src/LLMProviders/ChatOpenRouter.ts:L123-L145`

```typescript
protected toOpenRouterMessages(messages: BaseMessage[]): MessageType[] {
  return messages.map((msg) => {
    // Tool messages
    if (msg.role === "tool") {
      return {
        role: "tool",
        content: msg.content,
        tool_call_id: msg.toolCallId,
      };
    }

    // Function call messages
    if (msg.additional_kwargs?.function_call) {
      return {
        role: msg.role === "human" ? "user" : "assistant",
        content: msg.content,
        function_call: msg.additional_kwargs.function_call,
      };
    }

    // Standard messages
    return {
      role: msg.role === "human" ? "user" : "assistant",
      content: msg.content,
    };
  });
}
```

### 5.2 OpenAI Client Initialization

**File**: `src/LLMProviders/ChatOpenRouter.ts:L50-L59`

```typescript
this.openaiClient = new OpenAI({
  apiKey: fields.apiKey,
  baseURL: fields.configuration?.baseURL || "https://openrouter.ai/api/v1",
  defaultHeaders: fields.configuration?.defaultHeaders,
  fetch: fields.configuration?.fetch,
  dangerouslyAllowBrowser: true
});
```

### 5.3 Chat Model Invocation

**File**: `src/LLMProviders/chainRunner/LLMChainRunner.ts:L78-L82`

```typescript
const chatStream = await withSuppressedTokenWarnings(() =>
  this.chainManager.chatModelManager.getChatModel().stream(messages, {
    signal: abortController.signal,
  })
);
```

---

## 6. Implementation Checklist

### ✅ Must Implement

- [ ] **Endpoint**: `POST /v1/chat/completions`
- [ ] **Request Model**: `ChatCompletionRequest` with `messages: list[Message]`
- [ ] **Message Content**: Support both `string` and `list[dict]` formats with normalization
- [ ] **Response Model**: `ChatCompletionResponse` with `choices`, `usage`, `id`, `created`
- [ ] **Streaming**: Optional SSE streaming with `stream=true` parameter
- [ ] **Model Parameter**: Accept but can ignore (use our configured model)
- [ ] **Temperature/Top-P**: Pass through to Pydantic AI if supported
- [ ] **Error Handling**: Return OpenAI-compatible error format

### ⚠️ Nice to Have

- [ ] **Authentication**: Bearer token validation (API key)
- [ ] **Multiple Choices**: Support `n > 1` parameter
- [ ] **Stop Sequences**: Support custom stop sequences
- [ ] **Tool Calls**: Support function calling format (future)

### ❌ Not Required

- ❌ Image processing (Copilot normalizes to text)
- ❌ Token counting endpoint (`/v1/models`)
- ❌ Embeddings endpoint

---

## 7. User Configuration Guide

### For Obsidian Copilot Users

1. **Install Paddy API** (our FastAPI service)
2. **Start the server**: `uv run uvicorn app.main:app --reload --port 8123`
3. **Open Obsidian Settings** → Copilot → Custom Models
4. **Configure Custom Model**:
   - **Name**: `Paddy Agent`
   - **Provider**: Select "OpenAI"
   - **Base URL**: `http://localhost:8123/v1`
   - **API Key**: Your configured API key
   - **Model Name**: `claude-sonnet-4-0` (or any string)

### Base URL Examples

| Configuration | Final Endpoint |
|---------------|----------------|
| `http://localhost:8123/v1` | `http://localhost:8123/v1/chat/completions` ✅ |
| `http://localhost:8123` | `http://localhost:8123/chat/completions` ✅ |
| ~~`http://localhost:8123/v1/chat/completions`~~ | ~~`http://localhost:8123/v1/chat/completions/chat/completions`~~ ❌ |

---

## 8. References

### Source Code Analyzed
- [ChatOpenRouter.ts](https://github.com/logancyang/obsidian-copilot/blob/master/src/LLMProviders/ChatOpenRouter.ts) - Message normalization
- [chatModelManager.ts](https://github.com/logancyang/obsidian-copilot/blob/master/src/LLMProviders/chatModelManager.ts) - Model instantiation
- [LLMChainRunner.ts](https://github.com/logancyang/obsidian-copilot/blob/master/src/LLMProviders/chainRunner/LLMChainRunner.ts) - Message construction
- [aiParams.ts](https://github.com/logancyang/obsidian-copilot/blob/master/src/aiParams.ts) - Configuration types

### Documentation References
- [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create)
- [LangChain ChatOpenAI](https://js.langchain.com/docs/integrations/chat/openai)
- [LiteLLM OpenAI-Compatible Endpoints](https://docs.litellm.ai/docs/providers/openai_compatible)
- [LM Studio OpenAI Compatibility](https://lmstudio.ai/docs/api/openai-api)

---

## 9. Next Steps

1. **Create Pydantic models** for OpenAI request/response schemas
2. **Implement `/v1/chat/completions` endpoint** in `app/agent/routes.py`
3. **Add conversion layer** between OpenAI format ↔ Pydantic AI format
4. **Test with Obsidian Copilot** using custom model configuration
5. **Add streaming support** for better UX (optional but recommended)
6. **Document user configuration** in README

---

**Report Generated**: 2025-11-05
**Researcher**: Claude (Sonnet 4.5)
**Status**: ✅ Ready for Implementation
