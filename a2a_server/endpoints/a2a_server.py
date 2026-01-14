"""
A2A Server Endpoint

统一处理 A2A 协议请求：
- GET  /a2a/.well-known/agent.json -> Agent Card
- POST /a2a -> JSON-RPC
"""

import json
import asyncio
import logging
from collections.abc import Mapping

from werkzeug.wrappers import Request, Response
from dify_plugin import Endpoint

# A2A SDK imports
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

# 本地模块导入
from .adapters import StarletteRequestAdapter, ResponseAdapter
from .conversation import ConversationManager
from .executor import DifyAppAgentExecutor
from .utils import (
    register_agent_card, 
    get_agent_card,
    get_cached_agent_card, 
    set_cached_agent_card, 
    needs_registration
)

logger = logging.getLogger(__name__)

class A2aServerEndpoint(Endpoint):
    """
    A2A 协议统一端点
    
    根据 HTTP 方法分发请求：
    - GET  -> 返回 Agent Card
    - POST -> 处理 JSON-RPC
    """

    def _invoke(self, r: Request, values: Mapping, settings: Mapping) -> Response:
        """请求入口，根据 HTTP 方法分发"""
        method = r.method.upper()
        logger.info(f"A2A Plugin received: {method} {r.path}")
        
        if method == "GET":
            return self._handle_agent_card(settings)
        elif method == "POST":
            return self._handle_jsonrpc(r, settings)
        else:
            return self._json_response(
                {"error": "Method Not Allowed"},
                status=405
            )

    def _handle_agent_card(self, settings: Mapping) -> Response:
        """处理 GET 请求，返回 Agent Card 并根据配置注册到 Nacos"""
        try:
            agent_card = self._build_agent_card(settings)
            
            # 根据用户配置决定是否注册到 Nacos
            self._try_register_to_nacos(agent_card, settings)
            
            return self._json_response(
                agent_card.model_dump(mode='json', exclude_none=True)
            )
        except Exception as e:
            logger.exception("Error building Agent Card")
            return self._json_response(
                {"error": "Internal error", "message": str(e)},
                status=500
            )

    def _try_register_to_nacos(self, agent_card: AgentCard, settings: Mapping) -> None:
        """
        尝试将 AgentCard 注册到 Nacos
        
        根据用户配置的 enable_nacos_registry 开关决定是否注册。
        使用缓存避免频繁查询和注册，只有当 AgentCard 变更时才注册。
        注册失败不影响 Agent Card 的正常返回。
        """
        # 检查是否启用 Nacos 注册
        enable_nacos = settings.get('enable_nacos_registry', True)
        if not enable_nacos:
            logger.debug("Nacos registry is disabled by user settings")
            return
        
        # 检查必要参数
        nacos_addr = settings.get('nacos_addr', '')
        if not nacos_addr:
            logger.debug("Nacos address not configured, skipping registration")
            return
        
        # 获取 Nacos 配置参数
        namespace_id = settings.get('nacos_namespace_id', 'public') or 'public'
        username = settings.get('nacos_username', '') or ''
        password = settings.get('nacos_password', '') or ''
        access_key = settings.get('nacos_accessKey', '') or ''
        secret_key = settings.get('nacos_secretKey', '') or ''
        
        try:
            # 1. 从缓存获取已注册的 AgentCard（缓存过期会自动从 Nacos 获取）
            cached_card = get_cached_agent_card(
                session=self.session,
                nacos_addr=nacos_addr,
                namespace_id=namespace_id,
                agent_name=agent_card.name,
                version=agent_card.version,
                username=username,
                password=password,
                access_key=access_key,
                secret_key=secret_key
            )
            
            # 2. 判断是否需要注册（比较 name, description, url）
            if not needs_registration(agent_card, cached_card):
                print(f"[A2A] Agent '{agent_card.name}' already registered, skipping")
                return
            
            # 3. 执行注册
            asyncio.run(register_agent_card(
                agent_card=agent_card,
                nacos_addr=nacos_addr,
                namespace_id=namespace_id,
                username=username,
                password=password,
                access_key=access_key,
                secret_key=secret_key,
            ))
            
            # 4. 注册成功后从 Nacos 查询并更新缓存
            remote_card = asyncio.run(get_agent_card(
                agent_name=agent_card.name,
                version=agent_card.version,
                nacos_addr=nacos_addr,
                namespace_id=namespace_id,
                username=username,
                password=password,
                access_key=access_key,
                secret_key=secret_key,
            ))
            
            if remote_card:
                set_cached_agent_card(
                    session=self.session,
                    nacos_addr=nacos_addr,
                    namespace_id=namespace_id,
                    agent_card=remote_card
                )
            
            print(f"[A2A] Successfully registered agent '{agent_card.name}' to Nacos at {nacos_addr}")
            logger.info(f"Agent '{agent_card.name}' registered to Nacos at {nacos_addr}")
            
        except Exception as e:
            # 注册失败不影响正常流程，仅记录日志
            print(f"[A2A] Nacos registration failed (non-blocking): {e}")
            logger.warning(f"Failed to register agent card to Nacos: {e}")

    def _handle_jsonrpc(self, r: Request, settings: Mapping) -> Response:
        """处理 POST 请求，JSON-RPC 调用"""
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
        
        # 创建能力声明（所有字段可选）
        capabilities = AgentCapabilities(
            streaming=False,  # 不支持流式响应
            state_transition_history=False,
            push_notifications=False,
        )
        
        return AgentCard(
            name=settings.get('agent_name', 'Dify A2A Agent'),
            description=settings.get('agent_description', 'A2A Agent powered by Dify'),
            url=settings.get('agent_url', 'http://localhost/'),
            version=settings.get('agent_version', '1.0.0'),
            capabilities=capabilities,
            default_input_modes=['text'],
            default_output_modes=['text'],
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
