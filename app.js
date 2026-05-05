const STORAGE_KEY = "yesbot.chat.history.v1";

const state = {
  conversations: loadConversations(),
  activeId: null,
  thinking: false,
};

state.activeId = state.conversations[0]?.id;

const els = {
  sidebar: document.querySelector("#sidebar"),
  overlay: document.querySelector("#overlay"),
  openSidebar: document.querySelector("#openSidebar"),
  closeSidebar: document.querySelector("#closeSidebar"),
  newChatButton: document.querySelector("#newChatButton"),
  newChatTopButton: document.querySelector("#newChatTopButton"),
  clearButton: document.querySelector("#clearButton"),
  chatHistory: document.querySelector("#chatHistory"),
  chatTitle: document.querySelector("#chatTitle"),
  welcome: document.querySelector("#welcome"),
  messages: document.querySelector("#messages"),
  messagesArea: document.querySelector("#messagesArea"),
  composer: document.querySelector("#composer"),
  promptInput: document.querySelector("#promptInput"),
  sendButton: document.querySelector("#sendButton"),
};

function id() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

function timeLabel() {
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date());
}

function loadConversations() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return JSON.parse(saved);
  } catch (error) {
    console.warn("Could not load saved chats:", error);
  }

  return [
    {
      id: id(),
      title: "New chat",
      messages: [],
    },
  ];
}

function saveConversations() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.conversations));
}

function activeChat() {
  return state.conversations.find((chat) => chat.id === state.activeId) || state.conversations[0];
}

function setSidebar(open) {
  els.sidebar.classList.toggle("open", open);
  els.overlay.classList.toggle("open", open);
}

function createMessage(role, content) {
  return {
    id: id(),
    role,
    content,
    time: timeLabel(),
  };
}

function updateActiveChat(updater) {
  state.conversations = state.conversations.map((chat) => {
    if (chat.id !== state.activeId) return chat;
    return updater(chat);
  });
  saveConversations();
  render();
}

function newChat() {
  const chat = { id: id(), title: "New chat", messages: [] };
  state.conversations = [chat, ...state.conversations];
  state.activeId = chat.id;
  state.thinking = false;
  els.promptInput.value = "";
  saveConversations();
  setSidebar(false);
  render();
  window.setTimeout(() => els.promptInput.focus(), 50);
}

function clearChats() {
  const chat = { id: id(), title: "New chat", messages: [] };
  state.conversations = [chat];
  state.activeId = chat.id;
  state.thinking = false;
  els.promptInput.value = "";
  saveConversations();
  render();
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function messageRow(message) {
  const isUser = message.role === "user";
  const avatar = `<div class="avatar ${isUser ? "user-avatar" : "assistant-avatar"}">${isUser ? "👤" : "🤖"}</div>`;
  const bubble = `
    <div class="bubble-wrap">
      <div class="bubble">${escapeHtml(message.content)}</div>
      <div class="meta">
        <span>${message.time}</span>
        <button class="copy-button" data-copy="${escapeHtml(message.content)}">Copy</button>
      </div>
    </div>
  `;

  return `
    <div class="message-row ${isUser ? "user" : "assistant"}">
      ${isUser ? bubble + avatar : avatar + bubble}
    </div>
  `;
}

function typingRow() {
  return `
    <div class="message-row assistant">
      <div class="avatar assistant-avatar">🤖</div>
      <div class="bubble typing" aria-label="Assistant is typing">
        <span></span><span></span><span></span>
      </div>
    </div>
  `;
}

function renderHistory() {
  els.chatHistory.innerHTML = state.conversations
    .map((chat) => `
      <button class="history-item ${chat.id === state.activeId ? "active" : ""}" data-chat-id="${chat.id}">
        ${escapeHtml(chat.title || "New chat")}
      </button>
    `)
    .join("");

  document.querySelectorAll("[data-chat-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeId = button.dataset.chatId;
      state.thinking = false;
      setSidebar(false);
      render();
    });
  });
}

function renderMessages() {
  const chat = activeChat();
  els.chatTitle.textContent = chat?.title || "New chat";
  const hasMessages = Boolean(chat?.messages?.length);
  els.welcome.style.display = hasMessages ? "none" : "grid";

  els.messages.innerHTML = [
    ...(chat?.messages || []).map(messageRow),
    state.thinking ? typingRow() : "",
  ].join("");

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
        const original = button.textContent;
        button.textContent = "Copied";
        window.setTimeout(() => (button.textContent = original), 1200);
      } catch {
        button.textContent = "Copy failed";
      }
    });
  });

  window.setTimeout(() => {
    els.messagesArea.scrollTo({
      top: els.messagesArea.scrollHeight,
      behavior: "smooth",
    });
  }, 20);
}

function render() {
  renderHistory();
  renderMessages();
  els.sendButton.disabled = !els.promptInput.value.trim() || state.thinking;
}

async function getAssistantReply(userPrompt) {
  // Demo behavior for now:
  // Every prompt returns "Yes".
  //
  // Later, replace this function with your backend API call, for example:
  //
  // const response = await fetch("https://your-api.example.com/chat", {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({ message: userPrompt }),
  // });
  // const data = await response.json();
  // return data.reply;
  await new Promise((resolve) => setTimeout(resolve, 450));
  return "Yes";
}

async function submitPrompt(prompt) {
  const text = prompt.trim();
  if (!text || state.thinking) return;

  const userMessage = createMessage("user", text);
  updateActiveChat((chat) => ({
    ...chat,
    title: chat.messages.length === 0 ? text.slice(0, 42) : chat.title,
    messages: [...chat.messages, userMessage],
  }));

  els.promptInput.value = "";
  state.thinking = true;
  render();

  try {
    const reply = await getAssistantReply(text);
    updateActiveChat((chat) => ({
      ...chat,
      messages: [...chat.messages, createMessage("assistant", reply)],
    }));
  } catch (error) {
    updateActiveChat((chat) => ({
      ...chat,
      messages: [...chat.messages, createMessage("assistant", "Sorry, the backend request failed.")],
    }));
    console.error(error);
  } finally {
    state.thinking = false;
    render();
    els.promptInput.focus();
  }
}

function autoGrowTextarea() {
  els.promptInput.style.height = "auto";
  els.promptInput.style.height = Math.min(els.promptInput.scrollHeight, 160) + "px";
}

els.openSidebar.addEventListener("click", () => setSidebar(true));
els.closeSidebar.addEventListener("click", () => setSidebar(false));
els.overlay.addEventListener("click", () => setSidebar(false));
els.newChatButton.addEventListener("click", newChat);
els.newChatTopButton.addEventListener("click", newChat);
els.clearButton.addEventListener("click", clearChats);

els.promptInput.addEventListener("input", () => {
  autoGrowTextarea();
  render();
});

els.promptInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    submitPrompt(els.promptInput.value);
  }
});

els.composer.addEventListener("submit", (event) => {
  event.preventDefault();
  submitPrompt(els.promptInput.value);
});

document.querySelectorAll(".starter").forEach((button) => {
  button.addEventListener("click", () => submitPrompt(button.textContent));
});

render();
