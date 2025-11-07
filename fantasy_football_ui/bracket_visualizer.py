"""
Bracket visualization helper for displaying tournament brackets
"""

import streamlit as st
from typing import List, Dict, Optional

def get_playoff_seeds(rosters: List[Dict], user_lookup: Dict) -> Dict[int, int]:
    """
    Get playoff seeds for each roster (1-12 based on regular season finish)
    
    Args:
        rosters: List of roster dictionaries
        user_lookup: Dictionary mapping user_id to team name
    
    Returns:
        Dictionary mapping roster_id to seed (1-12)
    """
    # Calculate standings
    standings = []
    for roster in rosters:
        settings = roster.get('settings', {})
        wins = settings.get('wins', 0)
        points = settings.get('fpts', 0) + (settings.get('fpts_decimal', 0) / 100)
        standings.append({
            'roster_id': roster.get('roster_id'),
            'wins': wins,
            'points': points
        })
    
    # Sort by wins, then points (descending)
    standings.sort(key=lambda x: (x['wins'], x['points']), reverse=True)
    
    # Assign seeds (all teams get seeds 1-12)
    seed_map = {}
    for idx, team in enumerate(standings[:12], 1):
        seed_map[team['roster_id']] = idx
    
    return seed_map

def build_consolation_bracket(winners_bracket_by_round: Dict[int, List[Dict]], seed_map: Dict[int, int]) -> Dict[int, List[Dict]]:
    """
    Build consolation bracket from winners bracket by extracting losers
    
    Args:
        winners_bracket_by_round: Dictionary mapping round numbers to list of matchups from winners bracket
        seed_map: Dictionary mapping roster_id to seed
    
    Returns:
        Dictionary with consolation bracket matchups by round
    """
    consolation_bracket = {}
    round_losers = {}  # Track losers from each round
    
    sorted_rounds = sorted(winners_bracket_by_round.keys())
    
    for round_num in sorted_rounds:
        matchups = winners_bracket_by_round[round_num]
        consolation_matchups = []
        round_losers_list = []
        
        for matchup in matchups:
            team1_id = matchup.get('t1')
            team2_id = matchup.get('t2')
            winner_id = matchup.get('w')
            loser_id = matchup.get('l')
            
            # Track losers
            if loser_id:
                round_losers_list.append(loser_id)
            
            # For Round 1, losers go to consolation Round 1
            if round_num == 1 and loser_id:
                # Find the other team (the winner) to determine the matchup
                other_team_id = team1_id if loser_id == team2_id else team2_id
                consolation_matchups.append({
                    'team1_id': loser_id,
                    'team2_id': None,  # Will be paired with another loser
                    'team1_seed': seed_map.get(loser_id, 0),
                    'team2_seed': 0,
                    'winner_id': None,
                    'matchup_id': None
                })
        
        # For later rounds, pair up losers from previous round
        if round_num > 1:
            prev_losers = round_losers.get(round_num - 1, [])
            # Pair up losers from previous round
            for i in range(0, len(prev_losers), 2):
                if i + 1 < len(prev_losers):
                    team1_id = prev_losers[i]
                    team2_id = prev_losers[i + 1]
                    # Find the matchup in the winners bracket to get winner/loser
                    prev_matchups = winners_bracket_by_round.get(round_num - 1, [])
                    matchup_data = next((m for m in prev_matchups 
                                       if (m.get('t1') == team1_id and m.get('t2') == team2_id) or
                                          (m.get('t1') == team2_id and m.get('t2') == team1_id)), None)
                    
                    if matchup_data:
                        winner_id = matchup_data.get('w')
                        loser1 = team1_id if team1_id != winner_id else None
                        loser2 = team2_id if team2_id != winner_id else None
                        
                        if loser1 and loser2:
                            consolation_matchups.append({
                                'team1_id': loser1,
                                'team2_id': loser2,
                                'team1_seed': seed_map.get(loser1, 0),
                                'team2_seed': seed_map.get(loser2, 0),
                                'winner_id': None,  # Consolation matchups may not have winners yet
                                'matchup_id': None
                            })
        
        if consolation_matchups:
            consolation_bracket[round_num] = consolation_matchups
            round_losers[round_num] = round_losers_list
    
    return consolation_bracket

