"""
Fantasy Football Dashboard
A Streamlit UI for viewing Sleeper and Yahoo Fantasy Football league data
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Add parent directory to path to import fantasy_football_api
# Get the absolute path to the parent directory
app_dir = Path(__file__).resolve().parent
parent_dir = app_dir.parent
parent_dir_str = str(parent_dir)

# Add to path if not already there
if parent_dir_str not in sys.path:
    sys.path.insert(0, parent_dir_str)

# Also add the parent's parent in case we're nested
if str(parent_dir.parent) not in sys.path:
    sys.path.insert(0, str(parent_dir.parent))

# Verify the path and import
try:
    from fantasy_football_api import SleeperClient
    from fantasy_football_api.yahoo_client_yfpy import YahooClientYFPY
    from fantasy_football_api.yahoo_oauth_simple import YahooOAuthSimple
except ImportError as e:
    import traceback
    st.error(f"❌ Import Error: {str(e)}")
    st.error(f"**Looking for module in:** `{parent_dir_str}`")
    st.error(f"**Module exists:** {Path(parent_dir_str, 'fantasy_football_api').exists()}")
    st.error(f"**Current working directory:** {os.getcwd()}")
    st.error(f"**Python path:**")
    for p in sys.path[:5]:  # Show first 5 paths
        st.code(p)
    st.error("**Full error:**")
    st.code(traceback.format_exc())
    st.stop()
import pandas as pd
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Fantasy Football Dashboard",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .league-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: white;
        padding: 1rem;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'sleeper_client' not in st.session_state:
    st.session_state.sleeper_client = SleeperClient()

# Force reload of sleeper_client module to ensure latest code
# This ensures we're using the latest version with week-specific endpoints
import importlib
import sys

# Aggressively clear all cached modules related to sleeper_client
modules_to_remove = [
    'fantasy_football_api.sleeper_client',
    'fantasy_football_api',
]
for mod_name in modules_to_remove:
    if mod_name in sys.modules:
        del sys.modules[mod_name]

# Also clear any cached imports
if 'SleeperClient' in sys.modules:
    del sys.modules['SleeperClient']

# Force fresh import
try:
    from fantasy_football_api import SleeperClient
    import fantasy_football_api.sleeper_client
    importlib.reload(fantasy_football_api.sleeper_client)
    # Recreate client to use reloaded module
    if 'sleeper_client' not in st.session_state:
        st.session_state.sleeper_client = SleeperClient()
    else:
        # Force recreation
        st.session_state.sleeper_client = SleeperClient()
except Exception as e:
    # If reload fails, try to use existing client
    if 'sleeper_client' not in st.session_state:
        from fantasy_football_api import SleeperClient
        st.session_state.sleeper_client = SleeperClient()

if 'yahoo_authenticated' not in st.session_state:
    st.session_state.yahoo_authenticated = False

if 'yahoo_client' not in st.session_state:
    st.session_state.yahoo_client = None

if 'yfpy_oauth' not in st.session_state:
    st.session_state.yfpy_oauth = None

# Load saved Yahoo credentials from secrets if available
def load_yahoo_credentials():
    """Load Yahoo credentials from Streamlit secrets"""
    try:
        if hasattr(st, 'secrets') and 'yahoo' in st.secrets:
            yahoo_secrets = st.secrets['yahoo']
            return {
                'consumer_key': yahoo_secrets.get('consumer_key', ''),
                'consumer_secret': yahoo_secrets.get('consumer_secret', ''),
                'access_token': yahoo_secrets.get('access_token', ''),
                'access_token_secret': yahoo_secrets.get('access_token_secret', '')
            }
    except Exception:
        pass
    return None

def save_credentials_to_secrets(consumer_key: str, consumer_secret: str, 
                                access_token: str, access_token_secret: str):
    """Save Yahoo credentials to Streamlit secrets file"""
    try:
        secrets_dir = Path(__file__).parent / ".streamlit"
        secrets_dir.mkdir(exist_ok=True)
        secrets_file = secrets_dir / "secrets.toml"
        
        import toml
        
        # Load existing secrets if file exists
        secrets = {}
        if secrets_file.exists():
            secrets = toml.load(secrets_file)
        
        # Update Yahoo credentials
        if 'yahoo' not in secrets:
            secrets['yahoo'] = {}
        
        secrets['yahoo']['consumer_key'] = consumer_key
        secrets['yahoo']['consumer_secret'] = consumer_secret
        secrets['yahoo']['access_token'] = access_token
        secrets['yahoo']['access_token_secret'] = access_token_secret
        
        # Write to file
        with open(secrets_file, 'w') as f:
            toml.dump(secrets, f)
        
        return True
    except Exception as e:
        st.error(f"Error saving credentials: {str(e)}")
        return False

# Load default credentials if available
default_creds = load_yahoo_credentials()
if default_creds and default_creds.get('consumer_key') and default_creds.get('consumer_secret'):
    if default_creds.get('access_token') and default_creds.get('access_token_secret'):
        try:
            st.session_state.yahoo_client = YahooClientYFPY(
                default_creds['consumer_key'],
                default_creds['consumer_secret'],
                default_creds['access_token'],
                default_creds['access_token_secret']
            )
            st.session_state.yahoo_authenticated = True
        except Exception:
            # Credentials might be expired, user will need to re-authenticate
            pass

# League IDs
# Sleeper league IDs by season (Sleeper creates new league IDs each year)
# Note: 2021 was the first year on Sleeper. Years before 2021 were on Yahoo only.
SLEEPER_LEAGUE_IDS = {
    2025: "1257479697114075136",
    2024: "1124842071690067968",
    2023: "1004526732419911680",
    2022: "862956648505921536",
    2021: "740630336907657216",  # First year on Sleeper
}

# Default/current Sleeper league ID (for backwards compatibility)
SLEEPER_LEAGUE_ID = SLEEPER_LEAGUE_IDS.get(datetime.now().year, "1257479697114075136")

YAHOO_LEAGUE_ID = "572651"

def get_sleeper_league_id(season: int) -> str:
    """Get Sleeper league ID for a given season"""
    return SLEEPER_LEAGUE_IDS.get(season, None)

# Yahoo game keys by year (NFL)
# Format: {year: game_key}
# Note: Game keys may vary, but typically increment by 1 each year
# 2024 = 414, 2023 = 414, etc. (need to verify for your league)
YAHOO_GAME_KEYS = {
    2024: "414",
    2023: "414",  # May need to adjust based on actual game_key
    2022: "414",
    2021: "414",
    2020: "414",
}

def format_sleeper_league_name(league_data):
    """Format Sleeper league name"""
    return league_data.get('name', 'Unknown League')

def format_yahoo_league_name(league_data):
    """Format Yahoo league name"""
    if isinstance(league_data, dict):
        return league_data.get('name', 'Unknown League')
    return 'Unknown League'

def get_sleeper_standings(league_id: str):
    """Get and format Sleeper league standings"""
    try:
        users = st.session_state.sleeper_client.get_league_users(league_id)
        rosters = st.session_state.sleeper_client.get_league_rosters(league_id)
        
        standings_data = []
        user_lookup = {user['user_id']: user for user in users}
        
        for roster in rosters:
            user_id = roster.get('owner_id')
            if user_id and user_id in user_lookup:
                user = user_lookup[user_id]
                team_name = normalize_team_name(user.get('display_name') or user.get('username', 'Unknown'))
                
                settings = roster.get('settings', {})
                wins = settings.get('wins', 0)
                losses = settings.get('losses', 0)
                ties = settings.get('ties', 0)
                points_for = settings.get('fpts', 0) + (settings.get('fpts_decimal', 0) / 100)
                
                standings_data.append({
                    'Team': team_name,
                    'Wins': wins,
                    'Losses': losses,
                    'Ties': ties,
                    'Points For': round(points_for, 2)
                })
        
        # Sort by wins, then points
        standings_data.sort(key=lambda x: (x['Wins'], x['Points For']), reverse=True)
        
        return pd.DataFrame(standings_data)
    except Exception as e:
        st.error(f"Error fetching Sleeper standings: {str(e)}")
        return pd.DataFrame()

def get_sleeper_matchups(league_id: str, week: int):
    """Get and format Sleeper league matchups for a week"""
    try:
        matchups = st.session_state.sleeper_client.get_league_matchups(league_id, week)
        users = st.session_state.sleeper_client.get_league_users(league_id)
        rosters = st.session_state.sleeper_client.get_league_rosters(league_id)
        
        user_lookup = {user['user_id']: user for user in users}
        roster_lookup = {roster['roster_id']: roster for roster in rosters}
        
        matchup_data = []
        matchup_pairs = {}
        
        for matchup in matchups:
            roster_id = matchup.get('roster_id')
            matchup_id = matchup.get('matchup_id')
            
            if roster_id in roster_lookup:
                roster = roster_lookup[roster_id]
                user_id = roster.get('owner_id')
                
                if user_id and user_id in user_lookup:
                    user = user_lookup[user_id]
                    team_name = normalize_team_name(user.get('display_name') or user.get('username', 'Unknown'))
                    points = matchup.get('points', 0) or 0
                    
                    if matchup_id not in matchup_pairs:
                        matchup_pairs[matchup_id] = []
                    
                    matchup_pairs[matchup_id].append({
                        'Team': team_name,
                        'Points': round(points, 2)
                    })
        
        # Format as matchups
        for matchup_id, teams in matchup_pairs.items():
            if len(teams) == 2:
                matchup_data.append({
                    'Team 1': teams[0]['Team'],
                    'Points 1': teams[0]['Points'],
                    'vs': 'vs',
                    'Team 2': teams[1]['Team'],
                    'Points 2': teams[1]['Points']
                })
        
        return pd.DataFrame(matchup_data)
    except Exception as e:
        st.error(f"Error fetching Sleeper matchups: {str(e)}")
        return pd.DataFrame()

def setup_yahoo_oauth():
    """Setup Yahoo OAuth authentication"""
    st.sidebar.subheader("Yahoo Authentication")
    
    # Load saved credentials
    saved_creds = load_yahoo_credentials()
    
    if st.session_state.yahoo_authenticated and st.session_state.yahoo_client:
        st.sidebar.success("✅ Yahoo authenticated")
        if st.sidebar.button("Re-authenticate"):
            st.session_state.yahoo_authenticated = False
            st.session_state.yahoo_client = None
            st.rerun()
        return
    
    # Get credentials (use saved or ask user)
    consumer_key = st.sidebar.text_input(
        "Consumer Key",
        value=saved_creds.get('consumer_key', '') if saved_creds else '',
        type="default"
    )
    consumer_secret = st.sidebar.text_input(
        "Consumer Secret",
        value=saved_creds.get('consumer_secret', '') if saved_creds else '',
        type="password"
    )
    
    if consumer_key and consumer_secret:
        # Save credentials to session state
        st.session_state.temp_consumer_key = consumer_key
        st.session_state.temp_consumer_secret = consumer_secret
        
        # Check if already authenticated (check saved credentials)
        saved_creds = load_yahoo_credentials()
        if saved_creds and saved_creds.get('access_token') and saved_creds.get('access_token_secret'):
            # Try to use saved access tokens
            try:
                st.session_state.yahoo_client = YahooClientYFPY(
                    consumer_key, 
                    consumer_secret, 
                    saved_creds['access_token'],
                    saved_creds['access_token_secret']
                )
                # Test if tokens still work by trying to get league info
                test_league_key = f"414.l.{YAHOO_LEAGUE_ID}"
                test_league = st.session_state.yahoo_client.get_league(test_league_key)
                if test_league:
                    st.session_state.yahoo_authenticated = True
                    st.rerun()
            except:
                # Tokens expired, need to re-authenticate
                pass
        
        # Show verification code input if OAuth started
        if st.session_state.get('oauth_started', False):
            st.sidebar.markdown("---")
            st.sidebar.subheader("Complete Authentication")
            st.sidebar.info("""
            **Steps:**
            1. Click "Start Authentication" below
            2. A browser window will open
            3. Log in with your Yahoo account
            4. Copy the verification code
            5. Paste it here and click "Complete Authentication"
            """)
            
            verifier_code = st.sidebar.text_input(
                "Verification Code",
                type="default",
                placeholder="Paste your code here",
                help="Copy the code from the Yahoo authorization page after you log in"
            )
            
            if st.sidebar.button("Complete Authentication", type="primary", key="complete_auth"):
                if verifier_code and verifier_code.strip():
                    try:
                        consumer_key = st.session_state.temp_consumer_key
                        consumer_secret = st.session_state.temp_consumer_secret
                        request_token = st.session_state.oauth_request_token
                        request_token_secret = st.session_state.oauth_request_secret
                        verifier = verifier_code.strip()
                        
                        # Step 3: Exchange request token for access token using simplified helper
                        oauth_helper = YahooOAuthSimple(consumer_key, consumer_secret)
                        access_token, access_token_secret = oauth_helper.get_access_token(
                            request_token, request_token_secret, verifier
                        )
                        
                        if access_token and access_token_secret:
                            # Save token file for yfpy
                            token_dir = Path.home() / ".yfpy"
                            token_dir.mkdir(exist_ok=True)
                            token_file = token_dir / "oauth2.json"
                            
                            import json
                            token_data = {
                                "consumer_key": consumer_key,
                                "consumer_secret": consumer_secret,
                                "access_token": access_token,
                                "access_token_secret": access_token_secret
                            }
                            with open(token_file, 'w') as f:
                                json.dump(token_data, f)
                            
                            # Initialize Yahoo client
                            st.session_state.yahoo_client = YahooClientYFPY(
                                consumer_key, consumer_secret, access_token, access_token_secret
                            )
                            st.session_state.yahoo_authenticated = True
                            
                            # Save credentials to secrets
                            if save_credentials_to_secrets(consumer_key, consumer_secret, access_token, access_token_secret):
                                st.session_state.oauth_started = False
                                st.sidebar.success("✓ Authentication successful! Credentials saved.")
                            st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"Error: {str(e)}")
                        import traceback
                        st.sidebar.code(traceback.format_exc())
                        st.sidebar.info("💡 Make sure you entered the code correctly. Try starting authentication again.")
                else:
                    st.sidebar.error("Please enter the verification code")
        else:
            # Start OAuth button
            if st.sidebar.button("Start Authentication", type="primary"):
                try:
                    consumer_key = st.session_state.temp_consumer_key
                    consumer_secret = st.session_state.temp_consumer_secret
                    
                    # Use simplified OAuth helper
                    oauth_helper = YahooOAuthSimple(consumer_key, consumer_secret)
                    
                    try:
                        # Step 1: Get request token and authorization URL
                        request_token, request_token_secret, auth_url = oauth_helper.get_request_token()
                        
                        # Save request token to session state
                        st.session_state.oauth_request_token = request_token
                        st.session_state.oauth_request_secret = request_token_secret
                        
                        # Step 2: Open browser for authorization
                        browser_opened = oauth_helper.open_authorization_url(auth_url)
                        
                        # Set state to show verification code input
                        st.session_state.oauth_started = True
                        
                        if browser_opened:
                            st.sidebar.success("✅ Browser opened! Get your verification code from Yahoo.")
                        else:
                            st.sidebar.warning(f"⚠️ Could not open browser automatically.")
                            st.sidebar.markdown(f"**Visit this URL:** {auth_url}")
                        
                        st.rerun()
                        
                    except Exception as e:
                        error_msg = str(e)
                        st.sidebar.error(f"❌ Authentication failed: {error_msg}")
                        
                        # Show credential info
                        key_preview = consumer_key[:20] + "..." + consumer_key[-10:] if len(consumer_key) > 30 else consumer_key
                        st.sidebar.info(f"**Using Consumer Key:** `{key_preview}`")
                        st.sidebar.info(f"**Consumer Secret:** `{'*' * len(consumer_secret)}` (length: {len(consumer_secret)})")
                        
                        # Show detailed error info
                        with st.sidebar.expander("🔍 Detailed Error Information"):
                            import traceback
                            st.code(traceback.format_exc())
                        
                        # Provide specific troubleshooting based on error
                        if "401" in error_msg or "Unauthorized" in error_msg:
                            st.sidebar.markdown("""
                            **⚠️ 401 Unauthorized Error**
                            
                            Yahoo is rejecting your OAuth request. This means there's a configuration issue.
                            
                            **Check these in Yahoo Developer (https://developer.yahoo.com/apps/):**
                            
                            1. **App Status** (MOST IMPORTANT)
                               - Must be "Active" or "Approved"
                               - If "Pending", you must wait for Yahoo approval
                               - New apps often take hours/days to be approved
                            
                            2. **OAuth Client Type**
                               - Must select: "Confidential Client - Choose for traditional web apps"
                               - This is REQUIRED for server-side OAuth
                            
                            3. **API Permissions**
                               - Fantasy Sports must be checked/enabled
                               - Must have "Read" permission
                            
                            4. **Redirect URI**
                               - Set to: `https://localhost` (no port, no trailing slash)
                               - Or try: `http://localhost` if HTTPS doesn't work
                            
                            **After fixing:**
                            - Save changes in Yahoo Developer
                            - Wait 1-2 minutes for changes to propagate
                            - Try again
                            
                            **Run diagnostic test:**
                            ```bash
                            cd fantasy_football_ui
                            py test_yahoo_oauth_detailed.py
                            ```
                            """)
                        elif "403" in error_msg or "Forbidden" in error_msg:
                            st.sidebar.markdown("""
                            **⚠️ 403 Forbidden Error**
                            
                            Your app doesn't have permission to access the Fantasy Sports API.
                            
                            **Fix:**
                            - Go to Yahoo Developer app settings
                            - Enable "Fantasy Sports" API permission
                            - Make sure "Read" permission is selected
                            - Save and wait 1-2 minutes
                            """)
                        else:
                            st.sidebar.markdown("""
                            **⚠️ Authentication Error**
                            
                            **Common fixes:**
                            1. Check app status in Yahoo Developer (must be Active/Approved)
                            2. Select "Confidential Client" for OAuth Client Type
                            3. Enable Fantasy Sports API permission
                            4. Set Redirect URI to `https://localhost`
                            5. Save and wait 1-2 minutes
                            
                            **Run diagnostic:**
                            - Run `py test_yahoo_oauth_detailed.py` in the `fantasy_football_ui` folder
                            - This will test each step and show exactly where it fails
                            """)
                        
                        st.stop()
                    
                except Exception as e:
                    error_msg = str(e)
                    st.sidebar.error(f"❌ Error starting authentication: {error_msg}")
                    
                    # Show detailed error info
                    with st.sidebar.expander("🔍 Error Details"):
                        import traceback
                        st.code(traceback.format_exc())

def get_yahoo_league_key(season: int) -> str:
    """Get Yahoo league key for a given season"""
    game_key = YAHOO_GAME_KEYS.get(season, "414")  # Default to 414 if season not found
    return f"{game_key}.l.{YAHOO_LEAGUE_ID}"

def display_all_transactions():
    """Standalone Transactions tab showing ALL years combined"""
    st.header("📋 Transaction History (All Years)")
    st.info("This view shows all transactions across all seasons. No year filtering needed!")
    
    # Show only Sleeper transactions (Yahoo removed for now)
    display_transactions_tab(None, None, "Sleeper")

def main():
    # Header
    st.markdown('<h1 class="main-header">🏈 Fantasy Fuckbois History</h1>', unsafe_allow_html=True)
    
    # Sidebar - simplified to only show main navigation
    st.sidebar.title("Navigation")
    
    # Main navigation options
    page = st.sidebar.radio(
        "Select Page",
        ["Overview", "Records Book", "League History", "Matchup Breakdown", "Team Breakdown", "Transactions"],
        index=0,
        help="Choose which section to view"
    )
    
    # Main content area
    if page == "Overview":
        from fantasy_football_ui.overview import display_overview
        display_overview()
    elif page == "Records Book":
        from fantasy_football_ui.records_book import display_records_book
        display_records_book()
    elif page == "League History":
        display_history_view()
    elif page == "Matchup Breakdown":
        from fantasy_football_ui.matchup_breakdown import display_matchup_breakdown
        display_matchup_breakdown()
    elif page == "Team Breakdown":
        from fantasy_football_ui.team_breakdown import display_team_breakdown
        display_team_breakdown()
    else:  # Transactions
        display_all_transactions()

def display_sleeper_overview(league, league_id: str):
    """Display Sleeper league overview"""
    st.subheader("League Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### League Information")
        st.write(f"**Name:** {league.get('name', 'N/A')}")
        st.write(f"**Season:** {league.get('season', 'N/A')}")
        st.write(f"**Status:** {league.get('status', 'N/A').title()}")
        st.write(f"**Total Teams:** {league.get('total_rosters', 'N/A')}")
        st.write(f"**League ID:** `{league_id}`")
        
        scoring_settings = league.get('scoring_settings', {})
        scoring_type = "PPR" if scoring_settings.get('rec', 0) > 0 else "Standard"
        st.write(f"**Scoring Type:** {scoring_type}")
    
    with col2:
        st.markdown("### Quick Stats")
        try:
            standings = get_sleeper_standings(league_id)
            if not standings.empty:
                avg_wins = standings['Wins'].mean()
                avg_points = standings['Points For'].mean()
                max_points = standings['Points For'].max()
                
                st.metric("Average Wins", f"{avg_wins:.1f}")
                st.metric("Average Points", f"{avg_points:.1f}")
                st.metric("Highest Points", f"{max_points:.1f}")
        except:
            pass

def display_sleeper_data(season: int = None):
    """Display Sleeper league data"""
    try:
        season = season or datetime.now().year
        
        # Show selected season prominently
        st.info(f"📅 **Viewing Season: {season}**")
        
        # Check if season is before Sleeper era (2021)
        if season < 2021:
            st.warning(f"⚠️ **Pre-Sleeper Era:** {season} was before your league moved to Sleeper (2021 was the first year).")
            st.info(f"💡 **Tip:** Switch to Yahoo view to see data from {season} and earlier years.")
            return
        
        # Get league ID for selected season
        league_id = get_sleeper_league_id(season)
        
        if not league_id:
            st.error(f"❌ **No league ID configured for {season}**")
            st.info(f"Please add the Sleeper league ID for {season} to the `SLEEPER_LEAGUE_IDS` dictionary in the code.")
            return
        
        # Get league info
        try:
            league = st.session_state.sleeper_client.get_league(league_id)
            league_name = format_sleeper_league_name(league)
            league_season = league.get('season', season)
            
            # Verify season matches
            if season != league_season:
                st.warning(f"⚠️ **Season Mismatch:** League ID `{league_id}` is from **{league_season}**, but you selected **{season}**. "
                          f"Data shown is from {league_season}.")
        except Exception as e:
            st.error(f"❌ **Error loading league for {season}**")
            st.info(f"League ID: `{league_id}`")
            st.info(f"Error: {str(e)}")
            st.info("The league may not exist or the ID may be incorrect.")
            return
        
        st.subheader(f"📊 {league_name} - {league_season}")
        
        # League info metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Season", league_season)
        with col2:
            st.metric("Total Teams", league.get('total_rosters', 'N/A'))
        with col3:
            st.metric("Status", league.get('status', 'N/A').title())
        with col4:
            scoring_settings = league.get('scoring_settings', {})
            st.metric("Scoring Type", "PPR" if scoring_settings.get('rec', 0) > 0 else "Standard")
        
        # Tabs for different views
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Overview", "Standings", "Matchups", "Rosters", "Transactions", "League Info"])
        
        with tab1:
            display_sleeper_overview(league, league_id)
        
        with tab2:
            st.subheader("League Standings")
            standings_df = get_sleeper_standings(league_id)
            if not standings_df.empty:
                st.dataframe(standings_df, use_container_width=True, hide_index=True)
            else:
                st.info("No standings data available")
        
        with tab3:
            st.subheader("Weekly Matchups")
            # Get current week (for current season only)
            if season == datetime.now().year:
                try:
                    sport_state = st.session_state.sleeper_client.get_sport_state("nfl")
                    current_week = sport_state.get('week', 1)
                except:
                    current_week = 1
            else:
                current_week = 1
            
            week = st.selectbox("Select Week", range(1, 19), index=current_week-1 if current_week <= 18 else 0, key=f"sleeper_week_{season}")
            matchups_df = get_sleeper_matchups(league_id, week)
            
            if not matchups_df.empty:
                st.dataframe(matchups_df, use_container_width=True, hide_index=True)
            else:
                st.info(f"No matchups data available for week {week}")
        
        with tab4:
            st.subheader("Team Rosters")
            try:
                users = st.session_state.sleeper_client.get_league_users(league_id)
                rosters = st.session_state.sleeper_client.get_league_rosters(league_id)
                
                user_lookup = {user['user_id']: normalize_team_name(user.get('display_name') or user.get('username', 'Unknown')) for user in users}
                team_names = [normalize_team_name(user.get('display_name') or user.get('username', 'Unknown')) for user in users]
                
                selected_team = st.selectbox("Select Team", team_names, key=f"sleeper_team_{season}")
                selected_user_id = next((u['user_id'] for u in users if u.get('display_name', u.get('username')) == selected_team), None)
                
                if selected_user_id:
                    selected_roster = next((r for r in rosters if r.get('owner_id') == selected_user_id), None)
                    if selected_roster:
                        st.write(f"**Roster for {selected_team}**")
                        # Display roster players (simplified - would need player data for full names)
                        st.json(selected_roster.get('players', []))
            except Exception as e:
                st.error(f"Error loading rosters: {str(e)}")
        
        with tab5:
            display_transactions_tab(league_id, season, "Sleeper")
        
        with tab6:
            st.subheader("League Settings")
            st.json({
                "League Name": league.get('name'),
                "Season": league.get('season'),
                "League ID": league_id,
                "Total Rosters": league.get('total_rosters'),
                "Status": league.get('status'),
                "Scoring Settings": league.get('scoring_settings', {}),
                "Roster Positions": league.get('roster_positions', [])
            })
    
    except Exception as e:
        st.error(f"Error loading Sleeper data: {str(e)}")
        st.info("Make sure the Sleeper league ID is correct and the league is accessible.")

def get_yahoo_standings(league_key):
    """Get and format Yahoo league standings using yfpy"""
    try:
        standings = st.session_state.yahoo_client.get_league_standings(league_key)
        
        # Parse yfpy format
        standings_data = []
        try:
            teams = standings.get('teams', [])
            
            for team in teams:
                standings_data.append({
                    'Team': team.get('name', 'Unknown'),
                    'Wins': team.get('wins', 0),
                    'Losses': team.get('losses', 0),
                    'Ties': team.get('ties', 0),
                    'Points For': round(team.get('points_for', 0), 2),
                    'Points Against': round(team.get('points_against', 0), 2)
                })
            
            # Sort by wins, then points
            standings_data.sort(key=lambda x: (x['Wins'], x['Points For']), reverse=True)
        except (KeyError, IndexError, TypeError) as e:
            # If parsing fails, return empty
            st.warning(f"Could not parse Yahoo standings: {str(e)}")
            return pd.DataFrame()
        
        return pd.DataFrame(standings_data)
    except Exception as e:
        st.error(f"Error fetching Yahoo standings: {str(e)}")
        return pd.DataFrame()

def display_yahoo_data(season: int = None):
    """Display Yahoo league data"""
    if not st.session_state.yahoo_client:
        st.error("Yahoo client not initialized. Please authenticate in the sidebar.")
        return
    
    try:
        season = season or datetime.now().year
        
        # Show selected season prominently
        st.info(f"📅 **Viewing Season: {season}**")
        
        # Get league key for selected season
        league_key = get_yahoo_league_key(season)
        
        # Allow manual override
        with st.expander("🔧 Advanced: Override League Key"):
            league_key_input = st.text_input(
                "Yahoo League Key", 
                value=league_key, 
                help="Format: {game_key}.l.{league_id}. Game key changes by year.",
                key=f"yahoo_league_key_{season}"
            )
            if league_key_input:
                league_key = league_key_input
        
        try:
            league = st.session_state.yahoo_client.get_league(league_key)
            league_name = format_yahoo_league_name(league)
            
            st.subheader(f"📊 {league_name} - {season}")
            
            # Tabs for different views
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Standings", "Scoreboard", "Transactions", "League Info"])
            
            with tab1:
                st.subheader("League Overview")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Name:** {league_name}")
                    if isinstance(league, dict):
                        st.write(f"**Season:** {league.get('season', season)}")
                        st.write(f"**Teams:** {league.get('num_teams', 'N/A')}")
            
            with tab2:
                st.subheader("League Standings")
                standings_df = get_yahoo_standings(league_key)
                if not standings_df.empty:
                    st.dataframe(standings_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No standings data available")
            
            with tab3:
                st.subheader("Scoreboard")
                week = st.number_input("Week", min_value=1, max_value=18, value=1, key=f"yahoo_week_{season}")
                scoreboard = st.session_state.yahoo_client.get_league_scoreboard(league_key, week)
                st.json(scoreboard)
            
            with tab4:
                display_transactions_tab(league_key, season, "Yahoo")
            
            with tab5:
                st.subheader("League Settings")
                if isinstance(league, dict):
                    st.json(league)
                else:
                    st.json({"league": str(league)})
        
        except Exception as league_error:
            error_msg = str(league_error)
            if "404" in error_msg or "not found" in error_msg.lower():
                st.error(f"❌ **League not found for {season}**")
                st.info(f"""
                **Possible reasons:**
                1. The league didn't exist in {season}
                2. The game_key for {season} is incorrect (currently using: `{league_key.split('.')[0]}`)
                3. The league ID changed
                
                **To fix:**
                - Check if the league existed in {season}
                - Verify the game_key for {season} in the Yahoo Developer console
                - Use the "Advanced: Override League Key" section above to manually enter the correct league key
                """)
            else:
                st.error(f"Error loading Yahoo data: {error_msg}")
                st.info("Make sure you're authenticated and the league key is correct.")
    
    except Exception as e:
        st.error(f"Error loading Yahoo data: {str(e)}")
        st.info("Make sure you're authenticated and the league key is correct.")

def display_merged_stats(season: int = None):
    """Display merged stats from both Sleeper and Yahoo leagues"""
    st.header("📊 Merged League Statistics")
    
    try:
        season = season or datetime.now().year
        
        # Show selected season prominently
        st.info(f"📅 **Viewing Season: {season}**")
        
        # Check if season is before Sleeper era
        sleeper_available = season >= 2021
        yahoo_available = True  # Yahoo has all years
        
        if not sleeper_available:
            st.info(f"ℹ️ **Note:** {season} was before your league moved to Sleeper. Only Yahoo data will be shown.")
        
        # Get Sleeper league ID for selected season (if available)
        sleeper_league_id = None
        sleeper_league = None
        sleeper_name = None
        sleeper_standings = pd.DataFrame()
        
        if sleeper_available:
            sleeper_league_id = get_sleeper_league_id(season)
            if sleeper_league_id:
                try:
                    sleeper_league = st.session_state.sleeper_client.get_league(sleeper_league_id)
                    sleeper_name = format_sleeper_league_name(sleeper_league)
                    sleeper_standings = get_sleeper_standings(sleeper_league_id)
                except Exception as e:
                    st.warning(f"Could not load Sleeper data for {season}: {str(e)}")
        
        # Get Yahoo data (always available)
        league_key = get_yahoo_league_key(season)
        try:
            yahoo_league = st.session_state.yahoo_client.get_league(league_key)
            yahoo_name = format_yahoo_league_name(yahoo_league)
            yahoo_standings = get_yahoo_standings(league_key)
        except Exception as e:
            st.warning(f"Could not load Yahoo data for {season}: {str(e)}")
            yahoo_league = None
            yahoo_name = None
            yahoo_standings = pd.DataFrame()
        
        # Display league info
        col1, col2 = st.columns(2)
        with col1:
            if sleeper_available and sleeper_league:
                st.metric("Sleeper League", sleeper_name)
                st.metric("Teams", sleeper_league.get('total_rosters', 'N/A'))
            else:
                st.metric("Sleeper League", "Not Available")
                st.metric("Teams", "N/A")
        with col2:
            if yahoo_league:
                st.metric("Yahoo League", yahoo_name)
                st.metric("Teams", yahoo_standings.shape[0] if not yahoo_standings.empty else 'N/A')
            else:
                st.metric("Yahoo League", "Not Available")
                st.metric("Teams", "N/A")
        
        # Merged standings comparison
        st.subheader("📈 Combined Standings Comparison")
        
        if not sleeper_standings.empty and not yahoo_standings.empty:
            # Create comparison view
            tab1, tab2, tab3 = st.tabs(["Sleeper Standings", "Yahoo Standings", "Side-by-Side"])
            
            with tab1:
                st.write(f"**{sleeper_name}**")
                st.dataframe(sleeper_standings, use_container_width=True, hide_index=True)
            
            with tab2:
                st.write(f"**{yahoo_name}**")
                st.dataframe(yahoo_standings, use_container_width=True, hide_index=True)
            
            with tab3:
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**{sleeper_name}**")
                    st.dataframe(sleeper_standings, use_container_width=True, hide_index=True)
                with col2:
                    st.write(f"**{yahoo_name}**")
                    st.dataframe(yahoo_standings, use_container_width=True, hide_index=True)
        elif not sleeper_standings.empty:
            st.write(f"**{sleeper_name}** (Yahoo data not available)")
            st.dataframe(sleeper_standings, use_container_width=True, hide_index=True)
        elif not yahoo_standings.empty:
            st.write(f"**{yahoo_name}** (Sleeper data not available for {season})")
            st.dataframe(yahoo_standings, use_container_width=True, hide_index=True)
        else:
            st.warning("Unable to load standings from either league.")
        
        # Summary statistics
        st.subheader("📊 Summary Statistics")
        if not sleeper_standings.empty and not yahoo_standings.empty:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                avg_wins_sleeper = sleeper_standings['Wins'].mean()
                st.metric("Avg Wins (Sleeper)", f"{avg_wins_sleeper:.1f}")
            with col2:
                avg_wins_yahoo = yahoo_standings['Wins'].mean()
                st.metric("Avg Wins (Yahoo)", f"{avg_wins_yahoo:.1f}")
            with col3:
                avg_points_sleeper = sleeper_standings['Points For'].mean()
                st.metric("Avg Points (Sleeper)", f"{avg_points_sleeper:.1f}")
            with col4:
                avg_points_yahoo = yahoo_standings['Points For'].mean()
                st.metric("Avg Points (Yahoo)", f"{avg_points_yahoo:.1f}")
        elif not sleeper_standings.empty:
            col1, col2 = st.columns(2)
            with col1:
                avg_wins_sleeper = sleeper_standings['Wins'].mean()
                st.metric("Avg Wins (Sleeper)", f"{avg_wins_sleeper:.1f}")
            with col2:
                avg_points_sleeper = sleeper_standings['Points For'].mean()
                st.metric("Avg Points (Sleeper)", f"{avg_points_sleeper:.1f}")
        elif not yahoo_standings.empty:
            col1, col2 = st.columns(2)
            with col1:
                avg_wins_yahoo = yahoo_standings['Wins'].mean()
                st.metric("Avg Wins (Yahoo)", f"{avg_wins_yahoo:.1f}")
            with col2:
                avg_points_yahoo = yahoo_standings['Points For'].mean()
                st.metric("Avg Points (Yahoo)", f"{avg_points_yahoo:.1f}")
    
    except Exception as e:
        st.error(f"Error loading merged stats: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

def display_transactions_tab(league_id_or_key: str, season: int, platform: str):
    """Display transactions tab with ALL YEARS combined - ignores league_id_or_key and season parameters"""
    # This function now loads ALL years regardless of parameters
    st.subheader(f"📋 {platform} Transaction History (All Years)")
    
    # Get transactions from ALL available years
    try:
        all_transactions_by_year = {}
        current_year = datetime.now().year
        
        # Get available years (2021-2025 for Sleeper, all years for Yahoo)
        if platform == "Sleeper":
            available_years = [y for y in range(2021, current_year + 2) if y in SLEEPER_LEAGUE_IDS]
        else:
            available_years = list(range(current_year, current_year - 10, -1))
        
        st.info(f"🔍 Loading transactions from {len(available_years)} seasons: {available_years}")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, year in enumerate(available_years):
            status_text.text(f"Loading {year}... ({idx+1}/{len(available_years)})")
            progress_bar.progress((idx + 1) / len(available_years))
            
            try:
                if platform == "Sleeper":
                    league_id = get_sleeper_league_id(year)
                    if not league_id:
                        st.warning(f"⚠️ No league ID for {year}, skipping...")
                        continue
                    
                    try:
                        # Call without week parameter - function will iterate through weeks 1-18 internally
                        transactions = st.session_state.sleeper_client.get_league_transactions(league_id)
                        users = st.session_state.sleeper_client.get_league_users(league_id)
                        rosters = st.session_state.sleeper_client.get_league_rosters(league_id)
                        
                        # Get players (cache once)
                        if 'sleeper_players' not in st.session_state:
                            try:
                                st.session_state.sleeper_players = st.session_state.sleeper_client.get_players("nfl")
                            except Exception as e:
                                st.warning(f"Could not load player data: {str(e)}")
                                st.session_state.sleeper_players = None
                        
                        players = st.session_state.sleeper_players
                        
                        # Get player points and lineup data from matchups (Sleeper removed stats endpoint)
                        # We'll fetch matchups for all weeks and extract player points and starting lineups
                        matchup_data_by_week = {}  # {week: {roster_id: {players_points: {}, starters: []}}}
                        try:
                            # Fetch matchups for all weeks (1-18) to get player points and lineups
                            for week_num in range(1, 19):
                                try:
                                    matchups = st.session_state.sleeper_client.get_league_matchups(league_id, week_num)
                                    week_data = {}
                                    for matchup in matchups:
                                        roster_id = matchup.get('roster_id')
                                        if roster_id:
                                            week_data[roster_id] = {
                                                'players_points': matchup.get('players_points', {}),
                                                'starters': matchup.get('starters', [])
                                            }
                                    if week_data:
                                        matchup_data_by_week[week_num] = week_data
                                except:
                                    # Week might not exist yet, skip it
                                    continue
                        except Exception as e:
                            # Matchups might not be available for all years
                            pass
                        
                        from fantasy_football_ui.transactions_helper import parse_sleeper_transactions
                        # Pass matchup data and rosters for calculating post-pickup stats
                        parsed = parse_sleeper_transactions(transactions, users, rosters, players, matchup_data_by_week, year)
                        all_transactions_by_year[year] = parsed
                        st.success(f"✅ {year}: {len(transactions)} raw transactions → {len(parsed.get('trades', []))} trades, {len(parsed.get('waivers', []))} waivers, {len(parsed.get('add_drops', []))} add/drops")
                    except Exception as e:
                        st.error(f"❌ Error loading {year}: {str(e)}")
                        import traceback
                        with st.expander(f"Error details for {year}"):
                            st.code(traceback.format_exc())
                        continue
                    
                else:  # Yahoo
                    if not st.session_state.yahoo_client:
                        st.warning(f"⚠️ Yahoo client not initialized, skipping {year}")
                        continue
                    
                    league_key = get_yahoo_league_key(year)
                    try:
                        transactions_data = st.session_state.yahoo_client.get_league_transactions(league_key)
                        transactions = transactions_data.get('transactions', [])
                        teams_data = st.session_state.yahoo_client.get_league_teams(league_key)
                        teams = teams_data.get('teams', [])
                        
                        from fantasy_football_ui.transactions_helper import parse_yahoo_transactions
                        parsed = parse_yahoo_transactions(transactions, teams)
                        all_transactions_by_year[year] = parsed
                        st.success(f"✅ {year}: {len(transactions)} transactions loaded")
                    except Exception as e:
                        # League might not exist for this year
                        st.warning(f"⚠️ {year}: {str(e)}")
                        continue
            
            except Exception as e:
                # Skip years that fail
                st.error(f"❌ Unexpected error for {year}: {str(e)}")
                continue
        
        progress_bar.empty()
        status_text.empty()
        
        # Combine all years
        from fantasy_football_ui.transactions_combined import (
            combine_transactions_across_years,
            get_top_faab_pickups_all_years,
            get_team_transaction_stats
        )
        from fantasy_football_ui.transactions_helper import get_most_added_dropped
        
        if not all_transactions_by_year:
            st.error("❌ No transaction data loaded from any year!")
            st.info("""
            **Possible reasons:**
            1. All years failed to load
            2. League IDs might be incorrect
            3. API connection issues
            
            **Check the error messages above for details.**
            """)
            return
        
        combined = combine_transactions_across_years(all_transactions_by_year)
        
        all_trades = combined.get('trades', [])
        all_waivers = combined.get('waivers', [])
        all_add_drops = combined.get('add_drops', [])
        
        # Store matchup data and roster mappings by year for trade player stats calculation
        matchup_data_by_year = {}  # {year: {week: {roster_id: {players_points: {}, starters: []}}}}
        roster_mappings_by_year = {}  # {year: {roster_to_team: {}, team_to_roster: {}}}
        player_id_mappings_by_year = {}  # {year: {player_name: player_id}}
        
        # Re-fetch matchup data for Sleeper years (we need to store it for trade analytics)
        if platform == "Sleeper":
            for year in available_years:
                league_id = get_sleeper_league_id(year)
                if not league_id:
                    continue
                
                try:
                    users = st.session_state.sleeper_client.get_league_users(league_id)
                    rosters = st.session_state.sleeper_client.get_league_rosters(league_id)
                    players = st.session_state.sleeper_players
                    
                    if not users or not rosters or not players:
                        continue
                    
                    # Create mappings
                    user_lookup = {user['user_id']: normalize_team_name(user.get('display_name') or user.get('username', 'Unknown')) for user in users}
                    roster_to_team = {}
                    team_to_roster = {}
                    player_name_to_id = {}
                    
                    for roster in rosters:
                        roster_id = roster.get('roster_id')
                        owner_id = roster.get('owner_id')
                        if roster_id and owner_id:
                            team_name = user_lookup.get(owner_id, f"Team {roster_id}")
                            roster_to_team[roster_id] = team_name
                            team_to_roster[team_name] = roster_id
                    
                    if players:
                        for player_id, player_data in players.items():
                            full_name = player_data.get('full_name', '')
                            if not full_name:
                                first = player_data.get('first_name', '')
                                last = player_data.get('last_name', '')
                                full_name = f"{first} {last}".strip()
                            if full_name:
                                player_name_to_id[full_name] = player_id
                    
                    # Fetch matchup data
                    matchup_data = {}
                    for week_num in range(1, 19):
                        try:
                            matchups = st.session_state.sleeper_client.get_league_matchups(league_id, week_num)
                            week_data = {}
                            for matchup in matchups:
                                roster_id = matchup.get('roster_id')
                                if roster_id:
                                    week_data[roster_id] = {
                                        'players_points': matchup.get('players_points', {}),
                                        'starters': matchup.get('starters', [])
                                    }
                            if week_data:
                                matchup_data[week_num] = week_data
                        except:
                            continue
                    
                    matchup_data_by_year[year] = matchup_data
                    roster_mappings_by_year[year] = {'roster_to_team': roster_to_team, 'team_to_roster': team_to_roster}
                    player_id_mappings_by_year[year] = player_name_to_id
                except:
                    continue
        
        # Store in session state for use in trade analytics
        if platform == "Sleeper":
            st.session_state[f'matchup_data_by_year_{platform}'] = matchup_data_by_year
            st.session_state[f'roster_mappings_by_year_{platform}'] = roster_mappings_by_year
            st.session_state[f'player_id_mappings_by_year_{platform}'] = player_id_mappings_by_year
        
        # Show summary
        st.markdown("---")
        st.subheader("📊 Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Trades", len(all_trades))
        with col2:
            st.metric("Total FAAB Waivers", len(all_waivers))
        with col3:
            st.metric("Total Add/Drops", len(all_add_drops))
        with col4:
            st.metric("Years Covered", len(all_transactions_by_year))
        
        # Debug info
        with st.expander("🔍 Debug: Data Summary"):
            st.write(f"**Years loaded:** {list(all_transactions_by_year.keys())}")
            st.write(f"**Total trades:** {len(all_trades)}")
            st.write(f"**Total waivers:** {len(all_waivers)}")
            st.write(f"**Total add/drops:** {len(all_add_drops)}")
            if all_trades:
                st.write("**Sample trade:**")
                import json
                st.json(all_trades[0])
            if all_waivers:
                st.write("**Sample waiver:**")
                st.json(all_waivers[0])
        
        # Create tabs
        trans_tab1, trans_tab2, trans_tab3, trans_tab4, trans_tab5, trans_tab6 = st.tabs([
            "All Trades", "All Transactions", "Top 15 FAAB Pickups", "Most Added Players", 
            "Most Dropped Players", "Team Transaction Stats"
        ])
        
        with trans_tab1:
            st.subheader("All Accepted Trades (All Years)")
            
            if all_trades:
                # Sort by year and then by creation time (newest first)
                all_trades_sorted = sorted(all_trades, key=lambda x: (x.get('year', 0), -x.get('created', 0)), reverse=True)
                
                # Get all unique teams for filter
                all_teams = set()
                for trade in all_trades_sorted:
                    teams = trade.get('teams', [])
                    all_teams.update(teams)
                all_teams_sorted = sorted(list(all_teams))
                
                # Team filter
                col1, col2 = st.columns([3, 1])
                with col1:
                    selected_teams = st.multiselect(
                        "Filter by Team(s)",
                        options=all_teams_sorted,
                        default=[],
                        help="Select one or more teams to filter trades. Leave empty to show all trades."
                    )
                with col2:
                    st.write("")  # Spacing
                    st.write(f"**Total Trades:** {len(all_trades_sorted)}")
                
                # Filter trades if teams are selected
                if selected_teams:
                    filtered_trades = [
                        trade for trade in all_trades_sorted
                        if any(team in selected_teams for team in trade.get('teams', []))
                    ]
                    st.info(f"Showing {len(filtered_trades)} trades involving: {', '.join(selected_teams)}")
                else:
                    filtered_trades = all_trades_sorted
                
                # Create summary table with year, week, teams, and players separated by team
                trade_summary = []
                for trade in filtered_trades:
                    teams = trade.get('teams', [])
                    teams_str = ' vs '.join(teams) if len(teams) == 2 else ', '.join(teams)
                    
                    # Extract week from trade date/timestamp
                    week = 'N/A'
                    if trade.get('created'):
                        try:
                            # NFL season typically starts first week of September
                            # Week 1 is usually around Sept 4-10
                            date_obj = datetime.fromtimestamp(trade.get('created', 0) / 1000)
                            # Rough estimate: week 1 starts around Sept 4
                            season_start = datetime(date_obj.year, 9, 4)
                            days_diff = (date_obj - season_start).days
                            if days_diff >= 0:
                                estimated_week = min((days_diff // 7) + 1, 18)
                                week = estimated_week
                        except:
                            pass
                    elif trade.get('date'):
                        try:
                            date_obj = datetime.strptime(trade.get('date'), '%Y-%m-%d')
                            season_start = datetime(date_obj.year, 9, 4)
                            days_diff = (date_obj - season_start).days
                            if days_diff >= 0:
                                estimated_week = min((days_diff // 7) + 1, 18)
                                week = estimated_week
                        except:
                            pass
                    
                    # Get players by team (who received which players)
                    adds = trade.get('adds', {})  # {player_name: team_name}
                    drops = trade.get('drops', {})  # {player_name: team_name}
                    
                    # Group players by which team received them
                    team_received = {}
                    for player, team in adds.items():
                        if team not in team_received:
                            team_received[team] = []
                        team_received[team].append(player)
                    
                    # Group players by which team traded them away
                    team_traded_away = {}
                    for player, team in drops.items():
                        if team not in team_traded_away:
                            team_traded_away[team] = []
                        team_traded_away[team].append(player)
                    
                    # Create formatted strings for each team
                    if len(teams) == 2:
                        team1, team2 = teams[0], teams[1]
                        team1_received = ', '.join(sorted(team_received.get(team1, []))) or 'None'
                        team2_received = ', '.join(sorted(team_received.get(team2, []))) or 'None'
                        
                        trade_summary.append({
                            'Year': trade.get('year', 'Unknown'),
                            'Week': week,
                            'Team 1': team1,
                            'Team 1 Received': team1_received,
                            'Team 2': team2,
                            'Team 2 Received': team2_received
                        })
                    else:
                        # For trades with more than 2 teams, show all players
                        all_players = set(list(adds.keys()) + list(drops.keys()))
                        players_str = ', '.join(sorted(all_players)) if all_players else 'N/A'
                        trade_summary.append({
                            'Year': trade.get('year', 'Unknown'),
                            'Teams': teams_str,
                            'Players': players_str
                        })
                
                trade_df = pd.DataFrame(trade_summary)
                st.dataframe(trade_df, use_container_width=True, hide_index=True)
                
                # Visualizations Section
                st.markdown("---")
                st.subheader("📊 Trade Analytics")
                
                # Import plotly for charts
                try:
                    import plotly.express as px
                    import plotly.graph_objects as go
                except ImportError:
                    st.error("Plotly is required for charts. Please install it with: pip install plotly")
                    px = None
                    go = None
                
                # 1. Trades per Year
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### Trades per Year")
                    trades_by_year = {}
                    for trade in filtered_trades:
                        year = trade.get('year', 'Unknown')
                        trades_by_year[year] = trades_by_year.get(year, 0) + 1
                    
                    if trades_by_year:
                        year_df = pd.DataFrame({
                            'Year': list(trades_by_year.keys()),
                            'Trades': list(trades_by_year.values())
                        }).sort_values('Year')
                        
                        if px:
                            fig = px.bar(year_df, x='Year', y='Trades', 
                                       title='Trades per Year',
                                       labels={'Year': 'Year', 'Trades': 'Number of Trades'})
                            fig.update_layout(showlegend=False, height=300)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.dataframe(year_df, use_container_width=True, hide_index=True)
                
                # 2. Trades per Team
                with col2:
                    st.markdown("### Trades per Team")
                    trades_by_team = {}
                    for trade in filtered_trades:
                        teams = trade.get('teams', [])
                        for team in teams:
                            trades_by_team[team] = trades_by_team.get(team, 0) + 1
                    
                    if trades_by_team:
                        team_df = pd.DataFrame({
                            'Team': list(trades_by_team.keys()),
                            'Trades': list(trades_by_team.values())
                        }).sort_values('Trades', ascending=False)
                        
                        if px:
                            fig = px.bar(team_df, x='Team', y='Trades',
                                       title='Trades per Team',
                                       labels={'Team': 'Team', 'Trades': 'Number of Trades'})
                            fig.update_layout(showlegend=False, height=300, xaxis_tickangle=-45)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.dataframe(team_df, use_container_width=True, hide_index=True)
                
                # 3. Most Traded Players
                st.markdown("### Most Traded Players")
                player_trade_count = {}
                for trade in filtered_trades:
                    adds = trade.get('adds', {})
                    drops = trade.get('drops', {})
                    # Count players in both adds and drops (they were traded)
                    all_players = set(list(adds.keys()) + list(drops.keys()))
                    for player in all_players:
                        player_trade_count[player] = player_trade_count.get(player, 0) + 1
                
                if player_trade_count:
                    most_traded_df = pd.DataFrame({
                        'Player': list(player_trade_count.keys()),
                        'Times Traded': list(player_trade_count.values())
                    }).sort_values('Times Traded', ascending=False).head(15)
                    st.dataframe(most_traded_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No player trade data available.")
                
                # 4. Detailed Trade Analysis
                st.markdown("### Detailed Trade Analysis")
                st.info("💡 This analysis shows the value of players received vs. players sent away, including points in starting lineup and on bench.")
                
                # Get matchup data from session state (stored during loading)
                matchup_data_by_year = st.session_state.get(f'matchup_data_by_year_{platform}', {})
                roster_mappings_by_year = st.session_state.get(f'roster_mappings_by_year_{platform}', {})
                player_id_mappings_by_year = st.session_state.get(f'player_id_mappings_by_year_{platform}', {})
                
                # Detailed trade analysis - one row per trade
                trade_analyses = []  # List of detailed trade analyses
                
                if platform == "Sleeper" and matchup_data_by_year and roster_mappings_by_year and player_id_mappings_by_year:
                    for trade in filtered_trades:
                        year = trade.get('year')
                        if not year or year not in matchup_data_by_year:
                            continue
                        
                        matchup_data = matchup_data_by_year[year]
                        roster_mappings = roster_mappings_by_year[year]
                        player_id_mapping = player_id_mappings_by_year[year]
                        team_to_roster = roster_mappings.get('team_to_roster', {})
                        
                        adds = trade.get('adds', {})  # {player_name: team_name}
                        drops = trade.get('drops', {})  # {player_name: team_name}
                        teams = trade.get('teams', [])
                        
                        # Only process 2-team trades for now
                        if len(teams) != 2:
                            continue
                        
                        team1, team2 = teams[0], teams[1]
                        roster_id1 = team_to_roster.get(team1)
                        roster_id2 = team_to_roster.get(team2)
                        
                        if not roster_id1 or not roster_id2:
                            continue
                        
                        # Estimate trade week
                        trade_week = 'N/A'
                        if trade.get('created'):
                            try:
                                date_obj = datetime.fromtimestamp(trade.get('created', 0) / 1000)
                                season_start = datetime(date_obj.year, 9, 4)
                                days_diff = (date_obj - season_start).days
                                if days_diff >= 0:
                                    trade_week = min((days_diff // 7) + 1, 18)
                            except:
                                pass
                        
                        if trade_week == 'N/A' or not isinstance(trade_week, int):
                            continue
                        
                        # Helper function to calculate player stats after trade
                        def calc_player_stats_after_trade(players_list, roster_id, trade_week):
                            total_points_lineup = 0.0
                            total_points_bench = 0.0
                            total_starts = 0
                            
                            for player_name in players_list:
                                player_id = player_id_mapping.get(player_name)
                                if not player_id:
                                    continue
                                
                                player_id_str = str(player_id)
                                
                                for week_num in range(trade_week, 19):
                                    if week_num in matchup_data:
                                        week_matchups = matchup_data[week_num]
                                        if roster_id in week_matchups:
                                            team_matchup = week_matchups[roster_id]
                                            starters = team_matchup.get('starters', [])
                                            players_points = team_matchup.get('players_points', {})
                                            
                                            if player_id_str in players_points:
                                                points = players_points[player_id_str]
                                                if points and points > 0:
                                                    if player_id_str in starters:
                                                        total_points_lineup += float(points)
                                                        total_starts += 1
                                                    else:
                                                        # Player was on roster but not in starting lineup
                                                        total_points_bench += float(points)
                            
                            return total_points_lineup, total_points_bench, total_starts
                        
                        # Get players for each team
                        team1_received = [p for p, t in adds.items() if t == team1]
                        team1_sent = [p for p, t in drops.items() if t == team1]
                        team2_received = [p for p, t in adds.items() if t == team2]
                        team2_sent = [p for p, t in drops.items() if t == team2]
                        
                        # Calculate stats for team 1
                        team1_rec_points_lineup, team1_rec_points_bench, team1_rec_starts = calc_player_stats_after_trade(team1_received, roster_id1, trade_week)
                        team2_rec_points_lineup, team2_rec_points_bench, team2_rec_starts = calc_player_stats_after_trade(team2_received, roster_id2, trade_week)
                        
                        # Net points for each team (received - sent, but we only have received stats)
                        # For simplicity, we'll compare received points
                        team1_net = team1_rec_points_lineup
                        team2_net = team2_rec_points_lineup
                        
                        # Determine winner (team with higher net points)
                        if team1_net > team2_net:
                            winner = team1
                            is_fair = abs(team1_net - team2_net) < 20  # Within 20 points is "fair"
                            is_good_value_team1 = True
                            is_good_value_team2 = False
                        elif team2_net > team1_net:
                            winner = team2
                            is_fair = abs(team1_net - team2_net) < 20
                            is_good_value_team1 = False
                            is_good_value_team2 = True
                        else:
                            winner = "Tie"
                            is_fair = True
                            is_good_value_team1 = False
                            is_good_value_team2 = False
                        
                        # Format player lists
                        team1_rec_str = ', '.join(team1_received) if team1_received else 'None'
                        team1_sent_str = ', '.join(team1_sent) if team1_sent else 'None'
                        team2_rec_str = ', '.join(team2_received) if team2_received else 'None'
                        team2_sent_str = ', '.join(team2_sent) if team2_sent else 'None'
                        
                        trade_analyses.append({
                            'Year': year,
                            'Week': trade_week,
                            'Team 1': team1,
                            'Team 1 Received': team1_rec_str,
                            'Team 1 Starts': team1_rec_starts,
                            'Team 1 Points (Lineup)': round(team1_rec_points_lineup, 2),
                            'Team 1 Points (Bench)': round(team1_rec_points_bench, 2),
                            'Team 2': team2,
                            'Team 2 Received': team2_rec_str,
                            'Team 2 Starts': team2_rec_starts,
                            'Team 2 Points (Lineup)': round(team2_rec_points_lineup, 2),
                            'Team 2 Points (Bench)': round(team2_rec_points_bench, 2),
                            'Winner': winner,
                            'Fair Trade': 'Yes' if is_fair else 'No',
                            'Good Value (Team 1)': 'Yes' if is_good_value_team1 else 'No',
                            'Good Value (Team 2)': 'Yes' if is_good_value_team2 else 'No'
                        })
                    
                    if trade_analyses:
                        # Create DataFrame
                        analysis_df = pd.DataFrame(trade_analyses)
                        
                        # Sort by year and week (newest first)
                        analysis_df = analysis_df.sort_values(['Year', 'Week'], ascending=[False, False])
                        
                        # Style the DataFrame to highlight winners and unfair trades
                        def highlight_winner(row):
                            styles = [''] * len(row)
                            
                            # Check if trade is unfair
                            is_unfair = row['Fair Trade'] == 'No'
                            
                            if row['Winner'] == row['Team 1']:
                                # Highlight Team 1 columns
                                team1_cols = ['Team 1', 'Team 1 Received', 'Team 1 Starts', 
                                            'Team 1 Points (Lineup)', 'Team 1 Points (Bench)', 'Good Value (Team 1)']
                                bg_color = '#FFB6C1' if is_unfair else '#90EE90'  # Light red if unfair, light green if fair
                                for col in team1_cols:
                                    if col in analysis_df.columns:
                                        idx = list(analysis_df.columns).index(col)
                                        styles[idx] = f'background-color: {bg_color}'
                            elif row['Winner'] == row['Team 2']:
                                # Highlight Team 2 columns
                                team2_cols = ['Team 2', 'Team 2 Received', 'Team 2 Starts',
                                            'Team 2 Points (Lineup)', 'Team 2 Points (Bench)', 'Good Value (Team 2)']
                                bg_color = '#FFB6C1' if is_unfair else '#90EE90'  # Light red if unfair, light green if fair
                                for col in team2_cols:
                                    if col in analysis_df.columns:
                                        idx = list(analysis_df.columns).index(col)
                                        styles[idx] = f'background-color: {bg_color}'
                            
                            # Highlight Fair Trade column if unfair
                            if is_unfair and 'Fair Trade' in analysis_df.columns:
                                idx = list(analysis_df.columns).index('Fair Trade')
                                styles[idx] = 'background-color: #FFB6C1'  # Light red
                            
                            return styles
                        
                        # Apply styling
                        styled_df = analysis_df.style.apply(highlight_winner, axis=1)
                        st.dataframe(styled_df, use_container_width=True, hide_index=True)
                        
                        # Most Lopsided Trades Table
                        st.markdown("---")
                        st.markdown("### Most Lopsided Trades")
                        st.info("💡 This table shows trades with the biggest point differences, ordered from most lopsided to least.")
                        
                        # Calculate point differences
                        lopsided_trades = []
                        for idx, row in analysis_df.iterrows():
                            team1_points = row['Team 1 Points (Lineup)']
                            team2_points = row['Team 2 Points (Lineup)']
                            point_diff = abs(team1_points - team2_points)
                            
                            if team1_points > team2_points:
                                winner = row['Team 1']
                                winner_points = team1_points
                                loser = row['Team 2']
                                loser_points = team2_points
                            elif team2_points > team1_points:
                                winner = row['Team 2']
                                winner_points = team2_points
                                loser = row['Team 1']
                                loser_points = team1_points
                            else:
                                winner = "Tie"
                                winner_points = team1_points
                                loser = row['Team 2']
                                loser_points = team2_points
                            
                            lopsided_trades.append({
                                'Year': row['Year'],
                                'Week': row['Week'],
                                'Winner': winner,
                                'Winner Points': round(winner_points, 2),
                                'Loser': loser,
                                'Loser Points': round(loser_points, 2),
                                'Point Difference': round(point_diff, 2),
                                'Winner Received': row['Team 1 Received'] if winner == row['Team 1'] else row['Team 2 Received'],
                                'Loser Received': row['Team 1 Received'] if loser == row['Team 1'] else row['Team 2 Received']
                            })
                        
                        if lopsided_trades:
                            lopsided_df = pd.DataFrame(lopsided_trades)
                            # Sort by point difference (largest first)
                            lopsided_df = lopsided_df.sort_values('Point Difference', ascending=False)
                            
                            # Style to highlight the biggest differences
                            def highlight_lopsided(row):
                                styles = [''] * len(row)
                                # Highlight rows with very large differences (top 25% or >50 points)
                                if row['Point Difference'] > 50 or row.name < len(lopsided_df) * 0.25:
                                    for i in range(len(styles)):
                                        styles[i] = 'background-color: #FFE4E1'  # Light red/pink
                                return styles
                            
                            styled_lopsided = lopsided_df.style.apply(highlight_lopsided, axis=1)
                            st.dataframe(styled_lopsided, use_container_width=True, hide_index=True)
                        else:
                            st.info("No lopsided trade data available.")
                        
                        # Summary statistics
                        st.markdown("---")
                        st.markdown("#### Summary")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            fair_trades = len(analysis_df[analysis_df['Fair Trade'] == 'Yes'])
                            st.metric("Fair Trades", fair_trades)
                        with col2:
                            if len(analysis_df) > 0:
                                # Count wins for each unique team
                                all_winners = analysis_df['Winner'].value_counts()
                                if len(all_winners) > 0:
                                    top_winner = all_winners.index[0]
                                    top_winner_wins = all_winners.iloc[0]
                                    st.metric(f"{top_winner} Wins", top_winner_wins)
                                else:
                                    st.metric("Wins", 0)
                            else:
                                st.metric("Wins", 0)
                        with col3:
                            total_trades = len(analysis_df)
                            st.metric("Total Trades Analyzed", total_trades)
                    else:
                        st.info("No detailed trade analysis available.")
                else:
                    st.warning("⚠️ Detailed trade analysis is only available for Sleeper leagues with matchup data.")
                
                # Show all trade details in expandable sections
                st.markdown("---")
                st.subheader("Trade Details")
                for i, trade in enumerate(filtered_trades):
                    teams = trade.get('teams', [])
                    teams_str = ' vs '.join(teams) if len(teams) == 2 else ', '.join(teams)
                    year = trade.get('year', 'Unknown')
                    
                    with st.expander(f"Trade {i+1} - {year} ({teams_str})"):
                        st.write(f"**Year:** {year}")
                        st.write(f"**Teams:** {teams_str}")
                        
                        # Show players by team
                        adds = trade.get('adds', {})
                        drops = trade.get('drops', {})
                        
                        if adds or drops:
                            st.markdown("### Players Involved")
                            
                            # Group by team
                            team_changes = {}
                            for player, team in adds.items():
                                if team not in team_changes:
                                    team_changes[team] = {'adds': [], 'drops': []}
                                team_changes[team]['adds'].append(player)
                            
                            for player, team in drops.items():
                                if team not in team_changes:
                                    team_changes[team] = {'adds': [], 'drops': []}
                                team_changes[team]['drops'].append(player)
                            
                            for team, changes in team_changes.items():
                                st.markdown(f"**{team}:**")
                                if changes['adds']:
                                    st.write(f"  ➕ Received: {', '.join(changes['adds'])}")
                                if changes['drops']:
                                    st.write(f"  ➖ Traded Away: {', '.join(changes['drops'])}")
                        
                        if trade.get('draft_picks'):
                            st.markdown("### Draft Picks")
                            st.json(trade.get('draft_picks', []))
            else:
                st.info("No trades found across all seasons.")
        
        with trans_tab2:
            st.subheader("All Transactions (Adds/Drops) - All Years")
            
            # Combine waivers and add_drops for all transactions
            all_transactions = []
            for waiver in all_waivers:
                waiver['transaction_type'] = 'Waiver'
                all_transactions.append(waiver)
            for add_drop in all_add_drops:
                add_drop['transaction_type'] = 'Free Agent' if add_drop.get('type') == 'free_agent' else 'Add/Drop'
                all_transactions.append(add_drop)
            
            # Filter out transactions with 'N/A' week
            all_transactions = [
                trans for trans in all_transactions
                if trans.get('week') != 'N/A' and trans.get('week') is not None
            ]
            
            # Sort by date (newest first) - use created timestamp if available, otherwise use date string
            def get_sort_timestamp(trans):
                """Get timestamp for sorting - prefer created timestamp, fallback to date string"""
                if trans.get('created'):
                    return trans.get('created')
                elif trans.get('date') and trans.get('date') != 'Unknown':
                    try:
                        return datetime.strptime(trans.get('date'), '%Y-%m-%d').timestamp() * 1000  # Convert to milliseconds
                    except:
                        return 0
                return 0
            
            all_transactions_sorted = sorted(
                all_transactions, 
                key=lambda x: get_sort_timestamp(x),
                reverse=True  # Descending order (newest first)
            )
            
            if all_transactions_sorted:
                # Get all unique teams for filter
                all_teams = set()
                for trans in all_transactions_sorted:
                    team = trans.get('team', '')
                    if team:
                        all_teams.add(team)
                all_teams_sorted = sorted(list(all_teams))
                
                # Team filter
                col1, col2 = st.columns([3, 1])
                with col1:
                    selected_teams = st.multiselect(
                        "Filter by Team(s)",
                        options=all_teams_sorted,
                        default=[],
                        help="Select one or more teams to filter transactions. Leave empty to show all transactions.",
                        key="transactions_team_filter"
                    )
                with col2:
                    st.write("")  # Spacing
                
                # Filter transactions if teams are selected
                if selected_teams:
                    filtered_transactions = [
                        trans for trans in all_transactions_sorted
                        if trans.get('team', '') in selected_teams
                    ]
                    st.info(f"Showing {len(filtered_transactions)} transactions for: {', '.join(selected_teams)}")
                else:
                    filtered_transactions = all_transactions_sorted
                
                # Calculate totals based on filtered transactions
                # Each transaction (add/drop pair) counts as 1 transaction
                total_transactions = len(filtered_transactions)
                total_faab_spent = sum(t.get('faab_bid', 0) or 0 for t in filtered_transactions)
                
                # Show summary metrics (these now reflect the filtered data)
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Transactions", total_transactions)
                with col2:
                    st.metric("Total FAAB Spent", f"${total_faab_spent}")
                
                # Create transaction table
                transaction_data = []
                for trans in filtered_transactions:
                    transaction_data.append({
                        'Year': trans.get('year', 'Unknown'),
                        'Week': trans.get('week', 'N/A'),
                        'Player Added': trans.get('player_name', 'Unknown'),
                        'Player Dropped': trans.get('dropped_player_name', 'N/A'),
                        'FAAB Amount': trans.get('faab_bid', 0) or 0,
                        'Team': trans.get('team', 'Unknown'),
                        'Type': trans.get('transaction_type', 'Unknown')
                    })
                
                transaction_df = pd.DataFrame(transaction_data)
                st.dataframe(transaction_df, use_container_width=True, hide_index=True)
            else:
                st.info("No transactions found across all seasons.")
        
        with trans_tab3:
            st.subheader("FAAB Analysis")
            
            # Get matchup data for calculating points in starting lineup
            matchup_data_by_year = st.session_state.get(f'matchup_data_by_year_{platform}', {})
            roster_mappings_by_year = st.session_state.get(f'roster_mappings_by_year_{platform}', {})
            player_id_mappings_by_year = st.session_state.get(f'player_id_mappings_by_year_{platform}', {})
            
            if all_waivers:
                # Show existing top 15 by FAAB amount
                st.markdown("### Top 15 FAAB Pickups (By Amount Spent)")
                top_faab = get_top_faab_pickups_all_years(all_waivers, limit=15)
                if not top_faab.empty:
                    st.dataframe(top_faab, use_container_width=True, hide_index=True)
                else:
                    st.info("No FAAB bids found.")
                
                # New: Most Valuable FAAB Pickups (by points in starting lineup)
                st.markdown("---")
                st.markdown("### Most Valuable FAAB Pickups (By Points in Starting Lineup)")
                st.info("💡 This shows which FAAB pickups provided the most value based on points scored in the starting lineup.")
                
                if platform == "Sleeper" and matchup_data_by_year and roster_mappings_by_year and player_id_mappings_by_year:
                    valuable_pickups = []
                    
                    for waiver in all_waivers:
                        year = waiver.get('year')
                        if not year or year not in matchup_data_by_year:
                            continue
                        
                        matchup_data = matchup_data_by_year[year]
                        roster_mappings = roster_mappings_by_year[year]
                        player_id_mapping = player_id_mappings_by_year[year]
                        team_to_roster = roster_mappings.get('team_to_roster', {})
                        
                        team_name = waiver.get('team', '')
                        player_name = waiver.get('player_name', '')
                        player_id = waiver.get('player_id', '')
                        faab_bid = waiver.get('faab_bid', 0) or 0
                        week = waiver.get('week', 'N/A')
                        
                        if not team_name or not player_name or week == 'N/A' or not isinstance(week, int):
                            continue
                        
                        roster_id = team_to_roster.get(team_name)
                        if not roster_id:
                            continue
                        
                        # Get player ID from mapping if not already available
                        if not player_id:
                            player_id = player_id_mapping.get(player_name)
                        
                        if not player_id:
                            continue
                        
                        player_id_str = str(player_id)
                        
                        # Calculate points in starting lineup after pickup
                        points_in_lineup = 0.0
                        games_started = 0
                        points_on_bench = 0.0
                        
                        for week_num in range(week, 19):
                            if week_num in matchup_data:
                                week_matchups = matchup_data[week_num]
                                if roster_id in week_matchups:
                                    team_matchup = week_matchups[roster_id]
                                    starters = team_matchup.get('starters', [])
                                    players_points = team_matchup.get('players_points', {})
                                    
                                    if player_id_str in players_points:
                                        points = players_points[player_id_str]
                                        if points and points > 0:
                                            if player_id_str in starters:
                                                points_in_lineup += float(points)
                                                games_started += 1
                                            else:
                                                points_on_bench += float(points)
                        
                        # Calculate value metrics
                        points_per_start = (points_in_lineup / games_started) if games_started > 0 else 0
                        
                        valuable_pickups.append({
                            'Year': year,
                            'Week': week,
                            'Player': player_name,
                            'Team': team_name,
                            'FAAB Spent': faab_bid,
                            'Points (Lineup)': round(points_in_lineup, 2),
                            'Points (Bench)': round(points_on_bench, 2),
                            'Games Started': games_started,
                            'Points per Start': round(points_per_start, 2) if games_started > 0 else 'N/A'
                        })
                    
                    if valuable_pickups:
                        valuable_df = pd.DataFrame(valuable_pickups)
                        # Sort by points in lineup (most valuable first)
                        valuable_df = valuable_df.sort_values('Points (Lineup)', ascending=False)
                        
                        # Show top 25 most valuable
                        st.dataframe(valuable_df.head(25), use_container_width=True, hide_index=True)
                        
                        # Also show sorted by Points per Start
                        st.markdown("#### Best Value (Points per Start)")
                        value_df = valuable_df[valuable_df['Points per Start'] != 'N/A'].copy()
                        if not value_df.empty:
                            value_df = value_df.sort_values('Points per Start', ascending=False)
                            st.dataframe(value_df.head(25), use_container_width=True, hide_index=True)
                    else:
                        st.info("No valuable pickup data available.")
                else:
                    st.warning("⚠️ FAAB value analysis is only available for Sleeper leagues with matchup data.")
            else:
                st.info("No waiver transactions with FAAB bids found.")
        
        with trans_tab4:
            st.subheader("Most Added Players (All Years)")
            
            if all_add_drops:
                stats = get_most_added_dropped(all_add_drops)
                most_added = stats.get('most_added', pd.DataFrame())
                
                if not most_added.empty:
                    st.dataframe(most_added, use_container_width=True, hide_index=True)
                else:
                    st.info("No add transactions found.")
            else:
                st.info("No add/drop transactions found.")
        
        with trans_tab5:
            st.subheader("Most Dropped Players (All Years)")
            
            if all_add_drops:
                stats = get_most_added_dropped(all_add_drops)
                most_dropped = stats.get('most_dropped', pd.DataFrame())
                
                if not most_dropped.empty:
                    st.dataframe(most_dropped, use_container_width=True, hide_index=True)
                else:
                    st.info("No drop transactions found.")
            else:
                st.info("No add/drop transactions found.")
        
        with trans_tab6:
            st.subheader("Team Transaction Statistics (All Years)")
            
            team_stats = get_team_transaction_stats(all_trades, all_waivers, all_add_drops)
            
            if not team_stats.empty:
                st.dataframe(team_stats, use_container_width=True, hide_index=True)
            else:
                st.info("No team statistics available.")
    
    except Exception as e:
        st.error(f"Error loading transactions: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

def display_history_view():
    """Display league history view with season filter and game type selection"""
    from fantasy_football_ui.history_view import display_history_view as display_history
    display_history()

if __name__ == "__main__":
    main()
