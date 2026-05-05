# My LLM Backend

Local FastAPI backend for a personal website that calls OpenRouter while keeping the OpenRouter API key server-side only.

## Setup

Create a `.env` file in this folder:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

Start the backend from the `my-llm-backend` folder:

```powershell
uvicorn app.main:app --reload
```

The local chat website will run at `http://localhost:8000`.

## Test

Open the chat page:

```powershell
curl http://localhost:8000/
```

Health check JSON:

```powershell
curl http://localhost:8000/api/health
```

Check currently working free OpenRouter models:

```powershell
curl http://localhost:8000/api/models/check
```

Optional quick check filters:

```powershell
curl "http://localhost:8000/api/models/check?limit=5"
curl "http://localhost:8000/api/models/check?contains=gemma"
```

List working models from the latest CSV:

```powershell
curl http://localhost:8000/api/models/working
```

Chat:

```powershell
curl -X POST http://localhost:8000/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\":\"What is OFDM in telecommunications? Answer briefly.\"}"
```

Request a specific model:

```powershell
curl -X POST http://localhost:8000/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\":\"Explain OFDM in simple words.\",\"model\":\"google/gemma-3-27b-it:free\",\"temperature\":0.2,\"max_tokens\":500}"
```

## Notes

- The frontend should call this backend, not OpenRouter directly.
- The OpenRouter API key is loaded only from `.env` on the server.
- Free model status is saved to `data/openrouter_free_model_status.csv`.
- If a selected chat model is unavailable or rate-limited, the backend tries the next working model from the latest model check.
