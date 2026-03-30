# AI Planner

AI Planner is a local planning tool with two ways to use it:

- `Web version`: a browser UI powered by a React frontend and a Node.js/TypeScript backend
- `Normal user version`: a terminal-based CLI that runs locally and guides you through planning from the command line

Both versions help you break a goal into tasks, schedule time blocks, reschedule when the day changes, and run focus timers.

## Which version should I use?

| Version | Best for | Interface | Stack |
| --- | --- | --- | --- |
| Web version | Users who want a visual timeline in the browser | Browser UI | `frontend/` + `backend/` |
| Normal user version | Users who want the simplest local experience without opening the browser | Command line | `aiplanner_cli/` + `planner_core/` |

## Difference Between The Web Version And The Normal User Version

### Web version

The web version is the browser app.

- You open it in the browser.
- It has a visual planning flow and timeline.
- It needs two parts running:
  - the frontend in `frontend/`
  - the backend API in `backend/`
- It is a better fit if you want a more visual experience.

### Normal user version

The normal user version is the CLI app.

- You run it in `cmd`, `PowerShell`, or Linux shell.
- It is designed for direct local use without opening the browser.
- It walks you through provider setup, planning, rescheduling, and focus timers.
- It is a better fit if you just want to run the planner quickly from the terminal.

## Project Structure

| Path | Purpose |
| --- | --- |
| `frontend/` | React web UI |
| `backend/` | Node.js/TypeScript API for the web version |
| `aiplanner_cli/` | CLI app for the normal user version |
| `planner_core/` | Shared Python planning logic used by the CLI |
| `cli/` | Cross-platform install/run wrappers for the CLI |

## Quick Start: Normal User Version

Run from the repo root.

### Windows Command Prompt

```cmd
cli\run.cmd
```

### Windows PowerShell

```powershell
.\cli\run.ps1
```

### Linux

```sh
./cli/run.sh
```

What happens on first run:

- a local virtual environment is created in `.aiplanner-venv`
- Python dependencies are installed
- the CLI asks you to choose `OpenAI`, `Claude`, or `Gemini`
- you can enter your API key or open the provider page from the CLI

Direct Python entry also works after install:

```powershell
.\.aiplanner-venv\Scripts\python.exe -m aiplanner_cli
```

## Quick Start: Web Version

The web version needs the backend and frontend running at the same time.

### 1. Start the backend

Open a terminal in `backend/`:

```powershell
npm install
npm run dev
```

Backend environment variables are documented in `backend/.env.example`:

```env
AI_PLANNER_PROVIDER=gemini
GEMINI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
PORT=8000
```

### 2. Start the frontend

Open another terminal in `frontend/`:

```powershell
npm install
npm run dev
```

The frontend defaults to `http://localhost:8000` for the API. That is also shown in `frontend/.env.example`:

```env
VITE_API_URL=http://localhost:8000
```

Then open the Vite URL shown in the terminal, usually:

```text
http://localhost:5173
```

## Notes

- The CLI is the easiest choice for a single local user.
- The web version is better if you want a visual interface.
- The backend is only required for the web version.
- The CLI stores provider configuration in your user config directory, not in the repo.
