// app.js — WORKING NAV + JSON persistence
// --------------------------------------------------
// FastAPI endpoints assumed:
//   GET  /graphs.json
//   POST /api/favorite { index, is_fav }
//   POST /api/delete   { index }
// --------------------------------------------------

/* Wait until DOM is fully parsed so nav buttons & pages exist */
document.addEventListener("DOMContentLoaded", () => {
  /* -------------- NAVIGATION -------------- */
  const pages = document.querySelectorAll(".page");
  const navBtns = document.querySelectorAll(".nav-btn");

  function show(pageId) {
    pages.forEach((p) => p.classList.toggle("hidden", p.id !== pageId));
    navBtns.forEach((b) =>
      b.classList.toggle("active", b.dataset.page === pageId)
    );
  }

  navBtns.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault(); // prevent #hash jump if <a>
      show(btn.dataset.page);
    });
  });

  /* Default page */
  show("home");

  /* -------------- DATA + RENDER -------------- */
  let graphs = [];

  async function loadGraphs() {
    const res = await fetch("/graphs.json?" + Date.now()); // cache‑buster
    graphs = await res.json();
    render();
  }

  function render() {
    const homeWrap = document.getElementById("home-graphs");
    const allWrap = document.getElementById("all-graphs");
    homeWrap.innerHTML = "";
    allWrap.innerHTML = "";

    graphs.forEach((g, idx) => {
      const cardAll = buildCard(g, idx, true);
      allWrap.append(cardAll);
      if (g.is_fav) {
        const cardHome = buildCard(g, idx, false);
        homeWrap.append(cardHome);
      }
    });
  }

  function buildCard(g, idx, withControls) {
    const sampleX = g.series[0].x[0];
    const xOpts = Array.isArray(sampleX)
      ? {}
      : /^\d{4}-\d{2}-\d{2}/.test(sampleX)
      ? { type: "time", time: { unit: "day" } }
      : {};

    const card = document.createElement("div");
    card.className = "graph-card";

    const title = document.createElement("h3");
    title.textContent = g.title;
    card.append(title);

    const canvas = document.createElement("canvas");
    canvas.className = "chart-canvas"; // size controlled by CSS (width:100%; height:360px)
    card.append(canvas);

    if (withControls) {
      const row = document.createElement("div");
      row.className = "btn-row";

      const favBtn = document.createElement("button");
      favBtn.className = "fav-btn";
      favBtn.textContent = g.is_fav ? "★" : "☆";
      favBtn.title = g.is_fav ? "Remove from favourites" : "Add to favourites";
      favBtn.addEventListener("click", () => toggleFav(idx));

      const delBtn = document.createElement("button");
      delBtn.className = "del-btn";
      delBtn.textContent = "🗑";
      delBtn.title = "Delete graph";
      delBtn.addEventListener("click", () => deleteGraph(idx, g.title));

      row.append(favBtn, delBtn);
      card.append(row);
    }

    /* Chart.js */
    new Chart(canvas.getContext("2d"), {
      type: "line",
      data: {
        labels: g.series[0].x,
        datasets: g.series.map((s) => ({
          label: s.label,
          data: s.y,
          tension: 0.3,
        })),
      },
      options: {
        plugins: { legend: { labels: { color: "#fff" } } },
        scales: {
          x: { grid: { color: "#fff" }, ticks: { color: "#fff" } },
          y: { grid: { color: "#fff" }, ticks: { color: "#fff" } },
        },
      },
    });

    return card;
  }

  /* -------------- API actions -------------- */
  async function toggleFav(index) {
    graphs[index].is_fav = !graphs[index].is_fav; // optimistic
    render();
    await fetch("/api/favorite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index, is_fav: graphs[index].is_fav }),
    });
    loadGraphs();
  }

  async function deleteGraph(index, title) {
    if (!confirm(`Delete '${title}' permanently?`)) return;
    await fetch("/api/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index }),
    });
    loadGraphs();
  }

  /* -------------- CHAT BAR (unchanged) -------------- */
  const promptInput = document.getElementById("global-prompt");
  const sendBtn = document.getElementById("global-send");
  const chatArea = document.getElementById("chat-area");

  async function sendPrompt() {
    const txt = promptInput.value.trim();
    if (!txt) return;
    show("generate");
    appendBubble(txt, "user");
    promptInput.value = "";
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: txt }),
    });
    const data = await res.json();
    appendBubble(data.description ?? data.answer ?? "[no response]", "ai");

    /* -------------- NEW: if the LLM returned a chart, persist it -------------- */
    if (Array.isArray(data.series) && data.series.length) {
      // 1. optimistic update so the card appears instantly
      graphs.push({
        title: data.title || `Graph ${Date.now()}`,
        series: data.series,
        is_fav: false,
      });
      render();

      // 2. store it on the server
      await fetch("/api/add_graph", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: data.title, series: data.series }),
      });

      // 3. reload from disk so indices stay in sync
      loadGraphs();
    }
  }

  sendBtn.addEventListener("click", sendPrompt);
  promptInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendPrompt();
  });

  function appendBubble(text, who) {
    const div = document.createElement("div");
    div.className = `chat-bubble ${who}`;
    div.textContent = text;
    chatArea.append(div);
    chatArea.scrollTop = chatArea.scrollHeight;
  }

  /* -------------- BOOT -------------- */
  loadGraphs();
});
