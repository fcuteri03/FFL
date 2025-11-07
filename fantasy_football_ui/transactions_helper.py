"""
Helper functions for processing and displaying transactions
"""

import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter

from fantasy_football_ui.team_name_utils import normalize_team_name

def parse_sleeper_transactions(transactions: List[Dict], users: List[Dict], rosters: List[Dict] = None, players: Dict = None, matchup_data: Dict = None, season: int = None) -> Dict:
    """
    Parse Sleeper transactions into structured format
    
    Args:
        transactions: List of transaction dictionaries from Sleeper API
        users: List of user dictionaries for team name lookup
        rosters: Optional list of roster dictionaries to map roster_id to user_id
        players: Optional player dictionary for player name lookup (keyed by player_id)
        matchup_data: Optional matchup data by week: {week: {roster_id: {players_points: {}, starters: []}}}
        season: Optional season year for calculating post-pickup stats
    
    Returns:
        Dictionary with parsed transactions by type
    """
    user_lookup = {user['user_id']: normalize_team_name(user.get('display_name') or user.get('username', 'Unknown')) for user in users}
    
    # Create roster_id to user_id mapping
    roster_to_user = {}
    # Also create user_id to roster_id mapping (for finding which roster a team owns)
    user_to_roster = {}
    if rosters:
        for roster in rosters:
            roster_id = roster.get('roster_id')
            owner_id = roster.get('owner_id')
            if roster_id and owner_id:
                roster_to_user[roster_id] = owner_id
                user_to_roster[owner_id] = roster_id
    
    trades = []
    waivers = []
    add_drops = []
    
    for trans in transactions:
        if not trans:
            continue
            
        trans_type = trans.get('type', '')
        status = trans.get('status', '')
        
        # Skip failed/cancelled transactions (but include complete ones)
        if status not in ['complete', 'approved', 'processed']:
            continue
        
        if trans_type == 'trade':
            # Parse trade
            adds = trans.get('adds', {}) or {}
            drops = trans.get('drops', {}) or {}
            draft_picks = trans.get('draft_picks', []) or []
            
            # Get roster IDs involved
            roster_ids = set()
            for player_id, roster_id in adds.items():
                roster_ids.add(roster_id)
            for player_id, roster_id in drops.items():
                roster_ids.add(roster_id)
            
            if len(roster_ids) < 2:
                continue
            
            # Get team names from roster IDs
            team_names = []
            for roster_id in list(roster_ids)[:2]:  # Usually 2 teams in a trade
                user_id = roster_to_user.get(roster_id)
                if user_id:
                    team_name = user_lookup.get(user_id, f"Team {roster_id}")
                else:
                    team_name = f"Team {roster_id}"
                team_names.append(team_name)
            
            # Format players in trade
            adds_formatted = {}
            drops_formatted = {}
            
            for player_id, roster_id in adds.items():
                user_id = roster_to_user.get(roster_id)
                team_name = user_lookup.get(user_id, f"Team {roster_id}") if user_id else f"Team {roster_id}"
                player_name = players.get(str(player_id), {}).get('full_name', f"Player {player_id}") if players else f"Player {player_id}"
                adds_formatted[player_name] = team_name
            
            for player_id, roster_id in drops.items():
                user_id = roster_to_user.get(roster_id)
                team_name = user_lookup.get(user_id, f"Team {roster_id}") if user_id else f"Team {roster_id}"
                player_name = players.get(str(player_id), {}).get('full_name', f"Player {player_id}") if players else f"Player {player_id}"
                drops_formatted[player_name] = team_name
            
            trade_data = {
                'transaction_id': trans.get('transaction_id', ''),
                'status': status,
                'consenter_ids': trans.get('consenter_ids', []),
                'created': trans.get('created', 0),
                'date': datetime.fromtimestamp(trans.get('created', 0) / 1000).strftime('%Y-%m-%d') if trans.get('created') else 'Unknown',
                'adds': adds_formatted,
                'drops': drops_formatted,
                'draft_picks': draft_picks,
                'teams': team_names
            }
            trades.append(trade_data)
        
        elif trans_type in ['waiver', 'free_agent', 'commissioner']:
            # Parse waiver/add
            adds = trans.get('adds', {}) or {}
            drops = trans.get('drops', {}) or {}
            
            # Get waiver bid from settings
            settings = trans.get('settings', {}) or {}
            waiver_bid = settings.get('waiver_bid', 0) or 0
            
            for entity_id, roster_id in adds.items():
                user_id = roster_to_user.get(roster_id)
                team_name = user_lookup.get(user_id, f"Team {roster_id}") if user_id else f"Team {roster_id}"
                
                # Determine if entity_id is a player ID (numeric) or team abbreviation (3-letter)
                # Team abbreviations are like "IND", "CHI", "HOU", etc.
                # Player IDs are numeric strings like "4039", "6130"
                is_team = len(entity_id) == 3 and entity_id.isalpha() and entity_id.isupper()
                
                if is_team:
                    # It's a team defense (DST)
                    player_name = f"{entity_id} DST"
                else:
                    # It's a player ID
                    player_name = f"Player {entity_id}"
                    if players:
                        player_data = players.get(str(entity_id)) or players.get(entity_id)
                        if player_data:
                            full_name = player_data.get('full_name', '')
                            if not full_name:
                                first = player_data.get('first_name', '')
                                last = player_data.get('last_name', '')
                                full_name = f"{first} {last}".strip()
                            if full_name:
                                player_name = full_name
                
                # Get dropped player/team name
                dropped_entity_name = None
                if drops:
                    dropped_entity_id = list(drops.keys())[0]
                    is_dropped_team = len(dropped_entity_id) == 3 and dropped_entity_id.isalpha() and dropped_entity_id.isupper()
                    
                    if is_dropped_team:
                        dropped_entity_name = f"{dropped_entity_id} DST"
                    else:
                        dropped_entity_name = f"Player {dropped_entity_id}"
                        if players:
                            dropped_player_data = players.get(str(dropped_entity_id)) or players.get(dropped_entity_id)
                            if dropped_player_data:
                                full_name = dropped_player_data.get('full_name', '')
                                if not full_name:
                                    first = dropped_player_data.get('first_name', '')
                                    last = dropped_player_data.get('last_name', '')
                                    full_name = f"{first} {last}".strip()
                                if full_name:
                                    dropped_entity_name = full_name
                
                # Extract week if available (estimate from date)
                week = 'N/A'
                if trans.get('created'):
                    try:
                        # NFL season typically starts first week of September
                        # Week 1 is usually around Sept 4-10
                        date_obj = datetime.fromtimestamp(trans.get('created', 0) / 1000)
                        # Rough estimate: week 1 starts around Sept 4
                        season_start = datetime(date_obj.year, 9, 4)
                        days_diff = (date_obj - season_start).days
                        if days_diff >= 0:
                            estimated_week = min((days_diff // 7) + 1, 18)
                            week = estimated_week
                    except:
                        pass
                
                # Calculate total points after pickup and games started
                total_points_after_pickup = 'N/A'
                games_started = 'N/A'
                
                if matchup_data and week != 'N/A' and isinstance(week, int) and season:
                    try:
                        # roster_id from transaction is the roster that made the pickup
                        team_roster_id = roster_id
                        
                        if team_roster_id:
                            player_id_str = str(entity_id)
                            total_points = 0.0
                            games_in_lineup = 0
                            
                            # Look through all weeks after pickup week
                            for week_num in range(week + 1, 19):  # Start from week after pickup
                                if week_num in matchup_data:
                                    week_matchups = matchup_data[week_num]
                                    if team_roster_id in week_matchups:
                                        team_matchup = week_matchups[team_roster_id]
                                        starters = team_matchup.get('starters', [])
                                        players_points = team_matchup.get('players_points', {})
                                        
                                        # Check if player was in starting lineup
                                        if player_id_str in starters:
                                            games_in_lineup += 1
                                        
                                        # Get player points for this week (if they scored)
                                        if player_id_str in players_points:
                                            points = players_points[player_id_str]
                                            if points and points > 0:
                                                total_points += float(points)
                            
                            if total_points > 0 or games_in_lineup > 0:
                                total_points_after_pickup = round(total_points, 2) if total_points > 0 else 0
                                games_started = games_in_lineup
                    except Exception as e:
                        # Silently fail - stats might not be available
                        pass
                
                waiver_data = {
                    'transaction_id': trans.get('transaction_id', ''),
                    'type': trans_type,
                    'status': status,
                    'created': trans.get('created', 0),
                    'date': datetime.fromtimestamp(trans.get('created', 0) / 1000).strftime('%Y-%m-%d') if trans.get('created') else 'Unknown',
                    'team': team_name,
                    'player_id': entity_id,
                    'player_name': player_name,
                    'faab_bid': waiver_bid,
                    'dropped_player_id': list(drops.keys())[0] if drops else None,
                    'dropped_player_name': dropped_entity_name,
                    'week': week,
                    'total_points_after_pickup': total_points_after_pickup,
                    'games_started': games_started,
                    'year': season
                }
                
                if trans_type == 'waiver' and waiver_bid > 0:
                    waivers.append(waiver_data)
                else:
                    add_drops.append(waiver_data)
    
    return {
        'trades': trades,
        'waivers': waivers,
        'add_drops': add_drops
    }

def parse_yahoo_transactions(transactions: List[Dict], teams: List[Dict] = None) -> Dict:
    """
    Parse Yahoo transactions into structured format
    
    Args:
        transactions: List of transaction dictionaries from Yahoo API
        teams: Optional list of team dictionaries for team name lookup
    
    Returns:
        Dictionary with parsed transactions by type
    """
    team_lookup = {}
    if teams:
        for team in teams:
            team_lookup[team.get('team_key', '')] = team.get('name', 'Unknown')
    
    trades = []
    waivers = []
    add_drops = []
    
    for trans in transactions:
        trans_type = trans.get('type', '')
        status = trans.get('status', '')
        
        if status != 'successful':
            continue
        
        if trans_type == 'trade':
            # Parse trade
            trade_data = {
                'transaction_id': trans.get('transaction_key', ''),
                'status': status,
                'timestamp': trans.get('timestamp', ''),
                'date': datetime.fromtimestamp(int(trans.get('timestamp', 0))).strftime('%Y-%m-%d') if trans.get('timestamp') else 'Unknown',
                'players': trans.get('players', []),
                'teams': []
            }
            trades.append(trade_data)
        
        elif trans_type in ['add', 'drop', 'add/drop']:
            # Parse waiver/add
            faab_bid = trans.get('faab_bid', 0) or 0
            team_key = trans.get('team_key', '')
            team_name = team_lookup.get(team_key, 'Unknown')
            
            waiver_data = {
                'transaction_id': trans.get('transaction_key', ''),
                'type': trans_type,
                'status': status,
                'timestamp': trans.get('timestamp', ''),
                'date': datetime.fromtimestamp(int(trans.get('timestamp', 0))).strftime('%Y-%m-%d') if trans.get('timestamp') else 'Unknown',
                'team': team_name,
                'player_id': trans.get('player_id', ''),
                'player_name': trans.get('player_name', 'Unknown'),
                'faab_bid': faab_bid
            }
            
            if faab_bid > 0:
                waivers.append(waiver_data)
            else:
                add_drops.append(waiver_data)
    
    return {
        'trades': trades,
        'waivers': waivers,
        'add_drops': add_drops
    }

def get_top_faab_pickups(waivers: List[Dict], limit: int = 10) -> pd.DataFrame:
    """Get top FAAB pickups sorted by bid amount"""
    if not waivers:
        return pd.DataFrame()
    
    # Sort by FAAB bid descending
    sorted_waivers = sorted(waivers, key=lambda x: x.get('faab_bid', 0), reverse=True)
    
    data = []
    for w in sorted_waivers[:limit]:
        data.append({
            'Date': w.get('date', 'Unknown'),
            'Team': w.get('team', 'Unknown'),
            'Player': w.get('player_name', 'Unknown'),
            'FAAB Bid': w.get('faab_bid', 0),
            'Dropped': w.get('dropped_player_name', 'N/A')
        })
    
    return pd.DataFrame(data)

def get_most_added_dropped(add_drops: List[Dict]) -> Dict:
    """Get most added and dropped players"""
    added_counter = Counter()
    dropped_counter = Counter()
    
    for trans in add_drops:
        player_name = trans.get('player_name', 'Unknown')
        # All transactions in add_drops are adds (drops are in dropped_player_name)
        added_counter[player_name] += 1
        
        # Check if there's a dropped player
        dropped_player = trans.get('dropped_player_name')
        if dropped_player and dropped_player != 'N/A':
            dropped_counter[dropped_player] += 1
    
    # Get most added
    most_added = pd.DataFrame([
        {'Player': player, 'Times Added': count}
        for player, count in added_counter.most_common(15)
    ])
    
    # Get most dropped
    most_dropped = pd.DataFrame([
        {'Player': player, 'Times Dropped': count}
        for player, count in dropped_counter.most_common(15)
    ])
    
    return {
        'most_added': most_added,
        'most_dropped': most_dropped
    }

