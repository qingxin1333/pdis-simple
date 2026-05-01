const chat = document.getElementById("chat");
const chatWrap = document.getElementById("chatWrap");
const emptyState = document.getElementById("emptyState");
const input = document.getElementById("input");
const send = document.getElementById("send");
const planList = document.getElementById("planList");
const toolRuns = document.getElementById("toolRuns");
const memoryCtx = document.getElementById("memoryCtx");
const runMeta = document.getElementById("runMeta");
const drawer = document.getElementById("drawer");
const backdrop = document.getElementById("backdrop");
const toggleRuns = document.getElementById("toggleRuns");
const closeDrawer = document.getElementById("closeDrawer");
const fileInput = document.getElementById("file");
const pickFiles = document.getElementById("pickFiles");
const attachRow = document.getElementById("attachRow");
const historyList = document.getElementById("historyList");
const newChat = document.getElementById("newChat");
const userInfo = document.getElementById("userInfo");
const logoutBtn = document.getElementById("logoutBtn");

let currentMode = "SMART_ANALYSIS";
let selectedFiles = [];
let currentUser = null;

const STORAGE_KEY = "pdis_conversations_v1";
let conversations = [];
let currentConvId = null;

async function checkAuth() {
  try {
    const resp = await fetch("/api/v1/auth/me");
    if (resp.ok) {
      const data = await resp.json();
      currentUser = data.user;
      userInfo.textContent = currentUser.display_name;
      logoutBtn.style.display = "inline-block";
      return true;
    } else {
      window.location.href = "/login";
      return false;
    }
  } catch (e) {
    window.location.href = "/login";
    return false;
  }
}

async function logout() {
  try {
    await fetch("/api/v1/auth/logout", { method: "POST" });
  } catch (e) {
    console.error("Logout error:", e);
  }
  window.location.href = "/login";
}

function loadConversations() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const data = raw ? JSON.parse(raw) : [];
    conversations = Array.isArray(data) ? data : [];
  } catch {
    conversations = [];
  }
}

function saveConversations() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
}

function newConversation() {
  const id = crypto.randomUUID();
  const now = Date.now();
  const conv = {
    id,
    title: "新对话",
    createdAt: now,
    updatedAt: now,
    messages: [],
    lastRun: null,
  };
  conversations.unshift(conv);
  currentConvId = id;
  saveConversations();
  renderSidebar();
  renderChat();
  setMeta("就绪");
}

function getCurrentConversation() {
  return conversations.find((c) => c.id === currentConvId) || null;
}

function renderSidebar() {
  historyList.innerHTML = "";
  for (const c of conversations) {
    const item = document.createElement("div");
    item.className = "sbItem" + (c.id === currentConvId ? " active" : "");
    const title = document.createElement("div");
    title.className = "sbItemTitle";
    title.textContent = c.title || "对话";
    const meta = document.createElement("div");
    meta.className = "sbItemMeta";
    const dt = new Date(c.updatedAt || c.createdAt || Date.now());
    meta.textContent = dt.toLocaleString();
    item.appendChild(title);
    item.appendChild(meta);
    item.addEventListener("click", () => {
      currentConvId = c.id;
      renderSidebar();
      renderChat();
      if (c.lastRun) {
        setPlan(c.lastRun.plan_summary);
        setToolRuns(c.lastRun.tool_runs);
        memoryCtx.textContent = c.lastRun.memory_context || "";
      } else {
        setPlan([]);
        setToolRuns([]);
        memoryCtx.textContent = "";
      }
    });
    historyList.appendChild(item);
  }
}

function addMsg(role, text, isStreaming = false) {
  const row = document.createElement("div");
  row.className = "msg " + role;
  const r = document.createElement("div");
  r.className = "role";
  r.textContent = role === "user" ? "你" : "PDIS";
  const b = document.createElement("div");
  b.className = "bubble";
  b.textContent = text;
  if (isStreaming) {
    b.id = "streaming-bubble";
    b.classList.add("streaming");
  }
  row.appendChild(r);
  row.appendChild(b);
  chat.appendChild(row);
  chatWrap.scrollTop = chatWrap.scrollHeight;
  return b;
}

function setPlan(steps) {
  planList.innerHTML = "";
  for (const s of steps || []) {
    const li = document.createElement("li");
    li.textContent = s;
    planList.appendChild(li);
  }
}

function setToolRuns(runs) {
  toolRuns.innerHTML = "";
  for (const r of runs || []) {
    const item = document.createElement("div");
    item.className = "toolRun";
    const left = document.createElement("div");
    left.className = "name";
    left.textContent = r.tool || "tool";
    const right = document.createElement("div");
    right.className = "status";
    right.textContent = r.status || "";
    item.appendChild(left);
    item.appendChild(right);
    toolRuns.appendChild(item);
  }
}

function setMeta(text) {
  runMeta.textContent = text;
}

function setDrawerOpen(open) {
  if (open) {
    drawer.classList.add("open");
    backdrop.classList.add("open");
  } else {
    drawer.classList.remove("open");
    backdrop.classList.remove("open");
  }
}

