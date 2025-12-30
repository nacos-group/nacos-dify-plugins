import asyncio
import logging

from collections.abc import Generator
from typing import Any

from a2a.types import AgentCard
from dify_plugin import Tool
from dify_plugin.config.logger_format import plugin_logger_handler
from dify_plugin.entities.tool import ToolInvokeMessage
from maintainer.ai.nacos_ai_maintainer_service import NacosAIMaintainerService
from v2.nacos import ClientConfigBuilder


from tools.utils import get_agent_card_from_url

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(plugin_logger_handler)


class GetA2aAgentInformationTool(Tool):
	def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[
		ToolInvokeMessage]:

		async def get_a2a_agent_information() -> AgentCard:
			"""
			IMPLEMENT YOUR TOOL HERE
			"""
			agent_card : AgentCard | None = None
			type = tool_parameters.get("type")
			if type == "url":
				a2a_agent_url = tool_parameters.get("a2a_agent_url")
				if a2a_agent_url is None:
					raise ValueError("when type is url, a2a_agent_url is required")

				agent_card = await get_agent_card_from_url(a2a_agent_url)
			elif type == "nacos":
				a2a_agent_name = tool_parameters.get("a2a_agent_name")
				if a2a_agent_name is None:
					raise ValueError("when type is nacos, a2a_agent_name is required")
				nacos_addr = self.runtime.credentials.get("nacos_addr")
				if nacos_addr is None:
					raise ValueError("when type is nacos, nacos_addr is required")
				namespace_id = tool_parameters.get("namespace_id")
				username = self.runtime.credentials.get("nacos_username")
				password = self.runtime.credentials.get("nacos_password")
				access_key = self.runtime.credentials.get("nacos_accessKey")
				secret_key = self.runtime.credentials.get("nacos_secretKey")
				nacos_client_config = ClientConfigBuilder().server_address(
						nacos_addr).namespace_id(
						namespace_id).username(
						username).password(
						password).access_key(
						access_key).secret_key(
						secret_key).build()
				nacos_ai_maintainer_service = await NacosAIMaintainerService.create_ai_service(nacos_client_config)
				agent_card = await nacos_ai_maintainer_service.get_agent_card(namespace_id=namespace_id,
																			  agent_name=a2a_agent_name,
																			  registration_type="URL")
			return agent_card

		try:
			loop = asyncio.get_event_loop()
		except RuntimeError:
			loop = asyncio.new_event_loop()
			asyncio.set_event_loop(loop)

		try:
			agent_card_info : AgentCard = loop.run_until_complete(get_a2a_agent_information())
		except Exception as e:
			logger.error(f"Error calling tool: {e}")
			raise


		yield self.create_json_message({
			"name": agent_card_info.name,
			"description": agent_card_info.description,
			"skills": agent_card_info.skills,
		})
