import asyncio
import logging

from collections.abc import Generator
from typing import Any

from a2a.types import AgentCard
from dify_plugin import Tool
from dify_plugin.config.logger_format import plugin_logger_handler
from dify_plugin.entities.tool import ToolInvokeMessage


from tools.utils import get_a2a_agent_card

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(plugin_logger_handler)


class GetA2aAgentInformationTool(Tool):
	def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[
		ToolInvokeMessage]:

		agent_type = tool_parameters.get("type")
		a2a_agent_url = tool_parameters.get("a2a_agent_url")
		nacos_addr = self.runtime.credentials.get("nacos_addr")
		a2a_agent_name = tool_parameters.get("a2a_agent_name")
		namespace_id = tool_parameters.get("namespace_id")
		username = self.runtime.credentials.get("nacos_username")
		password = self.runtime.credentials.get("nacos_password")
		access_key = self.runtime.credentials.get("nacos_accessKey")
		secret_key = self.runtime.credentials.get("nacos_secretKey")

		try:
			loop = asyncio.get_event_loop()
		except RuntimeError:
			loop = asyncio.new_event_loop()
			asyncio.set_event_loop(loop)

		try:
			agent_card_info : AgentCard = loop.run_until_complete(get_a2a_agent_card(
					agent_type=agent_type,
					a2a_agent_url=a2a_agent_url,
					nacos_addr=nacos_addr,
					a2a_agent_name=a2a_agent_name,
					namespace_id=namespace_id,
					username=username,
					password=password,
					access_key=access_key,
					secret_key=secret_key,
			))
		except Exception as e:
			logger.error(f"Error calling tool: {e}")
			raise


		yield self.create_json_message({
			"name": agent_card_info.name,
			"description": agent_card_info.description,
			"skills": agent_card_info.skills,
		})
