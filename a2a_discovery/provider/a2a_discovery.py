import asyncio
from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from maintainer.ai.nacos_ai_maintainer_service import NacosAIMaintainerService
from v2.nacos import ClientConfigBuilder


class A2aDiscoveryProvider(ToolProvider):
    
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:

        async def validate_credentials() -> None:
            try:
                nacos_addr = credentials.get("nacos_addr")
                nacos_username = credentials.get("nacos_username")
                nacos_password = credentials.get("nacos_password")
                nacos_access_key = credentials.get("nacos_accessKey")
                nacos_secret_key = credentials.get("nacos_secretKey")

                if nacos_addr:
                    ai_client_config =ClientConfigBuilder().server_address(
                            nacos_addr).username(
                            nacos_username).password(
                            nacos_password).access_key(
                            nacos_access_key).secret_key(
                            nacos_secret_key).build()
                    nacos_ai_service = await NacosAIMaintainerService.create_ai_service(ai_client_config)
                    await nacos_ai_service.list_agent_cards_by_name(namespace_id="public", agent_name=None, page_no=1, page_size=10)
            except Exception as e:
                raise ToolProviderCredentialValidationError(str(e))

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(validate_credentials())
        except Exception as e:
            raise ToolProviderCredentialValidationError(str(e))


