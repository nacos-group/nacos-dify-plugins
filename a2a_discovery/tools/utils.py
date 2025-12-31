import json

import httpx
from a2a.client import A2AClientHTTPError, A2AClientJSONError
from a2a.types import AgentCard
from httpx import Timeout
from maintainer.ai.nacos_ai_maintainer_service import NacosAIMaintainerService
from pydantic import ValidationError
from v2.nacos import ClientConfigBuilder


async def get_a2a_agent_card(
		agent_type: str,
		a2a_agent_url: str,
		nacos_addr: str,
		a2a_agent_name: str,
		namespace_id: str,
		username: str,
		password: str,
		access_key: str,
		secret_key: str
) -> AgentCard:
	agent_card: AgentCard | None = None
	if agent_type == "url":
		if a2a_agent_url is None:
			raise ValueError("when type is url, a2a_agent_url is required")
		agent_card = await get_agent_card_from_url(a2a_agent_url)
	elif agent_type == "nacos":
		if a2a_agent_name is None:
			raise ValueError("when type is nacos, a2a_agent_name is required")
		if nacos_addr is None:
			raise ValueError("when type is nacos, nacos_addr is required")

		if ':' not in nacos_addr.split('//')[-1]:
			nacos_addr = f"{nacos_addr}:8848"

		nacos_client_config = ClientConfigBuilder().server_address(
				nacos_addr).namespace_id(
				namespace_id).username(
				username).password(
				password).access_key(
				access_key).secret_key(
				secret_key).build()
		nacos_ai_maintainer_service = await NacosAIMaintainerService.create_ai_service(
			nacos_client_config)
		agent_card = await nacos_ai_maintainer_service.get_agent_card(
			namespace_id=namespace_id,
			agent_name=a2a_agent_name,
			registration_type="URL")
	return agent_card


async def get_agent_card_from_url(target_url:str) -> AgentCard:

	_httpx_client = httpx.AsyncClient(timeout=Timeout(10))
	try:
		response = await _httpx_client.get(
				target_url,
		)
		response.raise_for_status()
		agent_card_data = response.json()
		agent_card = AgentCard.model_validate(agent_card_data)
	except httpx.HTTPStatusError as e:
		raise A2AClientHTTPError(
				e.response.status_code,
				f'Failed to fetch agent card from {target_url}: {e}',
		) from e
	except json.JSONDecodeError as e:
		raise A2AClientJSONError(
				f'Failed to parse JSON for agent card from {target_url}: {e}'
		) from e
	except httpx.RequestError as e:
		raise A2AClientHTTPError(
				503,
				f'Network communication error fetching agent card from {target_url}: {e}',
		) from e
	except ValidationError as e:  # Pydantic validation error
		raise A2AClientJSONError(
				f'Failed to validate agent card structure from {target_url}: {e.json()}'
		) from e

	return agent_card