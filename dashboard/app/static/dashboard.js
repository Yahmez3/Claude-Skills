// Live run view: subscribes to the SSE stream for this run, marks pipeline
// nodes as done, appends event log lines, and renders streaming reports.

(function () {
  const runId = window.RUN_ID;
  const initialStatus = window.RUN_STATUS;

  const pipelineEl = document.getElementById("pipeline");
  const eventsEl = document.getElementById("events");
  const reportsEl = document.getElementById("reports");
  const reportsEmpty = document.getElementById("reports-empty");
  const statusEl = document.getElementById("status");

  const fmtTime = (ts) => {
    if (!ts) return "";
    const d = new Date(ts * 1000);
    return d.toTimeString().slice(0, 8);
  };

  function appendEvent(ev) {
    const li = document.createElement("li");
    li.className = "evt-" + ev.type;
    let label = ev.type;
    if (ev.type === "node_completed") label = "✓ " + ev.node;
    else if (ev.type === "report") label = "📄 " + ev.field;
    else if (ev.type === "run_started") label = "▶ run started";
    else if (ev.type === "run_succeeded") label = "✅ done · " + (ev.decision || "");
    else if (ev.type === "run_failed") label = "❌ " + (ev.error || "");
    li.textContent = `[${fmtTime(ev.ts)}] ${label}`;
    eventsEl.appendChild(li);
    eventsEl.scrollTop = eventsEl.scrollHeight;
  }

  function markNodeDone(node) {
    const item = pipelineEl.querySelector(`[data-node="${CSS.escape(node)}"]`);
    if (item) item.classList.add("done");
  }

  function setStatus(s, decision) {
    statusEl.textContent = s;
    statusEl.className = "status status-" + s;
    if (decision) {
      const r = document.createElement("span");
      r.className = "rating rating-" + decision.toLowerCase();
      r.textContent = decision;
      statusEl.parentNode.insertBefore(r, statusEl.nextSibling);
    }
  }

  function renderReport(field, content) {
    if (reportsEmpty) reportsEmpty.remove();
    let det = reportsEl.querySelector(`[data-field="${field}"]`);
    if (!det) {
      det = document.createElement("details");
      det.dataset.field = field;
      if (field === "final_trade_decision") det.open = true;
      const sum = document.createElement("summary");
      sum.textContent = field.replace(/_/g, " ");
      const pre = document.createElement("pre");
      pre.textContent = content;
      det.appendChild(sum);
      det.appendChild(pre);
      reportsEl.appendChild(det);
    } else {
      det.querySelector("pre").textContent = content;
    }
  }

  // Don't open SSE for runs that have already finished — the server will just
  // replay the snapshot and close, but we save a connection by using the
  // already-rendered server-side artifacts instead.
  if (initialStatus === "succeeded" || initialStatus === "failed") {
    return;
  }

  const es = new EventSource(`/api/runs/${runId}/events`);

  function handle(ev) {
    let payload;
    try { payload = JSON.parse(ev.data); } catch { return; }
    appendEvent(payload);
    if (payload.type === "node_completed") {
      markNodeDone(payload.node);
    } else if (payload.type === "report") {
      renderReport(payload.field, payload.content);
    } else if (payload.type === "run_succeeded") {
      setStatus("succeeded", payload.decision);
      es.close();
    } else if (payload.type === "run_failed") {
      setStatus("failed");
      es.close();
    } else if (payload.type === "_eof") {
      es.close();
    }
  }

  ["run_started", "node_completed", "report", "run_succeeded", "run_failed", "_eof", "ping"]
    .forEach((t) => es.addEventListener(t, handle));

  es.onerror = () => {
    // Browser will auto-reconnect; nothing to do.
  };
})();
