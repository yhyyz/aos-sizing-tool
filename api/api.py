import os

import httpx

if proxy := os.environ.get('HTTPS_PROXY'):
    PROXIES = {"https://": proxy}
else:
    PROXIES = None


async def remote_data(message):
    url = "https://xxxxx/xxxx"
    async with httpx.AsyncClient(proxies=PROXIES) as client:
        response = await client.post(
            url,
            json=message.dict(),
            # headers={"Authorization": f"Bearer {api_key}"},
            timeout=180,
        )
        return response.json()


