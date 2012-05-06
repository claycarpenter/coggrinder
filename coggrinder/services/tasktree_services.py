'''
Created on Apr 26, 2012

@author: Clay Carpenter
'''

import unittest
import apiclient.discovery
from coggrinder.services.task_services import TaskService, TaskListService
from coggrinder.entities.tasks import Task, TaskList
from coggrinder.entities.tasktree import TaskTree
from coggrinder.core.test import ManagedFixturesTestSupport
from mockito import mock, when, any
import copy

class TaskTreeService(object):
    def __init__(self, auth_service=None, tasklist_service=None,
        task_service=None):
        self.auth_service = auth_service

        self.gtasks_service_proxy = None
        self.tasklist_service = tasklist_service
        self.task_service = task_service

        self._tree = TaskTree()

    """
    TODO: How do I give this a setter that can only be accessed via this
    class or descendants?
    """
    @property
    def tree(self):
        return self._tree

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

    def refresh_task_data(self):
        # Get refreshed task data from the TaskList and Task services.
        tasklists = self.tasklist_service.get_all_tasklists()
        all_tasks = dict()
        for tasklist in tasklists.values():
            all_tasks[tasklist.entity_id] = self.task_service.get_tasks_in_tasklist(
                tasklist)

        # Replace the current TaskTree with a new instance built from the 
        # fresh task data.
        self._tree = TaskTree(tasklists=tasklists, all_tasks=all_tasks)

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

    def get_tasklist(self, tasklist_id):
        return self.tree.get_entity_for_id(tasklist_id)

    def get_task(self, task_id):
        return self.tree.get_entity_for_id(task_id)

    def update_tasklist(self, tasklist):
        pass

    def update_task(self, task):
        pass

    def delete_tasklist(self, tasklist):
        # Child Tasks are deleted along with the TaskList, apparently. At the 
        # very least, they're apparently inaccessible. 
        self.tree.remove_entity(tasklist, remove_children=True)
        
    def delete_task(self,task):
        self.tree.remove_entity(task)
#------------------------------------------------------------------------------

class TaskTreeServiceTestCommon(object):
    def setUp(self):
        """Set up basic test fixtures.

        This will establish a TaskTreeService and mock TaskListService and
        TaskServices, and configure the TaskTreeService to use both of those
        mocks for data storage.
        """
        self.mock_tasklist_srvc = mock(TaskListService)
        self.mock_task_srvc = mock(TaskService)

        self.tasktree_srvc = TaskTreeService(
            tasklist_service=self.mock_tasklist_srvc,
            task_service=self.mock_task_srvc)

        self._register_fixtures(self.tasktree_srvc, self.mock_task_srvc,
            self.mock_tasklist_srvc)
#------------------------------------------------------------------------------ 

class TaskTreeServiceTest(ManagedFixturesTestSupport, TaskTreeServiceTestCommon, unittest.TestCase):
    def test_no_task_data(self):
        """Test creating an empty tree.

        This would be the case if the GTasks services returned no TaskLists
        or Tasks.

        Arrange:
            Configure both mock TaskListService and TaskService services to
            return empty lists when queried.
        Act:
            Ask the TaskTreeService to refresh the TaskTree.
        Assert:
            That the TaskTree held by the service is equivalent to a blank
            TaskTree.
        """
        ### Arrange ###
        when(self.mock_tasklist_srvc).get_all_tasklists().thenReturn({})
        when(self.mock_task_srvc).get_tasks_in_tasklist(any()).thenReturn({})
        expected_tasktree = TaskTree()

        ### Act ###
        self.tasktree_srvc.refresh_task_data()

        ### Assert ###
        self.assertIsNotNone(self.tasktree_srvc.tree)
        self.assertEqual(expected_tasktree, self.tasktree_srvc.tree)
#------------------------------------------------------------------------------ 

class TaskDataTestSupport(object):
    """Simple support class to make it more convenient to product mock TaskList
    and Task data for use in testing."""
    @classmethod
    def create_expected_tasklists(cls, entity_id_prefix="tl-",
        title_prefix="TaskList ", begin_count=0, end_count=3):
        """Create a dictionary of TaskList objects.

        Each TaskList object will be given a unique ID and title, beginning
        with the associated prefixes and ending with a integer between the
        begin count and end count values. The method will create begin_count -
        end_count TaskLists.

        Args:
            entity_id_prefix: str prefix for the TaskList ID.
            title_prefix: str prefix for the TaskList title.
            begin_count: int for the first TaskList.
            end_count: int for the last TaskList.
        Returns:
            A dictionary keyed with the TaskList IDs, with values mapping to
            the corresponding TaskList instance.
        """
        assert begin_count < end_count

        expected_tasklists = {entity_id_prefix + str(x):
            TaskList(entity_id=entity_id_prefix + str(x),
            title=title_prefix + str(x)) for x in range(begin_count, end_count)}

        return expected_tasklists

    @classmethod
    def create_expected_all_tasks(cls, expected_tasklists):
        expected_all_tasks = dict()
        for expected_tasklist in expected_tasklists.values():
            t_a = Task(entity_id=expected_tasklist.entity_id + "-t-0",
                tasklist_id=expected_tasklist.entity_id, title="Task 0")
            t_b = Task(entity_id=expected_tasklist.entity_id + "-t-1",
                tasklist_id=expected_tasklist.entity_id, title="Task 1",
                parent_id=t_a.entity_id)
            t_c = Task(entity_id=expected_tasklist.entity_id + "-t-2",
                tasklist_id=expected_tasklist.entity_id, title="Task 2",
                parent_id=t_a.entity_id)

            expected_all_tasks[expected_tasklist.entity_id] = {t_a.entity_id:t_a,
                t_b.entity_id:t_b, t_c.entity_id:t_c}

        return expected_all_tasks
