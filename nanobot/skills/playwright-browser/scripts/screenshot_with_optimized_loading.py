#!/usr/bin/env python3
"""
优化的小红书/百度首页截图脚本
解决图片加载不完整问题
"""

import asyncio
import sys
import os
from playwright.async_api import async_playwright

async def optimized_screenshot(url: str, output_path: str):
    """使用优化参数截图，确保图片加载完整"""
    async with async_playwright() as p:
        # 使用 Chromium 浏览器
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-background-networking',
                '--disable-default-apps',
                '--disable-extensions',
                '--disable-sync',
                '--disable-translate',
                '--metrics-recording-only',
                '--no-first-run',
                '--mute-audio',
                '--no-zygote',
                '--window-size=1920,1080'
            ]
        )
        
        # 创建上下文
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            java_script_enabled=True,
            ignore_https_errors=True,
            bypass_csp=True
        )
        
        # 创建页面
        page = await context.new_page()
        
        try:
            # 设置请求拦截器，确保所有资源加载
            await page.route("**/*", lambda route: route.continue_())
            
            # 导航到页面
            print(f"正在访问: {url}")
            await page.goto(url, wait_until='networkidle', timeout=60000)
            
            # 等待页面完全加载
            print("等待页面加载...")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(5)  # 额外等待5秒
            
            # 滚动页面确保所有内容加载
            print("滚动页面...")
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
            
            await asyncio.sleep(2)  # 等待滚动后的内容加载
            
            # 截图
            print(f"正在截图，保存到: {output_path}")
            await page.screenshot(
                path=output_path,
                full_page=True,
                type='png'
            )
            
            print(f"截图完成: {output_path}")
            return True
            
        except Exception as e:
            print(f"截图失败: {e}")
            return False
            
        finally:
            await browser.close()

def main():
    if len(sys.argv) != 3:
        print("用法: python3 screenshot_with_optimized_loading.py <URL> <输出路径>")
        print("示例: python3 screenshot_with_optimized_loading.py https://www.xiaohongshu.com /tmp/xiaohongshu.png")
        sys.exit(1)
    
    url = sys.argv[1]
    output_path = sys.argv[2]
    
    # 运行异步函数
    success = asyncio.run(optimized_screenshot(url, output_path))
    
    if success:
        print(f"截图成功保存到: {output_path}")
        print(f"文件大小: {os.path.getsize(output_path) if os.path.exists(output_path) else 0} bytes")
    else:
        print("截图失败")
        sys.exit(1)

if __name__ == "__main__":
    main()