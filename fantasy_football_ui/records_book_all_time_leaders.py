"""
All Time Leaders records helper function
"""

import pandas as pd
from datetime import datetime
import streamlit as st
from typing import Dict, List
from collections import defaultdict

from fantasy_football_ui.team_name_utils import normalize_team_name


def display_all_time_leaders(available_seasons: List[int], SLEEPER_LEAGUE_IDS: Dict[int, str]):
    """Display all-time leader statistics across regular seasons"""
    st.subheader("🏅 All Time Leaders")
    st.markdown("**Regular season records aggregated across all years**")

    team_stats = defaultdict(lambda: {
        'points_for': 0.0,
        'points_against': 0.0,
        'games_over_150': 0,
        'weeks_highest': 0,
        'weeks_lowest': 0,
        'longest_win_streak': 0,
        'longest_loss_streak': 0
    })

    current_win_streaks = defaultdict(int)
    current_loss_streaks = defaultdict(int)

    progress_bar = st.progress(0)
    status_text = st.empty()

    current_year = datetime.now().year
    current_week = None
    if current_year in available_seasons:
        try:
            sport_state = st.session_state.sleeper_client.get_sport_state("nfl")
            current_week = sport_state.get('week', 1)
        except Exception:  # noqa: BLE001
            current_week = 1

    sorted_seasons = sorted(available_seasons)

    for idx, season in enumerate(sorted_seasons):
        league_id = SLEEPER_LEAGUE_IDS[season]
        status_text.text(f"Loading regular season data for {season}...")
        progress_bar.progress((idx + 1) / len(sorted_seasons))

        try:
            league = st.session_state.sleeper_client.get_league(league_id)
            regular_season_weeks = league.get('settings', {}).get('reg_season_count', 14) or 14

            users = st.session_state.sleeper_client.get_league_users(league_id)
            rosters = st.session_state.sleeper_client.get_league_rosters(league_id)
            user_lookup = {user.get('user_id'): normalize_team_name(user.get('display_name') or user.get('username', 'Unknown')) for user in users}
            roster_lookup = {roster.get('roster_id'): roster for roster in rosters}

            if season == current_year and current_week:
                max_week = min(current_week - 1, regular_season_weeks)
            else:
                max_week = regular_season_weeks

            for week in range(1, max_week + 1):
                try:
                    matchups = st.session_state.sleeper_client.get_league_matchups(league_id, week)

                    matchup_pairs = {}
                    week_scores = []

                    for matchup in matchups:
                        matchup_id = matchup.get('matchup_id')
                        roster_id = matchup.get('roster_id')
                        points = matchup.get('points', 0) or 0

                        if matchup_id not in matchup_pairs:
                            matchup_pairs[matchup_id] = []

                        team_name = 'Unknown'
                        if roster_id in roster_lookup:
                            roster = roster_lookup[roster_id]
                            owner_id = roster.get('owner_id')
                            if owner_id in user_lookup:
                                team_name = user_lookup[owner_id]

                        matchup_pairs[matchup_id].append({
                            'team': team_name,
                            'roster_id': roster_id,
                            'score': round(float(points), 2)
                        })

                    for teams in matchup_pairs.values():
                        if len(teams) != 2:
                            continue

                        team1 = teams[0]
                        team2 = teams[1]
                        team1_name = team1['team']
                        team2_name = team2['team']
                        score1 = team1['score']
                        score2 = team2['score']

                        if score1 + score2 == 0:
                            continue

                        week_scores.append({'team': team1_name, 'score': score1})
                        week_scores.append({'team': team2_name, 'score': score2})

                        team_stats[team1_name]['points_for'] += score1
                        team_stats[team1_name]['points_against'] += score2
                        team_stats[team2_name]['points_for'] += score2
                        team_stats[team2_name]['points_against'] += score1

                        if score1 > 150:
                            team_stats[team1_name]['games_over_150'] += 1
                        if score2 > 150:
                            team_stats[team2_name]['games_over_150'] += 1

                        if score1 > score2:
                            current_win_streaks[team1_name] += 1
                            current_loss_streaks[team1_name] = 0
                            current_loss_streaks[team2_name] += 1
                            current_win_streaks[team2_name] = 0

                            team_stats[team1_name]['longest_win_streak'] = max(
                                team_stats[team1_name]['longest_win_streak'], current_win_streaks[team1_name]
                            )
                            team_stats[team2_name]['longest_loss_streak'] = max(
                                team_stats[team2_name]['longest_loss_streak'], current_loss_streaks[team2_name]
                            )
                        elif score2 > score1:
                            current_win_streaks[team2_name] += 1
                            current_loss_streaks[team2_name] = 0
                            current_loss_streaks[team1_name] += 1
                            current_win_streaks[team1_name] = 0

                            team_stats[team2_name]['longest_win_streak'] = max(
                                team_stats[team2_name]['longest_win_streak'], current_win_streaks[team2_name]
                            )
                            team_stats[team1_name]['longest_loss_streak'] = max(
                                team_stats[team1_name]['longest_loss_streak'], current_loss_streaks[team1_name]
                            )
                        else:
                            current_win_streaks[team1_name] = 0
                            current_loss_streaks[team1_name] = 0
                            current_win_streaks[team2_name] = 0
                            current_loss_streaks[team2_name] = 0
                except Exception:  # noqa: BLE001
                    continue

                if week_scores:
                    max_score = max(s['score'] for s in week_scores)
                    min_score = min(s['score'] for s in week_scores)

                    for entry in week_scores:
                        if entry['score'] == max_score:
                            team_stats[entry['team']]['weeks_highest'] += 1
                        if entry['score'] == min_score:
                            team_stats[entry['team']]['weeks_lowest'] += 1
        except Exception as e:  # noqa: BLE001
            st.warning(f"⚠️ Error loading {season}: {str(e)}")
            continue

    progress_bar.empty()
    status_text.empty()

    if not team_stats:
        st.info("No regular season data available.")
        return

    stats_list = []
    for team, stats in team_stats.items():
        stats_list.append({
            'team': team,
            **stats
        })

    def render_table(title: str, records: List[Dict], column_map: Dict[str, str]):
        st.markdown(title)
        if not records:
            st.info("No data available.")
            return
        df = pd.DataFrame(records)
        df['Rank'] = range(1, len(df) + 1)
        columns = ['Rank'] + list(column_map.keys())
        df = df[columns]
        df = df.rename(columns=column_map)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Points For
    points_for = sorted(stats_list, key=lambda x: x['points_for'], reverse=True)[:5]
    render_table("#### 🔥 Top 5 Points For", points_for, {'team': 'Team', 'points_for': 'Points For'})

    # Points Against
    points_against = sorted(stats_list, key=lambda x: x['points_against'], reverse=True)[:5]
    render_table("#### 🛡️ Top 5 Points Against", points_against, {'team': 'Team', 'points_against': 'Points Against'})

    # Games over 150
    games_150 = sorted(stats_list, key=lambda x: x['games_over_150'], reverse=True)[:5]
    render_table("#### 💯 Top 5 Games Over 150 Points", games_150, {'team': 'Team', 'games_over_150': 'Games Over 150'})

    # Weeks as highest scorer
    weeks_highest = sorted(stats_list, key=lambda x: x['weeks_highest'], reverse=True)[:5]
    render_table("#### 🔝 Top 5 Weeks as Highest Scorer", weeks_highest, {'team': 'Team', 'weeks_highest': 'Weeks as Highest Scorer'})

    # Weeks as lowest scorer
    weeks_lowest = sorted(stats_list, key=lambda x: x['weeks_lowest'], reverse=True)[:5]
    render_table("#### 📉 Top 5 Weeks as Lowest Scorer", weeks_lowest, {'team': 'Team', 'weeks_lowest': 'Weeks as Lowest Scorer'})

    # Longest win streak
    longest_win = sorted(stats_list, key=lambda x: x['longest_win_streak'], reverse=True)[:5]
    render_table("#### 🏆 Top 5 Longest Win Streak", longest_win, {'team': 'Team', 'longest_win_streak': 'Win Streak'})

    # Longest losing streak
    longest_loss = sorted(stats_list, key=lambda x: x['longest_loss_streak'], reverse=True)[:5]
    render_table("#### 😖 Top 5 Longest Losing Streak", longest_loss, {'team': 'Team', 'longest_loss_streak': 'Losing Streak'})
