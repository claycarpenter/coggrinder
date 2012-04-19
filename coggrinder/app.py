"""
Created on Apr 4, 2012

@author: Clay Carpenter
"""
from coggrinder.gui.task_widgets import TaskTreeWindowController
from gi.repository import Gtk
from coggrinder.authentication_services import AuthenticationService
from coggrinder.gui.authentication_widgets import AuthenticationDialogViewController
from coggrinder.task_services import GoogleTasksServiceProxy

class CogGrinder(object):
    def start(self):
        """
        Begin the CogGrinder application by authenticating the user, and then
        creating and starting the controller for the primary app view.
        """
        main_controller = TaskTreeWindowController()

        # With the UI built, attempt to access the authentication credentials
        # for the user. If those credentials cannot be found, prompt the user
        # for permission to proceed with the Google OpenID authentication 
        # process.
        auth_service = AuthenticationService()
        while not auth_service.has_valid_credentials():
            # Local credentials are either missing or invalid, notify the user
            # that an attempt will be made to authenticate them.
            auth_dialog_controller = AuthenticationDialogViewController(main_controller)
            
            user_choice = auth_dialog_controller.show_dialog()
            
            if user_choice == Gtk.ResponseType.CANCEL:
                # User has canceled the authentication process, and the 
                # app cannot proceed.
                main_controller.view.destroy()
                return
            else:
                # Delete the old dialog.
                auth_dialog_controller.delete_dialog()
                
        # Create an authenticated connection for use in communicating with 
        # the Google Task services. If the user doesn't have valid local
        # credentials, this will begin with running them 
        # through the Google Accounts authentication process.
        auth_http_connection = auth_service.authenticate_connection()
        
        gtasks_service_proxy = GoogleTasksServiceProxy(auth_http_connection)
        
        tasklist_service = gtasks_service_proxy.create_tasklist_service()
        task_service = gtasks_service_proxy.create_task_service()        
        
        tasktree_service = TaskTreeService()
        tasktree_service.tasklist_service = tasklist_service
        tasktree_service.task_service = task_service
        
        main_controller.tasktree_service = tasktree_service
        main_controller.refresh_task_data()
        main_controller.show()
        
        Gtk.main()
#------------------------------------------------------------------------------ 

if __name__ == '__main__':
    # TODO: Set up logging here.
    
    # Start up the application.
    CogGrinder().start()

        
#    # TODO: I think this needs to be moved to the main app module, where it
#    # can determine between testing and live states.
#    def _build_debug_entity_dicts(self):
#        tasklists = dict()
#        tasklist_count = 3
#        for i in range(tasklist_count):
#            tasklist = TaskList()
#            tasklist.entity_id = "tl-{0}".format(i)
#            tasklist.title = "TaskList {0}".format(i)
#            
#            tasklists[tasklist.entity_id] = tasklist
#                
#        expected_task_l1 = Task(entity_id="t-0", title="Task 0", tasklist_id=tasklist.entity_id)
#        expected_task_l2 = Task(entity_id="t-1", title="Task 1", tasklist_id=tasklist.entity_id, parent_id=expected_task_l1.entity_id)
#        tasks = {expected_task_l1.entity_id: expected_task_l1, expected_task_l2.entity_id:expected_task_l2}
#        
#        return (tasklists, tasks)