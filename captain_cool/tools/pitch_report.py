"""
Pitch report tool — provides venue-specific pitch behavior data.
Used by the Conditions Agent.
"""

VENUE_PITCH_DATA = {
    "wankhede": {
        "venue_name": "Wankhede Stadium, Mumbai",
        "pitch_type": "batting_friendly", "pace": "good_pace_and_bounce",
        "spin_friendliness": "low", "avg_first_innings_score": 177,
        "avg_second_innings_score": 163, "highest_chase": 209,
        "dew_factor": "heavy", "boundary_size": "short_straight_long_square",
        "characteristics": "True bounce, good carry. Heavy dew in night matches makes chasing easier.",
        "strategy_tips": "Bowl first if dew expected. Pace in powerplay. Spinners struggle in 2nd innings."
    },
    "chepauk": {
        "venue_name": "MA Chidambaram Stadium, Chennai",
        "pitch_type": "spin_friendly", "pace": "slow_and_low",
        "spin_friendliness": "very_high", "avg_first_innings_score": 162,
        "avg_second_innings_score": 148, "highest_chase": 208,
        "dew_factor": "moderate", "boundary_size": "medium_all_around",
        "characteristics": "Red soil turns from ball one. Low bounce. Spinners dominate as pitch breaks up.",
        "strategy_tips": "Bat first. Load spinners. Left-arm spin lethal. Pacers should use cutters."
    },
    "chinnaswamy": {
        "venue_name": "M Chinnaswamy Stadium, Bengaluru",
        "pitch_type": "batting_paradise", "pace": "true_bounce_good_pace",
        "spin_friendliness": "very_low", "avg_first_innings_score": 186,
        "avg_second_innings_score": 172, "highest_chase": 226,
        "dew_factor": "moderate", "boundary_size": "short_all_around",
        "characteristics": "Flattest IPL track. Short boundaries. Even 200 chaseable. Altitude helps carry.",
        "strategy_tips": "Wickets matter more than runs. Death bowling crucial. Spinners are cannon fodder."
    },
    "eden gardens": {
        "venue_name": "Eden Gardens, Kolkata",
        "pitch_type": "balanced", "pace": "good_pace",
        "spin_friendliness": "moderate", "avg_first_innings_score": 170,
        "avg_second_innings_score": 158, "highest_chase": 190,
        "dew_factor": "heavy", "boundary_size": "large_square",
        "characteristics": "Balanced pitch. Large square boundaries. Heavy dew in evenings.",
        "strategy_tips": "Chase-friendly with dew. Spinners good in 1st innings. Target straight boundaries."
    },
    "narendra modi": {
        "venue_name": "Narendra Modi Stadium, Ahmedabad",
        "pitch_type": "balanced_to_spin", "pace": "slow_medium",
        "spin_friendliness": "high", "avg_first_innings_score": 168,
        "avg_second_innings_score": 155, "highest_chase": 198,
        "dew_factor": "low", "boundary_size": "very_large",
        "characteristics": "Huge ground. Pitch slows down. Spinners find purchase. Singles crucial.",
        "strategy_tips": "Premium on rotation. Sixes harder. Quality spinners are gold."
    },
    "arun jaitley": {
        "venue_name": "Arun Jaitley Stadium, Delhi",
        "pitch_type": "balanced", "pace": "slow_turning",
        "spin_friendliness": "moderate_to_high", "avg_first_innings_score": 168,
        "avg_second_innings_score": 155, "highest_chase": 196,
        "dew_factor": "moderate", "boundary_size": "short_straight",
        "characteristics": "Two-paced. New ball does a bit, slows in middle. Short straight boundaries.",
        "strategy_tips": "Pace with new ball, transition to spin. Target straight boundaries."
    },
    "rajiv gandhi": {
        "venue_name": "Rajiv Gandhi Intl Stadium, Hyderabad",
        "pitch_type": "batting_friendly", "pace": "good_pace_and_bounce",
        "spin_friendliness": "low", "avg_first_innings_score": 175,
        "avg_second_innings_score": 165, "highest_chase": 206,
        "dew_factor": "heavy", "boundary_size": "medium",
        "characteristics": "Good batting surface. Heavy dew makes 2nd innings bowling nightmare.",
        "strategy_tips": "Bowl first. Dew makes chasing easier. Manage death bowlers wisely."
    },
    "sawai mansingh": {
        "venue_name": "Sawai Mansingh Stadium, Jaipur",
        "pitch_type": "spin_friendly", "pace": "slow",
        "spin_friendliness": "high", "avg_first_innings_score": 164,
        "avg_second_innings_score": 152, "highest_chase": 195,
        "dew_factor": "low", "boundary_size": "medium",
        "characteristics": "Dry, dusty. Grips and turns. Timing difficult on slow surface.",
        "strategy_tips": "Bat first. Spin-heavy attack. Use cutters and slower balls."
    },
    "ekana": {
        "venue_name": "Ekana Stadium, Lucknow",
        "pitch_type": "balanced", "pace": "medium",
        "spin_friendliness": "moderate", "avg_first_innings_score": 172,
        "avg_second_innings_score": 160, "highest_chase": 200,
        "dew_factor": "moderate", "boundary_size": "large",
        "characteristics": "Good batting surface. Some help for seamers with new ball.",
        "strategy_tips": "Use new ball well. Middle/death favor batting. Large boundaries need timing."
    },
    "dharamsala": {
        "venue_name": "HPCA Stadium, Dharamsala",
        "pitch_type": "pace_friendly", "pace": "extra_bounce_and_swing",
        "spin_friendliness": "low", "avg_first_innings_score": 174,
        "avg_second_innings_score": 160, "highest_chase": 193,
        "dew_factor": "heavy", "boundary_size": "asymmetric",
        "characteristics": "Mountain venue. Thin air = ball carries. Swing in evening. Short one side.",
        "strategy_tips": "Pace is king. Exploit short boundary side. Altitude helps ball travel."
    }
}

VENUE_ALIASES = {
    "mumbai": "wankhede", "chennai": "chepauk", "ma chidambaram": "chepauk",
    "bengaluru": "chinnaswamy", "bangalore": "chinnaswamy", "kolkata": "eden gardens",
    "ahmedabad": "narendra modi", "motera": "narendra modi", "delhi": "arun jaitley",
    "feroz shah kotla": "arun jaitley", "hyderabad": "rajiv gandhi", "uppal": "rajiv gandhi",
    "jaipur": "sawai mansingh", "lucknow": "ekana", "mohali": "is bindra",
}


def get_pitch_report(venue: str) -> dict:
    """
    Returns detailed pitch report and venue characteristics for an IPL ground.

    Args:
        venue: The stadium name or city (e.g., 'Wankhede', 'Chennai', 'Chinnaswamy').

    Returns:
        Dictionary with pitch type, average scores, and strategic tips.
    """
    v = venue.lower().strip()
    if v in VENUE_ALIASES:
        v = VENUE_ALIASES[v]
    if v in VENUE_PITCH_DATA:
        return VENUE_PITCH_DATA[v]
    for key, data in VENUE_PITCH_DATA.items():
        if key in v or v in key:
            return data
    return {
        "venue_name": f"{venue} (generic)", "pitch_type": "balanced",
        "pace": "medium", "spin_friendliness": "moderate",
        "avg_first_innings_score": 170, "avg_second_innings_score": 158,
        "highest_chase": 195, "dew_factor": "moderate", "boundary_size": "medium",
        "characteristics": "Standard IPL conditions assumed.",
        "strategy_tips": "Play the situation. Monitor pitch in first 5 overs."
    }
