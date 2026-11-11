# Chatbot Bridge Automation

Transform free chatbot interfaces (DeepSeek, ChatGPT, Claude) into fully-functional APIs by monitoring conversations, extracting programming commands, and executing them safely on your local machine.

## Features

- 🤖 **Multi-Platform Support**: Works with DeepSeek, ChatGPT, and Claude
- 🔒 **Security First**: Sandboxed execution with resource limits and path validation
- 🎭 **Stealth Operation**: Human behavior simulation to avoid detection
- 🔌 **Extensible**: Plugin architecture for easy addition of new chatbot platforms
- 💾 **Session Persistence**: Maintains browser sessions to avoid repeated authentication
- 🛡️ **Error Resilience**: Comprehensive error handling with retry logic
- 📊 **Full Observability**: Detailed logging of all operations

## Installation

### From PyPI (when published)

```bash
pip install chatbot-bridge
```

### From Source

```bash
git clone https://github.com/yourusername/chatbot-bridge-automation.git
cd chatbot-bridge-automation
pip install -e .
```

### Install Playwright Browsers

```bash
playwright install chromium
```

## Quick Start

### 1. Create Configuration

```bash
chatbot-bridge config --init
```

This creates a `config.yaml` file. Edit it to set your project root:

```yaml
project_root: /path/to/your/project
sessions_dir: ./sessions
logs_dir: ./logs
headless: false
```

### 2. Start a Session

```bash
chatbot-bridge start --chatbot deepseek
```

The bridge will:
1. Launch a browser window
2. Navigate to the chatbot
3. Monitor the conversation
4. Automatically detect and execute commands
5. Send results back to the chatbot

### 3. Use in Your Code

```python
import asyncio
from chatbot_bridge import ChatbotBridge

async def main():
    async with ChatbotBridge(config_path="config.yaml") as bridge:
        session_id = await bridge.start("deepseek")
        print(f"Session started: {session_id}")
        
        # Bridge monitors automatically
        await asyncio.sleep(3600)  # Run for 1 hour

asyncio.run(main())
```

## How It Works

1. **Monitoring**: Continuously monitors chatbot conversations (every 500-2000ms with random intervals)
2. **Command Extraction**: Detects programming commands in chatbot messages using pattern matching and code block detection
3. **Path Validation**: Ensures all file operations stay within PROJECT_ROOT for security
4. **Safe Execution**: Runs code in isolated subprocesses with resource limits (timeout, memory, CPU)
5. **Result Feedback**: Sends execution results back to the chatbot with human-like typing behavior

## Command Detection

The bridge automatically detects these operations:

### Create File
```
Create a file called `hello.py` with this code:
```python
print("Hello, World!")
```
```

### Execute Code
```
Run this Python code:
```python
import os
print(os.getcwd())
```
```

### Modify File
```
Update the file `config.json` with:
```json
{"debug": true}
```
```

## Configuration

### Basic Configuration

```yaml
# Required
project_root: /path/to/project

# Optional - Directories
sessions_dir: ./sessions
logs_dir: ./logs

# Optional - Browser Settings
headless: false
user_agent: null  # Random if not specified

# Optional - Monitoring
check_interval_range: [500, 2000]  # ms

# Optional - Execution Limits
execution_timeout: 30  # seconds
memory_limit_mb: 512
cpu_limit_percent: 50

# Optional - Human Behavior
typing_delay_range: [50, 150]  # ms
typo_rate: 0.02
pause_range: [500, 3000]  # ms
response_delay_range: [1000, 5000]  # ms

# Optional - CAPTCHA
captcha_api_key: null  # 2captcha API key
captcha_timeout: 120

# Optional - Proxies
proxies: []
proxy_rotation_interval: [10, 20]

# Optional - Error Handling
max_retries: 3
retry_backoff_factor: 2.0
rate_limit_backoff_factor: 2.0
```

### Security Settings

The bridge enforces strict security:

- **Path Validation**: All file operations must be within `project_root`
- **System Path Protection**: Blocks access to `/etc`, `/sys`, `/proc`, `C:\Windows`, etc.
- **Resource Limits**: Execution timeout (30s), memory limit (512MB), CPU limit (50%)
- **Sandboxed Execution**: Code runs in isolated subprocesses

## CLI Commands

### Start Session
```bash
chatbot-bridge start --chatbot deepseek
chatbot-bridge start --chatbot chatgpt --session <session-id>
```

### Stop Session
```bash
chatbot-bridge stop --session <session-id>
```

### List Sessions
```bash
chatbot-bridge list
chatbot-bridge list --chatbot deepseek
```

### Initialize Config
```bash
chatbot-bridge config --init
chatbot-bridge config --init --output custom-config.yaml
```

## Python API

### Basic Usage

```python
from chatbot_bridge import ChatbotBridge

async with ChatbotBridge(config_path="config.yaml") as bridge:
    session_id = await bridge.start("deepseek")
    await asyncio.sleep(3600)
```

### Event Hooks

```python
async def on_command(commands):
    print(f"Detected {len(commands)} commands")

async def on_complete(result):
    print(f"Execution: {result.success}")

async def on_error(error):
    print(f"Error: {error}")

bridge.on_command_detected(on_command)
bridge.on_execution_complete(on_complete)
bridge.on_error(on_error)
```

### Multiple Chatbots

```python
async with ChatbotBridge(config_path="config.yaml") as bridge:
    deepseek_session = await bridge.start("deepseek")
    chatgpt_session = await bridge.start("chatgpt")
    claude_session = await bridge.start("claude")
    
    # All three are monitored simultaneously
    await asyncio.sleep(3600)
```

## Supported Chatbots

| Chatbot | Status | URL |
|---------|--------|-----|
| DeepSeek | ✅ Supported | https://chat.deepseek.com |
| ChatGPT | ✅ Supported | https://chat.openai.com |
| Claude | ✅ Supported | https://claude.ai |

## Troubleshooting

### Browser Not Opening

Make sure Playwright browsers are installed:
```bash
playwright install chromium
```

### CAPTCHA Detected

1. **Manual Mode**: The bridge will pause and wait for you to solve it
2. **Automatic Mode**: Set `captcha_api_key` in config to use 2captcha service

### Commands Not Detected

- Ensure commands use clear keywords: "create file", "run code", "execute"
- Use markdown code blocks with language tags: ` ```python `
- Check logs in `./logs` directory for details

### Path Validation Errors

- All file paths must be within `project_root`
- Use relative paths or absolute paths within project root
- Check that `project_root` in config is correct

## Examples

See the `examples/` directory:

- `basic_usage.py` - Simple session start
- `multi_chatbot.py` - Multiple chatbots simultaneously
- `custom_event_handlers.py` - Event hooks for monitoring

## Development

### Running Tests

```bash
pytest tests/
```

### Adding a New Chatbot Plugin

1. Create a new file in `chatbot_bridge/plugins/`
2. Inherit from `ChatbotPlugin` base class
3. Implement required methods
4. Register in `BridgeSystem.PLUGINS`

See `chatbot_bridge/plugins/deepseek.py` for reference.

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please see CONTRIBUTING.md for guidelines.

## Disclaimer

This tool is for educational and personal use. Ensure you comply with the terms of service of the chatbot platforms you use. The authors are not responsible for any misuse or violations.
