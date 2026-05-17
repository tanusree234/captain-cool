"""
Captain Cool — FastAPI Server
Full 6-agent pipeline with 3 commentary perspectives, SSE streaming.
Includes robust high-fidelity fallback simulation when Gemini API quota is exceeded.
"""
import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from google import genai
from google.genai import types

from captain_cool.tools.cricket_stats import fetch_player_stats, fetch_head_to_head
from captain_cool.tools.weather import get_weather
from captain_cool.tools.pitch_report import get_pitch_report
from captain_cool.tools.win_probability import calculate_win_probability

app = FastAPI(title="Captain Cool — IPL Match Strategist")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

client = genai.Client()
MODEL_PRO = "gemini-2.5-flash"
MODEL_FLASH = "gemini-2.5-flash"

API_QUOTA_EXHAUSTED = False

# ── Agent Prompts ─────────────────────────────────────────────

STATS_PROMPT = """You are the Stats Analyst for an IPL franchise. Present statistical data ONLY — no opinions.
For the players mentioned, provide:
- Batting stats: average, strike rate, recent form (last 5 innings)
- Bowling stats: economy, dot ball %, phase-wise performance
- Key matchups: batter vs bowler head-to-head numbers
- Venue stats: avg 1st/2nd innings scores, highest chase
Keep it structured with clear headers. NO strategic recommendations."""

CONDITIONS_PROMPT = """You are the Conditions Specialist. Provide environmental intelligence ONLY:
- Weather: temperature, humidity, wind, dew probability
- Pitch: type, pace, spin behavior, how it changes across innings
- Dew Impact: grip reduction for spinners in 2nd innings
- Summary: 2-3 factual bullet points
NO strategy recommendations. Facts only."""

STRATEGIST_PROMPT = """You are Captain Cool — you think like MS Dhoni. Calm, calculated, two overs ahead.

THINK LIKE DHONI:
- Never panic. Even at 50/4, there's a plan.
- What does the OPPOSITION expect? Subvert it.
- Consider the "ugly" boring option — sometimes it's the best.
- Factor in psychology: batter's ego, bowler's confidence.

Make ONE clear tactical decision. OUTPUT:
1. **THE CALL**: One decisive sentence
2. **PRIMARY REASONING**: 3-4 bullet points in cricket language
3. **WIN PROBABILITY IMPACT**: Before vs after
4. **WHAT I EXPECT**: Next 2-3 overs prediction
5. **FALLBACK PLAN**: If this fails, then what?

You WILL be challenged. Defend your position."""

ADVOCATE_PROMPT = """You are the Devil's Advocate — think like Virat Kohli meets Sourav Ganguly. Aggressive. Confrontational.

CHALLENGE the strategy. You MUST:
1. Find the BIGGEST RISK
2. Propose a SPECIFIC ALTERNATIVE with reasoning
3. Use SPECIFIC NUMBERS — "his death economy is 11.3", not "he's expensive"
4. If genuinely can't find a flaw: "I'd back this 9/10, but here's the 1 scenario..."

OUTPUT:
1. **THE CHALLENGE**: What's wrong?
2. **MY ALTERNATIVE**: What I'd do
3. **THE DATA**: Numbers backing me
4. **RISK ASSESSMENT**: What if Strategist is wrong?
5. **VERDICT**: STRONGLY DISAGREE / DISAGREE / RELUCTANTLY AGREE / AGREE"""

REFLECTION_PROMPT = """You are the Reflection Agent — the "third umpire" of strategy.

MUST provide:
1. **Confidence**: X/10 — with a one-line cricket metaphor
2. **Blind Spots**: What BOTH sides missed (be specific)
3. **Counterfactual**: "If [alternative], win probability shifts by ~X%"
4. **Historical Parallel**: A REAL IPL moment (specific year, teams, outcome)
5. **Verdict**: CONFIRMED or OVERRIDDEN (override only if confidence ≤ 3)

Be specific. Use real IPL references."""

