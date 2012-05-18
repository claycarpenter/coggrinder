'''
Created on May 5, 2012

@author: Clay Carpenter
'''

import unittest
from datetime import datetime
from coggrinder.entities.tasks import Task, TaskList
from coggrinder.entities.tree import Tree, NodeNotFoundError
from coggrinder.core.test import ManagedFixturesTestSupport
import copy
import string
from coggrinder.services.task_services import UnregisteredTaskListError, \
    EntityOverwriteError, UnregisteredEntityError, UnregisteredTaskError
from operator import attrgetter

class TaskTree(Tree):
    def __init__(self, tasklists=None, all_tasks=None):
        Tree.__init__(self)

        """
        TODO: Should an error be raised if Task data is provided but TaskList
        data is not?
        """
        if tasklists is None:
            tasklists = dict()
        if all_tasks is None:
            all_tasks = dict()
            
        # Allows for a quick lookup of the TreeNode associated with a 
        # particular entity. This is keyed by ID and the values are the 
        # TreeNodes holding the entity for that ID.
        self._entity_node_map = dict()
        
        task_data = dict()
        task_data.update(tasklists)
        for tasklist_tasks in all_tasks.values():
            task_data.update(tasklist_tasks)
                
        self._build_tree(task_data)

    @property
    def all_entity_ids(self):
        """A set of IDs representing all known entities held by the TaskTree."""
        entity_ids = self._entity_node_map.keys()

        return set(entity_ids)
    
    @property
    def tasklists(self):
        tasklists = dict()
        
        # Find the root node and collect all of its direct children. Each 
        # child should represent a TaskList.
        root_node = self.get_root_node()
        for tasklist_node in root_node.children:
            tasklist = tasklist_node.value
            tasklists[tasklist.entity_id] = tasklist
            
        return tasklists

    def _build_tree(self, task_data):
        """Build the full tree from the task data."""

        # Clear the existing tree architecture.
        self.clear()

        # Check to see if a new root node already exists (this will be the case
        # if the tree isn't new and is being rebuilt after it was cleared.
        """
        TODO: Is this check really needed, or does the preceding clear()
        call guarantee that the root node will be present?
        """
        try:
            root_node = self.get_root_node(must_find=True)
        except NodeNotFoundError:
            # Tree does not have a root node, create a new one. The value of 
            # this node ("root") is arbitrary and shouldn't be relevant 
            # outside of human readability.
            root_node = self.append(None, "root")

        for entity in task_data.values():
            if entity.entity_id in self._entity_node_map:
                # Entity has already been added; skip.
                continue
            
            # First try to find the parent of the entity via the parent_id
            # property. If the entity is a TaskList, this will raise an 
            # AttributeError.
            try:
                self._add_task(task_data, entity)
            except AttributeError:
                # If AttributeError is raised the entity is a TaskList and
                # should be added directly to the tree.
                self.add_entity(entity)
    
    def _add_task(self, task_data, task):        
        parent_id = task.parent_id
                
        # If parent ID is present, attempt to locate parent. If parent ID
        # is None, the Task is a direct descendant of its TaskList. 
        # Otherwise the parent ID is another Task.
        try:
            parent_node = self.find_node_for_entity_id(parent_id)           
        except UnregisteredEntityError:
            if parent_id is None:
                # Parent node is the Task's TaskList, add the TaskList if it's
                # not already present in the tree.
                if task.tasklist_id not in self._entity_node_map:
                    try:
                        tasklist = task_data[task.tasklist_id]
                    except KeyError:
                        raise TaskDataError("Task with ID {task_id} has no defined parent TaskList.".format(
                            task_id=task.entity_id))
                    self.add_entity(tasklist)
            else:
                # Parent of this Task is another Task, but the parent Task has
                # not yet been added to the tree. Add it before attempting to 
                # add the current Task.
                try:
                    parent_task = task_data[task.parent_id]
                except KeyError:
                    # This is unlikely to happen, could occur if the parent 
                    # Task was deleted without also deleting this child task. 
                    raise TaskDataError("Could not find parent Task with ID '{parent_id}' for Task {task}".format(
                        parent_id=task.parent_id, task=task))
                    
                self._add_task(task_data, parent_task)
        
        # Parent node already exists in tree, add this Task child.
        self.add_entity(task)

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

                # Register the entity-node mapping.
                self._register_entity_node(task_node)

                # Recursively build out the branch below the current node/Task.
                self._build_task_tree(tasks, task_node)
                
    def _register_entity_node(self, entity_node):
        entity = entity_node.value
        
        if entity.entity_id in self._entity_node_map:
            raise EntityOverwriteError(entity.entity_id)
        
        self._entity_node_map[entity.entity_id] = entity_node
    
    def _deregister_entity_node(self, entity_node):
        entity = entity_node.value
        
        try:
            del self._entity_node_map[entity.entity_id]
        except KeyError:
            raise UnregisteredEntityError(entity.entity_id)
        
        # Recursively deregister all of the node's descendants.
        for child_node in entity_node.children:
            self._deregister_entity_node(child_node)

    def add_entity(self, entity):
        assert entity is not None

        try:
            # Access the tasklist_id property first, so it has a chance to 
            # raise an AttributeError if the entity is a TaskList (and 
            # therefore lacks that property).
            tasklist_id = entity.tasklist_id
            
            try:
                parent_tasklist = self.get_entity_for_id(tasklist_id)
            except UnregisteredEntityError:
                raise UnregisteredTaskListError(tasklist_id)
            
            if entity.parent_id:
                # Task has another Task as a parent. Attempt to locate the
                # parent.
                try:
                    parent_entity = self.get_entity_for_id(entity.parent_id)
                except UnregisteredEntityError:
                    raise UnregisteredTaskError(entity.parent_id)
            else:
                # Task has no parent. Add directly to the TaskList.
                parent_entity = parent_tasklist

            parent_node = self.find_node_for_entity(parent_entity)
        except AttributeError:
            # No TaskList ID found, assuming this is a TaskList.
            parent_node = self.get_node(self.ROOT_PATH)

        # Find the correct position for the new entity.
        entity_address = self._find_new_entity_address(parent_node, entity)
        
        entity_node = self.insert(entity_address, entity)
        self._register_entity_node(entity_node)
        
        return entity
    
    def _find_new_entity_address(self, parent_node, entity):
        position = len(parent_node.children)
                
        for sibling_entity_node in parent_node.children:
            sibling_entity = sibling_entity_node.value
            
            if sibling_entity > entity:
                position = parent_node.children.index(sibling_entity_node)
                break
               
        return parent_node.path + (position,)

    def clear(self):
        # Clear all of the nodes from the tree.
        Tree.clear(self)
        
        # Reset the entity id-to-node mapping.
        self._entity_node_map.clear()
        
        # Create a new, default root node (all TaskTrees have a default root 
        # node that is the direct parent of any TaskLists in that tree).
        self.append(None, "root")

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
    
    def get_all_descendant_nodes(self, node):
        descendant_nodes = list()
        
        # Iterate over all direct children, calling this method recursively
        # on each and collecting the results in the descendant nodes list.
        for direct_child in node.children:
            descendant_nodes.append(direct_child)
            
            descendant_nodes.extend(self.get_all_descendant_nodes(direct_child))
            
        return descendant_nodes    

    def get_tasks_for_tasklist(self, tasklist):
        tasklist_tasks = dict()
        
        # Lookup the node containing the TaskList.
        tasklist_node = self.find_node_for_entity(tasklist)
        
        # Find and collect all descendant nodes of the TaskList node.
        task_nodes = self.get_all_descendant_nodes(tasklist_node)
        
        # Iterate over the descendant nodes, adding the entity each contains
        # (in all cases, this should be a Task) to the TaskList Tasks 
        # collection.
        for task_node in task_nodes:
            entity = task_node.value
            tasklist_tasks[entity.entity_id] = entity
        
        return tasklist_tasks

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
        try:            
            if entity_id is None:
                raise KeyError
            
            # Lookup the node in the entity-node mapping.
            return self._entity_node_map[entity_id]
        except KeyError:
            raise UnregisteredEntityError(entity_id)
        
    def remove_entity(self, entity):
        # Find the entity's node.        
        entity_node = self.find_node_for_entity(entity)
        
        # Remove the node from the entity id-to-node registry.
        self._deregister_entity_node(entity_node)
        
        if len(entity_node.path) > 2:
            # This entity is not a TaskList, so move all of the children up to
            # the position of the deleted entity. 
            
            # Insert any children of the current entity into the entity's old 
            # position in reverse order. Using reverse order allows the ordering of
            # the children to be preserved as they're re-inserted into the tree.
            for child_node in reversed(entity_node.children):
                child_node = self.insert(entity_node.path, child_node.value)
                self._register_entity_node(child_node)
        
        # Remove the node from the tree. 
        self.remove_node(entity_node)
            
    def sort(self, current_node=None):
        if current_node is None:
            # Use the root node as the default starting point for a 
            # (recursive) sort.
            current_node = self.get_root_node()
         
        child_nodes = current_node.children
        sorted_child_nodes = sorted(child_nodes, key=attrgetter('value'))
        
        for i in range(0, len(sorted_child_nodes)):
            sorted_child_node = sorted_child_nodes[i]
            current_node.children[i] = sorted_child_node
            sorted_child_node.path = current_node.path + (i,)
            
            self.sort(sorted_child_node)

    def update_entity(self, entity):
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
        
    def test_simple_task_data_tree_creation(self):
        """Test the creation of a TaskTree with a simple and small task data
        set.
        
        The completed TaskTree should have the following architecture:
        - (TL) A
            - (T) B
            
        TL = TaskList, T = Task
        
        Arrange:
            - Create task data: TaskList A and Task B.
            - Manually build the expected TaskTree.
            - Create a task data set (in the "tasklist/all_tasks" form).
        Act:
            - Build actual TaskTree by providing task data during 
            initialization.
        Assert:
            - That the expected and actual TaskTrees are identical.
        """
        ### Arrange ###
        expected_tasklist_a = TestDataTaskList("A")
        actual_tasklist_a = copy.deepcopy(expected_tasklist_a)
        
        expected_task_b = TestDataTask("B", tasklist_id=actual_tasklist_a.entity_id)
        actual_task_b = copy.deepcopy(expected_task_b)
        
        expected_tasktree = TaskTree()
        expected_tasktree.add_entity(expected_tasklist_a)
        expected_tasktree.add_entity(expected_task_b)
        
        tasklists = {actual_tasklist_a.entity_id:actual_tasklist_a}
        all_tasks = {actual_tasklist_a.entity_id:{actual_task_b.entity_id:actual_task_b}}
        
        ### Act ###
        actual_tasktree = TaskTree(tasklists, all_tasks)
        
        ### Assert ###
        self.assertEqual(expected_tasktree, actual_tasktree)
