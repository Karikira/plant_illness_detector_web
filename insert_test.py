from dotenv import load_dotenv
import os
import bcrypt
from supabase import create_client
load_dotenv()
client=create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
h=bcrypt.hashpw('pass1234'.encode(), bcrypt.gensalt()).decode()
print('hash', h)
try:
    r=client.table('users').insert({'name':'test_user','email':'test4@test.com','password_hash':h}).execute()
    print('r', r)
    print('data', r.data)
    print('status', hasattr(r,'status_code') and r.status_code)
    print('dir', [a for a in dir(r) if 'error' in a.lower() or 'message' in a.lower()])
except Exception as e:
    print('exc', type(e), e)
