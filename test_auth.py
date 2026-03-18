import requests
print('register')
r = requests.post('http://127.0.0.1:8000/register', json={'display_name':'test','email':'test1@test.com','password':'pass1234'})
print(r.status_code, r.text)
print('login')
r = requests.post('http://127.0.0.1:8000/login', json={'email':'test1@test.com','password':'pass1234'})
print(r.status_code, r.text)
