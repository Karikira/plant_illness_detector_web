from fastapi.testclient import TestClient
from main import app
client=TestClient(app)
res=client.get('/history/1')
print(res.status_code)
print(res.text)
res2=client.get('/history/00000000-0000-0000-0000-000000000000')
print(res2.status_code)
print(res2.text)
