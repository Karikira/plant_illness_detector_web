# flake8: noqa: E302,E501
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import bcrypt
import os
from dotenv import load_dotenv
from supabase import create_client
from typing import Any
import json
import time
from postgrest.exceptions import APIError

# AI/agent imports
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai import ImageUrl
import base64

# load environment variables from .env file
load_dotenv()

app = FastAPI()

# region agent log
def _dbg(hypothesis_id: str, location: str, message: str, data: dict | None = None, run_id: str = "pre-fix") -> None:
    try:
        with open("debug-fff9b8.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "sessionId": "fff9b8",
                "runId": run_id,
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data or {},
                "timestamp": int(time.time() * 1000),
            }) + "\n")
    except Exception:
        pass
# endregion

# region agent log
try:
    import sys
    try:
        import jinja2 as _jinja2  # type: ignore
        _dbg("H2", "main.py:jinja2_check", "jinja2_import_ok", {"version": getattr(_jinja2, "__version__", None), "executable": sys.executable})
    except Exception as e:
        _dbg("H2", "main.py:jinja2_check", "jinja2_import_failed", {"error": str(e), "executable": sys.executable})
except Exception:
    pass
# endregion

templates = Jinja2Templates(directory="templates")

_dbg(
    "H1",
    "main.py:startup",
    "app_startup",
    {
        "has_root_route": any(getattr(r, "path", None) == "/" for r in app.routes),
        "route_paths": [getattr(r, "path", None) for r in app.routes if getattr(r, "path", None)],
        "templates_dir_exists": os.path.isdir("templates"),
    },
)


# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- SUPABASE ----------------
# use environment variables for credentials; make sure you have a .env file or
# set these in your hosting environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- APP SETTINGS ----------------
ADMIN_EMAIL = (os.getenv("ADMIN_EMAIL") or "").strip().lower()

# ---------------- AI AGENT ----------------
# model choice and prompt replicated from app.py
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "gpt-4o-mini")
model_agent = OpenAIModel(AI_MODEL_NAME)

agent = Agent(
    model=model_agent,
    system_prompt="""
You are an agricultural plant disease expert.

Analyze the uploaded plant leaf image and identify the disease.

Tasks:
1. Identify the plant name.
2. Identify the illness or disease affecting the plant.
3. Provide a short treatment recommendation.
4. Provide a short prevention method to avoid the disease.

If the plant is healthy, set:
illness: "Healthy"

Return ONLY valid JSON in the following format:

{
"name": "plant name",
"illness": "disease name or Healthy",
"treatment": "recommended treatment",
"prevention": "how to prevent the disease"
}

Do not include explanations, notes, or extra text.
Only return JSON.
"""

)


# ---------------- AUTH MODELS ----------------
class RegisterData(BaseModel):
    # Supabase table schema appears to use `name` (not `display_name`)
    # Keep `display_name` to match client naming, but write to `name` column.
    display_name: str
    email: str
    password: str


class LoginData(BaseModel):
    email: str
    password: str


# ---------------- REGISTER ----------------
@app.post("/register")
def register(data: RegisterData):
    password_hash = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()

    try:
        resp: Any = supabase.table("users").insert({
            "display_name": data.display_name,
            "email": data.email,
            "password_hash": password_hash
        }).execute()
        if getattr(resp, "error", None):
            raise HTTPException(status_code=500, detail=str(resp.error))
    except APIError as e:
        _dbg("H6", "main.py:register", "register_api_error", {"error": str(e)[:1000]})
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        _dbg("H6", "main.py:register", "register_exception", {"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Registration successful"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    _dbg("H1", "main.py:home", "home_route_hit", {"path": str(request.url.path)})
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    _dbg("H3", "main.py:dashboard", "dashboard_route_hit", {"path": str(request.url.path)})
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})


@app.get("/analysis", response_class=HTMLResponse)
def analysis_page(request: Request):
    return templates.TemplateResponse("analysis.html", {"request": request})


@app.get("/results", response_class=HTMLResponse)
def results_page(request: Request):
    return templates.TemplateResponse("results.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/favicon.ico")
def favicon():
    # avoid noisy 404s in logs; real icon can be added later
    return Response(status_code=204)


