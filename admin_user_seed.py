import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
admin_name = os.getenv("ADMIN_NAME", "Admin")

# Hash password (bcrypt)
import bcrypt
hashed_pw = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt()).decode()

# Insert admin user
resp = supabase.table("users").insert({
    "email": admin_email,
    "password": hashed_pw,
    "name": admin_name,
    "role": "admin"
}).execute()
print("Admin user created:", resp)
