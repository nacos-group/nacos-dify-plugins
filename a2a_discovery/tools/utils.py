import json

import httpx
from a2a.client import A2AClientHTTPError, A2AClientJSONError
from a2a.types import AgentCard
from httpx import Timeout
from pydantic import ValidationError


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