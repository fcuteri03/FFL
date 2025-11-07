"""
OAuth helper for Yahoo Fantasy Football API authentication
"""

from requests_oauthlib import OAuth1Session
from typing import Dict, Tuple, Optional
import webbrowser
from urllib.parse import parse_qs, urlparse


class YahooOAuthHelper:
    """Helper class for Yahoo OAuth 1.0 authentication flow"""
    
    REQUEST_TOKEN_URL = "https://api.login.yahoo.com/oauth/v1/get_request_token"
    AUTHORIZE_URL = "https://api.login.yahoo.com/oauth/v1/request_auth"
    ACCESS_TOKEN_URL = "https://api.login.yahoo.com/oauth/v1/get_token"
    
    # Alternative callback URIs to try if 'oob' doesn't work
    # Yahoo requires a proper URI format
    ALTERNATIVE_CALLBACKS = [
        "http://localhost",
        "http://localhost:8080", 
        "https://localhost",
        "urn:ietf:wg:oauth:2.0:oob",  # OAuth 2.0 out-of-band (some Yahoo apps accept this)
        "oob"  # Try last as fallback
    ]
    
    def __init__(self, consumer_key: str, consumer_secret: str, 
                 callback_uri: str = "http://localhost"):
        """
        Initialize OAuth helper
        
        Args:
            consumer_key: Yahoo OAuth consumer key
            consumer_secret: Yahoo OAuth consumer secret
            callback_uri: OAuth callback URI (default: "http://localhost")
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.callback_uri = callback_uri
        self.oauth_session = None
    
    def get_request_token(self, try_alternatives: bool = True) -> Tuple[str, str]:
        """
        Step 1: Get request token
        
        Args:
            try_alternatives: If True, try alternative callback URIs if default fails
        
        Returns:
            Tuple of (request_token, request_token_secret)
        """
        callbacks_to_try = [self.callback_uri]
        if try_alternatives:
            # Try alternatives if default fails
            callbacks_to_try.extend([cb for cb in self.ALTERNATIVE_CALLBACKS if cb != self.callback_uri])
        
        last_error = None
        for callback_uri in callbacks_to_try:
            try:
                self.oauth_session = OAuth1Session(
                    self.consumer_key,
                    client_secret=self.consumer_secret,
                    callback_uri=callback_uri
                )
                
                fetch_response = self.oauth_session.fetch_request_token(
                    self.REQUEST_TOKEN_URL
                )
                # If successful, update the callback_uri
                self.callback_uri = callback_uri
                return fetch_response.get('oauth_token'), fetch_response.get('oauth_token_secret')
            except Exception as e:
                last_error = e
                # Continue to next callback
                continue
        
        # If all callbacks failed, raise the last error
        error_msg = str(last_error) if last_error else "Unknown error"
        if hasattr(last_error, 'response') and last_error.response is not None:
            try:
                error_msg += f" | Response: {last_error.response.text}"
            except:
                pass
        raise Exception(f"Error getting request token with all callback URIs: {error_msg}")
    
    def get_authorization_url(self, request_token: str) -> str:
        """
        Step 2: Get authorization URL
        
        Args:
            request_token: Request token from step 1
        
        Returns:
            Authorization URL
        """
        return f"{self.AUTHORIZE_URL}?oauth_token={request_token}"
    
    def authorize(self, request_token: str, open_browser: bool = True) -> str:
        """
        Step 2: Open browser for user authorization
        
        Args:
            request_token: Request token from step 1
            open_browser: Whether to automatically open browser
        
        Returns:
            Authorization URL
        """
        auth_url = self.get_authorization_url(request_token)
        
        if open_browser:
            print(f"Opening browser for authorization...")
            print(f"If browser doesn't open, visit: {auth_url}")
            webbrowser.open(auth_url)
        else:
            print(f"Please visit this URL to authorize: {auth_url}")
        
        return auth_url
    
    def get_access_token(self, request_token: str, request_token_secret: str, 
                        verifier: str) -> Tuple[str, str]:
        """
        Step 3: Exchange request token for access token
        
        Args:
            request_token: Request token from step 1
            request_token_secret: Request token secret from step 1
            verifier: OAuth verifier from authorization step
        
        Returns:
            Tuple of (access_token, access_token_secret)
        """
        self.oauth_session = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=request_token,
            resource_owner_secret=request_token_secret,
            verifier=verifier
        )
        
        try:
            fetch_response = self.oauth_session.fetch_access_token(
                self.ACCESS_TOKEN_URL
            )
            return fetch_response.get('oauth_token'), fetch_response.get('oauth_token_secret')
        except Exception as e:
            raise Exception(f"Error getting access token: {str(e)}")
    
    def complete_oauth_flow(self, open_browser: bool = True) -> Tuple[str, str]:
        """
        Complete the full OAuth flow interactively
        
        Args:
            open_browser: Whether to automatically open browser
        
        Returns:
            Tuple of (access_token, access_token_secret)
        """
        print("Step 1: Getting request token...")
        request_token, request_token_secret = self.get_request_token()
        
        print("Step 2: Authorizing application...")
        auth_url = self.authorize(request_token, open_browser)
        
        print("\nAfter authorizing, you will receive a verification code.")
        verifier = input("Enter the verification code: ").strip()
        
        print("Step 3: Getting access token...")
        access_token, access_token_secret = self.get_access_token(
            request_token, request_token_secret, verifier
        )
        
        print("\nOAuth flow completed successfully!")
        print(f"Access Token: {access_token[:20]}...")
        print(f"Access Token Secret: {access_token_secret[:20]}...")
        
        return access_token, access_token_secret

