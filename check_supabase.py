import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url=os.getenv('SUPABASE_URL')
key=os.getenv('SUPABASE_KEY')
print('url',url)
print('keylen',len(key) if key else 0)
client=create_client(url,key)
for table in ['users','detections']:
    try:
        r=client.table(table).select('*').limit(1).execute()
        print(table, 'error', getattr(r, 'error', None), 'status', getattr(r, 'status_code', None), 'data_len', len(r.data) if getattr(r, 'data', None) is not None else None)
    except Exception as e:
        print(table,'exception',type(e).__name__,e)
