"""
Created on Mar 18, 2012

@author: Clay Carpenter
"""

from coggrinder.entities.tasks import TaskList, Task
import coggrinder.utilities
import unittest
from mockito import mock, when, verify, any
from datetime import datetime
from coggrinder.entities.properties import TaskStatus, IntConverter, \
    TaskStatusConverter, StrConverter, RFC3339Converter, BooleanConverter
from coggrinder.utilities import GoogleKeywords

class ProxiedService(object):
    def __init__(self, service_proxy):
        self.service_proxy = service_proxy
#------------------------------------------------------------------------------ 

class TaskService(ProxiedService):
    def get_task(self, tasklist_id, task_id):   
        assert (task_id is not None 
            and tasklist_id is not None)  
           
        result_str_dict = self.service_proxy.get(tasklist=tasklist_id, 
            task=task_id).execute()
        task = Task.from_str_dict(result_str_dict)
        
        return task
    
    def add_task(self, task):
        assert (task is not None and task.tasklist_id is not None)
        
        # Create the str dict (JSON formatted data) for the insert request.
        insert_str_dict = task.to_str_dict()
        
        # Store the tasklist ID as it will not be wiped out in the process
        # of creating a new task from the service results.
        tasklist_id = task.tasklist_id
        
        # Submit/execute the insert request and receive the resulting updated
        # task properties.
        if task.parent_id is not None:
            result_str_dict = self.service_proxy.insert(
                tasklist=task.tasklist_id, parent=task.parent_id, 
                body=insert_str_dict).execute()
        else:
            result_str_dict = self.service_proxy.insert(
                tasklist=task.tasklist_id, body=insert_str_dict).execute()
        
        # Re-populate the task with the updated propety information from 
        # Google.
        task = Task.from_str_dict(result_str_dict)
        task.tasklist_id = tasklist_id
        
        return task
    
    def delete_task(self, task):
        assert (task is not None 
            and task.entity_id is not None 
            and task.tasklist_id is not None)
        
        # Execute the delete operation.
        self.service_proxy.delete(tasklist=task.tasklist_id, 
            task=task.entity_id).execute()
        
        # Refresh the task by getting updated properties from the server.
        task = self.get_task(task.tasklist_id, task.entity_id)        
        
        return task
    
    def update_task(self, task):
        assert (task is not None 
            and task.entity_id is not None 
            and task.tasklist_id is not None)
        
        # Create a str dict that holds the task's updated properties.
        update_str_dict = task.to_str_dict()
        
        # Store the tasklist ID temporarily as it will be lost in the Task
        # object as it is re-created with the Google service update response.
        tasklist_id = task.tasklist_id
        
        # Execute the update operation and capture the resulting str dict, 
        # which contains the up-to-date values for the task properties.
        update_result_str_dict = self.service_proxy.update(
            tasklist=tasklist_id, task=task.entity_id,
            body=update_str_dict).execute()
        
        # Replace the Task with a new Task populated with the updated 
        # properties.
        task = Task.from_str_dict(update_result_str_dict)
        task.tasklist_id = tasklist_id
        
        return task
    
    def get_tasks_in_tasklist(self, tasklist):     
        """Return a dictionary of all tasks belonging to the specified TaskList.
         
        Dictionary keys will be entity IDs, values will be the corresponding 
        task instances.
        """   
        # Execute the list operation and store the resulting str dict, which 
        # contains an array/list of results stored under an "items" key.
        assert (tasklist is not None and tasklist.entity_id is not None)
        list_results_str_dict = self.service_proxy.list(tasklist=tasklist.entity_id).execute()
        
        tasks = dict()
        
        # Check to see if the tasklist has any assigned tasks.
        if list_results_str_dict.has_key(GoogleKeywords.ITEMS):               
            for task_str_dict in list_results_str_dict.get(GoogleKeywords.ITEMS):
                # Create a Task to represent the result captured in the str dict.
                task = Task.from_str_dict(task_str_dict)
                
                # Set the tasklist id (this property is maintained locally per
                # session, not provided by the Google service.
                task.tasklist_id = tasklist.entity_id
                
                # Add the resulting Task to the results list.
                tasks[task.entity_id] = task
        
        return tasks
#------------------------------------------------------------------------------ 

