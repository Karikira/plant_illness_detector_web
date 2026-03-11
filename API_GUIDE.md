# API Guide for Plant Disease Detector Backend

This document explains how the FastAPI backend is structured, how to
add or modify endpoints, and what the expected request and response formats
are. It also includes tips on testing and working with Supabase.

---

## 🚀 Getting Started

1. **Run the server** from the project root:
   ```powershell
   uvicorn main:app --reload
   ```
   - This launches FastAPI on `http://localhost:8000` by default.
   - You can visit `http://localhost:8000/docs` in a browser to see
     the automatically generated OpenAPI (swagger) UI.

2. **Set up environment variables**
   - Create a `.env` file with at least:
     ```text
     SUPABASE_URL=https://your-project.supabase.co
     SUPABASE_KEY=your-anon-or-service-key
     OPENAI_API_KEY=sk-xxx           # used by the AI agent
     AI_MODEL_NAME=gpt-4o-mini       # optional override for the agent model
     ```
   - The server loads these at startup (via `python-dotenv`).
   - Note: the backend no longer requires TensorFlow; the ML model is
     only used during training and is not loaded at runtime.

3. **Install dependencies** (one‑time):
   ```powershell
   pip install -r requirements.txt
   ```

---

## 📁 Application Structure

- `main.py` - single FastAPI application containing all endpoints and
  Supabase/AI logic.
- `database.py` - optional raw psycopg2 helper, not required for the typical
  flow.
- `model/` - machine learning assets (training scripts, weights) which
  aren’t loaded by the API itself.
- `utils/` - image preprocessing helpers.

All HTTP routes are defined as Python functions decorated with `@app.get`,
`@app.post`, etc.

---

## 🔧 Adding / Modifying Endpoints

1. **Choose HTTP method & path**
   - Common methods: `GET` (read), `POST` (create), `PUT`/`PATCH` (update),
     `DELETE` (remove).
   - Path should be descriptive, e.g. `/detections`, `/config/{key}`.

2. **Define request model (optional but recommended)**
   ```python
   class MyData(BaseModel):
       field1: str
       field2: int
   ```
   - Use Pydantic models for automatic validation and documentation.

3. **Write handler function**
   ```python
   @app.post("/myendpoint")
   def my_endpoint(data: MyData):
       # use supabase client or other logic
       return {"status": "ok", "data": data}
   ```
   - For file uploads use `UploadFile` and `File(...)` as parameters.
   - For query/path parameters simply add them as function args.

4. **Use Supabase client for database operations**
   All queries return a response object with `.data` and `.error` fields.
   Example:
   ```python
   resp = supabase.table("users").select("*")\
                 .eq("email", email).single().execute()
   if resp.error:
       raise HTTPException(status_code=500, detail=resp.error.message)
   return resp.data
   ```

5. **Return values**
   - FastAPI automatically converts dictionaries and Pydantic models to
     JSON.
   - Use `HTTPException` to send error responses, e.g. `HTTPException(401,
     "Invalid credentials")`.
   - The `@app` decorators can take additional metadata (e.g. `response_model`)
     for documentation.

---

## 🧪 Testing Endpoints

- Use **curl**, **Postman**, or the `/docs` UI.
- Example curl commands:
  ```bash
  curl -X POST http://localhost:8000/register \
       -H "Content-Type: application/json" \
       -d '{"display_name":"Alice","email":"alice@example.com","password":"secret"}'

  curl http://localhost:8000/history/123e4567-e89b-12d3-a456-426614174000
  ```
- Inspect Supabase dashboard to confirm the database state.

---

## ✅ Existing Endpoints (all in `main.py`)

| Method | Path                     | Description |
|--------|--------------------------|-------------|
| POST   | `/register`              | create a new user (`display_name`, `email`, `password`) |
| POST   | `/login`                 | authenticate user |
| POST   | `/detections`            | add detection record |
| GET    | `/history/{user_id}`     | fetch user’s detection history |
| POST   | `/activity`              | log an admin/activity event |
| GET    | `/config/{key}`          | read a configuration value |
| POST   | `/config`                | upsert configuration |
| POST   | `/predict`               | upload image for AI analysis |

---

## ⚠️ Best Practices

- **Validate input** using Pydantic models.
- **Check `.error`** on Supabase responses and handle gracefully.
- **Avoid hard-coded credentials**; always use environment variables.
- **Enable Row-Level Security (RLS)** in production and create policies to
  protect tables.
- **Use HTTPS** and authenticate mobile clients either with Supabase
  Auth or a custom token mechanism.

---

## 🛠 Helpful Tips

- Auto-generated docs are available at `/docs` (Swagger) and `/redoc`.
- You can define request/response models to make these docs more
  expressive.
- For long-running tasks (e.g. model training) separate them from the API
  or run in background tasks.

---

With these guidelines you should be able to extend the backend and
integrate it with your mobile application.  If you run into any issues or
need concrete examples for your platform (Android/iOS/Flutter/etc.), just
ask!