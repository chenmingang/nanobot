---
name: playwright-browser
description: |
  Modern browser automation using Playwright for fast, reliable web scraping and interaction.
  Features:
  - Navigate to URLs with auto-wait
  - Take screenshots (full page or element)
  - Extract text, HTML, and data
  - Fill forms and click elements
  - Handle dynamic content and SPAs
  - Export PDF
  - Mobile device emulation
  Use when you need reliable browser automation that's faster and more stable than Selenium.
---

# Playwright Browser Automation

## Quick Start

```bash
# Install Playwright
npm install playwright
npx playwright install chromium
```

## Core Functions

### 1. Navigate and Wait

```javascript
const { chromium } = require('playwright');

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext();
const page = await context.newPage();

// Navigate with auto-wait
await page.goto('https://example.com');

// Wait for specific element
await page.waitForSelector('.content', { timeout: 10000 });

// Wait for network idle
await page.goto('https://example.com', { waitUntil: 'networkidle' });
```

### 2. Take Screenshot

```javascript
// Full page screenshot
await page.screenshot({ 
  path: 'screenshot.png',
  fullPage: true 
});

// Element screenshot
const element = await page.locator('.container');
await element.screenshot({ path: 'element.png' });

// Clip region
await page.screenshot({
  path: 'clipped.png',
  clip: { x: 0, y: 0, width: 800, height: 600 }
});
```

### 3. Extract Content

```javascript
// Get page HTML
const html = await page.content();

// Get text content
const text = await page.evaluate(() => document.body.innerText);

// Get specific element text
const title = await page.locator('h1').textContent();

// Get all elements
const links = await page.locator('a').all();
const linkData = await Promise.all(
  links.map(async link => ({
    text: await link.textContent(),
    href: await link.getAttribute('href')
  }))
);
```

### 4. Interact with Elements

```javascript
// Click
await page.locator('#submit').click();

// Type text
await page.locator('#search').fill('search term');

// Press key
await page.locator('#search').press('Enter');

// Select dropdown
await page.locator('#country').selectOption('China');

// Check checkbox
await page.locator('#agree').check();
```

### 5. Handle Dynamic Content

```javascript
// Wait for element to appear
await page.locator('.dynamic').waitFor({ timeout: 10000 });

// Wait for element to disappear
await page.locator('.loading').waitFor({ state: 'hidden' });

// Wait for text
await page.locator('.status').filter({ hasText: 'Ready' }).waitFor();

// Auto-retry assertions
await expect(page.locator('.result')).toHaveText('Success');
```

### 6. Mobile Emulation

```javascript
const context = await browser.newContext({
  viewport: { width: 375, height: 667 },
  userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)...'
});
const page = await context.newPage();
```

### 7. Export PDF

```javascript
await page.pdf({
  path: 'page.pdf',
  format: 'A4',
  printBackground: true
});
```

## Common Patterns

### Pattern 1: Scrape with Retry

```javascript
const { chromium } = require('playwright');

async function scrapeWithRetry(url, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const browser = await chromium.launch();
      const page = await browser.newPage();
      
      await page.goto(url, { timeout: 30000 });
      await page.waitForLoadState('networkidle');
      
      const data = await page.evaluate(() => ({
        title: document.title,
        text: document.body.innerText
      }));
      
      await browser.close();
      return data;
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(r => setTimeout(r, 1000 * (i + 1)));
    }
  }
}
```

### Pattern 2: Login Flow

```javascript
async function loginAndScrape(loginUrl, credentials, targetUrl) {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // Login
  await page.goto(loginUrl);
  await page.locator('#username').fill(credentials.username);
  await page.locator('#password').fill(credentials.password);
  await page.locator('#login-btn').click();
  
  // Wait for navigation
  await page.waitForURL(/dashboard/);
  
  // Save session
  await context.storageState({ path: 'auth.json' });
  
  // Scrape target
  await page.goto(targetUrl);
  const data = await page.locator('.content').allTextContents();
  
  await browser.close();
  return data;
}
```

### Pattern 3: Infinite Scroll

```javascript
async function scrapeInfiniteScroll(url, maxScrolls = 10) {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  await page.goto(url);
  
  for (let i = 0; i < maxScrolls; i++) {
    const previousHeight = await page.evaluate(() => document.body.scrollHeight);
    
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(2000);
    
    const newHeight = await page.evaluate(() => document.body.scrollHeight);
    if (newHeight === previousHeight) break;
  }
  
  const items = await page.locator('.item').allTextContents();
  await browser.close();
  
  return items;
}
```

## Using the Helper Script

This skill includes helper scripts for common operations:

### JavaScript Helper
```bash
# Take screenshot
node scripts/playwright-helper.js screenshot https://example.com output.png

# Extract content
node scripts/playwright-helper.js extract https://example.com output.json

# Full page screenshot
node scripts/playwright-helper.js screenshot https://example.com output.png --full-page

# Mobile screenshot
node scripts/playwright-helper.js screenshot https://example.com mobile.png --mobile

# Wait for selector
node scripts/playwright-helper.js screenshot https://example.com output.png --wait-for ".content"
```

