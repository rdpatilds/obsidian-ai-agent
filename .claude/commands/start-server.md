# Start Server

Start the FastAPI development server with hot reload.

## Instructions

- Ensure dependencies are installed (if not, run `uv sync`)
- Start the server in the background so you can continue working
- Verify the server starts successfully by checking logs
- Test the health endpoint

## Run

- Start server in background: `uv run uvicorn src.main:app --host 0.0.0.0 --port 8030 --reload`
- Wait 2-3 seconds for startup
- Test health endpoint: `curl http://localhost:8030/health`
- Test root endpoint: `curl http://localhost:8030/`

## Report

- Confirm server is running on `http://localhost:8030`
- Show the health check response
- Mention: "Server logs will show structured logging with correlation IDs for each request"
- Remind: "Stop server with Ctrl+C or kill the process when done"
