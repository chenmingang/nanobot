---
name: browser-screenshot
description: Take screenshots of webpages with optimized loading and anti-detection bypass.
homepage: https://playwright.dev/docs/screenshots
metadata: {"nanobot":{"emoji":"📸","requires":{"bins":["python3","playwright"],"python_packages":["playwright"]}}}
---

# Browser Screenshot Skill

Take high-quality screenshots of webpages with optimized loading and anti-detection bypass.

## Features

- **Optimized loading**: Waits for network idle and lazy-loaded content
- **Anti-detection bypass**: Uses various techniques to avoid bot detection
- **Full-page screenshots**: Captures entire webpage, not just viewport
- **Scroll simulation**: Automatically scrolls to load all content
- **Multiple formats**: Supports PNG format

## Installation

```bash
# Install playwright if not already installed
playwright install chromium
```

## Usage Examples

### Basic screenshot (simple script)
```bash
python3 scripts/screenshot.py https://www.baidu.com /tmp/baidu.png
```

### Screenshot with default output path
```bash
python3 scripts/screenshot.py https://www.google.com
# Output: /tmp/www_google_com_screenshot.png
```

### Advanced screenshot (optimized loading)
```bash
python3 scripts/screenshot_with_optimized_loading.py https://www.netease.com /tmp/netease.png
```

### Direct from command line
```bash
cd /root/work/nanobot/nanobot/skills/browser-screenshot/scripts
python3 screenshot.py https://github.com /tmp/github.png
```

## Python API

```python
import asyncio
from playwright.async_api import async_playwright

async def take_screenshot(url: str, output_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        await page.goto(url, wait_until='networkidle')
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(3)  # Extra wait
        
        # Scroll to load lazy content
        await page.evaluate("""
            async () => {
                await new Promise(resolve => {
                    let totalHeight = 0;
                    const distance = 100;
                    const timer = setInterval(() => {
                        const scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        
                        if (totalHeight >= scrollHeight) {
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        """)
        
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()
```

## Configuration Options

### Browser Arguments
- `--disable-blink-features=AutomationControlled`: Hide automation indicators
- `--disable-dev-shm-usage`: Fix Docker memory issues
- `--no-sandbox`: Disable sandbox for container environments
- `--window-size=1920,1080`: Set window size

### Context Settings
- `viewport`: Set viewport size
- `user_agent`: Custom user agent to avoid detection
- `java_script_enabled`: Enable JavaScript
- `ignore_https_errors`: Ignore SSL errors
- `bypass_csp`: Bypass Content Security Policy

## Troubleshooting

### Common Issues

1. **Images not loading**: Increase the `await asyncio.sleep()` duration
2. **Bot detection**: Try different user agents or disable certain features
3. **Memory issues**: Use `--disable-dev-shm-usage` argument
4. **Timeout errors**: Increase timeout in `page.goto()`

### Debug Mode
Add `headless=False` to see browser window:
```python
browser = await p.chromium.launch(headless=False)
```

## Integration with nanobot

This skill can be integrated into nanobot workflows:
- Automated website monitoring
- Content verification
- Visual regression testing
- Website archiving

### Example: Using from nanobot agent
```python
import subprocess
import os

def take_website_screenshot(url):
    """Take screenshot of website using browser-screenshot skill"""
    script_path = "/root/work/nanobot/nanobot/skills/browser-screenshot/scripts/screenshot.py"
    domain = url.split('//')[-1].split('/')[0].replace('.', '_')
    output_path = f"/tmp/{domain}_screenshot.png"
    
    cmd = ["python3", script_path, url, output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        return output_path
    else:
        return None

# Usage in nanobot agent
screenshot_path = take_website_screenshot("https://www.example.com")
if screenshot_path:
    print(f"Screenshot saved: {screenshot_path}")
    # Can send screenshot via message tool
    # message(content="Screenshot taken", media=[screenshot_path])
```