# Privacy Policy

## A2A Agent Client Plugin

### Data Collection

This plugin collects and processes the following data:

1. **Configuration Data**: Nacos server address, namespace ID, and agent names configured by users for service discovery.
2. **Authentication Credentials**: Nacos username/password or Aliyun AccessKey/SecretKey (stored securely by Dify platform, not by the plugin).
3. **Query Messages**: User queries sent to remote A2A agents.

### Data Usage

- **Service Discovery**: Configuration data is used to connect to Nacos registry or directly to A2A agent URLs.
- **Agent Communication**: Query messages are forwarded to selected remote A2A agents for processing.
- **No Data Storage**: This plugin does not persistently store any user data. All data is processed in-memory during request handling.

### Data Sharing

- **Remote A2A Agents**: Query messages are sent to user-configured remote A2A agents.
- **Nacos Registry**: When using Nacos mode, the plugin communicates with the configured Nacos server to discover agent information.
- **No Third-Party Sharing**: We do not share any data with third parties beyond the configured services.

### Security

- All credentials are managed by the Dify platform's secure credential storage.
- Communication with Nacos and A2A agents uses standard HTTP/HTTPS protocols.
- Users are responsible for securing their Nacos instances and A2A agent endpoints.

### User Rights

- Users can modify or remove their configuration at any time.
- No persistent data is stored by this plugin.

### Contact

For privacy-related questions, please contact the Nacos community or raise an issue on the project repository.