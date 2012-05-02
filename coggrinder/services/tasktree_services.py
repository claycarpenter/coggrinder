'''
Created on Apr 26, 2012

@author: Clay Carpenter
'''

import unittest
import apiclient.discovery
from coggrinder.services.task_services import TaskService, TaskListService
from coggrinder.entities.tasks import Task, TaskList
from coggrinder.entities.tree import Tree, TreeNode
from coggrinder.core.test import ManagedFixturesTestCase
from mockito import mock, when, unstub, any

class TaskTreeService(object):
    def __init__(self, auth_service=None, tasklist_service=None,
        task_service=None):
        self.auth_service = auth_service

        self.gtasks_service_proxy = None
        self.tasklist_service = tasklist_service
        self.task_service = task_service

        self._tree = TaskTree()

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

    def refresh_tasktree(self):
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
#------------------------------------------------------------------------------

class TaskTreeServiceTest(ManagedFixturesTestCase):
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

    def test_blank_tree(self):
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
        self.tasktree_srvc.refresh_tasktree()

        ### Assert ###
        self.assertIsNotNone(self.tasktree_srvc.tree)
        self.assertEqual(expected_tasktree, self.tasktree_srvc.tree)

    def test_refresh_tasktree(self):
        """Test creating a tree with a list of TaskLists (and no Tasks).

        The expected TaskTree architecture:
        TaskTree root
            - TaskList 0
                - Task A
                    - Task B
                    - Task C
            - TaskList 1, 2
                [...]

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
        expected_tasklists = {"tl-" + str(x): 
            TaskList(entity_id="tl-" + str(x), title='Tasklist ' + str(x))
            for x in range(0, 3)}

        expected_all_tasks = dict()
        for expected_tasklist in expected_tasklists.values():
            expected_all_tasks[expected_tasklist] = list()
            t_a = Task(entity_id=expected_tasklist.entity_id + "-t-a",
                tasklist_id=expected_tasklist.entity_id, title="Task A")
            t_b = Task(entity_id=expected_tasklist.entity_id + "-t-b",
                tasklist_id=expected_tasklist.entity_id, title="Task B",
                parent_id=t_a.entity_id)
            t_c = Task(entity_id=expected_tasklist.entity_id + "-t-c",
                tasklist_id=expected_tasklist.entity_id, title="Task C",
                parent_id=t_a.entity_id)

        expected_tasktree = TaskTree(tasklists=expected_tasklists,
            all_tasks=expected_all_tasks)

        when(self.mock_tasklist_srvc).get_all_tasklists().thenReturn(
            expected_tasklists)
        for expected_tasklist in expected_tasklists:
            when(self.mock_task_srvc).get_tasks_in_tasklist().thenReturn(
                expected_all_tasks)

        ### Act ###
        self.tasktree_srvc.refresh_tasktree()

        ### Assert ###
        print "Expected:"
        print expected_tasktree._full_tree_as_str()
        print "Actual:"
        print self.tasktree_srvc.tree._full_tree_as_str()
        self.assertEqual(expected_tasktree, self.tasktree_srvc.tree)
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

        self._build_tree()

    @property
    def tasklists(self):
        return self._tasklists

    def _build_tree(self):
        # Clear the existing tree architecture.
        self.clear()

        # Create a new root node. The value of this node ("root") is arbitrary
        # and shouldn't be relevant outside of human readability.
        root_node = self.append(None, "root")

        # Add each TaskList as a 1-deep branch, and then recursively add
        # any associated Tasks to the branch.
        for tasklist in self._tasklists.values():
            tasklist_node = self.append(root_node, tasklist)

            try:
                tasklist_tasks = self._all_tasks[tasklist.entity_id]
                if tasklist_tasks:
                    self._build_tasklist_tree(tasklist_tasks, tasklist_node)
            except KeyError:
                # Ignore, this error should indicate that the current TaskList
                # simply doesn't have any associated Task data.
                pass
        pass

    def _build_tasklist_tree(self, tasks, parent_node, parent_id=None):
        for task in tasks.values():
            if task.parent_id == parent_id:
                task_node = self.append(parent_node, task)

                self._build_tasklist_tree(tasks, task_node,
                    parent_id=task.entity_id)

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
#------------------------------------------------------------------------------ 

class TaskTreeTest(ManagedFixturesTestCase):
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

    @unittest.skip("Not sure if this test is actually necessary.")
    def test_equality_empty_vs_populated(self):
        """Test that an empty TaskTree is not equal to a populated TaskTree.

        Act:
            Create empty TaskTree.
            Create populated TaskTree.
            Add ... to populated TaskTree.
        Assert:
            That the two TaskTrees are _not_ equal.
        """
        ### Act ###
        empty = TaskTree()
        populated = TaskTree()
#        populated.add_tasklist(tasklist)

        ### Assert ###
        self.assertEqual(empty, populated)
#------------------------------------------------------------------------------ 

class SimplePopulatedTaskTreeTest(ManagedFixturesTestCase):
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
        self.expected_t_0 = Task(entity_id="t-0", title="t-0", tasklist_id=self.expected_tl_0.entity_id,
            position="0")
        self.expected_t_1 = Task(entity_id="t-1", title="t-1", tasklist_id=self.expected_tl_0.entity_id,
            position="1")
        self.tasklists = {self.expected_tl_0.entity_id: self.expected_tl_0}
        self.all_tasks = {self.expected_tl_0.entity_id: [self.expected_t_0, self.expected_t_1]}

        self._register_fixtures(self.expected_tl_0, self.expected_t_0,
            self.expected_t_1, self.tasklists, self.all_tasks)

    def test_init_provided_data(self):
        """Test that providing TaskList and Task data through the constructor
        correctly populates the TaskTree.

        Act:
            Create a new TaskTree, providing it the TaskList and Task data
            through init arguments.
            Retrieve the actual TaskList and Task entities from the TaskTree.
        Assert:
            That the TaskTree has the expected TaskList and Task elements.
        """
        ### Arrange ###
        tasktree = TaskTree(tasklists=self.tasklists, all_tasks=self.all_tasks)

        ### Act ###
        actual_tl_0 = tasktree.get((0,))
        actual_t_0 = tasktree.get((0, 0))
        actual_t_1 = tasktree.get((0, 1))

        ### Assert ###
        self.assertEqual(self.expected_tl_0, actual_tl_0)
        self.assertEqual(self.expected_t_0, actual_t_0)
        self.assertEqual(self.expected_t_1, actual_t_1)

    def test_get_tasks_for_tasklist(self):
        """Test that providing Task data can be retrieved by the parent
        TaskList.

        Arrange:
            Create a new TaskTree, providing it the TaskList and Task data
            through init arguments.
            Acquire the expected list of Tasks.
        Act:
            Retrieve the actual Tasks associated with the expected TaskList via
            get_tasks_for_tasklist().
        Assert:
            That the expected and actual Task lists are identical.
        """
        ### Arrange ###        
        tasktree = TaskTree(tasklists=self.tasklists, all_tasks=self.all_tasks)
        expected_tasks = self.all_tasks[self.expected_tl_0.entity_id]

        ### Act ###
        actual_tasks = tasktree.get_tasks_for_tasklist(self.expected_tl_0)

        ### Assert ###
        self.assertEqual(expected_tasks, actual_tasks)
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
