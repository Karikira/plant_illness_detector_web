# flake8: noqa: E302,E501
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import bcrypt
import os
from dotenv import load_dotenv
from supabase import create_client

# AI/agent imports
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai import ImageUrl
import base64

# load environment variables from .env file
load_dotenv()

app = FastAPI()


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

    resp = supabase.table("users").insert({
        "display_name": data.display_name,
        "email": data.email,
        "password_hash": password_hash
    }).execute()
    if resp.error:
        raise HTTPException(status_code=500, detail=resp.error.message)

    return {"message": "Registration successful"}


# ---------------- LOGIN ----------------
@app.post("/login")
def login(data: LoginData):
    response = supabase.table("users").select("*").eq("email", data.email).execute()
    user = response.data[0] if response.data else None

    if not user or not bcrypt.checkpw(data.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"message": "Login successful"}


# helper function to fetch a user by email (used by login, etc.)
def get_user_by_email(email: str):
    resp = supabase.table("users").select("*") \
                  .eq("email", email).single().execute()
    if resp.error:
        raise HTTPException(status_code=500, detail=resp.error.message)
    return resp.data


@app.get("/history/{user_id}")
def history(user_id: str):
    resp = supabase.table("detections") \
                  .select("*") \
                  .eq("user_id", user_id) \
                  .order("created_at", desc=True) \
                  .execute()
    if resp.error:
        raise HTTPException(status_code=500, detail=resp.error.message)
    return resp.data


@app.post("/activity")
def log_activity(entry: dict):
    resp = supabase.table("activity_logs").insert(entry).execute()
    if resp.error:
        raise HTTPException(status_code=500, detail=resp.error.message)
    return {"status": "ok"}


@app.get("/config/{key}")
def get_config(key: str):
    resp = supabase.table("system_config") \
                  .select("value") \
                  .eq("key", key) \
                  .single() \
                  .execute()
    if resp.error:
        raise HTTPException(status_code=500, detail=resp.error.message)
    return resp.data


@app.post("/detections")
def add_detection(item: dict):
    resp = supabase.table("detections").insert(item).execute()
    if resp.error:
        raise HTTPException(status_code=500, detail=resp.error.message)
    return resp.data


@app.post("/config")
def set_config(item: dict):
    resp = supabase.table("system_config").upsert(item).execute()
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
    result = await agent.run(
        "Analyze this plant leaf image and identify the disease.",
        deps={"image": ImageUrl(url=image_base64)}
    )
    return {"result": result.output}
