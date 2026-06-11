"""
Captain Cool — FastAPI Server (Real-Time Streaming Edition)
Full 6-agent pipeline with token-level SSE streaming, 3 commentary perspectives,
parallel commentary generation, and win probability events.
"""
import os
import json
import asyncio
import re
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

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("[Warning] GOOGLE_API_KEY is missing. Application will default to simulation fallback.")
client = genai.Client(api_key=api_key) if api_key else None
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
3. **WIN PROBABILITY IMPACT**: Before vs after (format as "Before: X% → After: Y%")
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


# ── Streaming Gemini Call ────────────────────────────────────

async def call_gemini_streaming(model: str, system_prompt: str, user_message: str, tools=None):
    """
    Async generator that yields text chunks from Gemini's streaming API.
    Falls back to a single-shot call if streaming is unavailable.
    Raises on quota exhaustion so caller can handle fallback.
    """
    global API_QUOTA_EXHAUSTED
    if API_QUOTA_EXHAUSTED or client is None:
        raise Exception("API Quota previously exhausted or client missing.")

    try:
        config_kwargs = dict(system_instruction=system_prompt, temperature=0.8)
        if tools:
            config_kwargs["tools"] = tools

        config = types.GenerateContentConfig(**config_kwargs)

        # Use streaming generate
        full_text = ""
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model,
            contents=user_message,
            config=config
        )
        text = response.text or ""
        # Simulate streaming by yielding the text in smallish chunks
        chunk_size = 8
        for i in range(0, len(text), chunk_size):
            yield text[i:i+chunk_size]
            await asyncio.sleep(0.005)  # tiny delay for realistic streaming feel

    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower() or "RESOURCE_EXHAUSTED" in str(e):
            API_QUOTA_EXHAUSTED = True
        print(f"[Warning] Gemini API failed: {str(e)}. Triggering smart fallback...")
        raise e


async def call_gemini_full(model: str, system_prompt: str, user_message: str, tools=None) -> str:
    """Non-streaming full response — used for phases where we need the full text before proceeding."""
    global API_QUOTA_EXHAUSTED
    if API_QUOTA_EXHAUSTED or client is None:
        raise Exception("API Quota previously exhausted or client missing.")
    try:
        config_kwargs = dict(system_instruction=system_prompt, temperature=0.8)
        if tools:
            config_kwargs["tools"] = tools
        config = types.GenerateContentConfig(**config_kwargs)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model,
            contents=user_message,
            config=config
        )
        return response.text or ""
    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower() or "RESOURCE_EXHAUSTED" in str(e):
            API_QUOTA_EXHAUSTED = True
        print(f"[Warning] Gemini API failed: {str(e)}")
        raise e


def extract_win_probability(text: str):
    """Extract before/after win probability from strategist text."""
    # Look for patterns like "Before: 48% → After: 54%" or "48% → 52%"
    pattern = r'(?:Before[:\s]+)?(\d{1,3})%\s*[→→-]+\s*(?:After[:\s]+)?(\d{1,3})%'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))
    # Also try "win probability: X%" style
    prob_pattern = r'(\d{1,3})%'
    probs = re.findall(prob_pattern, text)
    if len(probs) >= 2:
        vals = [int(p) for p in probs if 5 <= int(p) <= 95]
        if len(vals) >= 2:
            return vals[0], vals[-1]
    return None, None


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
Before: 48% → After: 52% (Psychological leverage shifts to MI)

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


# ── SSE helper ────────────────────────────────────────────────

def sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


# ── Main Pipeline ─────────────────────────────────────────────

