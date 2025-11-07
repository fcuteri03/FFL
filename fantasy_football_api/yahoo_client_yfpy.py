"""
Yahoo Fantasy Football API Client using yfpy
"""

from yfpy import YahooFantasySportsQuery
from yahoo_oauth import OAuth2
from typing import Dict, List, Optional, Any
from pathlib import Path
import os


class YahooClientYFPY:
    """Client for interacting with the Yahoo Fantasy Football API using yfpy"""
    
    def __init__(self, consumer_key: str, consumer_secret: str, 
                 access_token: str = None, access_token_secret: str = None,
                 game_id: str = "nfl", game_code: str = "nfl"):
        """
        Initialize the Yahoo API client using yfpy
        
        Args:
            consumer_key: Yahoo OAuth consumer key
            consumer_secret: Yahoo OAuth consumer secret
            access_token: OAuth access token (if already authenticated)
            access_token_secret: OAuth access token secret (if already authenticated)
            game_id: Yahoo game ID (default: "nfl")
            game_code: Yahoo game code (default: "nfl")
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.game_id = game_id
        self.game_code = game_code
        
        # Set up OAuth
        self.oauth = None
        self.query = None
        
        if access_token and access_token_secret:
            self._initialize_query()
    
    def _initialize_query(self):
        """Initialize the yfpy query object"""
        try:
            # Create a temporary token file for yahoo-oauth
            token_dir = Path.home() / ".yfpy"
            token_dir.mkdir(exist_ok=True)
            token_file = token_dir / "oauth2.json"
            
            # Save token if we have it
            if self.access_token and self.access_token_secret:
                import json
                token_data = {
                    "consumer_key": self.consumer_key,
                    "consumer_secret": self.consumer_secret,
                    "access_token": self.access_token,
                    "access_token_secret": self.access_token_secret
                }
                with open(token_file, 'w') as f:
                    json.dump(token_data, f)
            
            # Initialize OAuth
            self.oauth = OAuth2(
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                from_file=str(token_file) if token_file.exists() else None
            )
            
            # Initialize query
            self.query = YahooFantasySportsQuery(
                self.game_id,
                self.game_code,
                oauth=self.oauth
            )
        except Exception as e:
            raise Exception(f"Error initializing yfpy query: {str(e)}")
    
    def authenticate(self, callback_uri: str = "http://localhost"):
        """
        Authenticate with Yahoo OAuth
        
        Args:
            callback_uri: OAuth callback URI
            
        Returns:
            Tuple of (access_token, access_token_secret)
        """
        try:
            token_dir = Path.home() / ".yfpy"
            token_dir.mkdir(exist_ok=True)
            token_file = token_dir / "oauth2.json"
            
            # Initialize OAuth
            self.oauth = OAuth2(
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                from_file=str(token_file) if token_file.exists() else None
            )
            
            # If token file doesn't exist, we need to authenticate
            if not token_file.exists() or not self.oauth.token_is_valid():
                # This will open browser for authentication
                self.oauth.refresh_access_token()
            
            # Get tokens
            if hasattr(self.oauth, 'token'):
                self.access_token = self.oauth.token.get('oauth_token', '')
                self.access_token_secret = self.oauth.token.get('oauth_token_secret', '')
            
            # Initialize query
            self._initialize_query()
            
            return self.access_token, self.access_token_secret
        except Exception as e:
            raise Exception(f"Authentication error: {str(e)}")
    
    def get_league(self, league_key: str) -> Dict:
        """Get league information"""
        if not self.query:
            self._initialize_query()
        
        try:
            # yfpy uses league_id format: 414.l.572651
            league = self.query.get_league(league_key)
            return self._league_to_dict(league)
        except Exception as e:
            raise Exception(f"Error getting league: {str(e)}")
    
    def get_league_standings(self, league_key: str) -> Dict:
        """Get league standings"""
        if not self.query:
            self._initialize_query()
        
        try:
            league = self.query.get_league(league_key)
            standings = league.standings
            return self._standings_to_dict(standings)
        except Exception as e:
            raise Exception(f"Error getting standings: {str(e)}")
    
    def get_league_teams(self, league_key: str) -> Dict:
        """Get all teams in a league"""
        if not self.query:
            self._initialize_query()
        
        try:
            league = self.query.get_league(league_key)
            teams = league.teams
            return self._teams_to_dict(teams)
        except Exception as e:
            raise Exception(f"Error getting teams: {str(e)}")
    
    def get_league_scoreboard(self, league_key: str, week: int = None) -> Dict:
        """Get scoreboard for a league"""
        if not self.query:
            self._initialize_query()
        
        try:
            league = self.query.get_league(league_key)
            if week:
                scoreboard = league.scoreboard(week)
            else:
                scoreboard = league.scoreboard()
            return self._scoreboard_to_dict(scoreboard)
        except Exception as e:
            raise Exception(f"Error getting scoreboard: {str(e)}")
    
    def _league_to_dict(self, league) -> Dict:
        """Convert yfpy league object to dictionary"""
        try:
            return {
                'name': getattr(league, 'name', 'Unknown'),
                'league_key': getattr(league, 'league_key', ''),
                'league_id': getattr(league, 'league_id', ''),
                'season': getattr(league, 'season', ''),
                'num_teams': getattr(league, 'num_teams', 0),
                'current_week': getattr(league, 'current_week', 1)
            }
        except Exception:
            return {}
    
    def _standings_to_dict(self, standings) -> Dict:
        """Convert yfpy standings to dictionary"""
        try:
            teams_data = []
            # yfpy returns standings as a list or object with teams
            if hasattr(standings, 'teams'):
                teams = standings.teams
            elif isinstance(standings, list):
                teams = standings
            else:
                teams = [standings]
            
            for team in teams:
                try:
                    # Try to get team data from yfpy object
                    team_standings = getattr(team, 'team_standings', {})
                    outcome_totals = getattr(team_standings, 'outcome_totals', {}) if hasattr(team_standings, 'outcome_totals') else {}
                    
                    teams_data.append({
                        'team_key': getattr(team, 'team_key', ''),
                        'name': getattr(team, 'name', 'Unknown'),
                        'wins': getattr(outcome_totals, 'wins', 0) if hasattr(outcome_totals, 'wins') else outcome_totals.get('wins', 0),
                        'losses': getattr(outcome_totals, 'losses', 0) if hasattr(outcome_totals, 'losses') else outcome_totals.get('losses', 0),
                        'ties': getattr(outcome_totals, 'ties', 0) if hasattr(outcome_totals, 'ties') else outcome_totals.get('ties', 0),
                        'points_for': float(getattr(team_standings, 'points_for', 0) or 0) if hasattr(team_standings, 'points_for') else float(team_standings.get('points_for', 0) or 0),
                        'points_against': float(getattr(team_standings, 'points_against', 0) or 0) if hasattr(team_standings, 'points_against') else float(team_standings.get('points_against', 0) or 0)
                    })
                except Exception as e:
                    # If parsing fails for a team, skip it
                    continue
            return {'teams': teams_data}
        except Exception as e:
            return {'teams': [], 'error': str(e)}
    
    def _teams_to_dict(self, teams) -> Dict:
        """Convert yfpy teams to dictionary"""
        try:
            teams_data = []
            for team in teams:
                teams_data.append({
                    'team_key': getattr(team, 'team_key', ''),
                    'name': getattr(team, 'name', 'Unknown'),
                    'team_id': getattr(team, 'team_id', '')
                })
            return {'teams': teams_data}
        except Exception:
            return {'teams': []}
    
    def _scoreboard_to_dict(self, scoreboard) -> Dict:
        """Convert yfpy scoreboard to dictionary"""
        try:
            matchups = []
            for matchup in scoreboard.matchups:
                matchups.append({
                    'week': getattr(matchup, 'week', ''),
                    'teams': [
                        {
                            'name': getattr(team, 'name', ''),
                            'points': float(getattr(team, 'team_points', {}).get('total', 0) or 0)
                        }
                        for team in getattr(matchup, 'teams', [])
                    ]
                })
            return {'matchups': matchups}
        except Exception:
            return {'matchups': []}
    
    def get_league_transactions(self, league_key: str, transaction_type: str = None) -> Dict:
        """Get transactions for a league"""
        if not self.query:
            self._initialize_query()
        
        try:
            league = self.query.get_league(league_key)
            # yfpy may have transactions method
            if hasattr(league, 'transactions'):
                transactions = league.transactions
                return self._transactions_to_dict(transactions)
            else:
                # Try alternative method
                return {'transactions': []}
        except Exception as e:
            raise Exception(f"Error getting transactions: {str(e)}")
    
    def _transactions_to_dict(self, transactions) -> Dict:
        """Convert yfpy transactions to dictionary"""
        try:
            transactions_data = []
            if hasattr(transactions, 'transactions'):
                trans_list = transactions.transactions
            elif isinstance(transactions, list):
                trans_list = transactions
            else:
                trans_list = [transactions]
            
            for trans in trans_list:
                try:
                    trans_type = getattr(trans, 'type', '')
                    transactions_data.append({
                        'transaction_key': getattr(trans, 'transaction_key', ''),
                        'transaction_id': getattr(trans, 'transaction_id', ''),
                        'type': trans_type,
                        'status': getattr(trans, 'status', ''),
                        'timestamp': getattr(trans, 'timestamp', ''),
                        'players': getattr(trans, 'players', []),
                        'faab_bid': getattr(trans, 'faab_bid', 0) if hasattr(trans, 'faab_bid') else 0,
                    })
                except Exception:
                    continue
            return {'transactions': transactions_data}
        except Exception as e:
            return {'transactions': [], 'error': str(e)}