#------------------------------------------------------------------------------ 

class TaskTreeServiceTaskDataManagementTest(ManagedFixturesTestSupport, TaskTreeServiceTestCommon, unittest.TestCase):
    """This collection of tests examines the TaskTreeService's ability to
    manage and synchronize the task data it holds with the remote Google
    services.
    """
    # TODO: This setUp is currently duplicated with the 
    # PopulatedTaskTreeServiceTest.
    def setUp(self):
        # Create a basic, blank TaskTreeService with TaskService and 
        # TaskListService mocks.
        TaskTreeServiceTestCommon.setUp(self)

        # Create the expected task data containers.
        self.expected_tasklists = TaskDataTestSupport.create_expected_tasklists()
        self.expected_all_tasks = TaskDataTestSupport.create_expected_all_tasks(
            self.expected_tasklists)

        # Wire the mock services to return the expected task data when
        # queried.                        
        when(self.mock_tasklist_srvc).get_all_tasklists().thenReturn(
            self.expected_tasklists)
        for expected_tasklist in self.expected_tasklists.values():
            when(self.mock_task_srvc).get_tasks_in_tasklist(expected_tasklist).thenReturn(
                self.expected_all_tasks[expected_tasklist.entity_id])

        # Update the TaskTreeService task data.
        self.tasktree_srvc.refresh_task_data()

    def test_refresh_tasktree(self):
        """Test creating a tree with a list of TaskLists (and no Tasks).

        Arrange:
            Create TaskTreeService.
            Create mock TaskList services, and stub to return expected TaskList
            data when queried.
            Create mock TaskList list, and stub to return expected Task data
            for each expected TaskList.
        Act:
            Ask TaskTreeService to populate the tree from the services' data.
        Assert:
            That all of the items in the TaskList list are 1-deep nodes (first
            children of the root) in the TaskTreeService's TaskTree.
        """
        ### Arrange ###
        expected_tasktree = TaskTree(tasklists=self.expected_tasklists,
            all_tasks=self.expected_all_tasks)

        ### Act ###
        self.tasktree_srvc.refresh_task_data()

        ### Assert ###
        self.assertEqual(expected_tasktree, self.tasktree_srvc.tree)
#------------------------------------------------------------------------------ 