#------------------------------------------------------------------------------ 

class TaskTreeSortTest(unittest.TestCase):
    def test_tasklist_ordering_via_add_entity(self):
        """Test that TaskLists are stored in order based on lexicographical 
        ordering.
        
        This test ensures that TaskLists supplied to the TaskTree via the 
        add_entity() method are properly sorted. Proper sorting is by 
        the lexicographical ordering of the TaskList title, which should be
        considered case-insensitive.
        
        Arrange:
            - Create TaskLists Foo, Bar, baz.
            - Create expected TaskTree by appending nodes in the expected
            order.
        Act:
            - Create a new TaskTree using the input_tasklists data set.
        Assert:
            - That the TaskLists are in this order, from highest to lowest:
                - Bar
                - baz
                - Foo
        """
        ### Arrange ###
        expected_tasktree = TaskTree()
        expected_root = expected_tasktree.get_root_node()
        expected_tasklist_bar = TestDataTaskList("Bar")
        expected_tasktree.append(expected_root, expected_tasklist_bar)
        expected_tasklist_baz = TestDataTaskList("baz")
        expected_tasktree.append(expected_root, expected_tasklist_baz)
        expected_tasklist_foo = TestDataTaskList("Foo")
        expected_tasktree.append(expected_root, expected_tasklist_foo)
        
        
        ### Act ###
        actual_tasktree = TaskTree()
        actual_tasktree.add_entity(copy.deepcopy(expected_tasklist_foo))
        actual_tasktree.add_entity(copy.deepcopy(expected_tasklist_bar))
        actual_tasktree.add_entity(copy.deepcopy(expected_tasklist_baz))
        
        ### Assert ###
        self.assertEqual(expected_tasktree, actual_tasktree)
        
    def test_tasklist_ordering_with_empty_title(self):
        """Test that TaskLists are stored in order based on lexicographical 
        ordering.
        
        This test ensures that a TaskList that has no title and is supplied 
        to the TaskTree via the add_entity() method is correctly positioned
        at the top of the TaskList group.
        
        Arrange:
            - Create TaskLists Foo, Bar, Baz.
            - Create expected TaskTree by appending Foo, Bar, Baz nodes in 
            the expected order.
            - Create actual TaskTree by cloning the expected TaskTree.
            - Create expected empty TaskList (TaskList with no defined title).
            - Insert the expected empty TaskList into the first position of 
            the expected TaskTree.
        Act:
            - Insert a clone of the expected empty TaskList into the actual
            TaskTree via add_entity().
        Assert:
            - That the TaskLists are in this order, from highest to lowest:
                - [None]
                - Bar
                - Baz
                - Foo
        """
        ### Arrange ###
        expected_tasktree = TaskTree()
        expected_root = expected_tasktree.get_root_node()
        expected_tasklist_bar = TestDataTaskList("Bar")
        expected_tasktree.append(expected_root, expected_tasklist_bar)
        expected_tasklist_baz = TestDataTaskList("Baz")
        expected_tasktree.append(expected_root, expected_tasklist_baz)
        expected_tasklist_foo = TestDataTaskList("Foo")
        expected_tasktree.append(expected_root, expected_tasklist_foo)
        
        actual_tasktree = copy.deepcopy(expected_tasktree)
        
        expected_tasklist_empty = TaskList()
        expected_tasktree.insert(expected_tasktree.ROOT_PATH + (0,),
            expected_tasklist_empty)
        
        ### Act ###
        actual_tasktree.add_entity(copy.deepcopy(expected_tasklist_empty))
        
        ### Assert ###
        self.assertEqual(expected_tasktree, actual_tasktree)
        
    def test_tasklist_ordering_via_init_task_data(self):
        """Test that TaskLists are stored in order based on lexicographical 
        ordering.
        
        This test ensures that TaskLists supplied to the TaskTree as 
        initialization arguments are properly sorted.
        
        Arrange:
            - Create TaskLists Foo, Bar, Baz.
            - Create input_tasklists data set out of the new TaskLists.
        Act:
            - Create a new TaskTree using the input_tasklists data set.
        Assert:
            - That the TaskLists are in this order, from highest to lowest:
                - Bar
                - Baz
                - Foo
        """
        ### Arrange ###
        expected_tasktree = TaskTree()
        expected_root = expected_tasktree.get_root_node()
        expected_tasklist_bar = TestDataTaskList("Bar")
        expected_tasktree.append(expected_root, expected_tasklist_bar)
        expected_tasklist_baz = TestDataTaskList("Baz")
        expected_tasktree.append(expected_root, expected_tasklist_baz)
        expected_tasklist_foo = TestDataTaskList("Foo")
        expected_tasktree.append(expected_root, expected_tasklist_foo)
        
        actual_tasklists = {expected_tasklist_foo.entity_id:copy.deepcopy(expected_tasklist_foo),
            expected_tasklist_bar.entity_id:copy.deepcopy(expected_tasklist_bar),
            expected_tasklist_baz.entity_id:copy.deepcopy(expected_tasklist_baz)}
        
        ### Act ###
        actual_tasktree = TaskTree(tasklists=actual_tasklists)
        
        ### Assert ###
        self.assertEqual(expected_tasktree, actual_tasktree)
        
    def test_sort_tasklist_title_updated(self):
        """Test that the TaskTree is properly sorted by TaskList title and
        Task position.       
        
        Arrange:
            - Create TaskLists Foo, Bar, Baz.
            - Create expected TaskTree by appending Foo, Bar, Baz nodes in 
            the expected order.
            - Create actual TaskTree by cloning the expected TaskTree.
            - Insert the expected empty TaskList into the first position of 
            the expected TaskTree.
        Act:
            - Insert a clone of the expected empty TaskList into the actual
            TaskTree via add_entity().
        Assert:
            - That the TaskLists are in this order, from highest to lowest:
                - [None]
                - Bar
                - Baz
                - Foo
        """
        ### Arrange ###        
        expected_tasklist_bar = TestDataTaskList("Bar")
        expected_tasklist_car = copy.deepcopy(expected_tasklist_bar)
        expected_tasklist_car.title = TestDataEntitySupport.create_full_title("Car", TestDataTaskList)
        expected_tasklist_baz = TestDataTaskList("Baz")
        expected_tasklist_foo = TestDataTaskList("Foo")
                
        initial_tasktree = TaskTree()        
        initial_tasktree.add_entity(expected_tasklist_bar)
        initial_tasktree.add_entity(expected_tasklist_baz)
        initial_tasktree.add_entity(expected_tasklist_foo)
        
        expected_tasktree = TaskTree()   
        expected_tasktree.add_entity(copy.deepcopy(expected_tasklist_baz))
        expected_tasktree.add_entity(copy.deepcopy(expected_tasklist_car))
        expected_tasktree.add_entity(copy.deepcopy(expected_tasklist_foo))
        
        actual_tasktree = copy.deepcopy(initial_tasktree)
        
        ### Act ###
        actual_tasklist_bar = expected_tasktree.get_entity_for_id(expected_tasklist_bar.entity_id)
        actual_tasklist_bar.title = expected_tasklist_car.title
        actual_tasktree.update_entity(actual_tasklist_bar)
        actual_tasktree.sort()
        
        ### Assert ###
        self.assertEqual(expected_tasktree, actual_tasktree)
        
    def test_task_ordering_via_init_task_data(self):
        """Test that Tasks are stored in order based on position property 
        values.
        
        This test ensures that Tasks supplied to the TaskTree as 
        initialization arguments are properly sorted.
        
        Arrange:
            - Create parent TaskList Foo.
            - Create Tasks 01, 03, 00.
            - Create input_tasklists data set out of the new TaskLists.
        Act:
            - Create a new TaskTree using the input_tasklists data set.
        Assert:
            - That the TaskLists are in this order, from highest to lowest:
                - 01
                - 03
                - 00
        """
        ### Arrange ###
        expected_tasktree = TaskTree()
        expected_root = expected_tasktree.get_root_node()
        expected_tasklist_foo = TestDataTaskList("Foo")
        tasklist_foo_node = expected_tasktree.append(expected_root, expected_tasklist_foo)
        expected_task_01 = TestDataTask("01", position=01, tasklist_id=expected_tasklist_foo.entity_id)
        expected_tasktree.append(tasklist_foo_node, expected_task_01)
        expected_task_03 = TestDataTask("03", position=03, tasklist_id=expected_tasklist_foo.entity_id)
        expected_tasktree.append(tasklist_foo_node, expected_task_03)
        expected_task_00 = TestDataTask("00", position=00, tasklist_id=expected_tasklist_foo.entity_id)
        expected_tasktree.append(tasklist_foo_node, expected_task_00)
        
        actual_tasklists = {expected_tasklist_foo.entity_id:copy.deepcopy(expected_tasklist_foo)}
        actual_tasks = {expected_task_01.entity_id:copy.deepcopy(expected_task_01),
            expected_task_00.entity_id:copy.deepcopy(expected_task_00),
            expected_task_03.entity_id:copy.deepcopy(expected_task_03)}
        actual_all_tasks = {expected_tasklist_foo.entity_id: actual_tasks}
        
        ### Act ###
        actual_tasktree = TaskTree(tasklists=actual_tasklists, all_tasks=actual_all_tasks)
        
        ### Assert ###
        self.assertEqual(expected_tasktree, actual_tasktree)
