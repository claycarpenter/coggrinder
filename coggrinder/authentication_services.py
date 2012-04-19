"""
Created on Mar 19, 2012

@author: Clay Carpenter
"""


import httplib2
import oauth2client.tools
import oauth2client.client
import oauth2client.file

import unittest
from mockito import mock, when, any
import apiclient.discovery

class AuthenticationService(object):        
    def __init__(self, credentials=None, storage=None,
            oauth_service=None):
        self.credentials = credentials
        self.storage = storage
        
        # Initialize OAuth service if none was provided.
        if oauth_service is None:
            oauth_service = OAuthService()
        self.oauth_service = oauth_service
        
    def authenticate_connection(self):
        # If credentials aren't already present, acquire them.        
        if self.credentials is None:        
            self.credentials = self.get_credentials()        
        assert self.credentials is not None
        
        # Use the credentials to override the default HTTP implementation with
        # and authorization-aware alternative.
        http = httplib2.Http()
        http = self.credentials.authorize(http)
        
        return http
    
    def get_credentials(self):        
        # First check to see if local credentials are already present.        
        credentials = self.get_local_credentials()
        
        # If local credentials aren't present or valid, begin the OAuth process.
        if not self.has_valid_credentials():
            credentials = self.oauth_service.get_credentials_from_oauth(self.storage)
            # TODO: Add check for credential validity after auth.        
        
        return credentials
    
    def get_local_credentials(self):
        # First check to see if local credentials are already present.
        if self.storage is None:
            self.storage = oauth2client.file.Storage("oauth-credentials.dat")
        
        assert self.storage is not None
        credentials = self.storage.get()
        
        return credentials
    
    def has_valid_credentials(self):
        credentials = self.get_local_credentials()
        
        # Ensure that the local credentials are both present and valid.
        if credentials is not None and not credentials.invalid:
            has_valid_credentials = True
        else:
            has_valid_credentials = False
        
        return has_valid_credentials

    def create_gtasks_service_proxy(self):
        authorized_http = self.authenticate_connection()
        gtasks_service_proxy = apiclient.discovery.build("tasks", "v1",
            http=authorized_http)

class OAuthService(object):
    CLIENT_ID = "877874321255.apps.googleusercontent.com"
    CLIENT_SECRET = "tYAa2PZSo1QXZC3DiyQeY7Xm"
    SCOPE = "https://www.googleapis.com/auth/tasks"
    USER_AGENT = "coggrinder/0.1"
        
    def get_credentials_from_oauth(self, storage):
        # Create the OAuth "flow". This walks the user through the OAuth
        # process (always?) via their browser.        
        oauth_flow = oauth2client.client.OAuth2WebServerFlow(
            OAuthService.CLIENT_ID, OAuthService.CLIENT_SECRET,
            OAuthService.SCOPE, OAuthService.USER_AGENT)
        
        credentials = oauth2client.tools.run(oauth_flow, storage)
        
        return credentials

class AuthenticationServiceTest(unittest.TestCase):
    def test_authenticate_connection(self):
        mock_http = mock()
        
        mock_credentials = mock(oauth2client.client.OAuth2Credentials)
        when(mock_credentials).authorize(any()).thenReturn(mock_http)
        
        auth_service = AuthenticationService(credentials=mock_credentials)
        http = auth_service.authenticate_connection()
        
        self.assertIs(http, mock_http)        
        
    def test_get_credentials_from_storage(self):        
        expected_credentials = mock()
        expected_credentials.invalid = False
        
        mock_storage = mock()
        when(mock_storage).get().thenReturn(expected_credentials)
        
        auth_service = AuthenticationService(storage=mock_storage)
        credentials = auth_service.get_credentials()
        
        self.assertIs(credentials, expected_credentials)
        