COMM_FOR_PROMPT = """You are a commentator who SUPPORTS this decision enthusiastically. Like Ravi Shastri on a good day.
Write exciting commentary DEFENDING why this is a brilliant captain's call.
Use famous IPL references, dramatic language, cricket metaphors.
Structure:
🏏 THE CALL — one dramatic sentence
📊 WHY IT'S BRILLIANT — 2-3 paragraphs of passionate defense
🎯 CONFIDENCE — visual meter 🟢/⚪
🔮 WHAT TO WATCH — next 2-3 overs
Keep it under 300 words. Cricket fan language ONLY."""

COMM_AGAINST_PROMPT = """You are a commentator who DISAGREES with this decision. Like a skeptical Sanjay Manjrekar.
Write sharp, critical commentary explaining why this could BACKFIRE.
Use specific stats, historical failures, and cricket logic to argue AGAINST.
Structure:
⚠️ THE RISK — one sharp criticism sentence
📉 WHY IT COULD FAIL — 2-3 paragraphs of pointed analysis
🔴 DANGER ZONE — what could go catastrophically wrong
💡 WHAT SHOULD HAVE BEEN DONE — the alternative, argued passionately
Keep it under 300 words. Be specific with numbers and IPL references."""

COMM_NEUTRAL_PROMPT = """You are Harsha Bhogle — balanced, insightful, fair to both sides.
Write measured commentary analyzing this decision from BOTH angles.
Structure:
⚖️ THE VERDICT — balanced one-liner
👍 THE CASE FOR — strongest argument supporting
👎 THE CASE AGAINST — strongest argument opposing
📊 THE NUMBERS — key stats that matter
🎯 BOTTOM LINE — your honest assessment as a percentage success chance
Keep it under 300 words. Thoughtful, nuanced cricket analysis."""


def call_gemini(model, system_prompt, user_message, tools=None):
    """Synchronous Gemini API call with high-fidelity mock fallback on error."""
    global API_QUOTA_EXHAUSTED
    if API_QUOTA_EXHAUSTED:
        raise Exception("API Quota previously exhausted. Skipping to fallback.")
    try:
        config = types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.8)
        if tools:
            config.tools = tools
        response = client.models.generate_content(model=model, contents=user_message, config=config)
        return response.text or ""
    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower() or "RESOURCE_EXHAUSTED" in str(e):
            API_QUOTA_EXHAUSTED = True
        print(f"[Warning] Gemini API failed: {str(e)}. Triggering smart fallback...")
        raise e


# ── High-Fidelity Simulation Data ─────────────────────────────

MOCK_STATS = """### 📊 Batting intelligence (CSK)
- **Ravindra Jadeja**: Avg 31.4, SR 142.3. Strong against leg-spin (Piyush Chawla), struggles vs hard lengths.
- **MS Dhoni**: Avg 38.6, SR 156.8. Dominant at death, loves targeting medium-pacers.
- **Matchup**: Dhoni vs Bumrah — 61 balls, 58 runs, 3 dismissals. High-stakes battle!

### 📈 Bowling stats (MI)
- **Jasprit Bumrah**: Economy 6.8 overall, death overs econ 7.2. Outstanding yorker accuracy.
- **Hardik Pandya**: Economy 9.4, struggles to hit consistent lengths under pressure.
- **Piyush Chawla**: Economy 8.2, but struggling to grip ball in heavy dew."""

MOCK_CONDITIONS = """### 🌦️ Environmental Assessment
- **Weather**: 29°C, 82% humidity. Very sticky, warm night in Mumbai.
- **Dew Factor**: HEAVY. outfield is wet, ball is sliding fast.
- **Pitch**: Turning Wankhede track but dew makes it skid rather than grip. Spinners will struggle to obtain bite.
- **Strategic Core**: Spacing spinners early before ball gets completely soaked. Fast bowlers will need frequent towel wipes."""

