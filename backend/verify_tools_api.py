import asyncio
import httpx
import sys

async def verify():
    print('Starting verification...')
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print('Attempting login...')
            auth_res = await client.post('http://localhost:8000/api/v1/auth/login', json={'email': 'admin@example.com', 'password': 'admin'})
            print(f'Login status: {auth_res.status_code}')
            if auth_res.status_code != 200:
                print(auth_res.text)
                return False
            token = auth_res.json()['access_token']
            print('Login success!')
            
            headers = {'Authorization': f'Bearer {token}'}
            tools_res = await client.get('http://localhost:8000/api/v1/tools?limit=3', headers=headers)
            print(f'Tools API status: {tools_res.status_code}')
            if tools_res.status_code == 200:
                 tools = tools_res.json()
                 print(f'✅ SUCCESS! Retrieved {len(tools)} tools.')
                 for i, tool in enumerate(tools[:3]):
                     print(f'  {i+1}. {tool["name"]} - {tool["status"]}')
                 return True
            else:
                 print(tools_res.text)
                 return False
        except Exception as e:
            print(f'❌ Error: {e!r}')
            return False

if __name__ == '__main__':
    result = asyncio.run(verify())
    sys.exit(0 if result else 1)