### Python Optimized Screenshot Script
专门解决图片加载不完整问题的优化脚本：

```bash
# 安装依赖
pip install playwright
playwright install chromium

# 使用优化脚本截图（解决图片加载问题）
python3 scripts/screenshot_with_optimized_loading.py https://www.xiaohongshu.com /tmp/xiaohongshu.png
python3 scripts/screenshot_with_optimized_loading.py https://www.baidu.com /tmp/baidu.png
```

优化特性：
1. **反自动化绕过**：禁用自动化检测标志
2. **完整资源加载**：等待网络空闲 + 额外等待时间
3. **页面滚动**：确保所有懒加载内容显示
4. **真实浏览器参数**：使用真实 User-Agent 和完整功能
5. **错误处理**：完善的异常处理和重试机制

## Best Practices

1. **Use locators**: Prefer `page.locator()` over `$` for auto-waiting and retry
2. **Auto-close**: Use `try/finally` or `using` pattern
3. **Set timeouts**: Prevent hanging on slow pages
4. **Reuse context**: Share cookies/session between pages
5. **Handle dialogs**: Listen for `dialog` events
6. **Respect rate limits**: Add delays between requests

## Comparison with Selenium

| Feature | Playwright | Selenium |
|---------|------------|----------|
| Speed | 🚀 Faster | ⚡ Slower |
| Stability | ✅ Auto-wait | ⚠️ Manual wait |
| API | Modern, clean | Verbose |
| Mobile | Built-in | Limited |
| Trace/Debug | Built-in | Limited |
| PDF | Built-in | Requires extra |

## 快速使用指南

### 安装依赖
```bash
# 安装 Playwright Python 包
pip install playwright

# 安装 Chromium 浏览器
playwright install chromium

# 安装 Node.js 版本（可选）
npm install playwright
npx playwright install chromium
```

### 基础截图
```bash
# 使用 Python 优化脚本（推荐）
python3 scripts/screenshot_with_optimized_loading.py https://www.xiaohongshu.com xiaohongshu.png

# 使用 JavaScript 脚本
node scripts/playwright-helper.js screenshot https://www.baidu.com baidu.png --full-page
```

### 常见问题解决

#### 问题：图片加载不完整
**解决方案**：
1. 使用优化脚本：`screenshot_with_optimized_loading.py`
2. 增加等待时间：修改脚本中的 `await asyncio.sleep(5)` 为更长值
3. 确保网络正常：检查代理和防火墙设置

#### 问题：被网站检测为自动化访问
**解决方案**：
1. 使用优化脚本中的反检测参数
2. 更换 User-Agent
3. 添加随机延迟

#### 问题：内存占用过高
**解决方案**：
1. 使用 `headless: true`
2. 及时关闭浏览器实例
3. 减少同时打开的页面数

## 优化截图脚本（Python）

### 脚本位置
`scripts/screenshot_with_optimized_loading.py`

### 使用示例
```bash
# 截图小红书首页（解决图片加载问题）
python3 scripts/screenshot_with_optimized_loading.py https://www.xiaohongshu.com /tmp/xiaohongshu.png

# 截图百度首页
python3 scripts/screenshot_with_optimized_loading.py https://www.baidu.com /tmp/baidu.png

# 截图任意网站
python3 scripts/screenshot_with_optimized_loading.py "https://example.com" "/path/to/output.png"
```

### 脚本特性
1. **反爬虫绕过**：
   - 禁用自动化检测标志
   - 使用真实 User-Agent
   - 禁用 WebDriver 标志

2. **完整资源加载**：
   - 等待网络空闲状态
   - 额外等待 5 秒确保图片加载
   - 自动滚动页面触发懒加载

3. **浏览器配置优化**：
   - 禁用沙盒和安全限制
   - 启用所有网络请求
   - 设置合理视窗大小

4. **错误处理**：
   - 完善的异常捕获
   - 超时处理
   - 资源清理

### 适用场景
- 小红书、微博等图片密集型网站
- 百度、淘宝等动态加载网站
- 需要完整截图的单页应用
- 反爬虫严格的网站

## 注意事项

### 图片加载问题解决
如果遇到图片加载不完整的问题：
1. 使用 `screenshot_with_optimized_loading.py` 脚本
2. 增加等待时间（修改脚本中的 `await asyncio.sleep(5)`）
3. 确保网络连接正常
4. 检查目标网站是否屏蔽自动化访问

### 性能优化
- 对于静态网站，可减少等待时间
- 对于动态网站，适当增加等待时间
- 使用 `headless: true` 减少资源占用
- 复用浏览器实例处理多个页面

## Resources

- [Playwright Docs](https://playwright.dev/)
- [API Reference](https://playwright.dev/docs/api/class-page)
- [Best Practices](https://playwright.dev/docs/best-practices)
