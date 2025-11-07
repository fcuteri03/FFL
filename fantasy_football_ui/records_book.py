"""
Records Book helper functions for displaying league records
"""

import pandas as pd
from datetime import datetime
import streamlit as st
from typing import Dict, List

from fantasy_football_ui.team_name_utils import normalize_team_name


def display_records_book():
    """Display records book with tabs for different record categories"""
    st.header("📖 Records Book")
    st.markdown("**All-time league records across all seasons**")
    
    # Get available seasons
    SLEEPER_LEAGUE_IDS = {
        2021: "740630336907657216",
        2022: "862956648505921536",
        2023: "1004526732419911680",
        2024: "1124842071690067968",
        2025: "1257479697114075136"
    }
    
    current_year = datetime.now().year
    available_seasons = [y for y in range(2021, current_year + 2) if y in SLEEPER_LEAGUE_IDS]
    
    record_tabs = st.tabs(["Single Game", "Regular Season", "Post Season", "Toilet Bowl", "All Time Leaders"])
    
    with record_tabs[0]:  # Single Game
        display_single_game_records(available_seasons, SLEEPER_LEAGUE_IDS)
    
    with record_tabs[1]:  # Regular Season
        from fantasy_football_ui.records_book_regular_season import display_regular_season_records
        display_regular_season_records(available_seasons, SLEEPER_LEAGUE_IDS)
    
    with record_tabs[2]:  # Post Season
        from fantasy_football_ui.records_book_post_season import display_post_season_records
        display_post_season_records(available_seasons, SLEEPER_LEAGUE_IDS)
    
    with record_tabs[3]:  # Toilet Bowl
        from fantasy_football_ui.records_book_toilet_bowl import display_toilet_bowl_records
        display_toilet_bowl_records(available_seasons, SLEEPER_LEAGUE_IDS)
    
    with record_tabs[4]:  # All Time Leaders
        from fantasy_football_ui.records_book_all_time_leaders import display_all_time_leaders
        display_all_time_leaders(available_seasons, SLEEPER_LEAGUE_IDS)


