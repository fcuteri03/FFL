"""
Matchup Breakdown helper functions for analyzing head-to-head matchup history
"""

import pandas as pd
from datetime import datetime
import streamlit as st
from typing import Dict, List, Set

from fantasy_football_ui.team_name_utils import normalize_team_name


def display_matchup_breakdown():
    """Display matchup breakdown view for analyzing head-to-head history"""
    st.header("⚔️ Matchup Breakdown")
    st.markdown("**Analyze head-to-head matchup history between two teams**")
    
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
    
    # Get all unique teams across all seasons
    st.info("📊 Loading team data from all seasons...")
    all_teams = set()
    
    for season in available_seasons:
        league_id = SLEEPER_LEAGUE_IDS[season]
        try:
            users = st.session_state.sleeper_client.get_league_users(league_id)
            for user in users:
                raw_name = user.get('display_name') or user.get('username', 'Unknown')
                team_name = normalize_team_name(raw_name)
                if team_name and team_name != 'Unknown':
                    all_teams.add(team_name)
        except:
            continue
    
    if not all_teams:
        st.error("No teams found. Please check your league connections.")
        return
    
    all_teams_sorted = sorted(list(all_teams))
    
    # Team selection
    col1, col2 = st.columns(2)
    with col1:
        team1 = st.selectbox(
            "Select Team 1",
            options=all_teams_sorted,
            index=0,
            key="matchup_team1"
        )
    with col2:
        # Filter out team1 from team2 options
        team2_options = [t for t in all_teams_sorted if t != team1]
        if not team2_options:
            st.warning("Please select a different team for Team 2")
            return
        
        team2 = st.selectbox(
            "Select Team 2",
            options=team2_options,
            index=0 if len(team2_options) > 0 else None,
            key="matchup_team2"
        )
    
    if not team1 or not team2 or team1 == team2:
        st.info("Please select two different teams to analyze their matchup history.")
        return
    
    # Load matchup history
    st.markdown("---")
    st.subheader(f"📈 {team1} vs {team2} - Head-to-Head History")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    matchup_history = []  # List of {year, week, team1, team1_score, team2, team2_score, winner, game_type}
    matchup_stats = {
        'team1_wins': 0,
        'team2_wins': 0,
        'ties': 0,
        'team1_total_points': 0.0,
        'team2_total_points': 0.0,
        'team1_avg_score': 0.0,
        'team2_avg_score': 0.0,
        'total_games': 0,
        'team1_longest_win_streak': 0,
        'team2_longest_win_streak': 0,
        'team1_current_streak': 0,
        'team2_current_streak': 0
    }
    
    for idx, season in enumerate(available_seasons):
        league_id = SLEEPER_LEAGUE_IDS[season]
        status_text.text(f"Loading {season} matchups...")
        progress_bar.progress((idx + 1) / len(available_seasons))
        
        try:
            # Get league to determine regular season length
            league = st.session_state.sleeper_client.get_league(league_id)
            regular_season_weeks = league.get('settings', {}).get('reg_season_count', 14) or 14
            
            # Get users and rosters
            users = st.session_state.sleeper_client.get_league_users(league_id)
            rosters = st.session_state.sleeper_client.get_league_rosters(league_id)
            user_lookup = {user.get('user_id'): normalize_team_name(user.get('display_name') or user.get('username', 'Unknown')) for user in users}
            roster_lookup = {roster.get('roster_id'): roster for roster in rosters}
            
            # Find roster IDs for the two teams
            team1_roster_id = None
            team2_roster_id = None
            
            for roster in rosters:
                owner_id = roster.get('owner_id')
                team_name = user_lookup.get(owner_id, 'Unknown')
                if team_name == team1:
                    team1_roster_id = roster.get('roster_id')
                elif team_name == team2:
                    team2_roster_id = roster.get('roster_id')
            
            if not team1_roster_id or not team2_roster_id:
                continue  # One or both teams not in this season
            
            # Get playoff brackets to identify playoff/toilet bowl games
            winners_bracket = None
            losers_bracket = None
            playoff_roster_ids = set()
            toilet_bowl_roster_ids = set()
            
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
            current_week = None
            if season == current_year:
                try:
                    sport_state = st.session_state.sleeper_client.get_sport_state("nfl")
                    current_week = sport_state.get('week', 1)
                except:
                    current_week = 1
            
            # Check all weeks (regular season and playoffs)
            max_week = 17  # Include playoffs
            if season == current_year and current_week:
                max_week = current_week - 1  # Only completed weeks
            
            for week in range(1, max_week + 1):
                try:
                    matchups = st.session_state.sleeper_client.get_league_matchups(league_id, week)
                    
                    # Find matchup between these two teams
                    team1_matchup = None
                    team2_matchup = None
                    
                    for matchup in matchups:
                        roster_id = matchup.get('roster_id')
                        matchup_id = matchup.get('matchup_id')
                        
                        if roster_id == team1_roster_id:
                            team1_matchup = matchup
                        elif roster_id == team2_roster_id:
                            team2_matchup = matchup
                    
                    # Check if they played each other (same matchup_id)
                    if team1_matchup and team2_matchup:
                        if team1_matchup.get('matchup_id') == team2_matchup.get('matchup_id'):
                            team1_score = round(float(team1_matchup.get('points', 0) or 0), 2)
                            team2_score = round(float(team2_matchup.get('points', 0) or 0), 2)
                            
                            # Determine game type
                            game_type = "Regular Season"
                            if week > regular_season_weeks:
                                if team1_roster_id in playoff_roster_ids and team2_roster_id in playoff_roster_ids:
                                    game_type = "Playoffs"
                                elif team1_roster_id in toilet_bowl_roster_ids and team2_roster_id in toilet_bowl_roster_ids:
                                    game_type = "Toilet Bowl"
                                else:
                                    game_type = "Consolation"
                            
                            # Determine winner
                            if team1_score > team2_score:
                                winner = team1
                            elif team2_score > team1_score:
                                winner = team2
                            else:
                                winner = "Tie"
                            
                            # Only include if combined score > 0
                            if team1_score + team2_score > 0:
                                matchup_history.append({
                                    'year': season,
                                    'week': week,
                                    'team1': team1,
                                    'team1_score': team1_score,
                                    'team2': team2,
                                    'team2_score': team2_score,
                                    'winner': winner,
                                    'game_type': game_type
                                })
                                
                                # Update stats
                                matchup_stats['total_games'] += 1
                                matchup_stats['team1_total_points'] += team1_score
                                matchup_stats['team2_total_points'] += team2_score
                                
                                if winner == team1:
                                    matchup_stats['team1_wins'] += 1
                                elif winner == team2:
                                    matchup_stats['team2_wins'] += 1
                                else:
                                    matchup_stats['ties'] += 1
                except:
                    continue
        except Exception as e:
            st.warning(f"⚠️ Error loading {season}: {str(e)}")
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    # Calculate averages
    if matchup_stats['total_games'] > 0:
        matchup_stats['team1_avg_score'] = matchup_stats['team1_total_points'] / matchup_stats['total_games']
        matchup_stats['team2_avg_score'] = matchup_stats['team2_total_points'] / matchup_stats['total_games']
    
    # Calculate longest win streaks
    # Sort matchups chronologically (oldest first) to calculate streaks
    matchup_history_sorted_chrono = sorted(matchup_history, key=lambda x: (x['year'], x['week']))
    
    team1_current_streak = 0
    team2_current_streak = 0
    team1_longest_streak = 0
    team2_longest_streak = 0
    
    for matchup in matchup_history_sorted_chrono:
        winner = matchup['winner']
        
        if winner == team1:
            team1_current_streak += 1
            team2_current_streak = 0
            team1_longest_streak = max(team1_longest_streak, team1_current_streak)
        elif winner == team2:
            team2_current_streak += 1
            team1_current_streak = 0
            team2_longest_streak = max(team2_longest_streak, team2_current_streak)
        else:  # Tie
            team1_current_streak = 0
            team2_current_streak = 0
    
    matchup_stats['team1_longest_win_streak'] = team1_longest_streak
    matchup_stats['team2_longest_win_streak'] = team2_longest_streak
    matchup_stats['team1_current_streak'] = team1_current_streak
    matchup_stats['team2_current_streak'] = team2_current_streak
    
    # Display summary statistics
    if matchup_history:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(f"{team1} Wins", matchup_stats['team1_wins'])
        with col2:
            st.metric(f"{team2} Wins", matchup_stats['team2_wins'])
        with col3:
            st.metric("Ties", matchup_stats['ties'])
        with col4:
            st.metric("Total Games", matchup_stats['total_games'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(f"{team1} Avg Score", f"{matchup_stats['team1_avg_score']:.2f}")
            st.metric(f"{team1} Total Points", f"{matchup_stats['team1_total_points']:.2f}")
            st.metric(f"{team1} Longest Win Streak", matchup_stats['team1_longest_win_streak'])
            st.metric(f"{team1} Current Win Streak", matchup_stats['team1_current_streak'])
        with col2:
            st.metric(f"{team2} Avg Score", f"{matchup_stats['team2_avg_score']:.2f}")
            st.metric(f"{team2} Total Points", f"{matchup_stats['team2_total_points']:.2f}")
            st.metric(f"{team2} Longest Win Streak", matchup_stats['team2_longest_win_streak'])
            st.metric(f"{team2} Current Win Streak", matchup_stats['team2_current_streak'])
        
        # Display matchup history table
        st.markdown("---")
        st.subheader("📋 Matchup History")
        
        # Sort by year (newest first), then by week
        matchup_history_sorted = sorted(matchup_history, key=lambda x: (x['year'], x['week']), reverse=True)
        
        matchup_df = pd.DataFrame(matchup_history_sorted)
        matchup_df = matchup_df.rename(columns={
            'year': 'Year',
            'week': 'Week',
            'team1': 'Team 1',
            'team1_score': 'Team 1 Score',
            'team2': 'Team 2',
            'team2_score': 'Team 2 Score',
            'winner': 'Winner',
            'game_type': 'Type'
        })
        
        # Reorder columns
        matchup_df = matchup_df[['Year', 'Week', 'Type', 'Team 1', 'Team 1 Score', 'Team 2', 'Team 2 Score', 'Winner']]
        
        # Highlight winner in the table
        def highlight_winner(row):
            styles = [''] * len(row)
            if row['Winner'] == team1:
                styles[3] = 'background-color: #90EE90'  # Light green for team1
            elif row['Winner'] == team2:
                styles[5] = 'background-color: #90EE90'  # Light green for team2
            elif row['Winner'] == 'Tie':
                styles[3] = 'background-color: #FFE4B5'  # Light yellow for ties
                styles[5] = 'background-color: #FFE4B5'
            return styles
        
        st.dataframe(
            matchup_df.style.apply(highlight_winner, axis=1),
            use_container_width=True,
            hide_index=True
        )
        
        # Breakdown by game type
        st.markdown("---")
        st.subheader("📊 Breakdown by Game Type")
        
        game_type_stats = {}
        for matchup in matchup_history:
            game_type = matchup['game_type']
            if game_type not in game_type_stats:
                game_type_stats[game_type] = {
                    'team1_wins': 0,
                    'team2_wins': 0,
                    'ties': 0,
                    'total': 0
                }
            
            game_type_stats[game_type]['total'] += 1
            if matchup['winner'] == team1:
                game_type_stats[game_type]['team1_wins'] += 1
            elif matchup['winner'] == team2:
                game_type_stats[game_type]['team2_wins'] += 1
            else:
                game_type_stats[game_type]['ties'] += 1
        
        for game_type, stats in game_type_stats.items():
            st.markdown(f"**{game_type}**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(f"{team1} Wins", stats['team1_wins'])
            with col2:
                st.metric(f"{team2} Wins", stats['team2_wins'])
            with col3:
                st.metric("Total Games", stats['total'])
    else:
        st.info(f"No matchup history found between {team1} and {team2}.")

