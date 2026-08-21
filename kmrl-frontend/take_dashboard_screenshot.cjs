const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('http://localhost:3000/dashboard');
  
  // Wait for boot screen to finish and dashboard to load
  await page.waitForTimeout(4000);

  // Take screenshot of dashboard
  await page.screenshot({ path: path.join('C:', 'Users', 'abhig', '.gemini', 'antigravity-ide', 'brain', '0735d45c-6560-4242-adf3-4cf86003c508', 'dashboard_live_plan.png'), fullPage: true });

  await browser.close();
})();
