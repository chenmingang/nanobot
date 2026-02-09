#!/usr/bin/env node
/**
 * Playwright Helper Script
 * Common browser automation tasks
 */

const { chromium, devices } = require('playwright');
const fs = require('fs');
const path = require('path');

async function takeScreenshot(url, outputPath, options = {}) {
  const browser = await chromium.launch({ headless: true });
  
  try {
    const contextOptions = options.mobile ? { ...devices['iPhone 14'] } : {};
    const context = await browser.newContext(contextOptions);
    const page = await context.newPage();
    
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    
    if (options.waitFor) {
      await page.locator(options.waitFor).waitFor({ timeout: 10000 });
    }
    
    if (options.delay) {
      await page.waitForTimeout(parseInt(options.delay));
    }
    
    await page.screenshot({
      path: outputPath,
      fullPage: options.fullPage || false
    });
    
    console.log(`Screenshot saved: ${outputPath}`);
    return { success: true, path: outputPath };
  } finally {
    await browser.close();
  }
}

async function extractContent(url, outputPath, options = {}) {
  const browser = await chromium.launch({ headless: true });
  
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    
    if (options.waitFor) {
      await page.locator(options.waitFor).waitFor({ timeout: 10000 });
    }
    
    const data = await page.evaluate(() => {
      const results = [];
      const items = document.querySelectorAll('.note-item, .feed-item, article, .post');
      
      items.forEach((item, index) => {
        const title = item.querySelector('h1, h2, h3, .title, [class*="title"]');
        const content = item.querySelector('p, .content, [class*="content"], [class*="desc"]');
        const author = item.querySelector('.author, [class*="author"], [class*="user"]');
        const likes = item.querySelector('.like, [class*="like"], [class*="vote"]');
        
        if (title || content) {
          results.push({
            index: index + 1,
            title: title ? title.innerText.trim() : '',
            content: content ? content.innerText.trim().substring(0, 200) : '',
            author: author ? author.innerText.trim() : '',
            likes: likes ? likes.innerText.trim() : ''
          });
        }
      });
      
      return {
        url: window.location.href,
        title: document.title,
        items: results.length > 0 ? results : [{
          index: 1,
          title: document.title,
          content: document.body.innerText.substring(0, 500),
          author: '',
          likes: ''
        }]
      };
    });
    
    fs.writeFileSync(outputPath, JSON.stringify(data, null, 2));
    console.log(`Content extracted: ${outputPath}`);
    return { success: true, path: outputPath, data };
  } finally {
    await browser.close();
  }
}

async function exportPDF(url, outputPath, options = {}) {
  const browser = await chromium.launch({ headless: true });
  
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    
    if (options.waitFor) {
      await page.locator(options.waitFor).waitFor({ timeout: 10000 });
    }
    
    await page.pdf({
      path: outputPath,
      format: 'A4',
      printBackground: true
    });
    
    console.log(`PDF exported: ${outputPath}`);
    return { success: true, path: outputPath };
  } finally {
    await browser.close();
  }
}

// CLI
const [,, command, url, output, ...args] = process.argv;

const options = {};
args.forEach((arg, i) => {
  if (arg === '--full-page') options.fullPage = true;
  if (arg === '--mobile') options.mobile = true;
  if (arg === '--wait-for' && args[i + 1]) options.waitFor = args[i + 1];
  if (arg === '--delay' && args[i + 1]) options.delay = args[i + 1];
});

if (!command || !url || !output) {
  console.log(`
Usage: node playwright-helper.js <command> <url> <output> [options]

Commands:
  screenshot <url> <output.png>   Take screenshot
  extract <url> <output.json>     Extract page content
  pdf <url> <output.pdf>          Export as PDF

Options:
  --full-page          Capture full page
  --mobile             Use mobile viewport
  --wait-for <selector> Wait for element before capture
  --delay <ms>         Delay before capture (milliseconds)

Examples:
  node playwright-helper.js screenshot https://example.com screenshot.png
  node playwright-helper.js screenshot https://example.com full.png --full-page
  node playwright-helper.js extract https://xiaohongshu.com content.json --wait-for ".note-item"
`);
  process.exit(1);
}

(async () => {
  try {
    switch (command) {
      case 'screenshot':
        await takeScreenshot(url, output, options);
        break;
      case 'extract':
        await extractContent(url, output, options);
        break;
      case 'pdf':
        await exportPDF(url, output, options);
        break;
      default:
        console.error(`Unknown command: ${command}`);
        process.exit(1);
    }
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
})();