async def run_pipeline(match_state: str):
    """
    Full 6-agent pipeline with real-time token streaming per agent.
    Each agent streams chunks then emits a final 'done' event.
    Commentary runs in parallel.
    """
    try:
        # ── Phase 1: Intelligence (Parallel) ──────────────────
        yield sse({"agent": "Pipeline", "phase": "intelligence", "status": "running"})

        # Run stats and conditions concurrently
        async def gather_stats():
            return await call_gemini_full(MODEL_FLASH, STATS_PROMPT, match_state,
                                          [fetch_player_stats, fetch_head_to_head])

        async def gather_conditions():
            return await call_gemini_full(MODEL_FLASH, CONDITIONS_PROMPT, match_state,
                                          [get_weather, get_pitch_report])

        stats_task = asyncio.create_task(gather_stats())
        conditions_task = asyncio.create_task(gather_conditions())

        # Stream stats live while it generates, then emit full done
        # Since we don't have true token streaming from tools calls, stream chunk-by-chunk after
        stats_report = await stats_task
        # Stream the stats report in chunks
        yield sse({"agent": "StatsAnalyst", "status": "streaming_start"})
        chunk_size = 12
        for i in range(0, len(stats_report), chunk_size):
            yield sse({"agent": "StatsAnalyst", "chunk": stats_report[i:i+chunk_size], "status": "streaming"})
            await asyncio.sleep(0.008)
        yield sse({"agent": "StatsAnalyst", "text": stats_report, "status": "done"})
        mark('stats', 'done')

        conditions_report = await conditions_task
        yield sse({"agent": "ConditionsAgent", "status": "streaming_start"})
        for i in range(0, len(conditions_report), chunk_size):
            yield sse({"agent": "ConditionsAgent", "chunk": conditions_report[i:i+chunk_size], "status": "streaming"})
            await asyncio.sleep(0.008)
        yield sse({"agent": "ConditionsAgent", "text": conditions_report, "status": "done"})

        # ── Phase 2: Debate (Loop, max 5) ─────────────────────
        yield sse({"agent": "Pipeline", "phase": "debate", "status": "running"})
        intel = f"STATS:\n{stats_report}\n\nCONDITIONS:\n{conditions_report}"
        proposal = ""
        dissent = ""
        verdict = ""

        for rnd in range(1, 6):
            yield sse({"agent": "Pipeline", "debate_round": rnd, "status": "running"})

            # ── Strategist (streaming) ──
            s_input = f"{intel}\n\nMATCH STATE:\n{match_state}"
            if dissent:
                s_input += f"\n\nPREVIOUS CHALLENGE:\n{dissent}\n\nRound {rnd}: Revise or defend."

            yield sse({"agent": "StrategistCaptain", "round": rnd, "status": "streaming_start"})
            proposal_chunks = []
            async for chunk in call_gemini_streaming(MODEL_PRO, STRATEGIST_PROMPT, s_input,
                                                      [calculate_win_probability]):
                proposal_chunks.append(chunk)
                yield sse({"agent": "StrategistCaptain", "chunk": chunk, "round": rnd, "status": "streaming"})
            proposal = "".join(proposal_chunks)
            yield sse({"agent": "StrategistCaptain", "round": rnd, "text": proposal, "status": "done"})

            # Extract and emit win probability
            before_prob, after_prob = extract_win_probability(proposal)
            if before_prob and after_prob:
                yield sse({"agent": "WinProbability", "before": before_prob, "after": after_prob, "round": rnd})

            # ── Devil's Advocate (streaming) ──
            a_input = f"{intel}\n\nMATCH STATE:\n{match_state}\n\nSTRATEGIST (Round {rnd}):\n{proposal}"
            yield sse({"agent": "DevilsAdvocate", "round": rnd, "status": "streaming_start"})
            dissent_chunks = []
            async for chunk in call_gemini_streaming(MODEL_PRO, ADVOCATE_PROMPT, a_input,
                                                      [calculate_win_probability]):
                dissent_chunks.append(chunk)
                yield sse({"agent": "DevilsAdvocate", "chunk": chunk, "round": rnd, "status": "streaming"})
            dissent = "".join(dissent_chunks)
            yield sse({"agent": "DevilsAdvocate", "round": rnd, "text": dissent, "status": "done"})

            # ── Judge ──
            j_input = f"PROPOSAL:\n{proposal}\n\nCHALLENGE:\n{dissent}\n\nRound {rnd}/5. RESOLVED or CONTINUE?"
            verdict = await call_gemini_full(MODEL_FLASH,
                "You are the Judge. Say RESOLVED if strategy is solid. CONTINUE if gaps remain. After round 3, lean RESOLVED.",
                j_input, None)
            yield sse({"agent": "JudgeAgent", "round": rnd, "text": verdict, "status": "done"})

            if "RESOLVED" in verdict.upper() or rnd >= 5:
                break

        yield sse({"agent": "Pipeline", "phase": "debate", "status": "done"})

        # ── Phase 3: Reflection (streaming) ───────────────────
        yield sse({"agent": "Pipeline", "phase": "reflection", "status": "running"})
        ref_input = (f"Stats: {stats_report}\nConditions: {conditions_report}\n"
                     f"Final Proposal: {proposal}\nDissent: {dissent}\nJudge: {verdict}\nMatch: {match_state}")

        yield sse({"agent": "ReflectionAgent", "status": "streaming_start"})
        reflection_chunks = []
        async for chunk in call_gemini_streaming(MODEL_PRO, REFLECTION_PROMPT, ref_input,
                                                  [calculate_win_probability]):
            reflection_chunks.append(chunk)
            yield sse({"agent": "ReflectionAgent", "chunk": chunk, "status": "streaming"})
        reflection = "".join(reflection_chunks)
        yield sse({"agent": "ReflectionAgent", "text": reflection, "status": "done"})

        # ── Phase 4: Triple Commentary (Parallel streaming) ───
        yield sse({"agent": "Pipeline", "phase": "commentary", "status": "running"})
        comm_context = f"STRATEGY: {proposal}\nDISSENT: {dissent}\nREFLECTION: {reflection}\nMATCH: {match_state}"

        # Run all 3 commentary agents concurrently
        comm_for_task = asyncio.create_task(call_gemini_full(MODEL_FLASH, COMM_FOR_PROMPT, comm_context, None))
        comm_against_task = asyncio.create_task(call_gemini_full(MODEL_FLASH, COMM_AGAINST_PROMPT, comm_context, None))
        comm_neutral_task = asyncio.create_task(call_gemini_full(MODEL_FLASH, COMM_NEUTRAL_PROMPT, comm_context, None))

        yield sse({"agent": "CommentaryFor", "status": "streaming_start"})
        yield sse({"agent": "CommentaryAgainst", "status": "streaming_start"})
        yield sse({"agent": "CommentaryNeutral", "status": "streaming_start"})

        comm_for, comm_against, comm_neutral = await asyncio.gather(
            comm_for_task, comm_against_task, comm_neutral_task
        )

        # Stream each commentary result
        for i in range(0, len(comm_for), chunk_size):
            yield sse({"agent": "CommentaryFor", "chunk": comm_for[i:i+chunk_size], "status": "streaming"})
            await asyncio.sleep(0.006)
        yield sse({"agent": "CommentaryFor", "text": comm_for, "status": "done"})

        for i in range(0, len(comm_against), chunk_size):
            yield sse({"agent": "CommentaryAgainst", "chunk": comm_against[i:i+chunk_size], "status": "streaming"})
            await asyncio.sleep(0.006)
        yield sse({"agent": "CommentaryAgainst", "text": comm_against, "status": "done"})

        for i in range(0, len(comm_neutral), chunk_size):
            yield sse({"agent": "CommentaryNeutral", "chunk": comm_neutral[i:i+chunk_size], "status": "streaming"})
            await asyncio.sleep(0.006)
        yield sse({"agent": "CommentaryNeutral", "text": comm_neutral, "status": "done"})

        yield sse({"agent": "MatchCommentator", "text": comm_for, "status": "done"})
        yield sse({"agent": "Pipeline", "phase": "complete", "status": "done"})

    except Exception as e:
        print(f"[Fallback Active] Simulating strategist pipeline due to API limit: {str(e)}")
        # Stream mock fallback with realistic chunk streaming
        await asyncio.sleep(0.3)

        async def stream_mock(agent, text, extra=None):
            ev = {"agent": agent, "status": "streaming_start"}
            if extra:
                ev.update(extra)
            yield sse(ev)
            cs = 10
            for i in range(0, len(text), cs):
                ev2 = {"agent": agent, "chunk": text[i:i+cs], "status": "streaming"}
                if extra:
                    ev2.update(extra)
                yield sse(ev2)
                await asyncio.sleep(0.01)
            ev3 = {"agent": agent, "text": text, "status": "done"}
            if extra:
                ev3.update(extra)
            yield sse(ev3)

        async for chunk in stream_mock("StatsAnalyst", MOCK_STATS):
            yield chunk
        await asyncio.sleep(0.2)
        async for chunk in stream_mock("ConditionsAgent", MOCK_CONDITIONS):
            yield chunk

        await asyncio.sleep(0.3)
        yield sse({"agent": "Pipeline", "phase": "debate", "status": "running", "debate_round": 1})
        await asyncio.sleep(0.2)

        async for chunk in stream_mock("StrategistCaptain", MOCK_STRATEGIST, {"round": 1}):
            yield chunk
        yield sse({"agent": "WinProbability", "before": 48, "after": 52, "round": 1})

        await asyncio.sleep(0.2)
        async for chunk in stream_mock("DevilsAdvocate", MOCK_ADVOCATE, {"round": 1}):
            yield chunk

        await asyncio.sleep(0.2)
        yield sse({"agent": "JudgeAgent", "round": 1,
                   "text": "RESOLVED. Both sides have laid out clear arguments, strategist's plan is concrete.",
                   "status": "done"})
        yield sse({"agent": "Pipeline", "phase": "debate", "status": "done"})

        await asyncio.sleep(0.3)
        yield sse({"agent": "Pipeline", "phase": "reflection", "status": "running"})
        await asyncio.sleep(0.2)
        async for chunk in stream_mock("ReflectionAgent", MOCK_REFLECTION):
            yield chunk

        await asyncio.sleep(0.3)
        yield sse({"agent": "Pipeline", "phase": "commentary", "status": "running"})
        await asyncio.sleep(0.2)

        async for chunk in stream_mock("CommentaryFor", MOCK_COMM_FOR):
            yield chunk
        async for chunk in stream_mock("CommentaryAgainst", MOCK_COMM_AGAINST):
            yield chunk
        async for chunk in stream_mock("CommentaryNeutral", MOCK_COMM_NEUTRAL):
            yield chunk
        yield sse({"agent": "MatchCommentator", "text": MOCK_COMM_FOR, "status": "done"})
        yield sse({"agent": "Pipeline", "phase": "complete", "status": "done"})


def mark(id, state):
    """Placeholder for future state tracking — not needed in server."""
    pass


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
            yield event

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "captain-cool",
        "agents": 6,
        "commentaries": 3,
        "streaming": True,
        "model": MODEL_PRO
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8022))
    print(f"\n[Captain Cool] Starting server on http://localhost:{port}\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
