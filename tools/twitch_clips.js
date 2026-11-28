// Usage: NODE_PATH=$(npm root -g) node tools/twitch_clips.js "https://www.twitch.tv/<channel>/clips?filter=clips&range=24hr" > out.json
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36' });
  await p.goto(process.argv[2], { waitUntil: 'domcontentloaded', timeout: 60000 });
  await p.waitForTimeout(8000);
  await p.mouse.move(800,600); for (let i=0;i<15;i++){ await p.mouse.wheel(0,3000); await p.keyboard.press("End"); await p.waitForTimeout(2000); }
  const rows = await p.evaluate(() => [...document.querySelectorAll('article')].map(a => {
     const l=[...a.querySelectorAll('a')].map(x=>x.href); return {links:l, text:a.innerText.replace(/\n+/g,' / ')};}));
  console.log(JSON.stringify(rows));
  await b.close();
})();
