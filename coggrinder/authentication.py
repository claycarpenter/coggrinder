"""
Created on Mar 19, 2012

@author: Clay Carpenter
"""


import httplib2
import oauth2client.tools
import oauth2client.client
import oauth2client.file
import os
import errno

import unittest
from mockito import mock, when, any
import apiclient.discovery
import datetime
import tempfile

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
        if not self.has_valid_credentials():
            raise AuthenticationException(
                "Cannot authenticate HTTP service connection without valid credentials.")

        # Use the credentials to override the default HTTP implementation with
        # an authorization-aware alternative.
        http = httplib2.Http()
        http = self.credentials.authorize(http)

        # Odd that at this point the access token has expired...
        return http

    def acquire_credentials(self):
        if not self.credentials:
            self.acquire_credentials_from_local()

        if not self.credentials:
            self.acquire_credentials_from_oauth()

        if not self.credentials:
            raise AuthenticationException(
                    "Could not acquire authentication credentials.")

    def acquire_credentials_from_oauth(self):
        # If local credentials aren't present or valid, begin the OAuth process.
        self.credentials = self.oauth_service.get_credentials_from_oauth(self.storage)

    def acquire_credentials_from_local(self):
        # First check to see if local credentials are already present.
        if self.storage is None:
            raise CredentialsRetrievalException("No storage location provided.")

        self.credentials = self.storage.get()

    def has_valid_credentials(self):
        # Ensure that the local credentials are both present and valid.
        if self.credentials is not None and not self.credentials.invalid:
            return True
        else:
            return False

    def create_gtasks_service_proxy(self):
        authorized_http = self.authenticate_connection()
        gtasks_service_proxy = apiclient.discovery.build("tasks", "v1",
            http=authorized_http)
#------------------------------------------------------------------------------ 

class AuthenticationServiceTest(unittest.TestCase):
    def test_authenticate_connection(self):
        mock_http = mock()

        mock_credentials = mock(oauth2client.client.OAuth2Credentials)
        mock_credentials.invalid = False
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
        auth_service.acquire_credentials()

        self.assertIs(expected_credentials, auth_service.credentials)
#------------------------------------------------------------------------------ 

class OAuthService(object):
    CLIENT_ID = "877874321255.apps.googleusercontent.com"
    CLIENT_SECRET = "tYAa2PZSo1QXZC3DiyQeY7Xm"
    SCOPE = "https://www.googleapis.com/auth/tasks"
    USER_AGENT = "coggrinder/0.1"

    # TODO: Couldn't this just be a static method?
    def get_credentials_from_oauth(self, storage):
        # Create the OAuth "flow". This walks the user through the OAuth
        # process (always?) via their browser.        
        oauth_flow = oauth2client.client.OAuth2WebServerFlow(
            OAuthService.CLIENT_ID, OAuthService.CLIENT_SECRET,
            OAuthService.SCOPE, OAuthService.USER_AGENT)

        try:
            # Looks like if the credentials come back, the user has 
            # successfully been authenticated.
            credentials = oauth2client.tools.run(oauth_flow, storage)
            print
        except IOError:
            # Unable to create the credentials file.
            raise CredentialsStorageException(storage.creds_file_path)
        except SystemExit as sysexit:
            # The OAuth tools call sys.exit when the authentication process
            # fails (either if the user denies access, or there is some error
            # in collecting the authentication token).
            # Trap this error and catch it, allowing for a more graceful 
            # response than simply exiting the app.
            raise AuthenticationException(root_cause=sysexit)

        return credentials
#------------------------------------------------------------------------------ 

class AuthenticationException(Exception):
    def __init__(self, root_cause=None):
        if root_cause:
            Exception.__init__(self,
                "Could not authenticate the user. Root cause of the failure: {cause}".format(cause=root_cause))
        else:
            Exception.__init__(self,
                "Could not authenticate the user.")

        self.root_cause = root_cause
#------------------------------------------------------------------------------ 

class CredentialsRetrievalException(AuthenticationException):
    def __init__(self, credentials_filename):
        AuthenticationException.__init__(self,
            root_cause="Could not retrieve the user's authentication credentials from the file {filename}".format(
            filename=credentials_filename))

        self.credentials_filename = credentials_filename
#------------------------------------------------------------------------------ 

class CredentialsStorageException(AuthenticationException):
    def __init__(self, credentials_filename):
        AuthenticationException.__init__(self,
            root_cause="Could not store the user's authentication credentials in the file {filename}".format(
            filename=credentials_filename))

        self.credentials_filename = credentials_filename
#------------------------------------------------------------------------------ 

class CredentialsStorage(object):
    CREDENTIALS_FILENAME = "oauth-credentials.dat"

    def __init__(self, directory_path=None):
        self.directory_path = directory_path
        self._creds_file_path = None

    @property
    def creds_file_path(self):
        """Full file path to the credentials storage file."""
        if self.directory_path is None:
            raise ValueError(
                "Cannot produce a credentials file path without specifying a directory path")

        return os.path.join(self.directory_path,
            CredentialsStorage.CREDENTIALS_FILENAME)

    def put(self, credential):
        """Store the Credentials in the credentials storage file.

        Storage will fail if the directory path has not been specified.

        Raises:
            CredentialsStorageException: If errors occur while writing to the
                credentials storage exception.
        """
        if credential is None:
            raise ValueError("Must provide a Credential object to store.")

        file_contents = credential.to_json()

        try:
            with open(self.creds_file_path, "w") as creds_file:
                creds_file.write(file_contents)
        except (IOError, OSError):
            raise CredentialsStorageException(self.creds_file_path)

    def get(self):
        """Retrieve the Credentials from the credentials file.

        Retrieval will fail if the directory path has not been specified.

        Raises:
            IOError, OSError: If errors occur while reading the file.
        """

        # Attempt to open and read the credentials file.
        with open(self.creds_file_path, "r") as creds_file:
            creds_file_contents = creds_file.read()

        credentials = oauth2client.client.Credentials.new_from_json(creds_file_contents)

        return credentials