#------------------------------------------------------------------------------ 

class PopulatedTaskTreeTest(ManagedFixturesTestSupport, unittest.TestCase):
    def setUp(self):
        """Set up basic test fixtures."""
        self.expected_tasktree = TaskDataTestSupport.create_tasktree()
        self.tasktree = TaskDataTestSupport.create_tasktree()

        self._register_fixtures(self.expected_tasktree, self.tasktree)

    def test_add_task(self):
        """Test that adding a Task to the TaskTree inserts the Task
        in the correct position in the tree.

        This new task should be inserted directly below the TaskList.

        Arrange:
            - Create new Task Foo for TaskList A.
            - Clone Task Foo into Task Foo Expected.
            - Append Task Foo Expected to the expected TaskTree, directly under
            TaskList A.
        Act:
            - Add Task Foo to the TaskTree.
        Assert:
            - That the expected and actual TaskTrees are identical.
            - That adding Task Foo a second time raises an error.
        """
        ### Arrange ###
        tasklist_a = self.expected_tasktree.get_entity_for_id(
            TestDataTaskList.convert_short_title_to_id("A"))
        task_foo = TestDataTask("Foo", tasklist_id=tasklist_a.entity_id)
        expected_task_foo = copy.deepcopy(task_foo)
        self.expected_tasktree.append(self.expected_tasktree.get_node((0, 0)),
            expected_task_foo)

        ### Act ###
        self.tasktree.add_entity(task_foo)

        ### Assert ###
        self.assertEqual(self.expected_tasktree, self.tasktree)
        with self.assertRaises(EntityOverwriteError):
            self.tasktree.add_entity(task_foo)

    def test_add_child_task(self):
        """Test that adding to the TaskTree a new Task that is the child of an
        existing Task inserts the new Task in the correct position in the tree.

        This new task should be inserted directly below the parent Task.

        Arrange:
            - Create new Task Foo for TaskList A.
            - Clone Task Foo into Task Foo Expected.
            - Append Task Foo Expected to the expected TaskTree, directly under
            Task B.
        Act:
            - Add Task Foo to the TaskTree.
        Assert:
            - That the expected and actual TaskTrees are identical.
        """
        ### Arrange ###
        expected_tasklist_a = self.expected_tasktree.get_entity_for_id(
            TestDataTaskList.convert_short_title_to_id("A"))
        task_b = self.expected_tasktree.get_entity_for_id("testdatatask-b")
        task_foo = TestDataTask("Foo", tasklist_id=expected_tasklist_a.entity_id,
            parent_id=task_b.entity_id)
        expected_task_foo = copy.deepcopy(task_foo)
        self.expected_tasktree.append(
            self.expected_tasktree.find_node_for_entity(task_b),
            expected_task_foo)

        ### Act ###
        self.tasktree.add_entity(task_foo)

        ### Assert ###
        self.assertEqual(self.expected_tasktree, self.tasktree)

    def test_add_tasklist(self):
        """Test that adding to the TaskTree a new TaskList inserts the new
        TaskList directly below the root of the tree.

        Arrange:
            - Create new TaskList Foo.
            - Clone TaskList Foo into TaskList Foo Expected.
            - Append TaskList Foo Expected to the expected TaskTree, directly under
            the tree root.
        Act:
            - Add TaskList Foo to the TaskTree.
        Assert:
            - That the expected and actual TaskTrees are identical.
        """
        ### Arrange ###
        tasklist_foo = TestDataTaskList("Foo")
        expected_tasklist_foo = copy.deepcopy(tasklist_foo)
        self.expected_tasktree.append(
            self.expected_tasktree.get_node(self.expected_tasktree.ROOT_PATH),
            expected_tasklist_foo)

        ### Act ###
        self.tasktree.add_entity(tasklist_foo)

        ### Assert ###
        self.assertEqual(self.expected_tasktree, self.tasktree)

    def test_all_entity_ids(self):
        """Test the all_entity_ids property of TaskTree, ensuring that it
        accurately reflects the IDs of the entities held by a populated
        TaskTree.

        Arrange:
            - Clear the TaskTree under test.
            - Create task data TaskList A and Task B, and add them to the 
            TaskTree.
            - Create a set of expected entity IDs reflecting the task data 
            added to TaskTree.
        Assert:
            - That the expected IDs set is equal to the test fixture's
            TaskTree.all_entity_ids property.
        """
        ### Arrange ###
        self.tasktree.clear()
        
        tasklist_a = TestDataTaskList("A")
        self.tasktree.add_entity(tasklist_a)
        
        task_b = TestDataTask("B", tasklist_id=tasklist_a.entity_id)        
        self.tasktree.add_entity(task_b)
        
        expected_entity_ids = set([tasklist_a.entity_id, task_b.entity_id])

        ### Assert ###
        self.assertEqual(expected_entity_ids, self.tasktree.all_entity_ids)

    def test_init_provided_data(self):
        """Test that providing TaskList and Task data through the constructor
        correctly populates the TaskTree.

        Arrange: 
            Find expected task data TaskList A, Tasks B,C.
        Act:
            Retrieve the actual TaskList and Task entities from the TaskTree.
        Assert:
            That the TaskTree has the expected TaskList and Task elements.
        """
        ### Arrange ###        
        expected_tasklist_a = self.expected_tasktree.get_entity_for_id(
            TestDataTaskList.convert_short_title_to_id("A"))
        expected_task_b = self.expected_tasktree.get_entity_for_id(
            TestDataTask.convert_short_title_to_id("B"))
        expected_task_c = self.expected_tasktree.get_entity_for_id(
            TestDataTask.convert_short_title_to_id("C"))

        ### Act ###
        actual_tasklist_a = self.tasktree.get((0,))
        actual_task_b = self.tasktree.get((0, 0))
        actual_task_c = self.tasktree.get((0, 1))

        ### Assert ###
        self.assertEqual(expected_tasklist_a, actual_tasklist_a)
        self.assertEqual(expected_task_b, actual_task_b)
        self.assertEqual(expected_task_c, actual_task_c)

    def test_get_tasks_for_tasklist(self):
        """Test that all Tasks belonging to a certain TaskList can be 
        retrieved by providing that TaskList.

        Arrange:
            - Clear the TaskTree under test.
            - Create task data TaskList A and Tasks B and C, and add them 
            to the TaskTree.
            - Create a dict of expected tasks reflecting the Tasks 
            added to TaskTree.
        Act:
            - Retrieve the actual Tasks associated with the expected 
            TaskList via get_tasks_for_tasklist().
        Assert:
            - That the expected and actual Task dicts are identical.
        """
        ### Arrange ###        
        self.tasktree.clear()
        
        tasklist_a = TestDataTaskList("A")
        self.tasktree.add_entity(tasklist_a)
        
        task_b = TestDataTask("B", tasklist_id=tasklist_a.entity_id)        
        self.tasktree.add_entity(task_b)
        
        task_c = TestDataTask("C", tasklist_id=tasklist_a.entity_id)        
        self.tasktree.add_entity(task_c)
        
        expected_tasks = {task_b.entity_id:task_b, task_c.entity_id:task_c}

        ### Act ###
        actual_tasks = self.tasktree.get_tasks_for_tasklist(tasklist_a)

        ### Assert ###
        self.assertEqual(expected_tasks, actual_tasks)

    def test_tasklists_property(self):
        """Test that the TaskTree can correctly generate a collection (dict) 
        containing of all of the TaskLists held within the TaskTree. 

        Arrange:
            - Clear the TaskTree under test.
            - Create task data TaskLists A, B, and C, and add them 
            to the TaskTree.
            - Create a dict of expected TaskLists reflecting those just 
            added to TaskTree.
        Act:
            - Retrieve the actual dict of TaskLists from the TaskTree using the 
            tasklists property.
        Assert:
            - That the expected and actual TaskList dicts are identical.
        """
        ### Arrange ###        
        self.tasktree.clear()
        
        tasklist_a = TestDataTaskList("A")
        self.tasktree.add_entity(tasklist_a)
        
        tasklist_b = TestDataTaskList("B")
        self.tasktree.add_entity(tasklist_b)
        
        tasklist_c = TestDataTaskList("C")
        self.tasktree.add_entity(tasklist_c)
        
        expected_tasklists = {tasklist_a.entity_id:tasklist_a,
            tasklist_b.entity_id:tasklist_b,
            tasklist_c.entity_id:tasklist_c}

        ### Act ###
        actual_tasklists = self.tasktree.tasklists

        ### Assert ###
        self.assertEqual(expected_tasklists, actual_tasklists)

    def test_get_entity_tasklist(self):
        """Test that searching the TaskTree for an entity ID belonging to a
        TaskList will return that TaskList instance.

        Arrange:
            Find expected TaskList A.
        Act:
            Search for a TaskList with the entity ID of the expected TaskList.
        Assert:
            That the found TaskList is equal to the expected TaskList, without
            considering the updated date.
        """
        ### Arrange ###
        expected_tasklist_a = self.expected_tasktree.get_entity_for_id(
            TestDataTaskList.convert_short_title_to_id("A"))

        ### Act ###
        actual_tasklist_a = self.tasktree.get_entity_for_id(expected_tasklist_a.entity_id)

        ### Assert ###
        now_timestamp = datetime.now()
        expected_tasklist_a.updated_date = actual_tasklist_a.updated_date = now_timestamp
        self.assertEqual(expected_tasklist_a, actual_tasklist_a)

    def test_get_entity_task(self):
        """Test that searching the TaskTree for an entity ID belonging to a
        Task will return that Task instance.

        Act:
            Search for a Task with the entity ID of the expected Task C.
        Assert:
            That the found Task is equal to the expected Task.
        """
        ### Arrange ###        
        expected_tasklist_a = self.expected_tasktree.get_entity_for_id(
            TestDataTaskList.convert_short_title_to_id("A"))
        expected_task_c = self.expected_tasktree.get_entity_for_id(
            TestDataTask.convert_short_title_to_id("C"))

        ### Act ###
        actual_task_c = self.tasktree.get_entity_for_id(expected_task_c.entity_id)

        ### Assert ###
        self.assertEqual(expected_task_c, actual_task_c)

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
        with self.assertRaises(UnregisteredEntityError):
            self.tasktree.get_entity_for_id(expected_bogus_id)

    def test_remove_entity_tasklist(self):
        """Test that removing TaskList A from the tree removes both the
        TaskList and any child Tasks.

        The difference between deleting a TaskList and a Task is that when a
        TaskList is deleted, so are all of the child Tasks. When a Task is
        deleted, only it is deleted, while any children of that deleted Task
        move into the same position occupied by the deleted Task.

        When removing a TaskList, the remove_entity method should be called
        with the remove_children flag set to True to ensure child Tasks are
        also cleared away.

        Arrange:
            - Find expected TaskList A.
        Act:
            - Delete TaskList A.
        Assert:
            - That TaskList A cannot be found via get_entity_for_id.
            - That the two child Tasks cannot be found via get_entity_for_id.
        """
        ### Arrange ###        
        expected_tasklist_a = self.expected_tasktree.get_entity_for_id(
            TestDataTaskList.convert_short_title_to_id("A"))
        expected_task_b = self.expected_tasktree.get_entity_for_id(
            TestDataTask.convert_short_title_to_id("B"))
        expected_task_c = self.expected_tasktree.get_entity_for_id(
            TestDataTask.convert_short_title_to_id("C"))
        
        ### Act ###
        self.tasktree.remove_entity(expected_tasklist_a)

        ### Assert ###
        with self.assertRaises(UnregisteredEntityError):
            self.tasktree.get_entity_for_id(expected_tasklist_a.entity_id)
            
        with self.assertRaises(UnregisteredEntityError):
            self.tasktree.get_entity_for_id(expected_task_b.entity_id)
            
        with self.assertRaises(UnregisteredEntityError):
            self.tasktree.get_entity_for_id(expected_task_c.entity_id)

    def test_remove_entity_childless_task(self):
        """Test that removing a Task from the TaskTree eliminates the Task
        from within the Tree.
        
        This test will be executed against a childless (leaf-node) Task.

        Arrange:
            - Find expected Task D.
        Act:
            - Delete Task D.
        Assert:
            - That Task D cannot be found via TaskTree.get_entity_for_id.
            - That attempting to remove Task D a second time raises an error.
            - That Task D can successfully be added back in after it has been
            removed.
        """
        ### Arrange ###        
        expected_task_d = self.expected_tasktree.get_entity_for_id(
            TestDataTask.convert_short_title_to_id("D"))
        
        ### Act ###
        self.tasktree.remove_entity(expected_task_d)

        ### Assert ###
        with self.assertRaises(UnregisteredEntityError):
            self.tasktree.get_entity_for_id(expected_task_d.entity_id)
            
        with self.assertRaises(UnregisteredEntityError):
            self.tasktree.remove_entity(expected_task_d)
            
        self.tasktree.add_entity(expected_task_d)
        actual_task_d = self.tasktree.get_entity_for_id(expected_task_d.entity_id)
        self.assertEqual(expected_task_d, actual_task_d)

    def test_remove_entity_parent_task(self):
        """Test that removing a parent Task from the TaskTree eliminates the 
        Task while preserving the Task's descendant Tasks.
        
        Any direct child Tasks of the deleted Task should move up to take the
        position of the deleted Task under the deleted Task's parent.

        Arrange:
            - Find expected Task C (parent of Tasks E, F).
        Act:
            - Delete Task C.
        Assert:
            - That Task C cannot be found via TaskTree.get_entity_for_id.
            - That Tasks E, F can be found via TaskTree.get_entity_for_id.
            - That the order of Tasks below TaskList A are: B, E, F, D.
        """
        ### Arrange ###        
        expected_task_c = self.expected_tasktree.get_entity_for_id(
            TestDataTask.convert_short_title_to_id("C"))
        expected_task_e = self.tasktree.get_entity_for_id(
            TestDataTask.convert_short_title_to_id("E"))
        expected_task_f = self.tasktree.get_entity_for_id(
            TestDataTask.convert_short_title_to_id("F"))
        
        ### Act ###
        self.tasktree.remove_entity(expected_task_c)

        ### Assert ###
        with self.assertRaises(UnregisteredEntityError):
            self.tasktree.get_entity_for_id(expected_task_c.entity_id)
        
        actual_task_e = self.tasktree.get_entity_for_id(
            TestDataTask.convert_short_title_to_id("E"))
        self.assertEqual(expected_task_e, actual_task_e)
        
        actual_task_f = self.tasktree.get_entity_for_id(
            TestDataTask.convert_short_title_to_id("F"))
        self.assertEqual(expected_task_f, actual_task_f)

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
        expected_tasklist_a = self.expected_tasktree.get_entity_for_id(
            TestDataTaskList.convert_short_title_to_id("A"))
        expected_entity_node = self.tasktree.get_node((0, 0))

        ### Act ###
        actual_entity_node = self.tasktree.find_node_for_entity(
            expected_tasklist_a)

        ### Assert ###
        self.assertEqual(expected_entity_node, actual_entity_node)

    def test_update_entity_task(self):
        """Test that updating a Task only updates the corresponding value in
        the TaskTree after update_entity() is called.

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
        expected_task_c = copy.deepcopy(
            self.expected_tasktree.get_entity_for_id("testdatatask-c"))
        expected_task_c.title = "updated"

        ### Act ###
        preop_task_c = self.tasktree.get_entity_for_id(expected_task_c.entity_id)
        self.tasktree.update_entity(expected_task_c)
        postop_task_c = self.tasktree.get_entity_for_id(expected_task_c.entity_id)

        ### Assert ###
        self.assertNotEqual(expected_task_c, preop_task_c)
        self.assertEqual(expected_task_c, postop_task_c)
#------------------------------------------------------------------------------ 

class UpdatedDateFilteredTask(Task):
    def _get_comparable_properties(self):
        comparable_props = Task._get_comparable_properties(self)

        return set(comparable_props).difference(("updated_date",))
#------------------------------------------------------------------------------ 

class UpdatedDateFilteredTaskList(TaskList):
    def _get_comparable_properties(self):
        comparable_props = TaskList._get_comparable_properties(self)

        return set(comparable_props).difference(("updated_date",))
#------------------------------------------------------------------------------ 

class TestDataTaskList(TaskList):
    def __init__(self, short_title, **kwargs):
        # Create a full title from the provided short title.
        title = TestDataEntitySupport.create_full_title(short_title, self.__class__)

        # Create an entity id from the full title.
        entity_id = TestDataEntitySupport.convert_title_to_id(title)

        TaskList.__init__(self, entity_id=entity_id, title=title,
            updated_date=datetime.now(), **kwargs)
        
    @classmethod
    def convert_short_title_to_id(cls, short_title):
        # Create a full title from the provided short title.
        title = TestDataEntitySupport.create_full_title(short_title, cls)

        # Create an entity id from the full title.
        entity_id = TestDataEntitySupport.convert_title_to_id(title)
        
        return entity_id
#------------------------------------------------------------------------------ 

class TestDataTaskListTest(unittest.TestCase):
    def test_create_test_tasklist(self):
        """Test the creation of a simple TestDataTaskList.

        Ensure that the provided short title is properly converted into a
        long title, and the ID is automatically generated from the full title.

        Arrange:
            - Create expected long title "TestDataTaskList A".
            - Create expected entity ID "testdatatasklist-A".
        Act:
            - Create new TestDataTaskList A with short title of "A".
        Assert:
            - That TestDataTaskList A has the expected long title and entity
            ID.
        """
        ### Arrange ###
        expected_long_title = "TestDataTaskList A"
        expected_id = "testdatatasklist-a"

        ### Act ###
        actual_tasklist_a = TestDataTaskList("A")

        ### Assert ###
        self.assertEqual(expected_long_title, actual_tasklist_a.title)
        self.assertEqual(expected_id, actual_tasklist_a.entity_id)

    def test_convert_short_title_to_id(self):
        """Test converting a short title into an ID.

        Should produce an ID of "testdatatasklist-a" when provided with a 
        short title "A".

        Arrange:
            - Create expected entity ID.
        Act:
            - Convert the short title "A" to the actual entity ID.
        Assert:
            - That the expected and actual IDs are the same.
        """
        ### Arrange ###
        expected_entity_id = "testdatatasklist-a"

        ### Act ###
        actual_entity_id = TestDataTaskList.convert_short_title_to_id("A")

        ### Assert ###
        self.assertEqual(expected_entity_id, actual_entity_id)
#------------------------------------------------------------------------------ 

class TestDataTask(Task):
    def __init__(self, short_title, **kwargs):
        # Create a full title from the provided short title.
        title = TestDataEntitySupport.create_full_title(short_title, self.__class__)

        # Create an entity id from the full title.
        entity_id = self.convert_short_title_to_id(short_title)

        Task.__init__(self, entity_id=entity_id, title=title,
            updated_date=datetime.now(), **kwargs)
        
    """
    TODO: As both TestDataTask and TestDataTaskList share this identical
    method, it should probably be moved out to a common mixin class.
    """ 
    @classmethod
    def convert_short_title_to_id(cls, short_title):
        # Create a full title from the provided short title.
        title = TestDataEntitySupport.create_full_title(short_title, cls)

        # Create an entity id from the full title.
        entity_id = TestDataEntitySupport.convert_title_to_id(title)
        
        return entity_id
#------------------------------------------------------------------------------ 

class TestDataTaskTest(unittest.TestCase):
    def test_create_test_task(self):
        """Test the creation of a simple TestDataTask.

        Ensure that the provided short title is properly converted into a
        long title, and the ID is automatically generated from the full title.

        Arrange:
            - Create expected long title "TestDataTask A".
            - Create expected entity ID "testdatatask-A".
        Act:
            - Create new TestDataTask A with short title of "A".
        Assert:
            - That TestDataTask A has the expected long title and entity
            ID.
        """
        ### Arrange ###
        expected_long_title = "TestDataTask A"
        expected_id = "testdatatask-a"

        ### Act ###
        actual_task_a = TestDataTask("A")

        ### Assert ###
        self.assertEqual(expected_long_title, actual_task_a.title)
        self.assertEqual(expected_id, actual_task_a.entity_id)

    def test_convert_short_title_to_id(self):
        """Test converting a short title into an ID.

        Should produce an ID of "testdatatask-a" when provided with a 
        short title "A".

        Arrange:
            - Create expected entity ID.
        Act:
            - Convert the short title "A" to the actual entity ID.
        Assert:
            - That the expected and actual IDs are the same.
        """
        ### Arrange ###
        expected_entity_id = "testdatatask-a"

        ### Act ###
        actual_entity_id = TestDataTask.convert_short_title_to_id("A")

        ### Assert ###
        self.assertEqual(expected_entity_id, actual_entity_id)
#------------------------------------------------------------------------------ 

class UpdatedDateIgnoredTestDataTaskList(TestDataTaskList, UpdatedDateFilteredTaskList):
    pass
#------------------------------------------------------------------------------ 

class UpdatedDateIgnoredTestDataTask(TestDataTask, UpdatedDateFilteredTask):
    pass
#------------------------------------------------------------------------------ 

class TestDataEntitySupport(object):
    @staticmethod
    def convert_title_to_id(title):
        # Convert to lowercase.
        entity_id = title.lower()

        # Replace spaces with dashes.
        entity_id = entity_id.replace(" ", "-")

        return entity_id

    @staticmethod
    def create_full_title(short_title, entity_class):
        # Get the short name of the entity.
        entity_class_name = entity_class.__name__

        # Create a full title by combining the entity's class name and the
        # short title provided.
        full_title = "{class_name} {short_title}".format(
            class_name=entity_class_name, short_title=short_title)

        return full_title
#------------------------------------------------------------------------------ 

class TestDataEntitySupportTest(unittest.TestCase):
    def test_convert_title_to_id(self):
        """Test converting a simple Task title to an entity ID.

        Will attempt to convert "Task A" to "task-a".

        Arrange:
            - Create title "Task A".
            - Create expected ID "task-a".
        Act:
            - Convert title to actual ID.
        Assert:
            - That the expected and actual converted IDs are the same.
        """
        ### Arrange ###
        expected_title = "Task A"
        expected_id = "task-a"

        ### Act ###
        actual_id = TestDataEntitySupport.convert_title_to_id(expected_title)

        ### Assert ###
        self.assertEqual(expected_id, actual_id)

    def test_create_full_title_task(self):
        """Test creating a full title for a Task entity.

        Should produce a full title of "Task A" from a short title of
        "A".

        Arrange:
            - Create expected full title "Task A".
        Act:
            - Convert the short title "A" to the actual full title.
        Assert:
            - That the expected and actual full titles are the same.
        """
        ### Arrange ###
        expected_full_title = "Task A"

        ### Act ###
        actual_full_title = TestDataEntitySupport.create_full_title("A", Task)

        ### Assert ###
        self.assertEqual(expected_full_title, actual_full_title)
#------------------------------------------------------------------------------ 

class TaskDataTestSupport(object):
    """Simple support class to make it more convenient to product mock TaskList
    and Task data for use in testing."""
    @classmethod
    def create_tasklists(cls, tasklist_type=TaskList, entity_id_prefix="tl-",
        title_prefix="TaskList ", begin_count=0, end_count=3):
        """Create a dictionary of TaskList objects.

        Each TaskList object will be given a unique ID and title, beginning
        with the associated prefixes and ending with an alphabetic character
        corresponding to the creation order of the TaskList.
        The method will create begin_count - end_count TaskLists.

        Args:
            entity_id_prefix: str prefix for the TaskList ID.
            title_prefix: str prefix for the TaskList title.
            begin_count: int for the index of the first character suffix.
            end_count: int for the index of the final character suffix.
        Returns:
            A dictionary keyed with the TaskList IDs, with values mapping to
            the corresponding TaskList instance.
        """
        assert begin_count < end_count

        updated_date = datetime.now()

        tasklists = {entity_id_prefix + string.ascii_uppercase[x]:
            tasklist_type(entity_id=entity_id_prefix + string.ascii_uppercase[x],
            title=title_prefix + string.ascii_uppercase[x],
            updated_date=updated_date)
            for x in range(begin_count, end_count)}

        return tasklists

    @classmethod
    def create_all_tasks(cls, tasklists, task_type=Task):
        updated_date = datetime.now()

        all_tasks = dict()
        for tasklist in tasklists.values():
            t_a = task_type(entity_id=tasklist.entity_id + "-t-A",
                tasklist_id=tasklist.entity_id, title="Task A",
                updated_date=updated_date)
            t_b = task_type(entity_id=tasklist.entity_id + "-t-B",
                tasklist_id=tasklist.entity_id, title="Task B",
                parent_id=t_a.entity_id, updated_date=updated_date)
            t_c = task_type(entity_id=tasklist.entity_id + "-t-C",
                tasklist_id=tasklist.entity_id, title="Task C",
                parent_id=t_a.entity_id, updated_date=updated_date)

            all_tasks[tasklist.entity_id] = {t_a.entity_id:t_a,
                t_b.entity_id:t_b, t_c.entity_id:t_c}

        return all_tasks

    @classmethod
    def create_tasktree(cls, tasklist_type=TaskList, task_type=Task):
        """This will establish a two-level tree of task data.

        The tree consists of a single TaskList A, with child Tasks B..F.
        The data should create a tree with the following architecture:

        - tl-A
            - t-B
            - t-C
                - t-E
                - t-F
            - t-D
        """
        tasklist_a = TestDataTaskList("A")

        task_b = TestDataTask("B", tasklist_id=tasklist_a.entity_id,
            position=1)

        task_c = TestDataTask("C", tasklist_id=tasklist_a.entity_id,
            position=2)
        task_e = TestDataTask("E", tasklist_id=tasklist_a.entity_id,
            position=1, parent_id=task_c.entity_id)
        task_f = TestDataTask("F", tasklist_id=tasklist_a.entity_id,
            position=2, parent_id=task_c.entity_id)

        task_d = TestDataTask("D", tasklist_id=tasklist_a.entity_id,
            position=3)

        tasklists = {tasklist_a.entity_id: tasklist_a}
        tasklist_a_tasks = {task_b.entity_id:task_b,
            task_c.entity_id:task_c,
            task_d.entity_id:task_d,
            task_e.entity_id:task_e,
            task_f.entity_id:task_f}
        all_tasks = {tasklist_a.entity_id: tasklist_a_tasks}

        """
        TODO: This should be updated to provide the task data in a single, 
        "flat" dictionary collection.
        """
        # Use the task data to build the TaskTree.
        tasktree = TaskTree(tasklists=tasklists, all_tasks=all_tasks)

        return tasktree
    
    @classmethod
    def create_dynamic_tasktree(cls, tasklist_type=TestDataTaskList,
        task_type=TestDataTask, siblings_count=3,
        tree_depth=3):
        
        tasklists = dict()
        all_tasks = dict()
        
        for tl_i in range(0, siblings_count):
            tasklist_short_title = string.ascii_uppercase[tl_i]
            tasklist = tasklist_type(tasklist_short_title)
            tasklists[tasklist.entity_id] = tasklist
                      
            tasklist_tasks = cls._create_task_branch(task_type,
                tasklist_short_title, tasklist.entity_id, None,
                siblings_count, tree_depth - 1, 1)
            all_tasks[tasklist.entity_id] = tasklist_tasks
            
        tasktree = TaskTree(tasklists=tasklists, all_tasks=all_tasks)
        return tasktree
    
    @classmethod
    def _create_task_branch(cls, task_type, parent_title, tasklist_id,
        parent_task_id, siblings_count, tree_depth, current_depth):
        
        tasks = dict()
        
        for t_i in range(0, siblings_count):
            task_short_title = parent_title + "-" + string.ascii_uppercase[t_i]
            task = task_type(task_short_title, tasklist_id=tasklist_id,
                parent_id=parent_task_id)
            
            tasks[task.entity_id] = task
            
            if current_depth < tree_depth:
                child_tasks = cls._create_task_branch(task_type,
                    task_short_title, tasklist_id, task.entity_id,
                    siblings_count, tree_depth, current_depth + 1)
                tasks.update(child_tasks)
        
        return tasks
#------------------------------------------------------------------------------

class TaskDataTestSupportTest(unittest.TestCase):
    def test_create_dynamic_tasktree(self):
        """Test the creation of a "4x3" TaskTree.
        
        A "4x3" TaskTree should have three siblings for every level, and a 
        depth (height?) of four branches.
        
        Arrange:
            - Create expected TaskList A and Task A-C-C.
        Act:
            - Create a TaskTree with three TaskLists and a depth of 3 
            (TaskList plus two levels of Tasks).
            - Find the actual TaskList A and Task A-C-C.
        Assert:
            - That the expected and actual TaskList A and Task A-C-C are equal.
        """
        ### Arrange ###
        expected_tasklist_a = TestDataTaskList("A")
        expected_task_acc = TestDataTask("A-C-C",tasklist_id=expected_tasklist_a.entity_id, parent_id="testdatatask-a-c")
            
        ### Act ###
        tasktree = TaskDataTestSupport.create_dynamic_tasktree(
            tasklist_type=TestDataTaskList, task_type=TestDataTask,
            siblings_count=3, tree_depth=3)
        
        actual_tasklist_a = tasktree.get_entity_for_id("testdatatasklist-a")
        actual_task_acc = tasktree.get_entity_for_id("testdatatask-a-c-c")
        
        ### Assert ###
        self.assertEqual(expected_tasklist_a, actual_tasklist_a)
        self.assertEqual(expected_task_acc, actual_task_acc)
        
class TaskTreeComparator(object):
    @classmethod
    def find_added_ids(cls, baseline_tree, altered_tree):
        # Find all entity IDs that are present in the altered tree but not in
        # the baseline tree.
        added_ids = altered_tree.all_entity_ids - baseline_tree.all_entity_ids
        
        return added_ids
    
    @classmethod
    def find_deleted_ids(cls, baseline_tree, altered_tree):
        # Find all entity IDs that were present in the baseline tree but are
        # missing in the altered tree.
        deleted_ids = baseline_tree.all_entity_ids - altered_tree.all_entity_ids
        
        return deleted_ids
#------------------------------------------------------------------------------ 

class TaskTreeComparatorTest(ManagedFixturesTestSupport, unittest.TestCase):
    def setUp(self):
        """Set up basic test fixtures."""

        # All tests in this test case will compare a pair of tree, original and 
        # current.
        self.original_tasktree = TaskDataTestSupport.create_tasktree()
        self.current_tasktree = TaskDataTestSupport.create_tasktree()

        # Create the TaskTreeComparator that will be under test.
        self.comparator = TaskTreeComparator()

        self._register_fixtures(self.original_tasktree, self.current_tasktree,
            self.comparator)
    
    def test_find_added(self):
        """Test that the TaskTreeComparator can identify any new entities added
        to a TaskTree.

        Four new entities will be added. The updated current TaskTree should
        have this architecture, where an asterisk (*) denotes an added entity:

        - tl-A
            - t-B
            - t-C
                - t-E
                - t-F
            - t-D
                - t-G *
        - tl-B *
            - t-B-A *
            - t-B-B *

        Arrange:
            - Add a TaskList B to current TaskTree.
            - Add Tasks B-A, B-B to TaskList B in current TaskTree.
            - Add Task G to TaskList A, Task D in current TaskTree.
            - Create a new set representing the IDs of the new entities.
        Act:
            - Use TaskTreeComparator.find_added to locate all task data that
            was added during the Arrange phase.
        Assert:
            - That the expected and actual sets of added entity IDs are
            identical.
        """
        ### Arrange ###
        tasklist_a = self.current_tasktree.get_entity_for_id("testdatatasklist-a")
        task_d = self.current_tasktree.get_entity_for_id("testdatatask-d")
        
        tasklist_b = self.current_tasktree.add_entity(TestDataTaskList("B"))
        task_b_a = self.current_tasktree.add_entity(TestDataTask("B-A", tasklist_id=tasklist_b.entity_id))
        task_b_b = self.current_tasktree.add_entity(TestDataTask("B-B", tasklist_id=tasklist_b.entity_id))
        task_g = self.current_tasktree.add_entity(TestDataTask("G", tasklist_id=tasklist_a.entity_id, parent_id=task_d.entity_id))
        
        expected_added_ids = set([tasklist_b.entity_id, task_b_a.entity_id,
            task_b_b.entity_id, task_g.entity_id])

        ### Act ###
        actual_added_ids = self.comparator.find_added_ids(self.original_tasktree,
            self.current_tasktree)

        ### Assert ###
        self.assertEqual(expected_added_ids, actual_added_ids)
    
    def test_find_added_no_change(self):
        """Test that the TaskTreeComparator finds no new entity IDs when a
        TaskTree remains unchanged.
        Act:
            - Use TaskTreeComparator.find_added to locate any added entities 
            (there should be none).
        Assert:
            - That the expected and actual sets of added entity IDs are
            identical.
        """
        ### Act ###
        actual_added_ids = self.comparator.find_added_ids(self.original_tasktree,
            self.current_tasktree)

        ### Assert ###
        self.assertEqual(set(), actual_added_ids)

    def test_find_deleted_tasks(self):
        """Test that the TaskTreeComparator can identify any entities that 
        were removed from a TaskTree.

        Two entities will be removed. The updated current TaskTree should
        have this architecture, where an asterisk (*) denotes a removed entity:

        - tl-A
            - t-B *
            - t-C
                - t-E
                - t-F
            - t-D *

        Arrange:
            - Remove Tasks B,D from the TaskTree.
            - Create a new set representing the IDs of the removed entities.
        Act:
            - Use TaskTreeComparator.find_added to locate all task data that
            was added during the Arrange phase.
        Assert:
            - That the expected and actual sets of added entity IDs are
            identical.
        """
        ### Arrange ###
        task_b = self.current_tasktree.get_entity_for_id("testdatatask-b")
        task_d = self.current_tasktree.get_entity_for_id("testdatatask-d")
        
        self.current_tasktree.remove_entity(task_b)
        self.current_tasktree.remove_entity(task_d)
        
        expected_deleted_ids = set([task_b.entity_id, task_d.entity_id])

        ### Act ###
        actual_deleted_ids = self.comparator.find_deleted_ids(self.original_tasktree,
            self.current_tasktree)

        ### Assert ###
        self.assertEqual(expected_deleted_ids, actual_deleted_ids)
#------------------------------------------------------------------------------

class TaskDataError(Exception):
    def __init__(self, message):
        Exception.__init__(self, "Corrupt task data: " + message) 
#------------------------------------------------------------------------------ 
