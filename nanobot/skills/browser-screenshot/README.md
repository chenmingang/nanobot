# Browser Screenshot Skill

A skill for taking high-quality screenshots of webpages with optimized loading and anti-detection bypass.

## Features

- **Optimized loading**: Waits for network idle and lazy-loaded content
- **Anti-detection bypass**: Uses various techniques to avoid bot detection
- **Full-page screenshots**: Captures entire webpage, not just viewport
- **Scroll simulation**: Automatically scrolls to load all content
- **Multiple formats**: Supports PNG format
- **Simple API**: Easy to use from command line or Python code

## Installation

### Prerequisites
```bash
# Install playwright
pip install playwright
playwright install chromium
```

### Skill Installation
The skill is already installed in the nanobot skills directory:
```
/root/work/nanobot/nanobot/skills/browser-screenshot/
```

## Quick Start

### Command Line Usage
```bash
# Simple screenshot
python3 scripts/screenshot.py https://www.baidu.com /tmp/baidu.png

# With default output path
python3 scripts/screenshot.py https://www.google.com

# Advanced optimized screenshot
python3 scripts/screenshot_with_optimized_loading.py https://www.netease.com /tmp/netease.png
```

### Python Integration
```python
import asyncio
import sys
sys.path.append('/root/work/nanobot/nanobot/skills/browser-screenshot/scripts')
from screenshot import take_screenshot

# Take screenshot
output_path = asyncio.run(take_screenshot("https://example.com"))
print(f"Screenshot saved to: {output_path}")
```

## API Reference

### `take_screenshot(url: str, output_path: str = None) -> str`
Take a screenshot of a webpage.

**Parameters:**
- `url` (str): The URL to screenshot
- `output_path` (str, optional): Output file path. If None, generates default path.

**Returns:**
- `str`: Path to saved screenshot file, or None on error

### `optimized_screenshot(url: str, output_path: str) -> bool`
Advanced screenshot with optimized loading and anti-detection.

**Parameters:**
- `url` (str): The URL to screenshot
- `output_path` (str): Output file path

**Returns:**
- `bool`: True if successful, False otherwise

## Configuration

### Browser Arguments
The scripts use optimized browser arguments:
- `--disable-blink-features=AutomationControlled`: Hide automation indicators
- `--disable-dev-shm-usage`: Fix Docker memory issues
- `--no-sandbox`: Disable sandbox for container environments
- `--window-size=1920,1080`: Set window size

### Context Settings
- `viewport`: Set viewport size (1920x1080)
- `user_agent`: Custom user agent to avoid detection
- `java_script_enabled`: Enable JavaScript
- `ignore_https_errors`: Ignore SSL errors

## Examples

### Example 1: Basic Screenshot
```bash
python3 scripts/screenshot.py https://www.github.com /tmp/github.png
```

### Example 2: Batch Screenshots
```bash
#!/bin/bash
URLS=(
    "https://www.baidu.com"
    "https://www.google.com"
    "https://www.github.com"
)

for url in "${URLS[@]}"; do
    domain=$(echo $url | sed 's|https://||' | sed 's|/|_|g')
    python3 scripts/screenshot.py "$url" "/tmp/${domain}.png"
done
```

### Example 3: Integration with nanobot
```python
# In nanobot skill or agent code
import subprocess
import os

def screenshot_website(url, output_dir="/tmp"):
    """Take screenshot and return file path"""
    domain = url.split('//')[-1].split('/')[0].replace('.', '_')
    output_path = f"{output_dir}/{domain}.png"
    
    cmd = [
        "python3",
        "/root/work/nanobot/nanobot/skills/browser-screenshot/scripts/screenshot.py",
        url,
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0 and os.path.exists(output_path):
        return output_path
    else:
        return None
```

## Troubleshooting

### Common Issues

1. **Playwright not installed**
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. **Images not loading completely**
   - Increase wait time in script
   - Check network connectivity
   - Try the optimized version

3. **Bot detection**
   - Script includes anti-detection measures
   - Try changing user agent
   - Add random delays

4. **Memory issues**
   - Use `--disable-dev-shm-usage` argument
   - Close browser properly after use
   - Reduce viewport size if needed

### Debug Mode
To debug issues, modify the script to run in non-headless mode:
```python
# Change this line in screenshot.py
browser = await p.chromium.launch(headless=False)  # Set to False
```

## File Structure
```
browser-screenshot/
├── SKILL.md                    # Skill metadata
├── README.md                   # This documentation
└── scripts/
    ├── screenshot.py           # Simple screenshot script
    └── screenshot_with_optimized_loading.py  # Advanced script
```

## License
This skill is part of the nanobot project.