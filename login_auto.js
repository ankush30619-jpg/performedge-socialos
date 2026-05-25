const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    headless: false,
    defaultViewport: null,
    args: ['--start-maximized']
  });
  const [page] = await browser.pages();
  await page.goto('http://localhost:3000/auth/login', {waitUntil:'networkidle2'});
  await page.waitForSelector('input[type=email]');
  await page.click('input[type=email]', {clickCount:3});
  await page.type('input[type=email]', 'pe.ankushmehra@gmail.com');
  await page.click('input[type=password]', {clickCount:3});
  await page.type('input[type=password]', 'SocialOS@2024');
  await Promise.all([
    page.waitForNavigation({waitUntil:'networkidle2', timeout:12000}),
    page.click('button[type=submit]')
  ]);
  console.log('DONE:' + page.url());
  await new Promise(r => setTimeout(r, 90000));
  await browser.close();
})().catch(e => { console.error('ERR:'+e.message); });
