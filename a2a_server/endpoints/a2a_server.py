"""
A2A Dify Plugin Endpoint

本模块实现了 A2A 协议的 Dify 插件端点，将 Dify App 通过 A2A 协议对外暴露。

核心组件:
- StarletteRequestAdapter: Werkzeug 到 Starlette 请求适配器
- ResponseAdapter: Starlette 到 Werkzeug 响应适配器
- ConversationManager: 会话管理器，使用 Dify Plugin Storage
- DifyAppAgentExecutor: Dify App 执行器
- A2aServerEndpoint: 插件主入口
"""

import json
import asyncio
import logging
from typing import Any, Optional
from collections.abc import Mapping

from werkzeug.wrappers import Request, Response
from dify_plugin import Endpoint

# A2A SDK imports
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentSkill
from a2a.utils import new_agent_text_message

logger = logging.getLogger(__name__)

# 常量定义
AGENT_CARD_PATH = '/.well-known/agent.json'


# =============================================================================
# Request/Response 适配器
# =============================================================================

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
            
            def __iter__(self):
                return iter(self._headers.keys())
            
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


# =============================================================================
# 会话管理器
# =============================================================================

class ConversationManager:
    """
    会话管理器
    维护 A2A contextId 到 Dify conversation_id 的映射
    
    使用 Dify Plugin Storage (KV) 进行持久化存储
    参考文档：https://docs.dify.ai/develop-plugin/features-and-specs/plugin-types/persistent-storage-kv
    """
    
    KEY_PREFIX = "conv"
    
    def __init__(self, session, app_id: str):
        """
        初始化会话管理器
        
        Args:
            session: Dify Plugin Session，用于访问存储
            app_id: Dify App ID，用于隔离不同 App 的会话
        """
        self.session = session
        self.app_id = app_id
    
    def _build_key(self, context_id: str) -> str:
        """构建存储键 - 格式: conv:{app_id}:{context_id}"""
        return f"{self.KEY_PREFIX}:{self.app_id}:{context_id}"
    
    def get_dify_conversation_id(self, a2a_context_id: str) -> Optional[str]:
        """
        根据 A2A contextId 获取 Dify conversation_id
        
        Args:
            a2a_context_id: A2A 协议的 contextId
            
        Returns:
            Dify conversation_id，如果不存在返回 None
        """
        if not a2a_context_id:
            return None
        
        key = self._build_key(a2a_context_id)
        try:
            # get() 返回 bytes 或 None
            value_bytes = self.session.storage.get(key)
            if value_bytes:
                # 解码 bytes 为字符串
                value = value_bytes.decode('utf-8')
                logger.debug(f"Found conversation mapping: {a2a_context_id} -> {value}")
                return value
        except Exception as e:
            logger.warning(f"Failed to get conversation mapping: {e}")
        
        return None
    
    def save_dify_conversation_id(
        self, 
        a2a_context_id: str, 
        dify_conversation_id: str
    ) -> bool:
        """
        保存 A2A contextId 到 Dify conversation_id 的映射
        
        Args:
            a2a_context_id: A2A 协议的 contextId
            dify_conversation_id: Dify 返回的 conversation_id
            
        Returns:
            是否保存成功
        """
        if not a2a_context_id or not dify_conversation_id:
            return False
        
        key = self._build_key(a2a_context_id)
        try:
            # set() 的值必须是 bytes 格式
            self.session.storage.set(key, dify_conversation_id.encode('utf-8'))
            logger.info(f"Saved conversation mapping: {a2a_context_id} -> {dify_conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save conversation mapping: {e}")
            return False
    
    def delete_conversation_mapping(self, a2a_context_id: str) -> bool:
        """删除会话映射（可选，用于清理）"""
        if not a2a_context_id:
            return False
        
        key = self._build_key(a2a_context_id)
        try:
            self.session.storage.delete(key)
            logger.info(f"Deleted conversation mapping: {a2a_context_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete conversation mapping: {e}")
            return False


# =============================================================================
# Dify App 执行器
# =============================================================================

