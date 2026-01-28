const $ = (sel) => document.querySelector(sel);

function setStatus(kind, msg) {
  const el = $("#status");
  el.className = `status ${kind}`;
  el.textContent = msg;
}

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderFields(fields) {
  if (!fields || !fields.length) {
    return `<div class="mutedSmall">No extra details.</div>`;
  }
  return fields
    .map((f) => {
      let v = f.value;
      if (Array.isArray(v)) v = v.join(", ");
      const isLink = typeof v === "string" && (v.startsWith("http://") || v.startsWith("https://"));
      return `
        <div class="kv">
          <div class="k">${escapeHtml(f.label)}</div>
          <div class="v">${isLink ? `<a href="${escapeHtml(v)}" target="_blank">${escapeHtml(v)}</a>` : escapeHtml(v)}</div>
        </div>
      `;
    })
    .join("");
}

function renderCards(cards) {
  if (!cards || !cards.length) {
    return `<div class="empty">No accounts/modules found for this email.</div>`;
  }
  return cards
    .map((c) => {
      const avatar = c.avatar
        ? `<img class="avatar" src="${escapeHtml(c.avatar)}" alt="avatar">`
        : `<div class="avatar placeholder"></div>`;
      return `
        <div class="resultCard">
          <div class="resultTop">
            ${avatar}
            <div class="resultMeta">
              <div class="resultTitle">${escapeHtml(c.title)}</div>
              <div class="resultSub">${escapeHtml(c.subtitle || "")}</div>
            </div>
            <div class="tag">${escapeHtml((c.module || "module").toUpperCase())}</div>
          </div>
          <div class="resultBody">
            ${renderFields(c.fields)}
          </div>
        </div>
      `;
    })
    .join("");
}

function renderBreaches(breaches, breachCount) {
  const count = Number(breachCount || 0);
  if (!count) {
    return `<div class="empty">No breach entries returned.</div>`;
  }
  const items = (breaches || [])
    .map((b) => {
      return `
        <div class="breachItem">
          <div class="breachTitle">
            ${escapeHtml(b.name || "Breach")}
            <span class="badge ${b.verified ? "good" : "warn"}">
              ${b.verified ? "Verified" : "Unverified"}
            </span>
          </div>
          <div class="breachSub">${escapeHtml(b.date || "")}</div>
          <div class="breachDesc">${escapeHtml(b.description || "")}</div>
        </div>
      `;
    })
    .join("");
  return `
    <div class="breachWrap">
      <div class="breachHeader">Breaches (${count})</div>
      ${items}
    </div>
  `;
}

async function lookup() {
  const email = $("#email").value.trim();
  const consent = $("#consent").checked;
  const includeBreaches = $("#includeBreaches").checked;
  $("#output").innerHTML = "";
  if (!email) {
    return setStatus("bad", "Please enter an email.");
  }
  if (!consent) {
    return setStatus("bad", "Please enable the consent switch.");
  }
  setStatus("neutral", "Looking up…");
  try {
    const res = await fetch("/api/lookup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        consent,
        include_data_breaches: includeBreaches,
        timeout_ms: 5000,
      }),
    });
    const data = await res.json();
    if (!data.ok) {
      setStatus("bad", data.error || "Request failed.");
      $("#output").innerHTML = `<div class="empty">${escapeHtml(data.error || "Error")}</div>`;
      return;
    }
    const r = data.result;
    const html = `
      <div class="sectionTitle">Accounts / Modules Found</div>
      ${renderCards(r.cards)}
      <div style="height:14px"></div>
      <div class="sectionTitle">Breach Summary</div>
      ${renderBreaches(r.breaches, r.breach_count)}
      <div style="height:14px"></div>
      <details class="raw">
        <summary>View raw JSON</summary>
        <pre>${escapeHtml(JSON.stringify(r.raw, null, 2))}</pre>
      </details>
    `;
    $("#output").innerHTML = html;
    setStatus("ok", "Clean results rendered ✅");
  } catch (err) {
    setStatus("bad", "Network or server error.");
    $("#output").innerHTML = `<div class="empty">${escapeHtml(String(err))}</div>`;
  }
}

function clearAll() {
  $("#email").value = "";
  $("#consent").checked = false;
  $("#includeBreaches").checked = true;
  $("#output").innerHTML = "";
  setStatus("neutral", "Ready.");
}

$("#btn").addEventListener("click", lookup);
$("#clear").addEventListener("click", clearAll);
$("#email").addEventListener("keydown", (e) => {
  if (e.key === "Enter") lookup();
});
