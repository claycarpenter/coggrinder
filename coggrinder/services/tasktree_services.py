'''
Created on Apr 26, 2012

@author: Clay Carpenter
'''

import unittest
import apiclient.discovery
from datetime import datetime
from coggrinder.services.task_services import GoogleServicesTaskService, GoogleServicesTaskListService, InMemoryTaskListService, InMemoryTaskService, UnregisteredEntityError
from coggrinder.entities.tasks import UpdatedDateFilteredTask, UpdatedDateFilteredTaskList, TestDataTaskList, TestDataTask, UpdatedDateIgnoredTestDataTaskList, UpdatedDateIgnoredTestDataTask, TestDataEntitySupport, \
    TaskList, Task
from coggrinder.entities.tasktree import TaskTree, TaskDataTestSupport, TaskTreeComparator, \
    TreeTaskList, TreeTask
    
from coggrinder.core.test import ManagedFixturesTestSupport
from mockito import mock, when, any
import copy
from coggrinder.entities.properties import TaskStatus

class TaskTreeService(object):
    def __init__(self, auth_service=None, tasklist_service=None,
        task_service=None):
        self.auth_service = auth_service

        self.gtasks_service_proxy = None
        self.tasklist_service = tasklist_service
        self.task_service = task_service

        self._current_tree = TaskTree()
        self._original_tasktree = None

    """
    TODO: How do I give this a setter that can only be accessed via this
    class or descendants?
    """
    @property
    def tree(self):
        return self._current_tree
    
    def add_task(self, parent, title=""):
        # Create a new Task and attach it to the parent provided.
        task = Task(parent, title=title)
        
        """
        TODO: Is this sort call necessary?
        """
        self.sort()
        
        return task        

    def add_tasklist(self):
        # Create a new TaskList, attaching it to the current (working) tree.
        # The TaskList will have an empty title by default. This allows the 
        # user to enter the name of the new TaskList, and also pushes the 
        # TaskList to the top of the ordering so that it is more prominent in 
        # the app UI.
        tasklist = TaskList(self.tree, title="")
        
        """
        TODO: This is not the most efficient way to keep the tree sorted; 
        instead the new TaskList should be inserted directly into the 
        correct position.
        """
        self.sort()
        
        return tasklist
    
    """
    TODO: Not entirely sure that this is the appropriate place for the connect
    logic. Perhaps a separate authentication service that returns the service
    proxy handle?
    """
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
        # Replace the current TaskTree with a new instance built from the 
        # fresh task data.
        self._current_tree = self._create_tasktree()

        # Make a local copy of the clean (unmodified by the user) task data.
        self._original_tasktree = copy.deepcopy(self.tree)
        
    """
    TODO: Does this method need a unit test, or should it simply rely on the 
    unit test coverage in TaskTree (given that this is little more than a 
    pass-through method)?
    """
    def sort(self):        
        # Sort the working TaskTree.
        self.tree.sort()

    def _create_tasktree(self):
        # Get refreshed task data from the TaskList and Task services.
        tasklists = self.tasklist_service.list()        
        for tasklist in tasklists:
            
            self.task_service.get_tasks_in_tasklist(tasklist)

        tasktree = TaskTree(task_data=tasklists)

        return tasktree               

    def _create_tasklist_service(self):
        assert self.gtasks_service_proxy is not None
        assert self.gtasks_service_proxy.tasklists() is not None

        tasklist_service = GoogleServicesTaskListService()
        tasklist_service.service_proxy = self.gtasks_service_proxy.tasklists()

        return tasklist_service

    def _create_task_service(self):
        assert self.gtasks_service_proxy is not None
        assert self.gtasks_service_proxy.tasks() is not None

        task_service = GoogleServicesTaskService()
        task_service.service_proxy = self.gtasks_service_proxy.tasks()

        return task_service
    
    def add_entity(self, entity):
        raise NotImplementedError

        # Add the new entity to the task tree.
        entity = self.tree.add_entity(entity)
                
        return entity

    def get_entity_for_id(self, entity_id):
        return self.tree.get_entity_for_id(entity_id)

    def update_entity(self, entity):
        # Update the entity value reference in the TaskTree.
        entity = self.tree.update_entity(entity)

        # Update the updated date timestamp.
        entity.updated_date = datetime.now()

        return entity

    def delete_entity(self, entity):
        # Child Tasks are deleted along with the TaskList, apparently. At the 
        # very least, they're apparently inaccessible.         
        self.tree.remove_entity(entity)

    def revert_task_data(self):
        self._current_tree = copy.deepcopy(self._original_tasktree)

    def push_task_data(self):
        # We need to determine what updates have been made to the tree here.
        """
        TODO: Is there a certain order of operations (add, update, delete) 
        that needs to be followed here?
        
        Updated probably needs to come before added. That way, any data added 
        to reordered tasks will be placed in the right position...  or does it
        not matter?
        """
        self._push_added()
        
        self._push_deleted()
        
    def update_task_status(self):
        pass
        
    def _push_added(self):
        # Find the IDs of all new entities.
        added_entity_ids = TaskTreeComparator.find_added_ids(self._original_tasktree,
            self.tree)
        
        # For each new entity, add it to its respective service.
        for entity_id in added_entity_ids:
            entity = self.get_entity_for_id(entity_id)
            
            # Get the proper service provider.            
            if hasattr(entity, "tasklist_id"):
                # Presence of a tasklist ID property should indicate a Task.
                service = self.task_service
            else:
                # Lack of a tasklist ID property should indicate a TaskList.
                service = self.tasklist_service
            
            service.insert(entity)
            
    def _push_deleted(self):
        # Find the IDs of all entities that were deleted.
        deleted_entity_ids = TaskTreeComparator.find_deleted_ids(
            self._original_tasktree, self.tree)
        
        # Delete each removed entity from its respective service.
        for entity_id in deleted_entity_ids:
            entity = self._original_tasktree.get_entity_for_id(entity_id)
            
            # Get the proper service provider.            
            if hasattr(entity, "tasklist_id"):
                # Presence of a tasklist ID property should indicate a Task.
                service = self.task_service
            else:
                # Lack of a tasklist ID property should indicate a TaskList.
                service = self.tasklist_service
            
            service.delete(entity)
