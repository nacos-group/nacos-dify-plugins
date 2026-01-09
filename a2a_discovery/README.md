# A2A Agent Client

[English](#english) | [中文](#中文)

---

## English

**Author:** Nacos  
**Version:** 0.0.1  
**Type:** Tool Plugin

### Overview

A2A Agent Client is a Dify plugin that enables discovering and invoking remote A2A (Agent-to-Agent) agents. It supports multi-agent collaboration by allowing dynamic selection from pre-configured agents.

### Features

- **Two Discovery Modes**
  - **Nacos Mode**: Discover agents from Nacos Agent Registry by name
  - **URL Mode**: Discover agents directly via their URLs

- **Multi-Agent Collaboration**: Configure multiple agents and let LLM dynamically select the most suitable one based on task requirements

- **Two Tools**
  - `get_a2a_agent_information`: Get information of all configured agents (name, description, skills)
  - `call_a2a_agent`: Call a selected agent with a query message

### Installation

1. Download the plugin package (`.difypkg` file)
2. Go to your Dify instance → Plugins → Install Plugin
3. Upload the `.difypkg` file
4. Configure provider credentials

### Configuration

#### Provider Credentials

| Parameter | Description | Required |
|-----------|-------------|:--------:|
| `nacos_addr` | Nacos server address (e.g., `127.0.0.1:8848`). Required for Nacos mode only. | No |
| `nacos_username` | Nacos username | No |
| `nacos_password` | Nacos password | No |
| `nacos_accessKey` | Aliyun AccessKey (for MSE Nacos) | No |
| `nacos_secretKey` | Aliyun SecretKey (for MSE Nacos) | No |

#### Tool Parameters

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

### Usage Examples

#### Nacos Mode

```
discovery_type: nacos
available_agent_names: translator_agent,search_agent,code_agent
namespace_id: public
```

#### URL Mode

```
discovery_type: url
available_agent_urls: {"translator_agent":"http://host1:8080/.well-known/agent.json","search_agent":"http://host2:8080/.well-known/agent.json"}
```

### Workflow

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

### Requirements

- Dify >= 0.4.0
- Python 3.12+
- nacos-maintainer-sdk-python >= 0.5.1

### License

Apache 2.0

### Links

- [GitHub Repository](https://github.com/nacos-group/nacos-dify-plugins)
- [Nacos](https://nacos.io/)
- [A2A Protocol](https://github.com/google/A2A)
- [Dify](https://dify.ai/)

---

## 中文

**作者:** Nacos  
**版本:** 0.0.1  
**类型:** 工具插件

### 概述

A2A Agent 客户端是一个 Dify 插件，用于发现和调用远程 A2A（Agent-to-Agent）智能体。它支持多智能体协作，允许 LLM 从预配置的智能体列表中动态选择。

### 功能特性

- **两种发现模式**
  - **Nacos 模式**: 通过名称从 Nacos 智能体注册中心发现智能体
  - **URL 模式**: 通过 URL 直接发现智能体

- **多智能体协作**: 配置多个智能体，让 LLM 根据任务需求动态选择最合适的智能体

- **两个工具**
  - `get_a2a_agent_information`: 获取所有配置的智能体信息（名称、描述、技能）
  - `call_a2a_agent`: 调用指定的智能体并发送查询消息

### 安装方法

1. 下载插件包（`.difypkg` 文件）
2. 进入 Dify 实例 → 插件 → 安装插件
3. 上传 `.difypkg` 文件
4. 配置提供者凭证

### 配置说明

#### 提供者凭证

| 参数 | 说明 | 必填 |
|------|------|:----:|
| `nacos_addr` | Nacos 服务器地址（如 `127.0.0.1:8848`）。仅 Nacos 模式需要。 | 否 |
| `nacos_username` | Nacos 用户名 | 否 |
| `nacos_password` | Nacos 密码 | 否 |
| `nacos_accessKey` | 阿里云 AccessKey（用于 MSE Nacos） | 否 |
| `nacos_secretKey` | 阿里云 SecretKey（用于 MSE Nacos） | 否 |

#### 工具参数

**获取 A2A 智能体信息**

| 参数 | 说明 | 表单类型 |
|------|------|----------|
| `discovery_type` | 发现方式：`nacos` 或 `url` | 用户配置 |
| `available_agent_names` | 逗号分隔的智能体名称（Nacos 模式） | 用户配置 |
| `available_agent_urls` | 名称到 URL 的 JSON 映射（URL 模式） | 用户配置 |
| `namespace_id` | Nacos 命名空间 ID（默认：`public`） | 用户配置 |

**调用 A2A 智能体**

| 参数 | 说明 | 表单类型 |
|------|------|----------|
| `discovery_type` | 发现方式：`nacos` 或 `url` | 用户配置 |
| `available_agent_names` | 逗号分隔的智能体名称（Nacos 模式） | 用户配置 |
| `available_agent_urls` | 名称到 URL 的 JSON 映射（URL 模式） | 用户配置 |
| `namespace_id` | Nacos 命名空间 ID（默认：`public`） | 用户配置 |
| `target_agent` | 要调用的智能体（由 LLM 选择） | LLM 填写 |
| `query` | 发送给智能体的消息 | LLM 填写 |

### 使用示例

#### Nacos 模式

```
discovery_type: nacos
available_agent_names: translator_agent,search_agent,code_agent
namespace_id: public
```

#### URL 模式

```
discovery_type: url
available_agent_urls: {"translator_agent":"http://host1:8080/.well-known/agent.json","search_agent":"http://host2:8080/.well-known/agent.json"}
```

### 工作流程

```
┌─────────────────────────────────────────────────┐
│  1. LLM 调用 get_a2a_agent_information        │
│     → 返回所有智能体的名称、描述、技能            │
└────────────────────────┬────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────┐
│  2. LLM 分析任务需求                          │
│     → 选择最合适的智能体                        │
└────────────────────────┬────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────┐
│  3. LLM 调用 call_a2a_agent                   │
│     → 传入 target_agent + query                 │
└────────────────────────┬────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────┐
│  4. 远程 A2A 智能体处理并返回结果              │
└─────────────────────────────────────────────────┘
```

### 环境要求

- Dify >= 0.4.0
- Python 3.12+
- nacos-maintainer-sdk-python >= 0.5.1

### 开源协议

Apache 2.0

### 相关链接

- [GitHub 仓库](https://github.com/nacos-group/nacos-dify-plugins)
- [Nacos](https://nacos.io/)
- [A2A 协议](https://github.com/google/A2A)
- [Dify](https://dify.ai/)