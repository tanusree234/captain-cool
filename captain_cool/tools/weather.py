"""
Weather tool — fetches real-time weather data from Open-Meteo API (free, no key needed).
Used by the Conditions Agent.
"""
import requests


# IPL venue coordinates
VENUE_COORDS = {
    "wankhede": {"lat": 18.9389, "lon": 72.8258, "city": "Mumbai"},
    "chepauk": {"lat": 13.0627, "lon": 80.2792, "city": "Chennai"},
    "chinnaswamy": {"lat": 12.9788, "lon": 77.5996, "city": "Bengaluru"},
    "eden gardens": {"lat": 22.5646, "lon": 88.3433, "city": "Kolkata"},
    "narendra modi": {"lat": 23.0914, "lon": 72.5952, "city": "Ahmedabad"},
    "motera": {"lat": 23.0914, "lon": 72.5952, "city": "Ahmedabad"},
    "arun jaitley": {"lat": 28.6373, "lon": 77.2433, "city": "Delhi"},
    "feroz shah kotla": {"lat": 28.6373, "lon": 77.2433, "city": "Delhi"},
    "rajiv gandhi": {"lat": 17.4065, "lon": 78.5506, "city": "Hyderabad"},
    "uppal": {"lat": 17.4065, "lon": 78.5506, "city": "Hyderabad"},
    "sawai mansingh": {"lat": 26.8929, "lon": 75.8052, "city": "Jaipur"},
    "is bindra": {"lat": 30.6886, "lon": 76.7378, "city": "Mohali"},
    "mohali": {"lat": 30.6886, "lon": 76.7378, "city": "Mohali"},
    "ekana": {"lat": 26.8512, "lon": 80.9476, "city": "Lucknow"},
    "dharamsala": {"lat": 32.2190, "lon": 76.3234, "city": "Dharamsala"},
    "brabourne": {"lat": 18.9322, "lon": 72.8327, "city": "Mumbai"},
    "dy patil": {"lat": 19.0455, "lon": 73.0290, "city": "Navi Mumbai"},
    "holkar": {"lat": 22.7236, "lon": 75.8628, "city": "Indore"},
    "greenfield": {"lat": 8.5322, "lon": 76.9119, "city": "Thiruvananthapuram"},
    "ma chidambaram": {"lat": 13.0627, "lon": 80.2792, "city": "Chennai"},
}


def get_weather(venue: str) -> dict:
    """
    Fetches current real-time weather conditions for an IPL venue using
    the free Open-Meteo API. Returns temperature, humidity, wind speed,
    and dew probability assessment.

    Args:
        venue: The stadium name or city (e.g., 'Wankhede', 'Chennai', 'Chinnaswamy').

    Returns:
        Dictionary with temperature, humidity, wind conditions, and dew
        probability for strategic decision-making.
    """
    venue_key = venue.lower().strip()

    # Try to match venue
    coords = None
    for key, val in VENUE_COORDS.items():
        if key in venue_key or venue_key in key or venue_key in val["city"].lower():
            coords = val
            break

    if not coords:
        return {
            "error": f"Unknown venue: {venue}",
            "fallback": "Using default conditions — moderate temperature, low humidity",
            "temperature_c": 28,
            "humidity_percent": 55,
            "wind_speed_kmh": 12,
            "dew_probability": "moderate",
            "city": "Unknown"
        }

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={coords['lat']}&longitude={coords['lon']}"
            f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,dew_point_2m"
            f"&timezone=Asia/Kolkata"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        current = data.get("current", {})

        temp = current.get("temperature_2m", 28)
        humidity = current.get("relative_humidity_2m", 55)
        wind = current.get("wind_speed_10m", 12)
        dew_point = current.get("dew_point_2m", 20)

        # Dew probability assessment based on temperature-dew point spread
        temp_dew_spread = temp - dew_point
        if temp_dew_spread <= 3:
            dew_prob = "very_high"
            dew_desc = "Heavy dew expected. Spinners will struggle to grip. Fast bowlers at the death will be lethal with pace and skid."
        elif temp_dew_spread <= 6:
            dew_prob = "high"
            dew_desc = "Significant dew likely in 2nd innings. Bowling second will be harder."
        elif temp_dew_spread <= 10:
            dew_prob = "moderate"
            dew_desc = "Some dew possible in late stages. Monitor conditions."
        else:
            dew_prob = "low"
            dew_desc = "Dry conditions. Spin should grip throughout."

        return {
            "city": coords["city"],
            "venue": venue,
            "temperature_c": temp,
            "humidity_percent": humidity,
            "wind_speed_kmh": wind,
            "dew_point_c": dew_point,
            "dew_probability": dew_prob,
            "dew_analysis": dew_desc,
            "wind_impact": "Strong crosswind — may assist swing" if wind > 20 else "Light wind — minimal impact" if wind < 10 else "Moderate wind — slight swing assistance",
            "heat_factor": "Extreme heat — fatigue risk for fast bowlers" if temp > 38 else "Hot — manage fast bowler spells" if temp > 33 else "Comfortable conditions"
        }

    except Exception as e:
        return {
            "error": f"Weather API call failed: {str(e)}",
            "fallback": "Using estimated conditions for venue",
            "city": coords["city"],
            "temperature_c": 30,
            "humidity_percent": 60,
            "wind_speed_kmh": 12,
            "dew_probability": "moderate",
            "dew_analysis": "Unable to fetch live data. Assuming moderate dew conditions typical for this venue."
        }
