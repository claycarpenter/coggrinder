'''
Created on May 5, 2012

@author: Clay Carpenter
'''

import unittest
from coggrinder.entities.tasks import Task, TaskList
from coggrinder.entities.tree import Tree
from coggrinder.core.test import ManagedFixturesTestSupport
import copy

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
        self._entity_node_map = dict()

        self._build_tree()

    @property
    def tasklists(self):
        return self._tasklists
    
    @property
    def all_entity_ids(self):
        """A set of IDs representing all known entities held by the TaskTree."""
        entity_ids = self._entity_node_map.keys()
        
        return set(entity_ids)

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
            self._entity_node_map[tasklist.entity_id] = tasklist_node

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
                or (task.tasklist_id == parent_node.value.entity_id and task.parent_id is None)):
                # Create a new TreeNode to hold the Task.
                task_node = self.append(parent_node, task)

                # Save the entity-node mapping.
                self._entity_node_map[task.entity_id] = task_node

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
        node = self.find_node_for_entity_id(entity_id)
        entity = node.value

        if entity is None:
            raise ValueError("Could not find entity with ID {id}".format(id=entity_id))

        return entity

    def find_node_for_entity(self, entity):
        # Lookup the node in the entity-node mapping using the entity's ID.
        return self.find_node_for_entity_id(entity.entity_id)
        
    def find_node_for_entity_id(self, entity_id):
        # Lookup the node in the entity-node mapping.
        return self._entity_node_map[entity_id]

    def remove_tasklist(self, entity):
        # Find the entity's node.        
        entity_node = self._entity_node_map[entity]

        # Remove the node from the tree. It is not necessary to check first if
        # the node exists, as the remove_node method will raise an error if 
        # that is the case.
        self.remove_node(entity_node)

        # Remove all Tasks belonging to this TaskList from the task data 
        # collection.
        for task_id in self._all_tasks[entity.entity_id].keys():
            del self._all_tasks[entity.entity_id][task_id]

        # Remove the TaskList from the task data collection.
        del self._tasklists[entity.entity_id]
        del self._all_tasks[entity.entity_id]

    def update(self, entity):
        # Lookup the containing tree node.
        node = self._entity_node_map[entity.entity_id]

        # Replace the entity instance held by the containing tree node.
        node.value = entity
        
        return entity
#------------------------------------------------------------------------------ 

