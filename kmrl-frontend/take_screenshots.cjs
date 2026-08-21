const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('http://localhost:3000/');
  
  // Wait for the app to settle
  await page.waitForTimeout(2000);

  // Take screenshot of problem section
  const problemHandle = await page.$('.lp-problem');
  if (problemHandle) {
    await problemHandle.screenshot({ path: path.join('C:', 'Users', 'abhig', '.gemini', 'antigravity-ide', 'brain', '0735d45c-6560-4242-adf3-4cf86003c508', 'tech_specs_block.png') });
  }

  // Click Aluva to bring up info card with new headway
  await page.evaluate(() => {
    document.querySelector('.nm-chip').click();
  });
  await page.waitForTimeout(1000);

  // Take screenshot of network map section
  const mapHandle = await page.$('.nm-section');
  if (mapHandle) {
    await mapHandle.screenshot({ path: path.join('C:', 'Users', 'abhig', '.gemini', 'antigravity-ide', 'brain', '0735d45c-6560-4242-adf3-4cf86003c508', 'map_info_card.png') });
  }

  await browser.close();
})();
