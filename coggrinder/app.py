"""
Created on Apr 4, 2012

@author: Clay Carpenter
"""
from coggrinder.gui.task_widgets import TaskTreeWindowController
from gi.repository import Gtk
from coggrinder.gui.authentication_widgets import AuthenticationController
from coggrinder.services.authentication_services import AuthenticationService, CredentialsStorage
from coggrinder.services.tasktree_services import TaskTreeService
from coggrinder.preferences import Preferences
import logging
from logging import info

class CogGrinderApp(object):
    def __init__(self, preferences=None):
        self.preferences = preferences
        self.auth_service = None
        self.tasktree_service = None

    def start(self):
        """
        Begin the CogGrinder application by authenticating the user, and then
        creating and starting the controller for the primary app view.
        """
        info("CogGrinder initializing...")
                
        # Begin by establishing the auth service.
        info("Building connection to the task data services.")
        credentials_storage = CredentialsStorage(
            directory_path=self.preferences.config_dir_path)
        self.auth_service = AuthenticationService(storage=credentials_storage)

        # Create the authentication controller and collect_credentials the user.
        auth_controller = AuthenticationController(app=self)
        auth_controller.collect_credentials()

        # I believe that at this point, if the credentials are valid locally, 
        # that is all we can do.
        # Only when the actual request is made will the Google OAuth code 
        # attempt to refresh the access token, and only then when it be known
        # if a user has successfully completed authentication and granted this
        # application access to the Tasks data.

        # Create the TaskTree service, giving it a reference to the auth 
        # service. When connect() is called, TaskTree service will use the
        # auth srvc's credential information to authenticate a new connection
        # to the remote Google Task services. 
        self.tasktree_service = TaskTreeService(auth_service=self.auth_service)
        self.tasktree_service.connect()

        # Create the main UI for the app. Give it a handle to the TaskTree
        # service so it can populate the task tree widget.
        main_controller = TaskTreeWindowController(
            tasktree_service=self.tasktree_service)
        info("Fetching initial task data set.")
        main_controller.refresh_task_data()
        info("Done fetching task data, displaying primary UI.")
        main_controller.show()

        # Begin the main program loop.
        Gtk.main()        
#------------------------------------------------------------------------------ 

if __name__ == '__main__':
    # TODO: Set up logging here.

    # Parse command line arguments.
    preferences = Preferences()
    preferences.parse_cli_arguments()

    # Create and configure the app.
    coggrinder = CogGrinderApp()
    coggrinder.preferences = preferences
    
    # Set up a default logger. Eventually, this should probably be configurable
    # via the app preferences.
    log_format = "%(asctime)s %(levelname)s [%(module)s - %(funcName)s] %(message)s"
    logging.basicConfig(filename='coggrinder.log', filemode='w',
        level=logging.DEBUG, format=log_format)
    
    # Start up the application.
    coggrinder.start()
