"""
Utility functions for working with both Sleeper and Yahoo Fantasy Football APIs
"""

from typing import Dict, List, Optional, Any
from datetime import datetime


def format_player_name(player: Dict, platform: str = "sleeper") -> str:
    """
    Format player name consistently across platforms
    
    Args:
        player: Player dictionary from API response
        platform: 'sleeper' or 'yahoo'
    
    Returns:
        Formatted player name string
    """
    if platform == "sleeper":
        first_name = player.get("first_name", "")
        last_name = player.get("last_name", "")
        return f"{first_name} {last_name}".strip()
    elif platform == "yahoo":
        name = player.get("name", {})
        if isinstance(name, dict):
            full_name = name.get("full", "")
            return full_name
        return str(name)
    return "Unknown Player"


def get_player_position(player: Dict, platform: str = "sleeper") -> str:
    """
    Extract player position from player data
    
    Args:
        player: Player dictionary from API response
        platform: 'sleeper' or 'yahoo'
    
    Returns:
        Player position string
    """
    if platform == "sleeper":
        return player.get("position", "")
    elif platform == "yahoo":
        return player.get("display_position", "") or player.get("position", "")
    return ""


def calculate_team_points(roster: List[Dict], platform: str = "sleeper") -> float:
    """
    Calculate total points for a team roster
    
    Args:
        roster: List of player dictionaries
        platform: 'sleeper' or 'yahoo'
    
    Returns:
        Total points as float
    """
    total_points = 0.0
    
    if platform == "sleeper":
        for player in roster:
            # Sleeper stores points in different places depending on context
            points = player.get("points", 0) or player.get("stats", {}).get("pts", 0)
            if isinstance(points, (int, float)):
                total_points += float(points)
    elif platform == "yahoo":
        for player in roster:
            # Yahoo stores points in player stats
            player_stats = player.get("player_points", {})
            if isinstance(player_stats, dict):
                total = player_stats.get("total", 0)
                if isinstance(total, (int, float)):
                    total_points += float(total)
    
    return total_points


def compare_platforms_stats(sleeper_stats: Dict, yahoo_stats: Dict) -> Dict:
    """
    Compare player stats between Sleeper and Yahoo platforms
    
    Args:
        sleeper_stats: Stats dictionary from Sleeper
        yahoo_stats: Stats dictionary from Yahoo
    
    Returns:
        Dictionary with comparison data
    """
    comparison = {
        "platforms": ["sleeper", "yahoo"],
        "differences": {},
        "matches": {}
    }
    
    # Common stat categories to compare
    stat_categories = ["passing_yds", "passing_td", "rushing_yds", 
                      "rushing_td", "receiving_yds", "receiving_td"]
    
    for stat in stat_categories:
        sleeper_val = sleeper_stats.get(stat, 0)
        yahoo_val = yahoo_stats.get(stat, 0)
        
        if sleeper_val == yahoo_val:
            comparison["matches"][stat] = sleeper_val
        else:
            comparison["differences"][stat] = {
                "sleeper": sleeper_val,
                "yahoo": yahoo_val,
                "difference": abs(sleeper_val - yahoo_val)
            }
    
    return comparison


def get_current_season() -> int:
    """Get current NFL season year"""
    now = datetime.now()
    # NFL season typically starts in September
    if now.month >= 9:
        return now.year
    else:
        return now.year - 1


def get_current_week(season: int = None) -> int:
    """
    Estimate current NFL week (simplified)
    Note: This is a basic estimation. Use API endpoints for accurate week data.
    
    Args:
        season: Season year (defaults to current season)
    
    Returns:
        Estimated week number (1-18)
    """
    if season is None:
        season = get_current_season()
    
    now = datetime.now()
    season_start = datetime(season, 9, 1)  # Approximate season start
    
    if now < season_start:
        return 1
    
    weeks_passed = (now - season_start).days // 7
    current_week = min(weeks_passed + 1, 18)  # Max 18 weeks
    
    return current_week



