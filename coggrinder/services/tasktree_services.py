'''
Created on Apr 26, 2012

@author: Clay Carpenter
'''

import unittest
import apiclient.discovery
from coggrinder.services.task_services import TaskService, TaskListService

class TaskTreeService(object):
    def __init__(self, auth_service=None):
        self.auth_service = auth_service

        self.gtasks_service_proxy = None

    def connect(self):
        # Create an authenticatable connection for use in communicating with 
        # the Google Task services. 
        auth_http_connection = self.auth_service.build_authenticated_connection()

        # Build the (real) Google Tasks service proxy.
        self.gtasks_service_proxy = apiclient.discovery.build("tasks", "v1",
            http=auth_http_connection)

        # Create the tasklist and task services.
        self.tasklist_service = self._create_tasklist_service()
        self.task_service = self._create_task_service()

    def _create_tasklist_service(self):
        assert self.gtasks_service_proxy is not None
        assert self.gtasks_service_proxy.tasklists() is not None

        tasklist_service = TaskListService(self.gtasks_service_proxy.tasklists())

        return tasklist_service

    def _create_task_service(self):
        assert self.gtasks_service_proxy is not None
        assert self.gtasks_service_proxy.tasks() is not None

        task_service = TaskService(self.gtasks_service_proxy.tasks())

        return task_service
#------------------------------------------------------------------------------

'''
TaskTreeService scratch.

    def refresh_task_data(self):
        """
        Pull updated tasklist and task information from the Google Task
        services. Store the updated results locally before refreshing the UI
        task tree.
        """
        # Pull updated tasklists and tasks from the services.
        self._tasklists = self.tasklist_service.get_all_tasklists()

        self._tasks = dict()
        for tasklist_id in self._tasklists:
            # Find all tasks for the current tasklist (by tasklist ID).
            tasklist = self._tasklists[tasklist_id]
            tasks_in_tasklist = self.task_service.get_tasks_in_tasklist(tasklist)

            # Merge the tasks-in-tasklist dict with the current dict of tasks.
            self._tasks.update(tasks_in_tasklist)

        # Update the UI task tree.
        self.view.update_task_tree(self._tasklists, self._tasks)
'''
