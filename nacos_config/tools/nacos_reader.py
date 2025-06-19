from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from nacos_py_client import NacosClient


class NacosTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        # Extract parameters
        server_addresses = str(tool_parameters['server_addresses'])
        username = str(tool_parameters['username'])
        password = str(tool_parameters['password'])
        namespace = str(tool_parameters['namespace'])
        data_id = str(tool_parameters['data_id'])
        group = str(tool_parameters['group'])
        client = NacosClient(server_addresses, username, password, namespace)

        try:
            config = client.config.get(data_id=data_id, group=group, namespaceId=namespace)
            yield self.create_json_message({
                "success": True,
                "config": config
            })

        except Exception as e:
            yield self.create_json_message({
                "success": False,
                "error": str(e)
            })