#------------------------------------------------------------------------------

class TaskTreeServiceTestSupport(ManagedFixturesTestSupport):
    def setUp(self, tasklists=None, all_tasks=None):
        """Set up basic test fixtures.

        This will establish a TaskTreeService that is backed by in-memory
        TaskListService and TaskServices.
        """
        if tasklists is None:
            tasklists = dict()
        if all_tasks is None:
            all_tasks = dict()

        # Create mock Task/List services that store the task data in temporary
        # in-memory collections.
        self.mock_tasklist_srvc = InMemoryTaskListService(tasklists)
        self.mock_task_srvc = InMemoryTaskService(all_tasks)
        
        # Create a TaskTreeService that uses the mock Task/List services for 
        # its task data store access.
        self.tasktree_srvc = TaskTreeService(
            tasklist_service=self.mock_tasklist_srvc,
            task_service=self.mock_task_srvc)

        # Update the TaskTreeService task data.
        self.tasktree_srvc.refresh_task_data()

        self._register_fixtures(self.tasktree_srvc, self.mock_task_srvc,
            self.mock_tasklist_srvc)
#------------------------------------------------------------------------------

class PopulatedTaskTreeServiceTestSupport(TaskTreeServiceTestSupport):
    def setUp(self):
        """Establish test fixtures common to all tests within this setup.

        - Create the expected task data.
        - Create mock in-memory task data services.
        - Wire the test fixture TaskTreeService to use both of these services
        for data storage.
        """

        # Create the expected task data and their containers.
        self.expected_tasklists = TaskDataTestSupport.create_tasklists(None,
            tasklist_type=UpdatedDateIgnoredTestDataTaskList)
        self.expected_all_tasks = TaskDataTestSupport.create_all_tasks(
            self.expected_tasklists, task_type=UpdatedDateIgnoredTestDataTask)

        # Create cloned copies of the expected task data that can be given to 
        # the mock task data services.
        # This is done so that modifying the expected TaskLists and expected 
        # Tasks fixtures doesn't also changes the data held by the 
        # TaskTreeService under test.
        cloned_tasklists = copy.deepcopy(self.expected_tasklists)
        cloned_all_tasks = copy.deepcopy(self.expected_all_tasks)

        # Create a basic, blank TaskTreeService with TaskService and 
        # TaskListService mocks.
        TaskTreeServiceTestSupport.setUp(self, tasklists=cloned_tasklists,
            all_tasks=cloned_all_tasks)
        
        self.expected_tasktree = copy.deepcopy(self.tasktree_srvc.tree)
        for tasklist in self.expected_tasklists:
            tasklist.attach_to_parent(self.expected_tasktree)

        # Register test fixtures.
        self._register_fixtures(self.expected_tasklists,
            self.expected_all_tasks, self.expected_tasktree)