#------------------------------------------------------------------------------ 

class CredentialsStorageCredsFilePathTest(unittest.TestCase):
    def setUp(self):
        """Arranges the fixtures for this test suite's test cases.

        Arrange:
            Create CredentialsStorage object.
        """
        self.creds_storage = CredentialsStorage()

    def tearDown(self):
        del self.creds_storage

    def test_creds_file_path(self):
        """Test that the creds file path property is correctly joining the
        directory path and default credentials file name.

        Arrange:
            Establish an expected dir path that points to the system temp
            directory.
            Configure creds storage with expected file path.
            Create an expected creds file path by joining the expected dir path
            and the default credentials file name.
        Act:
            Get the creds file path property from the creds storage instance.
        Assert:
            The actual creds file path matches the combination of expected file
            path and default credentials file name.
        """
        ### Arrange ###
        expected_dir_path = tempfile.gettempdir()
        self.creds_storage.directory_path = expected_dir_path
        expected_creds_file_path = os.path.join(expected_dir_path,
            CredentialsStorage.CREDENTIALS_FILENAME)

        ### Act ###
        actual_creds_file_path = self.creds_storage.creds_file_path

        ### Assert ###
        self.assertEqual(expected_creds_file_path, actual_creds_file_path)

    def test_creds_file_path_no_dir(self):
        """Test that accessing the creds file path property without first
        configuring a directory path raises an error.

        Arrange:
            Implicitly: the blank creds_storage instance will have no
            configured directory path.
        Assert:
            Access the creds file path property raises an error.
        """
        ### Assert ###
        with self.assertRaises(ValueError):
            self.creds_storage.creds_file_path
#------------------------------------------------------------------------------ 

class CredentialsStorageFileStoreTest(unittest.TestCase):
    """
    TODO: Not sure if actually writing to a real file violates unit testing
    best practices...

    Test Cases:

        - tools.py:162
            storage.put(credential)

        - Authentication code calling storage.get()
    """
    def setUp(self):
        """Arranges the fixtures for this test suite's test cases.

        Arrange:
            Create CredentialsStorage object.
            Set the storage location to the system temp directory.
            Create the expected Credentials object.
        """
        self.creds_storage = CredentialsStorage()
        self.expected_directory_path = tempfile.gettempdir()
        self.expected_creds_file_path = os.path.join(
            self.expected_directory_path,
            CredentialsStorage.CREDENTIALS_FILENAME)
        self.creds_storage.directory_path = self.expected_directory_path

        expected_token_expiry = datetime.datetime(2012, 04, 24, 16, 29, 34)
        self.expected_creds = oauth2client.client.OAuth2Credentials(
            "access_token",
            "client_id",
            "client_secret",
            "refresh_token",
            expected_token_expiry,
            "token_uri",
            "user_agent")

        self.expected_prop_values = self._create_comparable_properties(
            self.expected_creds)

    def tearDown(self):
        del self.creds_storage
        del self.expected_directory_path
        del self.expected_creds_file_path
        del self.expected_creds
        del self.expected_prop_values

    def test_put(self):
        """Test storing a credentials file where none currently exists.

        Act:
            Ask CredentialsStorage to store the expected Credentials.
        Assert:
            Implicitly: that the creds file exists.
            Explicitly: that the credentials read from the expected creds file
            create a Credentials object that is equal to the expected
            Credentials.
        """
        ### Act ###     
        self.creds_storage.put(self.expected_creds)

        ### Assert ###        
        try:
            creds_file = open(self.expected_creds_file_path, 'r')
            creds_file_contents = creds_file.read()
            actual_creds = oauth2client.client.Credentials.new_from_json(
                creds_file_contents)

            actual_prop_values = self._create_comparable_properties(
                actual_creds)
            self.assertEqual(self.expected_prop_values, actual_prop_values)
        finally:
            creds_file.close()

    def test_get(self):
        """Test retrieving Credentials from a credentials file.

        Arrange:
            Serialize a simple Credentials object to the system temp directory.
        Act:
            Retrieve the Credentials from CredentialsStorage.
        Assert:
            That the Credentials retrieved are equal to those expected.
        """
        ### Arrange ###        
        try:
            creds_file = open(self.expected_creds_file_path, 'w')
            creds_file_contents = self.expected_creds.to_json()
            creds_file.write(creds_file_contents)
        finally:
            creds_file.close()

        ### Act ###        
        actual_creds = self.creds_storage.get()

        ### Assert ###
        actual_prop_values = self._create_comparable_properties(actual_creds)
        self.assertEqual(self.expected_prop_values, actual_prop_values)

    def _create_comparable_properties(self, credentials):
        property_names = ("access_token", "client_id", "client_secret",
            "refresh_token", "token_expiry", "token_uri", "user_agent",
            "id_token")

        comparable_props = dict()

        for property_name in property_names:
            property_value = getattr(credentials, property_name)

            comparable_props[property_name] = property_value

        return comparable_props
#------------------------------------------------------------------------------ 
