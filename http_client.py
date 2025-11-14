import aiohttp
import requests
from typing import Optional, Dict, Any

class HTTPClient:
    @staticmethod
    async def get_async(url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                return {
                    'status': response.status,
                    'data': await response.json() if response.content_type == 'application/json' else await response.text(),
                    'headers': dict(response.headers)
                }
    
    @staticmethod
    async def post_async(url: str, data: Optional[Dict[str, Any]] = None, 
                        json: Optional[Dict[str, Any]] = None, 
                        headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, json=json, headers=headers) as response:
                return {
                    'status': response.status,
                    'data': await response.json() if response.content_type == 'application/json' else await response.text(),
                    'headers': dict(response.headers)
                }
    
    @staticmethod
    def get_sync(url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        response = requests.get(url, headers=headers)
        return {
            'status': response.status_code,
            'data': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
            'headers': dict(response.headers)
        }
    
    @staticmethod
    def post_sync(url: str, data: Optional[Dict[str, Any]] = None,
                 json: Optional[Dict[str, Any]] = None,
                 headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        response = requests.post(url, data=data, json=json, headers=headers)
        return {
            'status': response.status_code,
            'data': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
            'headers': dict(response.headers)
        }

