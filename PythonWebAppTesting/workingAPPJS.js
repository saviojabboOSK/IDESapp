// NAVIGATION
const navBtns = document.querySelectorAll(".nav-btn");
navBtns.forEach((b) => {
  b.addEventListener("click", () => {
    document
      .querySelectorAll(".page")
      .forEach((p) => p.classList.add("hidden"));
    document.getElementById(b.dataset.page).classList.remove("hidden");
    navBtns.forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
  });
});
navBtns[0].click(); // start on Home

// LOAD + RENDER
async function loadGraphs() {
  // fetch from root; graphs.json must live in static/
  const res = await fetch("/graphs.json");
  const graphs = await res.json();
  const favs = graphs.filter((g) => g.is_fav);
  renderGraphs(favs, document.getElementById("home-graphs"));
  renderGraphs(graphs, document.getElementById("all-graphs"));
}

function renderGraphs(list, container) {
  container.innerHTML = "";
  list.forEach((g, i) => {
    const card = document.createElement("div");
    card.className = "graph-card";

    const title = document.createElement("h3");
    title.textContent = g.title;
    card.append(title);

    const canvas = document.createElement("canvas");
    canvas.id = `chart-${container.id}-${i}`;
    card.append(canvas);

    if (container.id === "all-graphs") {
      // FAVORITE
      const favBtn = document.createElement("button");
      favBtn.className = "fav-btn";
      favBtn.textContent = g.is_fav ? "★" : "☆";
      favBtn.onclick = async () => {
        await fetch("/api/favorite", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: g.title, is_fav: !g.is_fav }),
        });
        loadGraphs();
      };
      card.append(favBtn);

      // DELETE
      const delBtn = document.createElement("button");
      delBtn.className = "del-btn";
      delBtn.textContent = "🗑";
      delBtn.onclick = async () => {
        if (confirm(`Are you sure you want to delete '${g.title}'?`)) {
          const resp = await fetch("/api/delete", {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: g.title }),
          });
          if (resp.ok) {
            loadGraphs();
          }
        }
      };
      card.append(delBtn);
    }

    container.append(card);

    // chart with light axes/grid
    const ctx = canvas.getContext("2d");
    const labels = g.series[0].x;
    const datasets = g.series.map((s) => ({
      label: s.label,
      data: s.y,
      fill: false,
      tension: 0.3,
    }));
    new Chart(ctx, {
      type: "line",
      data: { labels, datasets },
      options: {
        plugins: {
          legend: { labels: { color: "#fff" } },
        },
        scales: {
          x: {
            grid: { color: "#fff" },
            ticks: { color: "#fff" },
            title: { display: true, text: "", color: "#fff" },
          },
          y: {
            grid: { color: "#fff" },
            ticks: { color: "#fff" },
            title: { display: true, text: "", color: "#fff" },
          },
        },
      },
    });
  });
}

// CHAT BAR
const promptInput = document.getElementById("global-prompt");
const sendBtn = document.getElementById("global-send");
const chatArea = document.getElementById("chat-area");

async function sendPrompt() {
  const txt = promptInput.value.trim();
  if (!txt) return;
  document.querySelector('[data-page="generate"]').click();
  appendBubble(txt, "user");
  promptInput.value = "";
  const res = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt: txt }),
  });
  const data = await res.json();
  appendBubble(data.description, "ai");
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

// INIT
loadGraphs();