class PopulatedTaskTreeServiceTest(ManagedFixturesTestSupport, TaskTreeServiceTestCommon, unittest.TestCase):
    """This collection of tests intends to ensure that the TaskTreeService
    properly updates the TaskTree task data.

    It does not cover syncing the task data with the remote Google services.
    """
    def setUp(self):
        # Create a basic, blank TaskTreeService with TaskService and 
        # TaskListService mocks.
        TaskTreeServiceTestCommon.setUp(self)

        # Create the expected task data containers.
        self.expected_tasklists = TaskDataTestSupport.create_expected_tasklists()
        self.expected_all_tasks = TaskDataTestSupport.create_expected_all_tasks(
            self.expected_tasklists)

        # Wire the mock services to return the expected task data when
        # queried.                        
        when(self.mock_tasklist_srvc).get_all_tasklists().thenReturn(
            self.expected_tasklists)
        for expected_tasklist in self.expected_tasklists.values():
            when(self.mock_task_srvc).get_tasks_in_tasklist(expected_tasklist).thenReturn(
                self.expected_all_tasks[expected_tasklist.entity_id])

        # Update the TaskTreeService task data.
        self.tasktree_srvc.refresh_task_data()

    def test_get_tasklist(self):
        """Test that retrieving ("getting") a TaskList from the TaskTreeService
        returns the expected instance.

        Arrange:
            Find the expected TaskList in the expected TaskList data.
        Act:
            Retrieve the actual TaskList from the TaskTreeService.
        Assert:
            That the actual and expected TaskLists are identical.
        """
        ### Arrange ###
        expected_tasklist_id = "tl-0"
        expected_tasklist = self.expected_tasklists[expected_tasklist_id]

        ### Act ###   
        actual_tasklist = self.tasktree_srvc.get_tasklist(expected_tasklist_id)

        ### Assert ###
        self.assertEqual(expected_tasklist, actual_tasklist)

    def test_get_task(self):
        """Test that retrieving ("getting") a Task from the TaskTreeService
        returns the expected instance.

        Arrange:
            Find the expected Task in the expected Task data.
        Act:
            Retrieve the actual Task from the TaskTreeService.
        Assert:
            That the actual and expected Tasks are identical.
        """
        ### Arrange ###
        expected_tasklist_id = "tl-1"
        expected_task_id = expected_tasklist_id + "-t-1"
        expected_task = self.expected_all_tasks[expected_tasklist_id][expected_task_id]


        self.tasktree_srvc.refresh_task_data()

        ### Act ###   
        actual_task = self.tasktree_srvc.get_task(expected_task_id)

        ### Assert ###
        self.assertEqual(expected_task, actual_task)

    # TODO: This test is currently being passed despite the fact that 
    # TaskTreeService.update_tasklist is effectively a no-op. 
    def test_update_tasklist_title(self):
        """Test that updating a TaskList properly changes the target TaskList
        properties in the TaskTreeService's task data (TaskTree).

        Arrange:
            - Create an expected updated TaskList based on the properties of the
            existing expected TaskList (created in setUp()).
        Act:
            - Retrieve the actual TaskList from the TaskTreeService.
            - Update the actual TaskList title.
        Assert:
            - Retrieve the actual, updated TaskList from the TaskTree.
            - That the TaskList from the TaskTree is identical to the expected
            TaskList.
        """
        ### Arrange ###
        expected_updated_title = "updated"
        expected_updated_tasklist = copy.deepcopy(
            self.expected_tasklists["tl-0"])
        expected_updated_tasklist.title = expected_updated_title

        ### Act ###   
        actual_tasklist = self.tasktree_srvc.get_tasklist(expected_updated_tasklist.entity_id)
        actual_tasklist.title = expected_updated_title
        self.tasktree_srvc.update_tasklist(actual_tasklist)

        ### Assert ###
        tasktree_tasklist = self.tasktree_srvc.tree.get_entity_for_id(
                actual_tasklist.entity_id)
        self.assertEqual(expected_updated_tasklist, tasktree_tasklist)

    # TODO: This test is currently being passed despite the fact that 
    # TaskTreeService.update_task is effectively a no-op. 
    def test_update_task_title(self):
        """Test that updating a Task properly changes the target Task
        properties in the TaskTreeService's task data (TaskTree).

        Arrange:
            - Create an expected updated Task based on the properties of the
            existing expected Task (created in setUp()).
        Act:
            - Retrieve the actual Task from the TaskTreeService.
            - Update the actual Task title.
        Assert:
            - Retrieve the actual, updated Task from the TaskTree.
            - That the Task from the TaskTree is identical to the expected
            Task.
        """
        ### Arrange ###
        expected_updated_title = "updated"
        expected_updated_task = copy.deepcopy(
            self.expected_all_tasks["tl-0"]["tl-0-t-1"])
        expected_updated_task.title = expected_updated_title

        ### Act ###   
        actual_task = self.tasktree_srvc.get_tasklist(expected_updated_task.entity_id)
        actual_task.title = expected_updated_title
        self.tasktree_srvc.update_task(actual_task)

        ### Assert ###
        tasktree_task = self.tasktree_srvc.tree.get_entity_for_id(
                actual_task.entity_id)
        self.assertEqual(expected_updated_task, tasktree_task)

    @unittest.expectedFailure
    def test_delete_tasklist(self):
        """Test that deleting a TaskList removes the TaskList and any child
        Tasks from the TaskTree.

        Arrange:
            -
        Act:
            - Retrieve the actual TaskList from the TaskTreeService.
            - Delete the actual TaskList title.
        Assert:
            - Retrieve the actual, updated TaskList from the TaskTree.
            - That the TaskList from the TaskTree is identical to the expected
            TaskList.
        """
        ### Arrange ###
        expected_deleted_tasklist_id = "tl-0"

        ### Act ###   
        actual_tasklist = self.tasktree_srvc.get_tasklist(expected_deleted_tasklist_id)
        self.tasktree_srvc.delete_tasklist(actual_tasklist)

        ### Assert ###
        with self.assertRaises(ValueError):
            self.tasktree_srvc.tree.get_entity_for_id(actual_tasklist.entity_id)

        for x in range(0, 3):
            task_id = expected_deleted_tasklist_id + "-t-" + str(x)

            with self.assertRaises(ValueError):
                self.tasktree_srvc.tree.get_entity_for_id(task_id)
#------------------------------------------------------------------------------ 
