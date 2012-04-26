"""
Created on Apr 6, 2012

@author: Clay Carpenter
"""

from gi.repository import Gtk
from coggrinder.authentication import AuthenticationException, AuthenticationService, CredentialsStorage
import errno

class AuthenticationController(object):
    def __init__(self, app=None):
        self.app = app

    def collect_credentials(self):
        """Authenticates the user.

        Attempts to retrieve local credentials. If valid credentials cannot be
        found, this runs the user through the Google Accounts OAuth
        authentication process.

        Raises:
            AuthenticationException: If user could not be authenticated.
        """

        # Attempt to locate valid credentials for the user in a local file.
        # If those credentials cannot be found, prompt the user
        # for permission to proceed with the Google OpenID authentication 
        # process.

        try:
            self.app.auth_service.acquire_credentials_from_local()
        except IOError as io_err:
            # If the credentials file doesn't exist, that's fine. If 
            # anything else caused the error, re-raise it.
            if io_err.errno != errno.ENOENT:
                raise io_err

        # Check to see if local credentials were found. If not, begin the 
        # authentication process. Looping this process gives the user  
        # another chance to complete the Google authentication process if 
        # earlier attempts failed.
        while not self.app.auth_service.has_valid_credentials():
            # Credentials are either missing or invalid, notify the user
            # that an attempt will be made to authenticate them.
            auth_dialog_controller = AuthenticationDialogViewController()

            user_choice = auth_dialog_controller.show_dialog()

            if user_choice == Gtk.ResponseType.CANCEL:
                # User has canceled the authentication process, and the 
                # app cannot proceed.
                raise AuthenticationException(
                    "User terminated the Google authentication process.")
            else:
                # Delete the old dialog.
                auth_dialog_controller.destroy_dialog()

                # Start the user on the Google Accounts authentication 
                # process.
                self.app.auth_service.acquire_credentials_from_oauth()
#------------------------------------------------------------------------------         

class AuthenticationDialogViewController(object):
    def show_dialog(self):
        self.authentication_dialog = Gtk.MessageDialog(None, 0,
            Gtk.MessageType.QUESTION, Gtk.ButtonsType.OK_CANCEL,
            "No valid local credentials could be found.")

        self.authentication_dialog.format_secondary_text(
            "In order to communicate with the Google Tasks service, CogGrinder will need open a browser window to begin the Google Accounts authentication process. Clicking cancel will quit the application.")

        # TODO: This should probably control the placement of the dialog window
        # in some fashion to make sure it is displayed in a consistent 
        # location.
        user_choice = self.authentication_dialog.run()

        return user_choice

    def destroy_dialog(self):
        assert self.authentication_dialog is not None
        self.authentication_dialog.destroy()
#------------------------------------------------------------------------------ 
