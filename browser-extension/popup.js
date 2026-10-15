const statusEl = document.getElementById("status");
document.getElementById("send").addEventListener("click", async () => {
  const button = document.getElementById("send");
  button.disabled = true;
  statusEl.textContent = "Reading current tab…";
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.url) throw new Error("Could not read the current tab URL.");
    const u = new URL(tab.url);
    if (u.protocol !== "https:" || !["youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"].includes(u.hostname)) {
      throw new Error("Open a YouTube video first.");
    }
    statusEl.textContent = "Triggering GitHub Actions…";
    const response = await fetch("http://127.0.0.1:8765/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: tab.url, format: document.getElementById("format").value })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Bridge request failed (" + response.status + ").");
    statusEl.textContent = "Workflow requested successfully.\nRun: " + (data.run_url || "Check GitHub Actions.");
  } catch (err) {
    statusEl.textContent = "Error: " + err.message + "\n\nStart the local bridge and check its GitHub token.";
  } finally {
    button.disabled = false;
  }
});
