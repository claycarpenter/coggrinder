'''
Created on May 5, 2012

@author: Clay Carpenter
'''

import unittest
from coggrinder.entities.tasks import Task, TaskList
from coggrinder.entities.tree import Tree
from coggrinder.core.test import ManagedFixturesTestSupport

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
