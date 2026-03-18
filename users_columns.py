from dotenv import load_dotenv
import os
from supabase import create_client
load_dotenv()
client=create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
for c in ['id','name','display_name','email','password_hash','created_at']:
    try:
        r=client.table('users').select(c).limit(1).execute()
        print(c, 'ok', getattr(r,'data',None))
    except Exception as e:
        print(c, 'err', e)
