"""
Created on Mar 18, 2012

@author: Clay Carpenter
"""

from coggrinder.entities.tasks import TaskList, Task
import coggrinder.utilities
import copy
import string
import unittest
from mockito import mock, when, verify, any
from datetime import datetime
from coggrinder.entities.properties import TaskStatus, IntConverter, TaskStatusConverter, StrConverter, RFC3339Converter, BooleanConverter
from coggrinder.utilities import GoogleKeywords
from coggrinder.core.test import ManagedFixturesTestSupport
import apiclient.discovery

class ProxiedService(object):
    def __init__(self, service_proxy):
        self.service_proxy = service_proxy
#------------------------------------------------------------------------------ 

class AbstractTaskService(object):
    """Abstract class that defines a public interface for accessing Task data.

    This class primarily serves to define an interface, with the publicly
    accessible methods doing little more than providing small argument
    integrity checks before passing off the bulk of the work to the
    implementing descendant classes.

    TODO: It might be the case that this extra class above the implementing
    subclasses is unnecessary.
    """
    def get(self, tasklist_id, task_id):
        assert (task_id is not None
            and tasklist_id is not None)

        task = self._get(tasklist_id, task_id)

        return task

    def _get(self, tasklist_id, task_id):
        raise NotImplementedError

    def insert(self, task):
        assert (task is not None and task.tasklist_id is not None)

        task = self._insert(task)

        return task

    def _insert(self, task):
        raise NotImplementedError

    def delete(self, task):
        assert (task is not None
            and task.entity_id is not None
            and task.tasklist_id is not None)

        task = self._delete(task)

        return task

    def _delete(self, task):
        raise NotImplementedError

    def update(self, task):
        assert (task is not None
            and task.entity_id is not None
            and task.tasklist_id is not None)

        task = self._update(task)

        return task

    def _update(self, task):
        raise NotImplementedError

    """
    TODO: Rename this to list() to stay in line with Google Services API.
    """
    def get_tasks_in_tasklist(self, tasklist):
        """Return a dictionary of all tasks belonging to the specified TaskList.

        Dictionary keys will be entity IDs, values will be the corresponding
        task instances.
        """

        # Execute the list operation and store the resulting str dict, which 
        # contains an array/list of results stored under an "items" key.
        assert (tasklist is not None and tasklist.entity_id is not None)

        tasks = self._get_tasks_in_tasklist(tasklist)

        return tasks

    def _get_tasks_in_tasklist(self, tasklist):
        raise NotImplementedError
#------------------------------------------------------------------------------ 

