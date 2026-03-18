from dotenv import load_dotenv
import os
from supabase import create_client
load_dotenv()
client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
for uid in ['1', '00000000-0000-0000-0000-000000000000']:
    try:
        import uuid
        uuid.UUID(uid)
        print(uid, 'valid uuid')
    except Exception as e:
        print(uid, 'invalid uuid', e)
        continue
    r = client.table('detections').select('*').eq('user_id', uid).order('created_at', desc=True).execute()
    print(uid, 'data_len', len(r.data), 'data', r.data)
