"""
Captain Cool — Root Agent Orchestrator
The multi-agent IPL Match Strategist built on Google ADK + Gemini.

Architecture:
  Phase 1: ParallelAgent  → Stats Analyst + Conditions Agent (gather intel)
  Phase 2: LoopAgent      → Strategist ↔ Devil's Advocate ↔ Judge (debate, max 5 rounds)
  Phase 3: SequentialAgent → Reflection Agent (confidence + counterfactuals)
  Phase 4: SequentialAgent → Match Commentator (fan-friendly output)
"""
from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent

from captain_cool.agents.stats_analyst import stats_analyst
from captain_cool.agents.conditions_agent import conditions_agent
from captain_cool.agents.strategist_captain import strategist_captain
from captain_cool.agents.devils_advocate import devils_advocate
from captain_cool.agents.judge import judge_agent
from captain_cool.agents.reflection_agent import reflection_agent
from captain_cool.agents.match_commentator import match_commentator

# ── Phase 1: Intelligence Gathering (Parallel) ──────────────────────────────
# Stats Analyst and Conditions Agent work simultaneously to gather data.
intelligence_phase = ParallelAgent(
    name="IntelligenceGathering",
    sub_agents=[stats_analyst, conditions_agent],
)

# ── Phase 2: The Debate (Loop) ──────────────────────────────────────────────
# Strategist proposes → Devil's Advocate challenges → Judge decides continue/stop.
# Max 5 rounds of iterative improvement.
debate_round = SequentialAgent(
    name="DebateRound",
    sub_agents=[strategist_captain, devils_advocate, judge_agent],
)

debate_loop = LoopAgent(
    name="StrategyDebate",
    sub_agents=[debate_round],
    max_iterations=5,
)

# ── Phase 3: Reflection ─────────────────────────────────────────────────────
# Post-debate quality check: confidence score, blind spots, counterfactuals.
reflection_phase = SequentialAgent(
    name="Reflection",
    sub_agents=[reflection_agent],
)

# ── Phase 4: Final Commentary Output ────────────────────────────────────────
# Translates everything into exciting, fan-friendly cricket commentary.
output_phase = SequentialAgent(
    name="FinalOutput",
    sub_agents=[match_commentator],
)

# ── Root Orchestrator ────────────────────────────────────────────────────────
root_agent = SequentialAgent(
    name="CaptainCool",
    description=(
        "Captain Cool — The Multi-Agent IPL Match Strategist. "
        "Thinks like Dhoni, debates like Kohli, commentates like Harsha Bhogle. "
        "Input the current match state and get a tactical decision with full reasoning, "
        "internal debate transcript, confidence score, and counterfactual analysis."
    ),
    sub_agents=[intelligence_phase, debate_loop, reflection_phase, output_phase],
)