class TaskServiceTest(unittest.TestCase):
    def test_get_task_minimal(self):
        tasklist = TaskList()
        tasklist.entity_id = "tasklistid"
        
        expected_task_id = "abcid"
        expected_task_title = "Task title"
        expected_task_updated_date = datetime(2012, 3, 26, 22, 59, 24)
        expected_task_position = 10456
        expected_task_status = TaskStatus.NEEDS_ACTION
        
        result_str_dict = {
            GoogleKeywords.ID: StrConverter().to_str(expected_task_id),
            GoogleKeywords.TITLE: StrConverter().to_str(expected_task_title),
            GoogleKeywords.UPDATED: RFC3339Converter().to_str(expected_task_updated_date),
            GoogleKeywords.POSITION: IntConverter().to_str(expected_task_position),
            GoogleKeywords.STATUS: TaskStatusConverter().to_str(expected_task_status)
        }
        
        mock_service_proxy = mock()
        mock_get_request = mock()
        when(mock_service_proxy).get(tasklist=tasklist.entity_id, task=expected_task_id).thenReturn(mock_get_request)
        when(mock_get_request).execute().thenReturn(result_str_dict)
        
        task_service = TaskService(mock_service_proxy)
        actual_task = task_service.get_task(tasklist.entity_id, expected_task_id)
        
        self.assertIsNotNone(actual_task)
        self.assertEqual(expected_task_id, actual_task.entity_id)
        self.assertEqual(expected_task_title, actual_task.title)
        self.assertEqual(expected_task_updated_date, actual_task.updated_date)
        self.assertEqual(expected_task_position, actual_task.position)
        self.assertEqual(expected_task_status, actual_task.task_status)
    
    def test_get_tasks_in_tasklist(self):
        tasklist = TaskList()
        tasklist.entity_id = "abclistid"
        
        list_result_str_dict = {coggrinder.utilities.GoogleKeywords.ITEMS:[]}
        expected_tasks = dict()
        
        for count in range(1, 4):
            task = Task(entity_id=str(count),
                title="Test Task " + str(count),
                updated_date=datetime(2012, 3, 10, 3, 30, 6),
                parent_id=tasklist.entity_id) 
            
            expected_tasks[task.entity_id] = task
            list_result_str_dict.get(coggrinder.utilities.GoogleKeywords.ITEMS).append(task.to_str_dict())
                     
        # Mock service and request objects.
        mock_service_proxy = mock()
        mock_list_request = mock()        
                    
        when(mock_service_proxy).list(tasklist=tasklist.entity_id).thenReturn(mock_list_request) 
        when(mock_list_request).execute().thenReturn(list_result_str_dict) 
        
        # Establish the TaskService and execute the list request.
        task_service = TaskService(mock_service_proxy)
        actual_tasks = task_service.get_tasks_in_tasklist(tasklist)
        
        self.assertEqual(expected_tasks, actual_tasks) 
    
    def test_update_task_simple(self):
        # IDs used to specify which task to delete and get.
        tasklist = TaskList()
        tasklist.entity_id = "tasklistid"
        
        # Fake an updated update date by capturing a date, adding five minutes,
        # and using that new date as the date source for a str dict that is
        # returned by the fake service proxy?
        existing_updated_date = datetime(2012, 3, 21, 13, 52, 06)
        expected_updated_date = datetime(2012, 3, 21, 13, 57, 06)
        
        input_task = Task()
        input_task.entity_id = "abcid"
        input_task.tasklist_id = tasklist.entity_id
        input_task.title = "Task title"
        input_task.position = 10456 
        input_task.task_status = TaskStatus.COMPLETED
        input_task.updated_date = existing_updated_date
        
        expected_task = Task()
        expected_task.entity_id = input_task.entity_id
        expected_task.tasklist_id = tasklist.entity_id
        expected_task.title = input_task.entity_id
        expected_task.position = input_task.position
        expected_task.task_status = input_task.task_status
        expected_task.updated_date = expected_updated_date
        
        # Mock service and request objects.
        mock_service_proxy = mock()
        mock_update_request = mock()
        
        # Note that this str dict serves as the result of an update operation, 
        # which means that it will include updated properties from the server.
        update_result_str_dict = {
            GoogleKeywords.ID: StrConverter().to_str(expected_task.entity_id),
            GoogleKeywords.TITLE: StrConverter().to_str(expected_task.title),
            GoogleKeywords.UPDATED: RFC3339Converter().to_str(expected_updated_date),
            GoogleKeywords.POSITION: IntConverter().to_str(expected_task.position),
            GoogleKeywords.STATUS: TaskStatusConverter().to_str(expected_task.task_status)
        }
        
        # Set up service proxy mock behavior in order to provide the update
        # method with the necessary backend.
        when(mock_service_proxy).update(tasklist=tasklist.entity_id, task=input_task.entity_id, body=any(dict)).thenReturn(mock_update_request)
        when(mock_update_request).execute().thenReturn(update_result_str_dict)
        
        # Create a new TaskService.
        task_service = TaskService(mock_service_proxy)
        
        # Delete the task, and store the update results.
        actual_task = task_service.update_task(input_task)
        
        # Task should be present and have these updated properties:
        # * update date
        self.assertIsNotNone(actual_task)
        self.assertEqual(expected_updated_date, actual_task.updated_date)
        self.assertEqual(expected_task.entity_id, actual_task.entity_id)
        self.assertEqual(expected_task.tasklist_id, actual_task.tasklist_id)
        self.assertEqual(expected_task.title, actual_task.title)
        self.assertEqual(expected_task.position, actual_task.position)
        self.assertEqual(expected_task.task_status, actual_task.task_status)

    def test_add_task(self):
        tasklist = TaskList()
        tasklist.entity_id = "tasklistid"        
        
        expected_task = Task()
        expected_task.entity_id = "abcid"
        expected_task.tasklist_id = tasklist.entity_id
        expected_task.title = "Task title"
        
        now = datetime.now()
        expected_task_updated_date = datetime(now.year, now.month, now.day,
            now.hour, now.minute, now.second)
        expected_task_position = 10456 
        expected_task_status = TaskStatus.NEEDS_ACTION
        
        result_str_dict = {
            GoogleKeywords.ID: StrConverter().to_str(expected_task.entity_id),
            GoogleKeywords.TITLE: StrConverter().to_str(expected_task.title),
            GoogleKeywords.UPDATED: RFC3339Converter().to_str(expected_task_updated_date),
            GoogleKeywords.POSITION: IntConverter().to_str(expected_task_position),
            GoogleKeywords.STATUS: TaskStatusConverter().to_str(expected_task_status)
        }
        
        mock_service_proxy = mock()
        mock_insert_request = mock()
        when(mock_service_proxy).insert(tasklist=tasklist.entity_id, body=any(dict)).thenReturn(mock_insert_request)
        when(mock_insert_request).execute().thenReturn(result_str_dict)
        
        task_service = TaskService(mock_service_proxy)
        actual_task = task_service.add_task(expected_task)
        
        self.assertIsNotNone(actual_task)
        self.assertEqual(expected_task.entity_id, actual_task.entity_id)
        self.assertEqual(expected_task.tasklist_id, actual_task.tasklist_id)
        self.assertEqual(expected_task.title, actual_task.title)
        self.assertEqual(expected_task_updated_date, actual_task.updated_date)
        self.assertEqual(expected_task_position, actual_task.position)
        self.assertEqual(expected_task_status, actual_task.task_status)
    
    def test_delete_task(self):
        # IDs used to specify which task to delete and get.
        tasklist = TaskList()
        tasklist.entity_id = "tasklistid"
        
        # Fake an updated update date by capturing a date, adding five minutes,
        # and using that new date as the date source for a str dict that is
        # returned by the fake service proxy?
        existing_updated_date = datetime(2012, 3, 21, 13, 52, 06)
        expected_updated_date = datetime(2012, 3, 21, 13, 57, 06)
        
        input_task = Task()
        input_task.entity_id = "abcid"
        input_task.tasklist_id = tasklist.entity_id
        input_task.title = "Task title"
        input_task.position = 10456 
        input_task.task_status = TaskStatus.COMPLETED
        input_task.updated_date = existing_updated_date
        
        expected_task = Task()
        expected_task.entity_id = input_task.entity_id
        expected_task.title = input_task.entity_id
        expected_task.position = input_task.position
        expected_task.task_status = input_task.task_status
        expected_task.updated_date = expected_updated_date
        
        # Mock service and request objects.
        mock_service_proxy = mock()
        mock_delete_request = mock()
        mock_get_request = mock()
        
        # Note that this str dict serves as the result of a subsequent get 
        # called on the same task after that task has been deleted. It includes
        # the expected (mock updated) update date.
        get_result_str_dict = {
            GoogleKeywords.ID: StrConverter().to_str(expected_task.entity_id),
            GoogleKeywords.TITLE: StrConverter().to_str(expected_task.title),
            GoogleKeywords.UPDATED: RFC3339Converter().to_str(expected_updated_date),
            GoogleKeywords.POSITION: IntConverter().to_str(expected_task.position),
            GoogleKeywords.STATUS: TaskStatusConverter().to_str(expected_task.task_status),
            GoogleKeywords.DELETED: BooleanConverter().to_str(True)
        }
        
        # Set up service proxy mock behavior in order to provide the delete
        # method with the necessary backend.
        when(mock_service_proxy).delete(tasklist=tasklist.entity_id, task=input_task.entity_id).thenReturn(mock_delete_request)
        when(mock_delete_request).execute().thenReturn("")
        when(mock_service_proxy).get(tasklist=tasklist.entity_id, task=input_task.entity_id).thenReturn(mock_get_request)
        when(mock_get_request).execute().thenReturn(get_result_str_dict)
        
        # Create a new TaskService.
        task_service = TaskService(mock_service_proxy)
        
        # Delete the task, and store the updated results.
        actual_task = task_service.delete_task(input_task)
        
        # Task should be present and have these updated properties:
        # * update date
        # * deleted
        self.assertIsNotNone(actual_task)
        self.assertEqual(expected_updated_date, actual_task.updated_date)
        self.assertTrue(actual_task.is_deleted, True)
        
    @unittest.skip("Waiting for task tree to be completed before working on this method.")
    def test_move_task_change_parent_task(self):
        """
        Set up a simple hierarchy of three tasks, with task A the parent of 
        B, and B the parent of C.
        
        Move task C up to be a direct child of A.
        
        Check that:
        -- C is a child of A, not B
        -- C is ordered below B (i.e., has a higher position value)
        """
        
        self.assertTrue(False)
        
    @unittest.expectedFailure
    def test_move_task_change_parent_to_tasklist(self):
        """
        Set up a simple hierarchy of two tasks, with task A the parent of 
        B. 
        
        Move task B up to be a direct descendant of the owning tasklist.
        """
        
        self.assertTrue(False)
        
    @unittest.expectedFailure
    def test_move_task_change_position(self):
        """
        Set up a simple hierarchy of three tasks, with task A the parent of 
        both B and C (which are siblings). B initially has a higher position
        than C.
        
        Move C to be the first task under A (higher position than sibling B).
        """        
        
        self.assertTrue(False)