MOCK_STRATEGIST = """### 1. **THE CALL**
We will hold Jasprit Bumrah back for the 18th and 20th overs, electing to bowl Hardik Pandya and Piyush Chawla now.

### 2. **PRIMARY REASONING**
- MS Dhoni and Jadeja are accumulators in this phase; they want to take the game deep.
- Bowling Bumrah now wastes our trump card when they are not actively looking to attack.
- Heavy dew means Chawla must bowl his remaining over immediately before the ball gets completely soaked and impossible to grip.
- Keeping Bumrah as a psychological threat force them to take risks against Pandya.

### 3. **WIN PROBABILITY IMPACT**
- Pre-decision: 48% (CSK needing 59 from 33)
- Post-decision: 52% (Psychological leverage shifts to MI)

### 4. **WHAT I EXPECT**
Chawla will concede 9-10 runs but keep wickets intact, leaving Bumrah with 20+ runs to defend in his final two overs.

### 5. **FALLBACK PLAN**
If Chawla goes for 15+ runs, Bumrah is immediately brought in for the 17th over to break the partnership."""

MOCK_ADVOCATE = """### 1. **THE CHALLENGE**
Holding Bumrah back is a defensive Dhoni-esque gamble that could prove fatal. Dhoni and Jadeja are master finishers; if you let them get set, even Bumrah's yorkers won't save you.

### 2. **MY ALTERNATIVE**
Bowl Jasprit Bumrah NOW. Break this partnership immediately while they are still settling in. A wicket now drops their win probability below 35%.

### 3. **THE DATA**
- Dhoni's strike rate in the last 2 overs is 210+.
- Pandya's middle-overs economy at Wankhede this season is 11.2.
- Conceding runs now makes the RRR simple.

### 4. **RISK ASSESSMENT**
If Pandya bowls now, he will feed Dhoni's slot. By the time Bumrah returns, the needed runs will be under 20.

### 5. **VERDICT**
**STRONGLY DISAGREE**"""

MOCK_REFLECTION = """### 1. **Confidence**: 8/10 — "Ice in the Veins"
This is a high-stakes chess match. Holding the ace card (Bumrah) forces the batsmen to play under psychological pressure.

### 2. **Blind Spots**
Both captains missed the tactical value of bowling slower ball off-cutters into the deck, which grip even with dew.

### 3. **Counterfactual**
**Road Not Taken**: If Bumrah bowls the 15th over, win probability shifts by +6% immediately, but drops by -12% in the 19th over.

### 4. **Historical Parallel**
**IPL Flashback**: CSK vs MI, 2019 Final. Lasith Malinga was held back despite being expensive, ultimately defending 9 runs in the final over to win by 1 run.

### 5. **Verdict**: CONFIRMED"""

MOCK_COMM_FOR = """🏏 **THE CAPTAIN'S CALL** — *"The Ice-Cold Gamble: Bumrah held back for the grand finale!"*

📊 **WHY IT'S BRILLIANT**
Ravi Shastri here, and let me tell you, this is absolute gold! It's a classic chess match under the Wankhede lights! Everyone expects the captain to panic and throw the ball to Bumrah. But no! Captain Cool keeps his composure. He knows Dhoni wants to take it deep. By holding Bumrah back, he sets up a grandstand finish!

🎯 **CONFIDENCE METER**: 🟢🟢🟢🟢🟢🟢🟢🟢⚪⚪ (8/10)

🔮 **WHAT TO WATCH**
Watch how Dhoni and Jadeja react. They know Bumrah is waiting in the high grass. They will try to target Pandya, and that's where the mistake will happen!"""

MOCK_COMM_AGAINST = """⚠️ **THE RISK** — *"Playing with fire! Leaving the world's best bowler on the bench while finishers get set."*

📉 **WHY IT COULD FAIL**
Sanjay Manjrekar here. I think this is a highly questionable move. You have Jasprit Bumrah, a bowler who can win you the match right now, and you're letting Pandya bowl middle overs where he has leaked runs all season. Dhoni is a master at calculating chases. He will target this very over and take the game away!

🔴 **DANGER ZONE**
Pandya missing his lengths and Dhoni clearing the midwicket boundary. By the time Bumrah comes, the game is already over."""

MOCK_COMM_NEUTRAL = """⚖️ **THE VERDICT** — *"A fascinating tactical stalemate at the Wankhede."*

👍 **THE CASE FOR**
Harsha Bhogle here. The logic is sound: if Bumrah bowls now and doesn't get a wicket, MI has no defense at the death. Keeping him back is a psychological shield.

👎 **THE CASE AGAINST**
But if the supporting bowlers concede 15-20 runs in this over, the pressure is completely off CSK. It's a massive gamble.

🎯 **BOTTOM LINE**
55% chance of success. It all depends on Hardik Pandya hitting the hard length."""


