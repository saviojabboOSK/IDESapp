// app.js — WORKING NAV + JSON persistence + fixed chart sizing
// --------------------------------------------------
//   GET  /graphs.json
//   POST /api/favorite { index, is_fav }
//   POST /api/delete   { index }
// --------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  /* ---------- NAVIGATION ---------- */
  const pages = document.querySelectorAll(".page");
  const navBtns = document.querySelectorAll(".nav-btn");
  function show(pageId) {
    pages.forEach((p) => p.classList.toggle("hidden", p.id !== pageId));
    navBtns.forEach((b) =>
      b.classList.toggle("active", b.dataset.page === pageId)
    );
  }
  navBtns.forEach((btn) =>
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      show(btn.dataset.page);
    })
  );
  show("home");

  /* ---------- DATA ---------- */
  let graphs = [];
  async function loadGraphs() {
    const res = await fetch("/graphs.json?" + Date.now());
    graphs = await res.json();
    render();
  }

  /* ---------- RENDER ---------- */
  function render() {
    const homeWrap = document.getElementById("home-graphs");
    const allWrap = document.getElementById("all-graphs");
    homeWrap.innerHTML = allWrap.innerHTML = "";
    graphs.forEach((g, idx) => {
      allWrap.append(buildCard(g, idx, true));
      if (g.is_fav) homeWrap.append(buildCard(g, idx, false));
    });
  }

  function buildCard(g, idx, withControls) {
    const card = document.createElement("div");
    card.className = "graph-card";
    const title = document.createElement("h3");
    title.textContent = g.title;
    card.append(title);
    const canvas = document.createElement("canvas");
    canvas.className = "chart-canvas";
    card.append(canvas);
    if (withControls) {
      const row = document.createElement("div");
      row.className = "btn-row";
      const fav = document.createElement("button");
      fav.className = "fav-btn";
      fav.textContent = g.is_fav ? "★" : "☆";
      fav.title = g.is_fav ? "Remove from favourites" : "Add to favourites";
      fav.onclick = () => toggleFav(idx);
      const del = document.createElement("button");
      del.className = "del-btn";
      del.textContent = "🗑";
      del.title = "Delete graph";
      del.onclick = () => deleteGraph(idx, g.title);
      row.append(fav, del);
      card.append(row);
    }
    try {
      new Chart(canvas.getContext("2d"), {
        type: "line",
        data: {
          labels: g.series[0].x,
          datasets: g.series.map((s) => ({
            label: s.label,
            data: s.y,
            tension: 0.3,
            fill: false,
          })),
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          aspectRatio: 2,
          plugins: { legend: { labels: { color: "#fff" } } },
          scales: {
            x: { grid: { color: "#fff" }, ticks: { color: "#fff" } },
            y: { grid: { color: "#fff" }, ticks: { color: "#fff" } },
          },
        },
      });
    } catch (e) {
      console.error("Chart error", e);
    }
    return card;
  }

  /* ---------- API ACTIONS ---------- */
  async function toggleFav(i) {
    graphs[i].is_fav = !graphs[i].is_fav;
    render();
    await fetch("/api/favorite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index: i, is_fav: graphs[i].is_fav }),
    });
    loadGraphs();
  }
  async function deleteGraph(i, title) {
    if (!confirm(`Delete '${title}' permanently?`)) return;
    await fetch("/api/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index: i }),
    });
    loadGraphs();
  }

  /* ---------- CHAT (unchanged) ---------- */
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
    if (data.series && data.series.length > 0) {
      await fetch("/api/add_graph", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: data.title,
          series: data.series,
          is_fav: false,
        }),
      });
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

  /* ---------- BOOT ---------- */
  loadGraphs();
});
