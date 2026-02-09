#!/usr/bin/env python3
"""
Simple webpage screenshot tool for nanobot
Usage: python3 screenshot.py <url> [output_path]
"""

import asyncio
import sys
import os
from playwright.async_api import async_playwright

async def take_screenshot(url: str, output_path: str = None):
    """Take a screenshot of a webpage"""
    if output_path is None:
        # Generate default output path
        domain = url.split('//')[-1].split('/')[0].replace('.', '_')
        output_path = f"/tmp/{domain}_screenshot.png"
    
    async with async_playwright() as p:
        # Launch browser with optimized settings
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--window-size=1920,1080'
            ]
        )
        
        # Create context
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            java_script_enabled=True,
            ignore_https_errors=True
        )
        
        # Create page
        page = await context.new_page()
        
        try:
            print(f"🌐 Navigating to: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            print("⏳ Waiting for page to load...")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)  # Extra wait
            
            print("🖱️ Scrolling to load all content...")
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
            
            await asyncio.sleep(2)  # Wait for content after scrolling
            
            print(f"📸 Taking screenshot: {output_path}")
            await page.screenshot(
                path=output_path,
                full_page=True,
                type='png'
            )
            
            # Check file size
            file_size = os.path.getsize(output_path)
            print(f"✅ Screenshot saved: {output_path} ({file_size:,} bytes)")
            
            return output_path
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
            
        finally:
            await browser.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 screenshot.py <url> [output_path]")
        print("Example: python3 screenshot.py https://www.baidu.com /tmp/baidu.png")
        sys.exit(1)
    
    url = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Run async function
    result = asyncio.run(take_screenshot(url, output_path))
    
    if result:
        print(f"\n📁 Screenshot saved to: {result}")
        print(f"📊 File size: {os.path.getsize(result):,} bytes")
    else:
        print("Failed to take screenshot")
        sys.exit(1)

if __name__ == "__main__":
    main()