class GoogleServicesTaskService(AbstractTaskService):
    def __init__(self):
        AbstractTaskService.__init__(self)

        self.service_proxy = None

    def _get(self, tasklist_id, task_id):
        result_str_dict = self.service_proxy.get(tasklist=tasklist_id,
            task=task_id).execute()
        task = Task.from_str_dict(result_str_dict)

        return task

    def _insert(self, task):
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

        # Re-populate the task with the updated property information from 
        # Google.
        task = Task.from_str_dict(result_str_dict)
        task.tasklist_id = tasklist_id

        return task

    def _delete(self, task):
        # Execute the delete operation.
        self.service_proxy.delete(tasklist=task.tasklist_id,
            task=task.entity_id).execute()

        # Refresh the task by getting updated properties from the server.
        task = self.get(task.tasklist_id, task.entity_id)

        return task

    def update(self, task):
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
        task instances. In the case that the TaskList given in the arguments
        does not correspond to a list of Tasks, an empty collection will be 
        returned.
        """
        # Execute the list operation and store the resulting str dict, which 
        # contains an array/list of results stored under an "items" key.
        assert (tasklist is not None and tasklist.entity_id is not None)
        list_results_str_dict = self.service_proxy.list(tasklist=tasklist.entity_id).execute()

        tasks = dict()

        # Check to see if the tasklist has any assigned tasks.
        if list_results_str_dict.has_key(GoogleKeywords.ITEMS):
            for task_str_dict in list_results_str_dict.get(GoogleKeywords.ITEMS):
                # Create a Task to represent the result captured in the 
                # str dict.
                task = Task.from_str_dict(task_str_dict)

                # Set the tasklist id (this property is maintained locally per
                # session, not provided by the Google service.
                task.tasklist_id = tasklist.entity_id

                # Add the resulting Task to the results list.
                tasks[task.entity_id] = task

        return tasks
#------------------------------------------------------------------------------ 

class GoogleServicesTaskServiceTest(unittest.TestCase, ManagedFixturesTestSupport):
    def setUp(self):
        """Established basic fixtures mimicking the Google Tasks service proxy."""
        self.tasklist_service = GoogleServicesTaskService()
        
        """
        TODO: Investigate mock test stalling issues discussed below.
        
        This should be the proper way to build the mock service proxy:
            self.mock_service_proxy = mock(
               apiclient.discovery.build("tasks", "v1").tasks())
               
        However, for some reason this seems to stall out (possibly because
        of a missing/fake authenticated HTTP connection?), and causes the tests
        to take much, much longer to execute (<1s to >8s).
        """
        self.mock_service_proxy = mock()
        self.tasklist_service.service_proxy = self.mock_service_proxy

        self._register_fixtures(self.tasklist_service, self.mock_service_proxy)

    def test_get_minimal(self):
        ### Arrange ###        
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

        mock_get_request = mock()
        when(self.mock_service_proxy).get(tasklist=tasklist.entity_id, task=expected_task_id).thenReturn(mock_get_request)
        when(mock_get_request).execute().thenReturn(result_str_dict)

        ### Act ###        
        actual_task = self.tasklist_service.get(tasklist.entity_id, expected_task_id)

        ### Assert ###
        self.assertIsNotNone(actual_task)
        self.assertEqual(expected_task_id, actual_task.entity_id)
        self.assertEqual(expected_task_title, actual_task.title)
        self.assertEqual(expected_task_updated_date, actual_task.updated_date)
        self.assertEqual(expected_task_position, actual_task.position)
        self.assertEqual(expected_task_status, actual_task.task_status)

    def test_get_tasks_in_tasklist(self):
        ### Arrange ###
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

        # Mock request object.
        mock_list_request = mock()
        when(self.mock_service_proxy).list(tasklist=tasklist.entity_id).thenReturn(mock_list_request)
        when(mock_list_request).execute().thenReturn(list_result_str_dict)

        ### Act ###
        actual_tasks = self.tasklist_service.get_tasks_in_tasklist(tasklist)

        ### Assert ###
        self.assertEqual(expected_tasks, actual_tasks)

    def test_update_simple(self):
        ### Arrange ###        
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

        # Note that this str dict serves as the result of an update operation, 
        # which means that it will include updated properties from the server.
        update_result_str_dict = {
            GoogleKeywords.ID: StrConverter().to_str(expected_task.entity_id),
            GoogleKeywords.TITLE: StrConverter().to_str(expected_task.title),
            GoogleKeywords.UPDATED: RFC3339Converter().to_str(expected_updated_date),
            GoogleKeywords.POSITION: IntConverter().to_str(expected_task.position),
            GoogleKeywords.STATUS: TaskStatusConverter().to_str(expected_task.task_status)
        }

        # Mock request object.
        mock_update_request = mock()

        # Set up service proxy mock behavior in order to provide the update
        # method with the necessary backend.
        when(self.mock_service_proxy).update(tasklist=tasklist.entity_id,
            task=input_task.entity_id, body=any(dict)).thenReturn(mock_update_request)
        when(mock_update_request).execute().thenReturn(update_result_str_dict)

        ### Act ###        
        # Delete the task, and store the update results.
        actual_task = self.tasklist_service.update(input_task)

        ### Assert ###
        # Task should be present and have these updated properties:
        # * update date
        self.assertIsNotNone(actual_task)
        self.assertEqual(expected_updated_date, actual_task.updated_date)
        self.assertEqual(expected_task.entity_id, actual_task.entity_id)
        self.assertEqual(expected_task.tasklist_id, actual_task.tasklist_id)
        self.assertEqual(expected_task.title, actual_task.title)
        self.assertEqual(expected_task.position, actual_task.position)
        self.assertEqual(expected_task.task_status, actual_task.task_status)

    def test_insert(self):
        ### Arrange ###
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

        mock_insert_request = mock()
        when(self.mock_service_proxy).insert(tasklist=tasklist.entity_id,
            body=any(dict)).thenReturn(mock_insert_request)
        when(mock_insert_request).execute().thenReturn(result_str_dict)

        ### Act ###
        actual_task = self.tasklist_service.insert(expected_task)

        ### Assert ###
        self.assertIsNotNone(actual_task)
        self.assertEqual(expected_task.entity_id, actual_task.entity_id)
        self.assertEqual(expected_task.tasklist_id, actual_task.tasklist_id)
        self.assertEqual(expected_task.title, actual_task.title)
        self.assertEqual(expected_task_updated_date, actual_task.updated_date)
        self.assertEqual(expected_task_position, actual_task.position)
        self.assertEqual(expected_task_status, actual_task.task_status)

    def test_delete(self):
        ### Arrange ###
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

        # Mock request object.
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
        when(self.mock_service_proxy).delete(tasklist=tasklist.entity_id, task=input_task.entity_id).thenReturn(mock_delete_request)
        when(mock_delete_request).execute().thenReturn("")
        when(self.mock_service_proxy).get(tasklist=tasklist.entity_id, task=input_task.entity_id).thenReturn(mock_get_request)
        when(mock_get_request).execute().thenReturn(get_result_str_dict)

        ### Act ###
        # Delete the task, and store the updated results.
        actual_task = self.tasklist_service.delete(input_task)

        ### Assert ###
        # Task should be present and have these updated properties:
        # * update date
        # * deleted
        self.assertIsNotNone(actual_task)
        self.assertEqual(expected_updated_date, actual_task.updated_date)
        self.assertTrue(actual_task.is_deleted, True)

    @unittest.skip("Waiting for task tree to be completed before working on this test.")
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

    @unittest.skip("Waiting for task tree to be completed before working on this test.")
    def test_move_task_change_parent_to_tasklist(self):
        """
        Set up a simple hierarchy of two tasks, with task A the parent of
        B.

        Move task B up to be a direct descendant of the owning tasklist.
        """

        self.assertTrue(False)

    @unittest.skip("Waiting for task tree to be completed before working on this test.")
    def test_move_task_change_position(self):
        """
        Set up a simple hierarchy of three tasks, with task A the parent of
        both B and C (which are siblings). B initially has a higher position
        than C.

        Move C to be the first task under A (higher position than sibling B).
        """

        self.assertTrue(False)
#------------------------------------------------------------------------------

class InMemoryService(object):
    def __init__(self, data_store = None):
        if data_store is None:
            data_store = dict()
            
        self.data_store = data_store
#------------------------------------------------------------------------------ 

class InMemoryTaskService(AbstractTaskService, InMemoryService):
    def _insert(self, task):
        # Update the updated date on the Task.
        task.updated_date = datetime.now()

        # Attempt to retrieve the Tasks collection for the targeted TaskList.
        try:
            tasklists_tasks = self.data_store[task.tasklist_id]
        except KeyError:
            # This is a newly registered TaskList, create a collection to hold
            # the Tasks that belong to it.
            self.data_store[task.tasklist_id] = dict()

        # Ensure that the Task isn't already registered in the data store.
        if task.entity_id in self.data_store[task.tasklist_id]:
            raise EntityOverwriteError(task.tasklist_id)

        # Store the Task.        
        self.data_store[task.tasklist_id][task.entity_id] = task

        return task

    def _delete(self, task):
        try:
            tasklist_tasks = self.data_store[task.tasklist_id]
        except KeyError:
            raise UnregisteredTaskListError(task.tasklist_id)

        if not task.entity_id in tasklist_tasks:
            raise UnregisteredTaskError(task.entity_id)

        # Update the updated date and deleted flags on this Task.
        task.is_deleted = True
        task.updated_date = datetime.now()

        # Remove the deleted task from the data store.
        del tasklist_tasks[task.entity_id]

        return task

    def _get(self, tasklist_id, task_id):
        try:
            tasklist_tasks = self.data_store[tasklist_id]
        except KeyError:
            raise UnregisteredTaskListError(tasklist_id)

        try:
            task = tasklist_tasks[task_id]
        except KeyError:
            raise UnregisteredTaskError(task_id)

        if task.is_deleted:
            raise UnregisteredTaskError(task_id)

        return task

    def _get_tasks_in_tasklist(self, tasklist):
        tasklist_tasks = self.data_store.get(tasklist.entity_id, dict())

        return tasklist_tasks

    def _update(self, task):
        # Check to make sure the Task is already present in the data store.
        if task.tasklist_id not in self.data_store:
            raise UnregisteredTaskListError(task.tasklist_id)

        if task.entity_id not in self.data_store[task.tasklist_id]:
            raise UnregisteredTaskError(task.entity_id)

        # Update the updated date on the Task.
        task.updated_date = datetime.now()

        # Update the task in the data store.        
        self.data_store[task.tasklist_id][task.entity_id] = task

        return task
#------------------------------------------------------------------------------ 

class InMemoryTaskServiceTest(unittest.TestCase, ManagedFixturesTestSupport):
    def setUp(self):
        """Established basic fixture for testing the in-memory Task service."""

        # Create fake master TaskList.
        self.expected_tasklist = TaskList()
        self.expected_tasklist.entity_id = "tasklistid"

        # Create a fake Task data set - a dictionary of dictionaries, with the
        # first dictionary being keyed by the TaskList ID. The inner dictionary
        # has keys that equal that Task IDs, and values that equal the Task
        # instances.
        tasks = {"t-" + string.ascii_uppercase[x]:
            Task(entity_id="t-" + string.ascii_uppercase[x], title="Task " + string.ascii_uppercase[x], tasklist_id=self.expected_tasklist.entity_id)
            for x in range(0, 3)}
        self.expected_task_data = {self.expected_tasklist.entity_id:tasks}

        # Create an InMemoryTaskService that uses the expected data set as its
        # data store. Use a clone so that any changes made by the service don't
        # also affect the expected task data fixtures.
        self.tasklist_service = InMemoryTaskService()
        self.tasklist_service.data_store = copy.deepcopy(self.expected_task_data)

        self._register_fixtures(self.tasklist_service, self.expected_tasklist,
            self.expected_task_data)

    def test_get(self):
        """Test that the InMemoryTaskService can retrieve the correct Task
        given a pair TaskList and Task IDs.

        Arrange:
            - Set the expected Task to be the first Task in the expected
            task data fixture.
        Act:
            - Retrieve the actual Task from the task service using the expected
            TaskList and Task IDs.
        Assert:
            - That the expected Task and actual Task are equal.
        """
        ### Arrange ###        
        expected_task = self.expected_task_data[self.expected_tasklist.entity_id].values()[0]

        ### Act ###        
        actual_task = self.tasklist_service.get(
            self.expected_tasklist.entity_id, expected_task.entity_id)

        ### Assert ###
        self.assertEqual(expected_task, actual_task)

    def test_get_invalid_ids(self):
        """Test that the InMemoryTaskService raises an error when asked to
        retrieved a Task with a Task or TaskList ID that isn't registered.

        Arrange:
            - Establish fake/unregistered Task and TaskList IDs to query for.
            - Establish a valid Task and TaskList ID to pair with the opposite
            query parameters (i.e., task with tasklist).
        Assert:
            - That asking for the Task associated with the following
            combinations of IDs raises an error:
                - Registered TaskList, unregistered Task
                - Unregistered TaskList, registered Task
                - Unregistered TaskList, unregistered Task
        """
        ### Arrange ###        
        reg_task_id = self.expected_task_data[self.expected_tasklist.entity_id].keys()[0]
        reg_tasklist_id = self.expected_tasklist.entity_id
        unreg_task_id = "fake-task-id"
        unreg_tasklist_id = "fake-tasklist-id"

        ### Assert ###
        with self.assertRaises(UnregisteredTaskError):
            self.tasklist_service.get(reg_tasklist_id, unreg_task_id)
        with self.assertRaises(UnregisteredTaskListError):
            self.tasklist_service.get(unreg_tasklist_id, reg_task_id)
        with self.assertRaises(UnregisteredTaskListError):
            self.tasklist_service.get(unreg_tasklist_id, unreg_task_id)

    def test_get_tasks_in_tasklist(self):
        """Test that the InMemoryTaskService can retrieve all of the Tasks
        belonging to a specific TaskList.

        Act:
            - Get all Tasks associated with the expected TaskList fixture.
        Assert:
            - That the actual and expected Tasks collections are identical.
        """
        ### Act ###
        actual_tasks = self.tasklist_service.get_tasks_in_tasklist(self.expected_tasklist)

        ### Assert ###
        self.assertEqual(
            self.expected_task_data[self.expected_tasklist.entity_id],
            actual_tasks)

    def test_update(self):
        """Test that the InMemoryTaskService can persist an updated Task and
        return the updated information when later queried for that Task.

        Arrange:
            - Get Task A from the TaskService and clone it. This allows the
            test to compare the locally altered Task A with the Task A that is
            later returned by the TaskService.get request without worrying that
            the two variables are simply pointers to the same instance.
            - Update the title and updated date of the local Task A. Updating
            the updated date on the local Task A allows the test to later
            compare the updated timestamps of the local and actual Task As.
        Act:
            - Send the updated local Task A to TaskService.update.
            - Get the actual Task A from the TaskService.
        Assert:
            - That the locally updated Task A compares to the actual Task A in
            the following ways:
                - Local and actual Task A have identical titles.
                - Actual Task A has an updated date that is greater than the
                local Task A.
        """
        ### Arrange ###
        local_task_A = self.tasklist_service.get(self.expected_tasklist.entity_id, "t-A")
        local_task_A = copy.deepcopy(local_task_A)

        expected_updated_title = "updated"
        local_task_A.title = expected_updated_title
        local_task_A.updated_date = datetime.now()

        ### Act ###
        actual_task_A = self.tasklist_service.get(self.expected_tasklist.entity_id, "t-A")
        actual_task_A.title = expected_updated_title
        self.tasklist_service.update(actual_task_A)
        actual_task_A = self.tasklist_service.get(self.expected_tasklist.entity_id, "t-A")

        ### Assert ###
        self.assertEqual(local_task_A.title, actual_task_A.title)
        self.assertGreater(actual_task_A.updated_date, local_task_A.updated_date)

    def test_update_invalid_ids(self):
        """Test that attempting to update a Task with an unregistered ID will
        raise an error.

        Arrange:
            - Create a new Task with a fake ID.
        Assert:
            - That updating the Task through the task service raises an error.
        """
        ### Arrange ###
        unreg_task_id_task = Task(entity_id="unreg-id", tasklist_id=self.expected_tasklist.entity_id)
        unreg_tasklist_id_task = Task(entity_id="t-A", tasklist_id="unreg-id")

        ### Assert ###
        with self.assertRaises(UnregisteredTaskError):
            self.tasklist_service.update(unreg_task_id_task)
        with self.assertRaises(UnregisteredTaskListError):
            self.tasklist_service.update(unreg_tasklist_id_task)

    def test_add(self):
        """Test that adding a Task to the task service will persist the Task,
        and that the same Task can be later retrieved using get().

        This test will be attempted with both a registered and unregistered
        TaskList ID.

        Arrange:
            - Create two new Tasks, one with an existing TaskList ID and one
            with a new TaskList ID.
        Act:
            - Add tasks to TaskService.
            - Retrieve tasks from TaskService.
        Assert:
            - Updated date is not None.
            - Retrieved task has identical title, entity_id, etc., of expected.
        """
        ### Arrange ###
        entity_id = "new"
        title = "New Task"
        unreg_tasklist_id = "new-tasklist"
        before_operation = datetime.now()

        new_task_reg_tasklist = Task(entity_id=entity_id, title=title,
            tasklist_id=self.expected_tasklist.entity_id)
        new_task_unreg_tasklist = Task(entity_id=entity_id, title=title,
            tasklist_id=unreg_tasklist_id)

        ### Act ###
        self.tasklist_service.insert(new_task_reg_tasklist)
        self.tasklist_service.insert(new_task_unreg_tasklist)
        actual_task_reg_tasklist = self.tasklist_service.get(
            self.expected_tasklist.entity_id, entity_id)
        actual_task_unreg_tasklist = self.tasklist_service.get(
            unreg_tasklist_id, entity_id)

        ### Assert ###
        self.assertEqual((entity_id, title),
            (actual_task_reg_tasklist.entity_id, actual_task_reg_tasklist.title))
        self.assertEqual((entity_id, title),
            (actual_task_unreg_tasklist.entity_id, actual_task_unreg_tasklist.title))

        self.assertGreater(actual_task_reg_tasklist.updated_date, before_operation)
        self.assertGreater(actual_task_unreg_tasklist.updated_date, before_operation)

    def test_add_duplicate_id(self):
        """Test that attempting to insert a Task that would overwrite an existing
        Task (identical Task and TaskList IDs) raises an error.

        Arrange:
            - Create a new Task with Task and TaskList ID values that are
            identical to that of Task A in the test fixture.
        Assert:
            - Adding the Task raises an error.
        """
        ### Arrange ###
        duplicated_task = Task(
            entity_id=self.expected_task_data[self.expected_tasklist.entity_id].keys()[0],
            tasklist_id=self.expected_tasklist.entity_id)

        ### Assert ###
        with self.assertRaises(EntityOverwriteError):
            self.tasklist_service.insert(duplicated_task)

    def test_delete(self):
        """Test that deleting a registered Task from the TaskService properly
        updates that Task's deleted and updated date properties.

        Arrange:

        Act:

        Assert:
            - Attempting to retrieve deleted Task raises an error.
        """
        ### Arrange ###
        deletable_task = copy.deepcopy(
            self.expected_task_data[self.expected_tasklist.entity_id].values()[0])
        before_deletion = datetime.now()

        ### Act ###
        deletable_task = self.tasklist_service.delete(deletable_task)

        ### Assert ###
        self.assertTrue(deletable_task.is_deleted)
        self.assertGreater(deletable_task.updated_date, before_deletion)

    def test_delete_unreg_ids(self):
        """Test that attempting to delete a Task when either its Task or
        TaskList ID is unregistered raises an error.

        Arrange:
            - Create a Task with an unregistered Task ID.
            - Create a Task with an unregistered TaskList ID.
        Assert:
            - That deleting either Task will raise an error.
        """
        ### Arrange ###
        unreg_task_id_task = Task(entity_id="unreg",
            tasklist_id=self.expected_tasklist.entity_id)
        unreg_tasklist_id_task = Task(
            entity_id=self.expected_task_data[self.expected_tasklist.entity_id].keys()[0],
            tasklist_id="unreg")

        ### Assert ###
        with self.assertRaises(UnregisteredTaskError):
            self.tasklist_service.delete(unreg_task_id_task)
        with self.assertRaises(UnregisteredTaskListError):
            self.tasklist_service.delete(unreg_tasklist_id_task)
#------------------------------------------------------------------------------

class EntityOverwriteError(Exception):
    def __init__(self, entity_id):
        Exception.__init__(self,
            "Cannot register entity with duplicate ID {entity_id}".format(
            entity_id=entity_id))
#------------------------------------------------------------------------------ 

class UnregisteredEntityError(Exception):
    def __init__(self, entity_id):
        entity_type_name = self._get_entity_name()
        
        if entity_type_name is None:
            # Use a generic error message. 
            Exception.__init__(self,
                "Could not find an entity registered with the ID '{entity_id}'".format(
                entity_name=self._get_entity_name(), entity_id=entity_id))
        else:
            # Construct an error message that included the entity's type name. 
            Exception.__init__(self,
                "Could not find a {entity_name} registered with the ID '{entity_id}'".format(
                entity_name=entity_type_name, entity_id=entity_id))

    def _get_entity_name(self):
        return None
#------------------------------------------------------------------------------ 

class UnregisteredTaskError(Exception):
    def _get_entity_name(self):
        return "Task"
#------------------------------------------------------------------------------ 

class UnregisteredTaskListError(Exception):
    def _get_entity_name(self):
        return "TaskList"
#------------------------------------------------------------------------------ 

class AbstractTaskListService(object):
    def list(self):
        """
        Return a dictionary of all tasklists available. Dictionary keys will be
        entity IDs, values will be the corresponding tasklist instances.
        """
        all_tasklists = self._list()

        return all_tasklists

    def _list(self):
        raise NotImplementedError

    def get(self, entity_id):
        assert entity_id is not None

        tasklist = self._get(entity_id)

        return tasklist

    def _get(self, entity_id):
        raise NotImplementedError

    def insert(self, tasklist):
        # The TaskList must have defined, at a minimum, the ID of the TaskList.
        assert tasklist is not None and tasklist.entity_id is not None

        tasklist = self._insert(tasklist)

        return tasklist

    def _insert(self, tasklist):
        raise NotImplementedError

    def delete(self, tasklist):
        # The TaskList must have defined, at a minimum, the ID of the TaskList.
        assert tasklist is not None and tasklist.entity_id is not None

        # Execute the delete operation.
        tasklist = self._delete(tasklist)

        return tasklist

    def _delete(self, tasklist):
        raise NotImplementedError

    def update(self, tasklist):
        """
        This method updates the TaskList using a patch command rather than a
        full update.

        TODO: Enhance this method to only update fields that have been locally
        modified.
        """

        # The TaskList must have defined, at a minimum, the ID of the TaskList.
        assert tasklist is not None and tasklist.entity_id is not None

        tasklist = self._update(tasklist)

        return tasklist

    def _update(self, tasklist):
        raise NotImplementedError
#------------------------------------------------------------------------------  

class GoogleServicesTaskListService(AbstractTaskListService):
    def __init__(self):
        AbstractTaskListService.__init__(self)

        self.service_proxy = None

    def _list(self):
        tasklist_items_dict = self.service_proxy.list().execute()

        assert tasklist_items_dict.has_key(coggrinder.utilities.GoogleKeywords.ITEMS)

        tasklist_items_list = tasklist_items_dict.get(coggrinder.utilities.GoogleKeywords.ITEMS)

        tasklist_result_list = dict()
        for tasklist_dict in tasklist_items_list:
            tasklist = TaskList.from_str_dict(tasklist_dict)

            tasklist_result_list[tasklist.entity_id] = tasklist

        return tasklist_result_list

    def _get(self, entity_id):
        tasklist_dict = self.service_proxy.get(tasklist=entity_id).execute()

        tasklist = TaskList.from_str_dict(tasklist_dict)

        return tasklist

    def _insert(self, tasklist):
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

    def _delete(self, tasklist):
        # The TaskList must have defined, at a minimum, the id of the TaskList.
        assert tasklist.entity_id is not None

        # Execute the delete operation.
        self.service_proxy.delete(tasklist=tasklist.entity_id).execute()

    def _update(self, tasklist):
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

class GoogleServicesTaskListServiceTest(unittest.TestCase):
    """
    TODO: This test could use some refactoring, as the tests repeat a lot of
    boilerplate code trying to set up the same fixtures.
    """
    def test_get(self):
        expected_tasklist = TaskList(entity_id="1",
            title="Test List Title", updated_date=datetime(2012, 3, 10, 3, 30, 6))

        mock_service_proxy = mock()
        mock_get_request = mock()
        when(mock_service_proxy).get(tasklist=expected_tasklist.entity_id).thenReturn(mock_get_request)
        when(mock_get_request).execute().thenReturn(expected_tasklist.to_str_dict())

        tasklist_service = GoogleServicesTaskListService()
        tasklist_service.service_proxy = mock_service_proxy
        result_tasklist = tasklist_service.get(expected_tasklist.entity_id)

        self.assertEqual(expected_tasklist, result_tasklist)

    def test_list(self):
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

        tasklist_service = GoogleServicesTaskListService()
        tasklist_service.service_proxy = mock_service_proxy

        result_tasklists = tasklist_service.list()

        self.assertEqual(expected_tasklists, result_tasklists)

    def test_update(self):
        """
        TODO: Useless test?
        """
        mock_service_proxy = mock()
        mock_update_request = mock()

        tasklist = TaskList(entity_id="abcdfakekey", title="Test List 1",
            updated_date=datetime(2012, 3, 22, 13, 50, 00))

        when(mock_service_proxy).patch(tasklist=tasklist.entity_id, body=any(dict)).thenReturn(mock_update_request)
        when(mock_update_request).execute().thenReturn(tasklist.to_str_dict())

        tasklist_service = GoogleServicesTaskListService()
        tasklist_service.service_proxy = mock_service_proxy
        result_tasklist = tasklist_service.update(tasklist)

        verify(mock_update_request).execute()
        self.assertIsNotNone(result_tasklist)
        self.assertIsNotNone(result_tasklist.entity_id)

    def test_insert(self):
        mock_service_proxy = mock()
        mock_insert_request = mock()

        tasklist = TaskList(entity_id="abcdfakekey", title="Test List 1",
            updated_date=datetime(2012, 3, 22, 13, 50, 00))

        when(mock_service_proxy).insert(body=any(dict)).thenReturn(mock_insert_request)
        when(mock_insert_request).execute().thenReturn(tasklist.to_str_dict())

        tasklist_service = GoogleServicesTaskListService()
        tasklist_service.service_proxy = mock_service_proxy
        result_tasklist = tasklist_service.insert(tasklist)

        verify(mock_insert_request).execute()
        self.assertIsNotNone(result_tasklist)
        self.assertIsNotNone(result_tasklist.entity_id)

    def test_delete(self):
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

        tasklist_service = GoogleServicesTaskListService()
        tasklist_service.service_proxy = mock_service_proxy
        tasklist_service.delete(tasklist)

        verify(mock_delete_request).execute()
#------------------------------------------------------------------------------ 

class InMemoryTaskListService(AbstractTaskListService, InMemoryService):
    def _insert(self, tasklist):
        # Cannot overwrite an already registered TaskList.        
        if tasklist.entity_id in self.data_store:
            raise EntityOverwriteError(tasklist.entity_id)

        # Add the new TaskList to the data store and update its updated date.
        self.data_store[tasklist.entity_id] = tasklist
        tasklist.updated_date = datetime.now()

        return tasklist

    def _delete(self, tasklist):
        try:
            del self.data_store[tasklist.entity_id]
        except KeyError:
            raise UnregisteredTaskListError(tasklist.entity_id)

        return tasklist

    def _list(self):
        return self.data_store

    def _get(self, entity_id):
        try:
            tasklist = self.data_store[entity_id]
        except KeyError:
            raise UnregisteredTaskListError(entity_id)

        return tasklist

    def _update(self, tasklist):
        if tasklist.entity_id not in self.data_store:
            raise UnregisteredTaskListError(tasklist.entity_id)
        
        self.data_store[tasklist.entity_id] = tasklist
        tasklist.updated_date = datetime.now()            

        return tasklist
#------------------------------------------------------------------------------ 

class InMemoryTaskListServiceTest(unittest.TestCase, ManagedFixturesTestSupport):
    def setUp(self):
        """Established basic fixture for testing the in-memory TaskList
        service."""

        # Create fake, expected data set - a dictionary of TaskLists, with 
        # keys being the TaskList ID and values being the TaskList instances.
        self.expected_tasklists = {"tl-" + string.ascii_uppercase[x]:
            TaskList(entity_id="tl-" + string.ascii_uppercase[x], title="TaskList " + string.ascii_uppercase[x])
            for x in range(0, 3)}

        # Create an InMemoryTaskListService that uses the expected data set 
        # as its data store. Use a clone so that any changes made by the 
        # service don't also affect the expected task data fixtures.
        self.tasklist_service = InMemoryTaskListService()
        self.tasklist_service.data_store = copy.deepcopy(self.expected_tasklists)

        self._register_fixtures(self.tasklist_service, self.expected_tasklists)

    def test_insert(self):
        """Test that adding a TaskList to the TaskList service will persist
        the new TaskList, and that the same TaskList can later be retrieved
        using get().

        Arrange:
            - Create a new expected TaskList Foo with expected title and IDs.
            - Create a pre-operation timestamp.
        Act:
            - Add expected TaskList Foo to the TaskListService.
            - Retrieve actual TaskList Foo from the TaskListService.
        Assert:
            - That the actual and expected TaskList Foos compare as follows:
                - Identical title, ID properties.
                - Updated date of actual TaskList Foo has been updated during
                the insert operation.
        """
        ### Arrange ###
        expected_id = "tl-foo"
        expected_title = "TaskList Foo"
        before_operation = datetime.now()
        expected_tasklist = TaskList(entity_id=expected_id,
             title=expected_title)

        ### Act ###
        self.tasklist_service.insert(expected_tasklist)
        actual_tasklist = self.tasklist_service.get(expected_id)

        ### Assert ###
        self.assertEqual(expected_id, actual_tasklist.entity_id)
        self.assertEqual(expected_title, actual_tasklist.title)
        self.assertGreater(actual_tasklist.updated_date, before_operation)

    def test_insert_duplicate_id(self):
        """Test that adding a TaskList with an ID that has already been
        registered raises an error.

        Arrange:
            - Create a reference to TaskList A.
            - Create a new TaskList Foo with an empty title and TaskList A's
            ID.
        Assert:
            - That attempting to insert TaskList Foo into the TaskService 
            raises an error.
        """
        ### Arrange ###
        tasklist_a = self.expected_tasklists.values()[0]
        tasklist_foo = TaskList(entity_id=tasklist_a.entity_id, title="")

        ### Assert ###
        with self.assertRaises(EntityOverwriteError):
            self.tasklist_service.insert(tasklist_foo)

    def test_delete(self):
        """Test that deleting a TaskList from the TaskListSerivce removes the
        TaskList from the service's data store, and that the TaskList cannot
        later be retrieved using a get() request.

        Arrange:
            - Create a reference to TaskList A.
        Act:
            - Delete TaskList A through the TaskList service.
        Assert:
            - That attempting to retrieve TaskList A raises an error.
        """
        ### Arrange ###
        tasklist_a = self.expected_tasklists.values()[0]

        ### Act ###
        self.tasklist_service.delete(tasklist_a)

        ### Assert ###
        with self.assertRaises(UnregisteredTaskListError):
            self.tasklist_service.get(tasklist_a.entity_id)

    def test_delete_unreg_id(self):
       """Test that attempting to delete a TaskList with an
       unregistered ID raises an error.

       Arrange:
           - Create a new TaskList Foo with an unregistered ID and empty title.
       Assert:
           - That attempting to delete TaskList Foo raises an error.
       """
       ### Arrange ###
       unreg_tasklist_foo = TaskList(entity_id="foo-id", title="")

       ### Assert ###
       with self.assertRaises(UnregisteredTaskListError):
           self.tasklist_service.delete(unreg_tasklist_foo)

    def test_get(self):
        """Test that querying the TaskListService with a TaskList ID returns
        the correct TaskList associated with that ID.

        Arrange:
            - Create an expected value by cloning TaskList A.
        Act:
            - Retrieve the actual TaskList A from the TaskListService.
        Assert:
            - That the expected and actual TaskList As are identical.
        """
        ### Arrange ###
        expected_tasklist_a = copy.deepcopy(self.expected_tasklists.values()[0])

        ### Act ###
        actual_tasklist_a = self.tasklist_service.get(
            expected_tasklist_a.entity_id)

        ### Assert ###
        self.assertEqual(expected_tasklist_a, actual_tasklist_a)

    def test_get_unreg_id(self):
        """Test that querying the TaskListService with an unregistered TaskList
        ID raises an error.

        Arrange:
            - Create an unregistered TaskList ID.
        Assert:
            - That querying the TaskListService for the TaskList associated
            with an unregistered ID raises an error.
        """
        ### Arrange ###
        unreg_tasklist_id = "unreg-id"

        ### Assert ###
        with self.assertRaises(UnregisteredTaskListError):
            self.tasklist_service.get(unreg_tasklist_id)

    def test_list(self):
        """Test that querying the TaskListService for all TaskLists returns
        the expected set of TaskLists.

        Act:
            - Query the TaskListService for the actual set of TaskLists.
        Assert:
            - That the expected and actual sets of TaskLists are identical.
        """
        ### Act ###
        actual_tasklists = self.tasklist_service.list()

        ### Assert ###
        self.assertEqual(self.expected_tasklists, actual_tasklists)

    def test_list_empty(self):
        """Test that querying a TaskListService that contains no TaskLists
        returns an empty dict (rather than None).

        Arrange:
            - Create a new empty TaskListService.
        Act:
            - Query the TaskListService for the actual set of TaskLists.
        Assert:
            - That the actual set of TaskLists is identical to an empty dict.
        """
        ### Arrange ###
        empty_tasklist_service = InMemoryTaskListService()

        ### Act ###
        actual_tasklists = empty_tasklist_service.list()

        ### Assert ###
        self.assertEqual({}, actual_tasklists)

    def test_update(self):
        """Test that the TaskListService can persist an updated TaskList and
        return the updated information when later queried for the same
        TaskList.

        Arrange:
            - Clone TaskList A (cloning allows for testing in a "detached"
            instance situation).
            - Update the title of the cloned TaskList A.
            - Create a
        Act:
            - Update the cloned TaskList A.
            - Get the actual TaskList A from the TaskService.
        Assert:
            - That the actual and cloned TaskList As compare as follows:
                - Identical title, ID properties.
                - Updated date of actual TaskList Foo has been updated during
                the insert operation.
        """
        ### Arrange ###
        expected_title = "updated"
        expected_id = self.expected_tasklists.keys()[0]
        cloned_tasklist_a = copy.deepcopy(self.expected_tasklists[expected_id])
        cloned_tasklist_a.title = expected_title
        before_operation = datetime.now()

        ### Act ###
        self.tasklist_service.update(cloned_tasklist_a)
        actual_tasklist_a = self.tasklist_service.get(expected_id)

        ### Assert ###
        self.assertEqual(expected_id, actual_tasklist_a.entity_id)
        self.assertEqual(expected_title, actual_tasklist_a.title)
        self.assertGreater(actual_tasklist_a.updated_date, before_operation)

    def test_update_unreg_id(self):
        """Test that attempting to update a TaskList that isn't registered in
        the TaskListService raises an error.

        Arrange:
            - Create a new TaskList Foo with an unregistered ID and empty
            title.
        Assert:
            - That attempting to delete TaskList Foo raises an error.
        """
        ### Arrange ###
        unreg_tasklist_foo = TaskList(entity_id="unreg-id", title="")

        ### Assert ###
        with self.assertRaises(UnregisteredTaskListError):
            self.tasklist_service.update(unreg_tasklist_foo)
#------------------------------------------------------------------------------ 
