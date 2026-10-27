/* Public-data dashboard. This script never modifies a raster or selects a slot. */
(() => {
  'use strict';

  const expectedSites = ['GEMSDOE24', 'GEMSDOE25', 'GEMSDOE27', 'GEMSDOE28', 'GEMSDOE30', 'GEMSDOE31', 'GEMSDOE32', 'GEMSDOE33', 'GEMSDOE36'];
  const expectedSiteSet = new Set(expectedSites);

  function completeSites(items) {
    return Array.isArray(items) && items.length === expectedSites.length &&
      new Set(items.map(item => item && item.site)).size === expectedSites.length &&
      items.every(item => item && expectedSiteSet.has(item.site));
  }

  function summarizeFreshness(snapshot, observations) {
    if (!snapshot || snapshot.complete !== true || !completeSites(snapshot.sources) ||
        snapshot.sources.some(s => s.repo !== `buffedlizard55-lab/${s.site}`)) {
      return { state: 'unknown', message: 'Source snapshot is incomplete. Re-audit required.' };
    }
    if (!Array.isArray(observations) || observations.length !== snapshot.sources.length) {
      return { state: 'unknown', message: 'Source checks are incomplete. Re-audit required.' };
    }
    let changed = 0, unknown = 0;
    for (let i = 0; i < snapshot.sources.length; i++) {
      const ref = snapshot.sources[i].main_sha;
      const now = observations[i];
      if (!/^[a-f0-9]{40}$/.test(ref || '') || !/^[a-f0-9]{40}$/.test(now || '')) unknown++;
      else if (now !== ref) changed++;
    }
    if (unknown) return { state: 'unknown', message: `${unknown} of 9 source checks unavailable${changed ? `; ${changed} changed` : ''}. Re-audit required.` };
    if (changed) return { state: 'changed', message: `${changed} of 9 public repositories changed since this snapshot. Refresh the registry and audit.` };
    return { state: 'unchanged', message: 'Nine public main refs unchanged since the snapshot. This does not verify the registry or leaderboard.' };
  }

  function safeLink(href, host) {
    try {
      const url = new URL(href);
      return url.protocol === 'https:' && url.hostname === host ? url.href : null;
    } catch (_) { return null; }
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = { summarizeFreshness, safeLink };
  if (typeof document === 'undefined') return;

  const tbody = document.getElementById('portfolio-rows');
  const freshnessText = document.getElementById('freshness-text');
  const refreshButton = document.getElementById('refresh-sources');
  let refreshing = false;

  function cell(row, tag = 'td') {
    const el = document.createElement(tag); row.appendChild(el); return el;
  }
  function subtext(parent, text) {
    const small = document.createElement('span'); small.className = 'subtext'; small.textContent = text; parent.appendChild(small);
  }
  function externalLink(href, label, className) {
    const link = document.createElement('a');
    link.href = href; link.textContent = label; link.className = className || '';
    link.target = '_blank'; link.rel = 'noopener noreferrer';
    return link;
  }

  async function loadPortfolio() {
    if (!tbody) return;
    try {
      const response = await fetch('evidence/focus_audit.json', { cache: 'no-cache' });
      if (!response.ok) throw new Error('audit unavailable');
      const audit = await response.json();
      if (!completeSites(audit.rows) || audit.rows.some(row => row.all_eight_comparisons_duplicate !== true) ||
          audit.n_directed_comparisons !== 72 || !Array.isArray(audit.comparisons) || audit.comparisons.length !== 72) {
        throw new Error('incomplete audit');
      }
      const pairKeys = new Set();
      for (const pair of audit.comparisons) {
        if (!expectedSiteSet.has(pair.candidate) || !expectedSiteSet.has(pair.reference) || pair.candidate === pair.reference ||
            typeof pair.candidate_within_3px_fraction !== 'number' || !Number.isFinite(pair.candidate_within_3px_fraction) ||
            pair.candidate_within_3px_fraction <= 0.70 || pair.candidate_within_3px_fraction > 1) throw new Error('invalid comparison');
        pairKeys.add(`${pair.candidate}:${pair.reference}`);
      }
      if (pairKeys.size !== 72) throw new Error('duplicate comparison');
      const rows = [...audit.rows].sort((a, b) => b.claim - a.claim);
      tbody.replaceChildren();
      for (const item of rows) {
        const source = safeLink(item.historical_mirror_source, 'github.com');
        const site = safeLink(item.site_url, 'buffedlizard55-lab.github.io');
        if (!source || !site || typeof item.claim !== 'number' || !Number.isFinite(item.claim)) throw new Error('invalid audit row');
        const tr = document.createElement('tr');
        const a = cell(tr); a.appendChild(externalLink(site, item.site)); subtext(a, 'Owner site');
        const b = cell(tr); const file = externalLink(source, item.historical_mirror_name, 'file-name'); file.title = item.historical_mirror_name; b.appendChild(file); subtext(b, 'Pinned mirror · research only');
        const c = cell(tr); const score = document.createElement('strong'); score.textContent = item.claim.toFixed(4); c.appendChild(score); subtext(c, 'User-reported · unverified');
        const d = cell(tr); d.textContent = 'Not estimable'; subtext(d, 'No validated transfer');
        const e = cell(tr); e.className = 'negative'; e.textContent = item.all_eight_comparisons_duplicate ? 'NO · duplicate' : 'UNKNOWN';
        const f = cell(tr); f.className = 'negative'; f.textContent = 'DO NOT SUBMIT';
        tbody.appendChild(tr);
      }
    } catch (_) {
      tbody.replaceChildren();
      const tr = document.createElement('tr'); const td = cell(tr); td.colSpan = 6; td.className = 'table-message';
      td.textContent = 'Audit data unavailable or incomplete. No file is approved; see the linked JSON.'; tbody.appendChild(tr);
    }
  }

  async function fetchSha(repo) {
    if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo || '')) return null;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(`https://api.github.com/repos/${repo}/commits/main`, { signal: controller.signal, cache: 'no-store' });
      if (!response.ok) return null;
      const json = await response.json();
      return typeof json.sha === 'string' ? json.sha : null;
    } catch (_) { return null; }
    finally { clearTimeout(timer); }
  }

  async function checkSources() {
    if (!freshnessText || refreshing) return;
    refreshing = true;
    if (refreshButton) refreshButton.disabled = true;
    freshnessText.textContent = 'Checking public repository revisions…';
    try {
      const response = await fetch('evidence/source_freshness.json', { cache: 'no-cache' });
      if (!response.ok) throw new Error('snapshot unavailable');
      const snapshot = await response.json();
      if (!snapshot.complete || !Array.isArray(snapshot.sources) || snapshot.sources.length !== 9) throw new Error('snapshot incomplete');
      const observations = await Promise.all(snapshot.sources.map(s => fetchSha(s.repo)));
      freshnessText.textContent = summarizeFreshness(snapshot, observations).message;
    } catch (_) {
      freshnessText.textContent = 'Revision check unavailable. Treat source freshness as unknown.';
    } finally {
      refreshing = false;
      if (refreshButton) refreshButton.disabled = false;
    }
  }

  if (refreshButton) refreshButton.addEventListener('click', checkSources);
  loadPortfolio();
  checkSources();
})();