document.querySelectorAll(".mode").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentMode = btn.dataset.mode || "SMART_ANALYSIS";
    setMeta(`当前模式：${btn.textContent}`);
  });
});

function renderAttachments() {
  attachRow.innerHTML = "";
  selectedFiles.forEach((f, idx) => {
    const chip = document.createElement("div");
    chip.className = "chip";
    const name = document.createElement("div");
    name.textContent = f.name;
    const btn = document.createElement("button");
    btn.className = "chipBtn";
    btn.textContent = "×";
    btn.addEventListener("click", () => {
      selectedFiles.splice(idx, 1);
      renderAttachments();
    });
    chip.appendChild(name);
    chip.appendChild(btn);
    attachRow.appendChild(chip);
  });
}

async function uploadAttachments() {
  if (!selectedFiles.length) return [];
  const fd = new FormData();
  for (const f of selectedFiles) fd.append("files", f);
  const resp = await fetch("/api/v1/attachments/upload", { method: "POST", body: fd });
  const data = await resp.json();
  const refs = Array.isArray(data.files) ? data.files : [];
  return refs.map((x) => x.file_ref).filter(Boolean);
}

function renderChat() {
  chat.innerHTML = "";
  const conv = getCurrentConversation();
  const messages = conv?.messages || [];
  emptyState.style.display = messages.length ? "none" : "flex";
  for (const m of messages) addMsg(m.role, m.text);
  chatWrap.scrollTop = chatWrap.scrollHeight;
}

async function runAgent(text) {
  send.disabled = true;
  setMeta("运行中…");
  try {
    const conv = getCurrentConversation();
    if (!conv) return;

    const attachmentRefs = await uploadAttachments();

    // 先将用户消息添加到对话记录
    conv.messages.push({ role: "user", text });
    if (!conv.title || conv.title === "新对话") {
      conv.title = text.length > 14 ? text.slice(0, 14) + "…" : text;
    }
    conv.updatedAt = Date.now();
    saveConversations();
    renderSidebar();
    renderChat();

    // 添加AI消息占位符（流式）
    const streamingBubble = addMsg("assistant", "正在思考...", true);

    // 使用流式API
    const resp = await fetch("/api/v1/agent/run/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, mode: currentMode, attachments: attachmentRefs }),
    });

    if (!resp.ok) {
      throw new Error(`HTTP error! status: ${resp.status}`);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalAnswer = "";
    let planSummary = [];
    let toolRuns = [];
    let memoryContext = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === "start") {
              streamingBubble.textContent = data.content;
            } else if (data.type === "thinking") {
              streamingBubble.textContent = data.content;
            } else if (data.type === "final") {
              finalAnswer = data.content;
              streamingBubble.textContent = finalAnswer;
              streamingBubble.classList.remove("streaming");
            } else if (data.type === "done") {
              planSummary = data.plan_summary || [];
              toolRuns = data.tool_runs || [];
              memoryContext = data.memory_context || "";
            } else if (data.type === "error") {
              throw new Error(data.content);
            }
          } catch (e) {
            console.error("Parse error:", e);
          }
        }
      }
    }

    // 流式完成后，移除流式占位符，添加AI回复到对话记录
    streamingBubble.remove();
    conv.messages.push({ role: "assistant", text: finalAnswer || "无输出" });
    conv.lastRun = {
      plan_summary: planSummary,
      tool_runs: toolRuns,
      memory_context: memoryContext,
    };
    conv.updatedAt = Date.now();
    saveConversations();
    renderSidebar();
    renderChat();

    setPlan(planSummary);
    setToolRuns(toolRuns);
    memoryCtx.textContent = memoryContext || "";

    selectedFiles = [];
    renderAttachments();
    setMeta("完成");
  } catch (e) {
    const conv = getCurrentConversation();
    if (conv) {
      conv.messages.push({ role: "assistant", text: `运行失败：${String(e)}` });
      conv.updatedAt = Date.now();
      saveConversations();
      renderSidebar();
      renderChat();
    } else {
      addMsg("assistant", `运行失败：${String(e)}`);
    }
    setMeta("失败");
  } finally {
    send.disabled = false;
  }
}

send.addEventListener("click", () => {
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  runAgent(text);
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
    send.click();
  }
});

toggleRuns.addEventListener("click", () => setDrawerOpen(true));
closeDrawer.addEventListener("click", () => setDrawerOpen(false));
backdrop.addEventListener("click", () => setDrawerOpen(false));

pickFiles.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  selectedFiles = Array.from(fileInput.files || []);
  renderAttachments();
});

newChat.addEventListener("click", () => newConversation());
logoutBtn.addEventListener("click", logout);

checkAuth().then((authenticated) => {
  if (authenticated) {
    loadConversations();
    if (!conversations.length) newConversation();
    else {
      currentConvId = conversations[0].id;
      renderSidebar();
      renderChat();
    }
    setMeta("就绪");
  }
});