def build_tournament_bracket(matchups_by_round: Dict[int, List[Dict]], seed_map: Dict[int, int]) -> Dict[int, List[Dict]]:
    """
    Build proper tournament bracket structure with correct seeding and progression
    Only shows winners advancing to next rounds
    
    Args:
        matchups_by_round: Dictionary mapping round numbers to list of matchups
        seed_map: Dictionary mapping roster_id to seed
    
    Returns:
        Dictionary with properly structured bracket by round
    """
    if not matchups_by_round:
        return {}
    
    # Track winners from each round
    round_winners = {}  # {round: {matchup_id: winner_roster_id}}
    
    # Build bracket structure
    structured_bracket = {}
    
    # Process rounds in order
    sorted_rounds = sorted(matchups_by_round.keys())
    
    for round_num in sorted_rounds:
        matchups = matchups_by_round[round_num]
        structured_matchups = []
        
        if round_num == 1:
            # Round 1: Show all matchups with seeds, ordered by bracket structure
            # Expected matchups in order: 1v8, 4v5, 2v7, 3v6
            # Top bracket: 1v8 and 4v5 (winner plays winner)
            # Bottom bracket: 2v7 and 3v6 (winner plays winner)
            expected_pairs = [(1, 8), (4, 5), (2, 7), (3, 6)]
            
            for seed_pair in expected_pairs:
                seed1, seed2 = seed_pair
                # Find matchup with these seeds
                matchup = next((m for m in matchups 
                               if (seed_map.get(m.get('t1')) == seed1 and seed_map.get(m.get('t2')) == seed2) or
                                  (seed_map.get(m.get('t1')) == seed2 and seed_map.get(m.get('t2')) == seed1)), None)
                
                if matchup:
                    team1_id = matchup.get('t1')
                    team2_id = matchup.get('t2')
                    winner_id = matchup.get('w')
                    
                    # Ensure team1 is the lower seed
                    if seed_map.get(team1_id) == seed1:
                        structured_matchups.append({
                            'team1_id': team1_id,
                            'team2_id': team2_id,
                            'team1_seed': seed1,
                            'team2_seed': seed2,
                            'winner_id': winner_id,
                            'matchup_id': matchup.get('m')
                        })
                    else:
                        structured_matchups.append({
                            'team1_id': team2_id,
                            'team2_id': team1_id,
                            'team1_seed': seed1,
                            'team2_seed': seed2,
                            'winner_id': winner_id,
                            'matchup_id': matchup.get('m')
                        })
                    
                    if winner_id:
                        round_winners[round_num] = round_winners.get(round_num, {})
                        round_winners[round_num][matchup.get('m')] = winner_id
        else:
            # Later rounds: Only show winners from previous rounds
            # Round 2 (Semifinals): Should have 2 games (only winners from Round 1)
            # Round 3 (Championship): Should have 1 game (only winners from Round 2)
            prev_winners = list(round_winners.get(round_num - 1, {}).values())
            
            for matchup in matchups:
                team1_id = matchup.get('t1')
                team2_id = matchup.get('t2')
                winner_id = matchup.get('w')
                
                # Only include matchups where both teams are winners from the previous round
                # This ensures losers don't appear in later rounds
                if team1_id in prev_winners and team2_id in prev_winners:
                    structured_matchups.append({
                        'team1_id': team1_id,
                        'team2_id': team2_id,
                        'team1_seed': seed_map.get(team1_id, 0),
                        'team2_seed': seed_map.get(team2_id, 0),
                        'winner_id': winner_id,
                        'matchup_id': matchup.get('m')
                    })
                    
                    if winner_id:
                        round_winners[round_num] = round_winners.get(round_num, {})
                        round_winners[round_num][matchup.get('m')] = winner_id
        
        structured_bracket[round_num] = structured_matchups
    
    return structured_bracket