#------------------------------------------------------------------------------

class TaskListService(ProxiedService):    
    def get_all_tasklists(self):     
        """
        Return a dictionary of all tasklists available. Dictionary keys will be
        entity IDs, values will be the corresponding tasklist instances.
        """   
        tasklist_items_dict = self.service_proxy.list().execute()
        
        assert tasklist_items_dict.has_key(coggrinder.utilities.GoogleKeywords.ITEMS)
        
        tasklist_items_list = tasklist_items_dict.get(coggrinder.utilities.GoogleKeywords.ITEMS)
        
        tasklist_result_list = dict()
        for tasklist_dict in tasklist_items_list:
            tasklist = TaskList.from_str_dict(tasklist_dict)
            
            tasklist_result_list[tasklist.entity_id] = tasklist
         
        return tasklist_result_list
    
    def get_tasklist(self, entity_id):        
        tasklist_dict = self.service_proxy.get(tasklist=entity_id).execute()
        
        tasklist = TaskList.from_str_dict(tasklist_dict)
        
        return tasklist
    
    def add_tasklist(self, tasklist):
        tasklist_dict = tasklist.to_str_dict()
                
        # Create a dict with only a 'title' property; it looks like everything
        # else is ignored by the GTask service insert handler.
        keywords = coggrinder.utilities.GoogleKeywords
        filtered_insert_dict = coggrinder.utilities.DictUtilities.filter_dict(tasklist_dict,
            (keywords.TITLE,))
        
        # Execute the insert operation.
        result_dict = self.service_proxy.insert(body=filtered_insert_dict).execute()

        # Convert the resulting dict (which contains assigned ID, updated values
        # from the service) back into a TaskList object.
        tasklist = TaskList.from_str_dict(result_dict)

        return tasklist
    
    def delete_tasklist(self, tasklist):
        # The TaskList must have defined, at a minimum, the id of the TaskList.
        assert tasklist.entity_id is not None
        
        # Execute the delete operation.
        self.service_proxy.delete(tasklist=tasklist.entity_id).execute()
    
    def update_tasklist(self, tasklist):
        """
        This method updates the TaskList using a patch command rather than a
        full update.
        TODO: Enhance this method to only update fields that have been locally
        modified.
        """
        tasklist_dict = tasklist.to_str_dict()
                
        # Create a dict with only the 'title' and 'id' properties.   
        keywords = coggrinder.utilities.GoogleKeywords
        filtered_update_dict = coggrinder.utilities.DictUtilities.filter_dict(tasklist_dict,
            (keywords.TITLE, keywords.ID))
        
        # Execute the update operation.
        result_dict = self.service_proxy.patch(tasklist=tasklist.entity_id,
            body=filtered_update_dict).execute()

        # Convert the resulting dict (which contains updated values  from the 
        # service) back into a TaskList object.
        tasklist = TaskList.from_str_dict(result_dict)

        return tasklist
