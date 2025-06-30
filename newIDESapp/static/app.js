// app.js — WORKING NAV + JSON persistence + fixed chart sizing
 // --------------------------------------------------
 //   GET  /graphs.json
 //   POST /api/favorite { index, is_fav }
 //   POST /api/delete   { index }
 // --------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  let chatHistory = [];
  // Add controller for aborting fetch requests
  let controller = null;

  // --- DOMContentLoaded: App Bootstrapping ---
  // Sets up navigation, loads graphs, and initializes UI when the page loads.

  /* ---------- NAVIGATION ---------- */
  const pages = document.querySelectorAll(".page");
  const navBtns = document.querySelectorAll(".nav-btn");
  let currentPage = "home";           // track for reset logic
  function show(pageId) {
    // Only reset chat history when explicitly requested, not on every page visit
    currentPage = pageId;
    pages.forEach((p) => p.classList.toggle("hidden", p.id !== pageId));
    navBtns.forEach((b) =>
      b.classList.toggle("active", b.dataset.page === pageId)
    );
  }
  
  // Function to explicitly start a new chat session
  function startNewChatSession() {
    chatHistory = [];
    const chatArea = document.getElementById("chat-area");
    if (chatArea) chatArea.innerHTML = "";
    console.log("Started new chat session - history cleared");
  }
  navBtns.forEach((btn) =>
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      show(btn.dataset.page);
    })
  );
  show("home");

  // --- Data Loading ---
  // Fetches graphs from backend and triggers render.

  /* ---------- DATA ---------- */
  let graphs = [];
  async function loadGraphs() {
    const res = await fetch("/graphs.json?" + Date.now());
    graphs = await res.json();
    render();
  }

  // --- Render Functions ---
  // Renders graph cards for Home and Graphs pages, including chart drawing and controls.

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

  // --- API Actions ---
  // Handles favorite and delete actions via API calls and updates UI.

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
  const sendBtn = document.getElementById("global-send");  const chatArea = document.getElementById("chat-area");
  const loadingBar = document.getElementById("loading-bar");
  // Use the existing chatHistory from the top of the file
  
  async function sendPrompt() {
    const txt = promptInput.value.trim();
    if (!txt) return;
    show("generate");
    appendBubble(txt, "user");
    promptInput.value = "";
    loadingBar.style.display = "flex";
    try {
      // Append user message to chat history
      chatHistory.push({ role: "user", content: txt });
      console.log("Current chat history before sending:", chatHistory);
      
      // Send full chat history
      const payload = { chat_history: chatHistory };
      console.log("Sending /api/analyze payload:", payload);
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        if (res.status === 422) {
          const err = await res.json();
          throw new Error(`Processing error: ${err.detail||"Could not process request"}`);
        }
        throw new Error(`API error: ${res.status}`);
      }
      const data = await res.json();
      console.log("Received /api/analyze response data:", data);
      const responseType = data.responseType || "Analysis";
      
      // Add assistant response to chat history
      const assistantResponse = data.description ?? data.answer ?? "[no response]";
      chatHistory.push({ role: "assistant", content: assistantResponse });
      console.log("Updated chat history after response:", chatHistory);
      
      // Display response - don't add prefix for casual chat
      if (responseType === "Chat") {
        appendBubble(assistantResponse, "ai");
      } else {
        appendBubble("[" + responseType + "] " + assistantResponse, "ai");
      }
      if (data.series && data.series.length) {
        renderInlineChart(data.series);

        /* ----------- NEW: embed raw graph JSON into chatHistory ----------- */
        chatHistory.push({ role: "assistant", content: "[[GRAPH_DATA]] " + JSON.stringify(data.series) });

        /* Save to persistent store (unchanged) */
        const saveRes = await fetch("/api/add_graph", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: data.title,
            series: data.series,
            is_fav: false,
          }),
        });
        if (saveRes.ok) loadGraphs();
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        appendBubble("Request was stopped.", "ai");
      } else {
        appendBubble("Error: " + err.message, "ai");
      }
    } finally {
      controller = null;
      loadingBar.style.display = "none";
    }
  }
  sendBtn.addEventListener("click", sendPrompt);
  promptInput.addEventListener("keydown", e => { if (e.key === "Enter") sendPrompt(); });

  function appendBubble(text, who) {
    const div = document.createElement("div");
    div.className = "chat-bubble " + who;
    div.textContent = text;
    chatArea.append(div);
    chatArea.scrollTop = chatArea.scrollHeight;
  }

  function renderInlineChart(series) {
    console.log("Rendering inline chart with series:", series);
    const container = document.createElement("div");
    container.className = "chat-bubble ai inline-chart";
    const canvas = document.createElement("canvas");
    canvas.style.width = "800px";
    canvas.style.height = "400px";
    container.appendChild(canvas);
    chatArea.appendChild(container);

    const labels = series[0].x;
    const datasets = series.map(function(s, idx) {
      return {
        label: s.label || "Series " + (idx + 1),
        data: s.y,
        tension: 0.3,
        fill: false
      };
    });

    new Chart(canvas.getContext("2d"), {
      type: "line",
      data: {
        labels: labels,
        datasets: datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        aspectRatio: 2,
        plugins: { legend: { labels: { color: "#fff" } } },
        scales: {
          x: { grid: { color: "#fff" }, ticks: { color: "#fff" }, display: true },
          y: { grid: { color: "#fff" }, ticks: { color: "#fff" }, display: true },
        },
      },
    });

    chatArea.scrollTop = chatArea.scrollHeight;
  }
  async function sendPrompt() {
    const txt = promptInput.value.trim();
    if (!txt) return;
    show("generate");
    appendBubble(txt, "user");
    promptInput.value = "";
    loadingBar.style.display = "flex";
    
    // Cancel any ongoing request
    if (controller) {
      controller.abort();
    }
    
    // Create a new AbortController for this request
    controller = new AbortController();
    
    try {
      // Append user message to chat history
      chatHistory.push({ role: "user", content: txt });
      const payload = { chat_history: chatHistory };
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal      });
      if (!res.ok) {
        // If it's a 422 error, try to get the error details
        if (res.status === 422) {
          const errorData = await res.json();
          throw new Error(`Processing error: ${errorData.detail || "Could not process request"}`);
        }
        throw new Error(`API error: ${res.status}`);
      }
      const data = await res.json();
      console.log("Received /api/analyze response data:", data);
      // Get the response type for display
      const responseType = data.responseType || "Analysis";
      console.log(`Response type: ${responseType}`);
      
      // Append assistant message to chat history
      const assistantResponse = data.description !== undefined ? data.description : (data.answer !== undefined ? data.answer : "[no response]");
      chatHistory.push({ role: "assistant", content: assistantResponse });
      
      // Display response - don't add prefix for casual chat
      if (responseType === "Chat") {
        appendBubble(assistantResponse, "ai");
      } else {
        appendBubble("[" + responseType + "] " + assistantResponse, "ai");
      }
      if (data.series && data.series.length > 0) {
        // Normalize series data for Chart.js
        const normalizedSeries = data.series.map(function(s, idx) {
          return {
            label: s.label || "Series " + (idx + 1),
            x: s.x,
            y: s.y
          };
        });
        // Render graph inline below the text bubble
        renderInlineChart(normalizedSeries);
        // Save graph to backend
        const saveRes = await fetch("/api/add_graph", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: data.title,
            series: normalizedSeries,
            is_fav: false,
          }),
        });
        if (!saveRes.ok) throw new Error("Save error: " + saveRes.status);
        await loadGraphs();
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        appendBubble("Request was stopped.", "ai");
      } else {
        appendBubble("Error: " + err.message, "ai");
      }
    } finally {
      controller = null;  // Reset controller
      loadingBar.style.display = "none";
    }
  }
  
  // Initialize stop button
  const stopButton = document.getElementById("stop-ai");
  stopButton.addEventListener("click", () => {
    if (controller) {
      controller.abort();
      console.log("AI request aborted by user");
    }
  });

  // Initialize clear chat button
  const clearChatButton = document.getElementById("clear-chat");
  clearChatButton.addEventListener("click", () => {
    startNewChatSession();
  });

  /* ---------- BOOT ---------- */
  loadGraphs();
});
