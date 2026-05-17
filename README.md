# 🏏 Captain Cool — The Multi-Agent IPL Match Strategist

> *"Process is more important than result." — MS Dhoni*

**Captain Cool** is an agentic AI system that acts as a virtual IPL captain — making tactical decisions the way Dhoni, Rohit, or Hardik would. Built entirely on the **Google Gemini** stack.

## 🏗️ Architecture

```
User Input (Match State)
       │
       ▼
┌─────────────────────────────────────────────────┐
│  Phase 1: Intelligence Gathering (Parallel)      │
│  ├── 📊 Stats Analyst (gemini-2.5-flash)        │
│  └── 🌦️  Conditions Agent (gemini-2.5-flash)    │
├─────────────────────────────────────────────────┤
│  Phase 2: The Debate (Loop, max 5 rounds)        │
│  ├── 🧠 Strategist Captain (gemini-2.5-pro)     │
│  ├── 😈 Devil's Advocate (gemini-2.5-pro)        │
│  └── ⚖️ Judge Agent (gemini-2.5-flash)           │
├─────────────────────────────────────────────────┤
│  Phase 3: Reflection                             │
│  └── 🪞 Reflection Agent (gemini-2.5-pro)        │
│      → Confidence Score, Counterfactuals          │
├─────────────────────────────────────────────────┤
│  Phase 4: Commentary                             │
│  └── 🎙️ Match Commentator (gemini-2.5-flash)     │
│      → Fan-friendly cricket talk output           │
└─────────────────────────────────────────────────┘
       │
       ▼
Final Decision + Debate Transcript + Confidence Score
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Your API Key
Edit `.env` and add your Google AI Studio API key:
```
GOOGLE_API_KEY=your_key_here
```

### 3. Run the Server
```bash
python server.py
```

### 4. Open the UI
Navigate to `http://localhost:8000` in your browser.

### Alternative: Run with ADK CLI
```bash
adk web captain_cool
```

## 🤖 The 6 Agents

| Agent | Model | Role |
|-------|-------|------|
| 📊 Stats Analyst | gemini-2.5-flash | Fetches player stats, matchup data, venue history |
| 🌦️ Conditions Agent | gemini-2.5-flash | Weather, pitch, dew analysis via live APIs |
| 🧠 Strategist Captain | gemini-2.5-pro | Makes the tactical call — thinks like Dhoni |
| 😈 Devil's Advocate | gemini-2.5-pro | Challenges every decision aggressively |
| 🪞 Reflection Agent | gemini-2.5-pro | Confidence scoring, blind spots, counterfactuals |
| 🎙️ Match Commentator | gemini-2.5-flash | Fan-friendly cricket commentary output |

## 🔧 Tools (Gemini Function Calling)

- **fetch_player_stats** — CricketData.org API (fallback: curated JSON)
- **fetch_head_to_head** — Batter vs bowler matchup data
- **get_weather** — Live weather from Open-Meteo API (free, no key)
- **get_pitch_report** — Venue-specific pitch behavior database
- **calculate_win_probability** — DLS-inspired win probability model

## 📋 Tech Stack

- **Google Gemini 2.5 Pro / Flash** — Core LLM
- **Google ADK** — Multi-agent orchestration framework
- **google-genai SDK** — Gemini API with function calling
- **FastAPI** — Backend server with SSE streaming
- **Vanilla HTML/CSS/JS** — Premium dark-themed frontend
- **Open-Meteo API** — Real-time weather data

## 📁 Project Structure

```
captain-cool/
├── captain_cool/           # ADK agent package
│   ├── agent.py            # Root orchestrator
│   ├── agents/             # 6 individual agents
│   └── tools/              # 5 function-calling tools
├── frontend/               # Web UI
├── server.py               # FastAPI server
├── requirements.txt
└── .env                    # API keys
```

## Built With
- 🧠 Google Gemini 2.5
- 🔧 Google ADK
- ⚡ Google Antigravity (vibe-coded!)
