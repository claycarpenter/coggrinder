'''
Created on Apr 26, 2012

@author: Clay Carpenter
'''

import unittest
import apiclient.discovery
from coggrinder.services.task_services import TaskService, TaskListService
from coggrinder.entities.tasks import Task, TaskList
from coggrinder.entities.tree import Tree
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
        self.tree.remove_entity(tasklist.entity_id)
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

class TaskTree(Tree):
    def __init__(self, tasklists=None, all_tasks=None):
        Tree.__init__(self)

        # TODO: Should an error be raised if Task data is provided but TaskList
        # data is not?
        if tasklists is None:
            tasklists = dict()
        if all_tasks is None:
            all_tasks = dict()

        self._tasklists = tasklists
        self._all_tasks = all_tasks

        # Allows for a quick lookup of the TreeNode associated with a 
        # particular entity.        
        self._entity_node_map = None

        self._build_tree()

    @property
    def tasklists(self):
        return self._tasklists

    def _build_tree(self):
        """Build the full tree from the task data."""

        # Clear the existing tree architecture.
        self.clear()

        # Reset the entity to node indices address map.
        self._entity_node_map = dict()

        # Create a new root node. The value of this node ("root") is arbitrary
        # and shouldn't be relevant outside of human readability.
        root_node = self.append(None, "root")

        # Add each TaskList as a 1-deep branch, and then recursively add
        # any associated Tasks to the branch.
        for tasklist in self._tasklists.values():
            tasklist_node = self.append(root_node, tasklist)
            
            # Save the entity-node mapping.
            self._entity_node_map[tasklist] = tasklist_node

            try:
                tasklist_tasks = self._all_tasks[tasklist.entity_id]
                if tasklist_tasks:
                    self._build_task_tree(tasklist_tasks, tasklist_node)
            except KeyError:
                # Ignore, this error should indicate that the current TaskList
                # simply doesn't have any associated Task data.
                pass
        pass

    def _build_task_tree(self, tasks, parent_node):
        """Recursively build a branch out under the parent node that includes
        all descendant Tasks.

        Args:
            tasks: All Tasks for consideration in the branch creation.
            parent_node: The TreeNode that owns all of the descendant
                TreeNodes (each of which will contain a Task value).
        """
        for task in tasks.values():
            if (task.parent_id == parent_node.value.entity_id
                or task.tasklist_id == parent_node.value.entity_id):
                # Create a new TreeNode to hold the Task.
                task_node = self.append(parent_node, task)
                
                # Save the entity-node mapping.
                self._entity_node_map[task] = task_node

                # Recursively build out the branch below the current node/Task.
                self._build_task_tree(tasks, task_node)

    def get(self, node_indices):
        """Overrides the default get() implementation by prefixing the provided
        node indices with the Tree root path index.

        This is a convenience method that attempts to make accessing tree
        nodes easier, especially when converting from a TreeStore path.

        Args:
            node_indices: A tuple containing a collection of node indices with
            point to the targeted node. Node indices should begin with a level
            1 depth node (always a TaskList), and continue in order down the
            tree to the target node.
        Raises:
            KeyError if provided TaskList is not held within this tree.
        """
        return Tree.get(self, Tree.ROOT_PATH + node_indices)

    def get_tasks_for_tasklist(self, tasklist):
        return self._all_tasks[tasklist.entity_id]

    def get_entity_for_id(self, entity_id):
        entity = None
        try:
            entity = self._tasklists[entity_id]
        except KeyError:
            for tasklist_id in self._tasklists.keys():
                tasklist_tasks = self._all_tasks[tasklist_id]

                if tasklist_tasks:
                    try:
                        entity = tasklist_tasks[entity_id]
                    except KeyError:
                        pass

        if entity is None:
            raise ValueError("Could not find entity with ID {id}".format(id=entity_id))

        return entity

    def find_node_for_entity(self, entity):
        # Lookup the node in the entity-node mapping.
        return self._entity_node_map[entity]

    def remove_entity(self, entity):
        # Lookup the node in the entity-node mapping.         
        entity_node = self._entity_node_map[entity]
        
        # Remove the node from the tree. It is not necessary to check first if
        # the node exists, as the remove_node method will raise an error if 
        # that is the case.
        self.remove_node(entity_node)
        
        # Remove the entity from the task data collection.
        try:
            del self._tasklists[entity.entity_id]
        except KeyError:
            for tasklist_id in self._tasklists.keys():
                tasklist_tasks = self._all_tasks[tasklist_id]

                if tasklist_tasks:
                    del tasklist_tasks[entity.entity_id]
                    break
                        
#------------------------------------------------------------------------------ 

class TaskTreeTest(unittest.TestCase):
    """
    If there are going to be tests for this class, they need to be ones that
    stress the unique features of a TaskTree, rather than just duplicating
    those already being performed on Tree.
    """
    def test_equality_empty(self):
        """Test the equality of two newly created, empty TaskTrees.

        TODO: How much utility does this test really have?

        Act:
            Create two TaskTrees.
        Assert:
            That the two TaskTrees are equal.
        """
        ### Act ###
        tasktree_one = TaskTree()
        tasktree_two = TaskTree()

        ### Assert ###
        self.assertEqual(tasktree_one, tasktree_two)

    # TODO: Finish this test.
    @unittest.skip("Test yet to be completed.")
    def test_tree_creation_bad_data(self):
        """Test creating a TaskTree without providing an adequate Tasks data
        collection.

        If a TaskList collection is supplied, then there must be a Tasks dict
        provided that has a key for every TaskList ID.

        Arrange:

        Act:

        Assert:

        """
        ### Arrange ###

        ### Act ###

        ### Assert ###
        self.assertTrue(False)
#------------------------------------------------------------------------------ 

