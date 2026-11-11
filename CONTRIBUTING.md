# Contributing to Chatbot Bridge Automation

Thank you for your interest in contributing! This document provides guidelines for development and contributions.

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/chatbot-bridge-automation.git
cd chatbot-bridge-automation
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -e ".[dev]"
playwright install chromium
```

### 4. Run Tests

```bash
pytest tests/
```

## Project Structure

```
chatbot-bridge-automation/
├── chatbot_bridge/
│   ├── core/              # Core logic components
│   │   ├── config.py      # Configuration management
│   │   ├── path_validator.py
│   │   ├── command_extractor.py
│   │   ├── code_executor.py
│   │   ├── session_manager.py
│   │   ├── chatbot_monitor.py
│   │   └── bridge_system.py
│   ├── automation/        # Browser automation
│   │   ├── browser.py
│   │   ├── human_behavior.py
│   │   ├── proxy_manager.py
│   │   └── captcha_resolver.py
│   ├── plugins/           # Chatbot plugins
│   │   ├── base.py
│   │   ├── deepseek.py
│   │   ├── chatgpt.py
│   │   └── claude.py
│   ├── utils/             # Utilities
│   │   └── logger.py
│   ├── cli.py             # CLI interface
│   └── api.py             # Python API
├── tests/                 # Test suite
├── examples/              # Example scripts
├── docs/                  # Documentation
└── pyproject.toml         # Package configuration
```

## Adding a New Chatbot Plugin

### 1. Create Plugin File

Create a new file in `chatbot_bridge/plugins/`:

```python
# chatbot_bridge/plugins/my_chatbot.py

from typing import List
from playwright.async_api import Page
from .base import ChatbotPlugin


class MyChatbotPlugin(ChatbotPlugin):
    """Plugin for My Chatbot platform."""
    
    @property
    def name(self) -> str:
        return "my_chatbot"
    
    @property
    def url(self) -> str:
        return "https://my-chatbot.com"
    
    async def navigate_to_chat(self, page: Page) -> None:
        await page.goto(self.url, wait_until='networkidle')
    
    async def get_message_selectors(self) -> List[str]:
        return [
            '.message-content',
            '[data-role="assistant"]',
        ]
    
    async def get_input_selectors(self) -> List[str]:
        return [
            'textarea[placeholder*="Message"]',
            'textarea',
        ]
    
    async def send_message(
        self,
        page: Page,
        message: str,
        human_behavior: any
    ) -> bool:
        # Implementation here
        pass
    
    async def wait_for_response(
        self,
        page: Page,
        timeout: int = 60000
    ) -> bool:
        # Implementation here
        pass
```

### 2. Register Plugin

Add to `chatbot_bridge/core/bridge_system.py`:

```python
from ..plugins.my_chatbot import MyChatbotPlugin

class BridgeSystem:
    PLUGINS = {
        'deepseek': DeepSeekPlugin,
        'chatgpt': ChatGPTPlugin,
        'claude': ClaudePlugin,
        'my_chatbot': MyChatbotPlugin,  # Add here
    }
```

### 3. Test Plugin

Create tests in `tests/plugins/test_my_chatbot.py`:

```python
import pytest
from chatbot_bridge.plugins.my_chatbot import MyChatbotPlugin


def test_plugin_properties():
    plugin = MyChatbotPlugin()
    assert plugin.name == "my_chatbot"
    assert plugin.url == "https://my-chatbot.com"


@pytest.mark.asyncio
async def test_selectors():
    plugin = MyChatbotPlugin()
    message_selectors = await plugin.get_message_selectors()
    assert len(message_selectors) > 0
```

## Testing Guidelines

### Unit Tests

- Test individual components in isolation
- Mock external dependencies (browser, network)
- Use pytest fixtures for common setup

```python
import pytest
from chatbot_bridge.core.path_validator import PathValidator


def test_path_within_root(tmp_path):
    validator = PathValidator(str(tmp_path))
    
    test_file = tmp_path / "test.txt"
    is_valid, abs_path, error = validator.validate_path(str(test_file))
    
    assert is_valid
    assert error is None
```

### Integration Tests

- Test component interactions
- Use real browser instances (with Playwright)
- Mark as slow: `@pytest.mark.slow`

```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_browser_automation():
    automation = BrowserAutomation(headless=True)
    browser = await automation.launch_browser()
    # Test browser operations
    await automation.close()
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/core/test_path_validator.py

# Run with coverage
pytest --cov=chatbot_bridge

# Skip slow tests
pytest -m "not slow"
```

## Code Style

### Python Style Guide

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use docstrings for all public functions/classes

```python
def validate_path(self, path: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate that path is safe and within project root.
    
    Args:
        path: File path to validate (relative or absolute)
        
    Returns:
        Tuple of (is_valid, absolute_path, error_message)
    """
    pass
```

### Formatting

Use `black` for code formatting:

```bash
black chatbot_bridge/
```

### Linting

Use `flake8` for linting:

```bash
flake8 chatbot_bridge/
```

## Documentation

### Docstrings

Use Google-style docstrings:

```python
def my_function(arg1: str, arg2: int) -> bool:
    """
    Brief description of function.
    
    Longer description if needed.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When something is invalid
    """
    pass
```

### README Updates

When adding features, update:
- README.md - User-facing documentation
- CONTRIBUTING.md - Developer documentation
- Examples in `examples/` directory

## Pull Request Process

### 1. Create Branch

```bash
git checkout -b feature/my-new-feature
```

### 2. Make Changes

- Write code
- Add tests
- Update documentation

### 3. Run Tests

```bash
pytest
black chatbot_bridge/
flake8 chatbot_bridge/
```

### 4. Commit Changes

Use clear commit messages:

```bash
git commit -m "Add support for new chatbot platform"
```

### 5. Push and Create PR

```bash
git push origin feature/my-new-feature
```

Then create a pull request on GitHub.

### PR Checklist

- [ ] Tests pass
- [ ] Code is formatted (black)
- [ ] No linting errors (flake8)
- [ ] Documentation updated
- [ ] Examples added (if applicable)
- [ ] CHANGELOG.md updated

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create git tag: `git tag v1.0.0`
4. Push tag: `git push origin v1.0.0`
5. Build package: `python -m build`
6. Upload to PyPI: `twine upload dist/*`

## Getting Help

- Open an issue on GitHub
- Join our Discord server (link)
- Email: support@example.com

## Code of Conduct

Be respectful and inclusive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/).

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
