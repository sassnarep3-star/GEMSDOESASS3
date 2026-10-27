/* Public, read-only metadata; no organizer login, scraping, or submission. */
(() => {
  "use strict";
  const body = document.getElementById("focus-rows");
  if (!body) return;
  const cell = (row) => row.insertCell();
  const text = (tag, value, className) => {
    const el = document.createElement(tag);
    el.textContent = value;
    if (className) el.className = className;
    return el;
  };
  const safeRepo = (repo) => /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo);
  const apiActivity = async (repo, target) => {
    if (!safeRepo(repo)) {
      target.textContent = "Unavailable";
      return;
    }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    try {
      const r = await fetch(`https://api.github.com/repos/${repo}`, {
        headers: { Accept: "application/vnd.github+json" },
        signal: controller.signal,
        cache: "no-store",
      });
      if (!r.ok) throw new Error(`GitHub HTTP ${r.status}`);
      const data = await r.json();
      const date = new Date(data.pushed_at);
      if (!data.pushed_at || Number.isNaN(date.getTime())) throw new Error("No date");
      const link = document.createElement("a");
      link.href = `https://github.com/${repo}`;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = `Last push ${date.toISOString().slice(0, 10)} ↗`;
      target.replaceChildren(link);
      target.title = "Public GitHub repository pushed_at; not a score or evidence refresh.";
    } catch (_) {
      target.textContent = "Feed unavailable";
      target.title = "GitHub API unavailable or rate-limited. The pinned audit remains unchanged.";
    } finally {
      clearTimeout(timeout);
    }
  };
  (async () => {
    try {
      const response = await fetch("docs/data/focus-nine-audit.json", { cache: "no-store" });
      if (!response.ok) throw new Error(`Audit HTTP ${response.status}`);
      const audit = await response.json();
      if (!Array.isArray(audit.rows) || audit.rows.length !== 9) throw new Error("Invalid audit");
      body.replaceChildren();
      for (const item of audit.rows) {
        const row = body.insertRow();
        const first = cell(row);
        first.append(text("span", item.site, "site-name"));
        if (
          safeRepo(item.repo) &&
          /^[0-9a-f]{40}$/.test(item.ref) &&
          typeof item.path === "string" &&
          !item.path.includes("..")
        ) {
          const a = text("a", "Inspect old file · audit only ↗", "site-source");
          a.href = `https://github.com/${item.repo}/blob/${item.ref}/${item.path}`;
          a.target = "_blank";
          a.rel = "noopener noreferrer";
          first.append(a);
        }
        const score = cell(row);
        score.append(text("span", Number(item.reported_value).toFixed(4), "value"));
        score.append(text("span", "Not receipt-confirmed", "sub"));
        const estimate = cell(row);
        estimate.append(text("span", "—", "value"));
        estimate.append(text("span", "Not estimable", "sub"));
        const unique = cell(row);
        if (
          item.unique_by_protocol_among_these_nine !== false ||
          !Number.isFinite(item.max_fraction_within_3px) ||
          item.max_fraction_within_3px <= 0.7
        ) {
          unique.append(text("span", "Review audit", "failure"));
        } else {
          unique.append(text("span", "No · over 70%", "failure"));
          unique.append(
            text(
              "span",
              `${(100 * item.max_fraction_within_3px).toFixed(1)}% near ${item.worst_peer}`,
              "sub",
            ),
          );
        }
        const activity = text("span", "Checking GitHub…", "activity");
        cell(row).append(activity);
        apiActivity(item.repo, activity);
      }
    } catch (_) {
      body.replaceChildren();
      const row = body.insertRow();
      const notice = cell(row);
      notice.colSpan = 5;
      notice.append("The audit could not be loaded. No file is approved. ");
      const link = text("a", "Open the pinned audit JSON.");
      link.href = "docs/data/focus-nine-audit.json";
      notice.append(link);
    }
  })();
})();
