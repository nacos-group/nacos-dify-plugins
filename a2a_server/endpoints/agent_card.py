"""
Agent Card Endpoint

处理 GET /.well-known/agent.json 请求，返回 A2A Agent Card。
"""

import json
import logging
from collections.abc import Mapping

from werkzeug.wrappers import Request, Response
from dify_plugin import Endpoint

from a2a.types import AgentCard, AgentSkill

logger = logging.getLogger(__name__)


class AgentCardEndpoint(Endpoint):
    """
    Agent Card 端点
    
    处理 GET 请求，返回 A2A 协议的 Agent Card
    """

    def _invoke(self, r: Request, values: Mapping, settings: Mapping) -> Response:
        """返回 Agent Card"""
        try:
            logger.info("A2A Plugin: GET Agent Card request")
            agent_card = self._build_agent_card(settings)
            return self._json_response(
                agent_card.model_dump(mode='json', exclude_none=True)
            )
        except Exception as e:
            logger.exception("Error building Agent Card")
            return self._json_response(
                {"error": "Internal error", "message": str(e)},
                status=500
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
