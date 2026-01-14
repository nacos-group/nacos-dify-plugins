# Privacy Policy

## Data Collection

This plugin (A2A Server) collects and processes the following types of data:

**1. Configuration Data (Type B: Indirect Identifiers)**
- Nacos server address
- Nacos namespace ID
- Nacos username and password (if authentication is enabled)
- Aliyun AccessKey and SecretKey (if using Aliyun MSE Nacos)

**2. Agent Metadata**
- Agent name, description, URL, and version configured by the user
- These are used to register the agent to Nacos Agent Registry

**3. Session Data**
- A2A protocol contextId to Dify conversation_id mappings
- Stored locally using Dify Plugin Storage for multi-turn conversation support

## How Data is Used

- **Nacos credentials**: Used solely to authenticate with the Nacos Agent Registry for agent registration and discovery. Credentials are transmitted directly to Nacos and are not stored or logged by this plugin.
- **Agent metadata**: Registered to Nacos Agent Registry to enable agent discovery by other A2A clients.
- **Session mappings**: Stored locally in Dify Plugin Storage to maintain conversation context across multiple requests.

## Third-Party Services

This plugin integrates with the following third-party services:

| Service | Purpose | Privacy Policy |
|---------|---------|----------------|
| Nacos (Self-hosted or Aliyun MSE) | Agent registration and discovery | [Nacos Documentation](https://nacos.io/) / [Aliyun Privacy Policy](https://www.alibabacloud.com/help/legal/latest/alibaba-cloud-international-website-privacy-policy) |

## Data Storage

- Configuration data is stored securely within Dify's plugin configuration system
- Session mappings are stored in Dify Plugin Storage (key-value store)
- No data is transmitted to external services other than Nacos

## Data Retention

- Session mappings are stored persistently until explicitly deleted
- Agent registration data is managed by Nacos according to its retention policies
