# A2A Agent Client

**Author:** Nacos  
**Version:** 0.0.1  
**Type:** Tool Plugin

## Overview

A2A Agent Client is a Dify plugin that enables discovering and invoking remote A2A (Agent-to-Agent) agents. It supports multi-agent collaboration by allowing dynamic selection from pre-configured agents.

## Features

- **Two Discovery Modes**
  - **Nacos Mode**: Discover agents from Nacos Agent Registry by name
  - **URL Mode**: Discover agents directly via their URLs

- **Multi-Agent Collaboration**: Configure multiple agents and let LLM dynamically select the most suitable one based on task requirements

- **Two Tools**
  - `get_a2a_agent_information`: Get information of all configured agents (name, description, skills)
  - `call_a2a_agent`: Call a selected agent with a query message

## Installation

1. Download the plugin package (`.difypkg` file)
2. Go to your Dify instance → Plugins → Install Plugin
3. Upload the `.difypkg` file
4. Configure provider credentials

## Configuration

### Provider Credentials

| Parameter | Description | Required |
|-----------|-------------|:--------:|
| `nacos_addr` | Nacos server address (e.g., `127.0.0.1:8848`). Required for Nacos mode only. | No |
| `nacos_username` | Nacos username | No |
| `nacos_password` | Nacos password | No |
| `nacos_accessKey` | Aliyun AccessKey (for MSE Nacos) | No |
| `nacos_secretKey` | Aliyun SecretKey (for MSE Nacos) | No |

### Tool Parameters

**Get A2A Agent Information**

| Parameter | Description | Form |
|-----------|-------------|------|
| `discovery_type` | Discovery method: `nacos` or `url` | User Config |
| `available_agent_names` | Comma-separated agent names (Nacos mode) | User Config |
| `available_agent_urls` | JSON mapping of names to URLs (URL mode) | User Config |
| `namespace_id` | Nacos namespace ID (default: `public`) | User Config |

**Call A2A Agent**

| Parameter | Description | Form |
|-----------|-------------|------|
| `discovery_type` | Discovery method: `nacos` or `url` | User Config |
| `available_agent_names` | Comma-separated agent names (Nacos mode) | User Config |
| `available_agent_urls` | JSON mapping of names to URLs (URL mode) | User Config |
| `namespace_id` | Nacos namespace ID (default: `public`) | User Config |
| `target_agent` | Agent to call (selected by LLM) | LLM |
| `query` | Message to send to the agent | LLM |

## Usage Examples

### Nacos Mode

```
discovery_type: nacos
available_agent_names: translator_agent,search_agent,code_agent
namespace_id: public
```

### URL Mode

```
discovery_type: url
available_agent_urls: {"translator_agent":"http://host1:8080/.well-known/agent.json","search_agent":"http://host2:8080/.well-known/agent.json"}
```

## Workflow

```
┌─────────────────────────────────────────────────────┐
│  1. LLM calls get_a2a_agent_information            │
│     → Returns all agents' name, description, skills │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│  2. LLM analyzes task requirements                  │
│     → Selects the most suitable agent              │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│  3. LLM calls call_a2a_agent                        │
│     → target_agent + query                         │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│  4. Remote A2A Agent processes and responds         │
└─────────────────────────────────────────────────────┘
```

## Requirements

- Dify >= 0.4.0
- Python 3.12+
- nacos-maintainer-sdk-python >= 0.5.1

## License

Apache 2.0

## Links

- [GitHub Repository](https://github.com/nacos-group/nacos-dify-plugins)
- [Nacos](https://nacos.io/)
- [A2A Protocol](https://github.com/google/A2A)
- [Dify](https://dify.ai/)