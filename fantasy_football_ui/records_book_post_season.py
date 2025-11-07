"""
Post Season Records helper function
"""

import pandas as pd
from datetime import datetime
import streamlit as st
from typing import Dict, List

from fantasy_football_ui.team_name_utils import normalize_team_name


def display_post_season_records(available_seasons: List[int], SLEEPER_LEAGUE_IDS: Dict[int, str]):
    """Display post season records"""
    st.subheader("🏆 Post Season Records")
    
    # Collect post season data
    team_post_season_stats = {}  # {team: {titles, runner_ups, appearances, wins, losses, total_points, games}}
    all_playoff_matchups = []  # List of all playoff matchups
    championship_matchups = []  # List of championship matchups
    all_player_post_season_stats = {}  # {(year, team, player_id, position): {player_name, total_points, games_started}}
    
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
        status_text.text(f"Loading post season data for {season}...")
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
            
            # Get playoff bracket
            winners_bracket = None
            playoff_roster_ids = set()
            
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
            
            if not winners_bracket or not isinstance(winners_bracket, list):
                continue
            
            # Determine champion and runner-up
            max_round = max([m.get('r', 0) for m in winners_bracket if isinstance(m, dict)], default=0)
            championship_matchups_list = [m for m in winners_bracket if isinstance(m, dict) and m.get('r') == max_round]
            
            champion = None
            runner_up = None
            
            for matchup in championship_matchups_list:
                winner_id = matchup.get('w')
                loser_id = matchup.get('l')
                
                if winner_id:
                    winner_roster = next((r for r in rosters if r.get('roster_id') == winner_id), None)
                    if winner_roster:
                        owner_id = winner_roster.get('owner_id')
                        champion = user_lookup.get(owner_id, 'Unknown')
                
                if loser_id:
                    loser_roster = next((r for r in rosters if r.get('roster_id') == loser_id), None)
                    if loser_roster:
                        owner_id = loser_roster.get('owner_id')
                        runner_up = user_lookup.get(owner_id, 'Unknown')
            
            # Update team stats for champion and runner-up
            if champion:
                if champion not in team_post_season_stats:
                    team_post_season_stats[champion] = {
                        'titles': 0,
                        'runner_ups': 0,
                        'appearances': 0,
                        'wins': 0,
                        'losses': 0,
                        'total_points': 0.0,
                        'games': 0
                    }
                team_post_season_stats[champion]['titles'] += 1
            
            if runner_up:
                if runner_up not in team_post_season_stats:
                    team_post_season_stats[runner_up] = {
                        'titles': 0,
                        'runner_ups': 0,
                        'appearances': 0,
                        'wins': 0,
                        'losses': 0,
                        'total_points': 0.0,
                        'games': 0
                    }
                team_post_season_stats[runner_up]['runner_ups'] += 1
            
            # Mark playoff appearances
            for roster_id in playoff_roster_ids:
                roster = next((r for r in rosters if r.get('roster_id') == roster_id), None)
                if roster:
                    owner_id = roster.get('owner_id')
                    team_name = user_lookup.get(owner_id, 'Unknown')
                    if team_name not in team_post_season_stats:
                        team_post_season_stats[team_name] = {
                            'titles': 0,
                            'runner_ups': 0,
                            'appearances': 0,
                            'wins': 0,
                            'losses': 0,
                            'total_points': 0.0,
                            'games': 0
                        }
                    team_post_season_stats[team_name]['appearances'] += 1
            
            # Get player data for position lookup
            players = {}
            try:
                players = st.session_state.sleeper_client.get_players("nfl")
            except:
                pass
            
            # Process playoff weeks (15-17)
            max_week = 17
            if season == current_year and current_week:
                max_week = min(current_week - 1, 17)  # Only completed weeks
            
            # Track player stats by position for this season
            player_stats_by_key = {}  # {(team, player_id, position): {player_name, total_points, games_started}}
            
            for week in range(regular_season_weeks + 1, max_week + 1):
                try:
                    matchups = st.session_state.sleeper_client.get_league_matchups(league_id, week)
                    
                    # Group matchups by matchup_id
                    matchup_pairs = {}
                    for matchup in matchups:
                        matchup_id = matchup.get('matchup_id')
                        roster_id = matchup.get('roster_id')
                        points = matchup.get('points', 0) or 0
                        
                        # Only process playoff teams
                        if roster_id not in playoff_roster_ids:
                            continue
                        
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
                            'roster_id': roster_id,
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
                                # Update team stats
                                for team_data in teams:
                                    team_name = team_data['team']
                                    if team_name not in team_post_season_stats:
                                        team_post_season_stats[team_name] = {
                                            'titles': 0,
                                            'runner_ups': 0,
                                            'appearances': 0,
                                            'wins': 0,
                                            'losses': 0,
                                            'total_points': 0.0,
                                            'games': 0
                                        }
                                    
                                    team_post_season_stats[team_name]['total_points'] += team_data['score']
                                    team_post_season_stats[team_name]['games'] += 1
                                
                                # Determine winner/loser
                                if team1['score'] > team2['score']:
                                    team_post_season_stats[team1['team']]['wins'] += 1
                                    team_post_season_stats[team2['team']]['losses'] += 1
                                    winner = team1['team']
                                    loser = team2['team']
                                elif team2['score'] > team1['score']:
                                    team_post_season_stats[team2['team']]['wins'] += 1
                                    team_post_season_stats[team1['team']]['losses'] += 1
                                    winner = team2['team']
                                    loser = team1['team']
                                else:
                                    winner = None
                                    loser = None
                                
                                # Check if this is a championship matchup
                                is_championship = False
                                for champ_matchup in championship_matchups_list:
                                    if (team1['roster_id'] in [champ_matchup.get('t1'), champ_matchup.get('t2')] and
                                        team2['roster_id'] in [champ_matchup.get('t1'), champ_matchup.get('t2')]):
                                        is_championship = True
                                        break
                                
                                all_playoff_matchups.append({
                                    'year': season,
                                    'week': week,
                                    'team1': team1['team'],
                                    'team1_score': team1['score'],
                                    'team2': team2['team'],
                                    'team2_score': team2['score'],
                                    'winner': winner,
                                    'loser': loser,
                                    'is_championship': is_championship
                                })
                                
                                if is_championship:
                                    championship_matchups.append({
                                        'year': season,
                                        'week': week,
                                        'team1': team1['team'],
                                        'team1_score': team1['score'],
                                        'team2': team2['team'],
                                        'team2_score': team2['score'],
                                        'winner': winner,
                                        'loser': loser
                                    })
                    
                    # Process player stats from matchups (only starters)
                    for matchup in matchups:
                        roster_id = matchup.get('roster_id')
                        if roster_id not in playoff_roster_ids:
                            continue
                        
                        starters = matchup.get('starters', [])
                        players_points = matchup.get('players_points', {})
                        
                        # Get team name
                        team_name = 'Unknown'
                        if roster_id in roster_lookup:
                            roster = roster_lookup[roster_id]
                            owner_id = roster.get('owner_id')
                            if owner_id in user_lookup:
                                team_name = user_lookup[owner_id]
                        
                        # Process each starter
                        for player_id in starters:
                            if not player_id:
                                continue
                            
                            player_id_str = str(player_id)
                            points = players_points.get(player_id_str) or players_points.get(player_id) or 0
                            points = float(points) if points else 0.0
                            
                            # Get player info
                            player_data = players.get(player_id_str) or players.get(player_id)
                            position = None
                            player_name = f"Player {player_id_str}"
                            
                            if player_data:
                                position = player_data.get('position', '')
                                full_name = player_data.get('full_name', '')
                                if not full_name:
                                    first = player_data.get('first_name', '')
                                    last = player_data.get('last_name', '')
                                    full_name = f"{first} {last}".strip()
                                if full_name:
                                    player_name = full_name
                            else:
                                # Check if it's a DST (team abbreviation like "IND", "CHI")
                                if len(player_id_str) == 3 and player_id_str.isalpha() and player_id_str.isupper():
                                    position = 'DEF'
                                    player_name = f"{player_id_str} DST"
                            
                            # Only process if we have a valid position
                            if position and position in ['QB', 'RB', 'WR', 'TE', 'DEF', 'K']:
                                key = (season, team_name, player_id_str, position)
                                
                                if key not in player_stats_by_key:
                                    player_stats_by_key[key] = {
                                        'player_name': player_name,
                                        'total_points': 0.0,
                                        'games_started': 0
                                    }
                                
                                player_stats_by_key[key]['total_points'] += points
                                player_stats_by_key[key]['games_started'] += 1
                except:
                    continue
            
            # Store player stats for this season
            for (season_year, team_name, player_id, position), stats in player_stats_by_key.items():
                if stats['games_started'] > 0:
                    key = (season_year, team_name, player_id, position)
                    all_player_post_season_stats[key] = {
                        'year': season_year,
                        'team': team_name,
                        'player': stats['player_name'],
                        'position': position,
                        'total_points': round(stats['total_points'], 2),
                        'games_started': stats['games_started']
                    }
        except Exception as e:
            st.warning(f"⚠️ Error loading {season}: {str(e)}")
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    if not team_post_season_stats and not all_playoff_matchups:
        st.info("No post season data available.")
        return
    
    # Display team records
    st.markdown("### 🏆 Team Records")
    
    # Convert team stats to list
    team_stats_list = []
    for team, stats in team_post_season_stats.items():
        win_pct = (stats['wins'] / (stats['wins'] + stats['losses'])) * 100 if (stats['wins'] + stats['losses']) > 0 else 0
        team_stats_list.append({
            'team': team,
            'titles': stats['titles'],
            'runner_ups': stats['runner_ups'],
            'appearances': stats['appearances'],
            'wins': stats['wins'],
            'losses': stats['losses'],
            'win_pct': win_pct,
            'total_points': stats['total_points'],
            'games': stats['games']
        })
    
    # 1. Most Titles
    st.markdown("#### 🥇 Top 5 Most Titles")
    most_titles = sorted(team_stats_list, key=lambda x: x['titles'], reverse=True)[:5]
    if most_titles:
        titles_df = pd.DataFrame(most_titles)
        titles_df['Rank'] = range(1, len(titles_df) + 1)
        titles_df = titles_df[['Rank', 'team', 'titles']]
        titles_df = titles_df.rename(columns={'team': 'Team', 'titles': 'Titles'})
        st.dataframe(titles_df, use_container_width=True, hide_index=True)
    
    # 2. Most Runner Ups
    st.markdown("#### 🥈 Top 5 Most Runner Ups")
    most_runner_ups = sorted(team_stats_list, key=lambda x: x['runner_ups'], reverse=True)[:5]
    if most_runner_ups:
        runner_ups_df = pd.DataFrame(most_runner_ups)
        runner_ups_df['Rank'] = range(1, len(runner_ups_df) + 1)
        runner_ups_df = runner_ups_df[['Rank', 'team', 'runner_ups']]
        runner_ups_df = runner_ups_df.rename(columns={'team': 'Team', 'runner_ups': 'Runner Ups'})
        st.dataframe(runner_ups_df, use_container_width=True, hide_index=True)
    
    # 3. Most Playoff Appearances
    st.markdown("#### 🎯 Top 5 Most Playoff Appearances")
    most_appearances = sorted(team_stats_list, key=lambda x: x['appearances'], reverse=True)[:5]
    if most_appearances:
        appearances_df = pd.DataFrame(most_appearances)
        appearances_df['Rank'] = range(1, len(appearances_df) + 1)
        appearances_df = appearances_df[['Rank', 'team', 'appearances']]
        appearances_df = appearances_df.rename(columns={'team': 'Team', 'appearances': 'Appearances'})
        st.dataframe(appearances_df, use_container_width=True, hide_index=True)
    
    # 4. Most Wins
    st.markdown("#### 💪 Top 5 Most Playoff Wins")
    most_wins = sorted(team_stats_list, key=lambda x: x['wins'], reverse=True)[:5]
    if most_wins:
        wins_df = pd.DataFrame(most_wins)
        wins_df['Rank'] = range(1, len(wins_df) + 1)
        wins_df = wins_df[['Rank', 'team', 'wins']]
        wins_df = wins_df.rename(columns={'team': 'Team', 'wins': 'Wins'})
        st.dataframe(wins_df, use_container_width=True, hide_index=True)
    
    # 5. Best Win %
    st.markdown("#### 📈 Top 5 Best Playoff Win % (Min 3 Games)")
    best_win_pct = [t for t in team_stats_list if (t['wins'] + t['losses']) >= 3]
    best_win_pct = sorted(best_win_pct, key=lambda x: x['win_pct'], reverse=True)[:5]
    if best_win_pct:
        win_pct_df = pd.DataFrame(best_win_pct)
        win_pct_df['Rank'] = range(1, len(win_pct_df) + 1)
        win_pct_df = win_pct_df[['Rank', 'team', 'win_pct']]
        win_pct_df = win_pct_df.rename(columns={'team': 'Team', 'win_pct': 'Win %'})
        win_pct_df['Win %'] = win_pct_df['Win %'].round(1)
        st.dataframe(win_pct_df, use_container_width=True, hide_index=True)
    
    # 6. Worst Win %
    st.markdown("#### 📉 Top 5 Worst Playoff Win % (Min 3 Games)")
    worst_win_pct = [t for t in team_stats_list if (t['wins'] + t['losses']) >= 3]
    worst_win_pct = sorted(worst_win_pct, key=lambda x: x['win_pct'], reverse=False)[:5]
    if worst_win_pct:
        worst_pct_df = pd.DataFrame(worst_win_pct)
        worst_pct_df['Rank'] = range(1, len(worst_pct_df) + 1)
        worst_pct_df = worst_pct_df[['Rank', 'team', 'win_pct']]
        worst_pct_df = worst_pct_df.rename(columns={'team': 'Team', 'win_pct': 'Win %'})
        worst_pct_df['Win %'] = worst_pct_df['Win %'].round(1)
        st.dataframe(worst_pct_df, use_container_width=True, hide_index=True)
    
    # Game Records
    st.markdown("### 🎮 Game Records")
    
    # 7. Biggest Blowout
    st.markdown("#### 💥 Top 5 Biggest Blowout")
    blowouts = []
    for matchup in all_playoff_matchups:
        if matchup['winner']:
            winner_score = matchup['team1_score'] if matchup['winner'] == matchup['team1'] else matchup['team2_score']
            loser_score = matchup['team2_score'] if matchup['winner'] == matchup['team1'] else matchup['team1_score']
            differential = winner_score - loser_score
            blowouts.append({
                'year': matchup['year'],
                'week': matchup['week'],
                'winner': matchup['winner'],
                'winner_score': winner_score,
                'loser': matchup['loser'],
                'loser_score': loser_score,
                'differential': differential
            })
    
    if blowouts:
        biggest_blowouts = sorted(blowouts, key=lambda x: x['differential'], reverse=True)[:5]
        blowout_df = pd.DataFrame(biggest_blowouts)
        blowout_df['Rank'] = range(1, len(blowout_df) + 1)
        blowout_df = blowout_df[['Rank', 'year', 'week', 'winner', 'winner_score', 'loser', 'loser_score', 'differential']]
        blowout_df = blowout_df.rename(columns={
            'year': 'Year',
            'week': 'Week',
            'winner': 'Winner',
            'winner_score': 'Winner Score',
            'loser': 'Loser',
            'loser_score': 'Loser Score',
            'differential': 'Differential'
        })
        blowout_df['Differential'] = blowout_df['Differential'].round(2)
        st.dataframe(blowout_df, use_container_width=True, hide_index=True)
    
    # 8. Smallest Victory
    st.markdown("#### 🎯 Top 5 Smallest Victory")
    if blowouts:
        smallest_victories = sorted(blowouts, key=lambda x: x['differential'], reverse=False)[:5]
        victory_df = pd.DataFrame(smallest_victories)
        victory_df['Rank'] = range(1, len(victory_df) + 1)
        victory_df = victory_df[['Rank', 'year', 'week', 'winner', 'winner_score', 'loser', 'loser_score', 'differential']]
        victory_df = victory_df.rename(columns={
            'year': 'Year',
            'week': 'Week',
            'winner': 'Winner',
            'winner_score': 'Winner Score',
            'loser': 'Loser',
            'loser_score': 'Loser Score',
            'differential': 'Differential'
        })
        victory_df['Differential'] = victory_df['Differential'].round(2)
        st.dataframe(victory_df, use_container_width=True, hide_index=True)
    
    # 9. Most Combined Points
    st.markdown("#### 🔥 Top 5 Most Combined Points")
    combined_points = []
    for matchup in all_playoff_matchups:
        combined = matchup['team1_score'] + matchup['team2_score']
        if combined > 0:
            combined_points.append({
                'year': matchup['year'],
                'week': matchup['week'],
                'team1': matchup['team1'],
                'team1_score': matchup['team1_score'],
                'team2': matchup['team2'],
                'team2_score': matchup['team2_score'],
                'combined': combined
            })
    
    if combined_points:
        most_combined = sorted(combined_points, key=lambda x: x['combined'], reverse=True)[:5]
        combined_df = pd.DataFrame(most_combined)
        combined_df['Rank'] = range(1, len(combined_df) + 1)
        combined_df = combined_df[['Rank', 'year', 'week', 'team1', 'team1_score', 'team2', 'team2_score', 'combined']]
        combined_df = combined_df.rename(columns={
            'year': 'Year',
            'week': 'Week',
            'team1': 'Team 1',
            'team1_score': 'Team 1 Score',
            'team2': 'Team 2',
            'team2_score': 'Team 2 Score',
            'combined': 'Combined'
        })
        combined_df['Combined'] = combined_df['Combined'].round(2)
        st.dataframe(combined_df, use_container_width=True, hide_index=True)
    
    # 10. Least Combined Points
    st.markdown("#### 🥶 Top 5 Least Combined Points")
    if combined_points:
        least_combined = sorted(combined_points, key=lambda x: x['combined'], reverse=False)[:5]
        least_df = pd.DataFrame(least_combined)
        least_df['Rank'] = range(1, len(least_df) + 1)
        least_df = least_df[['Rank', 'year', 'week', 'team1', 'team1_score', 'team2', 'team2_score', 'combined']]
        least_df = least_df.rename(columns={
            'year': 'Year',
            'week': 'Week',
            'team1': 'Team 1',
            'team1_score': 'Team 1 Score',
            'team2': 'Team 2',
            'team2_score': 'Team 2 Score',
            'combined': 'Combined'
        })
        least_df['Combined'] = least_df['Combined'].round(2)
        st.dataframe(least_df, use_container_width=True, hide_index=True)
    
    # 11. Highest Score in a Championship Victory
    st.markdown("#### 🏆 Top 5 Highest Score in a Championship Victory")
    championship_victories = []
    for matchup in championship_matchups:
        if matchup['winner']:
            winner_score = matchup['team1_score'] if matchup['winner'] == matchup['team1'] else matchup['team2_score']
            loser_score = matchup['team2_score'] if matchup['winner'] == matchup['team1'] else matchup['team1_score']
            championship_victories.append({
                'year': matchup['year'],
                'week': matchup['week'],
                'winner': matchup['winner'],
                'winner_score': winner_score,
                'loser': matchup['loser'],
                'loser_score': loser_score
            })
    
    if championship_victories:
        highest_champ = sorted(championship_victories, key=lambda x: x['winner_score'], reverse=True)[:5]
        champ_df = pd.DataFrame(highest_champ)
        champ_df['Rank'] = range(1, len(champ_df) + 1)
        champ_df = champ_df[['Rank', 'year', 'week', 'winner', 'winner_score', 'loser', 'loser_score']]
        champ_df = champ_df.rename(columns={
            'year': 'Year',
            'week': 'Week',
            'winner': 'Winner',
            'winner_score': 'Winner Score',
            'loser': 'Loser',
            'loser_score': 'Loser Score'
        })
        champ_df['Winner Score'] = champ_df['Winner Score'].round(2)
        champ_df['Loser Score'] = champ_df['Loser Score'].round(2)
        st.dataframe(champ_df, use_container_width=True, hide_index=True)
    
    # 12. Lowest Score in a Championship Victory
    st.markdown("#### 📉 Top 5 Lowest Score in a Championship Victory")
    if championship_victories:
        lowest_champ = sorted(championship_victories, key=lambda x: x['winner_score'], reverse=False)[:5]
        low_champ_df = pd.DataFrame(lowest_champ)
        low_champ_df['Rank'] = range(1, len(low_champ_df) + 1)
        low_champ_df = low_champ_df[['Rank', 'year', 'week', 'winner', 'winner_score', 'loser', 'loser_score']]
        low_champ_df = low_champ_df.rename(columns={
            'year': 'Year',
            'week': 'Week',
            'winner': 'Winner',
            'winner_score': 'Winner Score',
            'loser': 'Loser',
            'loser_score': 'Loser Score'
        })
        low_champ_df['Winner Score'] = low_champ_df['Winner Score'].round(2)
        low_champ_df['Loser Score'] = low_champ_df['Loser Score'].round(2)
        st.dataframe(low_champ_df, use_container_width=True, hide_index=True)
    
    # Player Statistics
    st.markdown("---")
    st.markdown("### 👤 Player Statistics (Post Season)")
    st.markdown("**Only includes players who were in the starting lineup**")
    
    if not all_player_post_season_stats:
        st.info("No player statistics available.")
        return
    
    player_stats_list = list(all_player_post_season_stats.values())
    positions = ['QB', 'RB', 'WR', 'TE', 'DEF', 'K']
    
    # Most points by position in a single post season
    for position in positions:
        position_players = [p for p in player_stats_list if p['position'] == position]
        
        if not position_players:
            continue
        
        st.markdown(f"#### {position} - Most Points in a Single Post Season")
        highest_position = sorted(position_players, key=lambda x: x['total_points'], reverse=True)[:5]
        highest_df = pd.DataFrame(highest_position)
        highest_df['Rank'] = range(1, len(highest_df) + 1)
        highest_df = highest_df[['Rank', 'year', 'team', 'player', 'total_points']]
        highest_df = highest_df.rename(columns={
            'year': 'Year',
            'team': 'Team',
            'player': 'Player',
            'total_points': 'Total Points'
        })
        st.dataframe(highest_df, use_container_width=True, hide_index=True)
    
    # Most combined points per position (sum of all players at that position for a team in a season)
    # Exclude QB from combined points
    st.markdown("#### Most Combined Points by Position (Team Total)")
    
    # Group by year, team, position and track players
    position_totals = {}  # {(year, team, position): {total_points, players: [(name, points)]}}
    
    for player_stat in player_stats_list:
        key = (player_stat['year'], player_stat['team'], player_stat['position'])
        if key not in position_totals:
            position_totals[key] = {
                'total_points': 0.0,
                'players': []
            }
        position_totals[key]['total_points'] += player_stat['total_points']
        position_totals[key]['players'].append({
            'name': player_stat['player'],
            'points': player_stat['total_points']
        })
    
    # Exclude QB from combined points
    positions_for_combined = [p for p in positions if p != 'QB']
    
    for position in positions_for_combined:
        position_combined = []
        for (year, team, pos), data in position_totals.items():
            if pos == position:
                # Format players list as "Player1 (pts), Player2 (pts)"
                players_str = ", ".join([f"{p['name']} ({p['points']:.1f})" for p in data['players']])
                position_combined.append({
                    'year': year,
                    'team': team,
                    'position': position,
                    'total_points': round(data['total_points'], 2),
                    'players': players_str
                })
        
        if position_combined:
            st.markdown(f"**{position}**")
            highest_combined = sorted(position_combined, key=lambda x: x['total_points'], reverse=True)[:5]
            combined_df = pd.DataFrame(highest_combined)
            combined_df['Rank'] = range(1, len(combined_df) + 1)
            combined_df = combined_df[['Rank', 'year', 'team', 'total_points', 'players']]
            combined_df = combined_df.rename(columns={
                'year': 'Year',
                'team': 'Team',
                'total_points': 'Total Points',
                'players': 'Players'
            })
            st.dataframe(combined_df, use_container_width=True, hide_index=True)