def create_bracket_html(matchups_by_round: Dict[int, List[Dict]], rosters: List[Dict], user_lookup: Dict, seed_map: Dict[int, int] = None, is_consolation: bool = False, custom_round_names: Dict[int, str] = None) -> str:
    """
    Create HTML for a tournament bracket visualization with traditional bracket style
    
    Args:
        matchups_by_round: Dictionary mapping round numbers to list of matchups
        rosters: List of roster dictionaries
        user_lookup: Dictionary mapping user_id to team name
        seed_map: Dictionary mapping roster_id to seed (optional, will calculate if not provided)
    
    Returns:
        HTML string for the bracket
    """
    if not matchups_by_round:
        return ""
    
    # Get or calculate seed map
    if seed_map is None:
        seed_map = get_playoff_seeds(rosters, user_lookup)
    
    # Build proper tournament bracket structure
    structured_bracket = build_tournament_bracket(matchups_by_round, seed_map)
    
    # Get team name from roster ID
    def get_team_name(roster_id):
        if not roster_id:
            return "TBD"
        roster = next((r for r in rosters if r.get('roster_id') == roster_id), None)
        if roster:
            owner_id = roster.get('owner_id')
            return user_lookup.get(owner_id, f'Team {roster_id}')
        return f'Team {roster_id}'
    
    # Sort rounds (lowest to highest for tournament progression)
    sorted_rounds = sorted(structured_bracket.keys())
    
    # Build bracket HTML
    html_parts = ['<div class="tournament-bracket">']
    
    # Round name mapping
    if custom_round_names:
        round_names = custom_round_names
    elif is_consolation:
        # For consolation brackets, we'll use generic names
        # The calling code can override with specific place names
        round_names = {
            1: "Round 1",
            2: "Round 2",
            3: "Round 3"
        }
    else:
        round_names = {
            1: "Round 1",
            2: "Semifinals",
            3: "Championship"
        }
    
    # Create a horizontal bracket layout
    for round_num in sorted_rounds:
        matchups = structured_bracket[round_num]
        if not matchups:  # Skip empty rounds
            continue
            
        html_parts.append(f'<div class="bracket-round round-{round_num}">')
        round_name = round_names.get(round_num, f"Round {round_num}")
        html_parts.append(f'<div class="round-header">{round_name}</div>')
        html_parts.append('<div class="round-matchups">')
        
        for matchup in matchups:
            team1_id = matchup.get('team1_id')
            team2_id = matchup.get('team2_id')
            winner_id = matchup.get('winner_id')
            seed1 = matchup.get('team1_seed', 0)
            seed2 = matchup.get('team2_seed', 0)
            
            team1_name = get_team_name(team1_id)
            team2_name = get_team_name(team2_id)
            
            # Determine winner
            is_team1_winner = winner_id == team1_id
            is_team2_winner = winner_id == team2_id
            
            html_parts.append('<div class="matchup-box">')
            # Show seed if available
            seed1_display = f"#{seed1} " if seed1 > 0 else ""
            seed2_display = f"#{seed2} " if seed2 > 0 else ""
            html_parts.append(f'<div class="team-slot {"winner" if is_team1_winner else ""}">{seed1_display}{team1_name}</div>')
            html_parts.append(f'<div class="team-slot {"winner" if is_team2_winner else ""}">{seed2_display}{team2_name}</div>')
            html_parts.append('</div>')
        
        html_parts.append('</div>')
        html_parts.append('</div>')
    
    html_parts.append('</div>')
    
    # Add CSS styling for tournament bracket
    css = """
    <style>
    .tournament-bracket {
        display: flex;
        flex-direction: row;
        gap: 30px;
        padding: 20px;
        overflow-x: auto;
        font-family: Arial, sans-serif;
        background: linear-gradient(to right, #f8f9fa, #e9ecef);
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .bracket-round {
        min-width: 220px;
        background: white;
        border-radius: 8px;
        padding: 15px;
        border: 2px solid #dee2e6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .round-header {
        text-align: center;
        font-size: 16px;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 2px solid #1f77b4;
    }
    .round-matchups {
        display: flex;
        flex-direction: column;
        gap: 20px;
    }
    .matchup-box {
        background: #f8f9fa;
        border: 2px solid #ced4da;
        border-radius: 6px;
        padding: 0;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .team-slot {
        padding: 12px 15px;
        background: white;
        border-bottom: 1px solid #dee2e6;
        font-weight: 500;
        font-size: 14px;
        min-height: 40px;
        display: flex;
        align-items: center;
        transition: all 0.2s;
    }
    .team-slot:last-child {
        border-bottom: none;
    }
    .team-slot.winner {
        background: linear-gradient(to right, #d4edda, #c3e6cb);
        border-left: 4px solid #28a745;
        font-weight: bold;
        color: #155724;
        box-shadow: inset 0 0 10px rgba(40, 167, 69, 0.1);
    }
    .team-slot:not(.winner) {
        color: #6c757d;
    }
    @media (max-width: 768px) {
        .tournament-bracket {
            flex-direction: column;
        }
        .bracket-round {
            width: 100%;
        }
    }
    </style>
    """
    
    return css + ''.join(html_parts)

def display_bracket(matchups_by_round: Dict[int, List[Dict]], rosters: List[Dict], user_lookup: Dict, title: str = "Bracket", is_consolation: bool = False, custom_round_names: Dict[int, str] = None):
    """
    Display a tournament bracket in Streamlit
    
    Args:
        matchups_by_round: Dictionary mapping round numbers to list of matchups
        rosters: List of roster dictionaries
        user_lookup: Dictionary mapping user_id to team name
        title: Title for the bracket
        is_consolation: Whether this is a consolation bracket (affects round naming)
        custom_round_names: Optional dictionary mapping round numbers to custom names
    """
    if not matchups_by_round:
        st.info(f"{title} bracket not available yet.")
        return
    
    # Get seed map
    seed_map = get_playoff_seeds(rosters, user_lookup)
    
    html = create_bracket_html(matchups_by_round, rosters, user_lookup, seed_map, is_consolation, custom_round_names)
    st.markdown(html, unsafe_allow_html=True)

