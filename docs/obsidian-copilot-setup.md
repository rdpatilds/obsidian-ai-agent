# Obsidian Copilot Integration Guide

This guide explains how to connect Obsidian Copilot to your custom FastAPI agent, enabling AI-powered features with custom tools (like calculator, web search, etc.) directly in your Obsidian note-taking workflow.

## Prerequisites

1. **Obsidian** installed on your system ([Download here](https://obsidian.md/))
2. **Obsidian Copilot plugin** installed in Obsidian
   - Open Obsidian → Settings → Community Plugins → Browse
   - Search for "Copilot" and install
3. **FastAPI agent** running locally (this server)

## Step-by-Step Configuration

### 1. Start the FastAPI Server

First, ensure your FastAPI agent is running:

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8030 --reload
```

You should see log output indicating the server started successfully, including:
```
cors_middleware_enabled origins=['http://localhost', 'http://127.0.0.1', 'app://obsidian.md']
```

### 2. Configure Environment Variables

Ensure your `.env` file has CORS enabled (this is the default):

```bash
# CORS Configuration
CORS_ENABLED=true
CORS_ORIGINS=http://localhost,http://127.0.0.1,app://obsidian.md
CORS_ALLOW_CREDENTIALS=true
```

### 3. Open Obsidian Copilot Settings

1. Open Obsidian
2. Go to **Settings** (gear icon in the bottom left)
3. Navigate to **Community plugins** → **Copilot**
4. Scroll down to the **Model Configuration** section

### 4. Add Custom Model Provider

1. Click **"Add Custom Model"** or **"Add Model"** button
2. Fill in the following fields:

   | Field | Value | Description |
   |-------|-------|-------------|
   | **Provider** | `3rd party (OpenAI format)` | Select this option from dropdown |
   | **Base URL** | `http://localhost:8030/v1` | Your local FastAPI endpoint |
   | **API Key** | `dev-key-change-in-production` | Value from your `.env` file (`OPENAI_COMPATIBLE_API_KEY`) |
   | **Model Name** | `gpt-4o-mini` | Value from your `.env` file (`MODEL_NAME`) |
   | **Enable CORS** | ✅ Checked | **REQUIRED** for browser-based clients |
   | **Enable Streaming** | ❌ Unchecked | **NOT SUPPORTED** with CORS (see Known Limitations) |

3. Click **"Save"** or **"Apply"** to save the configuration

### 5. Test the Connection

1. Open a note in Obsidian
2. Select some text or position your cursor
3. Open the Copilot chat panel (usually via command palette: `Cmd/Ctrl+P` → "Copilot: Open chat")
4. Send a test message:
   ```
   Calculate 42 * 137
   ```
5. The agent should respond using the calculator tool

**Expected behavior:**
- The agent processes your request
- For math calculations, it uses the calculator tool
- You see a properly formatted response in the chat panel

## Known Limitations

### No Streaming Support with CORS

**Important:** Obsidian Copilot does **not support streaming** when CORS is enabled.

- **Streaming disabled:** Responses are returned all at once after processing completes
- **Why:** Browser CORS security restrictions prevent streaming responses from custom origins
- **Impact:** You may experience slightly longer wait times for responses, but functionality is unchanged

**Configuration:** Ensure "Enable Streaming" is **UNCHECKED** in your Obsidian Copilot settings.

### Browser Security Restrictions

The integration uses CORS (Cross-Origin Resource Sharing) to enable communication between Obsidian's Electron environment and your local server. This requires:
- CORS middleware enabled in the FastAPI server (configured by default)
- `app://obsidian.md` included in allowed origins
- Credentials (Authorization headers) enabled for API key authentication

## Troubleshooting

### CORS Error: "Access to fetch blocked by CORS policy"

**Symptom:** Error message in Obsidian Developer Tools console (Help → Toggle Developer Tools)

**Solution:**
1. Verify `CORS_ENABLED=true` in your `.env` file
2. Ensure `CORS_ORIGINS` includes `app://obsidian.md`
3. Restart the FastAPI server after changing `.env`
4. Verify the server logs show: `cors_middleware_enabled`

### 401 Unauthorized Error

**Symptom:** Copilot shows "Unauthorized" or "API key invalid" error

**Solution:**
1. Check the **API Key** in Obsidian Copilot settings matches your `.env` file
   - Open `.env` and find `OPENAI_COMPATIBLE_API_KEY` value
   - Copy this exact value to Copilot's "API Key" field
2. Ensure "Enable CORS" is checked in Copilot settings (required for Authorization header)
3. Verify the server logs show authentication events (`authentication_successful`)

### Connection Refused Error

**Symptom:** Copilot shows "Connection refused" or "Cannot connect to server"

**Solution:**
1. Verify the FastAPI server is running:
   ```bash
   curl http://localhost:8030/health
   ```
   Expected response: `{"status": "healthy", ...}`
2. Check the **Base URL** in Copilot settings is correct: `http://localhost:8030/v1`
   - Note the `/v1` path is **required**
3. Ensure the port matches your configuration (default: 8030)
4. Check firewall settings aren't blocking local connections

### Model Not Found Error

**Symptom:** Copilot shows "Model not found" or similar error

**Solution:**
1. Check the **Model Name** in Copilot settings matches your `.env` file
   - Open `.env` and find `MODEL_NAME` value (e.g., `openai:gpt-4o-mini`)
   - For Obsidian Copilot, use the model name **without** the provider prefix: `gpt-4o-mini`
2. If using a different model provider (Anthropic, Ollama, etc.), update the model name accordingly

### Slow Response Times

**Symptom:** Responses take longer than expected

**Possible causes:**
1. **Streaming disabled:** Without streaming, you wait for the complete response (this is expected with CORS)
2. **Tool execution:** Tools like calculator or web search add processing time
3. **Model latency:** OpenAI API response time varies by load and model

**Tips:**
- Check server logs for `duration_ms` fields to identify bottlenecks
- Use faster models (e.g., `gpt-4o-mini` instead of `gpt-4`)
- Consider tools are executing (look for `tool_execution_started` logs)

## Testing with curl

You can test the integration manually using curl before configuring Obsidian:

### Test Health Endpoint

```bash
curl http://localhost:8030/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "components": {
    "agent": true
  }
}
```

### Test CORS Preflight Request

```bash
curl -X OPTIONS http://localhost:8030/v1/chat/completions \
  -H "Origin: app://obsidian.md" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Authorization,Content-Type" \
  -v
```

**Expected headers in response:**
```
Access-Control-Allow-Origin: app://obsidian.md
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Authorization, Content-Type
```

### Test Chat Completions Endpoint

```bash
curl -X POST http://localhost:8030/v1/chat/completions \
  -H "Origin: app://obsidian.md" \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Calculate 42 * 137"}],
    "stream": false
  }' \
  -v
```

**Expected response:**
- Status: `200 OK`
- CORS headers present (as above)
- JSON response with OpenAI-compatible format:
  ```json
  {
    "id": "...",
    "object": "chat.completion",
    "model": "gpt-4o-mini",
    "choices": [{
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "..."
      },
      "finish_reason": "stop"
    }]
  }
  ```

## Advanced Configuration

### Using HTTPS in Production

For production deployments, use HTTPS to ensure secure communication:

1. Set up a reverse proxy (nginx, Caddy, Traefik) with SSL/TLS
2. Update `CORS_ORIGINS` to include your HTTPS domain:
   ```bash
   CORS_ORIGINS=https://your-domain.com,app://obsidian.md
   ```
3. Update Obsidian Copilot's **Base URL** to your HTTPS endpoint

### Multiple Origins for Development

If you're testing from multiple sources (browser, Obsidian, mobile), add all origins:

```bash
CORS_ORIGINS=http://localhost,http://127.0.0.1,app://obsidian.md,http://192.168.1.100:8030
```

### Disabling CORS

If you're not using browser-based clients, you can disable CORS:

```bash
CORS_ENABLED=false
```

**Note:** Obsidian Copilot requires CORS enabled to function.

## Additional Resources

- [Obsidian Copilot Documentation](https://www.obsidiancopilot.com/en/docs/settings)
- [Obsidian Copilot GitHub Repository](https://github.com/logancyang/obsidian-copilot)
- [FastAPI CORS Documentation](https://fastapi.tiangolo.com/tutorial/cors/)
- [MDN Web Docs - CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)

## Support

If you encounter issues not covered in this guide:

1. Check the FastAPI server logs for detailed error messages
   - Look for `correlation_id` to trace requests
   - Check `event` field for error types
2. Enable Obsidian Developer Tools (Help → Toggle Developer Tools)
   - Check Console tab for JavaScript errors
   - Check Network tab for failed requests
3. Review your `.env` configuration for typos or missing values

## Example Workflow

Once configured, here's a typical workflow:

1. **Open Obsidian** and create a new note
2. **Ask a question** in Copilot chat:
   ```
   What's the square root of 144?
   ```
3. **Agent responds** using the calculator tool:
   ```
   The square root of 144 is 12.
   ```
4. **Ask follow-up questions** or request other tool usage:
   ```
   Calculate 12 * 12 to verify
   ```

The agent will use tools as needed and provide context-aware responses integrated with your note-taking workflow.