class PopulatedTaskTreeTest(ManagedFixturesTestSupport, unittest.TestCase):
    def setUp(self):
        """Set up basic test fixtures.

        This will establish a simple set of task data that includes a single
        TaskList (tl-0) and two child Tasks (t-0,t-1). The data should be used
        to create a simple tree with the following architecture:

        - tl-0
            - t-0
            - t-1
        """
        self.expected_tl_0 = TaskList(entity_id="tl-0", title="tl-0")
        self.expected_t_0 = Task(entity_id="t-0", title="t-0",
            tasklist_id=self.expected_tl_0.entity_id, position="0")
        self.expected_t_1 = Task(entity_id="t-1", title="t-1",
            tasklist_id=self.expected_tl_0.entity_id, position="1")

        self.tasklists = {self.expected_tl_0.entity_id: self.expected_tl_0}
        tl_0_tasks = {self.expected_t_0.entity_id:self.expected_t_0,
            self.expected_t_1.entity_id:self.expected_t_1}
        self.all_tasks = {self.expected_tl_0.entity_id: tl_0_tasks}

        self.tasktree = TaskTree(tasklists=self.tasklists,
            all_tasks=self.all_tasks)

        self._register_fixtures(self.expected_tl_0, self.expected_t_0,
            self.expected_t_1, self.tasklists, self.all_tasks, self.tasktree)

    def test_init_provided_data(self):
        """Test that providing TaskList and Task data through the constructor
        correctly populates the TaskTree.

        Act:
            Retrieve the actual TaskList and Task entities from the TaskTree.
        Assert:
            That the TaskTree has the expected TaskList and Task elements.
        """
        ### Act ###
        actual_tl_0 = self.tasktree.get((0,))
        actual_t_0 = self.tasktree.get((0, 0))
        actual_t_1 = self.tasktree.get((0, 1))

        ### Assert ###
        self.assertEqual(self.expected_tl_0, actual_tl_0)
        self.assertEqual(self.expected_t_0, actual_t_0)
        self.assertEqual(self.expected_t_1, actual_t_1)

    def test_get_tasks_for_tasklist(self):
        """Test that provided Task data can be retrieved by the parent
        TaskList.

        Arrange:
            Acquire the expected list of Tasks.
        Act:
            Retrieve the actual Tasks associated with the expected TaskList via
            get_tasks_for_tasklist().
        Assert:
            That the expected and actual Task lists are identical.
        """
        ### Arrange ###        
        expected_tasks = self.all_tasks[self.expected_tl_0.entity_id]

        ### Act ###
        actual_tasks = self.tasktree.get_tasks_for_tasklist(self.expected_tl_0)

        ### Assert ###
        self.assertEqual(expected_tasks, actual_tasks)

    def test_get_entity_tasklist(self):
        """Test that searching the TaskTree for an entity ID belonging to a
        TaskList will return that TaskList instance.

        Act:
            Search for a TaskList with the entity ID of the expected TaskList.
        Assert:
            That the found TaskList is equal to the expected TaskList.
        """
        ### Act ###
        actual_tl_0 = self.tasktree.get_entity_for_id(self.expected_tl_0.entity_id)

        ### Assert ###
        self.assertEqual(self.expected_tl_0, actual_tl_0)

    def test_get_entity_task(self):
        """Test that searching the TaskTree for an entity ID belonging to a
        Task will return that Task instance.

        Act:
            Search for a Task with the entity ID of the expected Task (t-1).
        Assert:
            That the found Task is equal to the expected Task.
        """
        ### Act ###
        actual_t_1 = self.tasktree.get_entity_for_id(self.expected_t_1.entity_id)

        ### Assert ###
        self.assertEqual(self.expected_t_1, actual_t_1)

    def test_get_entity_missing(self):
        """Test that searching for an entity that is not in the TaskTree will
        raise an error.

        Arrange:
            Create a bogus Task ID.
        Assert:
            That searching the TaskTree for the bogus Task ID raises a
            ValueError.
        """
        ### Arrange ###
        expected_bogus_id = "bogus-task-id"

        ### Assert ###
        with self.assertRaises(ValueError):
            self.tasktree.get_entity_for_id(expected_bogus_id)

    def test_remove_entity_tasklist(self):
        """Test that removing a TaskList from the tree removes both the
        TaskList and any child Tasks.

        Act:
            - Delete a TaskList with the entity ID of the expected TaskList.
        Assert:
            - That the TaskList cannot be found via get_entity_for_id.
            - That the two child Tasks cannot be found via get_entity_for_id.
        """
        ### Act ###
        self.tasktree.remove_entity(self.expected_tl_0)

        ### Assert ###
        with self.assertRaises(ValueError):
            self.tasktree.get_entity_for_id(self.expected_tl_0.entity_id)
        with self.assertRaises(ValueError):
            self.tasktree.get_entity_for_id(self.expected_t_0.entity_id)
        with self.assertRaises(ValueError):
            self.tasktree.get_entity_for_id(self.expected_t_1.entity_id)

    def test_find_node_for_entity(self):
        """Test that...

        Act:
            - Delete a TaskList with the entity ID of the expected TaskList.
        Assert:
            - That the TaskList cannot be found via get_entity_for_id.
            - That the two child Tasks cannot be found via get_entity_for_id.
        """
        ### Arrange ###
#        expected_entity_node = TreeNode(parent=self.tasktree, path=(0,0),value=self.expected_tl_0)
        expected_entity_node = self.tasktree.get_node((0, 0))

        ### Act ###
        actual_entity_node = self.tasktree.find_node_for_entity(
            self.expected_tl_0)

        ### Assert ###
        self.assertEqual(expected_entity_node, actual_entity_node)
#------------------------------------------------------------------------------ 
