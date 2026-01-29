# A2A Server 插件

**作者:** nacos  
**版本:** 0.0.3  
**类型:** extension  
**仓库:** [https://github.com/nacos-group/nacos-dify-plugins](https://github.com/nacos-group/nacos-dify-plugins)

将 Dify 应用暴露为 [A2A (Agent-to-Agent)](https://google.github.io/A2A/) 协议 Agent，支持外部发现和调用。

## 功能特性

- **A2A 协议支持**：将任意 Dify App（Chatbot/Agent/Chatflow/Workflow）暴露为 A2A 兼容的 Agent
- **Agent 发现**：支持 `/.well-known/agent.json` 端点用于 Agent 元数据发现
- **Nacos 集成**：可选注册到 Nacos 智能体注册中心，实现集中式 Agent 管理
- **多轮对话**：使用 Dify 插件存储在多次请求间保持对话上下文
- **流式响应**：支持 Agent Chat App 的流式响应模式

## 快速开始

### 第一步：安装插件

1. 从 [GitHub Releases](https://github.com/nacos-group/nacos-dify-plugins/releases) 下载插件包
2. 在 Dify 中，进入 **插件** → **安装插件**
3. 上传插件包并完成安装

### 第二步：创建端点（首次配置）

1. 进入 **插件** → **a2a_server** → **创建端点**
2. 配置必要参数：

| 参数 | 示例值 | 说明 |
|------|--------|------|
| Dify App | 选择你的应用 | 要暴露的 Dify App |
| Agent 名称 | `我的助手` | Agent 显示名称 |
| Agent 描述 | `一个有用的 AI 助手` | Agent 功能描述 |
| Agent 公开访问 URL | `https://your-domain.com/a2a` | **占位值**（稍后更新） |

3. 点击 **保存** 创建端点

> **重要说明**：端点 ID 是由 Dify 在保存后自动生成的。在创建端点之前，你无法知道正确的 URL。请先填写一个占位值（如：`https://your-domain.com/a2a`）。

### 第三步：更新正确的 URL

保存后，Dify 会生成一个端点 ID（如：`abc123`）。现在你需要更新 URL：

1. 返回 **编辑端点**
2. 将 **Agent 公开访问 URL** 更新为正确的值：
   ```
   https://your-domain.com/e/abc123/a2a
   ```
3. 再次点击 **保存**

你的最终 A2A URL 格式如下：

```
Agent Card:  https://your-domain.com/e/{endpoint_id}/a2a/.well-known/agent.json
JSON-RPC:    https://your-domain.com/e/{endpoint_id}/a2a
```

### 第四步：测试 Agent

通过获取 Agent Card 进行测试：

```bash
curl https://your-domain.com/e/{endpoint_id}/a2a/.well-known/agent.json
```

如果成功，你将收到一个包含 Agent 元数据的 JSON 响应。

> **注意**：如果启用了 Nacos 注册，Agent 会在你第一次调用这个 GET 接口时注册到 Nacos。在调用此接口之前，Agent 不会被注册到 Nacos。

如需通过 POST 接口发送消息，建议使用 [A2A SDK](https://a2a-protocol.org/latest/sdk/) 或 A2A 兼容的客户端。

## 配置参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| Dify App | 是 | - | 选择要暴露为 A2A Agent 的 Dify App |
| Agent 名称 | 是 | - | A2A Agent 的名称 |
| Agent 描述 | 是 | - | Agent 能力的描述 |
| Agent 公开访问 URL | 是 | - | Agent 的公开访问地址 |
| Agent 版本 | 否 | `1.0.0` | 版本号 |
| 启用 Nacos 注册 | 是 | `true` | 启用/禁用 Nacos 注册 |
| Nacos 地址 | 否 | - | Nacos 服务器地址（如：`127.0.0.1:8848`） |
| Nacos 命名空间 ID | 否 | `public` | Nacos 命名空间 ID |
| Nacos 用户名 | 否 | - | Nacos 认证用户名 |
| Nacos 密码 | 否 | - | Nacos 认证密码 |
| 阿里云 AccessKey | 否 | - | 阿里云 MSE Nacos 的 AccessKey |
| 阿里云 SecretKey | 否 | - | 阿里云 MSE Nacos 的 SecretKey |

## Nacos 注册

### 何时使用 Nacos

- 你有多个 A2A Agent 需要集中发现
- 你正在使用 Nacos 作为服务注册中心
- 你希望 Agent 之间能够自动发现

### 注册行为

1. **延迟注册**：插件启动时不会立即将 Agent 注册到 Nacos
2. **首次请求触发**：只有在第一次 GET 请求访问 `/.well-known/agent.json` 时才会触发注册
3. **缓存去重**：注册成功后，AgentCard 会被缓存到本地（15 秒 TTL），避免重复注册
4. **变更检测**：如果 Agent 配置发生变化（名称、描述或 URL），会重新注册到 Nacos
5. **远端同步**：注册成功后，插件会从 Nacos 获取 AgentCard 以确保缓存一致性

### 配置示例

**自建 Nacos：**
```
Nacos 地址: 192.168.1.100:8848
Nacos 用户名: nacos
Nacos 密码: nacos
```

**阿里云 MSE Nacos：**
```
Nacos 地址: mse-xxx.mse.aliyuncs.com:8848
阿里云 AccessKey: LTAI5t***
阿里云 SecretKey: ***
```

## API 参考

### 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/a2a/.well-known/agent.json` | 返回 AgentCard 元数据 |
| POST | `/a2a` | A2A 协议 JSON-RPC 端点 |

### 支持的 JSON-RPC 方法

| 方法 | 说明 |
|------|------|
| `message/send` | 向 Agent 发送消息并接收响应 |

### 响应格式

```json
{
  "jsonrpc": "2.0",
  "result": {
    "id": "task-id",
    "status": {
      "state": "completed"
    },
    "artifacts": [
      {
        "parts": [{"kind": "text", "text": "Agent 的响应内容"}]
      }
    ]
  },
  "id": "1"
}
```

## 常见问题

### Agent Card 无法返回

- 检查端点配置是否正确
- 确认 URL 路径包含 `/a2a/.well-known/agent.json`
- 查看 Dify 日志中的错误信息

### Nacos 注册失败

- 确认 Nacos 服务器可从 Dify 访问
- 检查认证凭证是否正确
- 确保命名空间 ID 在 Nacos 中存在

### 消息发送返回错误

- 确认 Dify App 配置正确
- 检查应用是否支持对话模式
- 检查 JSON-RPC 请求格式

## 环境要求

- 支持插件的 Dify 版本
- Python 3.12+
- （可选）用于 Agent 注册的 Nacos 服务器

## 许可证

Apache License 2.0
