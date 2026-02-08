#!/usr/bin/env python3
"""
Optimized screenshot tool for web pages with proper image loading.
Based on lessons learned from previous screenshot issues.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional, List

class ScreenshotOptimizer:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.timeout = 30  # seconds
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def take_screenshot(self, url: str, output_path: str, 
                       wait_time: int = 5, 
                       viewport_width: int = 1920,
                       viewport_height: int = 1080) -> bool:
        """
        Take a screenshot of a webpage with optimized settings for image loading.
        
        Args:
            url: The URL to screenshot
            output_path: Path to save the screenshot
            wait_time: Time to wait for page load (seconds)
            viewport_width: Viewport width in pixels
            viewport_height: Viewport height in pixels
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Create output directory if it doesn't exist
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Use Playwright CLI for reliable screenshots
        command = [
            "playwright", "screenshot",
            url,
            output_path,
            f"--wait-for-timeout={wait_time * 1000}",  # Convert to milliseconds
            f"--viewport-size={viewport_width},{viewport_height}",
            "--full-page",
            "--color-scheme=light"
        ]
        
        if self.headless:
            command.append("--headless")
        
        # Add user agent for better compatibility
        command.extend(["--user-agent", self.user_agent])
        
        # Add additional options for better image loading
        command.extend([
            "--ignore-https-errors",  # Ignore SSL errors
            "--timeout=30000",  # 30 second timeout
        ])
        
        try:
            print(f"Taking screenshot of {url}...")
            print(f"Command: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                print(f"Screenshot saved to: {output_path}")
                
                # Verify the file was created and has content
                if Path(output_path).exists():
                    file_size = Path(output_path).stat().st_size
                    print(f"File size: {file_size} bytes")
                    
                    if file_size > 1024:  # At least 1KB
                        return True
                    else:
                        print("Warning: Screenshot file is too small")
                        return False
                else:
                    print("Error: Screenshot file was not created")
                    return False
            else:
                print(f"Playwright error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"Timeout after {self.timeout} seconds")
            return False
        except FileNotFoundError:
            print("Error: Playwright not found. Please install with: pip install playwright && playwright install")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False
    
    def take_screenshot_with_retry(self, url: str, output_path: str, 
                                  max_retries: int = 3) -> bool:
        """
        Take screenshot with retry logic for better reliability.
        
        Args:
            url: The URL to screenshot
            output_path: Path to save the screenshot
            max_retries: Maximum number of retry attempts
        
        Returns:
            bool: True if successful, False otherwise
        """
        for attempt in range(max_retries):
            print(f"Attempt {attempt + 1}/{max_retries}")
            
            # Increase wait time on each retry
            wait_time = 3 + (attempt * 2)  # 3, 5, 7 seconds
            
            # Try different viewport sizes
            if attempt == 1:
                viewport_width, viewport_height = 1366, 768
            elif attempt == 2:
                viewport_width, viewport_height = 1024, 768
            else:
                viewport_width, viewport_height = 1920, 1080
            
            success = self.take_screenshot(
                url=url,
                output_path=output_path,
                wait_time=wait_time,
                viewport_width=viewport_width,
                viewport_height=viewport_height
            )
            
            if success:
                return True
            
            # Wait before retry
            if attempt < max_retries - 1:
                print(f"Retrying in 2 seconds...")
                time.sleep(2)
        
        return False
    
    def take_screenshot_with_custom_js(self, url: str, output_path: str,
                                      js_script: Optional[str] = None) -> bool:
        """
        Take screenshot with custom JavaScript execution.
        
        Args:
            url: The URL to screenshot
            output_path: Path to save the screenshot
            js_script: JavaScript to execute before taking screenshot
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Create a temporary Python script with custom logic
        temp_script = "/tmp/screenshot_custom.py"
        
        script_content = f'''#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # Launch browser with optimized settings
        browser = await p.chromium.launch(
            headless={self.headless},
            args=[
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
            ]
        )
        
        # Create context with custom user agent
        context = await browser.new_context(
            viewport={{'width': 1920, 'height': 1080}},
            user_agent='{self.user_agent}',
            ignore_https_errors=True,
            color_scheme='light'
        )
        
        page = await context.new_page()
        
        try:
            # Navigate to URL
            await page.goto('{url}', wait_until='networkidle', timeout=30000)
            
            # Wait for additional time
            await page.wait_for_timeout(5000)
            
            # Execute custom JavaScript if provided
            {f"await page.evaluate('''{js_script}''')" if js_script else "# No custom JS"}
            
            # Take screenshot
            await page.screenshot(path='{output_path}', full_page=True)
            print(f"Screenshot saved to: {{'{output_path}'}}")
            
        except Exception as e:
            print(f"Error: {{e}}")
            return False
        finally:
            await browser.close()
        
        return True

if __name__ == '__main__':
    result = asyncio.run(main())
    exit(0 if result else 1)
'''
        
        try:
            with open(temp_script, 'w') as f:
                f.write(script_content)
            
            # Make script executable
            os.chmod(temp_script, 0o755)
            
            # Run the script
            result = subprocess.run(
                [sys.executable, temp_script],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            # Clean up
            if Path(temp_script).exists():
                os.remove(temp_script)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error with custom script: {e}")
            return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Take optimized screenshots of web pages")
    parser.add_argument("url", help="URL to screenshot")
    parser.add_argument("output", help="Output file path")
    parser.add_argument("--wait", type=int, default=5, help="Wait time in seconds (default: 5)")
    parser.add_argument("--retry", type=int, default=3, help="Max retry attempts (default: 3)")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode")
    parser.add_argument("--custom-js", help="Custom JavaScript to execute before screenshot")
    
    args = parser.parse_args()
    
    optimizer = ScreenshotOptimizer(headless=args.headless)
    
    if args.custom_js:
        success = optimizer.take_screenshot_with_custom_js(
            url=args.url,
            output_path=args.output,
            js_script=args.custom_js
        )
    else:
        success = optimizer.take_screenshot_with_retry(
            url=args.url,
            output_path=args.output,
            max_retries=args.retry
        )
    
    if success:
        print(f"✓ Screenshot successfully saved to {args.output}")
        sys.exit(0)
    else:
        print(f"✗ Failed to take screenshot")
        sys.exit(1)

if __name__ == "__main__":
    main()