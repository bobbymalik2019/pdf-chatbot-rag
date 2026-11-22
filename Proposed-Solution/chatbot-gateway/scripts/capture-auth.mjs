/**
 * Opens a REAL Chrome login session; saves only Playwright browser state
 * in a gitignored file. Never output cookies or access tokens.
 */
import { chromium } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
const user = process.argv.includes('--user=b') ? 'b' : 'a';
const baseURL = (process.env.TEST_GATEWAY_URL || 'https://chatbottest.charter26.com').replace(/\/+$/, '');
const output = resolve(`playwright/.auth/user-${user}.json`);
mkdirSync(resolve('playwright/.auth'), {recursive:true});
const browser = await chromium.launch({
  channel: process.env.PW_BROWSER_CHANNEL || 'chrome',
  headless: false,
});
const context = await browser.newContext({ ignoreHTTPSErrors: false });
const page = await context.newPage();
console.log(`Log in to ${baseURL} as test user ${user.toUpperCase()}.`);
console.log('The browser will close after authentication is detected.');
try {
  await page.goto(baseURL, {waitUntil: 'domcontentloaded', timeout: 30000});
  const deadline = Date.now() + 180000;
  let authenticated = false;
  while (Date.now() < deadline) {
    try {
      const response = await context.request.get(`${baseURL}/auth/me`, {timeout:5000});
      if (response.status() === 200) {
        const data = await response.json();
        if (data.authenticated === true) { authenticated = true; break; }
      }
    } catch { /* login may be in progress */ }
    await page.waitForTimeout(1000);
  }
  if (!authenticated) throw new Error('Authentication not detected in 3 minutes');
  await context.storageState({path:output});
  console.log(`Saved test session locally: ${output}`);
  console.log('Treat this file like a password. Do NOT commit or share it.');
} finally {
  await browser.close();
}
