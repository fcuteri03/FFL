"""
Team Breakdown helper functions for analyzing individual team fantasy careers
"""

import pandas as pd
from datetime import datetime
import streamlit as st
from typing import Dict, List, Set, Tuple
import plotly.express as px
import plotly.graph_objects as go

from fantasy_football_ui.team_name_utils import normalize_team_name


def display_team_breakdown():
    """Display team breakdown view for analyzing individual team fantasy careers"""
    st.header("👤 Team Breakdown")
    st.markdown("**Analyze individual team fantasy career statistics**")
    
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
    team_first_season = {}  # Track when each team joined
    
    for season in available_seasons:
        league_id = SLEEPER_LEAGUE_IDS[season]
        try:
            users = st.session_state.sleeper_client.get_league_users(league_id)
            for user in users:
                raw_name = user.get('display_name') or user.get('username', 'Unknown')
                team_name = normalize_team_name(raw_name)
                if team_name and team_name != 'Unknown':
                    all_teams.add(team_name)
                    if team_name not in team_first_season:
                        team_first_season[team_name] = season
        except:
            continue
    
    if not all_teams:
        st.error("No teams found. Please check your league connections.")
        return
    
    all_teams_sorted = sorted(list(all_teams))
    
    # Team selection
    selected_team = st.selectbox(
        "Select Team",
        options=all_teams_sorted,
        index=0,
        key="team_breakdown_select"
    )
    
    if not selected_team:
        st.info("Please select a team to analyze.")
        return
    
    # Load team data
    st.markdown("---")
    st.subheader(f"📈 {selected_team} - Career Breakdown")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Initialize team stats
    team_stats = {
        'member_since': team_first_season.get(selected_team, 2021),
        'overall_wins': 0,
        'overall_losses': 0,
        'overall_ties': 0,
        'championships': 0,
        'first_place_seasons': 0,
        'runner_up_playoffs': 0,
        'playoff_appearances': 0,
        'playoff_wins': 0,
        'playoff_losses': 0,
        'toilet_bowl_appearances': 0,
        'toilet_bowl_wins': 0,
        'toilet_bowl_losses': 0,
        'toilet_bowl_championships': 0,
        'toilet_bowl_losers': 0,
        'total_points': 0.0,
        'total_games': 0,
        'highest_score': 0.0,
        'lowest_score': float('inf'),
        'season_stats': [],  # List of {year, wins, losses, ties, points, avg_score, games}
        'game_log': [],  # List of all games
        'opponent_records': {}  # {opponent: {regular_season: {wins, losses}, playoffs: {...}, etc.}}
    }
    
    # Get current week for current season
    current_week = None
    if current_year in available_seasons:
        try:
            sport_state = st.session_state.sleeper_client.get_sport_state("nfl")
            current_week = sport_state.get('week', 1)
        except:
            current_week = 1
    
    for idx, season in enumerate(available_seasons):
        league_id = SLEEPER_LEAGUE_IDS[season]
        status_text.text(f"Loading {season} data...")
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
            
            # Find roster ID for selected team
            team_roster_id = None
            for roster in rosters:
                owner_id = roster.get('owner_id')
                team_name = user_lookup.get(owner_id, 'Unknown')
                if team_name == selected_team:
                    team_roster_id = roster.get('roster_id')
                    break
            
            if not team_roster_id:
                continue  # Team not in this season
            
            # Get standings
            standings = []
            for roster in rosters:
                settings = roster.get('settings', {})
                wins = settings.get('wins', 0)
                losses = settings.get('losses', 0)
                ties = settings.get('ties', 0)
                points = settings.get('fpts', 0) + (settings.get('fpts_decimal', 0) / 100)
                
                owner_id = roster.get('owner_id')
                team_name = user_lookup.get(owner_id, 'Unknown')
                
                standings.append({
                    'team_name': team_name,
                    'wins': wins,
                    'losses': losses,
                    'ties': ties,
                    'points': points
                })
            
            # Sort by wins, then points
            standings.sort(key=lambda x: (x['wins'], x['points']), reverse=True)
            
            # Check for first place
            if standings and standings[0]['team_name'] == selected_team:
                team_stats['first_place_seasons'] += 1
            
            # Get playoff brackets
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
            
            # Check playoff/toilet bowl appearances
            if team_roster_id in playoff_roster_ids:
                team_stats['playoff_appearances'] += 1
            if team_roster_id in toilet_bowl_roster_ids:
                team_stats['toilet_bowl_appearances'] += 1
            
            # Determine champion, runner-up, toilet bowl champion/loser
            champion = None
            runner_up = None
            toilet_bowl_champion = None
            toilet_bowl_loser = None
            
            if winners_bracket and isinstance(winners_bracket, list):
                # Find championship matchup (highest round)
                max_round = max([m.get('r', 0) for m in winners_bracket if isinstance(m, dict)], default=0)
                championship_matchups = [m for m in winners_bracket if isinstance(m, dict) and m.get('r') == max_round]
                
                for matchup in championship_matchups:
                    winner_id = matchup.get('w')
                    if winner_id:
                        winner_roster = next((r for r in rosters if r.get('roster_id') == winner_id), None)
                        if winner_roster:
                            owner_id = winner_roster.get('owner_id')
                            champion = user_lookup.get(owner_id, 'Unknown')
                    
                    # Find runner-up (loser of championship)
                    loser_id = matchup.get('l')
                    if loser_id:
                        loser_roster = next((r for r in rosters if r.get('roster_id') == loser_id), None)
                        if loser_roster:
                            owner_id = loser_roster.get('owner_id')
                            runner_up = user_lookup.get(owner_id, 'Unknown')
            
            if losers_bracket and isinstance(losers_bracket, list):
                from fantasy_football_ui.bracket_visualizer import get_playoff_seeds
                seed_map = get_playoff_seeds(rosters, user_lookup)
                
                # Find toilet bowl matchups (seeds 9-12)
                toilet_bowl_matchups = []
                for matchup in losers_bracket:
                    if isinstance(matchup, dict):
                        t1 = matchup.get('t1')
                        t2 = matchup.get('t2')
                        t1_seed = seed_map.get(t1, 0)
                        t2_seed = seed_map.get(t2, 0)
                        if (9 <= t1_seed <= 12) and (9 <= t2_seed <= 12):
                            toilet_bowl_matchups.append(matchup)
                
                # Find Round 1 and Round 2 toilet bowl matchups
                round1_toilet_bowl = [m for m in toilet_bowl_matchups if m.get('r') == 1]
                round2_toilet_bowl = [m for m in toilet_bowl_matchups if m.get('r') == 2]
                
                round1_winners = set()
                round1_losers = set()
                for r1_matchup in round1_toilet_bowl:
                    r1_winner = r1_matchup.get('w')
                    r1_loser = r1_matchup.get('l')
                    if r1_winner:
                        round1_winners.add(r1_winner)
                    if r1_loser:
                        round1_losers.add(r1_loser)
                
                for matchup in round2_toilet_bowl:
                    team1_id = matchup.get('t1')
                    team2_id = matchup.get('t2')
                    winner_id = matchup.get('w')
                    loser_id = matchup.get('l')
                    
                    # Toilet bowl champion: Winner of Round 2 matchup between winners
                    if team1_id in round1_winners and team2_id in round1_winners:
                        if winner_id:
                            champion_roster = next((r for r in rosters if r.get('roster_id') == winner_id), None)
                            if champion_roster:
                                owner_id = champion_roster.get('owner_id')
                                toilet_bowl_champion = user_lookup.get(owner_id, 'Unknown')
                    
                    # Toilet bowl loser: Loser of Round 2 matchup between losers
                    if team1_id in round1_losers and team2_id in round1_losers:
                        if loser_id:
                            loser_roster = next((r for r in rosters if r.get('roster_id') == loser_id), None)
                            if loser_roster:
                                owner_id = loser_roster.get('owner_id')
                                toilet_bowl_loser = user_lookup.get(owner_id, 'Unknown')
            
            if champion == selected_team:
                team_stats['championships'] += 1
            if runner_up == selected_team:
                team_stats['runner_up_playoffs'] += 1
            if toilet_bowl_champion == selected_team:
                team_stats['toilet_bowl_championships'] += 1
            if toilet_bowl_loser == selected_team:
                team_stats['toilet_bowl_losers'] += 1
            
            # Count playoff wins/losses
            if winners_bracket and isinstance(winners_bracket, list):
                for matchup in winners_bracket:
                    if isinstance(matchup, dict):
                        winner_id = matchup.get('w')
                        loser_id = matchup.get('l')
                        if winner_id == team_roster_id:
                            team_stats['playoff_wins'] += 1
                        elif loser_id == team_roster_id:
                            team_stats['playoff_losses'] += 1
            
            # Count toilet bowl wins/losses
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
                            winner_id = matchup.get('w')
                            loser_id = matchup.get('l')
                            if winner_id == team_roster_id:
                                team_stats['toilet_bowl_wins'] += 1
                            elif loser_id == team_roster_id:
                                team_stats['toilet_bowl_losses'] += 1
            
            # Process all games for this season
            season_wins = 0
            season_losses = 0
            season_ties = 0
            season_points = 0.0
            season_games = 0
            season_scores = []
            
            # Determine max week to fetch
            max_week = 17  # Include playoffs
            if season == current_year and current_week:
                max_week = current_week - 1  # Only completed weeks
            
            for week in range(1, max_week + 1):
                try:
                    matchups = st.session_state.sleeper_client.get_league_matchups(league_id, week)
                    
                    for matchup in matchups:
                        roster_id = matchup.get('roster_id')
                        if roster_id != team_roster_id:
                            continue
                        
                        matchup_id = matchup.get('matchup_id')
                        points = round(float(matchup.get('points', 0) or 0), 2)
                        
                        # Find opponent
                        opponent_roster_id = None
                        opponent_name = 'Unknown'
                        for opp_matchup in matchups:
                            if opp_matchup.get('matchup_id') == matchup_id and opp_matchup.get('roster_id') != team_roster_id:
                                opponent_roster_id = opp_matchup.get('roster_id')
                                if opponent_roster_id in roster_lookup:
                                    opp_roster = roster_lookup[opponent_roster_id]
                                    owner_id = opp_roster.get('owner_id')
                                    opponent_name = user_lookup.get(owner_id, 'Unknown')
                                break
                        
                        # Determine game type
                        game_type = "Regular Season"
                        if week > regular_season_weeks:
                            if team_roster_id in playoff_roster_ids and opponent_roster_id in playoff_roster_ids:
                                game_type = "Playoffs"
                            elif team_roster_id in toilet_bowl_roster_ids and opponent_roster_id in toilet_bowl_roster_ids:
                                game_type = "Toilet Bowl"
                            else:
                                game_type = "Consolation"
                        
                        # Get opponent score
                        opponent_points = 0.0
                        for opp_matchup in matchups:
                            if opp_matchup.get('matchup_id') == matchup_id and opp_matchup.get('roster_id') == opponent_roster_id:
                                opponent_points = round(float(opp_matchup.get('points', 0) or 0), 2)
                                break
                        
                        # Determine result
                        if points > opponent_points:
                            result = "W"
                            season_wins += 1
                            team_stats['overall_wins'] += 1
                        elif opponent_points > points:
                            result = "L"
                            season_losses += 1
                            team_stats['overall_losses'] += 1
                        else:
                            result = "T"
                            season_ties += 1
                            team_stats['overall_ties'] += 1
                        
                        # Update stats
                        season_points += points
                        season_games += 1
                        season_scores.append(points)
                        team_stats['total_points'] += points
                        team_stats['total_games'] += 1
                        team_stats['highest_score'] = max(team_stats['highest_score'], points)
                        team_stats['lowest_score'] = min(team_stats['lowest_score'], points)
                        
                        # Track opponent records
                        if opponent_name not in team_stats['opponent_records']:
                            team_stats['opponent_records'][opponent_name] = {
                                'regular_season': {'wins': 0, 'losses': 0, 'ties': 0},
                                'playoffs': {'wins': 0, 'losses': 0, 'ties': 0},
                                'toilet_bowl': {'wins': 0, 'losses': 0, 'ties': 0},
                                'consolation': {'wins': 0, 'losses': 0, 'ties': 0}
                            }
                        
                        if result == "W":
                            team_stats['opponent_records'][opponent_name][game_type.lower().replace(' ', '_')]['wins'] += 1
                        elif result == "L":
                            team_stats['opponent_records'][opponent_name][game_type.lower().replace(' ', '_')]['losses'] += 1
                        else:
                            team_stats['opponent_records'][opponent_name][game_type.lower().replace(' ', '_')]['ties'] += 1
                        
                        # Add to game log
                        team_stats['game_log'].append({
                            'year': season,
                            'week': week,
                            'opponent': opponent_name,
                            'team_score': points,
                            'opponent_score': opponent_points,
                            'result': result,
                            'game_type': game_type
                        })
                except:
                    continue
            
            # Store season stats
            avg_score = season_points / season_games if season_games > 0 else 0
            team_stats['season_stats'].append({
                'year': season,
                'wins': season_wins,
                'losses': season_losses,
                'ties': season_ties,
                'points': round(season_points, 2),
                'avg_score': round(avg_score, 2),
                'games': season_games
            })
        except Exception as e:
            st.warning(f"⚠️ Error loading {season}: {str(e)}")
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    # Fix lowest score if no games played
    if team_stats['lowest_score'] == float('inf'):
        team_stats['lowest_score'] = 0.0
    
    # Display statistics
    display_team_statistics(selected_team, team_stats, available_seasons, SLEEPER_LEAGUE_IDS)


