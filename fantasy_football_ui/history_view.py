"""
History view helper functions for displaying league history
"""

import pandas as pd
from datetime import datetime
import streamlit as st

from fantasy_football_ui.team_name_utils import normalize_team_name

def display_history_view():
    """Display league history view with season filter and game type selection"""
    st.header("📅 League History")
    
    # Get available seasons
    current_year = datetime.now().year
    available_seasons = list(range(current_year, current_year - 10, -1))
    
    # Season selector
    selected_season = st.selectbox(
        "Select Season",
        options=available_seasons,
        index=0,
        help="Select a season to view history"
    )
    
    if not selected_season:
        st.info("Please select a season to view history.")
        return
    
    # Get league ID for selected season
    # Import SLEEPER_LEAGUE_IDS from app
    import sys
    import os
    from pathlib import Path
    app_dir = Path(__file__).resolve().parent
    parent_dir = app_dir.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    # Get league ID from the dictionary
    SLEEPER_LEAGUE_IDS = {
        2021: "740630336907657216",
        2022: "862956648505921536",
        2023: "1004526732419911680",
        2024: "1124842071690067968",
        2025: "1257479697114075136"
    }
    league_id = SLEEPER_LEAGUE_IDS.get(selected_season)
    if not league_id:
        st.error(f"No league ID found for {selected_season}")
        return
    
    # Fetch league data
    try:
        league = st.session_state.sleeper_client.get_league(league_id)
        users = st.session_state.sleeper_client.get_league_users(league_id)
        rosters = st.session_state.sleeper_client.get_league_rosters(league_id)
        
        # Create user lookup
        user_lookup = {user.get('user_id'): normalize_team_name(user.get('display_name') or user.get('username', 'Unknown')) for user in users}
        
        # Get champions and winners
        try:
            winners_bracket = st.session_state.sleeper_client.get_league_playoff_bracket(league_id)
            losers_bracket = st.session_state.sleeper_client.get_league_consolation_bracket(league_id)
        except:
            winners_bracket = None
            losers_bracket = None
        
        # Display champions and winners at the top
        st.markdown("---")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        # Champion (playoff winner)
        champion = "TBD"
        runner_up = "TBD"
        toilet_bowl_champion = "TBD"
        toilet_bowl_loser = "TBD"
        if winners_bracket:
            # Brackets are returned as a flat list of matchups
            # Each matchup has: m (matchup_id), r (round), t1 (team1), t2 (team2), w (winner), l (loser)
            if isinstance(winners_bracket, list):
                # Find the final round (highest round number)
                max_round = max((m.get('r', 0) for m in winners_bracket if isinstance(m, dict)), default=0)
                if max_round > 0:
                    # Get matchups from final round
                    final_matchups = [m for m in winners_bracket if isinstance(m, dict) and m.get('r') == max_round]
                    if final_matchups:
                        # Find the championship matchup (should be the one with winner)
                        final_matchup = next((m for m in final_matchups if m.get('w')), final_matchups[0])
                        winner_roster_id = final_matchup.get('w')
                        loser_roster_id = final_matchup.get('l')
                        if winner_roster_id:
                            winner_roster = next((r for r in rosters if r.get('roster_id') == winner_roster_id), None)
                            if winner_roster:
                                owner_id = winner_roster.get('owner_id')
                                champion = user_lookup.get(owner_id, 'Unknown')
                        if loser_roster_id:
                            loser_roster = next((r for r in rosters if r.get('roster_id') == loser_roster_id), None)
                            if loser_roster:
                                owner_id = loser_roster.get('owner_id')
                                runner_up = user_lookup.get(owner_id, 'Unknown')
                
                # Get toilet bowl champion and loser from losers bracket
                if losers_bracket and isinstance(losers_bracket, list):
                    from fantasy_football_ui.bracket_visualizer import get_playoff_seeds
                    seed_map = get_playoff_seeds(rosters, user_lookup)
                    
                    # Find toilet bowl matchups (teams with seeds 9-12)
                    toilet_bowl_matchups = []
                    for matchup in losers_bracket:
                        if isinstance(matchup, dict):
                            team1_id = matchup.get('t1')
                            team2_id = matchup.get('t2')
                            team1_seed = seed_map.get(team1_id, 0)
                            team2_seed = seed_map.get(team2_id, 0)
                            
                            if (9 <= team1_seed <= 12) and (9 <= team2_seed <= 12):
                                toilet_bowl_matchups.append(matchup)
                    
                    # Toilet bowl structure:
                    # Round 1: 9v12, 10v11
                    # Round 2: Winners play for championship, Losers play (loser of losers game is toilet bowl loser)
                    
                    # Find Round 1 toilet bowl matchups
                    round1_toilet_bowl = [m for m in toilet_bowl_matchups if m.get('r') == 1]
                    
                    # Find Round 2 toilet bowl matchups
                    round2_toilet_bowl = [m for m in toilet_bowl_matchups if m.get('r') == 2]
                    
                    # Get Round 1 winners and losers
                    round1_winners = set()
                    round1_losers = set()
                    for r1_matchup in round1_toilet_bowl:
                        r1_winner = r1_matchup.get('w')
                        r1_loser = r1_matchup.get('l')
                        if r1_winner:
                            round1_winners.add(r1_winner)
                        if r1_loser:
                            round1_losers.add(r1_loser)
                    
                    # Toilet bowl champion: Winner of Round 2 matchup between winners
                    for matchup in round2_toilet_bowl:
                        team1_id = matchup.get('t1')
                        team2_id = matchup.get('t2')
                        winner_id = matchup.get('w')
                        
                        # If both teams are winners from round 1, this is the championship
                        if team1_id in round1_winners and team2_id in round1_winners:
                            if winner_id:
                                champion_roster = next((r for r in rosters if r.get('roster_id') == winner_id), None)
                                if champion_roster:
                                    owner_id = champion_roster.get('owner_id')
                                    toilet_bowl_champion = user_lookup.get(owner_id, 'Unknown')
                        
                        # If both teams are losers from round 1, the loser of this game is the toilet bowl loser
                        if team1_id in round1_losers and team2_id in round1_losers:
                            loser_id = matchup.get('l')
                            if loser_id:
                                loser_roster = next((r for r in rosters if r.get('roster_id') == loser_id), None)
                                if loser_roster:
                                    owner_id = loser_roster.get('owner_id')
                                    toilet_bowl_loser = user_lookup.get(owner_id, 'Unknown')
        
        # First place season (regular season winner)
        first_place_season = "TBD"
        if rosters:
            # Sort by wins, then points
            sorted_rosters = sorted(rosters, key=lambda x: (x.get('settings', {}).get('wins', 0), x.get('settings', {}).get('fpts', 0)), reverse=True)
            if sorted_rosters:
                top_roster = sorted_rosters[0]
                owner_id = top_roster.get('owner_id')
                first_place_season = user_lookup.get(owner_id, 'Unknown')
        
        
        with col1:
            st.metric("🏆 Champion", champion)
        with col2:
            st.metric("🥈 Runner Up", runner_up)
        with col3:
            st.metric("📊 First Place (Season)", first_place_season)
        with col4:
            st.metric("🚽 Toilet Bowl Champion", toilet_bowl_champion)
        with col5:
            st.metric("💩 Toilet Bowl Loser", toilet_bowl_loser)
        
        st.markdown("---")
        
        # Game type selection
        game_type = st.radio(
            "Select Game Type",
            options=["Regular Season", "Post Season", "Consolation"],
            horizontal=True
        )
        
        if game_type == "Regular Season":
            # Week selector
            max_week = 14  # Regular season is weeks 1-14
            selected_week = st.selectbox(
                "Select Week",
                options=list(range(1, max_week + 1)),
                index=min(13, max_week - 1)  # Default to last week
            )
            
            # Get standings up to selected week
            st.subheader(f"Standings Through Week {selected_week}")
            
            # Calculate cumulative standings through selected week
            standings_data = []
            for roster in rosters:
                owner_id = roster.get('owner_id')
                team_name = user_lookup.get(owner_id, 'Unknown')
                
                # Get wins and points through selected week
                wins = 0
                losses = 0
                ties = 0
                total_points = 0.0
                
                for week_num in range(1, selected_week + 1):
                    try:
                        matchups = st.session_state.sleeper_client.get_league_matchups(league_id, week_num)
                        for matchup in matchups:
                            if matchup.get('roster_id') == roster.get('roster_id'):
                                points = matchup.get('points', 0) or 0
                                total_points += float(points)
                                
                                # Find opponent and determine win/loss
                                matchup_id = matchup.get('matchup_id')
                                opponent_matchup = next((m for m in matchups if m.get('matchup_id') == matchup_id and m.get('roster_id') != roster.get('roster_id')), None)
                                if opponent_matchup:
                                    opponent_points = opponent_matchup.get('points', 0) or 0
                                    if points > opponent_points:
                                        wins += 1
                                    elif points < opponent_points:
                                        losses += 1
                                    else:
                                        ties += 1
                                break
                    except:
                        continue
                
                standings_data.append({
                    'Team': team_name,
                    'Wins': wins,
                    'Losses': losses,
                    'Ties': ties,
                    'Points': round(total_points, 2)
                })
            
            if standings_data:
                standings_df = pd.DataFrame(standings_data)
                standings_df = standings_df.sort_values(['Wins', 'Points'], ascending=[False, False])
                standings_df['Rank'] = range(1, len(standings_df) + 1)
                standings_df = standings_df[['Rank', 'Team', 'Wins', 'Losses', 'Ties', 'Points']]
                st.dataframe(standings_df, use_container_width=True, hide_index=True)
            
            # Show matchups and results for selected week
            st.subheader(f"Week {selected_week} Matchups")
            try:
                matchups = st.session_state.sleeper_client.get_league_matchups(league_id, selected_week)
                
                # Get player data for roster display
                players = st.session_state.get('sleeper_players', {})
                if not players:
                    # Try to get players if not cached
                    try:
                        import requests
                        players_response = requests.get("https://api.sleeper.app/v1/players/nfl")
                        if players_response.status_code == 200:
                            players = players_response.json()
                            st.session_state.sleeper_players = players
                    except:
                        players = {}
                
                matchup_pairs = {}
                matchup_details = {}  # Store full matchup data for roster display
                
                for matchup in matchups:
                    matchup_id = matchup.get('matchup_id')
                    roster_id = matchup.get('roster_id')
                    points = matchup.get('points', 0) or 0
                    starters = matchup.get('starters', [])
                    players_list = matchup.get('players', [])  # All players on roster
                    players_points = matchup.get('players_points', {})
                    
                    roster = next((r for r in rosters if r.get('roster_id') == roster_id), None)
                    if roster:
                        owner_id = roster.get('owner_id')
                        team_name = user_lookup.get(owner_id, 'Unknown')
                        
                        if matchup_id not in matchup_pairs:
                            matchup_pairs[matchup_id] = []
                            matchup_details[matchup_id] = []
                        
                        matchup_pairs[matchup_id].append({
                            'Team': team_name,
                            'Points': round(points, 2)
                        })
                        
                        # Store roster details
                        matchup_details[matchup_id].append({
                            'team_name': team_name,
                            'roster_id': roster_id,
                            'points': points,
                            'starters': starters,
                            'players': players_list,
                            'players_points': players_points
                        })
                
                matchup_results = []
                for matchup_id, teams in matchup_pairs.items():
                    if len(teams) == 2:
                        team1, team2 = teams[0], teams[1]
                        winner = team1['Team'] if team1['Points'] > team2['Points'] else team2['Team']
                        matchup_results.append({
                            'Matchup ID': matchup_id,
                            'Team 1': team1['Team'],
                            'Points 1': team1['Points'],
                            'Team 2': team2['Team'],
                            'Points 2': team2['Points'],
                            'Winner': winner
                        })
                
                if matchup_results:
                    matchup_df = pd.DataFrame(matchup_results)
                    
                    # Display matchups with expandable roster details
                    for idx, row in matchup_df.iterrows():
                        matchup_id = row['Matchup ID']
                        team1_name = row['Team 1']
                        team2_name = row['Team 2']
                        team1_points = row['Points 1']
                        team2_points = row['Points 2']
                        winner = row['Winner']
                        
                        # Create expandable section for each matchup
                        with st.expander(f"🏈 {team1_name} ({team1_points}) vs {team2_name} ({team2_points}) - Winner: {winner}", expanded=False):
                            if matchup_id in matchup_details and len(matchup_details[matchup_id]) == 2:
                                team1_details = matchup_details[matchup_id][0]
                                team2_details = matchup_details[matchup_id][1]
                                
                                # Display Team 1 roster
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.markdown(f"### {team1_details['team_name']} - {team1_points:.2f} pts")
                                    
                                    # Starters
                                    st.markdown("**Starters:**")
                                    starters_data = []
                                    starters = team1_details.get('starters', [])
                                    players_points = team1_details.get('players_points', {})
                                    
                                    for player_id in starters:
                                        if player_id:
                                            player_points = players_points.get(str(player_id)) or players_points.get(player_id) or 0
                                            player_name = f"Player {player_id}"
                                            position = ""
                                            
                                            # Try to get player name and position
                                            if players:
                                                player_data = players.get(str(player_id)) or players.get(player_id)
                                                if player_data:
                                                    full_name = player_data.get('full_name', '')
                                                    if not full_name:
                                                        first = player_data.get('first_name', '')
                                                        last = player_data.get('last_name', '')
                                                        full_name = f"{first} {last}".strip()
                                                    if full_name:
                                                        player_name = full_name
                                                    
                                                    position = player_data.get('position', '')
                                            
                                            starters_data.append({
                                                'Player': player_name,
                                                'Position': position if position else 'N/A',
                                                'Points': round(player_points, 2)
                                            })
                                    
                                    if starters_data:
                                        starters_df = pd.DataFrame(starters_data)
                                        st.dataframe(starters_df, use_container_width=True, hide_index=True)
                                    
                                    # Bench players
                                    st.markdown("**Bench:**")
                                    bench_data = []
                                    all_players = team1_details.get('players', [])
                                    starters_set = set(starters)
                                    
                                    for player_id in all_players:
                                        if player_id and player_id not in starters_set:
                                            player_points = players_points.get(str(player_id)) or players_points.get(player_id) or 0
                                            player_name = f"Player {player_id}"
                                            position = ""
                                            
                                            # Try to get player name and position
                                            if players:
                                                player_data = players.get(str(player_id)) or players.get(player_id)
                                                if player_data:
                                                    full_name = player_data.get('full_name', '')
                                                    if not full_name:
                                                        first = player_data.get('first_name', '')
                                                        last = player_data.get('last_name', '')
                                                        full_name = f"{first} {last}".strip()
                                                    if full_name:
                                                        player_name = full_name
                                                    
                                                    position = player_data.get('position', '')
                                            
                                            bench_data.append({
                                                'Player': player_name,
                                                'Position': position if position else 'N/A',
                                                'Points': round(player_points, 2)
                                            })
                                    
                                    if bench_data:
                                        bench_df = pd.DataFrame(bench_data)
                                        st.dataframe(bench_df, use_container_width=True, hide_index=True)
                                    else:
                                        st.info("No bench players")
                                
                                with col2:
                                    st.markdown(f"### {team2_details['team_name']} - {team2_points:.2f} pts")
                                    
                                    # Starters
                                    st.markdown("**Starters:**")
                                    starters_data = []
                                    starters = team2_details.get('starters', [])
                                    players_points = team2_details.get('players_points', {})
                                    
                                    for player_id in starters:
                                        if player_id:
                                            player_points = players_points.get(str(player_id)) or players_points.get(player_id) or 0
                                            player_name = f"Player {player_id}"
                                            position = ""
                                            
                                            # Try to get player name and position
                                            if players:
                                                player_data = players.get(str(player_id)) or players.get(player_id)
                                                if player_data:
                                                    full_name = player_data.get('full_name', '')
                                                    if not full_name:
                                                        first = player_data.get('first_name', '')
                                                        last = player_data.get('last_name', '')
                                                        full_name = f"{first} {last}".strip()
                                                    if full_name:
                                                        player_name = full_name
                                                    
                                                    position = player_data.get('position', '')
                                            
                                            starters_data.append({
                                                'Player': player_name,
                                                'Position': position if position else 'N/A',
                                                'Points': round(player_points, 2)
                                            })
                                    
                                    if starters_data:
                                        starters_df = pd.DataFrame(starters_data)
                                        st.dataframe(starters_df, use_container_width=True, hide_index=True)
                                    
                                    # Bench players
                                    st.markdown("**Bench:**")
                                    bench_data = []
                                    all_players = team2_details.get('players', [])
                                    starters_set = set(starters)
                                    
                                    for player_id in all_players:
                                        if player_id and player_id not in starters_set:
                                            player_points = players_points.get(str(player_id)) or players_points.get(player_id) or 0
                                            player_name = f"Player {player_id}"
                                            position = ""
                                            
                                            # Try to get player name and position
                                            if players:
                                                player_data = players.get(str(player_id)) or players.get(player_id)
                                                if player_data:
                                                    full_name = player_data.get('full_name', '')
                                                    if not full_name:
                                                        first = player_data.get('first_name', '')
                                                        last = player_data.get('last_name', '')
                                                        full_name = f"{first} {last}".strip()
                                                    if full_name:
                                                        player_name = full_name
                                                    
                                                    position = player_data.get('position', '')
                                            
                                            bench_data.append({
                                                'Player': player_name,
                                                'Position': position if position else 'N/A',
                                                'Points': round(player_points, 2)
                                            })
                                    
                                    if bench_data:
                                        bench_df = pd.DataFrame(bench_data)
                                        st.dataframe(bench_df, use_container_width=True, hide_index=True)
                                    else:
                                        st.info("No bench players")
                else:
                    st.info(f"No matchup data available for week {selected_week}")
            except Exception as e:
                st.error(f"Error loading matchups: {str(e)}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
        
        elif game_type == "Post Season":
            st.subheader("Playoff Bracket")
            
            if winners_bracket:
                # Brackets are returned as a flat list of matchups
                # Group by round number
                if isinstance(winners_bracket, list):
                    # Group matchups by round
                    rounds_dict = {}
                    for matchup in winners_bracket:
                        if isinstance(matchup, dict):
                            round_num = matchup.get('r', 0)
                            if round_num not in rounds_dict:
                                rounds_dict[round_num] = []
                            rounds_dict[round_num].append(matchup)
                    
                    # Display tournament bracket visualization (only shows winners advancing)
                    from fantasy_football_ui.bracket_visualizer import display_bracket
                    display_bracket(rounds_dict, rosters, user_lookup, "Playoff")
                    
                    # Also show table view in expander
                    with st.expander("📊 Table View"):
                        for round_num in sorted(rounds_dict.keys()):
                            st.markdown(f"### Round {round_num}")
                            matchups = rounds_dict[round_num]
                            
                            matchup_list = []
                            for matchup in matchups:
                                team1_roster_id = matchup.get('t1')
                                team2_roster_id = matchup.get('t2')
                                winner_roster_id = matchup.get('w')
                                
                                team1_roster = next((r for r in rosters if r.get('roster_id') == team1_roster_id), None)
                                team2_roster = next((r for r in rosters if r.get('roster_id') == team2_roster_id), None)
                                
                                team1_name = user_lookup.get(team1_roster.get('owner_id'), 'Unknown') if team1_roster else 'TBD'
                                team2_name = user_lookup.get(team2_roster.get('owner_id'), 'Unknown') if team2_roster else 'TBD'
                                
                                winner_name = 'TBD'
                                if winner_roster_id:
                                    winner_roster = next((r for r in rosters if r.get('roster_id') == winner_roster_id), None)
                                    if winner_roster:
                                        winner_name = user_lookup.get(winner_roster.get('owner_id'), 'Unknown')
                                
                                matchup_list.append({
                                    'Team 1': team1_name,
                                    'Team 2': team2_name,
                                    'Winner': winner_name
                                })
                            
                            if matchup_list:
                                matchup_df = pd.DataFrame(matchup_list)
                                st.dataframe(matchup_df, use_container_width=True, hide_index=True)
                else:
                    st.info("Playoff bracket not available yet.")
            else:
                st.info("Playoff bracket data not available.")
        
        elif game_type == "Consolation":
            # Get playoff seeds to identify teams 9-12 (toilet bowl) vs 5-8 (consolation)
            from fantasy_football_ui.bracket_visualizer import get_playoff_seeds
            seed_map = get_playoff_seeds(rosters, user_lookup)
            
            # Separate teams by seed ranges
            toilet_bowl_teams = {roster_id: seed for roster_id, seed in seed_map.items() if seed >= 9}
            consolation_teams = {roster_id: seed for roster_id, seed in seed_map.items() if 5 <= seed <= 8}
            
            # Build toilet bowl bracket (9-12 seeds)
            st.subheader("🚽 Toilet Bowl (9th-12th Place)")
            
            toilet_bowl_rounds_dict = {}
            if losers_bracket and isinstance(losers_bracket, list):
                # Group losers bracket by round
                all_losers_rounds = {}
                for matchup in losers_bracket:
                    if isinstance(matchup, dict):
                        round_num = matchup.get('r', 0)
                        if round_num not in all_losers_rounds:
                            all_losers_rounds[round_num] = []
                        all_losers_rounds[round_num].append(matchup)
                
                # Filter for toilet bowl matchups (teams with seeds 9-12)
                # Round 1 should be: 9v12, 10v11
                for round_num in sorted(all_losers_rounds.keys()):
                    matchups = all_losers_rounds[round_num]
                    toilet_bowl_matchups = []
                    
                    for matchup in matchups:
                        team1_id = matchup.get('t1')
                        team2_id = matchup.get('t2')
                        
                        # Check if both teams are in toilet bowl (seeds 9-12)
                        team1_seed = seed_map.get(team1_id, 0)
                        team2_seed = seed_map.get(team2_id, 0)
                        
                        if (9 <= team1_seed <= 12) and (9 <= team2_seed <= 12):
                            # This is a toilet bowl matchup
                            toilet_bowl_matchups.append(matchup)
                    
                    if toilet_bowl_matchups:
                        # Order Round 1 matchups: 9v12, 10v11
                        if round_num == 1:
                            ordered_matchups = []
                            expected_pairs = [(9, 12), (10, 11)]
                            
                            for seed_pair in expected_pairs:
                                seed1, seed2 = seed_pair
                                matchup = next((m for m in toilet_bowl_matchups 
                                             if (seed_map.get(m.get('t1')) == seed1 and seed_map.get(m.get('t2')) == seed2) or
                                                (seed_map.get(m.get('t1')) == seed2 and seed_map.get(m.get('t2')) == seed1)), None)
                                if matchup:
                                    ordered_matchups.append(matchup)
                            
                            toilet_bowl_rounds_dict[round_num] = ordered_matchups if ordered_matchups else toilet_bowl_matchups
                        elif round_num == 2:
                            # Round 2 has two games: championship (winners) and losers game
                            # Get Round 1 winners and losers
                            round1_winners = set()
                            round1_losers = set()
                            for r1_matchup in toilet_bowl_rounds_dict.get(1, []):
                                if r1_matchup.get('w'):
                                    round1_winners.add(r1_matchup.get('w'))
                                if r1_matchup.get('l'):
                                    round1_losers.add(r1_matchup.get('l'))
                            
                            # Separate championship and losers game
                            championship_matchups = []
                            losers_matchups = []
                            
                            for matchup in toilet_bowl_matchups:
                                team1_id = matchup.get('t1')
                                team2_id = matchup.get('t2')
                                
                                if team1_id in round1_winners and team2_id in round1_winners:
                                    championship_matchups.append(matchup)
                                elif team1_id in round1_losers and team2_id in round1_losers:
                                    losers_matchups.append(matchup)
                            
                            # Store both games in Round 2 (championship first, then losers)
                            if championship_matchups or losers_matchups:
                                round2_matchups = championship_matchups + losers_matchups
                                toilet_bowl_rounds_dict[round_num] = round2_matchups
                        else:
                            toilet_bowl_rounds_dict[round_num] = toilet_bowl_matchups
            
            if toilet_bowl_rounds_dict:
                # Split Round 2 into championship and losers game for display
                # We need to create separate rounds for visualization
                display_toilet_bowl_rounds = {}
                for round_num in sorted(toilet_bowl_rounds_dict.keys()):
                    if round_num == 1:
                        display_toilet_bowl_rounds[round_num] = toilet_bowl_rounds_dict[round_num]
                    elif round_num == 2:
                        # Split Round 2 into two separate rounds for display
                        matchups = toilet_bowl_rounds_dict[round_num]
                        round1_winners = set()
                        round1_losers = set()
                        for r1_matchup in toilet_bowl_rounds_dict.get(1, []):
                            if r1_matchup.get('w'):
                                round1_winners.add(r1_matchup.get('w'))
                            if r1_matchup.get('l'):
                                round1_losers.add(r1_matchup.get('l'))
                        
                        championship_matchups = []
                        losers_matchups = []
                        
                        for matchup in matchups:
                            team1_id = matchup.get('t1')
                            team2_id = matchup.get('t2')
                            
                            if team1_id in round1_winners and team2_id in round1_winners:
                                championship_matchups.append(matchup)
                            elif team1_id in round1_losers and team2_id in round1_losers:
                                losers_matchups.append(matchup)
                        
                        # Create separate rounds: 2 for championship, 3 for losers game
                        if championship_matchups:
                            display_toilet_bowl_rounds[2] = championship_matchups
                        if losers_matchups:
                            display_toilet_bowl_rounds[3] = losers_matchups
                    else:
                        display_toilet_bowl_rounds[round_num] = toilet_bowl_rounds_dict[round_num]
                
                # Determine round names for toilet bowl
                toilet_bowl_round_names = {
                    1: "Round 1 (9v12, 10v11)",
                    2: "Toilet Bowl Championship",
                    3: "Toilet Bowl Losers Game"
                }
                
                # Display toilet bowl bracket
                from fantasy_football_ui.bracket_visualizer import display_bracket
                display_bracket(display_toilet_bowl_rounds, rosters, user_lookup, "Toilet Bowl", is_consolation=True, custom_round_names=toilet_bowl_round_names)
                
                # Also show table view in expander
                with st.expander("📊 Table View"):
                    for round_num in sorted(display_toilet_bowl_rounds.keys()):
                        round_name = toilet_bowl_round_names.get(round_num, f"Round {round_num}")
                        st.markdown(f"### {round_name}")
                        matchups = display_toilet_bowl_rounds[round_num]
                        
                        matchup_list = []
                        for matchup in matchups:
                            team1_roster_id = matchup.get('t1')
                            team2_roster_id = matchup.get('t2')
                            winner_roster_id = matchup.get('w')
                            
                            team1_roster = next((r for r in rosters if r.get('roster_id') == team1_roster_id), None) if team1_roster_id else None
                            team2_roster = next((r for r in rosters if r.get('roster_id') == team2_roster_id), None) if team2_roster_id else None
                            
                            team1_name = user_lookup.get(team1_roster.get('owner_id'), 'Unknown') if team1_roster else 'TBD'
                            team2_name = user_lookup.get(team2_roster.get('owner_id'), 'Unknown') if team2_roster else 'TBD'
                            
                            winner_name = 'TBD'
                            if winner_roster_id:
                                winner_roster = next((r for r in rosters if r.get('roster_id') == winner_roster_id), None)
                                if winner_roster:
                                    winner_name = user_lookup.get(winner_roster.get('owner_id'), 'Unknown')
                            
                            matchup_list.append({
                                'Team 1': team1_name,
                                'Team 2': team2_name if team2_name != 'TBD' else 'Bye',
                                'Winner': winner_name
                            })
                        
                        if matchup_list:
                            matchup_df = pd.DataFrame(matchup_list)
                            st.dataframe(matchup_df, use_container_width=True, hide_index=True)
            else:
                st.info("Toilet Bowl bracket data not available.")
            
            st.markdown("---")
            
            # Build consolation bracket (5-8 seeds)
            st.subheader("🏆 Consolation (5th-8th Place)")
            
            consolation_rounds_dict = {}
            if losers_bracket and isinstance(losers_bracket, list):
                # Group losers bracket by round
                all_losers_rounds = {}
                for matchup in losers_bracket:
                    if isinstance(matchup, dict):
                        round_num = matchup.get('r', 0)
                        if round_num not in all_losers_rounds:
                            all_losers_rounds[round_num] = []
                        all_losers_rounds[round_num].append(matchup)
                
                # Filter for consolation matchups (teams with seeds 5-8)
                for round_num in sorted(all_losers_rounds.keys()):
                    matchups = all_losers_rounds[round_num]
                    consolation_matchups = []
                    
                    for matchup in matchups:
                        team1_id = matchup.get('t1')
                        team2_id = matchup.get('t2')
                        
                        # Check if both teams are in consolation (seeds 5-8)
                        team1_seed = seed_map.get(team1_id, 0)
                        team2_seed = seed_map.get(team2_id, 0)
                        
                        if (5 <= team1_seed <= 8) and (5 <= team2_seed <= 8):
                            # This is a consolation matchup
                            consolation_matchups.append(matchup)
                    
                    if consolation_matchups:
                        consolation_rounds_dict[round_num] = consolation_matchups
            
            if consolation_rounds_dict:
                # Display consolation bracket
                from fantasy_football_ui.bracket_visualizer import display_bracket
                display_bracket(consolation_rounds_dict, rosters, user_lookup, "Consolation", is_consolation=True)
                
                # Also show table view in expander
                with st.expander("📊 Table View"):
                    for round_num in sorted(consolation_rounds_dict.keys()):
                        round_name = "5th Place Game" if round_num == 1 else "7th Place Game" if round_num == 2 else f"Round {round_num}"
                        st.markdown(f"### {round_name}")
                        matchups = consolation_rounds_dict[round_num]
                        
                        matchup_list = []
                        for matchup in matchups:
                            team1_roster_id = matchup.get('t1')
                            team2_roster_id = matchup.get('t2')
                            winner_roster_id = matchup.get('w')
                            
                            team1_roster = next((r for r in rosters if r.get('roster_id') == team1_roster_id), None) if team1_roster_id else None
                            team2_roster = next((r for r in rosters if r.get('roster_id') == team2_roster_id), None) if team2_roster_id else None
                            
                            team1_name = user_lookup.get(team1_roster.get('owner_id'), 'Unknown') if team1_roster else 'TBD'
                            team2_name = user_lookup.get(team2_roster.get('owner_id'), 'Unknown') if team2_roster else 'TBD'
                            
                            winner_name = 'TBD'
                            if winner_roster_id:
                                winner_roster = next((r for r in rosters if r.get('roster_id') == winner_roster_id), None)
                                if winner_roster:
                                    winner_name = user_lookup.get(winner_roster.get('owner_id'), 'Unknown')
                            
                            matchup_list.append({
                                'Team 1': team1_name,
                                'Team 2': team2_name if team2_name != 'TBD' else 'Bye',
                                'Winner': winner_name
                            })
                        
                        if matchup_list:
                            matchup_df = pd.DataFrame(matchup_list)
                            st.dataframe(matchup_df, use_container_width=True, hide_index=True)
            else:
                st.info("Consolation bracket data not available.")
    
    except Exception as e:
        st.error(f"Error loading history data: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

