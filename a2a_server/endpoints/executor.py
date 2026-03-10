"""
Dify App 执行器

将 A2A 请求转换为 Dify App 调用，支持会话管理。
"""

import logging
from typing import Any, Optional

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message
from dify_plugin.config.logger_format import plugin_logger_handler

from .conversation import ConversationManager

logger = logging.getLogger(__name__)
logger.addHandler(plugin_logger_handler)

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
                part_payload = self._unwrap_part(part)
                if hasattr(part_payload, 'text') and part_payload.text:
                    text_parts.append(part_payload.text)
            return '\n'.join(text_parts) if text_parts else ''
        return ''

    def _unwrap_part(self, part):
        """Unwrap A2A RootModel parts so handlers can inspect concrete payloads."""
        return part.root if hasattr(part, 'root') else part

    def _merge_input_values(
        self,
        current: dict[str, Any],
        incoming: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Shallow-merge structured context into Dify inputs."""
        if not incoming:
            return current
        for key, value in incoming.items():
            current[key] = value
        return current

    def _extract_dify_inputs(self, context: RequestContext) -> dict[str, Any]:
        """
        Map standard A2A structured context into Dify inputs.

        Mapping order:
        1. Request-level params.metadata
        2. Message-level message.metadata
        3. Structured data from message.parts[].data

        Later sources override earlier ones so explicit structured message data wins.
        """
        inputs: dict[str, Any] = {}

        inputs = self._merge_input_values(inputs, context.metadata)

        message = context.message
        if not message:
            return inputs

        if getattr(message, 'metadata', None):
            inputs = self._merge_input_values(inputs, message.metadata)

        for part in message.parts or []:
            part_payload = self._unwrap_part(part)
            if getattr(part_payload, 'kind', None) != 'data':
                continue
            if isinstance(getattr(part_payload, 'data', None), dict):
                inputs = self._merge_input_values(inputs, part_payload.data)

        return inputs
    
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
        
        注意：Agent Chat App 不支持 blocking 模式，必须使用 streaming
        """
        # 1. 获取 A2A contextId
        a2a_context_id = self._get_context_id(context)
        dify_inputs = self._extract_dify_inputs(context)
        
        # 2. 查找已有的 Dify conversation_id
        dify_conversation_id = ''
        if a2a_context_id:
            dify_conversation_id = self.conversation_manager.get_dify_conversation_id(
                a2a_context_id
            ) or ''
        
        # 3. 调用 Dify App
        try:
            # Chat 接口（支持 Chatbot/Agent/Chatflow）
            # Agent App 不支持 blocking，必须用 streaming
            response_gen = self.session.app.chat.invoke(
                app_id=self.app_id,
                query=user_message,
                inputs=dify_inputs,
                response_mode='streaming',
                conversation_id=dify_conversation_id or None,
            )
            
            # 收集流式响应
            result_text = ''
            conversation_id = None
            for chunk in response_gen:
                if isinstance(chunk, dict):
                    # 提取 answer 片段
                    if 'answer' in chunk:
                        result_text += chunk['answer']
                    # 提取 conversation_id
                    if 'conversation_id' in chunk and chunk['conversation_id']:
                        conversation_id = chunk['conversation_id']
            
            # 4. 保存返回的 conversation_id（如果是新会话）
            if a2a_context_id and conversation_id and conversation_id != dify_conversation_id:
                self.conversation_manager.save_dify_conversation_id(
                    a2a_context_id, 
                    conversation_id
                )
            
            return result_text or 'No response'
            
        except Exception as chat_error:
            logger.warning(f"Chat invoke failed, trying workflow: {chat_error}")
            try:
                # Workflow 接口（默认 blocking）
                response = self.session.app.workflow.invoke(
                    app_id=self.app_id,
                    inputs=self._merge_input_values(dify_inputs.copy(), {'query': user_message}),
                    response_mode='blocking',
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
