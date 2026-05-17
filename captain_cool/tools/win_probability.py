"""
Win probability calculator — simplified DLS-inspired model for IPL T20 matches.
Used by Strategist Captain, Devil's Advocate, and Reflection Agent.
"""


def calculate_win_probability(
    current_score: int,
    wickets_lost: int,
    overs_completed: float,
    target: int,
    innings: int
) -> dict:
    """
    Calculates the estimated win probability for the batting team based on
    current match situation using a simplified DLS-inspired model.

    Args:
        current_score: Runs scored so far in the current innings.
        wickets_lost: Number of wickets fallen (0-10).
        overs_completed: Overs bowled as a decimal (e.g., 14.3 means 14 overs 3 balls).
        target: Target score to chase. Use 0 if first innings.
        innings: Current innings number (1 or 2).

    Returns:
        Dictionary with win probability metrics, required run rate, and a
        human-readable assessment of the batting team's position.
    """
    # Convert overs to balls
    full_overs = int(overs_completed)
    part_balls = round((overs_completed - full_overs) * 10)
    balls_bowled = full_overs * 6 + part_balls
    balls_remaining = max(0, 120 - balls_bowled)

    if innings == 1:
        # First innings: project total based on current run rate and wickets
        run_rate = current_score / max(balls_bowled / 6, 0.1)

        # Wicket penalty factor — more wickets = lower projected total
        wicket_factors = [1.0, 0.95, 0.88, 0.80, 0.70, 0.58, 0.45, 0.32, 0.20, 0.10, 0.05]
        wicket_factor = wicket_factors[min(wickets_lost, 10)]

        # Phase acceleration: death overs typically score faster
        if full_overs < 6:
            phase_factor = 1.15  # Powerplay momentum
        elif full_overs < 15:
            phase_factor = 1.05  # Middle overs slight uptick expected
        else:
            phase_factor = 0.95  # Harder to accelerate with fewer balls

        projected = int(current_score + (run_rate * (balls_remaining / 6) * wicket_factor * phase_factor))
        projected = max(projected, current_score)  # Can't project below current score

        # IPL average score benchmark
        avg_ipl_score = 170
        strength = "above_par" if projected > avg_ipl_score else "below_par" if projected < 155 else "par"

        return {
            "projected_total": projected,
            "current_run_rate": round(run_rate, 2),
            "wicket_resource_remaining": f"{wicket_factor * 100:.0f}%",
            "balls_remaining": balls_remaining,
            "phase": "powerplay" if full_overs < 6 else "middle" if full_overs < 15 else "death",
            "strength": strength,
            "assessment": f"Projected total: {projected}. {'Strong position' if strength == 'above_par' else 'Need acceleration' if strength == 'below_par' else 'Par score territory'}."
        }

    # Second innings
    runs_needed = max(0, target - current_score)

    if balls_remaining == 0:
        return {
            "win_probability": "0%" if runs_needed > 0 else "100%",
            "runs_needed": runs_needed,
            "balls_remaining": 0,
            "required_run_rate": 0,
            "assessment": "Match over." if runs_needed > 0 else "Target achieved!"
        }

    rrr = (runs_needed / balls_remaining) * 6

    # Resource-based win probability
    wicket_resource = max(0, 1 - (wickets_lost * 0.12))
    over_resource = balls_remaining / 120

    # RRR difficulty factor
    if rrr <= 6:
        rrr_factor = 75
    elif rrr <= 8:
        rrr_factor = 60
    elif rrr <= 10:
        rrr_factor = 45
    elif rrr <= 12:
        rrr_factor = 30
    elif rrr <= 15:
        rrr_factor = 15
    else:
        rrr_factor = 5

    win_prob = min(95, max(5, int(
        (wicket_resource * 35) + (over_resource * 15) + (rrr_factor * 0.65)
    )))

    # Determine assessment
    if win_prob >= 70:
        assessment = "Commanding position. The chase is well on track."
    elif win_prob >= 55:
        assessment = "Slight edge to the batting team. A good over can seal it."
    elif win_prob >= 45:
        assessment = "Neck and neck. This is anybody's game."
    elif win_prob >= 30:
        assessment = "Bowling team has the edge. Batting team needs a big over."
    else:
        assessment = "Deep trouble. Need a miracle or a Dhoni-esque finish."

    return {
        "win_probability": f"{win_prob}%",
        "runs_needed": runs_needed,
        "balls_remaining": balls_remaining,
        "required_run_rate": round(rrr, 2),
        "current_run_rate": round(current_score / max(balls_bowled / 6, 0.1), 2),
        "wicket_resource_remaining": f"{wicket_resource * 100:.0f}%",
        "phase": "powerplay" if full_overs < 6 else "middle" if full_overs < 15 else "death",
        "assessment": assessment
    }
