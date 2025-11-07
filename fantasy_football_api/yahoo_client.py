"""
Yahoo Fantasy Football API Client
Yahoo Fantasy API Documentation: https://developer.yahoo.com/fantasysports/guide/
Note: Yahoo requires OAuth 1.0 authentication
"""

import requests
from requests_oauthlib import OAuth1
from typing import Dict, List, Optional, Any
import json


class YahooClient:
    """Client for interacting with the Yahoo Fantasy Football API"""
    
    BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"
    OAUTH_BASE_URL = "https://api.login.yahoo.com/oauth/v1"
    
    def __init__(self, consumer_key: str, consumer_secret: str, 
                 access_token: str = None, access_token_secret: str = None):
        """
        Initialize the Yahoo API client
        
        Args:
            consumer_key: Yahoo OAuth consumer key
            consumer_secret: Yahoo OAuth consumer secret
            access_token: OAuth access token (if already authenticated)
            access_token_secret: OAuth access token secret (if already authenticated)
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        
        self.session = requests.Session()
        if access_token and access_token_secret:
            self._set_oauth()
    
    def _set_oauth(self):
        """Set up OAuth authentication"""
        self.oauth = OAuth1(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_token_secret,
            signature_method='HMAC-SHA1',
            signature_type='AUTH_HEADER'
        )
        self.session.auth = self.oauth
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None, 
                     format: str = "json") -> Dict:
        """Make a GET request to the Yahoo Fantasy API"""
        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        params['format'] = format
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            if format == "json":
                return response.json()
            else:
                return response.text
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error making request to Yahoo API: {str(e)}")
    
    def set_access_tokens(self, access_token: str, access_token_secret: str):
        """Update access tokens after OAuth flow"""
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self._set_oauth()
    
    # User/Game endpoints
    def get_user_games(self, game_key: str = None) -> Dict:
        """Get user's games or specific game"""
        if game_key:
            endpoint = f"game/{game_key}"
        else:
            endpoint = "users;use_login=1/games"
        return self._make_request(endpoint)
    
    def get_game(self, game_key: str) -> Dict:
        """Get game information"""
        return self._make_request(f"game/{game_key}")
    
    def get_game_leagues(self, game_key: str) -> Dict:
        """Get leagues for a game"""
        return self._make_request(f"game/{game_key}/leagues")
    
    # League endpoints
    def get_league(self, league_key: str) -> Dict:
        """Get league information"""
        return self._make_request(f"league/{league_key}")
    
    def get_league_settings(self, league_key: str) -> Dict:
        """Get league settings"""
        return self._make_request(f"league/{league_key}/settings")
    
    def get_league_standings(self, league_key: str) -> Dict:
        """Get league standings"""
        return self._make_request(f"league/{league_key}/standings")
    
    def get_league_teams(self, league_key: str) -> Dict:
        """Get all teams in a league"""
        return self._make_request(f"league/{league_key}/teams")
    
    def get_league_players(self, league_key: str, start: int = 0, count: int = 25) -> Dict:
        """Get available players in a league"""
        endpoint = f"league/{league_key}/players"
        params = {"start": start, "count": count}
        return self._make_request(endpoint, params)
    
    def get_league_draft_results(self, league_key: str) -> Dict:
        """Get draft results for a league"""
        return self._make_request(f"league/{league_key}/draftresults")
    
    def get_league_transactions(self, league_key: str, transaction_key: str = None) -> Dict:
        """Get transactions for a league"""
        if transaction_key:
            endpoint = f"league/{league_key}/transaction/{transaction_key}"
        else:
            endpoint = f"league/{league_key}/transactions"
        return self._make_request(endpoint)
    
    def get_league_scoreboard(self, league_key: str, week: int = None) -> Dict:
        """Get scoreboard for a league"""
        endpoint = f"league/{league_key}/scoreboard"
        params = {"week": week} if week else None
        return self._make_request(endpoint, params)
    
    # Team endpoints
    def get_team(self, team_key: str) -> Dict:
        """Get team information"""
        return self._make_request(f"team/{team_key}")
    
    def get_team_roster(self, team_key: str, week: int = None) -> Dict:
        """Get team roster"""
        endpoint = f"team/{team_key}/roster"
        params = {"week": week} if week else None
        return self._make_request(endpoint, params)
    
    def get_team_stats(self, team_key: str, week: int = None) -> Dict:
        """Get team stats"""
        endpoint = f"team/{team_key}/stats"
        params = {"week": week} if week else None
        return self._make_request(endpoint, params)
    
    def get_team_matchups(self, team_key: str, week: int = None) -> Dict:
        """Get team matchups"""
        endpoint = f"team/{team_key}/matchups"
        params = {"week": week} if week else None
        return self._make_request(endpoint, params)
    
    # Player endpoints
    def get_player(self, player_key: str) -> Dict:
        """Get player information"""
        return self._make_request(f"player/{player_key}")
    
    def get_player_stats(self, player_key: str, week: int = None) -> Dict:
        """Get player stats"""
        endpoint = f"player/{player_key}/stats"
        params = {"week": week} if week else None
        return self._make_request(endpoint, params)
    
    # Helper methods for common operations
    def get_current_week(self, league_key: str) -> int:
        """Get current week for a league"""
        league = self.get_league(league_key)
        # Parse the response to extract current week
        # This is a simplified version - actual parsing depends on response structure
        try:
            # Yahoo API response structure may vary
            fantasy_content = league.get('fantasy_content', {})
            league_data = fantasy_content.get('league', [{}])[0]
            current_week = league_data.get('current_week', 1)
            return int(current_week)
        except (KeyError, IndexError, ValueError):
            return 1
    
    def get_my_teams(self, game_key: str = "nfl") -> List[Dict]:
        """Get all teams for the authenticated user"""
        games = self.get_user_games()
        # Parse response to get teams
        # This is a simplified version - actual parsing depends on response structure
        teams = []
        try:
            fantasy_content = games.get('fantasy_content', {})
            users = fantasy_content.get('users', [{}])
            for user in users:
                user_teams = user.get('user', [{}])[0].get('games', [{}])[0].get('game', [{}])[0].get('teams', [])
                teams.extend(user_teams)
        except (KeyError, IndexError):
            pass
        return teams



