// app/index.html 을 실제 브라우저로 열어 콘솔 오류·가로 넘침을 확인하고 스크린샷을 남긴다.
const { chromium } = require("playwright");
const http = require("http"), fs = require("fs"), path = require("path");
const APP = path.resolve(__dirname, "..", "..", "app"), OUT = process.env.OUT_DIR || require("os").tmpdir();
const skeleton = (body) => `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light}body{margin:0;font:14px system-ui;background:#f8f8f6}img{max-width:100%}[hidden]{display:none!important}</style></head><body>${body}</body></html>`;
const srv = http.createServer((req, res) => {
  const p = req.url === "/" ? "index.html" : decodeURIComponent(req.url.slice(1));
  const f = path.join(APP, p);
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  let body = fs.readFileSync(f);
  if (p === "index.html") body = skeleton(body.toString());
  res.writeHead(200, { "content-type": p.endsWith(".json") ? "application/json" : p.endsWith(".js") ? "text/javascript" : "text/html; charset=utf-8" });
  res.end(body);
}).listen(8765, async () => {
  const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" });
  for (const [name, w, scheme] of [["desktop-light", 1100, "light"], ["phone-dark", 390, "dark"]]) {
    const page = await browser.newPage({ viewport: { width: w, height: 900 }, colorScheme: scheme });
    const errs = []; page.on("console", (m) => m.type() === "error" && errs.push(m.text())); page.on("pageerror", (e) => errs.push(String(e)));
    await page.goto("http://localhost:8765/"); await page.waitForTimeout(1500);
    // 사용자 사례로도 한 번: 범위 입력 + ENFP-T
    if (name === "phone-dark") {
      await page.fill("#date", "1973-12-16"); await page.selectOption("#sex", ""); await page.selectOption("#place", "");
      await page.fill("#t1", "10:00"); await page.fill("#t2", "11:59"); await page.fill("#mbti", "ENFP-T"); await page.click("#go"); await page.waitForTimeout(800);
    }
    const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    const text = await page.evaluate(() => document.querySelector("#out").innerText.slice(0, 400));
    await page.screenshot({ path: path.join(OUT, `shot-${name}.png`), fullPage: true });
    console.log(name, "overflowX:", over, "errors:", errs, "\n", text.replace(/\n+/g, " | "));
    await page.close();
  }
  await browser.close(); srv.close();
});
