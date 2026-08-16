# 🤖 my_neo-agent: Multi-Agent AI Development & Companion Studio

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.0-blueviolet.svg)](https://github.com/langchain-ai/langgraph)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLMs-black.svg?logo=ollama&logoColor=white)](https://ollama.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**my_neo-agent** is a multi-agent AI development environment, coding copilot, and desktop companion powered by **LangGraph**, **FastAPI**, and local **Ollama** LLMs. It features an intelligent **Master Orchestrator** that coordinates specialized agents for building web applications, scaffolding full-stack Next.js projects, performing deep code analysis with on-disk auto-fixing, parsing complex documents, and generating slide presentations.

---

## 📑 Table of Contents

- [✨ Key Features & Multi-Agent Architecture](#-key-features--multi-agent-architecture)
- [📋 System Requirements](#-system-requirements)
- [🚀 Quick Start (Step-by-Step Guide)](#-quick-start-step-by-step-guide)
  - [Step 1: Clone the Repository](#step-1-clone-the-repository)
  - [Step 2: Create & Activate Virtual Environment](#step-2-create--activate-virtual-environment)
  - [Step 3: Install Dependencies](#step-3-install-dependencies)
  - [Step 4: Install Ollama & Pull Models](#step-4-install-ollama--pull-models)
  - [Step 5: Configure Environment Variables (`.env`)](#step-5-configure-environment-variables-env)
- [🖥️ How to Run the Application](#️-how-to-run-the-application)
  - [Mode 1: Web UI Dashboard](#mode-1-web-ui-dashboard-recommended)
  - [Mode 2: Interactive Terminal CLI](#mode-2-interactive-terminal-cli)
  - [Mode 3: Desktop Floating Mascot Companion](#mode-3-desktop-floating-mascot-companion)
- [🧠 Ollama Model Setup & Recommendations](#-ollama-model-setup--recommendations)
- [💬 Directives & Agent Invocation](#-directives--agent-invocation)
- [🔌 REST API & WebSocket Reference](#-rest-api--websocket-reference)
- [🧪 Running Integration Tests](#-running-integration-tests)
- [🛠️ Troubleshooting & FAQ](#️-troubleshooting--faq)
- [📁 Project Structure](#-project-structure)

---

## ✨ Key Features & Multi-Agent Architecture

```
                                  ┌──────────────────────────┐
                                  │   User Request / Prompt  │
                                  └────────────┬─────────────┘
                                               │
                                  ┌────────────▼─────────────┐
                                  │   Master Orchestrator    │
                                  │  (Intent & Route Logic)  │
                                  └──────┬───┬───┬───┬───────┘
                                         │   │   │   │
             ┌───────────────────────────┘   │   │   └───────────────────────────┐
             │                               │   │                               │
┌────────────▼────────────┐ ┌────────────────▼───▼──────────┐ ┌──────────────────▼──────────┐
│        🤖 NEO           │ │      ⚡ CLAW        🦅 EAGLE    │ │        📊 HERALD          │
│ Single-File Web Apps,   │ │ Full-Stack React/  Code Review,│ │ Academic & Professional    │
│ HTML/CSS/JS, Canvas     │ │ Next.js, Tailwind  Auto-Fixing,│ │ Presentations in Reveal.js  │
│ Games & Python Scripts  │ │ & TS Architecture  Vision & PDF│ │ HTML and PowerPoint (.pptx)│
└─────────────────────────┘ └───────────────────────────────┘ └─────────────────────────────┘
```

1. **🎯 Master Orchestrator**
   - Automatically analyzes incoming prompts and routes tasks to the best-suited specialist.
   - Supports explicit directive tags (e.g. `@eagle`, `@claw`, `@herald`, `@neo`, `[agent:claw]`).
   - Unified real-time streaming protocol with permission safety gates.

2. **🤖 Neo Agent (Web & Script Specialist)**
   - Generates interactive, single-file HTML5/CSS/JavaScript web applications, Canvas 2D/3D games, CSS animations, and standalone Python utility scripts.

3. **⚡ Claw Agent (Full-Stack Architect)**
   - Scaffolds modular Next.js (App Router / Pages Router), React, Tailwind CSS, and TypeScript applications.
   - Generates project folder structures, multiple components, and configuration files.

4. **🦅 Eagle Agent (Code Analysis & Vision Debugger)**
   - **Deep Code Review**: Identifies syntax errors, logic bugs, performance bottlenecks, and style violations.
   - **Automated On-Disk Patching**: Extracts corrected code blocks and writes fixes directly to your workspace files.
   - **Document Extraction**: Reads and summarizes PDF documents, Excel spreadsheets (`.xlsx`, `.csv`), PowerPoint decks (`.pptx`), and source code files.
   - **Vision Debugger**: Analyzes screenshots and UI errors using multimodal vision models.

5. **📊 Herald Agent (Presentation Builder)**
   - Transforms topics, research prompts, and notes into structured slide presentations.
   - Generates both interactive **Reveal.js HTML** slide decks and editable **Microsoft PowerPoint (`.pptx`)** presentations.

---

## 📋 System Requirements

- **Operating System**: Windows 10/11, macOS (Apple Silicon or Intel), or Linux.
- **Python**: Version `3.10`, `3.11`, or `3.12` recommended.
- **Ollama**: Installed and running locally (or reachable via network).
- **RAM / VRAM**:
  - **8 GB RAM**: Sufficient for 7B/8B quantized models (e.g., `qwen2.5-coder:7b`).
  - **16 GB+ RAM / GPU**: Recommended for 14B models (e.g., `qwen2.5-coder:14b`).
  - **32 GB+ RAM / Dedicated VRAM**: For large 32B+ models.
- **Optional**: Node.js `18+` and npm (for running and previewing generated Next.js apps).

---

## 🚀 Quick Start (Step-by-Step Guide)

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/my_neo-agent.git
cd my_neo-agent
```

### Step 2: Create & Activate Virtual Environment

#### On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> **Note for Windows users**: If PowerShell blocks script execution, run:  
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

#### On macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### Step 3: Install Dependencies

Ensure `pip` is up to date, then install all required packages:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 4: Install Ollama & Pull Models

1. **Download & Install Ollama**:
   - Download the installer from [https://ollama.com/download](https://ollama.com/download) and follow the installation wizard.

2. **Start the Ollama Service**:
   - On Windows/macOS, Ollama usually starts in the system tray automatically.
   - On Linux (or to run in terminal):
     ```bash
     ollama serve
     ```

3. **Verify Ollama is Running**:
   Open a browser or terminal and navigate to:
   ```bash
   curl http://localhost:11434/api/version
   ```
   You should receive a JSON response such as `{"version":"0.5.x"}`.

4. **Pull Recommended Models**:
   Run the following commands in your terminal to download the models:

   ```bash
   # 1. Primary coding & reasoning model (Fast & High Quality)
   ollama pull qwen2.5-coder:7b

   # 2. Vision model for screenshot & visual debugging (Eagle Agent)
   ollama pull llava:7b

   # 3. (Optional) Larger coding model for higher reasoning fidelity
   ollama pull qwen2.5-coder:14b

   # 4. (Optional) Deep reasoning model
   ollama pull deepseek-r1:8b
   ```

---

### Step 5: Configure Environment Variables (`.env`)

1. Copy the provided `.env.example` file to `.env`:

   **On Windows (PowerShell / CMD):**
   ```powershell
   Copy-Item .env.example .env
   ```

   **On macOS / Linux:**
   ```bash
   cp .env.example .env
   ```

2. Open `.env` in your editor and configure your preferred models and paths:

```env
# ==============================================================================
# Ollama Server Configuration
# ==============================================================================
OLLAMA_BASE_URL=http://localhost:11434
PRIMARY_MODEL=qwen2.5-coder:7b
VISION_MODEL=llava:7b

# ==============================================================================
# Workspace & File System Paths
# ==============================================================================
# Root folder where generated code and projects are saved
WORKSPACE_PATH=.

# Storage directories for persistent data
DATA_DIR=./data
CHECKPOINT_DB_PATH=./data/checkpoints.db
CHAT_HISTORY_DB_PATH=./data/chat_history.db
PRESENTATIONS_DIR=./data/presentations
ANALYSIS_OUTPUT_DIR=./data/analysis_output

# ==============================================================================
# Server Settings
# ==============================================================================
PORT=8000
HOST=127.0.0.1
```

---

## 🖥️ How to Run the Application

`my_neo-agent` provides **three distinct interfaces** depending on your workflow:

### Mode 1: Web UI Dashboard (Recommended)

Launches the FastAPI backend and dark-themed Cyberpunk/Carbon Web UI with live code previews, model switcher, and file tree.

```bash
python main.py --web
```
*or specify a custom port / auto-reload:*
```bash
python main.py --web --port 8000 --reload
```

🌐 Open your browser at: **`http://127.0.0.1:8000`**

#### Web UI Highlights:
- **Real-Time WebSocket Streaming**: Watch code generate line-by-line.
- **Dynamic Model Switcher**: Change active Ollama models on-the-fly without restarting.
- **Interactive Code & File Inspector**: Browse, preview, and edit files in your workspace.
- **Security Confirmation Modals**: Accept or decline terminal commands and file modifications.

---

### Mode 2: Interactive Terminal CLI

Launches a terminal shell with rich ASCII formatting, live markdown streaming, and security prompts:

```bash
python main.py --cli
```

#### In-CLI Commands:
- `/model` — Interactively view and switch the active Ollama model.
- `/files` — Display a formatted table of all indexed workspace files and line counts.
- `/reindex` — Rescan and reindex the codebase.
- `/exit` or `quit` — Close the CLI session.

---

### Mode 3: Desktop Floating Mascot Companion

Launches a transparent, floating desktop mascot overlay built with Tkinter that stays on top of your screen for assistance and vision diagnostics:

```bash
python main.py --desktop
```

#### Mascot Features:
- **Draggable & Always-On-Top**: Position anywhere on your display.
- **Multiple Visual Themes**: Classic Blue Bot, Doc Bot, Data Bot, and Code Bot.
- **Screen Perception**: Click to trigger instant screen diagnostics via Eagle Agent.

---

## 🧠 Ollama Model Setup & Recommendations

You can configure any model installed in Ollama. Below are tested recommendations grouped by hardware tiers and use-cases:

| Use Case | Model Tag | Size / RAM | Ollama Pull Command | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Best Balance (Coding & Web)** | `qwen2.5-coder:7b` | ~4.7 GB (8 GB RAM) | `ollama pull qwen2.5-coder:7b` | **Recommended default**. Outstanding coding syntax and tool calling. |
| **High Reasoning (Coding)** | `qwen2.5-coder:14b` | ~9.0 GB (16 GB RAM) | `ollama pull qwen2.5-coder:14b` | Superior architectural reasoning for complex Next.js apps. |
| **Deep Reasoning / Math** | `deepseek-r1:8b` | ~4.9 GB (8 GB RAM) | `ollama pull deepseek-r1:8b` | Excels at logic debugging and algorithm problem-solving. |
| **Fast / Low-Spec Machines** | `qwen2.5-coder:1.5b` | ~1.0 GB (4 GB RAM) | `ollama pull qwen2.5-coder:1.5b` | Ultra-fast responses on laptops and low-VRAM machines. |
| **Vision & Screen Debugging** | `llava:7b` | ~4.5 GB (8 GB RAM) | `ollama pull llava:7b` | Standard multimodal vision model for screenshot analysis. |
| **Advanced Vision** | `llama3.2-vision:11b`| ~7.9 GB (16 GB RAM) | `ollama pull llama3.2-vision:11b` | High precision UI and OCR screen debugging. |

### Verifying Installed Models in Ollama:

```bash
ollama list
```

---

## 💬 Directives & Agent Invocation

While the Master Orchestrator automatically detects intent, you can explicitly force a specific specialist agent using prefix tags or `@` mentions:

### 1. 🤖 Neo Agent (`@neo` or `[agent:neo]`)
*Use for single-page web applications, Canvas games, visual calculators, or Python scripts.*
```text
@neo Build a retro 80s arcade Space Invaders game with sound effects in HTML5 Canvas.
```

### 2. ⚡ Claw Agent (`@claw` or `[agent:claw]`)
*Use for full-stack Next.js, React, Tailwind CSS, and TypeScript project scaffolding.*
```text
@claw Create a modern Kanban board application with drag-and-drop support in Next.js and Tailwind CSS.
```

### 3. 🦅 Eagle Agent (`@eagle` or `[agent:eagle]`)
*Use for code reviews, finding bugs, fixing files directly to disk, or document analysis.*
```text
@eagle Review math_helper.py and fix the divide-by-zero bug directly on disk.
```
```text
@eagle Analyze this PDF document: data/sample_paper.pdf and summarize key findings.
```

### 4. 📊 Herald Agent (`@herald` or `[agent:herald]`)
*Use for generating presentation slide decks in Reveal.js HTML and PowerPoint (`.pptx`).*
```text
@herald Create a 10-slide presentation on "Quantum Computing Fundamentals" with code examples.
```

---

## 🔌 REST API & WebSocket Reference

The FastAPI server provides REST endpoints and WebSocket channels for integration:

### REST Endpoints:
- `GET /api/status` — Server status, active model, workspace root, and indexed file count.
- `GET /api/models` — List installed Ollama models and currently selected model.
- `POST /api/models/select` — Change the active Ollama model (`{"model_id": "qwen2.5-coder:7b"}`).
- `GET /api/agents` — List available specialized agents (`neo`, `claw`, `eagle`, `herald`) and status.
- `GET /api/files` — Retrieve workspace file tree and metadata.
- `GET /api/file/content?path=<relative_path>` — Read contents of a workspace file.
- `POST /api/reindex` — Trigger full workspace file re-indexing.
- `POST /api/analyze-document` — Submit document path for Eagle extraction (`{"file_path": "...", "query": "..."}`).
- `POST /api/generate-presentation` — Create presentation (`{"topic": "...", "num_slides": 10, "format": "both"}`).
- `POST /api/debug-screen` — Trigger vision diagnosis of current desktop screen.

### WebSocket Endpoint:
- `ws://127.0.0.1:8000/ws` — Real-time bidirectional streaming for chat, code tokens, artifacts, and permission approvals.

---

## 🧪 Running Integration Tests

The project includes an automated test suite verifying the Base Agent infrastructure, Orchestrator routing, specialized agents, document parsers, slide generators, vision debuggers, and server REST endpoints.

Run the test suite with:

```bash
python test_multi_agent.py
```

Expected output:
```text
Running integration tests...
  [PASS] Base agent classes.
  [PASS] Orchestrator initialization & properties.
  [PASS] Orchestrator routing.
  [PASS] Eagle agent handling & context building.
  [PASS] Slide builder.
  [PASS] DebugCard formatting.
  [PASS] Vision debugger base64 & data URI handling.
  [PASS] Server REST API.

=== ALL INTEGRATION TESTS PASSED SUCCESSFULLY! ===
```

---

## 🛠️ Troubleshooting & FAQ

### 1. `Connection Refused` or `Failed to connect to Ollama`
- **Cause**: Ollama is not running or is bound to a different port/host.
- **Solution**:
  1. Open a terminal and run `ollama serve`.
  2. Test in your browser: `http://localhost:11434`.
  3. If running Ollama on a separate machine or Docker, update `OLLAMA_BASE_URL` in `.env` (e.g., `http://192.168.1.50:11434`).

### 2. `Model not found` error
- **Cause**: The model specified in `.env` is not yet downloaded into Ollama.
- **Solution**:
  Run `ollama pull <model_name>` in your terminal (e.g. `ollama pull qwen2.5-coder:7b`).

### 3. Out of Memory (OOM) / Slow Inference
- **Cause**: The chosen model parameter size exceeds available system RAM or GPU VRAM.
- **Solution**:
  Switch to a lighter quantized model in `.env` or via the UI `/model` selector:
  - Use `qwen2.5-coder:7b` or `qwen2.5-coder:1.5b`.
  - For vision tasks, use `llava:7b` instead of larger multimodal models.

### 4. PowerShell Script Execution Policy on Windows
- **Cause**: Windows default policy restricts running virtual environment activation scripts.
- **Solution**:
  Run the following command once in PowerShell:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```

### 5. Port 8000 Already in Use
- **Solution**: Run the web server on a different port:
  ```bash
  python main.py --web --port 8080
  ```

---

## 📁 Project Structure

```
my_neo-agent/
├── agent/                      # Multi-agent core logic & orchestrator
│   ├── base_agent.py           # Abstract BaseAgent, AgentTask, AgentResponse, AgentArtifact
│   ├── orchestrator.py         # MasterOrchestrator & intent router
│   ├── neo_agent.py            # Neo Agent (HTML/CSS/JS web apps & games)
│   ├── claw_agent.py           # Claw Agent (Next.js & full-stack architect)
│   ├── eagle_agent.py          # Eagle Agent (Code review, auto-fixer, vision debug)
│   ├── herald_agent.py         # Herald Agent (Reveal.js & PowerPoint slide builder)
│   ├── prompts.py              # System prompts for all agents & orchestrator
│   ├── graph.py                # LangGraph state graph definitions
│   ├── state.py                # LangGraph agent state schemas
│   └── nodes.py                # Execution and tool calling nodes
├── tools/                      # Tool definitions for agents
│   ├── file_tools.py           # Workspace file I/O & safe path validation
│   ├── code_executor.py        # Sandboxed Python & PowerShell code execution
│   ├── document_tools.py       # PDF, PPTX, Excel, and code extraction tools
│   ├── slide_builder.py        # Reveal.js HTML and python-pptx builder
│   ├── vision_debugger.py      # Screenshot capture & multimodal vision debugger
│   ├── web_search.py           # DuckDuckGo search integration
│   └── rag_tools.py            # Vector memory & ChromaDB search
├── ui/                         # Web UI frontend dashboard
│   ├── index.html              # Modern single-page app layout
│   ├── app.js                  # WebSocket client & real-time UI controller
│   ├── style.css               # Cyberpunk / Carbon design system styling
│   └── mascot.js               # Web UI interactive mascot renderer
├── data/                       # Storage for checkpoints, DBs, and outputs
│   ├── checkpoints.db          # LangGraph execution checkpoints
│   ├── chat_history.db         # Persistent chat history database
│   ├── presentations/          # Generated .html & .pptx slide presentations
│   └── analysis_output/        # Eagle code analysis reports
├── indexer.py                  # Codebase scanner, line counter, & search engine
├── config.py                   # Centralized Pydantic settings & environment loader
├── server.py                   # FastAPI REST API & WebSocket server
├── cli.py                      # Interactive Rich terminal CLI
├── desktop_mascot.py           # Floating Tkinter desktop companion app
├── main.py                     # Unified entrypoint (--web, --cli, --desktop)
├── test_multi_agent.py         # Multi-agent automated integration test suite
├── requirements.txt            # Python package dependencies
├── .env.example                # Example environment configuration template
└── README.md                   # Project documentation
```

---

## 📄 License

This project is licensed under the **MIT License**.
