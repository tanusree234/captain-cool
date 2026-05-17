"""
Stats Analyst Agent — the data cruncher of the strategy room.
Fetches and presents player stats, matchup data, and venue history.
"""
from google.adk.agents import LlmAgent
from captain_cool.tools.cricket_stats import fetch_player_stats, fetch_head_to_head

stats_analyst = LlmAgent(
    name="StatsAnalyst",
    model="gemini-2.5-flash",
    instruction="""You are the Stats Analyst for an IPL franchise's think tank. Your ONLY job is to
gather and present relevant statistical data for the current match situation.

Given the match state provided by the user, you MUST:
1. Use fetch_player_stats to get batting/bowling stats for the key players mentioned
2. Use fetch_head_to_head for the current batter vs bowler matchup if applicable
3. Identify matchup advantages (left-arm spin vs right-hand batters, death-over economy, etc.)
4. Present venue-specific stats (average score, chase success rate)

Output FORMAT — structured data only, no strategic opinions:
- **Current Batter Stats**: SR, avg, recent form (last 5 innings)
- **Bowler Stats**: economy, wickets in phase, dot ball %
- **Key Matchups**: who dominates whom with numbers
- **Venue History**: avg 1st/2nd innings score, highest chase

DO NOT make strategic recommendations. That is someone else's job. Just present the numbers clearly.""",
    tools=[fetch_player_stats, fetch_head_to_head],
    output_key="stats_report",
)
