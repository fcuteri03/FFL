"""
Simplified Yahoo OAuth helper for Streamlit
Uses requests_oauthlib directly (no terminal input needed)
"""

from requests_oauthlib import OAuth1Session
from typing import Tuple, Optional
import webbrowser


class YahooOAuthSimple:
    """Simple Yahoo OAuth helper that works in Streamlit"""
    
    REQUEST_TOKEN_URL = "https://api.login.yahoo.com/oauth/v1/get_request_token"
    AUTHORIZE_URL = "https://api.login.yahoo.com/oauth/v1/request_auth"
    ACCESS_TOKEN_URL = "https://api.login.yahoo.com/oauth/v1/get_token"
    
    def __init__(self, consumer_key: str, consumer_secret: str):
        """
        Initialize OAuth helper
        
        Args:
            consumer_key: Yahoo OAuth consumer key
            consumer_secret: Yahoo OAuth consumer secret
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
    
    def get_request_token(self, callback_uri: str = "https://localhost") -> Tuple[str, str, str]:
        """
        Step 1: Get request token and authorization URL
        
        Args:
            callback_uri: OAuth callback URI (default: "https://localhost")
        
        Returns:
            Tuple of (request_token, request_token_secret, authorization_url)
        """
        # Try different callback URIs (Yahoo may require HTTPS)
        callbacks_to_try = [callback_uri, "https://localhost", "http://localhost", "oob", ""]
        
        for cb_uri in callbacks_to_try:
            try:
                oauth_session = OAuth1Session(
                    self.consumer_key,
                    client_secret=self.consumer_secret,
                    callback_uri=cb_uri if cb_uri else None
                )
                
                response = oauth_session.fetch_request_token(self.REQUEST_TOKEN_URL)
                
                request_token = response.get('oauth_token')
                request_token_secret = response.get('oauth_token_secret')
                
                if request_token and request_token_secret:
                    auth_url = f"{self.AUTHORIZE_URL}?oauth_token={request_token}"
                    return request_token, request_token_secret, auth_url
            except Exception as e:
                # Store the last error for debugging
                last_error = e
                continue
        
        # All callbacks failed - provide detailed error
        error_details = []
        if 'last_error' in locals():
            error_str = str(last_error)
            if "401" in error_str or "Unauthorized" in error_str:
                error_details.append("401 Unauthorized - Yahoo is rejecting your request")
                error_details.append("Check: App Status, OAuth Client Type, API Permissions, Redirect URI")
            elif "403" in error_str or "Forbidden" in error_str:
                error_details.append("403 Forbidden - App may not have Fantasy Sports API permission")
            else:
                error_details.append(f"Error: {error_str}")
        
        error_msg = "Failed to get request token with all callback URIs."
        if error_details:
            error_msg += f" {'. '.join(error_details)}"
        error_msg += " Check your Yahoo Developer app configuration."
        
        raise Exception(error_msg)
    
    def get_access_token(self, request_token: str, request_token_secret: str, 
                        verifier: str) -> Tuple[str, str]:
        """
        Step 3: Exchange request token for access token
        
        Args:
            request_token: Request token from step 1
            request_token_secret: Request token secret from step 1
            verifier: OAuth verifier code from user
        
        Returns:
            Tuple of (access_token, access_token_secret)
        """
        oauth_session = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=request_token,
            resource_owner_secret=request_token_secret,
            verifier=verifier
        )
        
        response = oauth_session.fetch_access_token(self.ACCESS_TOKEN_URL)
        
        access_token = response.get('oauth_token')
        access_token_secret = response.get('oauth_token_secret')
        
        if not access_token or not access_token_secret:
            raise Exception("Failed to get access tokens from Yahoo")
        
        return access_token, access_token_secret
    
    def open_authorization_url(self, auth_url: str) -> bool:
        """
        Open authorization URL in browser
        
        Args:
            auth_url: Authorization URL from get_request_token
        
        Returns:
            True if browser opened successfully
        """
        try:
            webbrowser.open(auth_url)
            return True
        except Exception:
            return False

