"""
Sleeper Fantasy Football API Client
Sleeper API Documentation: https://docs.sleeper.app/
"""

import requests
from typing import Dict, List, Optional, Any
from datetime import datetime


class SleeperClient:
    """Client for interacting with the Sleeper Fantasy Football API"""
    
    BASE_URL = "https://api.sleeper.app/v1"
    
    def __init__(self):
        """Initialize the Sleeper API client"""
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'FantasyFootballAPI/1.0'
        })
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """Make a GET request to the Sleeper API"""
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Re-raise HTTP errors so caller can handle 404s specifically
            # Include the URL in the error for debugging
            error_msg = f"HTTP {e.response.status_code}: {e.response.reason} for url: {url}"
            http_error = requests.exceptions.HTTPError(error_msg, response=e.response)
            raise http_error
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error making request to Sleeper API: {str(e)}")
    
    # User endpoints
    def get_user(self, username: str) -> Dict:
        """Get user information by username"""
        return self._make_request(f"user/{username}")
    
    # League endpoints
    def get_user_leagues(self, user_id: str, sport: str = "nfl", season: str = None) -> List[Dict]:
        """Get all leagues for a user"""
        if season is None:
            season = datetime.now().year
        return self._make_request(f"user/{user_id}/leagues/{sport}/{season}")
    
    def get_league(self, league_id: str) -> Dict:
        """Get league information"""
        return self._make_request(f"league/{league_id}")
    
    def get_league_rosters(self, league_id: str) -> List[Dict]:
        """Get all rosters in a league"""
        return self._make_request(f"league/{league_id}/rosters")
    
    def get_league_users(self, league_id: str) -> List[Dict]:
        """Get all users in a league"""
        return self._make_request(f"league/{league_id}/users")
    
    def get_league_matchups(self, league_id: str, week: int) -> List[Dict]:
        """Get matchups for a specific week"""
        return self._make_request(f"league/{league_id}/matchups/{week}")
    
    def get_league_playoff_bracket(self, league_id: str, bracket_id: str = None) -> Dict:
        """Get playoff bracket (winners bracket) for a league"""
        if bracket_id:
            return self._make_request(f"league/{league_id}/winners_bracket/{bracket_id}")
        return self._make_request(f"league/{league_id}/winners_bracket")
    
    def get_league_consolation_bracket(self, league_id: str, bracket_id: str = None) -> Dict:
        """Get consolation bracket (losers bracket/toilet bowl) for a league"""
        if bracket_id:
            return self._make_request(f"league/{league_id}/losers_bracket/{bracket_id}")
        return self._make_request(f"league/{league_id}/losers_bracket")
    
    def get_league_transactions(self, league_id: str, week: int = None) -> List[Dict]:
        """
        Get transactions for a league
        
        Args:
            league_id: League ID
            week: Optional week number. If None, returns all transactions from weeks 1-18.
        
        Returns:
            List of transaction dictionaries
        
        NOTE: Sleeper API REQUIRES week number in URL. Base endpoint /league/{id}/transactions does NOT work.
        This function ALWAYS uses week-specific endpoints: /league/{id}/transactions/{week}
        """
        # CRITICAL: Never call base endpoint - it returns 404
        # Always use week-specific endpoints: /league/{id}/transactions/{week}
        
        if week is not None and week > 0:
            # Get transactions for specific week
            endpoint = f"league/{league_id}/transactions/{week}"
            try:
                result = self._make_request(endpoint)
                return result if isinstance(result, list) else []
            except requests.exceptions.HTTPError as e:
                if e.response and e.response.status_code == 404:
                    # Week doesn't exist yet
                    return []
                raise
            except Exception as e:
                # Week might not exist yet
                if "404" in str(e) or "Not Found" in str(e):
                    return []
                raise
        
        # Get transactions for all weeks (1-18)
        # CRITICAL: Sleeper API requires round/week number in URL: /league/{id}/transactions/<round>
        # The base endpoint /league/{id}/transactions does NOT work and returns 404
        # API docs: GET https://api.sleeper.app/v1/league/<league_id>/transactions/<round>
        # Where <round> is the week number (1-18 for regular season)
        # We MUST iterate through weeks 1-18 and call week-specific endpoints
        all_transactions = []
        errors = []
        successful_weeks = 0
        
        # Iterate through all possible weeks/rounds (1-18 for regular season)
        for w in range(1, 19):
            try:
                # CRITICAL: Always use week/round-specific endpoint - base endpoint doesn't work
                # NEVER call: /league/{id}/transactions (this returns 404)
                # ALWAYS call: /league/{id}/transactions/{round} where round = week number
                # API format: GET /league/<league_id>/transactions/<round>
                endpoint = f"league/{league_id}/transactions/{w}"
                week_transactions = self._make_request(endpoint)
                if week_transactions and isinstance(week_transactions, list):
                    all_transactions.extend(week_transactions)
                    successful_weeks += 1
            except requests.exceptions.HTTPError as e:
                if e.response and e.response.status_code == 404:
                    # Week doesn't exist yet (e.g., future weeks, or season hasn't started)
                    # This is normal and expected - skip silently
                    continue
                else:
                    # Non-404 error (e.g., 500, 403) - log it but continue with other weeks
                    errors.append(f"Week {w}: HTTP {e.response.status_code}")
            except Exception as e:
                # Check if it's a 404 error (might be wrapped in Exception)
                error_str = str(e)
                if "404" in error_str or "Not Found" in error_str:
                    # Week doesn't exist yet, skip it
                    continue
                else:
                    # Other error - log it
                    errors.append(f"Week {w}: {error_str}")
        
        # If we got some transactions, return them even if some weeks failed
        if all_transactions:
            return all_transactions
        
        # If no transactions found and we have errors, raise the first one
        if errors:
            raise Exception(f"No transactions found after checking all weeks. Errors: {errors[0]}")
        
        # No transactions found and no errors (all weeks returned 404 or empty)
        # This is normal for leagues with no transactions yet
        return []
    
    def get_league_traded_picks(self, league_id: str) -> List[Dict]:
        """Get traded picks for a league"""
        return self._make_request(f"league/{league_id}/traded_picks")
    
    # Draft endpoints
    def get_league_drafts(self, league_id: str) -> List[Dict]:
        """Get all drafts for a league"""
        return self._make_request(f"league/{league_id}/drafts")
    
    def get_draft(self, draft_id: str) -> Dict:
        """Get draft information"""
        return self._make_request(f"draft/{draft_id}")
    
    def get_draft_picks(self, draft_id: str) -> List[Dict]:
        """Get all picks in a draft"""
        return self._make_request(f"draft/{draft_id}/picks")
    
    def get_draft_traded_picks(self, draft_id: str) -> List[Dict]:
        """Get traded picks in a draft"""
        return self._make_request(f"draft/{draft_id}/traded_picks")
    
    # Player endpoints
    def get_players(self, sport: str = "nfl") -> Dict:
        """Get all players for a sport (cached data)"""
        return self._make_request(f"players/{sport}")
    
    def get_trending_players(self, sport: str = "nfl", type: str = "add", 
                            lookback_hours: int = 24, limit: int = 25) -> List[Dict]:
        """Get trending players (adds/drops)"""
        params = {
            "type": type,
            "lookback_hours": lookback_hours,
            "limit": limit
        }
        return self._make_request(f"players/{sport}/trending", params)
    
    # Projections and stats
    def get_projections(self, sport: str = "nfl", week: int = None, season: str = None) -> Dict:
        """Get player projections"""
        if season is None:
            season = datetime.now().year
        endpoint = f"projections/{sport}/{season}"
        params = {"week": week} if week else None
        return self._make_request(endpoint, params)
    
    def get_stats(self, sport: str = "nfl", week: int = None, season: str = None, 
                  position: str = None) -> Dict:
        """Get player stats"""
        if season is None:
            season = datetime.now().year
        endpoint = f"stats/{sport}/{season}"
        params = {}
        if week:
            params["week"] = week
        if position:
            params["position"] = position
        return self._make_request(endpoint, params if params else None)
    
    # Sport state
    def get_sport_state(self, sport: str = "nfl") -> Dict:
        """Get current state of the sport (week, season, etc.)"""
        return self._make_request(f"state/{sport}")