def display_single_game_records(available_seasons: List[int], SLEEPER_LEAGUE_IDS: Dict[int, str]):
    """Display single game records"""
    st.subheader("🎮 Single Game Records")
    
    # Collect all matchup data across all seasons
    all_matchups = []  # List of {year, week, team1, team1_score, team2, team2_score, matchup_id}
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Get current week for current season (to exclude incomplete weeks)
    current_year = datetime.now().year
    current_week = None
    if current_year in available_seasons:
        try:
            sport_state = st.session_state.sleeper_client.get_sport_state("nfl")
            current_week = sport_state.get('week', 1)
        except:
            current_week = 1
    
    for idx, season in enumerate(available_seasons):
        league_id = SLEEPER_LEAGUE_IDS[season]
        status_text.text(f"Loading matchups for {season}...")
        progress_bar.progress((idx + 1) / len(available_seasons))
        
        try:
            # Get league to determine regular season length
            league = st.session_state.sleeper_client.get_league(league_id)
            # Regular season is typically weeks 1-14, but check league settings
            regular_season_weeks = league.get('settings', {}).get('reg_season_count', 14) or 14
            
            # Get users and rosters for team name mapping
            users = st.session_state.sleeper_client.get_league_users(league_id)
            rosters = st.session_state.sleeper_client.get_league_rosters(league_id)
            user_lookup = {user.get('user_id'): normalize_team_name(user.get('display_name') or user.get('username', 'Unknown')) for user in users}
            roster_lookup = {roster.get('roster_id'): roster for roster in rosters}
            
            # Get playoff brackets to identify playoff and toilet bowl teams
            winners_bracket = None
            losers_bracket = None
            playoff_roster_ids = set()  # Roster IDs in winners bracket (seeds 1-8)
            toilet_bowl_roster_ids = set()  # Roster IDs in toilet bowl (seeds 9-12)
            
            try:
                winners_bracket = st.session_state.sleeper_client.get_league_playoff_bracket(league_id)
                if winners_bracket and isinstance(winners_bracket, list):
                    for matchup in winners_bracket:
                        if isinstance(matchup, dict):
                            t1 = matchup.get('t1')
                            t2 = matchup.get('t2')
                            if t1:
                                playoff_roster_ids.add(t1)
                            if t2:
                                playoff_roster_ids.add(t2)
            except:
                pass
            
            try:
                losers_bracket = st.session_state.sleeper_client.get_league_consolation_bracket(league_id)
                if losers_bracket and isinstance(losers_bracket, list):
                    from fantasy_football_ui.bracket_visualizer import get_playoff_seeds
                    seed_map = get_playoff_seeds(rosters, user_lookup)
                    for matchup in losers_bracket:
                        if isinstance(matchup, dict):
                            t1 = matchup.get('t1')
                            t2 = matchup.get('t2')
                            # Only include if both teams are seeds 9-12 (toilet bowl)
                            t1_seed = seed_map.get(t1, 0)
                            t2_seed = seed_map.get(t2, 0)
                            if (9 <= t1_seed <= 12) and (9 <= t2_seed <= 12):
                                if t1:
                                    toilet_bowl_roster_ids.add(t1)
                                if t2:
                                    toilet_bowl_roster_ids.add(t2)
            except:
                pass
            
            # Determine max week to fetch
            # For past seasons, include all weeks 1-17
            # For current season, only include weeks before current week (completed weeks)
            if season == current_year and current_week:
                max_week = min(current_week - 1, 17)  # Only completed weeks, max 17
            else:
                max_week = 17  # Past seasons, all weeks are complete
            
            # Fetch matchups for completed weeks only (1-17, excluding week 18)
            for week in range(1, max_week + 1):
                try:
                    matchups = st.session_state.sleeper_client.get_league_matchups(league_id, week)
                    
                    # Group matchups by matchup_id
                    matchup_pairs = {}
                    for matchup in matchups:
                        matchup_id = matchup.get('matchup_id')
                        roster_id = matchup.get('roster_id')
                        points = matchup.get('points', 0) or 0
                        
                        if matchup_id not in matchup_pairs:
                            matchup_pairs[matchup_id] = []
                        
                        # Get team name
                        team_name = 'Unknown'
                        if roster_id in roster_lookup:
                            roster = roster_lookup[roster_id]
                            owner_id = roster.get('owner_id')
                            if owner_id in user_lookup:
                                team_name = user_lookup[owner_id]
                        
                        matchup_pairs[matchup_id].append({
                            'team': team_name,
                            'score': round(points, 2)
                        })
                    
                    # Process matchup pairs
                    for matchup_id, teams in matchup_pairs.items():
                        if len(teams) == 2:
                            team1 = teams[0]
                            team2 = teams[1]
                            
                            # Exclude matchups with combined 0 points
                            combined_score = team1['score'] + team2['score']
                            if combined_score > 0:
                                # Get roster IDs for this matchup to check if it's playoff/toilet bowl
                                team1_roster_id = None
                                team2_roster_id = None
                                for matchup in matchups:
                                    if matchup.get('matchup_id') == matchup_id:
                                        roster_id = matchup.get('roster_id')
                                        team_name_from_matchup = 'Unknown'
                                        if roster_id in roster_lookup:
                                            roster = roster_lookup[roster_id]
                                            owner_id = roster.get('owner_id')
                                            if owner_id in user_lookup:
                                                team_name_from_matchup = user_lookup[owner_id]
                                        
                                        if team_name_from_matchup == team1['team']:
                                            team1_roster_id = roster_id
                                        elif team_name_from_matchup == team2['team']:
                                            team2_roster_id = roster_id
                                
                                # Determine if this matchup should be included
                                include_matchup = False
                                
                                if week <= regular_season_weeks:
                                    # Regular season weeks - include all matchups
                                    include_matchup = True
                                elif week > regular_season_weeks:
                                    # Playoff weeks (15-17) - only include if both teams are in playoffs or toilet bowl
                                    if team1_roster_id and team2_roster_id:
                                        # Check if both teams are in playoffs (winners bracket)
                                        if team1_roster_id in playoff_roster_ids and team2_roster_id in playoff_roster_ids:
                                            include_matchup = True
                                        # Check if both teams are in toilet bowl
                                        elif team1_roster_id in toilet_bowl_roster_ids and team2_roster_id in toilet_bowl_roster_ids:
                                            include_matchup = True
                                
                                if include_matchup:
                                    all_matchups.append({
                                        'year': season,
                                        'week': week,
                                        'team1': team1['team'],
                                        'team1_score': team1['score'],
                                        'team2': team2['team'],
                                        'team2_score': team2['score'],
                                        'matchup_id': matchup_id
                                    })
                except:
                    continue  # Skip weeks that don't exist
        except Exception as e:
            st.warning(f"⚠️ Error loading {season} matchups: {str(e)}")
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    if not all_matchups:
        st.info("No matchup data available.")
        return
    
    # Calculate records
    # 1. Top 5 Highest Scores
    st.markdown("### 🏆 Top 5 Highest Scores")
    highest_scores = []
    for matchup in all_matchups:
        highest_scores.append({
            'Year': matchup['year'],
            'Week': matchup['week'],
            'Team': matchup['team1'],
            'Score': matchup['team1_score']
        })
        highest_scores.append({
            'Year': matchup['year'],
            'Week': matchup['week'],
            'Team': matchup['team2'],
            'Score': matchup['team2_score']
        })
    
    highest_scores_df = pd.DataFrame(highest_scores)
    highest_scores_df = highest_scores_df.sort_values('Score', ascending=False).head(5)
    highest_scores_df['Rank'] = range(1, len(highest_scores_df) + 1)
    highest_scores_df = highest_scores_df[['Rank', 'Year', 'Week', 'Team', 'Score']]
    st.dataframe(highest_scores_df, use_container_width=True, hide_index=True)
    
    # 2. Top 5 Lowest Scores
    st.markdown("### 📉 Top 5 Lowest Scores")
    lowest_scores_df = pd.DataFrame(highest_scores)
    lowest_scores_df = lowest_scores_df.sort_values('Score', ascending=True).head(5)
    lowest_scores_df['Rank'] = range(1, len(lowest_scores_df) + 1)
    lowest_scores_df = lowest_scores_df[['Rank', 'Year', 'Week', 'Team', 'Score']]
    st.dataframe(lowest_scores_df, use_container_width=True, hide_index=True)
    
    # 3. Top 5 Highest Score in a Loss
    st.markdown("### 😢 Top 5 Highest Score in a Loss")
    highest_loss_scores = []
    for matchup in all_matchups:
        if matchup['team1_score'] > matchup['team2_score']:
            # Team 2 lost
            highest_loss_scores.append({
                'Year': matchup['year'],
                'Week': matchup['week'],
                'Matchup': f"{matchup['team2']} vs {matchup['team1']}",
                'Score': matchup['team2_score']
            })
        elif matchup['team2_score'] > matchup['team1_score']:
            # Team 1 lost
            highest_loss_scores.append({
                'Year': matchup['year'],
                'Week': matchup['week'],
                'Matchup': f"{matchup['team1']} vs {matchup['team2']}",
                'Score': matchup['team1_score']
            })
    
    if highest_loss_scores:
        highest_loss_df = pd.DataFrame(highest_loss_scores)
        highest_loss_df = highest_loss_df.sort_values('Score', ascending=False).head(5)
        highest_loss_df['Rank'] = range(1, len(highest_loss_df) + 1)
        highest_loss_df = highest_loss_df[['Rank', 'Year', 'Week', 'Matchup', 'Score']]
        st.dataframe(highest_loss_df, use_container_width=True, hide_index=True)
    else:
        st.info("No data available.")
    
    # 4. Top 5 Lowest Score in a Win
    st.markdown("### 🎉 Top 5 Lowest Score in a Win")
    lowest_win_scores = []
    for matchup in all_matchups:
        if matchup['team1_score'] > matchup['team2_score']:
            # Team 1 won
            lowest_win_scores.append({
                'Year': matchup['year'],
                'Week': matchup['week'],
                'Matchup': f"{matchup['team1']} vs {matchup['team2']}",
                'Score': matchup['team1_score']
            })
        elif matchup['team2_score'] > matchup['team1_score']:
            # Team 2 won
            lowest_win_scores.append({
                'Year': matchup['year'],
                'Week': matchup['week'],
                'Matchup': f"{matchup['team2']} vs {matchup['team1']}",
                'Score': matchup['team2_score']
            })
    
    if lowest_win_scores:
        lowest_win_df = pd.DataFrame(lowest_win_scores)
        lowest_win_df = lowest_win_df.sort_values('Score', ascending=True).head(5)
        lowest_win_df['Rank'] = range(1, len(lowest_win_df) + 1)
        lowest_win_df = lowest_win_df[['Rank', 'Year', 'Week', 'Matchup', 'Score']]
        st.dataframe(lowest_win_df, use_container_width=True, hide_index=True)
    else:
        st.info("No data available.")
    
    # 5. Top 5 Biggest Blowout (Biggest point differential in a win)
    st.markdown("### 💥 Top 5 Biggest Blowout")
    blowouts = []
    for matchup in all_matchups:
        diff = abs(matchup['team1_score'] - matchup['team2_score'])
        if matchup['team1_score'] > matchup['team2_score']:
            winner = matchup['team1']
            loser = matchup['team2']
            winner_score = matchup['team1_score']
            loser_score = matchup['team2_score']
        else:
            winner = matchup['team2']
            loser = matchup['team1']
            winner_score = matchup['team2_score']
            loser_score = matchup['team1_score']
        
        blowouts.append({
            'Year': matchup['year'],
            'Week': matchup['week'],
            'Matchup': f"{winner} vs {loser}",
            'Winner Score': winner_score,
            'Loser Score': loser_score,
            'Differential': round(diff, 2)
        })
    
    if blowouts:
        blowouts_df = pd.DataFrame(blowouts)
        blowouts_df = blowouts_df.sort_values('Differential', ascending=False).head(5)
        blowouts_df['Rank'] = range(1, len(blowouts_df) + 1)
        blowouts_df = blowouts_df[['Rank', 'Year', 'Week', 'Matchup', 'Winner Score', 'Loser Score', 'Differential']]
        st.dataframe(blowouts_df, use_container_width=True, hide_index=True)
    else:
        st.info("No data available.")
    
    # 6. Top 5 Closest Matchup (Smallest point differential)
    st.markdown("### ⚡ Top 5 Closest Matchup")
    close_matchups = []
    for matchup in all_matchups:
        diff = abs(matchup['team1_score'] - matchup['team2_score'])
        close_matchups.append({
            'Year': matchup['year'],
            'Week': matchup['week'],
            'Matchup': f"{matchup['team1']} vs {matchup['team2']}",
            'Team 1 Score': matchup['team1_score'],
            'Team 2 Score': matchup['team2_score'],
            'Differential': round(diff, 2)
        })
    
    if close_matchups:
        close_df = pd.DataFrame(close_matchups)
        close_df = close_df.sort_values('Differential', ascending=True).head(5)
        close_df['Rank'] = range(1, len(close_df) + 1)
        close_df = close_df[['Rank', 'Year', 'Week', 'Matchup', 'Team 1 Score', 'Team 2 Score', 'Differential']]
        st.dataframe(close_df, use_container_width=True, hide_index=True)
    else:
        st.info("No data available.")
    
    # 7. Top 5 Highest Combined Score
    st.markdown("### 🔥 Top 5 Highest Combined Score")
    combined_scores = []
    for matchup in all_matchups:
        combined = matchup['team1_score'] + matchup['team2_score']
        combined_scores.append({
            'Year': matchup['year'],
            'Week': matchup['week'],
            'Matchup': f"{matchup['team1']} vs {matchup['team2']}",
            'Team 1 Score': matchup['team1_score'],
            'Team 2 Score': matchup['team2_score'],
            'Combined Score': round(combined, 2)
        })
    
    if combined_scores:
        combined_df = pd.DataFrame(combined_scores)
        combined_df = combined_df.sort_values('Combined Score', ascending=False).head(5)
        combined_df['Rank'] = range(1, len(combined_df) + 1)
        combined_df = combined_df[['Rank', 'Year', 'Week', 'Matchup', 'Team 1 Score', 'Team 2 Score', 'Combined Score']]
        st.dataframe(combined_df, use_container_width=True, hide_index=True)
    else:
        st.info("No data available.")
    
    # 8. Top 5 Lowest Combined Score
    st.markdown("### 🥶 Top 5 Lowest Combined Score")
    lowest_combined_df = pd.DataFrame(combined_scores)
    lowest_combined_df = lowest_combined_df.sort_values('Combined Score', ascending=True).head(5)
    lowest_combined_df['Rank'] = range(1, len(lowest_combined_df) + 1)
    lowest_combined_df = lowest_combined_df[['Rank', 'Year', 'Week', 'Matchup', 'Team 1 Score', 'Team 2 Score', 'Combined Score']]
    st.dataframe(lowest_combined_df, use_container_width=True, hide_index=True)
    
    # Player Stats Records
    st.markdown("---")
    st.markdown("## 👤 Player Stats Records")
    
    # Get player data (cache it)
    if 'sleeper_players' not in st.session_state:
        try:
            import requests
            players_response = requests.get("https://api.sleeper.app/v1/players/nfl")
            if players_response.status_code == 200:
                st.session_state.sleeper_players = players_response.json()
            else:
                st.session_state.sleeper_players = {}
        except:
            st.session_state.sleeper_players = {}
    
    players = st.session_state.sleeper_players
    
    # Collect player data from matchups
    all_player_games = []  # List of {year, week, team, player_id, player_name, position, points}
    all_team_position_totals = []  # List of {year, week, team, position, total_points, players} for RB/WR
    
    player_status_text = st.empty()
    player_progress_bar = st.progress(0)
    player_status_text.text("Loading player data from matchups...")
    
    # Get current week for current season (to exclude incomplete weeks)
    current_year = datetime.now().year
    current_week = None
    if current_year in available_seasons:
        try:
            sport_state = st.session_state.sleeper_client.get_sport_state("nfl")
            current_week = sport_state.get('week', 1)
        except:
            current_week = 1
    
    for idx, season in enumerate(available_seasons):
        league_id = SLEEPER_LEAGUE_IDS[season]
        player_status_text.text(f"Loading player data for {season}...")
        player_progress_bar.progress((idx + 1) / len(available_seasons))
        
        try:
            # Get league to determine regular season length
            league = st.session_state.sleeper_client.get_league(league_id)
            # Regular season is typically weeks 1-14, but check league settings
            regular_season_weeks = league.get('settings', {}).get('reg_season_count', 14) or 14
            
            users = st.session_state.sleeper_client.get_league_users(league_id)
            rosters = st.session_state.sleeper_client.get_league_rosters(league_id)
            user_lookup = {user.get('user_id'): normalize_team_name(user.get('display_name') or user.get('username', 'Unknown')) for user in users}
            roster_lookup = {roster.get('roster_id'): roster for roster in rosters}
            
            # Get playoff brackets to identify playoff and toilet bowl teams
            winners_bracket = None
            losers_bracket = None
            playoff_roster_ids = set()  # Roster IDs in winners bracket (seeds 1-8)
            toilet_bowl_roster_ids = set()  # Roster IDs in toilet bowl (seeds 9-12)
            
            try:
                winners_bracket = st.session_state.sleeper_client.get_league_playoff_bracket(league_id)
                if winners_bracket and isinstance(winners_bracket, list):
                    for matchup in winners_bracket:
                        if isinstance(matchup, dict):
                            t1 = matchup.get('t1')
                            t2 = matchup.get('t2')
                            if t1:
                                playoff_roster_ids.add(t1)
                            if t2:
                                playoff_roster_ids.add(t2)
            except:
                pass
            
            try:
                losers_bracket = st.session_state.sleeper_client.get_league_consolation_bracket(league_id)
                if losers_bracket and isinstance(losers_bracket, list):
                    from fantasy_football_ui.bracket_visualizer import get_playoff_seeds
                    seed_map = get_playoff_seeds(rosters, user_lookup)
                    for matchup in losers_bracket:
                        if isinstance(matchup, dict):
                            t1 = matchup.get('t1')
                            t2 = matchup.get('t2')
                            # Only include if both teams are seeds 9-12 (toilet bowl)
                            t1_seed = seed_map.get(t1, 0)
                            t2_seed = seed_map.get(t2, 0)
                            if (9 <= t1_seed <= 12) and (9 <= t2_seed <= 12):
                                if t1:
                                    toilet_bowl_roster_ids.add(t1)
                                if t2:
                                    toilet_bowl_roster_ids.add(t2)
            except:
                pass
            
            # Determine max week to fetch
            # For past seasons, include all weeks 1-17
            # For current season, only include weeks before current week (completed weeks)
            if season == current_year and current_week:
                max_week = min(current_week - 1, 17)  # Only completed weeks, max 17
            else:
                max_week = 17  # Past seasons, all weeks are complete
            
            for week in range(1, max_week + 1):
                try:
                    matchups = st.session_state.sleeper_client.get_league_matchups(league_id, week)
                    
                    for matchup in matchups:
                        roster_id = matchup.get('roster_id')
                        starters = matchup.get('starters', [])
                        players_points = matchup.get('players_points', {})
                        
                        # Get team name
                        team_name = 'Unknown'
                        if roster_id in roster_lookup:
                            roster = roster_lookup[roster_id]
                            owner_id = roster.get('owner_id')
                            if owner_id in user_lookup:
                                team_name = user_lookup[owner_id]
                        
                        # Check if this matchup should be included (regular season, playoff, or toilet bowl)
                        include_matchup = False
                        if week <= regular_season_weeks:
                            # Regular season weeks - include all matchups
                            include_matchup = True
                        elif week > regular_season_weeks:
                            # Playoff weeks (15-17) - only include if team is in playoffs or toilet bowl
                            if roster_id in playoff_roster_ids or roster_id in toilet_bowl_roster_ids:
                                include_matchup = True
                        
                        if not include_matchup:
                            continue
                        
                        # Process each starter
                        rb_players = []  # List of {name, points}
                        wr_players = []  # List of {name, points}
                        
                        for player_id in starters:
                            if not player_id:
                                continue
                            
                            player_id_str = str(player_id)
                            points = players_points.get(player_id_str) or players_points.get(player_id) or 0
                            
                            # Get player info
                            player_data = players.get(player_id_str) or players.get(player_id)
                            if player_data:
                                position = player_data.get('position', '')
                                full_name = player_data.get('full_name', '')
                                if not full_name:
                                    first = player_data.get('first_name', '')
                                    last = player_data.get('last_name', '')
                                    full_name = f"{first} {last}".strip()
                                
                                if position and full_name:
                                    points_rounded = round(float(points), 2)
                                    all_player_games.append({
                                        'year': season,
                                        'week': week,
                                        'team': team_name,
                                        'player_id': player_id_str,
                                        'player_name': full_name,
                                        'position': position,
                                        'points': points_rounded
                                    })
                                    
                                    # Track RB and WR for combined totals
                                    if position == 'RB':
                                        rb_players.append({'name': full_name, 'points': points_rounded})
                                    elif position == 'WR':
                                        wr_players.append({'name': full_name, 'points': points_rounded})
                        
                        # Calculate combined RB and WR totals
                        if rb_players:
                            rb_total = sum(p['points'] for p in rb_players)
                            # Format players list as "Player1 (pts), Player2 (pts)"
                            rb_players_str = ', '.join([f"{p['name']} ({p['points']})" for p in rb_players])
                            all_team_position_totals.append({
                                'year': season,
                                'week': week,
                                'team': team_name,
                                'position': 'RB',
                                'total_points': rb_total,
                                'players': rb_players_str
                            })
                        
                        if wr_players:
                            wr_total = sum(p['points'] for p in wr_players)
                            # Format players list as "Player1 (pts), Player2 (pts)"
                            wr_players_str = ', '.join([f"{p['name']} ({p['points']})" for p in wr_players])
                            all_team_position_totals.append({
                                'year': season,
                                'week': week,
                                'team': team_name,
                                'position': 'WR',
                                'total_points': wr_total,
                                'players': wr_players_str
                            })
                except:
                    continue
        except Exception as e:
            st.warning(f"⚠️ Error loading player data for {season}: {str(e)}")
            continue
    
    player_progress_bar.empty()
    player_status_text.empty()
    
    if not all_player_games:
        st.info("No player data available.")
        return
    
    # Position-specific records
    positions = ['QB', 'RB', 'WR', 'TE', 'DEF', 'K']
    
    # Highest scores by position
    st.markdown("### 🏆 Highest Score by Position (Starting Lineup)")
    for position in positions:
        st.markdown(f"#### {position}")
        position_games = [g for g in all_player_games if g['position'] == position]
        if position_games:
            position_df = pd.DataFrame(position_games)
            position_df = position_df.sort_values('points', ascending=False).head(5)
            position_df['Rank'] = range(1, len(position_df) + 1)
            position_df = position_df.rename(columns={'player_name': 'Player', 'points': 'Points', 'year': 'Year', 'week': 'Week', 'team': 'Team'})
            position_df = position_df[['Rank', 'Year', 'Week', 'Team', 'Player', 'Points']]
            st.dataframe(position_df, use_container_width=True, hide_index=True)
        else:
            st.info(f"No {position} data available.")
    
    # Lowest scores by position
    st.markdown("### 📉 Lowest Score by Position (Starting Lineup)")
    for position in positions:
        st.markdown(f"#### {position}")
        position_games = [g for g in all_player_games if g['position'] == position]
        if position_games:
            position_df = pd.DataFrame(position_games)
            position_df = position_df.sort_values('points', ascending=True).head(5)
            position_df['Rank'] = range(1, len(position_df) + 1)
            position_df = position_df.rename(columns={'player_name': 'Player', 'points': 'Points', 'year': 'Year', 'week': 'Week', 'team': 'Team'})
            position_df = position_df[['Rank', 'Year', 'Week', 'Team', 'Player', 'Points']]
            st.dataframe(position_df, use_container_width=True, hide_index=True)
        else:
            st.info(f"No {position} data available.")
    
    # Combined RB and WR totals
    st.markdown("### 🏃 Combined Running Back Points")
    st.markdown("#### Most Combined RB Points (Starting RBs)")
    rb_totals = [t for t in all_team_position_totals if t['position'] == 'RB']
    if rb_totals:
        rb_df = pd.DataFrame(rb_totals)
        rb_df = rb_df.sort_values('total_points', ascending=False).head(5)
        rb_df['Rank'] = range(1, len(rb_df) + 1)
        rb_df = rb_df.rename(columns={'total_points': 'Total Points', 'year': 'Year', 'week': 'Week', 'team': 'Team', 'players': 'Players'})
        rb_df = rb_df[['Rank', 'Year', 'Week', 'Team', 'Total Points', 'Players']]
        st.dataframe(rb_df, use_container_width=True, hide_index=True)
    else:
        st.info("No RB data available.")
    
    st.markdown("#### Least Combined RB Points (Starting RBs)")
    if rb_totals:
        rb_df = pd.DataFrame(rb_totals)
        rb_df = rb_df.sort_values('total_points', ascending=True).head(5)
        rb_df['Rank'] = range(1, len(rb_df) + 1)
        rb_df = rb_df.rename(columns={'total_points': 'Total Points', 'year': 'Year', 'week': 'Week', 'team': 'Team', 'players': 'Players'})
        rb_df = rb_df[['Rank', 'Year', 'Week', 'Team', 'Total Points', 'Players']]
        st.dataframe(rb_df, use_container_width=True, hide_index=True)
    
    st.markdown("### 🏈 Combined Wide Receiver Points")
    st.markdown("#### Most Combined WR Points (Starting WRs)")
    wr_totals = [t for t in all_team_position_totals if t['position'] == 'WR']
    if wr_totals:
        wr_df = pd.DataFrame(wr_totals)
        wr_df = wr_df.sort_values('total_points', ascending=False).head(5)
        wr_df['Rank'] = range(1, len(wr_df) + 1)
        wr_df = wr_df.rename(columns={'total_points': 'Total Points', 'year': 'Year', 'week': 'Week', 'team': 'Team', 'players': 'Players'})
        wr_df = wr_df[['Rank', 'Year', 'Week', 'Team', 'Total Points', 'Players']]
        st.dataframe(wr_df, use_container_width=True, hide_index=True)
    else:
        st.info("No WR data available.")
    
    st.markdown("#### Least Combined WR Points (Starting WRs)")
    if wr_totals:
        wr_df = pd.DataFrame(wr_totals)
        wr_df = wr_df.sort_values('total_points', ascending=True).head(5)
        wr_df['Rank'] = range(1, len(wr_df) + 1)
        wr_df = wr_df.rename(columns={'total_points': 'Total Points', 'year': 'Year', 'week': 'Week', 'team': 'Team', 'players': 'Players'})
        wr_df = wr_df[['Rank', 'Year', 'Week', 'Team', 'Total Points', 'Players']]
        st.dataframe(wr_df, use_container_width=True, hide_index=True)