#------------------------------------------------------------------------------  

class TaskListServiceTest(unittest.TestCase):
    def test_get_tasklist(self):
        expected_tasklist = TaskList(entity_id="1",
            title="Test List Title", updated_date=datetime(2012, 3, 10, 3, 30, 6))
        
        mock_service_proxy = mock()
        mock_get_request = mock()
        when(mock_service_proxy).get(tasklist=expected_tasklist.entity_id).thenReturn(mock_get_request)
        when(mock_get_request).execute().thenReturn(expected_tasklist.to_str_dict())
        
        tasklist_service = TaskListService(mock_service_proxy)
        result_tasklist = tasklist_service.get_tasklist(expected_tasklist.entity_id) 
        
        self.assertEqual(expected_tasklist, result_tasklist)

    def test_get_all_tasklists(self):         
        mock_service_proxy = mock()
        mock_list_request = mock()
                         
        tasklist_items_dict = {coggrinder.utilities.GoogleKeywords.ITEMS:[]}
        expected_tasklists = dict()
        
        for count in range(1, 4):
            tasklist = TaskList(entity_id=str(count),
                title="Test List " + str(count), updated_date=datetime(2012, 3, 10, 3, 30, 6)) 
            
            expected_tasklists[tasklist.entity_id] = tasklist
            tasklist_items_dict.get(coggrinder.utilities.GoogleKeywords.ITEMS).append(tasklist.to_str_dict())
                    
        when(mock_service_proxy).list().thenReturn(mock_list_request) 
        when(mock_list_request).execute().thenReturn(tasklist_items_dict)        
        
        tasklist_service = TaskListService(mock_service_proxy)
        
        result_tasklists = tasklist_service.get_all_tasklists()
        
        self.assertEqual(expected_tasklists, result_tasklists)

    def test_update_list(self):
        """
        TODO: Useless test?
        """
        mock_service_proxy = mock()
        mock_update_request = mock()
        
        tasklist = TaskList(entity_id="abcdfakekey", title="Test List 1",
            updated_date=datetime(2012, 3, 22, 13, 50, 00))
        
        when(mock_service_proxy).patch(tasklist=tasklist.entity_id, body=any(dict)).thenReturn(mock_update_request)
        when(mock_update_request).execute().thenReturn(tasklist.to_str_dict())
                
        tasklist_service = TaskListService(mock_service_proxy)        
        result_tasklist = tasklist_service.update_tasklist(tasklist)
        
        verify(mock_update_request).execute()
        self.assertIsNotNone(result_tasklist)
        self.assertIsNotNone(result_tasklist.entity_id)

    def test_add_list(self):
        mock_service_proxy = mock()
        mock_insert_request = mock()
        
        tasklist = TaskList(entity_id="abcdfakekey", title="Test List 1",
            updated_date=datetime(2012, 3, 22, 13, 50, 00))
        
        when(mock_service_proxy).insert(body=any(dict)).thenReturn(mock_insert_request)
        when(mock_insert_request).execute().thenReturn(tasklist.to_str_dict())
                
        tasklist_service = TaskListService(mock_service_proxy)        
        result_tasklist = tasklist_service.add_tasklist(tasklist)
        
        verify(mock_insert_request).execute()
        self.assertIsNotNone(result_tasklist)
        self.assertIsNotNone(result_tasklist.entity_id)

    def test_delete_list(self):
        """
        As it currently stands, this test seems a bit too much like I'm simply
        writing the delete function twice.
        
        TODO: Useless test?
        """
        mock_service_proxy = mock()
        mock_delete_request = mock()
        
        tasklist = TaskList(entity_id="abcdfakekey", title="Test List 1",
            updated_date=datetime(2012, 3, 22, 13, 50, 00))
        
        when(mock_service_proxy).delete(tasklist=tasklist.entity_id).thenReturn(mock_delete_request)
                
        tasklist_service = TaskListService(mock_service_proxy)        
        tasklist_service.delete_tasklist(tasklist)
        
        verify(mock_delete_request).execute()
#------------------------------------------------------------------------------ 
