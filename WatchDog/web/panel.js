const TOKEN = window.localStorage.getItem("watchdogToken") || "";
if (window.location.search.includes("token=")) {
    window.history.replaceState({}, "", window.location.pathname);
}
let terminalSource = "wrapper";
let lastCommandResult = "";
let terminalAutoScroll = window.localStorage.getItem("watchdogTerminalAutoScroll") !== "false";

function authHeaders(extra = {}) {
    return {
        Authorization: `Bearer ${TOKEN}`,
        ...extra,
    };
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function setPill(id, state, label) {
    const element = document.getElementById(id);
    if (!element) {
        return;
    }

    element.className = `pill ${state}`;
    element.textContent = label;
}

async function requestJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({
        ok: false,
        message: "Invalid JSON response",
    }));

    if (!response.ok && data.ok !== false) {
        data.ok = false;
    }

    if (response.status === 401) {
        window.localStorage.removeItem("watchdogToken");
        window.location.href = "/login";
    }

    return data;
}

async function loadStatus() {
    const data = await requestJson("/api/status", {
        headers: authHeaders(),
    });

    const bridge = data.aetherreach || {};
    const players = bridge.playersOnline ?? 0;
    const maxPlayers = bridge.maxPlayers ?? 0;

    setText("wrapper-state", data.wrapper || "unknown");
    setText("server-state", data.server_running ? "running" : "offline");
    setText("bridge-state", bridge.bridge || "offline");
    setText("players-state", `${players}/${maxPlayers}`);

    setPill("server-pill", data.server_running ? "good" : "bad", data.server_running ? "Server online" : "Server offline");
    setPill("bridge-pill", bridge.ok ? "good" : "warn", bridge.ok ? "Bridge online" : "Bridge offline");
    setPill("plugin-count", "good", `${(data.plugins || []).length} plugins`);

    const pluginList = document.getElementById("plugins-list");
    pluginList.innerHTML = "";
    for (const plugin of data.plugins || []) {
        const item = document.createElement("span");
        item.className = "chip";
        item.textContent = plugin;
        pluginList.appendChild(item);
    }
}

async function loadTerminal() {
    const data = await requestJson(`/api/terminal?source=${encodeURIComponent(terminalSource)}&limit=400`, {
        headers: authHeaders(),
    });

    const terminal = document.getElementById("terminal");
    const nextText = (data.lines || []).join("\n");
    const previousScrollTop = terminal.scrollTop;

    terminal.textContent = nextText || "No terminal output yet.";

    if (terminalAutoScroll) {
        terminal.scrollTop = terminal.scrollHeight;
    } else {
        terminal.scrollTop = previousScrollTop;
    }
}

async function loadCommands() {
    const data = await requestJson("/api/commands", {
        headers: authHeaders(),
    });

    const list = document.getElementById("commands-list");
    list.innerHTML = "";

    for (const command of data.commands || []) {
        const row = document.createElement("article");
        row.className = "command-row";

        const name = document.createElement("strong");
        name.textContent = `wrapper ${command.name}`;

        const help = document.createElement("span");
        help.textContent = command.help || command.usage || "";

        const owner = document.createElement("span");
        owner.textContent = `owner: ${command.owner}`;

        row.append(name, help, owner);
        list.appendChild(row);
    }
}

async function runCommand(command) {
    const result = await requestJson("/api/command", {
        method: "POST",
        headers: authHeaders({
            "Content-Type": "application/json",
        }),
        body: JSON.stringify({ command }),
    });

    lastCommandResult = JSON.stringify(result, null, 2);
    setText("command-result", lastCommandResult);
    await Promise.all([loadStatus(), loadTerminal(), loadCommands()]);
}

function bindForms() {
    document.getElementById("command-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const input = document.getElementById("command-input");
        const command = input.value.trim();
        if (!command) {
            return;
        }
        input.value = "";
        await runCommand(command);
    });

    document.getElementById("veil-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const input = document.getElementById("veil-input");
        const message = input.value.trim();
        if (!message) {
            return;
        }
        input.value = "";
        await runCommand(`wrapper bridge veil ${message}`);
    });

    document.getElementById("broadcast-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const input = document.getElementById("broadcast-input");
        const message = input.value.trim();
        if (!message) {
            return;
        }
        input.value = "";
        await runCommand(`wrapper bridge broadcast ${message}`);
    });

    document.getElementById("plugin-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const input = document.getElementById("plugin-input");
        const plugin = input.value.trim();
        if (!plugin) {
            return;
        }
        input.value = "";
        await runCommand(`wrapper plugin reload ${plugin}`);
    });

    for (const button of document.querySelectorAll(".tab")) {
        button.addEventListener("click", async () => {
            terminalSource = button.dataset.source;
            document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
            button.classList.add("active");
            await loadTerminal();
        });
    }

    document.getElementById("refresh-terminal").addEventListener("click", loadTerminal);
    document.getElementById("refresh-commands").addEventListener("click", loadCommands);

    const autoScrollToggle = document.getElementById("terminal-autoscroll");
    autoScrollToggle.checked = terminalAutoScroll;
    autoScrollToggle.addEventListener("change", async () => {
        terminalAutoScroll = autoScrollToggle.checked;
        window.localStorage.setItem("watchdogTerminalAutoScroll", terminalAutoScroll ? "true" : "false");
        if (terminalAutoScroll) {
            const terminal = document.getElementById("terminal");
            terminal.scrollTop = terminal.scrollHeight;
        }
    });
}

async function boot() {
    bindForms();
    setText("command-result", "Ready.");
    await Promise.all([loadStatus(), loadTerminal(), loadCommands()]);
    setInterval(loadStatus, 4000);
    setInterval(loadTerminal, 1200);
    setInterval(loadCommands, 10000);
}

boot();
