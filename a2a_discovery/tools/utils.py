import json
from typing import Optional

import httpx
from a2a.client import A2AClientHTTPError, A2AClientJSONError
from a2a.types import AgentCard
from httpx import Timeout
from maintainer.ai.nacos_ai_maintainer_service import NacosAIMaintainerService
from pydantic import ValidationError
from v2.nacos import ClientConfigBuilder


def parse_available_agents_nacos(available_agent_names: Optional[str]) -> list[str]:
    """
    Parse comma-separated agent names for Nacos mode.
    
    Args:
        available_agent_names: Comma-separated agent names, e.g., "agent1,agent2,agent3"
    
    Returns:
        List of agent names
    """
    if not available_agent_names:
        return []
    return [name.strip() for name in available_agent_names.split(',') if name.strip()]


def parse_available_agents_url(available_agent_urls: Optional[str]) -> dict[str, str]:
    """
    Parse JSON mapping of agent names to URLs for URL mode.
    
    Args:
        available_agent_urls: JSON string, e.g., '{"agent1":"http://url1","agent2":"http://url2"}'
    
    Returns:
        Dictionary mapping agent names to URLs
    
    Raises:
        ValueError: If JSON parsing fails
    """
    if not available_agent_urls:
        return {}
    try:
        result = json.loads(available_agent_urls)
        if not isinstance(result, dict):
            raise ValueError("available_agent_urls must be a JSON object")
        return result
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse available_agent_urls as JSON: {e}")


def get_agent_names_list(discovery_type: str, available_agent_names: Optional[str], 
                         available_agent_urls: Optional[str]) -> list[str]:
    """
    Get list of available agent names based on discovery type.
    
    Args:
        discovery_type: Either 'nacos' or 'url'
        available_agent_names: For nacos mode, comma-separated names
        available_agent_urls: For url mode, JSON mapping
    
    Returns:
        List of available agent names
    """
    if discovery_type == "nacos":
        return parse_available_agents_nacos(available_agent_names)
    elif discovery_type == "url":
        url_mapping = parse_available_agents_url(available_agent_urls)
        return list(url_mapping.keys())
    return []


def validate_target_agent(target_agent: str, discovery_type: str, 
                          available_agent_names: Optional[str],
                          available_agent_urls: Optional[str]) -> None:
    """
    Validate that target_agent exists in the available agents list.
    
    Raises:
        ValueError: If target_agent is not in the available list
    """
    available_names = get_agent_names_list(discovery_type, available_agent_names, available_agent_urls)
    if not available_names:
        raise ValueError("No available agents configured. Please configure available_agent_names (Nacos mode) or available_agent_urls (URL mode).")
    if target_agent not in available_names:
        raise ValueError(f"Target agent '{target_agent}' is not in the available agents list: {available_names}")


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


async def get_target_agent_card(
		discovery_type: str,
		target_agent: str,
		available_agent_names: Optional[str],
		available_agent_urls: Optional[str],
		nacos_addr: str,
		namespace_id: str,
		username: str,
		password: str,
		access_key: str,
		secret_key: str
) -> AgentCard:
	"""
	Get AgentCard for the target agent from multi-agent configuration.
	
	Args:
		discovery_type: 'nacos' or 'url'
		target_agent: The name of the agent to get
		available_agent_names: For nacos mode, comma-separated agent names
		available_agent_urls: For url mode, JSON mapping of name to URL
		nacos_addr: Nacos server address
		namespace_id: Nacos namespace ID
		username: Nacos username
		password: Nacos password
		access_key: Aliyun access key
		secret_key: Aliyun secret key
	
	Returns:
		AgentCard for the target agent
	
	Raises:
		ValueError: If target agent not found or configuration invalid
	"""
	# Validate target agent exists in available list
	validate_target_agent(target_agent, discovery_type, available_agent_names, available_agent_urls)
	
	if discovery_type == "nacos":
		# For Nacos mode, target_agent is the agent name in registry
		return await get_a2a_agent_card(
			agent_type="nacos",
			a2a_agent_url=None,
			nacos_addr=nacos_addr,
			a2a_agent_name=target_agent,
			namespace_id=namespace_id,
			username=username,
			password=password,
			access_key=access_key,
			secret_key=secret_key
		)
	elif discovery_type == "url":
		# For URL mode, get URL from mapping
		url_mapping = parse_available_agents_url(available_agent_urls)
		agent_url = url_mapping.get(target_agent)
		if not agent_url:
			raise ValueError(f"URL not found for agent '{target_agent}'")
		return await get_a2a_agent_card(
			agent_type="url",
			a2a_agent_url=agent_url,
			nacos_addr=None,
			a2a_agent_name=None,
			namespace_id=None,
			username=None,
			password=None,
			access_key=None,
			secret_key=None
		)
	else:
		raise ValueError(f"Invalid discovery_type: {discovery_type}")


async def get_all_agents_info(
		discovery_type: str,
		available_agent_names: Optional[str],
		available_agent_urls: Optional[str],
		nacos_addr: str,
		namespace_id: str,
		username: str,
		password: str,
		access_key: str,
		secret_key: str
) -> list[dict]:
	"""
	Get information for all configured agents.
	
	Args:
		discovery_type: 'nacos' or 'url'
		available_agent_names: For nacos mode, comma-separated agent names
		available_agent_urls: For url mode, JSON mapping of name to URL
		nacos_addr: Nacos server address
		namespace_id: Nacos namespace ID
		username: Nacos username
		password: Nacos password
		access_key: Aliyun access key
		secret_key: Aliyun secret key
	
	Returns:
		List of agent info dicts, each containing:
		- agent_name: The configured name (user-defined)
		- description: Agent description from AgentCard
		- skills: Agent skills from AgentCard
	"""
	agent_names = get_agent_names_list(discovery_type, available_agent_names, available_agent_urls)
	if not agent_names:
		raise ValueError("No available agents configured. Please configure available_agent_names (Nacos mode) or available_agent_urls (URL mode).")
	
	results = []
	for agent_name in agent_names:
		try:
			agent_card = await get_target_agent_card(
				discovery_type=discovery_type,
				target_agent=agent_name,
				available_agent_names=available_agent_names,
				available_agent_urls=available_agent_urls,
				nacos_addr=nacos_addr,
				namespace_id=namespace_id,
				username=username,
				password=password,
				access_key=access_key,
				secret_key=secret_key
			)
			results.append({
				"agent_name": agent_name,  # Use configured name, not AgentCard.name
				"description": agent_card.description,
				"skills": agent_card.skills,
			})
		except Exception as e:
			# Include error info for failed agents
			results.append({
				"agent_name": agent_name,
				"error": str(e),
			})
	
	return results


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