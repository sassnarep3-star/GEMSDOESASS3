const test = require('node:test');
const assert = require('node:assert/strict');
const { summarizeFreshness, safeLink } = require('../assets/app.js');

const sites = ['GEMSDOE24', 'GEMSDOE25', 'GEMSDOE27', 'GEMSDOE28', 'GEMSDOE30', 'GEMSDOE31', 'GEMSDOE32', 'GEMSDOE33', 'GEMSDOE36'];
const snapshot = () => ({ complete: true, sources: sites.map((site, i) => ({ site, repo: `buffedlizard55-lab/${site}`, main_sha: String(i).repeat(40) })) });

test('unchanged means exactly nine valid matching public refs, not registry approval', () => {
  const s = snapshot();
  const result = summarizeFreshness(s, s.sources.map(x => x.main_sha));
  assert.equal(result.state, 'unchanged');
  assert.match(result.message, /does not verify the registry or leaderboard/);
});
test('changed and unavailable checks fail closed', () => {
  const s = snapshot(); const results = s.sources.map(x => x.main_sha);
  results[0] = 'f'.repeat(40);
  assert.equal(summarizeFreshness(s, results).state, 'changed');
  results[1] = null;
  const unknown = summarizeFreshness(s, results);
  assert.equal(unknown.state, 'unknown');
  assert.match(unknown.message, /1 changed/);
  assert.equal(summarizeFreshness({ complete: false, sources: [] }, []).state, 'unknown');
  assert.equal(summarizeFreshness(s, []).state, 'unknown');
});
test('links reject invalid protocol and deceptive host names', () => {
  assert.equal(safeLink('https://github.com/owner/repo', 'github.com'), 'https://github.com/owner/repo');
  assert.equal(safeLink('https://github.com.evil.test/x', 'github.com'), null);
  assert.equal(safeLink('javascript:alert(1)', 'github.com'), null);
  assert.equal(safeLink('/relative', 'github.com'), null);
});
test('duplicated or unrelated source entries never count as the nine-site watch', () => {
  const s = snapshot();
  s.sources[8] = { ...s.sources[0] };
  assert.equal(summarizeFreshness(s, s.sources.map(x => x.main_sha)).state, 'unknown');
  const wrongRepo = snapshot(); wrongRepo.sources[8].repo = 'unrelated/GEMSDOE36';
  assert.equal(summarizeFreshness(wrongRepo, wrongRepo.sources.map(x => x.main_sha)).state, 'unknown');
});
