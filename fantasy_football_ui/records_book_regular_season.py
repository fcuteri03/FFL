"""
Regular Season Records helper function
"""

import pandas as pd
from datetime import datetime
import streamlit as st
from typing import Dict, List

from fantasy_football_ui.team_name_utils import normalize_team_name


def display_regular_season_records(available_seasons: List[int], SLEEPER_LEAGUE_IDS: Dict[int, str]):
    """Display regular season records"""
    st.subheader("📅 Regular Season Records")
    
    # Collect regular season data for each team per season
    team_season_stats = {}  # {(year, team): {games, total_points, wins, losses, ties, margins, weekly_scores, win_streak, loss_streak, games_over_150}}
    
    # Collect player stats by position for regular season
    player_season_stats = {}  # {(year, team, player_id, position): {player_name, total_points, games_started, avg_per_game}}
    
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
        status_text.text(f"Loading regular season data for {season}...")
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
            
            # Get player data for position lookup
            players = {}
            try:
                players = st.session_state.sleeper_client.get_players("nfl")
            except:
                pass
            
            # Determine max week to fetch (only completed regular season weeks)
            if season == current_year and current_week:
                max_week = min(current_week - 1, regular_season_weeks)  # Only completed weeks
            else:
                max_week = regular_season_weeks  # Past seasons, all regular season weeks are complete
            
            # Collect weekly scores for all teams
            weekly_scores_by_team = {}  # {team: [scores]}
            team_records = {}  # {team: {wins, losses, ties}}
            team_margins = {}  # {team: [margins]} (positive = victory, negative = defeat)
            
            # Track player stats by position (accumulate across all weeks)
            player_stats_by_key = {}  # {(team, player_id, position): {player_name, total_points, games_started}}
            
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
                            'roster_id': roster_id,
                            'score': round(points, 2)
                        })
                    
                    # Process matchup pairs and calculate records
                    for matchup_id, teams in matchup_pairs.items():
                        if len(teams) == 2:
                            team1 = teams[0]
                            team2 = teams[1]
                            
                            # Exclude matchups with combined 0 points
                            combined_score = team1['score'] + team2['score']
                            if combined_score > 0:
                                # Track weekly scores
                                if team1['team'] not in weekly_scores_by_team:
                                    weekly_scores_by_team[team1['team']] = []
                                    team_records[team1['team']] = {'wins': 0, 'losses': 0, 'ties': 0}
                                    team_margins[team1['team']] = []
                                
                                if team2['team'] not in weekly_scores_by_team:
                                    weekly_scores_by_team[team2['team']] = []
                                    team_records[team2['team']] = {'wins': 0, 'losses': 0, 'ties': 0}
                                    team_margins[team2['team']] = []
                                
                                weekly_scores_by_team[team1['team']].append(team1['score'])
                                weekly_scores_by_team[team2['team']].append(team2['score'])
                                
                                # Calculate winner/loser and margins
                                if team1['score'] > team2['score']:
                                    team_records[team1['team']]['wins'] += 1
                                    team_records[team2['team']]['losses'] += 1
                                    team_margins[team1['team']].append(team1['score'] - team2['score'])
                                    team_margins[team2['team']].append(team2['score'] - team1['score'])
                                elif team2['score'] > team1['score']:
                                    team_records[team2['team']]['wins'] += 1
                                    team_records[team1['team']]['losses'] += 1
                                    team_margins[team2['team']].append(team2['score'] - team1['score'])
                                    team_margins[team1['team']].append(team1['score'] - team2['score'])
                                else:
                                    team_records[team1['team']]['ties'] += 1
                                    team_records[team2['team']]['ties'] += 1
                                    team_margins[team1['team']].append(0)
                                    team_margins[team2['team']].append(0)
                    
                    # Process player stats from matchups (only starters)
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
                                key = (team_name, player_id_str, position)
                                
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
            
            # Calculate season stats for each team
            for team_name, scores in weekly_scores_by_team.items():
                if not scores:
                    continue
                
                key = (season, team_name)
                record = team_records.get(team_name, {'wins': 0, 'losses': 0, 'ties': 0})
                margins = team_margins.get(team_name, [])
                
                # Calculate averages
                avg_score = sum(scores) / len(scores) if scores else 0
                
                # Calculate margins
                victory_margins = [m for m in margins if m > 0]
                defeat_margins = [abs(m) for m in margins if m < 0]
                avg_margin_victory = sum(victory_margins) / len(victory_margins) if victory_margins else 0
                avg_margin_defeat = sum(defeat_margins) / len(defeat_margins) if defeat_margins else 0
                
                # Calculate win/loss streaks
                win_streak = 0
                loss_streak = 0
                current_win_streak = 0
                current_loss_streak = 0
                
                # Need to reconstruct game-by-game results to calculate streaks
                # We'll do this by iterating through weeks and checking if team won or lost
                for week in range(1, max_week + 1):
                    try:
                        matchups = st.session_state.sleeper_client.get_league_matchups(league_id, week)
                        matchup_pairs = {}
                        for matchup in matchups:
                            matchup_id = matchup.get('matchup_id')
                            roster_id = matchup.get('roster_id')
                            points = matchup.get('points', 0) or 0
                            
                            if matchup_id not in matchup_pairs:
                                matchup_pairs[matchup_id] = []
                            
                            team_name_from_matchup = 'Unknown'
                            if roster_id in roster_lookup:
                                roster = roster_lookup[roster_id]
                                owner_id = roster.get('owner_id')
                                if owner_id in user_lookup:
                                    team_name_from_matchup = user_lookup[owner_id]
                            
                            matchup_pairs[matchup_id].append({
                                'team': team_name_from_matchup,
                                'score': round(points, 2)
                            })
                        
                        # Check if this team played this week and won/lost
                        for matchup_id, teams in matchup_pairs.items():
                            if len(teams) == 2:
                                team1 = teams[0]
                                team2 = teams[1]
                                
                                if team1['team'] == team_name:
                                    if team1['score'] > team2['score']:
                                        current_win_streak += 1
                                        current_loss_streak = 0
                                        win_streak = max(win_streak, current_win_streak)
                                    elif team2['score'] > team1['score']:
                                        current_loss_streak += 1
                                        current_win_streak = 0
                                        loss_streak = max(loss_streak, current_loss_streak)
                                    else:
                                        # Tie - reset streaks
                                        current_win_streak = 0
                                        current_loss_streak = 0
                                elif team2['team'] == team_name:
                                    if team2['score'] > team1['score']:
                                        current_win_streak += 1
                                        current_loss_streak = 0
                                        win_streak = max(win_streak, current_win_streak)
                                    elif team1['score'] > team2['score']:
                                        current_loss_streak += 1
                                        current_win_streak = 0
                                        loss_streak = max(loss_streak, current_loss_streak)
                                    else:
                                        # Tie - reset streaks
                                        current_win_streak = 0
                                        current_loss_streak = 0
                    except:
                        continue
                
                # Count games over 150 points
                games_over_150 = sum(1 for score in scores if score > 150)
                
                # Find weeks as highest/lowest scorer
                # We need to compare across all teams each week
                weeks_as_highest = 0
                weeks_as_lowest = 0
                
                for week in range(1, max_week + 1):
                    try:
                        matchups = st.session_state.sleeper_client.get_league_matchups(league_id, week)
                        matchup_pairs = {}
                        for matchup in matchups:
                            matchup_id = matchup.get('matchup_id')
                            roster_id = matchup.get('roster_id')
                            points = matchup.get('points', 0) or 0
                            
                            if matchup_id not in matchup_pairs:
                                matchup_pairs[matchup_id] = []
                            
                            team_name_from_matchup = 'Unknown'
                            if roster_id in roster_lookup:
                                roster = roster_lookup[roster_id]
                                owner_id = roster.get('owner_id')
                                if owner_id in user_lookup:
                                    team_name_from_matchup = user_lookup[owner_id]
                            
                            matchup_pairs[matchup_id].append({
                                'team': team_name_from_matchup,
                                'score': round(points, 2)
                            })
                        
                        # Get all scores for this week
                        week_scores = []
                        for matchup_id, teams in matchup_pairs.items():
                            if len(teams) == 2:
                                combined = teams[0]['score'] + teams[1]['score']
                                if combined > 0:  # Exclude 0 combined scores
                                    week_scores.append(teams[0]['score'])
                                    week_scores.append(teams[1]['score'])
                        
                        if week_scores:
                            max_score = max(week_scores)
                            min_score = min(week_scores)
                            
                            # Check if this team had the highest or lowest score this week
                            team_week_score = None
                            for matchup_id, teams in matchup_pairs.items():
                                if len(teams) == 2:
                                    if teams[0]['team'] == team_name:
                                        team_week_score = teams[0]['score']
                                        break
                                    elif teams[1]['team'] == team_name:
                                        team_week_score = teams[1]['score']
                                        break
                            
                            if team_week_score is not None:
                                if team_week_score == max_score:
                                    weeks_as_highest += 1
                                if team_week_score == min_score:
                                    weeks_as_lowest += 1
                    except:
                        continue
                
                team_season_stats[key] = {
                    'year': season,
                    'team': team_name,
                    'games': len(scores),
                    'total_points': sum(scores),
                    'avg_score': avg_score,
                    'wins': record['wins'],
                    'losses': record['losses'],
                    'ties': record['ties'],
                    'record_str': f"{record['wins']}-{record['losses']}-{record['ties']}",
                    'win_pct': record['wins'] / len(scores) if scores else 0,
                    'avg_margin_victory': avg_margin_victory,
                    'avg_margin_defeat': avg_margin_defeat,
                    'win_streak': win_streak,
                    'loss_streak': loss_streak,
                    'games_over_150': games_over_150,
                    'weeks_as_highest': weeks_as_highest,
                    'weeks_as_lowest': weeks_as_lowest
                }
            
            # Store player stats for this season
            for (team_name, player_id, position), stats in player_stats_by_key.items():
                if stats['games_started'] > 0:
                    key = (season, team_name, player_id, position)
                    avg_per_game = stats['total_points'] / stats['games_started'] if stats['games_started'] > 0 else 0
                    
                    player_season_stats[key] = {
                        'year': season,
                        'team': team_name,
                        'player': stats['player_name'],
                        'position': position,
                        'total_score': round(stats['total_points'], 2),
                        'avg_per_game': round(avg_per_game, 2),
                        'games_started': stats['games_started']
                    }
        except Exception as e:
            st.warning(f"⚠️ Error loading {season}: {str(e)}")
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    if not team_season_stats:
        st.info("No regular season data available.")
        return
    
    # Display records
    stats_list = list(team_season_stats.values())
    
    # 1. Highest Scoring Avg Per Game
    st.markdown("### 🏆 Top 5 Highest Scoring Avg Per Game")
    highest_avg = sorted(stats_list, key=lambda x: x['avg_score'], reverse=True)[:5]
    highest_avg_df = pd.DataFrame(highest_avg)
    highest_avg_df['Rank'] = range(1, len(highest_avg_df) + 1)
    highest_avg_df = highest_avg_df[['Rank', 'year', 'team', 'avg_score']]
    highest_avg_df = highest_avg_df.rename(columns={'year': 'Year', 'team': 'Team', 'avg_score': 'Avg Score'})
    highest_avg_df['Avg Score'] = highest_avg_df['Avg Score'].round(2)
    st.dataframe(highest_avg_df, use_container_width=True, hide_index=True)
    
    # 2. Lowest Scoring Avg Per Game
    st.markdown("### 📉 Top 5 Lowest Scoring Avg Per Game")
    lowest_avg = sorted(stats_list, key=lambda x: x['avg_score'], reverse=False)[:5]
    lowest_avg_df = pd.DataFrame(lowest_avg)
    lowest_avg_df['Rank'] = range(1, len(lowest_avg_df) + 1)
    lowest_avg_df = lowest_avg_df[['Rank', 'year', 'team', 'avg_score']]
    lowest_avg_df = lowest_avg_df.rename(columns={'year': 'Year', 'team': 'Team', 'avg_score': 'Avg Score'})
    lowest_avg_df['Avg Score'] = lowest_avg_df['Avg Score'].round(2)
    st.dataframe(lowest_avg_df, use_container_width=True, hide_index=True)
    
    # 3. Best Record
    st.markdown("### 🎯 Top 5 Best Record")
    best_records = sorted(stats_list, key=lambda x: (x['win_pct'], x['wins']), reverse=True)[:5]
    best_records_df = pd.DataFrame(best_records)
    best_records_df['Rank'] = range(1, len(best_records_df) + 1)
    best_records_df = best_records_df[['Rank', 'year', 'team', 'record_str']]
    best_records_df = best_records_df.rename(columns={'year': 'Year', 'team': 'Team', 'record_str': 'Record'})
    st.dataframe(best_records_df, use_container_width=True, hide_index=True)
    
    # 4. Worst Record
    st.markdown("### 😢 Top 5 Worst Record")
    worst_records = sorted(stats_list, key=lambda x: (x['win_pct'], x['wins']), reverse=False)[:5]
    worst_records_df = pd.DataFrame(worst_records)
    worst_records_df['Rank'] = range(1, len(worst_records_df) + 1)
    worst_records_df = worst_records_df[['Rank', 'year', 'team', 'record_str']]
    worst_records_df = worst_records_df.rename(columns={'year': 'Year', 'team': 'Team', 'record_str': 'Record'})
    st.dataframe(worst_records_df, use_container_width=True, hide_index=True)
    
    # 5. Best Avg Margin of Victory
    st.markdown("### 💪 Top 5 Best Avg Margin of Victory")
    best_margin_victory = [s for s in stats_list if s['avg_margin_victory'] > 0]
    best_margin_victory = sorted(best_margin_victory, key=lambda x: x['avg_margin_victory'], reverse=True)[:5]
    if best_margin_victory:
        best_margin_df = pd.DataFrame(best_margin_victory)
        best_margin_df['Rank'] = range(1, len(best_margin_df) + 1)
        best_margin_df = best_margin_df[['Rank', 'year', 'team', 'avg_margin_victory']]
        best_margin_df = best_margin_df.rename(columns={'year': 'Year', 'team': 'Team', 'avg_margin_victory': 'Avg Margin'})
        best_margin_df['Avg Margin'] = best_margin_df['Avg Margin'].round(2)
        st.dataframe(best_margin_df, use_container_width=True, hide_index=True)
    else:
        st.info("No data available.")
    
    # 6. Worst Avg Margin of Defeat
    st.markdown("### 😞 Top 5 Worst Avg Margin of Defeat")
    worst_margin_defeat = [s for s in stats_list if s['avg_margin_defeat'] > 0]
    worst_margin_defeat = sorted(worst_margin_defeat, key=lambda x: x['avg_margin_defeat'], reverse=True)[:5]
    if worst_margin_defeat:
        worst_margin_df = pd.DataFrame(worst_margin_defeat)
        worst_margin_df['Rank'] = range(1, len(worst_margin_df) + 1)
        worst_margin_df = worst_margin_df[['Rank', 'year', 'team', 'avg_margin_defeat']]
        worst_margin_df = worst_margin_df.rename(columns={'year': 'Year', 'team': 'Team', 'avg_margin_defeat': 'Avg Margin'})
        worst_margin_df['Avg Margin'] = worst_margin_df['Avg Margin'].round(2)
        st.dataframe(worst_margin_df, use_container_width=True, hide_index=True)
    else:
        st.info("No data available.")
    
    # 7. Weeks in a season as highest scorer
    st.markdown("### 🔥 Top 5 Weeks in a Season as Highest Scorer")
    highest_scorer_weeks = sorted(stats_list, key=lambda x: x['weeks_as_highest'], reverse=True)[:5]
    highest_scorer_df = pd.DataFrame(highest_scorer_weeks)
    highest_scorer_df['Rank'] = range(1, len(highest_scorer_df) + 1)
    highest_scorer_df = highest_scorer_df[['Rank', 'year', 'team', 'weeks_as_highest']]
    highest_scorer_df = highest_scorer_df.rename(columns={'year': 'Year', 'team': 'Team', 'weeks_as_highest': 'Weeks'})
    st.dataframe(highest_scorer_df, use_container_width=True, hide_index=True)
    
    # 8. Weeks in a season as lowest scorer
    st.markdown("### 🥶 Top 5 Weeks in a Season as Lowest Scorer")
    lowest_scorer_weeks = sorted(stats_list, key=lambda x: x['weeks_as_lowest'], reverse=True)[:5]
    lowest_scorer_df = pd.DataFrame(lowest_scorer_weeks)
    lowest_scorer_df['Rank'] = range(1, len(lowest_scorer_df) + 1)
    lowest_scorer_df = lowest_scorer_df[['Rank', 'year', 'team', 'weeks_as_lowest']]
    lowest_scorer_df = lowest_scorer_df.rename(columns={'year': 'Year', 'team': 'Team', 'weeks_as_lowest': 'Weeks'})
    st.dataframe(lowest_scorer_df, use_container_width=True, hide_index=True)
    
    # 9. Longest Win Streak
    st.markdown("### 🏅 Top 5 Longest Win Streak in a Season")
    longest_win_streaks = sorted(stats_list, key=lambda x: x['win_streak'], reverse=True)[:5]
    win_streak_df = pd.DataFrame(longest_win_streaks)
    win_streak_df['Rank'] = range(1, len(win_streak_df) + 1)
    win_streak_df = win_streak_df[['Rank', 'year', 'team', 'win_streak']]
    win_streak_df = win_streak_df.rename(columns={'year': 'Year', 'team': 'Team', 'win_streak': 'Win Streak'})
    st.dataframe(win_streak_df, use_container_width=True, hide_index=True)
    
    # 10. Longest Losing Streak
    st.markdown("### 📉 Top 5 Longest Losing Streak in a Season")
    longest_loss_streaks = sorted(stats_list, key=lambda x: x['loss_streak'], reverse=True)[:5]
    loss_streak_df = pd.DataFrame(longest_loss_streaks)
    loss_streak_df['Rank'] = range(1, len(loss_streak_df) + 1)
    loss_streak_df = loss_streak_df[['Rank', 'year', 'team', 'loss_streak']]
    loss_streak_df = loss_streak_df.rename(columns={'year': 'Year', 'team': 'Team', 'loss_streak': 'Losing Streak'})
    st.dataframe(loss_streak_df, use_container_width=True, hide_index=True)
    
    # 11. Games in a season scoring over 150 points
    st.markdown("### 💯 Top 5 Games in a Season Scoring Over 150 Points")
    games_over_150 = sorted(stats_list, key=lambda x: x['games_over_150'], reverse=True)[:5]
    games_150_df = pd.DataFrame(games_over_150)
    games_150_df['Rank'] = range(1, len(games_150_df) + 1)
    games_150_df = games_150_df[['Rank', 'year', 'team', 'games_over_150']]
    games_150_df = games_150_df.rename(columns={'year': 'Year', 'team': 'Team', 'games_over_150': 'Games Over 150'})
    st.dataframe(games_150_df, use_container_width=True, hide_index=True)
    
    # Player Stats by Position
    st.markdown("---")
    st.markdown("## 👤 Player Statistics (Regular Season)")
    st.markdown("**Only includes players who were in the starting lineup**")
    
    if not player_season_stats:
        st.info("No player statistics available.")
        return
    
    player_stats_list = list(player_season_stats.values())
    positions = ['QB', 'RB', 'WR', 'TE', 'DEF', 'K']
    
    for position in positions:
        position_players = [p for p in player_stats_list if p['position'] == position]
        
        if not position_players:
            continue
        
        st.markdown(f"### {position} - Highest Total Scores")
        highest_position = sorted(position_players, key=lambda x: x['total_score'], reverse=True)[:5]
        highest_df = pd.DataFrame(highest_position)
        highest_df['Rank'] = range(1, len(highest_df) + 1)
        highest_df = highest_df[['Rank', 'year', 'team', 'player', 'total_score', 'avg_per_game']]
        highest_df = highest_df.rename(columns={
            'year': 'Year',
            'team': 'Team',
            'player': 'Player',
            'total_score': 'Total Score',
            'avg_per_game': 'Avg Per Game'
        })
        st.dataframe(highest_df, use_container_width=True, hide_index=True)
        
        st.markdown(f"### {position} - Lowest Total Scores (Min 7 Games Started)")
        # Filter to only include players who started at least 7 games
        lowest_position = [p for p in position_players if p['games_started'] >= 7]
        lowest_position = sorted(lowest_position, key=lambda x: x['total_score'], reverse=False)[:5]
        if lowest_position:
            lowest_df = pd.DataFrame(lowest_position)
            lowest_df['Rank'] = range(1, len(lowest_df) + 1)
            lowest_df = lowest_df[['Rank', 'year', 'team', 'player', 'total_score', 'avg_per_game']]
            lowest_df = lowest_df.rename(columns={
                'year': 'Year',
                'team': 'Team',
                'player': 'Player',
                'total_score': 'Total Score',
                'avg_per_game': 'Avg Per Game'
            })
            st.dataframe(lowest_df, use_container_width=True, hide_index=True)
        else:
            st.info(f"No {position} players with at least 7 games started found.")

