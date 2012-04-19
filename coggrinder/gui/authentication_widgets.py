"""
Created on Apr 6, 2012

@author: Clay Carpenter
"""

from gi.repository import Gtk

class AuthenticationDialogViewController(object):
    def __init__(self, parent_controller):
        self.parent_controller = parent_controller
        
    def show_dialog(self):
        self.authentication_dialog = Gtk.MessageDialog(
            self.parent_controller.view, 0, Gtk.MessageType.QUESTION,
            Gtk.ButtonsType.OK_CANCEL, 
            "No valid local credentials could be found.")
        
        self.authentication_dialog.format_secondary_text(
            "In order to communicate with the Google Tasks service, CogGrinder will need open a browser window to begin the Google Accounts authentication process. Clicking cancel will quit the application.")
        
        user_choice = self.authentication_dialog.run()
        
        print "User chose: {0}".format(user_choice)
        
        return user_choice
    
    def destroy_dialog(self):
        assert self.authentication_dialog is not None
        self.authentication_dialog.destroy()
#------------------------------------------------------------------------------ 
