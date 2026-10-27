// Browser smoke checks use the same static files as GitHub Pages, with deterministic
// GitHub API responses. The server and its port exist only for this test process.
const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const zlib = require('node:zlib');
const { execFileSync } = require('node:child_process');
const { chromium } = require('playwright-core');
const bundledChromium = require('@sparticuz/chromium').default;

const root = path.resolve(__dirname, '..');
const snapshot = JSON.parse(fs.readFileSync(path.join(root, 'evidence/source_freshness.json')));
const refs = Object.fromEntries(snapshot.sources.map(s => [s.repo, s.main_sha]));
let server, browser, base, libdir;

test.before(async () => {
  // The serverless Chromium package includes NSS/NSPR libraries. Unpack them
  // for minimal Linux environments; never place the browser or libraries in Git.
  libdir = fs.mkdtempSync(path.join(os.tmpdir(), 'gems-browser-'));
  const brotli = fs.readFileSync(path.join(root, 'node_modules/@sparticuz/chromium/bin/al2023.tar.br'));
  const tar = path.join(libdir, 'libs.tar');
  fs.writeFileSync(tar, zlib.brotliDecompressSync(brotli));
  execFileSync('tar', ['xf', tar, '-C', libdir]);
  browser = await chromium.launch({ executablePath: await bundledChromium.executablePath(),
    headless: true, args: bundledChromium.args,
    env: { ...process.env, LD_LIBRARY_PATH: `${libdir}/lib:${process.env.LD_LIBRARY_PATH || ''}` } });
  server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    const name = decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname);
    const file = path.resolve(root, '.' + name);
    if (!file.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
    const contentTypes = { '.html': 'text/html', '.css': 'text/css', '.js': 'application/javascript', '.json': 'application/json' };
    fs.readFile(file, (error, bytes) => {
      if (error) { res.writeHead(404).end(); return; }
      res.writeHead(200, { 'Content-Type': contentTypes[path.extname(file)] || 'text/plain' }); res.end(bytes);
    });
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});

test.after(async () => {
  if (browser) await browser.close();
  if (server) await new Promise(resolve => server.close(resolve));
  if (libdir) fs.rmSync(libdir, { recursive: true, force: true });
});

async function stubRefs(page, mode = 'unchanged') {
  await page.route('https://api.github.com/**', async route => {
    if (mode === 'unavailable') return route.abort();
    const repo = new URL(route.request().url()).pathname.split('/').slice(2, 4).join('/');
    const sha = mode === 'changed' && repo === snapshot.sources[0].repo ? 'f'.repeat(40) : refs[repo];
    return route.fulfill({ status: sha ? 200 : 404, contentType: 'application/json', body: JSON.stringify({ sha }) });
  });
}

test('desktop and mobile dashboards render evidence and remain fail-closed', async () => {
  for (const width of [1440, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 850 } });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await stubRefs(page);
    assert.equal((await page.goto(base + '/index.html')).status(), 200);
    await page.waitForFunction(() => document.querySelectorAll('#portfolio-rows tr').length === 9);
    await page.waitForFunction(() => document.querySelector('#freshness-text')?.textContent.includes('unchanged'), null, { timeout: 5000 });
    assert.equal(await page.locator('#portfolio-rows .negative').count(), 18);
    assert.match(await page.locator('.download-state').innerText(), /Submission file unavailable/);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), width);
    assert.deepEqual(errors, []);
    await page.goto(base + '/executive-summary.html');
    assert.match(await page.locator('h1').textContent(), /Know when to submit/);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), width);
    await page.goto(base + '/research.html');
    assert.match(await page.locator('h1').textContent(), /Four ways to look/);
    assert.equal(await page.locator('[id^="hypothesis-"]').count(), 4);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), width);
    // Reuse the browser process; the serverless shell can terminate on page.close().
  }
});

test('changed or unavailable sources never appear verified', async () => {
  for (const [mode, expected] of [['changed', 'changed'], ['unavailable', 'unavailable']]) {
    const page = await browser.newPage(); await stubRefs(page, mode);
    await page.goto(base + '/index.html');
    await page.waitForFunction(text => document.querySelector('#freshness-text')?.textContent.includes(text), expected, { timeout: 5000 });
    assert.equal(await page.locator('#portfolio-rows tr').count(), 9);
    assert.match(await page.locator('.status-card').innerText(), /Not ready to submit/);
  }
});

test('missing audit shows an error rather than optimistic rows', async () => {
  const page = await browser.newPage(); await stubRefs(page, 'unavailable');
  await page.route('**/evidence/focus_audit.json', route => route.fulfill({ status: 500, body: 'unavailable' }));
  await page.goto(base + '/index.html');
  await page.waitForFunction(() => document.querySelector('#portfolio-rows')?.textContent.includes('Audit data unavailable'));
  assert.match(await page.locator('.status-card').innerText(), /Not ready to submit/);
});


test('malformed audit rows do not render unsafe links or partial success', async () => {
  const page = await browser.newPage(); await stubRefs(page, 'unavailable');
  const audit = JSON.parse(fs.readFileSync(path.join(root, 'evidence/focus_audit.json')));
  audit.rows[8].historical_mirror_source = 'https://github.com.evil.example/repo';
  await page.route('**/evidence/focus_audit.json', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(audit) }));
  await page.goto(base + '/index.html');
  await page.waitForFunction(() => document.querySelector('#portfolio-rows')?.textContent.includes('Audit data unavailable'), null, { timeout: 5000 });
  assert.equal(await page.locator('#portfolio-rows tr').count(), 1);
  assert.equal(await page.locator('#portfolio-rows a').count(), 0);
  assert.match(await page.locator('.status-card').innerText(), /Not ready to submit/);
});

test('duplicated sites or comparisons cannot masquerade as a complete audit', async () => {
  for (const defect of ['site', 'comparison']) {
    const page = await browser.newPage(); await stubRefs(page, 'unavailable');
    const audit = JSON.parse(fs.readFileSync(path.join(root, 'evidence/focus_audit.json')));
    if (defect === 'site') audit.rows[8] = { ...audit.rows[0] };
    else audit.comparisons[71] = { ...audit.comparisons[0] };
    await page.route('**/evidence/focus_audit.json', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(audit) }));
    await page.goto(base + '/index.html');
    await page.waitForFunction(() => document.querySelector('#portfolio-rows')?.textContent.includes('Audit data unavailable'), null, { timeout: 5000 });
    assert.equal(await page.locator('#portfolio-rows a').count(), 0);
  }
});

test('preserved parallel dashboard remains readable, marked provisional and fail-closed', async () => {
  for (const width of [1440, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 850 } });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.route('https://api.github.com/**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ pushed_at: '2026-10-27T10:00:00Z' }) }));
    await page.goto(base + '/parallel-h1.html');
    await page.waitForFunction(() => document.querySelectorAll('#focus-rows tr').length === 9, null, { timeout: 5000 });
    assert.match(await page.locator('[role="note"]').first().innerText(), /protocol deviation/);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), width);
    assert.deepEqual(errors, []);
    await page.goto(base + '/parallel-h1-guide.html');
    assert.match(await page.locator('[role="note"]').first().innerText(), /no TIFF was approved/);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), width);
  }
});
