"""
A2A Server Endpoints Package

包含以下模块:
- adapters: Request/Response 适配器
- conversation: 会话管理器
- executor: Dify App 执行器
- a2a_server: 统一端点入口 (GET/POST)
"""

from .a2a_server import A2aServerEndpoint
from .adapters import StarletteRequestAdapter, ResponseAdapter
from .conversation import ConversationManager
from .executor import DifyAppAgentExecutor

__all__ = [
    'A2aServerEndpoint',
    'StarletteRequestAdapter',
    'ResponseAdapter',
    'ConversationManager',
    'DifyAppAgentExecutor',
]
