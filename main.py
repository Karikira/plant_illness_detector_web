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
from pydantic_ai import ImageUrl
import base64

# optional Groq model support, fallback to OpenAI
try:
    from pydantic_ai.models.groq import GroqModel
except Exception:
    GroqModel = None
try:
    from pydantic_ai.models.openai import OpenAIModel
except Exception:
    OpenAIModel = None

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
AI_PROVIDER = (os.getenv("AI_PROVIDER") or "GROQ").strip().upper()
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "meta-llama/llama-4-scout-17b")
AI_API_KEY = os.getenv("AI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Support API key forwarding from common env var names.
if not AI_API_KEY:
    AI_API_KEY = OPENAI_API_KEY or GROQ_API_KEY

if AI_PROVIDER == "GROQ":
    if GroqModel is None:
        raise RuntimeError("GroqModel unavailable. Install pydantic-ai-slim[groq] and restart.")
    groq_key = GROQ_API_KEY or AI_API_KEY
    if not groq_key:
        raise RuntimeError("GROQ_API_KEY must be set for Groq provider.")
    os.environ["GROQ_API_KEY"] = groq_key
    model_agent = GroqModel(AI_MODEL_NAME)
elif AI_PROVIDER == "OPENAI":
    if OpenAIModel is None:
        raise RuntimeError("OpenAIModel unavailable. Install openai and pydantic-ai.")
    openai_key = OPENAI_API_KEY or AI_API_KEY
    if not openai_key:
        raise RuntimeError("OPENAI_API_KEY must be set for OpenAI provider.")
    os.environ["OPENAI_API_KEY"] = openai_key
    model_agent = OpenAIModel(AI_MODEL_NAME)
else:
    raise RuntimeError(f"Unsupported AI_PROVIDER: {AI_PROVIDER}. Use OPENAI or GROQ.")

agent = Agent(
    model=model_agent,
    system_prompt="""
You are an agricultural plant disease expert.

Analyze the uploaded plant leaf image and identify the disease.

Return ONLY valid JSON with these keys: name, illness, treatment, prevention.
Use short phrases and no extra text.

If healthy, illness should be "Healthy".

Example:
{"name":"tomato","illness":"early blight","treatment":"remove infected leaves and apply fungicide","prevention":"rotate crops and avoid overhead watering"}
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
    nickname: str | None = None
    email: str | None = None
    address: str | None = None
    password: str | None = None
    profile_picture: str | None = None


@app.get("/users/{user_id}")
def get_user(user_id: str):
    resp: Any = supabase.table("users").select("*").eq("id", user_id).single().execute()
    if getattr(resp, "error", None):
        raise HTTPException(status_code=500, detail=str(resp.error))
    if not resp.data:
        raise HTTPException(status_code=404, detail="User not found")
    user = dict(resp.data)
    user.pop("password_hash", None)
    # .nickname in DB may be optional; keep response stable
    if "nickname" not in user:
        user["nickname"] = user.get("display_name") or user.get("name")
    return user


@app.put("/users/{user_id}")
def update_user(user_id: str, data: UpdateProfileData):
    update: dict[str, Any] = {}
    if data.display_name is not None:
        update["display_name"] = data.display_name
    if data.nickname is not None:
        update["nickname"] = data.nickname
    if data.email is not None:
        update["email"] = data.email
    if data.address is not None:
        update["address"] = data.address
    if data.password is not None:
        update["password_hash"] = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
    if data.profile_picture is not None:
        update["profile_picture"] = data.profile_picture
    if not update:
        return {"status": "ok"}

    try:
        resp: Any = supabase.table("users").update(update).eq("id", user_id).execute()
        if getattr(resp, "error", None):
            raise HTTPException(status_code=500, detail=str(resp.error))
        return {"status": "ok", "user": (resp.data[0] if getattr(resp, "data", None) else None)}
    except APIError as e:
        msg = str(e).lower()
        if "relation \"users\" does not exist" in msg or "column \"nickname\"" in msg:
            # fallback by retrying without nickname column if schema doesn't have it
            if "nickname" in update:
                update.pop("nickname", None)
                try:
                    resp: Any = supabase.table("users").update(update).eq("id", user_id).execute()
                    if getattr(resp, "error", None):
                        raise HTTPException(status_code=500, detail=str(resp.error))
                    return {"status": "ok", "user": (resp.data[0] if getattr(resp, "data", None) else None)}
                except Exception:
                    pass
        if "duplicate key" in msg or "already exists" in msg or "unique" in msg:
            raise HTTPException(status_code=409, detail="Email already in use.")
        raise HTTPException(status_code=500, detail="Profile update failed.")


@app.get("/admin/users")
def admin_users():
    # Minimal admin endpoint. In production, protect this with proper auth.
    resp: Any = supabase.table("users").select("*").execute()
    if getattr(resp, "error", None):
        raise HTTPException(status_code=500, detail=str(resp.error))
    return resp.data


@app.get("/admin/stats")
def admin_stats():
    # Simple stats for graphs (counts by illness + daily detections).
    resp: Any = supabase.table("detections").select("*").execute()
    if getattr(resp, "error", None):
        raise HTTPException(status_code=500, detail=str(resp.error))
    rows = resp.data or []

    by_day: dict[str, int] = {}
    by_illness: dict[str, int] = {}
    for r in rows:
        created_at = str(r.get("created_at") or r.get("inserted_at") or "")
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


@app.delete("/detections/{detection_id}")
def delete_detection(detection_id: str):
    try:
        resp: Any = supabase.table("detections").delete().eq("id", detection_id).execute()
        if getattr(resp, "error", None):
            raise HTTPException(status_code=500, detail=str(resp.error))
        # Return 204 or confirmation
        return {"status": "deleted", "id": detection_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete detection: " + str(e))


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
    safe_columns = {"user_id", "image_url", "plant_name", "illness", "treatment", "prevention", "raw_result"}
    payload = {k: item[k] for k in safe_columns if k in item}
    if "user_id" not in payload or "image_url" not in payload or "plant_name" not in payload:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields for detection: user_id, image_url, plant_name",
        )
    resp: Any = _insert_detection(payload)
    if getattr(resp, "error", None):
        raise HTTPException(status_code=500, detail=str(resp.error))
    return resp.data


@app.post("/config")
def set_config(item: dict):
    resp: Any = supabase.table("system_config").upsert(item).execute()
    if resp.error:
        raise HTTPException(status_code=500, detail=resp.error.message)
    return {"status": "ok"}


def _is_missing_column_error(error: Any) -> bool:
    msg = str(error or "").lower()
    return (
        "does not exist" in msg
        or "could not find the" in msg
        or "pgrst204" in msg
    )


def _insert_detection(payload: dict) -> Any:
    resp: Any = supabase.table("detections").insert(payload).execute()
    if not getattr(resp, "error", None):
        return resp

    if _is_missing_column_error(getattr(resp, "error", None)):
        # Retry with the core required columns only.
        base_payload = {
            "user_id": payload.get("user_id"),
            "image_url": payload.get("image_url"),
            "plant_name": payload.get("plant_name"),
            "illness": payload.get("illness"),
        }
        base_payload = {k: v for k, v in base_payload.items() if v is not None}
        if base_payload:
            resp2: Any = supabase.table("detections").insert(base_payload).execute()
            if not getattr(resp2, "error", None):
                return resp2
        return resp2

    return resp


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


def _is_unknown_value(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip().lower()
    return text in ("", "unknown", "none", "n/a", "not available", "not sure", "undetermined")


def _normalize_ai_output(output: Any) -> dict[str, Any]:
    # Accept dict output directly
    if isinstance(output, dict):
        normalized = output
    elif isinstance(output, str):
        try:
            parsed = json.loads(output)
            if isinstance(parsed, dict):
                normalized = parsed
            else:
                normalized = {"raw": output}
        except Exception:
            # Try to extract JSON substring
            start = output.find('{')
            end = output.rfind('}')
            if start != -1 and end != -1 and end > start:
                try:
                    parsed = json.loads(output[start:end+1])
                    if isinstance(parsed, dict):
                        normalized = parsed
                    else:
                        normalized = {"raw": output}
                except Exception:
                    normalized = {"raw": output}
            else:
                normalized = {"raw": output}
    else:
        normalized = {"raw": output}

    # Enforce expected keys and defaults
    name_val = str(normalized.get("name") or normalized.get("plant") or "unknown").strip()
    illness_val = str(normalized.get("illness") or normalized.get("disease") or "unknown").strip()

    if _is_unknown_value(name_val):
        name_val = "Unknown plant"
    if _is_unknown_value(illness_val):
        illness_val = "Disease not identified"

    final = {
        "name": name_val,
        "illness": illness_val,
        "treatment": str(normalized.get("treatment") or "No treatment available").strip(),
        "prevention": str(normalized.get("prevention") or "No prevention available").strip(),
        "raw": normalized,
    }
    return final


async def _ai_run_analysis(image_base64: str, prompt: str) -> Any:
    agent_any: Any = agent
    result = await agent_any.run(
        prompt,
        deps={"image": ImageUrl(url=image_base64)},
    )
    return getattr(result, "output", None)


async def _ai_analyze(image_bytes: bytes, image_base64: str) -> dict[str, Any]:
    # Strict prompt to avoid unknowns - force classification from known diseases
    strict_prompt = """Analyze this plant leaf image and identify the specific plant and disease.
    
You MUST choose from these exact categories only:
- Apple: Apple scab, Black rot, Cedar apple rust, healthy
- Blueberry: healthy
- Cherry: healthy, Powdery mildew
- Corn: Cercospora leaf spot, Common rust, healthy, Northern Leaf Blight
- Grape: Black rot, Esca (Black Measles), healthy, Leaf blight
- Orange: Haunglongbing (Citrus greening)
- Peach: Bacterial spot, healthy
- Pepper: Bacterial spot, healthy
- Potato: Early blight, healthy, Late blight
- Raspberry: healthy
- Soybean: healthy
- Squash: Powdery mildew
- Strawberry: healthy, Leaf scorch
- Tomato: Bacterial spot, Early blight, healthy, Late blight, Leaf Mold, Septoria leaf spot, Spider mites, Target Spot, Tomato mosaic virus, Tomato Yellow Leaf Curl Virus

Return ONLY valid JSON with keys: "name" (plant name), "illness" (specific disease or "healthy"), "treatment", "prevention".
Do NOT return "unknown" or similar. Choose the closest match from the list above."""

    try:
        output = await _ai_run_analysis(image_base64, strict_prompt)
        normalized = _normalize_ai_output(output)
        
        # Validate that we got valid results
        if _is_unknown_value(normalized["name"]) or _is_unknown_value(normalized["illness"]):
            # Fallback with even stricter prompt
            fallback_prompt = """This is a plant leaf. Identify the exact plant type and disease state.
            
Choose ONE from these options:
Tomato - Early blight
Tomato - Late blight  
Tomato - healthy
Potato - Early blight
Potato - Late blight
Potato - healthy
Apple - Apple scab
Apple - Black rot
Grape - Black rot
Grape - healthy
Corn - Common rust
Corn - healthy
Pepper - Bacterial spot
Pepper - healthy
Orange - Citrus greening
Strawberry - Leaf scorch
Strawberry - healthy

Return JSON: {"name": "plant", "illness": "disease", "treatment": "specific treatment", "prevention": "prevention methods"}"""

            output2 = await _ai_run_analysis(image_base64, fallback_prompt)
            normalized2 = _normalize_ai_output(output2)
            if not (_is_unknown_value(normalized2["name"]) and _is_unknown_value(normalized2["illness"])):
                normalized = normalized2
        
        return normalized
    except Exception as e:
        print(f"AI analysis failed: {e}")
        return {
            "name": "Unknown plant",
            "illness": "Disease not identified",
            "treatment": "Consult a local agricultural expert",
            "prevention": "Practice good plant hygiene",
        }


@app.post("/analyze")
async def analyze_and_save(user_id: str = Form(...), file: UploadFile = File(...)):
    image_bytes = await file.read()
    encoded_string = base64.b64encode(image_bytes).decode("utf-8")
    image_base64 = f"data:{file.content_type};base64,{encoded_string}"

    try:
        normalized = await _ai_analyze(image_bytes, image_base64)

        detection_payload = {
            "user_id": user_id,
            # persisted as a full data URI so it can be previewed later
            "image_url": image_base64,
            "plant_name": normalized.get("name") or (file.filename.rsplit('.', 1)[0] if file.filename else "Unknown plant"),
            "illness": normalized.get("illness") or "Disease not identified",
        }
        full_fields = {
            "treatment": normalized.get("treatment"),
            "prevention": normalized.get("prevention"),
            "raw_result": normalized,
        }
        # Insert optional fields only if table supports them.
        for k, v in full_fields.items():
            detection_payload[k] = v

        resp: Any = _insert_detection(detection_payload)
        if getattr(resp, "error", None):
            _dbg("H8", "main.py:analyze", "supabase_insert_error", {"error": str(resp.error)})
            raise HTTPException(status_code=500, detail="Failed to save detection result")

        return {"result": normalized, "detection": resp.data}
    except Exception as e:
        _dbg("H8", "main.py:analyze", "analyze_exception", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Analysis failed: " + str(e))