class DifyAppAgentExecutor(AgentExecutor):
    """
    Dify App 执行器
    将 A2A 请求转换为 Dify App 调用，支持会话管理
    
    支持的 App 类型：
    - Chatbot/Agent/Chatflow (chat) - 使用 session.app.chat.invoke()
    - Workflow - 使用 session.app.workflow.invoke()
    - Completion - 使用 session.app.completion.invoke()
    """

    def __init__(
        self, 
        session, 
        app_config: dict,
        conversation_manager: ConversationManager
    ):
        """
        初始化 Dify App 执行器
        
        Args:
            session: Dify Plugin Session
            app_config: app-selector 返回的 App 配置对象
            conversation_manager: 会话管理器
        """
        self.session = session
        self.app_id = app_config.get('app_id', '')
        self.conversation_manager = conversation_manager

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        执行 A2A 请求，调用 Dify App
        
        Args:
            context: A2A 请求上下文，包含用户消息
            event_queue: 事件队列，用于返回响应
        """
        try:
            # 1. 从 context 中提取用户消息
            user_message = self._extract_user_message(context)
            logger.info(f"Received message for Dify App {self.app_id}: {user_message[:100]}...")
            
            # 2. 调用 Dify App
            result = self._call_app(user_message, context)
            
            # 3. 将结果封装为 A2A 消息并返回
            await event_queue.enqueue_event(new_agent_text_message(result))
            
        except Exception as e:
            logger.exception(f"Error executing Dify App {self.app_id}")
            await event_queue.enqueue_event(
                new_agent_text_message(f"Error: {str(e)}")
            )

    def _extract_user_message(self, context: RequestContext) -> str:
        """
        从 A2A 请求上下文中提取用户消息
        
        A2A 消息结构:
        {
            "role": "user",
            "parts": [{"kind": "text", "text": "用户消息"}]
        }
        """
        message = context.message
        if message and message.parts:
            text_parts = []
            for part in message.parts:
                if hasattr(part, 'text'):
                    text_parts.append(part.text)
                elif hasattr(part, 'root') and hasattr(part.root, 'text'):
                    text_parts.append(part.root.text)
            return '\n'.join(text_parts) if text_parts else ''
        return ''
    
    def _get_context_id(self, context: RequestContext) -> str:
        """从 A2A RequestContext 中提取 contextId"""
        # 优先使用 context_id
        if hasattr(context, 'context_id') and context.context_id:
            return context.context_id
        # 备选：从 task 中获取
        if hasattr(context, 'task') and context.task:
            if hasattr(context.task, 'context_id'):
                return context.task.context_id or ''
        return ''

    def _call_app(self, user_message: str, context: RequestContext) -> str:
        """
        调用 Dify App（支持会话管理）
        
        根据 Dify 文档：
        - Chat 接口参数：app_id, inputs, response_mode, conversation_id, files
        - Workflow 接口参数：app_id, inputs, response_mode, files
        - Completion 接口参数：app_id, inputs, response_mode, files
        
        注意：用户消息通过 inputs 字典传递
        """
        # 1. 获取 A2A contextId
        a2a_context_id = self._get_context_id(context)
        
        # 2. 查找已有的 Dify conversation_id
        dify_conversation_id = ''
        if a2a_context_id:
            dify_conversation_id = self.conversation_manager.get_dify_conversation_id(
                a2a_context_id
            ) or ''
        
        # 3. 调用 Dify App
        try:
            # 优先尝试 Chat 接口（支持 Chatbot/Agent/Chatflow）
            response = self.session.app.chat.invoke(
                app_id=self.app_id,
                inputs={'query': user_message},
                response_mode='blocking',
                conversation_id=dify_conversation_id,
                files=[],
            )
            
            # 4. 保存返回的 conversation_id（如果是新会话）
            if a2a_context_id:
                returned_conv_id = self._extract_conversation_id(response)
                if returned_conv_id and returned_conv_id != dify_conversation_id:
                    self.conversation_manager.save_dify_conversation_id(
                        a2a_context_id, 
                        returned_conv_id
                    )
            
            return self._extract_response(response)
            
        except Exception as chat_error:
            logger.warning(f"Chat invoke failed, trying workflow: {chat_error}")
            try:
                # 如果 Chat 失败，尝试 Workflow 接口
                response = self.session.app.workflow.invoke(
                    app_id=self.app_id,
                    inputs={'query': user_message},
                    response_mode='blocking',
                    files=[],
                )
                return self._extract_workflow_response(response)
            except Exception as workflow_error:
                logger.error(f"Workflow invoke also failed: {workflow_error}")
                raise chat_error
    
    def _extract_conversation_id(self, response) -> Optional[str]:
        """从 Dify 响应中提取 conversation_id"""
        if isinstance(response, dict):
            return response.get('conversation_id')
        if hasattr(response, 'conversation_id'):
            return response.conversation_id
        return None
    
    def _extract_response(self, response) -> str:
        """从 Chat/Completion 响应中提取结果"""
        if isinstance(response, dict):
            return response.get('answer', '') or response.get('text', '') or str(response)
        if hasattr(response, 'answer'):
            return response.answer
        return str(response)
    
    def _extract_workflow_response(self, response) -> str:
        """从 Workflow 响应中提取结果"""
        if isinstance(response, dict):
            outputs = response.get('data', {}).get('outputs', {})
            return outputs.get('text', '') or outputs.get('result', '') or str(outputs)
        if hasattr(response, 'data') and response.data:
            outputs = response.data.get('outputs', {})
            return outputs.get('text', '') or outputs.get('result', '') or str(outputs)
        return str(response)

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """取消执行（当前不支持）"""
        raise Exception('Cancel operation is not supported')


# =============================================================================
# A2A Plugin Endpoint
# =============================================================================

class A2aServerEndpoint(Endpoint):
    """
    A2A 协议的 Dify 插件端点实现
    
    支持的路由：
    - POST / - JSON-RPC 请求处理
    - GET /.well-known/agent.json - Agent Card
    """

    def _invoke(self, r: Request, values: Mapping, settings: Mapping) -> Response:
        """
        插件入口方法
        根据 HTTP 方法和 URL 路径路由到不同的处理函数
        """
        try:
            method = r.method.upper()
            path = r.path
            
            logger.info(f"A2A Plugin received request: {method} {path}")
            
            # === 路由逻辑 ===
            
            # 1. GET /.well-known/agent.json - 返回 Agent Card
            if method == "GET" and path.endswith(AGENT_CARD_PATH):
                return self._handle_get_agent_card(settings)
            
            # 2. POST / - JSON-RPC 处理
            elif method == "POST":
                return self._handle_jsonrpc_request(r, settings)
            
            # 3. 未知路由
            else:
                return self._json_response(
                    {"error": "Not Found", "message": f"Unknown endpoint: {method} {path}"},
                    status=404
                )
                
        except Exception as e:
            logger.exception("Unhandled error in A2A plugin")
            return self._json_error_response(
                code=-32603,
                message="Internal error",
                data=str(e),
                status=500
            )

    def _handle_get_agent_card(self, settings: Mapping) -> Response:
        """
        处理 GET Agent Card 请求
        直接根据用户配置生成 AgentCard 并返回
        """
        agent_card = self._build_agent_card(settings)
        return self._json_response(agent_card.model_dump(mode='json', exclude_none=True))

    def _handle_jsonrpc_request(self, r: Request, settings: Mapping) -> Response:
        """处理 JSON-RPC POST 请求"""
        try:
            # 1. 解析 JSON-RPC 请求
            request_data = r.get_json(force=True)
            logger.debug(f"JSON-RPC request: {request_data}")
            
            # 2. 创建 Starlette 请求适配器
            starlette_request = StarletteRequestAdapter(r)
            
            # 3. 获取 App 配置
            app_config = settings.get('app', {})
            app_id = app_config.get('app_id', '')
            
            # 4. 创建会话管理器
            conversation_manager = ConversationManager(
                session=self.session,
                app_id=app_id,
            )
            
            # 5. 创建执行器
            agent_executor = DifyAppAgentExecutor(
                session=self.session,
                app_config=app_config,
                conversation_manager=conversation_manager,
            )
            
            # 6. 创建请求处理器
            request_handler = DefaultRequestHandler(
                agent_executor=agent_executor,
                task_store=InMemoryTaskStore(),
            )
            
            # 7. 创建 A2A 应用
            agent_card = self._build_agent_card(settings)
            app = A2AStarletteApplication(
                agent_card=agent_card,
                http_handler=request_handler,
            )
            
            # 8. 调用处理方法（异步转同步）
            starlette_response = asyncio.run(
                app._handle_requests(starlette_request)
            )
            
            # 9. 转换响应
            return ResponseAdapter.to_werkzeug(starlette_response)
            
        except json.JSONDecodeError as e:
            return self._json_error_response(
                code=-32700,
                message="Parse error",
                data=str(e)
            )
        except Exception as e:
            logger.exception("Error handling JSON-RPC request")
            return self._json_error_response(
                code=-32603,
                message="Internal error",
                data=str(e)
            )

    def _build_agent_card(self, settings: Mapping) -> AgentCard:
        """根据用户配置构建 AgentCard"""
        # 创建默认技能
        skill = AgentSkill(
            id='dify_app',
            name=settings.get('agent_name', 'Dify App'),
            description=settings.get('agent_description', 'A Dify-powered agent'),
            tags=['dify', 'chatbot'],
            examples=['Hello', 'Help me with...'],
        )
        
        return AgentCard(
            name=settings.get('agent_name', 'Dify A2A Agent'),
            description=settings.get('agent_description', 'A2A Agent powered by Dify'),
            url=settings.get('agent_url', 'http://localhost/'),
            version=settings.get('agent_version', '1.0.0'),
            defaultInputModes=['text'],
            defaultOutputModes=['text'],
            skills=[skill],
        )

    def _json_response(self, data: dict, status: int = 200) -> Response:
        """创建 JSON 响应"""
        return Response(
            json.dumps(data, ensure_ascii=False),
            status=status,
            content_type='application/json'
        )

    def _json_error_response(
        self, 
        code: int, 
        message: str, 
        data: str = None, 
        request_id=None,
        status: int = 200
    ) -> Response:
        """创建 JSON-RPC 错误响应"""
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message,
            },
            "id": request_id
        }
        if data:
            error_response["error"]["data"] = data
        return self._json_response(error_response, status=status)
