import asyncio
import logging
from collections.abc import Generator
from typing import Any
from uuid import uuid4

import httpx
from a2a.client import ClientFactory, ClientConfig
from a2a.types import AgentCard, Message, TextPart, Part, Role
from dify_plugin import Tool
from dify_plugin.config.logger_format import plugin_logger_handler
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.utils import get_a2a_agent_card

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(plugin_logger_handler)


class CallA2aAgentTool(Tool):
	def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[
		ToolInvokeMessage]:

		agent_type = tool_parameters.get("type")
		a2a_agent_url = tool_parameters.get("a2a_agent_url")
		nacos_addr = self.runtime.credentials.get("nacos_addr")
		a2a_agent_name = tool_parameters.get("a2a_agent_name")
		namespace_id = tool_parameters.get("namespace_id")
		query = tool_parameters.get("query")
		username = self.runtime.credentials.get("nacos_username")
		password = self.runtime.credentials.get("nacos_password")
		access_key = self.runtime.credentials.get("nacos_accessKey")
		secret_key = self.runtime.credentials.get("nacos_secretKey")

		async def call_a2a_agent():
			agent_card: AgentCard = await get_a2a_agent_card(
					agent_type=agent_type,
					a2a_agent_url=a2a_agent_url,
					nacos_addr=nacos_addr,
					a2a_agent_name=a2a_agent_name,
					namespace_id=namespace_id,
					username=username,
					password=password,
					access_key=access_key,
					secret_key=secret_key
			)

			a2a_client_config = ClientConfig(
					streaming=False,
					polling=False,
					httpx_client=httpx.AsyncClient(
							timeout=httpx.Timeout(timeout=600),
					),
			)

			a2a_client_factory = ClientFactory(
					config=a2a_client_config,
			)

			msg = Message(
					role=Role.user,
					parts=[
						Part(root=TextPart(
								text=query,
						))
					],
					message_id=str(uuid4()),
					context_id=str(uuid4()) if self.session.conversation_id is None
					else self.session.conversation_id
			)
			client = a2a_client_factory.create(
					card=agent_card,
			)
			response_msg = None
			async for item in client.send_message(msg):
				if isinstance(item, Message):
					response_msg = item
					logger.debug(
							"[%s] Received direct message response",
							self.__class__.__name__,
					)
				elif isinstance(item, tuple):
					task, update_event = item
					if task is not None:
						response_msg = task
					elif update_event is not None:
						response_msg = update_event
					else:
						raise ValueError("Invalid item")

			return response_msg

		try:
			loop = asyncio.get_event_loop()
		except RuntimeError:
			loop = asyncio.new_event_loop()
			asyncio.set_event_loop(loop)

		try:
			call_result: AgentCard = loop.run_until_complete(call_a2a_agent())
		except Exception as e:
			logger.error(f"Error calling tool: {e}")
			raise

		yield self.create_json_message({
			"result": call_result
		})
