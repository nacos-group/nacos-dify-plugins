import json
import time
import asyncio
from typing import Optional

from a2a.types import AgentCard
from maintainer.ai.nacos_ai_maintainer_service import NacosAIMaintainerService
from v2.nacos import ClientConfigBuilder


async def register_agent_card(
		agent_card: AgentCard,
		nacos_addr: str,
		namespace_id: str,
		username: str,
		password: str,
		access_key: str,
		secret_key: str
):
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
	await nacos_ai_maintainer_service.register_agent(
			agent_card=agent_card,
			namespace_id=namespace_id,
			registration_type="SERVICE"
	)


async def get_agent_card(
		agent_name: str,
		version: str,
		nacos_addr: str,
		namespace_id: str,
		username: str,
		password: str,
		access_key: str,
		secret_key: str
) -> AgentCard:
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
	return await nacos_ai_maintainer_service.get_agent_card(
			agent_name=agent_name,
			version=version,
			namespace_id=namespace_id,
			registration_type="URL"
	)


# ============== AgentCard 缓存 ==============

CACHE_KEY_PREFIX = "agentcard"
CACHE_TTL_SECONDS = 15  # 15 秒


def _build_cache_key(
		nacos_addr: str,
		namespace_id: str,
		agent_name: str,
		version: str
) -> str:
	"""构建缓存 key: agentcard:{addr}:{namespace_id}:{name}:{version}"""
	safe_addr = nacos_addr.replace(':', '_').replace('/', '_')
	return f"{CACHE_KEY_PREFIX}:{safe_addr}:{namespace_id}:{agent_name}:{version}"


def get_cached_agent_card(
		session,
		nacos_addr: str,
		namespace_id: str,
		agent_name: str,
		version: str,
		username: str = '',
		password: str = '',
		access_key: str = '',
		secret_key: str = ''
) -> Optional[AgentCard]:
	"""
	从缓存获取 AgentCard，缓存过期则从 Nacos 获取并刷新缓存

	Returns:
		AgentCard 对象，如果缓存不存在或已过期会从 Nacos 获取
	"""
	key = _build_cache_key(nacos_addr, namespace_id, agent_name, version)

	try:
		value_bytes = session.storage.get(key)
		if value_bytes:
			cache_data = json.loads(value_bytes.decode('utf-8'))
			cached_time = cache_data.get('cached_time', 0)

			# 缓存未过期，直接返回
			if time.time() - cached_time <= CACHE_TTL_SECONDS:
				agent_card = AgentCard.model_validate(cache_data.get('agent_card'))
				print(f"[AgentCardCache] Cache hit: {agent_name}")
				return agent_card
			else:
				print(f"[AgentCardCache] Cache expired: {agent_name}")
		else:
			print(f"[AgentCardCache] Cache miss: {agent_name}")

		# 缓存不存在或已过期，从 Nacos 获取
		print(f"[AgentCardCache] Fetching from Nacos: {agent_name}")
		agent_card = asyncio.run(get_agent_card(
			agent_name=agent_name,
			version=version,
			nacos_addr=nacos_addr,
			namespace_id=namespace_id,
			username=username,
			password=password,
			access_key=access_key,
			secret_key=secret_key
		))

		# 更新缓存
		if agent_card:
			set_cached_agent_card(session, nacos_addr, namespace_id, agent_card)
			print(f"[AgentCardCache] Refreshed cache from Nacos: {agent_name}")

		return agent_card

	except Exception as e:
		print(f"[AgentCardCache] Error getting agent card: {e}")
		return None


def set_cached_agent_card(
		session,
		nacos_addr: str,
		namespace_id: str,
		agent_card: AgentCard
) -> bool:
	"""将 AgentCard 存入缓存"""
	key = _build_cache_key(nacos_addr, namespace_id, agent_card.name,
						   agent_card.version)

	try:
		cache_data = {
			'cached_time': time.time(),
			'agent_card': agent_card.model_dump(mode='json', exclude_none=True)
		}
		value_bytes = json.dumps(cache_data, ensure_ascii=False).encode('utf-8')
		session.storage.set(key, value_bytes)
		print(f"[AgentCardCache] Cached: {agent_card.name}")
		return True
	except Exception as e:
		print(f"[AgentCardCache] Error writing cache: {e}")
		return False


def needs_registration(current_card: AgentCard,
		cached_card: Optional[AgentCard]) -> bool:
	"""
	判断是否需要注册/更新 AgentCard

	比较 name、description、url 是否一致
	"""
	if cached_card is None:
		print("[AgentCardCache] No cached card, registration needed")
		return True

	if current_card.name != cached_card.name:
		print(
			f"[AgentCardCache] Name changed: {cached_card.name} -> {current_card.name}")
		return True

	if current_card.description != cached_card.description:
		print("[AgentCardCache] Description changed")
		return True

	if current_card.url != cached_card.url:
		print(
			f"[AgentCardCache] URL changed: {cached_card.url} -> {current_card.url}")
		return True

	print("[AgentCardCache] No changes detected, skip registration")
	return False
