"""
Functions for combining transactions across multiple seasons
"""

import pandas as pd
from typing import Dict, List
from collections import Counter
from datetime import datetime

def combine_transactions_across_years(all_transactions: Dict[int, Dict]) -> Dict:
    """
    Combine transactions from multiple years into unified views
    
    Args:
        all_transactions: Dictionary mapping year to parsed transactions dict
    
    Returns:
        Combined transactions dictionary
    """
    all_trades = []
    all_waivers = []
    all_add_drops = []
    
    for year, parsed in all_transactions.items():
        # Add year to each transaction
        for trade in parsed.get('trades', []):
            trade['year'] = year
            all_trades.append(trade)
        
        for waiver in parsed.get('waivers', []):
            waiver['year'] = year
            all_waivers.append(waiver)
        
        for add_drop in parsed.get('add_drops', []):
            add_drop['year'] = year
            all_add_drops.append(add_drop)
    
    return {
        'trades': all_trades,
        'waivers': all_waivers,
        'add_drops': all_add_drops
    }

def get_top_faab_pickups_all_years(waivers: List[Dict], limit: int = 15) -> pd.DataFrame:
    """Get top FAAB pickups across all years"""
    if not waivers:
        return pd.DataFrame()
    
    # Sort by FAAB bid descending
    sorted_waivers = sorted(waivers, key=lambda x: x.get('faab_bid', 0), reverse=True)
    
    data = []
    for w in sorted_waivers[:limit]:
        data.append({
            'Player': w.get('player_name', 'Unknown'),
            'FAAB': w.get('faab_bid', 0),
            'Team': w.get('team', 'Unknown'),
            'Year': w.get('year', 'Unknown'),
            'Week': w.get('week', 'N/A'),
            'Total Points After Pickup': w.get('total_points_after_pickup', 'N/A'),
            'Games Started': w.get('games_started', 'N/A')
        })
    
    return pd.DataFrame(data)

def get_team_transaction_stats(trades: List[Dict], waivers: List[Dict], add_drops: List[Dict]) -> pd.DataFrame:
    """
    Get transaction statistics by team
    
    Returns:
        DataFrame with team stats: total moves, FA pickups, trades
    """
    team_stats = {}
    
    # Count trades
    for trade in trades:
        teams = trade.get('teams', [])
        for team in teams:
            if team not in team_stats:
                team_stats[team] = {'trades': 0, 'fa_pickups': 0, 'total_moves': 0}
            team_stats[team]['trades'] += 1
            team_stats[team]['total_moves'] += 1
    
    # Count FA pickups (free_agent type)
    for add_drop in add_drops:
        if add_drop.get('type') == 'free_agent':
            team = add_drop.get('team', 'Unknown')
            if team not in team_stats:
                team_stats[team] = {'trades': 0, 'fa_pickups': 0, 'total_moves': 0}
            team_stats[team]['fa_pickups'] += 1
            team_stats[team]['total_moves'] += 1
    
    # Count waivers
    for waiver in waivers:
        team = waiver.get('team', 'Unknown')
        if team not in team_stats:
            team_stats[team] = {'trades': 0, 'fa_pickups': 0, 'total_moves': 0}
        team_stats[team]['total_moves'] += 1
    
    # Convert to DataFrame
    data = []
    for team, stats in team_stats.items():
        data.append({
            'Team': team,
            'Total Moves': stats['total_moves'],
            'FA Pickups': stats['fa_pickups'],
            'Trades': stats['trades']
        })
    
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values('Total Moves', ascending=False)
    return df