def display_team_statistics(team_name: str, team_stats: Dict, available_seasons: List[int], SLEEPER_LEAGUE_IDS: Dict[int, str]):
    """Display all team statistics in organized sections"""
    
    # Basic Info
    st.markdown("### 📋 Basic Information")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Member Since", team_stats['member_since'])
    with col2:
        win_pct = (team_stats['overall_wins'] / (team_stats['overall_wins'] + team_stats['overall_losses'] + team_stats['overall_ties'])) * 100 if (team_stats['overall_wins'] + team_stats['overall_losses'] + team_stats['overall_ties']) > 0 else 0
        st.metric("Overall Record", f"{team_stats['overall_wins']}-{team_stats['overall_losses']}-{team_stats['overall_ties']} ({win_pct:.1f}%)")
    with col3:
        st.metric("Total Games", team_stats['total_games'])
    
    # Achievements
    st.markdown("### 🏆 Achievements")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Championships", team_stats['championships'])
    with col2:
        st.metric("First Place Seasons", team_stats['first_place_seasons'])
    with col3:
        st.metric("Runner Up (Playoffs)", team_stats['runner_up_playoffs'])
    with col4:
        st.metric("Toilet Bowl Championships", team_stats['toilet_bowl_championships'])
    
    # Playoff Statistics
    st.markdown("### 🎯 Playoff Statistics")
    playoff_total = team_stats['playoff_wins'] + team_stats['playoff_losses']
    playoff_win_pct = (team_stats['playoff_wins'] / playoff_total * 100) if playoff_total > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Playoff Appearances", team_stats['playoff_appearances'])
    with col2:
        st.metric("Playoff Record", f"{team_stats['playoff_wins']}-{team_stats['playoff_losses']}")
    with col3:
        st.metric("Playoff Win %", f"{playoff_win_pct:.1f}%")
    with col4:
        st.metric("Playoff Games", playoff_total)
    
    # Toilet Bowl Statistics
    st.markdown("### 🚽 Toilet Bowl Statistics")
    toilet_bowl_total = team_stats['toilet_bowl_wins'] + team_stats['toilet_bowl_losses']
    toilet_bowl_win_pct = (team_stats['toilet_bowl_wins'] / toilet_bowl_total * 100) if toilet_bowl_total > 0 else 0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Toilet Bowl Appearances", team_stats['toilet_bowl_appearances'])
    with col2:
        st.metric("Toilet Bowl Record", f"{team_stats['toilet_bowl_wins']}-{team_stats['toilet_bowl_losses']}")
    with col3:
        st.metric("Toilet Bowl Win %", f"{toilet_bowl_win_pct:.1f}%")
    with col4:
        st.metric("Toilet Bowl Championships", team_stats['toilet_bowl_championships'])
    with col5:
        st.metric("Toilet Bowl Losers", team_stats['toilet_bowl_losers'])
    
    # Performance History
    st.markdown("### 📊 Performance History")
    avg_score_per_game = team_stats['total_points'] / team_stats['total_games'] if team_stats['total_games'] > 0 else 0
    avg_wins_per_year = team_stats['overall_wins'] / len(team_stats['season_stats']) if team_stats['season_stats'] else 0
    
    # Calculate average point differential (need to get opponent scores from game log)
    total_point_differential = 0.0
    for game in team_stats['game_log']:
        total_point_differential += (game['team_score'] - game['opponent_score'])
    avg_point_differential = total_point_differential / len(team_stats['game_log']) if team_stats['game_log'] else 0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Avg Score Per Game", f"{avg_score_per_game:.2f}")
    with col2:
        st.metric("Highest Score", f"{team_stats['highest_score']:.2f}")
    with col3:
        st.metric("Lowest Score", f"{team_stats['lowest_score']:.2f}")
    with col4:
        st.metric("Avg Wins Per Year", f"{avg_wins_per_year:.2f}")
    with col5:
        st.metric("Avg Point Differential", f"{avg_point_differential:.2f}")
    
    # Scoring Average by Year vs League Average
    if team_stats['season_stats']:
        st.markdown("#### 📈 Scoring Average by Year vs League Average")
        
        # Calculate league average for each year
        league_avg_by_year = {}
        for season in available_seasons:
            league_id = SLEEPER_LEAGUE_IDS[season]
            try:
                league = st.session_state.sleeper_client.get_league(league_id)
                rosters = st.session_state.sleeper_client.get_league_rosters(league_id)
                
                total_league_points = 0.0
                total_league_games = 0
                
                for roster in rosters:
                    settings = roster.get('settings', {})
                    points = settings.get('fpts', 0) + (settings.get('fpts_decimal', 0) / 100)
                    wins = settings.get('wins', 0)
                    losses = settings.get('losses', 0)
                    ties = settings.get('ties', 0)
                    games = wins + losses + ties
                    
                    total_league_points += points
                    total_league_games += games
                
                league_avg = total_league_points / total_league_games if total_league_games > 0 else 0
                league_avg_by_year[season] = league_avg
            except:
                league_avg_by_year[season] = 0
        
        # Create chart data
        chart_data = []
        for season_stat in team_stats['season_stats']:
            year = season_stat['year']
            team_avg = season_stat['avg_score']
            league_avg = league_avg_by_year.get(year, 0)
            
            chart_data.append({
                'Year': year,
                'Team Average': team_avg,
                'League Average': round(league_avg, 2)
            })
        
        chart_df = pd.DataFrame(chart_data)
        chart_df = chart_df.sort_values('Year')
        
        # Create line chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=chart_df['Year'],
            y=chart_df['Team Average'],
            mode='lines+markers',
            name=f'{team_name} Average',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=10)
        ))
        fig.add_trace(go.Scatter(
            x=chart_df['Year'],
            y=chart_df['League Average'],
            mode='lines+markers',
            name='League Average',
            line=dict(color='#ff7f0e', width=3, dash='dash'),
            marker=dict(size=10)
        ))
        
        fig.update_layout(
            title='Scoring Average by Year',
            xaxis_title='Year',
            yaxis_title='Average Points Per Game',
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Opponent Records
    if team_stats['opponent_records']:
        st.markdown("### ⚔️ Head-to-Head Records vs Opponents")
        
        opponent_data = []
        for opponent, records in team_stats['opponent_records'].items():
            reg_season = records['regular_season']
            playoffs = records['playoffs']
            toilet_bowl = records['toilet_bowl']
            consolation = records['consolation']
            
            reg_total = reg_season['wins'] + reg_season['losses'] + reg_season['ties']
            playoff_total = playoffs['wins'] + playoffs['losses'] + playoffs['ties']
            toilet_total = toilet_bowl['wins'] + toilet_bowl['losses'] + toilet_bowl['ties']
            cons_total = consolation['wins'] + consolation['losses'] + consolation['ties']
            
            if reg_total > 0 or playoff_total > 0 or toilet_total > 0 or cons_total > 0:
                opponent_data.append({
                    'Opponent': opponent,
                    'Regular Season': f"{reg_season['wins']}-{reg_season['losses']}-{reg_season['ties']}" if reg_total > 0 else "N/A",
                    'Playoffs': f"{playoffs['wins']}-{playoffs['losses']}-{playoffs['ties']}" if playoff_total > 0 else "N/A",
                    'Toilet Bowl': f"{toilet_bowl['wins']}-{toilet_bowl['losses']}-{toilet_bowl['ties']}" if toilet_total > 0 else "N/A",
                    'Consolation': f"{consolation['wins']}-{consolation['losses']}-{consolation['ties']}" if cons_total > 0 else "N/A"
                })
        
        if opponent_data:
            opponent_df = pd.DataFrame(opponent_data)
            opponent_df = opponent_df.sort_values('Opponent')
            st.dataframe(opponent_df, use_container_width=True, hide_index=True)
    
    # Game Log
    if team_stats['game_log']:
        st.markdown("### 📝 Game Log")
        
        # Sort game log by year (newest first), then week
        game_log_sorted = sorted(team_stats['game_log'], key=lambda x: (x['year'], x['week']), reverse=True)
        
        game_log_df = pd.DataFrame(game_log_sorted)
        game_log_df = game_log_df.rename(columns={
            'year': 'Year',
            'week': 'Week',
            'opponent': 'Opponent',
            'team_score': 'Score',
            'opponent_score': 'Opp Score',
            'result': 'Result',
            'game_type': 'Type'
        })
        
        game_log_df = game_log_df[['Year', 'Week', 'Type', 'Opponent', 'Score', 'Opp Score', 'Result']]
        
        # Highlight wins/losses
        def highlight_result(row):
            styles = [''] * len(row)
            if row['Result'] == 'W':
                styles[6] = 'background-color: #90EE90'  # Light green for wins
            elif row['Result'] == 'L':
                styles[6] = 'background-color: #FFB6C1'  # Light pink for losses
            else:
                styles[6] = 'background-color: #FFE4B5'  # Light yellow for ties
            return styles
        
        st.dataframe(
            game_log_df.style.apply(highlight_result, axis=1),
            use_container_width=True,
            hide_index=True
        )

