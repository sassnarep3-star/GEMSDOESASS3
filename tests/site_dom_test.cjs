// Exercise the public, read-only table without a browser or network.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const script = fs.readFileSync(path.join(root, 'assets/site.js'), 'utf8');
const audit = JSON.parse(fs.readFileSync(path.join(root, 'docs/data/focus-nine-audit.json'), 'utf8'));
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.textContent = ''; this.className = ''; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; this.textContent = ''; }
  insertRow() { const x = new Element('tr'); this.children.push(x); return x; }
  insertCell() { const x = new Element('td'); this.children.push(x); return x; }
}
async function run(broken) {
  const body = new Element('tbody');
  const fetch = async url => {
    if (url === 'docs/data/focus-nine-audit.json') {
      if (broken) throw new Error('offline');
      return {ok: true, json: async () => audit};
    }
    assert.match(url, /^https:\/\/api\.github\.com\/repos\//);
    return {ok: true, json: async () => ({pushed_at: '2026-10-27T10:00:00Z'})};
  };
  const document = {getElementById: id => id === 'focus-rows' ? body : null,
                    createElement: tag => new Element(tag)};
  vm.runInNewContext(script, {document, fetch, AbortController, setTimeout, clearTimeout});
  await new Promise(resolve => setTimeout(resolve, 25));
  return body;
}
(async () => {
  const body = await run(false);
  assert.equal(body.children.length, 9);
  for (const row of body.children) {
    assert.equal(row.children.length, 5);
    assert.equal(row.children[2].children[1].textContent, 'Not estimable');
    assert.equal(row.children[3].children[0].textContent, 'No · over 70%');
    const historical = row.children[0].children[1];
    assert.match(historical.textContent, /audit only/);
    assert.match(historical.href, /^https:\/\/github\.com\//);
    assert.equal(historical.rel, 'noopener noreferrer');
    assert.match(row.children[4].children[0].children[0].textContent, /Last push 2026-10-27/);
  }
  const offline = await run(true);
  assert.equal(offline.children.length, 1);
  assert.match(offline.children[0].children[0].children[0], /No file is approved/);
  console.log('Site DOM: nine audited rows, live metadata and fail-closed offline state OK.');
})().catch(err => {console.error(err); process.exitCode = 1;});
