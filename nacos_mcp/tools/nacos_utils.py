from typing import Any

from maintainer.ai.model.nacos_mcp_info import McpServerDetailInfo, McpToolMeta
from mcp import types


def is_tool_enabled(tool_name: str , _tools_meta :dict[str, McpToolMeta]) -> bool:
	if _tools_meta is None:
		return True
	if tool_name in _tools_meta:
		mcp_tool_meta = _tools_meta[tool_name]
		if mcp_tool_meta.enabled is not None:
			if not mcp_tool_meta.enabled:
				return False
	return True

def update_tools_according_to_nacos(tools :types.ListToolsResult
		,mcp_server_detail :McpServerDetailInfo):

	def update_args_description(_local_args: dict[str, Any],
			_nacos_args: dict[str, Any]):
		for key, value in _local_args.items():
			if key in _nacos_args and "description" in _nacos_args[key]:
				_local_args[key]["description"] = _nacos_args[key][
					"description"]


	nacos_tools_meta = mcp_server_detail.toolSpec.toolsMeta
	nacos_tools = mcp_server_detail.toolSpec.tools
	new_tools = []
	for tool in tools.tools:
		if not is_tool_enabled(tool.name, nacos_tools_meta):
			continue
		for nacos_tool in nacos_tools:
			if tool.name == nacos_tool.name:
				if nacos_tool.description is not None:
					tool.description = nacos_tool.description
				local_args = tool.inputSchema["properties"]
				nacos_args = nacos_tool.inputSchema["properties"]
				update_args_description(local_args, nacos_args)
				break
		new_tools.append(tool)

	return new_tools