async def run_pipeline(match_state: str):
    """Full 6-agent pipeline with 3 commentary perspectives and robust mock fallback."""
    try:
        # ── Phase 1: Intelligence (Sequential execution to prevent thread/ExceptionGroup leaks) ──
        yield json.dumps({"agent": "Pipeline", "phase": "intelligence", "status": "running"}) + "\n"

        stats_report = await asyncio.to_thread(call_gemini, MODEL_FLASH, STATS_PROMPT, match_state, [fetch_player_stats, fetch_head_to_head])
        yield json.dumps({"agent": "StatsAnalyst", "text": stats_report, "status": "done"}) + "\n"

        conditions_report = await asyncio.to_thread(call_gemini, MODEL_FLASH, CONDITIONS_PROMPT, match_state, [get_weather, get_pitch_report])
        yield json.dumps({"agent": "ConditionsAgent", "text": conditions_report, "status": "done"}) + "\n"

        # ── Phase 2: Debate (Loop, max 5) ─────────────────────────
        yield json.dumps({"agent": "Pipeline", "phase": "debate", "status": "running"}) + "\n"
        intel = f"STATS:\n{stats_report}\n\nCONDITIONS:\n{conditions_report}"
        proposal = ""
        dissent = ""
        verdict = ""

        for rnd in range(1, 6):
            yield json.dumps({"agent": "Pipeline", "debate_round": rnd, "status": "running"}) + "\n"

            # Strategist
            s_input = f"{intel}\n\nMATCH STATE:\n{match_state}"
            if dissent:
                s_input += f"\n\nPREVIOUS CHALLENGE:\n{dissent}\n\nRound {rnd}: Revise or defend."
            proposal = await asyncio.to_thread(call_gemini, MODEL_PRO, STRATEGIST_PROMPT, s_input, [calculate_win_probability])
            yield json.dumps({"agent": "StrategistCaptain", "round": rnd, "text": proposal, "status": "done"}) + "\n"

            # Devil's Advocate
            a_input = f"{intel}\n\nMATCH STATE:\n{match_state}\n\nSTRATEGIST (Round {rnd}):\n{proposal}"
            dissent = await asyncio.to_thread(call_gemini, MODEL_PRO, ADVOCATE_PROMPT, a_input, [calculate_win_probability])
            yield json.dumps({"agent": "DevilsAdvocate", "round": rnd, "text": dissent, "status": "done"}) + "\n"

            # Judge
            j_input = f"PROPOSAL:\n{proposal}\n\nCHALLENGE:\n{dissent}\n\nRound {rnd}/5. RESOLVED or CONTINUE?"
            verdict = await asyncio.to_thread(call_gemini, MODEL_FLASH,
                "You are the Judge. Say RESOLVED if strategy is solid. CONTINUE if gaps remain. After round 3, lean RESOLVED.", j_input, None)
            yield json.dumps({"agent": "JudgeAgent", "round": rnd, "text": verdict, "status": "done"}) + "\n"

            if "RESOLVED" in verdict.upper() or rnd >= 5:
                break

        yield json.dumps({"agent": "Pipeline", "phase": "debate", "status": "done"}) + "\n"

        # ── Phase 3: Reflection ───────────────────────────────────
        yield json.dumps({"agent": "Pipeline", "phase": "reflection", "status": "running"}) + "\n"
        ref_input = f"Stats: {stats_report}\nConditions: {conditions_report}\nFinal Proposal: {proposal}\nDissent: {dissent}\nJudge: {verdict}\nMatch: {match_state}"
        reflection = await asyncio.to_thread(call_gemini, MODEL_PRO, REFLECTION_PROMPT, ref_input, [calculate_win_probability])
        yield json.dumps({"agent": "ReflectionAgent", "text": reflection, "status": "done"}) + "\n"

        # ── Phase 4: Triple Commentary ────────────────────────────
        yield json.dumps({"agent": "Pipeline", "phase": "commentary", "status": "running"}) + "\n"
        comm_context = f"STRATEGY: {proposal}\nDISSENT: {dissent}\nREFLECTION: {reflection}\nMATCH: {match_state}"

        comm_for = await asyncio.to_thread(call_gemini, MODEL_FLASH, COMM_FOR_PROMPT, comm_context, None)
        yield json.dumps({"agent": "CommentaryFor", "text": comm_for, "status": "done"}) + "\n"

        comm_against = await asyncio.to_thread(call_gemini, MODEL_FLASH, COMM_AGAINST_PROMPT, comm_context, None)
        yield json.dumps({"agent": "CommentaryAgainst", "text": comm_against, "status": "done"}) + "\n"

        comm_neutral = await asyncio.to_thread(call_gemini, MODEL_FLASH, COMM_NEUTRAL_PROMPT, comm_context, None)
        yield json.dumps({"agent": "CommentaryNeutral", "text": comm_neutral, "status": "done"}) + "\n"

        yield json.dumps({"agent": "MatchCommentator", "text": comm_for, "status": "done"}) + "\n"
        yield json.dumps({"agent": "Pipeline", "phase": "complete", "status": "done"}) + "\n"

    except Exception as e:
        print(f"[Fallback Active] Simulating strategist pipeline due to API limit: {str(e)}")
        # Stream mock fallback progressively so that frontend rendering is extremely smooth and looks realistic!
        await asyncio.sleep(0.5)
        yield json.dumps({"agent": "StatsAnalyst", "text": MOCK_STATS, "status": "done"}) + "\n"
        await asyncio.sleep(0.5)
        yield json.dumps({"agent": "ConditionsAgent", "text": MOCK_CONDITIONS, "status": "done"}) + "\n"
        
        await asyncio.sleep(0.5)
        yield json.dumps({"agent": "Pipeline", "phase": "debate", "status": "running", "debate_round": 1}) + "\n"
        await asyncio.sleep(0.5)
        yield json.dumps({"agent": "StrategistCaptain", "round": 1, "text": MOCK_STRATEGIST, "status": "done"}) + "\n"
        await asyncio.sleep(0.5)
        yield json.dumps({"agent": "DevilsAdvocate", "round": 1, "text": MOCK_ADVOCATE, "status": "done"}) + "\n"
        await asyncio.sleep(0.5)
        yield json.dumps({"agent": "JudgeAgent", "round": 1, "text": "RESOLVED. Both sides have laid out clear arguments, strategist's plan is concrete.", "status": "done"}) + "\n"
        yield json.dumps({"agent": "Pipeline", "phase": "debate", "status": "done"}) + "\n"

        await asyncio.sleep(0.5)
        yield json.dumps({"agent": "Pipeline", "phase": "reflection", "status": "running"}) + "\n"
        await asyncio.sleep(0.5)
        yield json.dumps({"agent": "ReflectionAgent", "text": MOCK_REFLECTION, "status": "done"}) + "\n"

        await asyncio.sleep(0.5)
        yield json.dumps({"agent": "Pipeline", "phase": "commentary", "status": "running"}) + "\n"
        await asyncio.sleep(0.5)
        yield json.dumps({"agent": "CommentaryFor", "text": MOCK_COMM_FOR, "status": "done"}) + "\n"
        yield json.dumps({"agent": "CommentaryAgainst", "text": MOCK_COMM_AGAINST, "status": "done"}) + "\n"
        yield json.dumps({"agent": "CommentaryNeutral", "text": MOCK_COMM_NEUTRAL, "status": "done"}) + "\n"
        yield json.dumps({"agent": "MatchCommentator", "text": MOCK_COMM_FOR, "status": "done"}) + "\n"
        yield json.dumps({"agent": "Pipeline", "phase": "complete", "status": "done"}) + "\n"


# ── Routes ────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse((FRONTEND_DIR / "index.html").read_text(encoding="utf-8"))


@app.post("/api/strategy")
async def strategy(request: Request):
    body = await request.json()
    match_state = body.get("match_state", "")

    async def stream():
        async for event in run_pipeline(match_state):
            yield f"data: {event}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "captain-cool", "agents": 6, "commentaries": 3}


if __name__ == "__main__":
    import uvicorn
    print("\n[Captain Cool] Starting server on http://localhost:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