# ---------------- LOGIN ----------------
@app.post("/login")
def login(data: LoginData):
    # region agent log
    _dbg("H4", "main.py:login", "login_attempt", {"email": data.email})
    # endregion
    try:
        response: Any = supabase.table("users").select("*").eq("email", data.email).execute()
        # region agent log
        _dbg(
            "H4",
            "main.py:login",
            "login_supabase_response",
            {
                "has_data": bool(getattr(response, "data", None)),
                "data_type": str(type(getattr(response, "data", None))),
                "data_len": len(getattr(response, "data", []) or []) if isinstance(getattr(response, "data", None), list) else None,
                "has_error_attr": hasattr(response, "error"),
                "error_str": str(getattr(response, "error", None))[:200] if hasattr(response, "error") else None,
            },
        )
        # endregion
        user: Any = response.data[0] if response.data else None

        if not user:
            # region agent log
            _dbg("H4", "main.py:login", "login_user_not_found", {"email": data.email})
            # endregion
            raise HTTPException(status_code=401, detail="Invalid credentials")

        stored_hash = user.get("password_hash") if isinstance(user, dict) else None
        ok = bool(stored_hash) and bcrypt.checkpw(data.password.encode(), str(stored_hash).encode())
        # region agent log
        _dbg(
            "H4",
            "main.py:login",
            "login_password_check",
            {"stored_hash_present": bool(stored_hash), "password_ok": ok},
        )
        # endregion

        if not ok:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        is_admin = False
        if ADMIN_EMAIL and isinstance(user, dict):
            is_admin = (str(user.get("email") or "").strip().lower() == ADMIN_EMAIL)

        return {
            "message": "Login successful",
            "is_admin": is_admin,
            "user": {
                "id": user.get("id") if isinstance(user, dict) else None,
                "display_name": (user.get("display_name") or user.get("name")) if isinstance(user, dict) else None,
                "email": user.get("email") if isinstance(user, dict) else None,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        # region agent log
        _dbg("H4", "main.py:login", "login_exception", {"error": str(e)[:300]})
        # endregion
        raise HTTPException(status_code=500, detail="Login failed due to server error")


# helper function to fetch a user by email (used by login, etc.)
def get_user_by_email(email: str):
    resp: Any = supabase.table("users").select("*") \
        .eq("email", email).single().execute()
    if resp.error:
        raise HTTPException(status_code=500, detail=resp.error.message)
    return resp.data


class UpdateProfileData(BaseModel):
    display_name: str | None = None
    email: str | None = None


@app.get("/users/{user_id}")
def get_user(user_id: str):
    resp: Any = supabase.table("users").select("id,display_name,email").eq("id", user_id).single().execute()
    if getattr(resp, "error", None):
        raise HTTPException(status_code=500, detail=str(resp.error))
    return resp.data


@app.put("/users/{user_id}")
def update_user(user_id: str, data: UpdateProfileData):
    update: dict[str, Any] = {}
    if data.display_name is not None:
        update["display_name"] = data.display_name
    if data.email is not None:
        update["email"] = data.email
    if not update:
        return {"status": "ok"}

    try:
        resp: Any = supabase.table("users").update(update).eq("id", user_id).execute()
        if getattr(resp, "error", None):
            raise HTTPException(status_code=500, detail=str(resp.error))
        return {"status": "ok", "user": (resp.data[0] if getattr(resp, "data", None) else None)}
    except APIError as e:
        msg = str(e).lower()
        if "duplicate key" in msg or "already exists" in msg or "unique" in msg:
            raise HTTPException(status_code=409, detail="Email already in use.")
        raise HTTPException(status_code=500, detail="Profile update failed.")


@app.get("/admin/users")
def admin_users():
    # Minimal admin endpoint. In production, protect this with proper auth.
    resp: Any = supabase.table("users").select("id,display_name,email,created_at").order("created_at", desc=True).execute()
    if getattr(resp, "error", None):
        raise HTTPException(status_code=500, detail=str(resp.error))
    return resp.data


@app.get("/admin/stats")
def admin_stats():
    # Simple stats for graphs (counts by illness + daily detections).
    resp: Any = supabase.table("detections").select("created_at,illness").order("created_at", desc=False).execute()
    if getattr(resp, "error", None):
        raise HTTPException(status_code=500, detail=str(resp.error))
    rows = resp.data or []

    by_day: dict[str, int] = {}
    by_illness: dict[str, int] = {}
    for r in rows:
        created_at = str(r.get("created_at") or "")
        day = created_at[:10] if len(created_at) >= 10 else "unknown"
        by_day[day] = by_day.get(day, 0) + 1
        illness = str(r.get("illness") or "Unknown").strip() or "Unknown"
        by_illness[illness] = by_illness.get(illness, 0) + 1

    return {"by_day": by_day, "by_illness": by_illness, "total": len(rows)}


@app.get("/history/{user_id}")
def history(user_id: str):
    try:
        import uuid as _uuid
        _uuid.UUID(user_id)
    except Exception:
        return []
    try:
        resp: Any = supabase.table("detections") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .execute()
        if getattr(resp, "error", None):
            _dbg("H7", "main.py:history", "history_supabase_error", {"error": str(resp.error)})
            raise HTTPException(status_code=500, detail=str(resp.error))
        return resp.data
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        _dbg("H7", "main.py:history", "history_exception", {"error": msg})
        raise HTTPException(status_code=500, detail="Failed to fetch history: " + msg)


@app.post("/activity")
def log_activity(entry: dict):
    resp: Any = supabase.table("activity_logs").insert(entry).execute()
    if resp.error:
        raise HTTPException(status_code=500, detail=resp.error.message)
    return {"status": "ok"}


@app.get("/config/{key}")
def get_config(key: str):
    resp: Any = supabase.table("system_config") \
        .select("value") \
        .eq("key", key) \
        .single() \
        .execute()
    if resp.error:
        raise HTTPException(status_code=500, detail=resp.error.message)
    return resp.data


@app.post("/detections")
def add_detection(item: dict):
    resp: Any = supabase.table("detections").insert(item).execute()
    if resp.error:
        raise HTTPException(status_code=500, detail=resp.error.message)
    return resp.data


@app.post("/config")
def set_config(item: dict):
    resp: Any = supabase.table("system_config").upsert(item).execute()
    if resp.error:
        raise HTTPException(status_code=500, detail=resp.error.message)
    return {"status": "ok"}


# ---------------- AI PREDICT ----------------
@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    # read bytes and convert to data URL
    image_bytes = await file.read()
    encoded_string = base64.b64encode(image_bytes).decode("utf-8")
    image_base64 = f"data:{file.content_type};base64,{encoded_string}"

    # run agent
    agent_any: Any = agent
    result = await agent_any.run(
        "Analyze this plant leaf image and identify the disease.",
        deps={"image": ImageUrl(url=image_base64)},
    )

    return {"result": result.output}


def _normalize_ai_output(output: Any) -> dict[str, Any]:
    if isinstance(output, dict):
        return output
    if isinstance(output, str):
        try:
            parsed = json.loads(output)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {"raw": output}


@app.post("/analyze")
async def analyze_and_save(user_id: str = Form(...), file: UploadFile = File(...)):
    image_bytes = await file.read()
    encoded_string = base64.b64encode(image_bytes).decode("utf-8")
    image_base64 = f"data:{file.content_type};base64,{encoded_string}"

    try:
        agent_any: Any = agent
        result = await agent_any.run(
            "Analyze this plant leaf image and identify the disease.",
            deps={"image": ImageUrl(url=image_base64)},
        )

        output: Any = getattr(result, "output", None)
        normalized = _normalize_ai_output(output)

        detection_payload = {
            "user_id": user_id,
            "image_filename": file.filename,
            "name": normalized.get("name"),
            "illness": normalized.get("illness"),
            "treatment": normalized.get("treatment"),
            "prevention": normalized.get("prevention"),
            "raw_result": normalized,
        }

        resp: Any = supabase.table("detections").insert(detection_payload).execute()
        if getattr(resp, "error", None):
            _dbg("H8", "main.py:analyze", "supabase_insert_error", {"error": str(resp.error)})
            raise HTTPException(status_code=500, detail="Failed to save detection result")

        return {"result": normalized, "detection": resp.data}
    except Exception as e:
        _dbg("H8", "main.py:analyze", "analyze_exception", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Analysis failed: " + str(e))