#------------------------------------------------------------------------------ 

class TaskTreeServiceCreationTest(TaskTreeServiceTestSupport, unittest.TestCase):
    def test_refresh_task_data_empty(self):
        """Test refreshing the task data set when the backend services return
        no results.

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
        when(self.mock_tasklist_srvc).list().thenReturn({})
        when(self.mock_task_srvc).get_tasks_in_tasklist(any()).thenReturn({})
        expected_tasktree = TaskTree()

        ### Act ###
        self.tasktree_srvc.refresh_task_data()

        ### Assert ###
        self.assertIsNotNone(self.tasktree_srvc.tree)
        self.assertEqual(expected_tasktree, self.tasktree_srvc.tree)
        
    def test_refresh_task_data_populated(self):
        """Test refreshing the task data set when the backend services return
        a basic set of results.

        Arrange:
            - Create expected TaskList and Tasks.
            - Configure both mock TaskListService and TaskService services to
            return empty lists when queried.
        Act:
            - Ask the TaskTreeService to refresh the TaskTree.
        Assert:
            - That the TaskTree held by the service is equivalent to a blank
            TaskTree.
        """
        ### Arrange ###
        tasklist_a = TaskList(None, title="a")
        task_aa = Task(tasklist_a, title="a-a")
        task_ab = Task(tasklist_a, title="a-b")
        task_ac = Task(tasklist_a, title="a-c")
        expected_tasks = [task_aa, task_ab, task_ac]
        
        when(self.mock_tasklist_srvc).list().thenReturn([tasklist_a])
        when(self.mock_task_srvc).get_tasks_in_tasklist(tasklist_a).thenReturn(expected_tasks)

        ### Act ###
        self.tasktree_srvc.refresh_task_data()

        ### Assert ###
        self.assertIsNotNone(self.tasktree_srvc.tree)
#------------------------------------------------------------------------------ 

@unittest.skip("Disabling due to refactoring.")
class TaskTreeServiceTaskDataManagementTest(PopulatedTaskTreeServiceTestSupport, unittest.TestCase):
    """This collection of tests examines the TaskTreeService's ability to
    manage and synchronize the task data it holds with the task data services
    that manage the TaskList and Task entities.
    """
    def test_revert_task_data(self):
        """Test reverting the changes on the current task data back to what
        they were after the last data refresh from the task data services.

        Arrange:
            - Create the expected result TaskTree by making a full clone
            (deep copy) of the TaskService's original TaskTree.
        Act:
            - Update the title of tl-A.
            - Revert the task data.
        Assert:
            - That the expected TaskTree and the TaskTree currently held by the
            TaskTreeService are identical.
        """
        ### Arrange ###
        expected_tasktree = copy.deepcopy(self.tasktree_srvc.tree)

        ### Act ###
        expected_tasklist_a = self.tasktree_srvc.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id('a'))
        expected_tasklist_a.title = "updated"

        self.tasktree_srvc.revert_task_data()

        ### Assert ###
        self.assertEqual(expected_tasktree, self.tasktree_srvc.tree)

    def test_save_task_data_tasklist_added(self):
        """Test that saving the task data will persist an added TaskList to 
        the task data services.

        Arrange:
            - Create new expected TaskList Foo.
            - Create actual clone of TaskList Foo
        Act:
            - Add actual TaskList Foo through the TaskTreeService.
            - Save the task tree data.
            - Refresh the task data.
            - Get the actual TaskList Foo.
        Assert:
            - That the post-refresh task data includes the expected TaskList 
            Foo.
        """
        ### Arrange ###
        expected_tasklist_foo = UpdatedDateIgnoredTestDataTaskList("Foo")
        actual_tasklist_foo = copy.deepcopy(expected_tasklist_foo)

        ### Act ###
        self.tasktree_srvc.add_entity(actual_tasklist_foo)

        self.tasktree_srvc.push_task_data()
        self.tasktree_srvc.refresh_task_data()

        actual_tasklist_foo = self.tasktree_srvc.get_entity_for_id(
            expected_tasklist_foo.entity_id)

        ### Assert ###
        self.assertEqual(expected_tasklist_foo, actual_tasklist_foo)

    def test_save_task_data_task_added(self):
        """Test that saving the task data will persist an added Task to 
        the task data services.

        Arrange:
            - Create new expected Task Foo.
            - Create actual clone of Task Foo
        Act:
            - Add actual Task Foo through the TaskTreeService.
            - Save the task tree data.
            - Refresh the task data.
            - Get the actual Task Foo.
        Assert:
            - That the post-refresh task data includes the expected Task Foo.
        """
        ### Arrange ###
        expected_tasklist_a = self.tasktree_srvc.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id('a'))
        expected_task_foo = UpdatedDateIgnoredTestDataTask("Foo",
            tasklist_id=expected_tasklist_a.entity_id)
        actual_task_foo = copy.deepcopy(expected_task_foo)
        expected_task_foo.previous_task_id = TestDataEntitySupport.short_title_to_id(*list('ac'))

        ### Act ###
        self.tasktree_srvc.add_entity(actual_task_foo)

        self.tasktree_srvc.push_task_data()
        self.tasktree_srvc.refresh_task_data()

        actual_task_foo = self.tasktree_srvc.get_entity_for_id(
            expected_task_foo.entity_id)

        ### Assert ###
        self.assertEqual(expected_task_foo, actual_task_foo)

    def test_save_task_data_task_deleted(self):
        """Test that saving the task data will persist a deleted Task to 
        the task data services.

        Arrange:
            - Find expected Task a-c-c and make local clone actual Task a-c-c.
        Act:
            - Delete actual Task a-c-c through the TaskTreeService.
            - Save the task tree data.
            - Refresh the task data.
        Assert:
            - That the post-refresh task data does not include Task a-c-c.
        """
        ### Arrange ###
        expected_task_acc = self.tasktree_srvc.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*list('acc')))        
        actual_task_acc = copy.deepcopy(expected_task_acc)

        ### Act ###
        self.tasktree_srvc.delete_entity(actual_task_acc)

        self.tasktree_srvc.push_task_data()
        self.tasktree_srvc.refresh_task_data()

        ### Assert ###
        with self.assertRaises(UnregisteredEntityError):
            self.tasktree_srvc.get_entity_for_id(expected_task_acc.entity_id)

    def test_save_task_data_tasklist_deleted(self):
        """Test that saving the task data will persist a deleted TaskList to 
        the task data services.

        Arrange:
            - Find expected TaskList a and make local clone actual TaskList a.
        Act:
            - Delete actual TaskList a through the TaskTreeService.
            - Save the task tree data.
            - Refresh the task data.
        Assert:
            - That the post-refresh task data does not include:
                - TaskList a
                - Task a-c-c (child of TaskList a)
        """
        ### Arrange ###
        expected_tasklist_a = self.tasktree_srvc.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id('a'))        
        actual_tasklist_a = copy.deepcopy(expected_tasklist_a)

        ### Act ###
        self.tasktree_srvc.delete_entity(actual_tasklist_a)

        self.tasktree_srvc.push_task_data()
        self.tasktree_srvc.refresh_task_data()

        ### Assert ###
        with self.assertRaises(UnregisteredEntityError):
            self.tasktree_srvc.get_entity_for_id(expected_tasklist_a.entity_id)
        with self.assertRaises(UnregisteredEntityError):
            self.tasktree_srvc.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*list('acc')))

    def test_save_task_data_tasklist_task_titles_updated(self):
        """Test that saving the task data will persist updated TaskList and
        Task titles to the task data services.

        Arrange:
            - Update titles of TaskList A and TaskList A Task A.
        Act:
            - Update TaskList A and Task A through the TaskTreeService.
            - Save the task tree data.
            - Refresh the task data.
            - Get the actual TaskList A and Task A.
        Assert:
            - That the post-refresh task data still reflects the updated
            TaskList and Task titles. (by querying for TaskList A and TaskList
            A Task B and checking their titles?)
        """
        ### Arrange ###
        updated_title = "Updated!"

        expected_tasklist_a = self.tasktree_srvc.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id('A'))
        expected_tasklist_a.title = updated_title

        expected_task_a = self.tasktree_srvc.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id('A', 'A'))
        expected_tasklist_a.title = updated_title

        ### Act ###
        self.tasktree_srvc.update_entity(expected_tasklist_a)
        self.tasktree_srvc.update_entity(expected_task_a)

        self.tasktree_srvc.push_task_data()
        self.tasktree_srvc.refresh_task_data()

        actual_tasklist_a = self.tasktree_srvc.get_entity_for_id(
            expected_tasklist_a.entity_id)
        actual_task_a = self.tasktree_srvc.get_entity_for_id(expected_task_a.entity_id)

        ### Assert ###
        self.assertEqual(expected_tasklist_a, actual_tasklist_a)
        self.assertEqual(expected_task_a, actual_task_a)

    def test_task_data_not_saved_not_updated(self):
        """Test that updating the task data through TaskTreeService, but not
        saving leaves the task data stores unmodified.

        This test ensures that the TaskTreeService only pushes changes to the
        task data stores upon save commands, and not beforehand.

        Arrange:
            - Update titles of TaskList A and TaskList A Task A.
        Act:
            - Update TaskList A and Task A through the TaskTreeService.
            - Refresh the task data.
            - Get the actual TaskList A and Task A.
        Assert:
            - That the post-refresh task data does _not_ reflect the updated
            TaskList and Task titles.
        """
        ### Arrange ###
        updated_title = "Updated!"

        expected_tasklist_a = self.tasktree_srvc.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id('a'))
        cloned_tasklist_a = copy.deepcopy(expected_tasklist_a)
        cloned_tasklist_a.title = updated_title

        expected_task_a = self.tasktree_srvc.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*list("aa")))
        cloned_task_a = copy.deepcopy(expected_task_a)
        cloned_task_a.title = updated_title

        ### Act ###
        self.tasktree_srvc.update_entity(cloned_tasklist_a)
        self.tasktree_srvc.update_entity(cloned_task_a)

        self.tasktree_srvc.refresh_task_data()

        actual_tasklist_a = self.tasktree_srvc.get_entity_for_id(expected_tasklist_a.entity_id)
        actual_task_a = self.tasktree_srvc.get_entity_for_id(expected_task_a.entity_id)

        ### Assert ###
        self.assertEqual(expected_tasklist_a, actual_tasklist_a)
        self.assertEqual(expected_task_a, actual_task_a)
#------------------------------------------------------------------------------ 

class PopulatedTaskTreeServiceTest(PopulatedTaskTreeServiceTestSupport, unittest.TestCase):
    """This collection of tests intends to ensure that the basic operations of
    TaskTreeService properly updates the TaskTree task data.

    It does not cover syncing the task data with the remote Google services.
    """
    def test_add_tasklist(self):
        """Test that the add_tasklist method creates a new TaskList and places
        it in the correct position in the TaskTree.
        
        Arrange:
        
        Act:
            - Create new TaskList Empty with default blank title.
        Assert:
            - TaskList Empty exists?
            - TaskList Empty is ordered first among TaskLists.
        """
        ### Arrange ###
        
        ### Act ###
        tasklist_empty = self.tasktree_srvc.add_tasklist()
        
        ### Assert ###
        self.assertIsNotNone(self.tasktree_srvc.get_entity_for_id(tasklist_empty.entity_id))
        self.assertEqual(0, tasklist_empty.child_index)

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
        expected_tasklist_id = TestDataEntitySupport.short_title_to_id('a')
        expected_tasklist = self.tasktree_srvc.tree.get_node((0,0))

        ### Act ###   
        actual_tasklist = self.tasktree_srvc.get_entity_for_id(expected_tasklist_id)

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
        ### Arrange ### expected_task.parent.parent == actual_task.parent.parent
        expected_task_id = TestDataEntitySupport.short_title_to_id(*list('bc'))
        expected_task = self.tasktree_srvc.get_entity_for_id(expected_task_id)
        
        # Comparison fails because expected_task grandparent is not TaskTree.

        ### Act ###   
        actual_task = self.tasktree_srvc.get_entity_for_id(expected_task_id)

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
        expected_tasklist_a = copy.deepcopy(self.tasktree_srvc.tree.get_node((0,0)))
        expected_tasklist_a.title = expected_updated_title
        expected_tasklist_a.updated_date = datetime(2012, 6, 20, 12, 0, 0)

        ### Act ###   
        actual_tasklist_a = self.tasktree_srvc.get_entity_for_id(expected_tasklist_a.entity_id)
        actual_tasklist_a.title = expected_updated_title
        self.tasktree_srvc.update_entity(actual_tasklist_a)

        ### Assert ###
        self.assertEqual(expected_tasklist_a, actual_tasklist_a)
        self.assertGreater(actual_tasklist_a.updated_date, expected_tasklist_a.updated_date)

    # TODO: This test is currently being passed despite the fact that 
    # TaskTreeService.update_task is effectively a no-op. 
    def test_update_task_title(self):
        """Test that updating a Task properly changes the target Task
        properties in the TaskTreeService's task data (TaskTree).

        Arrange:
            - Create a reference to Task A.
        Act:
            - Retrieve the actual Task from the TaskTreeService.
            - Update the actual Task title.
            - Retrieve the actual Task A from the TaskTree.
        Assert:
            - That the expected and actual Task As are identical across all
            properties but the updated date.
            - That actual Task A has a more recent updated date than expected
            Task A.
        """
        ### Arrange ###
        expected_updated_title = "updated"
        expected_task_b = copy.deepcopy(self.tasktree_srvc.tree.get_node((0,0,1)))
        expected_task_b.title = expected_updated_title
        expected_task_b.updated_date = datetime(2012, 6, 20, 12, 0, 0)

        ### Act ###   
        actual_task_b = self.tasktree_srvc.get_entity_for_id(expected_task_b.entity_id)
        actual_task_b.title = expected_updated_title
        self.tasktree_srvc.update_entity(actual_task_b)
        actual_task_b = self.tasktree_srvc.tree.get_entity_for_id(
                expected_task_b.entity_id)

        ### Assert ###
        self.assertEqual(expected_task_b, actual_task_b)
        self.assertGreater(actual_task_b.updated_date, expected_task_b.updated_date)

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
        expected_deleted_tasklist_id = TestDataEntitySupport.short_title_to_id('a')
        expected_tasklist = self.tasktree_srvc.get_entity_for_id(expected_deleted_tasklist_id)
        child_task_ids = [x.entity_id for x in expected_tasklist.children]

        ### Act ###   
        actual_tasklist = self.tasktree_srvc.get_entity_for_id(expected_deleted_tasklist_id)
        self.tasktree_srvc.delete_entity(actual_tasklist)

        ### Assert ###
        with self.assertRaises(UnregisteredEntityError):
            self.tasktree_srvc.tree.get_entity_for_id(actual_tasklist.entity_id)

        for task_id in child_task_ids:
            with self.assertRaises(UnregisteredEntityError):
                self.tasktree_srvc.tree.get_entity_for_id(task_id)
#------------------------------------------------------------------------------ 

class UpdateTaskStatus(ManagedFixturesTestSupport, unittest.TestCase):
    def setUp(self):
        self.working_tasktree = TaskDataTestSupport.create_dynamic_tasktree(siblings_count=2, tree_depth=2)
        
        self._register_fixtures(self.working_tasktree)
        
    def test_update_task_status_childless_task(self):
        """Test changing the status of a childless Task from Needs Action to 
        Complete and vice-versa.
        
        Arrange:
            - Create TaskTreeService backed by mock Task/List services
            populated with TaskList A, Tasks AA, AAA, AAB.
        Act:
            - Update the task status of Tasks AAA, AAB to be Completed 
            and Needs Action, respectively.
        Assert:
            - Tasks AAA, AAB as retrieved from the TaskTree, have task 
            statuses of Completed and Needs Action, respectively.
        """
        ### Arrange ###
        tasklist_a = TestDataTaskList(None, 'a')
        task_aa = TestDataTask(tasklist_a, *'aa')
        task_aaa = TestDataTask(task_aa, *'aaa')
        task_aab = TestDataTask(task_aa, *'aab', task_status=TaskStatus.COMPLETED)
        
        mock_tasklist_service = InMemoryTaskListService(data_store=[tasklist_a])
        mock_task_service = InMemoryTaskService(data_store=[task_aa,
            task_aaa, task_aab])
        
        tasktreeservice = TaskTreeService(task_service=mock_task_service,
            tasklist_service=mock_tasklist_service)
        
        ### Act ###
        tasktreeservice.update_task_status(task_aaa, TaskStatus.COMPLETED)
        tasktreeservice.update_task_status(task_aab, TaskStatus.NEEDS_ACTION)
        
        ### Assert ###
        self.assertEqual(tasktreeservice.get_entity_for_id(task_aaa.entity_id).task_status,
            TaskStatus.COMPLETED)
        self.assertEqual(tasktreeservice.get_entity_for_id(task_aab.entity_id).task_status,
            TaskStatus.NEEDS_ACTION)
#------------------------------------------------------------------------------