class TaskTreeTest(unittest.TestCase):
    """
    If there are going to be tests for this class, they need to be ones that
    stress the unique features of a TaskTree, rather than just duplicating
    those already being performed on Tree.
    """        
    def test_all_entity_ids_empty(self):
        """Test the all_entity_ids property of TaskTree, ensuring that it
        accurately reflects the IDs of the entities held by an empty 
        TaskTree.
        
        Act:
            - Create a new TaskTree without providing any default data.
        Assert:
            - That TaskTree.all_entity_ids reports no entities (length of 0).
        """
        ### Act ###
        empty_tasktree = TaskTree()
        
        ### Assert ###
        self.assertEqual(set(), empty_tasktree.all_entity_ids)
        
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
        TaskList (tl-A) and a two-level tree of child Tasks (t-B..t-F). The
        data should create a simple tree with the following architecture:

        - tl-A
            - t-B
            - t-C
                - t-E
                - t-F
            - t-D
        """
        self.expected_tl_A = TaskList(entity_id="tl-A", title="tl-A")

        self.expected_t_B = Task(entity_id="t-B", title="t-B",
            tasklist_id=self.expected_tl_A.entity_id, position="0")

        self.expected_t_C = Task(entity_id="t-C", title="t-C",
            tasklist_id=self.expected_tl_A.entity_id, position="1")
        self.expected_t_E = Task(entity_id="t-E", title="t-E",
            tasklist_id=self.expected_tl_A.entity_id, position="1",
            parent_id=self.expected_t_C.entity_id)
        self.expected_t_F = Task(entity_id="t-F", title="t-F",
            tasklist_id=self.expected_tl_A.entity_id, position="2",
            parent_id=self.expected_t_C.entity_id)

        self.expected_t_D = Task(entity_id="t-D", title="t-D",
            tasklist_id=self.expected_tl_A.entity_id, position="2")

        self.tasklists = {self.expected_tl_A.entity_id: self.expected_tl_A}
        tl_A_tasks = {self.expected_t_B.entity_id:self.expected_t_B,
            self.expected_t_C.entity_id:self.expected_t_C,
            self.expected_t_D.entity_id:self.expected_t_D,
            self.expected_t_E.entity_id:self.expected_t_E,
            self.expected_t_F.entity_id:self.expected_t_F}
        self.all_tasks = {self.expected_tl_A.entity_id: tl_A_tasks}

        # Make clones to ensure that modifying the expected task data doesn't
        # also (directly) modify the task data held by the TaskTree.
        cloned_tasklists = copy.deepcopy(self.tasklists)
        cloned_all_tasks = copy.deepcopy(self.all_tasks)

        # Use the cloned task data to build a TaskTree fixture.
        self.tasktree = TaskTree(tasklists=cloned_tasklists,
            all_tasks=cloned_all_tasks)

        """
        TODO: Is there a better way to register these fixtures? Listing each
        individually is getting somewhat cumbersome.
        """
        self._register_fixtures(self.expected_tl_A, self.expected_t_B,
            self.expected_t_C, self.expected_t_D, self.expected_t_E,
            self.expected_t_F, self.tasklists, self.all_tasks, self.tasktree)
        
    def test_all_entity_ids(self):
        """Test the all_entity_ids property of TaskTree, ensuring that it
        accurately reflects the IDs of the entities held by a populated 
        TaskTree.
        
        Arrange:
            - Create a new set that includes all the IDs of the entities in 
            the expected task data.
        Assert:
            - That the expected IDs set is equal to the test fixture's 
            TaskTree.all_entity_ids property.
        """
        ### Arrange ###
        expected_tasklist_keys = self.tasklists.keys()
        expected_task_keys = list()
        for expected_tasklist_key in expected_tasklist_keys:
            tasklist_tasks = self.all_tasks[expected_tasklist_key]
            expected_task_keys.extend(tasklist_tasks.keys())
        expected_entity_ids = set(expected_tasklist_keys + expected_task_keys) 
        
        ### Assert ###
        self.assertEqual(expected_entity_ids, self.tasktree.all_entity_ids)

    def test_init_provided_data(self):
        """Test that providing TaskList and Task data through the constructor
        correctly populates the TaskTree.

        Act:
            Retrieve the actual TaskList and Task entities from the TaskTree.
        Assert:
            That the TaskTree has the expected TaskList and Task elements.
        """
        ### Act ###
        actual_tl_A = self.tasktree.get((0,))
        actual_t_B = self.tasktree.get((0, 0))
        actual_t_C = self.tasktree.get((0, 1))

        ### Assert ###
        self.assertEqual(self.expected_tl_A, actual_tl_A)
        self.assertEqual(self.expected_t_B, actual_t_B)
        self.assertEqual(self.expected_t_C, actual_t_C)

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
        expected_tasks = self.all_tasks[self.expected_tl_A.entity_id]

        ### Act ###
        actual_tasks = self.tasktree.get_tasks_for_tasklist(self.expected_tl_A)

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
        actual_tl_A = self.tasktree.get_entity_for_id(self.expected_tl_A.entity_id)

        ### Assert ###
        self.assertEqual(self.expected_tl_A, actual_tl_A)

    def test_get_entity_task(self):
        """Test that searching the TaskTree for an entity ID belonging to a
        Task will return that Task instance.

        Act:
            Search for a Task with the entity ID of the expected Task (t-C).
        Assert:
            That the found Task is equal to the expected Task.
        """
        ### Act ###
        actual_t_C = self.tasktree.get_entity_for_id(self.expected_t_C.entity_id)

        ### Assert ###
        self.assertEqual(self.expected_t_C, actual_t_C)

    def test_get_entity_missing(self):
        """Test that searching for an entity that is not in the TaskTree will
        raise an error.

        Arrange:
            Create a bogus Task ID.
        Assert:
            That searching the TaskTree for the bogus Task ID raises an
            error.
        """
        ### Arrange ###
        expected_bogus_id = "bogus-task-id"

        ### Assert ###
        with self.assertRaises(KeyError):
            self.tasktree.get_entity_for_id(expected_bogus_id)

    @unittest.expectedFailure
    def test_remove_tasklist(self):
        """Test that removing TaskList A from the tree removes both the
        TaskList and any child Tasks.

        The difference between deleting a TaskList and a Task is that when a
        TaskList is deleted, so are all of the child Tasks. When a Task is
        deleted, only it is deleted, while any children of that deleted Task
        move into the same position occupied by the deleted Task.

        When removing a TaskList, the remove_entity method should be called
        with the remove_children flag set to True to ensure child Tasks are
        also cleared away.

        Act:
            - Delete TaskList A.
        Assert:
            - That TaskList A cannot be found via get_entity_for_id.
            - That TaskList A is now found in the collection of deleted
            TaskLists.
            - That the two child Tasks cannot be found via get_entity_for_id.
        """
        ### Act ###
        self.tasktree.remove_tasklist(self.expected_tl_A)

        ### Assert ###
        with self.assertRaises(ValueError):
            self.tasktree.get_entity_for_id(self.expected_tl_A.entity_id)
        self.assertIn(self.expected_tl_A, self.tasktree.deleted_tasklists)
        with self.assertRaises(ValueError):
            self.tasktree.get_entity_for_id(self.expected_t_B.entity_id)
        with self.assertRaises(ValueError):
            self.tasktree.get_entity_for_id(self.expected_t_C.entity_id)

    @unittest.expectedFailure
    def test_remove_task(self):
        """Test that removing a Task from the tree only removes the Task, with
        any direct children moving up to take the position of the removed
        parent Task.

        Act:
            - Delete Task C.
        Assert:
            - That Task C cannot be found via TaskTree.get_entity_for_id.
            - That Task C is now found in the collection of deleted Tasks.
            - That the direct child Tasks of the TaskList are now Tasks B, E,
            F, and D (in that order).
        """
        ### Act ###
        self.tasktree.remove_task(self.expected_t_C)

        ### Assert ###
        with self.assertRaises(ValueError):
            self.tasktree.get_entity_for_id(self.expected_t_C.entity_id)
        self.assertIn(self.expected_t_C, self.tasktree.deleted_tasks)

    def test_find_node_for_entity(self):
        """Test that given an entity, the TaskTree can correctly find the node
        of the tree that holds the entity.

        Arrange:
            - Use the direct node address to pull the node for the expected
            entity (tl-A).
        Act:
            - Retrieve the actual node found for the expected entity.
        Assert:
            - The actual node found via find_node_for_entity is identical to
            that retrieved from the TaskTree via get_node.
        """
        ### Arrange ###
        expected_entity_node = self.tasktree.get_node((0, 0))

        ### Act ###
        actual_entity_node = self.tasktree.find_node_for_entity(
            self.expected_tl_A)

        ### Assert ###
        self.assertEqual(expected_entity_node, actual_entity_node)

    def test_update_task(self):
        """Test that updating a Task only updates the corresponding value in
        the TaskTree after update() is called.

        Arrange:
            - Change title of expected Task C.
        Act:
            - Get pre-operation Task C.
            - Update Task C through the TaskTree.
            - Get post-operation Task C.
        Assert:
            - That pre-op Task C is not equal to expected Task C.
            - That post-op Task C is equal to expected Task C.
        """
        ### Arrange ###
        self.expected_t_C.title = "updated"

        ### Act ###
        preop_t_C = self.tasktree.get_entity_for_id(self.expected_t_C.entity_id)
        self.tasktree.update(self.expected_t_C)
        postop_t_C = self.tasktree.get_entity_for_id(self.expected_t_C.entity_id)

        ### Assert ###
        self.assertNotEqual(self.expected_t_C, preop_t_C)
        self.assertEqual(self.expected_t_C, postop_t_C)
#------------------------------------------------------------------------------ 
