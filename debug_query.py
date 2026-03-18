from dotenv import load_dotenv
from supabase import create_client
import os
load_dotenv()
client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
for expr in [
    "client.table('detections').select('*').execute()",
    "client.table('detections').select('*').order('created_at', desc=True).execute()",
    "client.table('detections').select('*').eq('user_id','1').order('created_at', desc=True).execute()",
]:
    try:
        r=eval(expr)
        print(expr)
        print('error', getattr(r,'error',None))
        print('data', getattr(r,'data',None))
    except Exception as e:
        print(expr,'exception',type(e).__name__,e)
