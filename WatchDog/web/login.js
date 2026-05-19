let pendingPlayer = "";

function setResult(message) {
    document.getElementById("auth-result").textContent = message;
}

async function postJson(url, body) {
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({ ok: false, error: "Invalid JSON response" }));

    if (!response.ok && data.ok !== false) {
        data.ok = false;
    }

    return data;
}

document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const playerInput = document.getElementById("player-input");
    pendingPlayer = playerInput.value.trim();

    if (!pendingPlayer) {
        setResult("Enter your Minecraft player name.");
        return;
    }

    setResult("Sending an in-game login code...");
    const data = await postJson("/api/auth/request", { player: pendingPlayer });

    if (!data.ok) {
        setResult(data.error || "Could not request a login code.");
        return;
    }

    document.getElementById("code-form").classList.remove("hidden");
    document.getElementById("code-input").focus();
    setResult(`A login code was sent to ${data.player} in Minecraft.`);
});

document.getElementById("code-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const code = document.getElementById("code-input").value.trim();

    if (!pendingPlayer || !code) {
        setResult("Enter the code from Minecraft.");
        return;
    }

    const data = await postJson("/api/auth/verify", {
        player: pendingPlayer,
        code,
    });

    if (!data.ok) {
        setResult(data.error || "Login failed.");
        return;
    }

    window.localStorage.setItem("watchdogToken", data.token);
    window.localStorage.setItem("watchdogPlayer", data.player);
    window.location.href = "/";
});
