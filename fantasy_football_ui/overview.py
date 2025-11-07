"""
Overview view helper functions for displaying league-wide statistics across all years
"""

import pandas as pd
from datetime import datetime
import streamlit as st
from typing import Dict, List

from fantasy_football_ui.team_name_utils import normalize_team_name

def display_overview():
    """Display league overview with aggregated statistics across all years"""
    st.header("📊 League Overview")
    st.markdown("**All-time statistics across all seasons**")
    
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
    
    # Initialize aggregated stats
    team_stats = {}  # team_name -> {wins, losses, championships, first_place_seasons, playoff_appearances, toilet_bowl_appearances}
    
    st.info(f"📈 Loading data from {len(available_seasons)} seasons: {available_seasons}")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, season in enumerate(available_seasons):
        league_id = SLEEPER_LEAGUE_IDS[season]
        status_text.text(f"Loading {season}...")
        progress_bar.progress((idx + 1) / len(available_seasons))
        
        try:
            # Get league data
            league = st.session_state.sleeper_client.get_league(league_id)
            rosters = st.session_state.sleeper_client.get_league_rosters(league_id)
            users = st.session_state.sleeper_client.get_league_users(league_id)
            
            # Create user lookup
            user_lookup = {user.get('user_id'): normalize_team_name(user.get('display_name') or user.get('username', 'Unknown')) for user in users}
            
            # Get standings (regular season)
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
                    'points': points,
                    'season': season
                })
            
            # Sort by wins, then points to determine regular season finish
            standings.sort(key=lambda x: (x['wins'], x['points']), reverse=True)
            
            # Get playoff brackets
            winners_bracket = None
            losers_bracket = None
            try:
                winners_bracket = st.session_state.sleeper_client.get_league_playoff_bracket(league_id)
            except:
                pass
            
            try:
                losers_bracket = st.session_state.sleeper_client.get_league_consolation_bracket(league_id)
            except:
                pass
            
            # Get playoff seeds (top 8 teams make playoffs)
            playoff_teams = set()
            for i, team in enumerate(standings[:8], 1):
                playoff_teams.add(team['team_name'])
            
            # Get toilet bowl teams (seeds 9-12)
            from fantasy_football_ui.bracket_visualizer import get_playoff_seeds
            seed_map = get_playoff_seeds(rosters, user_lookup)
            toilet_bowl_teams = set()
            for roster in rosters:
                roster_id = roster.get('roster_id')
                seed = seed_map.get(roster_id, 0)
                if 9 <= seed <= 12:
                    owner_id = roster.get('owner_id')
                    team_name = user_lookup.get(owner_id, 'Unknown')
                    toilet_bowl_teams.add(team_name)
            
            # Determine champion and runner-up
            champion = None
            runner_up = None
            if winners_bracket and isinstance(winners_bracket, list):
                # Find final round matchup
                max_round = max((m.get('r', 0) for m in winners_bracket if isinstance(m, dict)), default=0)
                if max_round > 0:
                    final_matchups = [m for m in winners_bracket if isinstance(m, dict) and m.get('r') == max_round]
                    if final_matchups:
                        final_matchup = final_matchups[0]
                        winner_id = final_matchup.get('w')
                        if winner_id:
                            winner_roster = next((r for r in rosters if r.get('roster_id') == winner_id), None)
                            if winner_roster:
                                owner_id = winner_roster.get('owner_id')
                                champion = user_lookup.get(owner_id, 'Unknown')
                        
                        # Runner-up is the loser of the final
                        loser_id = final_matchup.get('l')
                        if loser_id:
                            loser_roster = next((r for r in rosters if r.get('roster_id') == loser_id), None)
                            if loser_roster:
                                owner_id = loser_roster.get('owner_id')
                                runner_up = user_lookup.get(owner_id, 'Unknown')
            
            # Determine first place (regular season winner)
            first_place = standings[0]['team_name'] if standings else None
            
            # Count playoff wins for all teams (do this once, not per team)
            playoff_wins_by_team = {}
            if winners_bracket and isinstance(winners_bracket, list):
                roster_id_to_team = {}
                for roster in rosters:
                    roster_id = roster.get('roster_id')
                    owner_id = roster.get('owner_id')
                    roster_team_name = user_lookup.get(owner_id, 'Unknown')
                    roster_id_to_team[roster_id] = roster_team_name
                
                # Count wins in winners bracket for each team
                for matchup in winners_bracket:
                    if isinstance(matchup, dict):
                        winner_id = matchup.get('w')
                        if winner_id:
                            winner_team = roster_id_to_team.get(winner_id)
                            if winner_team:
                                playoff_wins_by_team[winner_team] = playoff_wins_by_team.get(winner_team, 0) + 1
            
            # Update team stats
            for team_standings in standings:
                team_name = team_standings['team_name']
                
                if team_name not in team_stats:
                    team_stats[team_name] = {
                        'total_wins': 0,
                        'total_losses': 0,
                        'total_ties': 0,
                        'championships': 0,
                        'first_place_seasons': 0,
                        'playoff_appearances': 0,
                        'playoff_wins': 0,
                        'toilet_bowl_appearances': 0,
                        'seasons': []
                    }
                
                team_stats[team_name]['total_wins'] += team_standings['wins']
                team_stats[team_name]['total_losses'] += team_standings['losses']
                team_stats[team_name]['total_ties'] += team_standings['ties']
                team_stats[team_name]['seasons'].append(season)
                
                # Check for first place (team with highest wins and points)
                if team_standings['team_name'] == standings[0]['team_name']:
                    team_stats[team_name]['first_place_seasons'] += 1
                
                # Check for playoff appearance
                if team_name in playoff_teams:
                    team_stats[team_name]['playoff_appearances'] += 1
                
                # Add playoff wins for this season
                if team_name in playoff_wins_by_team:
                    team_stats[team_name]['playoff_wins'] += playoff_wins_by_team[team_name]
                
                # Check for toilet bowl appearance
                if team_name in toilet_bowl_teams:
                    team_stats[team_name]['toilet_bowl_appearances'] += 1
            
            # Check for championship
            if champion:
                if champion not in team_stats:
                    team_stats[champion] = {
                        'total_wins': 0,
                        'total_losses': 0,
                        'total_ties': 0,
                        'championships': 0,
                        'first_place_seasons': 0,
                        'playoff_appearances': 0,
                        'playoff_wins': 0,
                        'toilet_bowl_appearances': 0,
                        'seasons': []
                    }
                team_stats[champion]['championships'] += 1
                # Make sure champion gets playoff wins if they weren't in standings loop
                if champion in playoff_wins_by_team and champion not in [s['team_name'] for s in standings]:
                    team_stats[champion]['playoff_wins'] += playoff_wins_by_team[champion]
        
        except Exception as e:
            st.warning(f"⚠️ Error loading {season}: {str(e)}")
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    if not team_stats:
        st.error("No data available for any seasons.")
        return
    
    # Calculate win percentages
    for team_name in team_stats:
        total_games = team_stats[team_name]['total_wins'] + team_stats[team_name]['total_losses'] + team_stats[team_name]['total_ties']
        if total_games > 0:
            team_stats[team_name]['win_pct'] = team_stats[team_name]['total_wins'] / total_games
        else:
            team_stats[team_name]['win_pct'] = 0.0
    
    # Create DataFrames for each metric
    st.markdown("---")
    
    # Most Wins
    st.subheader("🏆 Most Wins (All-Time)")
    wins_data = []
    for team_name, stats in team_stats.items():
        wins_data.append({
            'Team': team_name,
            'Wins': stats['total_wins'],
            'Losses': stats['total_losses'],
            'Ties': stats['total_ties'],
            'Win %': f"{stats['win_pct']:.3f}",
            'Seasons': len(stats['seasons'])
        })
    wins_df = pd.DataFrame(wins_data)
    wins_df = wins_df.sort_values('Wins', ascending=False)
    st.dataframe(wins_df, use_container_width=True, hide_index=True)
    
    # Best Win Percentage
    st.subheader("📈 Best Win Percentage (All-Time)")
    win_pct_data = []
    for team_name, stats in team_stats.items():
        total_games = stats['total_wins'] + stats['total_losses'] + stats['total_ties']
        if total_games >= 10:  # Only show teams with at least 10 games
            win_pct_data.append({
                'Team': team_name,
                'Win %': f"{stats['win_pct']:.3f}",
                'Wins': stats['total_wins'],
                'Losses': stats['total_losses'],
                'Ties': stats['total_ties'],
                'Total Games': total_games
            })
    if win_pct_data:
        win_pct_df = pd.DataFrame(win_pct_data)
        win_pct_df = win_pct_df.sort_values('Win %', ascending=False)
        st.dataframe(win_pct_df, use_container_width=True, hide_index=True)
    else:
        st.info("Not enough data to calculate win percentages.")
    
    # Most Championships
    st.subheader("👑 Most Championships")
    championships_data = []
    for team_name, stats in team_stats.items():
        if stats['championships'] > 0:
            championships_data.append({
                'Team': team_name,
                'Championships': stats['championships'],
                'Seasons Active': len(stats['seasons'])
            })
    if championships_data:
        championships_df = pd.DataFrame(championships_data)
        championships_df = championships_df.sort_values('Championships', ascending=False)
        st.dataframe(championships_df, use_container_width=True, hide_index=True)
    else:
        st.info("No championship data available.")
    
    # Most First Place Seasons
    st.subheader("🥇 Most First Place Seasons (Regular Season)")
    first_place_data = []
    for team_name, stats in team_stats.items():
        if stats['first_place_seasons'] > 0:
            first_place_data.append({
                'Team': team_name,
                'First Place Seasons': stats['first_place_seasons'],
                'Seasons Active': len(stats['seasons'])
            })
    if first_place_data:
        first_place_df = pd.DataFrame(first_place_data)
        first_place_df = first_place_df.sort_values('First Place Seasons', ascending=False)
        st.dataframe(first_place_df, use_container_width=True, hide_index=True)
    else:
        st.info("No first place season data available.")
    
    # Most Playoff Appearances
    st.subheader("🎯 Most Playoff Appearances")
    playoff_data = []
    for team_name, stats in team_stats.items():
        if stats['playoff_appearances'] > 0:
            playoff_data.append({
                'Team': team_name,
                'Playoff Appearances': stats['playoff_appearances'],
                'Seasons Active': len(stats['seasons']),
                'Appearance Rate': f"{stats['playoff_appearances'] / len(stats['seasons']):.1%}" if stats['seasons'] else "0%"
            })
    if playoff_data:
        playoff_df = pd.DataFrame(playoff_data)
        playoff_df = playoff_df.sort_values('Playoff Appearances', ascending=False)
        st.dataframe(playoff_df, use_container_width=True, hide_index=True)
    else:
        st.info("No playoff data available.")
    
    # Most Playoff Wins
    st.subheader("🏆 Most Playoff Wins")
    playoff_wins_data = []
    for team_name, stats in team_stats.items():
        if stats['playoff_wins'] > 0:
            playoff_wins_data.append({
                'Team': team_name,
                'Playoff Wins': stats['playoff_wins'],
                'Playoff Appearances': stats['playoff_appearances'],
                'Win Rate': f"{stats['playoff_wins'] / stats['playoff_appearances']:.1%}" if stats['playoff_appearances'] > 0 else "0%",
                'Championships': stats['championships']
            })
    if playoff_wins_data:
        playoff_wins_df = pd.DataFrame(playoff_wins_data)
        playoff_wins_df = playoff_wins_df.sort_values('Playoff Wins', ascending=False)
        st.dataframe(playoff_wins_df, use_container_width=True, hide_index=True)
    else:
        st.info("No playoff wins data available.")
    
    # Most Toilet Bowl Appearances
    st.subheader("🚽 Most Toilet Bowl Appearances")
    toilet_bowl_data = []
    for team_name, stats in team_stats.items():
        if stats['toilet_bowl_appearances'] > 0:
            toilet_bowl_data.append({
                'Team': team_name,
                'Toilet Bowl Appearances': stats['toilet_bowl_appearances'],
                'Seasons Active': len(stats['seasons']),
                'Appearance Rate': f"{stats['toilet_bowl_appearances'] / len(stats['seasons']):.1%}" if stats['seasons'] else "0%"
            })
    if toilet_bowl_data:
        toilet_bowl_df = pd.DataFrame(toilet_bowl_data)
        toilet_bowl_df = toilet_bowl_df.sort_values('Toilet Bowl Appearances', ascending=False)
        st.dataframe(toilet_bowl_df, use_container_width=True, hide_index=True)
    else:
        st.info("No toilet bowl data available.")
    
    # Summary Statistics
    st.markdown("---")
    st.subheader("📊 Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_teams = len(team_stats)
        st.metric("Total Teams", total_teams)
    
    with col2:
        total_seasons = len(available_seasons)
        st.metric("Total Seasons", total_seasons)
    
    with col3:
        total_championships = sum(stats['championships'] for stats in team_stats.values())
        st.metric("Total Championships", total_championships)
    
    with col4:
        total_playoff_appearances = sum(stats['playoff_appearances'] for stats in team_stats.values())
        st.metric("Total Playoff Appearances", total_playoff_appearances)
    

