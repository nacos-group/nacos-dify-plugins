"""
Request/Response 适配器

将 Werkzeug Request/Response 适配为 Starlette 格式，
以便与 A2A SDK 集成。
"""

import json
from typing import Any

from werkzeug.wrappers import Request, Response


class StarletteRequestAdapter:
    """
    将 Werkzeug Request 适配为 Starlette Request 接口
    
    A2A SDK 使用 Starlette 框架，而 Dify Plugin 使用 Werkzeug。
    此适配器提供 Starlette Request 所需的属性和方法接口。
    """
    
    def __init__(self, werkzeug_request: Request):
        self._request = werkzeug_request
        self._json_data = None
        self._state = {}
    
    @property
    def method(self) -> str:
        """HTTP 方法"""
        return self._request.method
    
    @property
    def url(self):
        """URL 对象，需要提供 path 属性"""
        class URLAdapter:
            def __init__(self, werkzeug_request):
                self._request = werkzeug_request
            
            @property
            def path(self) -> str:
                return self._request.path
            
            @property
            def scheme(self) -> str:
                return self._request.scheme
        
        return URLAdapter(self._request)
    
    @property
    def headers(self):
        """请求头，需要支持 get() 和 getlist() 方法"""
        class HeadersAdapter:
            def __init__(self, werkzeug_headers):
                self._headers = werkzeug_headers
            
            def get(self, key: str, default: Any = None) -> Any:
                return self._headers.get(key, default)
            
            def getlist(self, key: str) -> list[str]:
                return self._headers.getlist(key)
            
            def __getitem__(self, key: str) -> str:
                """Support dict(headers) and headers[key]"""
                value = self._headers.get(key)
                if value is None:
                    raise KeyError(key)
                return value
            
            def __iter__(self):
                return iter(self._headers.keys())
            
            def __len__(self):
                return len(list(self._headers.keys()))
            
            def items(self):
                return self._headers.items()
            
            def keys(self):
                return self._headers.keys()
            
            def values(self):
                return self._headers.values()
        
        return HeadersAdapter(self._request.headers)
    
    async def json(self) -> dict | list:
        """解析 JSON body（异步方法）"""
        if self._json_data is None:
            try:
                self._json_data = self._request.get_json(force=True)
            except Exception as e:
                raise json.JSONDecodeError(
                    f"Failed to parse JSON: {e}",
                    doc=str(self._request.get_data()),
                    pos=0
                )
        return self._json_data
    
    @property
    def user(self):
        """用户对象（认证相关）"""
        class UnauthenticatedUserAdapter:
            @property
            def is_authenticated(self) -> bool:
                return False
            
            @property
            def display_name(self) -> str:
                return "anonymous"
        
        return UnauthenticatedUserAdapter()
    
    @property
    def auth(self):
        """认证信息"""
        return self.headers.get('Authorization')
    
    @property
    def state(self) -> dict:
        """请求状态字典"""
        return self._state


class ResponseAdapter:
    """将 Starlette Response 转换为 Werkzeug Response"""
    
    @staticmethod
    def to_werkzeug(starlette_response) -> Response:
        """转换 Starlette Response 到 Werkzeug Response"""
        # 处理 JSONResponse
        if hasattr(starlette_response, 'body'):
            body = starlette_response.body
            if isinstance(body, bytes):
                body = body.decode('utf-8')
        else:
            body = ""
        
        # 提取状态码
        status_code = getattr(starlette_response, 'status_code', 200)
        
        # 提取响应头
        headers = {}
        if hasattr(starlette_response, 'headers'):
            headers = dict(starlette_response.headers)
        
        # 确定 content-type
        content_type = headers.get('content-type', 'application/json')
        
        return Response(
            response=body,
            status=status_code,
            headers=headers,
            content_type=content_type
        )
