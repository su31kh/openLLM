# YesBot Chat UI

A responsive ChatGPT-style frontend template for an LLM web app.

For now, every user prompt returns:

```text
Yes
```

## Files

- `index.html` - page structure
- `styles.css` - responsive desktop/mobile styling
- `app.js` - chat state, local storage, prompt submit behavior, fake backend reply

## Run locally

Open `index.html` directly in your browser.

For a local development server, you can also run:

```bash
python3 -m http.server 8080
```

Then open:

```text
http://localhost:8080
```

## Deploy free with GitHub Pages

1. Create a new GitHub repository.
2. Upload `index.html`, `styles.css`, `app.js`, and `README.md`.
3. Go to **Settings > Pages**.
4. Set the source to your main branch and root folder.
5. Open the published `github.io` URL after GitHub finishes deploying.

## Connect your own backend later

In `app.js`, replace this function:

```js
async function getAssistantReply(userPrompt) {
  await new Promise((resolve) => setTimeout(resolve, 450));
  return "Yes";
}
```

with your API call:

```js
async function getAssistantReply(userPrompt) {
  const response = await fetch("https://your-api.example.com/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: userPrompt }),
  });

  if (!response.ok) {
    throw new Error("Backend request failed");
  }

  const data = await response.json();
  return data.reply;
}
```

## Important security note

Do not put private API keys in frontend JavaScript. Use your own backend or a serverless function to call paid LLM APIs safely.
