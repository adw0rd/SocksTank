# AGENTS.md

## Communication Rule

- Communicate with the user in Russian.
- Write code, code comments, and commit messages in English.

## Local Run Rule

- If the user asks to run the project locally, start the full required local stack by default.
- For frontend preview, this means starting both the Vite dev server and the local backend if the UI depends on API, WebSocket, video, or mock data.
- Do not start only a partial local service unless the user explicitly asks for only that part.
