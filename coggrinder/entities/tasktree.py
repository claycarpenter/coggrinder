'''
Created on May 5, 2012

@author: Clay Carpenter
'''

import unittest
from unittest import skip
from datetime import datetime
from coggrinder.entities.tasks import Task, TaskList, TestDataEntitySupport, \
    TestDataTaskList, TestDataTask, UpdatedDateIgnoredTestDataTask, UpdatedDateIgnoredTestDataTaskList, \
    SortedTaskDataChildrenSupport, GoogleServicesTask
from coggrinder.entities.tree import Tree
from coggrinder.core.test import ManagedFixturesTestSupport, DISABLED_WORKING_OTHER_TESTS
import copy
import string
from coggrinder.services.task_services import UnregisteredTaskListError, \
    EntityOverwriteError, UnregisteredEntityError, UnregisteredTaskError
from coggrinder.entities.properties import TaskStatus
from logging import debug as temp_debug
from coggrinder.core.comparable import DeclaredPropertiesComparable

class TaskTree(SortedTaskDataChildrenSupport, Tree):
    def __init__(self, tasklists=None, all_tasks=None, task_data=None):
        Tree.__init__(self, value="<TaskTree>")
        
        # Compile a tree from the provided task data.
        if task_data is None:                
            task_data = dict()
                            
        self._build_tree(task_data)

    @property
    def entity_ids(self):
        """A set of IDs representing all known entities held by the TaskTree."""
        entity_ids = [x.entity_id for x in self.descendants]

        return set(entity_ids)
    
    @property
    def tasklists(self):        
        # Collect all of the direct children of this tree. Each 
        # child should represent a TaskList.        
        tasklists = {x.entity_id:x for x in self.children}
            
        return tasklists
    
    @property
    def all_tasks(self):
        """Returns a collection of all Task-type entities currently held by 
        the TaskTree.
        
        This collection is in the form of a dictionary. The dictionary keys 
        are the entity IDs, while the values are the corresponding entity 
        instances.
        """
        all_tasks = dict()
        
        # Collect all of the Tasks (all your Tasks are belong to us?), 
        # grouping by their common TaskList parents.
        for tasklist in self.tasklists.values():
            tasks = self.get_tasks_for_tasklist(tasklist)
            all_tasks[tasklist.entity_id] = tasks
            
        return all_tasks
    
    @property
    def task_data(self):
        """Returns a collection of all entities currently held by the TaskTree.
        
        This collection is in the form of a dictionary. The dictionary keys 
        are the entity IDs, while the values are the corresponding entity 
        instances.
        
        Note: this collection is dynamically built upon each call. If calling
        code knows that the data underlying a TaskTree won't be modified, it 
        might make sense to cache the result of this property call.        
        """            
        task_data = {x.entity_id:x for x in self.descendants}
        
        return task_data

    def _build_tree(self, task_data):
        """Build the full tree from the task data."""

        # Clear the existing tree architecture.
        self.clear()
        
        # Add all entities to their parent.
        for entity in task_data.values():
            try:
                # All Tasks should have the parent ID attribute.
                parent_id = entity.parent_id
                
                if parent_id is not None:
                    # This Task is a child of another Task.
                    parent = task_data[entity.parent_id]
                else:
                    # This Task is directly a child of a TaskList.
                    parent = task_data[entity.tasklist_id]
            except AttributeError:
                # No parent ID, entity must be a TaskList. 
                # A TaskList is a direct child of the TaskTree.
                parent = self
                
            # Register the current entity as a child of its parent.
            parent.add_child(entity)
    
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
                if task.tasklist_id not in self._entity_map:
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
                
    def _register_entity(self, entity):
        """Register the entity and all child entities.
        
        Raises:
            EntityOverwriteError is the entity is already registered.
        """
        if entity.entity_id in self._entity_map:
            raise EntityOverwriteError(entity.entity_id)
                
        self._entity_map[entity.entity_id] = entity
        
        for child in entity.children:
            self._register_entity(child)
    
    def _deregister_entity(self, entity, recursively_deregister=False):        
        try:
            del self._entity_map[entity.entity_id]
        except KeyError:
            raise UnregisteredEntityError(entity.entity_id)
        
        if recursively_deregister:
            # Recursively deregister all of the node's descendants.
            # This should probably only need to be done when the 
            # deregistration target is a TaskList.
            for child_task in entity.children:
                self._deregister_entity(child_task,
                    recursively_deregister=recursively_deregister)

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
            
            # Find the correct position for the new entity.
            entity_address = self._find_new_entity_node_address(parent_node, entity)
        except AttributeError:
            # No TaskList ID found, assuming this is a TaskList.
            parent_node = self.get_node(self.ROOT_PATH)

            # Find the correct position for the new entity.
            entity_address = self._find_new_entity_node_address(parent_node, entity)
        
        entity_node = self.insert(entity_address, entity)
        self._register_entity_node(entity_node)
                
        # If the entity is a Task, set the previous Task property.
        try:
            self._set_sibling_task_id(parent_node, entity_node)
            temp_debug("Updated Task to have previous Task ID: {0}".format(entity.previous_task_id))                
        except AttributeError:
            # Ignore; simply indicates entity is not a Task.
            pass        
        
        if self._is_task_node(entity_node):
            temp_debug("Updating Task sibling relationships, possibly for no reason.")
            # Entity is a Task, update the previous Task IDs of all siblings
            # in this Task group.
            self._update_child_task_relationships(parent_node)
        
        return entity
    
    def _find_new_entity_node_address(self, parent_node, entity):
        position = len(parent_node.children)
                
        for sibling_entity_node in parent_node.children:
            sibling_entity = sibling_entity_node.value
            
            if sibling_entity > entity:
                position = parent_node.children.index(sibling_entity_node)
                break
               
        return parent_node.path + (position,)
    
    def _update_child_task_relationships(self, parent_node):
        parent_entity = parent_node.value
        for sibling_task_node in parent_node.children:                            
            sibling_task = sibling_task_node.value      
            
            # Ensure that the parent reference is accurate. If the current
            # parent entity is a TaskList (indicated by equality between the 
            # current parent entity ID and the sibling task's tasklist ref.), 
            # set parent to None. Otherwise, set the sibling task's parent ref
            # to point to the current parent Task.
            if parent_entity.entity_id == sibling_task.tasklist_id:
                sibling_task.parent_id = None
            else:
                sibling_task.parent_id = parent_entity.entity_id
            
            # Update Task sibling links.          
            self._set_sibling_task_id(parent_node, sibling_task_node)
                
    def _set_sibling_task_id(self, parent_node, task_node):
        # If the task has a previous task ID, use that to make sure that it's
        # place in the correct position under the parent.
        
        # If the task doesn't have a previous Task ID, assign to that property 
        # the parent ID if it's an only child, or the ID of the previous
        # (last, or lowest ordered) Task in the sibling group.
        
        child_index = parent_node.children.index(task_node)
        task = task_node.value
        
        if child_index == 0:
            task.previous_task_id = task.parent_id
        else:
            previous_task = parent_node.children[child_index - 1].value
            task.previous_task_id = previous_task.entity_id

    def _is_task_node(self, entity_node):
        return self._is_task_node_path(entity_node.path)

    def _is_task_node_path(self, entity_node_path):
        if len(entity_node_path) > 1:
            return True
        
        return False

    def clear(self):
        # Clear all of the TaskList children from the root object.
        self.children = list()
        
    def demote_task(self, *tasks):
        assert tasks is not None
        
        # Demote the targeted Tasks. 
        Tree.demote(self, *tasks)
        
        # Refresh the sibling links of both the old and new/current 
        # sibling groups.
        for task in tasks:
            self._update_child_task_relationships(task.parent.parent)
            self._update_child_task_relationships(task.parent)
    
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
        all_entities = self.descendants
        
        matching_entities = [x for x in all_entities if x.entity_id == entity_id]

        if not matching_entities:
            raise UnregisteredEntityError(entity_id)

        return matching_entities[0]

    def find_node_for_entity(self, entity):
        # Lookup the node in the entity-node mapping using the entity's ID.
        return self.find_node_for_entity_id(entity.entity_id)

    def find_node_for_entity_id(self, entity_id):        
        try:            
            if entity_id is None:
                """
                TODO: This should give a more descriptive error message.
                """
                raise KeyError
            
            # Lookup the node in the entity-node mapping.
            return self._entity_map[entity_id]
        except KeyError:
            raise UnregisteredEntityError(entity_id)
        
    def promote_task(self, *tasks):
        assert tasks
        
#        task_nodes = list()
        old_parent_nodes = list()
        for task in tasks:
#            task_nodes.append(task)
            
            # Get the current parent node now, as this reference will change 
            # after the Tree.promote operation. This reference provides an 
            # easy pointer to the correct node for refreshing child Task
            # relationships.
            old_parent_nodes.append(task.parent)
        
        # Promote the targeted Tasks.
        Tree.promote(self, *tasks)
        
        # Refresh the sibling links of both the new/current 
        # sibling groups.
        for task in tasks:            
            self._update_child_task_relationships(task.parent)
        
        # Refresh the sibling links of both the new/current 
        # sibling groups.
        for old_parent_node in old_parent_nodes:
            self._update_child_task_relationships(old_parent_node)
        
    def remove_entity(self, entity):
        # Find the entity's node.        
#        entity_node = self.find_node_for_entity(entity)        
        
        # If the entity isn't a direct descendant of the TaskTree (default)
        # root, then it is a Task.
        if entity.parent != self:
            # This entity is not a TaskList, so move all of the children up to
            # the position of the deleted entity. 
            
            # Deregister just the current Task (not the descendants).
#            self._deregister_entity(entity)
            
            # Insert any children of the current entity into the entity's old 
            # position in reverse order. Using reverse order allows the ordering of
            # the children to be preserved as they're re-inserted into the tree.
            child_index = entity.child_index
            for child_node in reversed(entity.children):
                child_node = self.move_node(entity.parent, child_node, child_index)
#        else:
#            # Deregister the current TaskList as well as all Task
#            # descendants.
#            self._deregister_entity(entity,
#                recursively_deregister=True)
        
        # Remove the node from the tree. 
        self.remove_node(entity)
            
    def reorder_task_down(self, *tasks):
        assert tasks
        
        # Reorder down all provided Tasks. If the Task is not eligible to be
        # moved down, this will result in a no-op.
        self.reorder_down(*tasks)      
            
    def reorder_task_up(self, *tasks):
        assert tasks
        
        # Reorder up all provided Tasks. If the Task is not eligible to be
        # moved up, this will result in a no-op.
        self.reorder_up(*tasks) 

    def _find_task_node(self, task):
        # Find the Task's node.
        task_node = self.find_node_for_entity(task)
        
        # Ensure that the target task is a Task. Otherwise, raise an error.        
        if not self._is_task_node(task_node):
            raise InvalidReorderOperationTargetError(task)
        
        return task_node
            
    def sort(self, current_node=None):
        if current_node is None:
            # Use the root node as the default starting point for a 
            # (recursive) sort.
            current_node = self
         
        child_nodes = current_node.children
        sorted_child_nodes = sorted(child_nodes)
        
        for i in range(0, len(sorted_child_nodes)):
            sorted_child_node = sorted_child_nodes[i]
            current_node.children[i] = sorted_child_node
            
            self.sort(sorted_child_node)

    def update_entity(self, entity):
        """As entities are "attached" to the TaskTree and therefore can be
        directly modified and have those changes reflected in the tree, this
        method simply updates the updated date timestamp on the entity.
        """
        entity.updated_date = datetime.now()

        return entity
        
    def update_task_status(self, task, new_status):
        # If the task is being switched from Completed to Needs Action, then
        # also update any parent Tasks to also have a status of Needs Action.
        if task.task_status == TaskStatus.COMPLETED and new_status == TaskStatus.NEEDS_ACTION:
            updating_task = task
            try:
                while True:
                    updating_task.task_status = new_status
                    
                    updating_task = updating_task.parent
            except AttributeError:
                # Reached a TaskList-type parent entity, stop updating. 
                pass
        
        # Update the status of any child Tasks.
        self._update_branch_task_status(task, new_status)
        
    def _update_branch_task_status(self, task, new_status):
        # Set the new status.
        task.task_status = new_status
        
        # Update the task.
        self.update_entity(task)
        
        # Push the updated status down to all child tasks.
        for child_task in task.children:
            self._update_branch_task_status(child_task, new_status)
#------------------------------------------------------------------------------ 

"""
TODO: This seems to replicate the coggrinder.entities.tree.NodeMoveTargetError.
Perhaps these two classes should either be combined, or share a common 
ancestor?
"""
class InvalidReorderOperationTargetError(Exception):
    def __init__(self, entity):
        Exception.__init__(self,
            "{entity_id} is not a valid target for a reorder operation.".format(entity_id=entity.entity_id))
#------------------------------------------------------------------------------

class TaskDataTestSupport(object):
    """Simple support class to make it more convenient to product mock TaskList
    and Task data for use in testing."""
    
    @classmethod
    def create_tasklists(cls, tasktree, tasklist_type=UpdatedDateIgnoredTestDataTaskList,
        siblings_count=3):
        
        tasklists = dict()
        
        for tl_i in range(0, siblings_count):
            tasklist_short_title = string.ascii_uppercase[tl_i]
            
            # Create all TaskLists without attachments to any TaskTree.
            tasklist = tasklist_type(tasktree, tasklist_short_title, is_persisted=True)
            tasklists[tasklist.entity_id] = tasklist
            
        return tasklists

    @classmethod
    def create_all_tasks(cls, tasklists, task_type=UpdatedDateIgnoredTestDataTask,
        siblings_count=3, tree_depth=3):

        all_tasks = dict()
        
        for tasklist in tasklists.values():
            tasklist_tasks = cls._create_task_branch(task_type,
                tasklist,
                siblings_count, tree_depth - 1, 1)
            
            all_tasks.update(tasklist_tasks)
            
        return all_tasks
    
    @classmethod
    def _create_task_branch(cls, task_type, parent,
        siblings_count, tree_depth, current_depth):
        
        tasks = dict()
        
        for t_i in range(0, siblings_count):            
            task_short_title = TestDataEntitySupport.combine_short_title_sections(
                    parent.entity_id.upper(), string.ascii_uppercase[t_i])

            # Create Tasks and attach them to the parent TaskList.
            task = task_type(parent, task_short_title, tasklist_id=parent.tasklist.entity_id)
            
            tasks[task.entity_id] = task
            
            if current_depth < tree_depth:
                child_tasks = cls._create_task_branch(task_type,
                    task,
                    siblings_count, tree_depth, current_depth + 1)
                
                tasks.update(child_tasks)
        
        return tasks

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
        
        tasktree = TaskTree()
        tasklists = cls.create_tasklists(tasktree, tasklist_type, siblings_count)
        all_tasks = cls.create_all_tasks(tasklists, task_type, siblings_count,
            tree_depth)
        
        return tasktree
        
    def find_entity(self, tasktree, entity_type, *short_title_sections):
        entity_id = TestDataEntitySupport.short_title_to_id(*short_title_sections)
        
        entity = tasktree.get_entity_for_id(entity_id)
        
        return entity
    
    def find_tasklist(self, tasktree, *short_title_sections):
        return self.find_entity(tasktree, TestDataTaskList,
            *short_title_sections)
    
    def find_task(self, tasktree, *short_title_sections):
        return self.find_entity(tasktree, TestDataTask,
            *short_title_sections)
        
    def branch_str(self, tasktree, entity):
        entity_node = tasktree.find_node_for_entity(entity)
        branch_debug_output = tasktree._create_branch_str(node=entity_node)
        
        return branch_debug_output
    
    def tasklist_branch_str(self, tasktree, *short_title_sections):
        tasklist = self.find_tasklist(tasktree, *short_title_sections)
        return self.branch_str(tasktree, tasklist)        
#------------------------------------------------------------------------------

@unittest.skip("Ordering broken with Task refactor.")
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
        expected_task_acc = TestDataTask("A-C-C",
            tasklist_id=expected_tasklist_a.entity_id,
            parent_id="a-c",
            previous_task_id=TestDataEntitySupport.short_title_to_id(*list('acb')))
            
        ### Act ###
        tasktree = TaskDataTestSupport.create_dynamic_tasktree(
            tasklist_type=TestDataTaskList, task_type=TestDataTask,
            siblings_count=3, tree_depth=3)
        
        actual_tasklist_a = tasktree.get_entity_for_id("a")
        actual_task_acc = tasktree.get_entity_for_id("a-c-c")
        
        ### Assert ###
        self.assertEqual(expected_tasklist_a, actual_tasklist_a)
        self.assertEqual(expected_task_acc, actual_task_acc)
#------------------------------------------------------------------------------ 
class PopulatedTaskTreeTestSupport(TaskDataTestSupport, ManagedFixturesTestSupport):
    def setUp(self):
        """Establish test fixtures common to all tests within this setup.

        - Create (identical) expected/baseline and working versions of 
        populated TaskTrees.
        """
        self.baseline_tasktree = TaskDataTestSupport.create_dynamic_tasktree()
        self.working_tasktree = TaskDataTestSupport.create_dynamic_tasktree()

        self._register_fixtures(self.baseline_tasktree, self.working_tasktree)        
#------------------------------------------------------------------------------

class TaskTreeTest(unittest.TestCase):
    """
    If there are going to be tests for this class, they need to be ones that
    stress the unique features of a TaskTree, rather than just duplicating
    those already being performed on Tree.
    """
    def test_descendants_populated(self):
        """Test that the descendants property returns only task data entities
        within the TaskTree, and specifically does not include the default 
        root node.
        
        Arrange:
            - Create a TaskTree New with no default data.
            - Populate TaskTree New with TaskList A, Tasks AA, AB.
            - Create expected descendants collection.
        Act:
            - Get the actual descendants collection of TaskTree New.
        Assert:
            - That expected and actual descendants collections are identical.
        """
        ### Arrange ###
        tasktree_new = TaskTree()
        tasklist_a = TaskList(tasktree_new, title="A")
        task_aa = Task(tasklist_a, title="A-A")
        task_ab = Task(tasklist_a, title="A-B")
        
        expected_descendants = [tasklist_a, task_aa, task_ab]
        
        ### Act ###
        actual_descendants = tasktree_new.descendants
        
        ### Assert ###
        self.assertEqual(expected_descendants, actual_descendants)

    def test_entity_ids_empty(self):
        """Test the entity_ids property of TaskTree, ensuring that it
        accurately reflects the IDs of the entities held by an empty
        TaskTree.

        Act:
            - Create a new TaskTree without providing any default data.
        Assert:
            - That TaskTree.entity_ids reports no entities (length of 0).
        """
        ### Act ###
        empty_tasktree = TaskTree()

        ### Assert ###
        self.assertEqual(set(), empty_tasktree.entity_ids)

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
        
    def test_init_arg_tree_creation_task_data(self):
        """Test the creation of a TaskTree task data provided through the 
        initialization arguments.
        
        This test focuses on the task_data init argument.
        
        The completed TaskTree should have the following architecture:
        - tl-a
            - t-a-a
        
        Arrange:
            - Manually build the expected TaskTree, populated with 
            TaskList A and Task A-A.
            - Create the task_data collection.
        Act:
            - Build actual TaskTree by providing task data during 
            initialization.
        Assert:
            - That the expected and actual TaskTrees are identical.
        """
        ### Arrange ###        
        expected_tasklist_a = TestDataTaskList(None, 'a')
        actual_tasklist_a = expected_tasklist_a.clean_clone()
        
        expected_tasklist_b = TestDataTaskList(None, 'B')
        actual_tasklist_b = expected_tasklist_b.clean_clone()
        
        expected_task_aa = TestDataTask(None, *'aa', tasklist_id=expected_tasklist_a.entity_id)
        actual_task_aa = copy.deepcopy(expected_task_aa)
        
        expected_tasklist_a.add_child(expected_task_aa)
        
        expected_tasktree = TaskTree()
        expected_tasktree.children.append(expected_tasklist_a)
        expected_tasklist_a.parent = expected_tasktree
        expected_tasktree.children.append(expected_tasklist_b)
        expected_tasklist_b.parent = expected_tasktree
        
        task_data = TestDataEntitySupport.create_task_data_dict(
            actual_tasklist_b, actual_tasklist_a, actual_task_aa)
        
        ### Act ###
        actual_tasktree = TaskTree(task_data=task_data)
        
        ### Assert ###
        self.assertEqual(expected_tasktree, actual_tasktree)

    def test_task_data_property(self):
        """Test the accuracy of the TaskTree .task_data property.
        
        The .task_data property should accurately reflect all entities 
        currently held within the TaskTree.
        
        Arrange:
            - Create the working TaskTree.
            - Create expected entities TaskList A, Task B; adding them to the 
            TaskTree during initialization.
            - Create expected task data collection (dict).
        Act:
            - Get TaskTree.task_data
        Assert:
            - Expected and actual task data collections are identical.
        """
        ### Arrange ###
        tasktree = TaskTree()
        expected_tl_a = TestDataTaskList(tasktree, 'A')
        expected_t_b = TestDataTask(expected_tl_a, 'B')
        expected_task_data = {expected_tl_a.entity_id:expected_tl_a,
            expected_t_b.entity_id:expected_t_b}
        
        ### Act ###        
        actual_task_data = tasktree.task_data
        
        ### Assert ###
        self.assertEqual(expected_task_data, actual_task_data)
        
    @unittest.skip("Disabling due to refactoring.")
    def test_all_tasks_property(self):
        """Test the accuracy of the TaskTree all_tasks property.
        
        The all_tasks property should accurately reflect all Task-type 
        entities currently held within the TaskTree. The Tasks will be grouped
        by parent TaskList, with the return collection defining a dictionary
        of TaskList ID keys pointing to Task sub-dictionaries. Each Task 
        sub-dictionary will contain Task ID keys pointing to Task instances. 
        
        Arrange:
            - Create expected entities TaskList A, Task B.
            - Create expected all_tasks dict.
        Act:
            - Create TaskTree.
            - Add clones of expected entities to TaskTree.
            - Get TaskTree.all_tasks
        Assert:
            - Expected and actual all_task collections are identical.
        """
        ### Arrange ###
        expected_tl_a = TestDataTaskList('A')
        expected_t_b = TestDataTask('B', tasklist_id=expected_tl_a.entity_id)
        tasks = {expected_t_b.entity_id: expected_t_b}
        expected_all_tasks = {expected_tl_a.entity_id:tasks}
        
        ### Act ###
        tasktree = TaskTree()
        tasktree.add_entity(copy.deepcopy(expected_tl_a))
        tasktree.add_entity(copy.deepcopy(expected_t_b))
        
        actual_all_tasks = tasktree.all_tasks
        
        ### Assert ###
        self.assertEqual(expected_all_tasks, actual_all_tasks)
        
    def test_children_empty(self):
        """Test that an empty TaskTree has no children.
        
        Act:
            - Create empty TaskTree.
        Assert:
            - That the TaskTree task_data reflects no children (has no
            task data).
        """        
        ### Act ###
        empty_tasktree = TaskTree()
        
        ### Assert ###
        self.assertEquals(0, len(empty_tasktree.task_data))
#------------------------------------------------------------------------------ 

class TaskTreeSortTest(unittest.TestCase):                
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
        expected_tasklist_empty = TestDataTaskList(expected_tasktree, "")
        expected_tasklist_bar = TestDataTaskList(expected_tasktree, "bar")
        expected_tasklist_baz = TestDataTaskList(expected_tasktree, "Baz")
        expected_tasklist_foo = TestDataTaskList(expected_tasktree, "Foo")
        
        actual_task_data = TestDataEntitySupport.create_task_data_dict(
            expected_tasklist_foo.clean_clone(),
            expected_tasklist_bar.clean_clone(),
            expected_tasklist_empty.clean_clone(),
            expected_tasklist_baz.clean_clone())
        
        ### Act ###
        actual_tasktree = TaskTree(task_data=actual_task_data)
        
        ### Assert ###
        self.assertEqual(expected_tasktree, actual_tasktree)

    @unittest.skip("Ordering broken with Task refactor.")
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
        expected_tasklist_car.title = TestDataEntitySupport.create_full_title(TestDataTaskList, "Car")
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
            - Create parent TaskList A.
            - Create Tasks AA, AB, AC.
            - Create input_tasklists data set out of the new TaskLists.
        Act:
            - Create a new TaskTree using the input_tasklists data set.
        Assert:
            - That the TaskLists are in this order, from highest to lowest:
                - aa
                - ab
                - ac
        """
        ### Arrange ###
        expected_tasktree = TaskTree()        
        expected_tasklist_a = TestDataTaskList(expected_tasktree, "A")
        expected_task_first = TestDataTask(expected_tasklist_a, 'first',
            tasklist_id=expected_tasklist_a.entity_id)
        expected_task_second = TestDataTask(expected_tasklist_a, 'second',
            tasklist_id=expected_tasklist_a.entity_id)
        expected_task_last = TestDataTask(expected_tasklist_a, 'last',
            tasklist_id=expected_tasklist_a.entity_id)
        
        actual_task_data = TestDataEntitySupport.create_task_data_dict(
            expected_tasklist_a, expected_task_last, expected_task_first,
            expected_task_second)
        
        ### Act ###
        actual_tasktree = TaskTree(task_data=actual_task_data)
        
        ### Assert ###
        self.assertEqual(expected_tasktree, actual_tasktree)
#------------------------------------------------------------------------------ 

class PopulatedTaskTreeTest(PopulatedTaskTreeTestSupport, unittest.TestCase):
    @skip("Test covers use case that is now possibly deprecated.")
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
        tasklist_a = self.baseline_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id("a"))
        task_foo = TestDataTask("Foo", tasklist_id=tasklist_a.entity_id)
        expected_task_foo = copy.deepcopy(task_foo)
        expected_task_foo.previous_task_id = TestDataEntitySupport.short_title_to_id(*list("ac"))
        self.baseline_tasktree.append(self.baseline_tasktree.get_node((0, 0)),
            expected_task_foo)

        ### Act ###
        self.working_tasktree.add_entity(task_foo)

        ### Assert ###
        self.assertEqual(self.baseline_tasktree, self.working_tasktree)
        with self.assertRaises(EntityOverwriteError):
            self.working_tasktree.add_entity(task_foo)

    @skip("Test covers use case that is now possibly deprecated.")
    def test_add_child_task(self):
        """Test that adding to the TaskTree a new Task that is the child of an
        existing Task inserts the new Task in the correct position in the tree.

        This new task should be inserted directly below the parent Task.

        Arrange:
            - Create new Task Foo for TaskList A.
            - Clone Task Foo into Task Foo Expected.
            - Append Task Foo Expected to the expected TaskTree, directly under
            Task A-B.
        Act:
            - Add Task Foo to the TaskTree under Task A-B.
        Assert:
            - That the expected and actual TaskTrees are identical.
        """
        ### Arrange ###
        tasklist_a = self.baseline_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id("a"))
        task_ab = self.baseline_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*list("ab")))
        
        task_foo = TestDataTask("Foo",
            tasklist_id=tasklist_a.entity_id,
            parent_id=task_ab.entity_id)
        
        expected_task_foo = copy.deepcopy(task_foo)
        expected_task_foo.previous_task_id = TestDataEntitySupport.short_title_to_id(*list("abc"))
         
        self.baseline_tasktree.append(
            self.baseline_tasktree.find_node_for_entity(task_ab),
            expected_task_foo)

        ### Act ###
        self.working_tasktree.add_entity(task_foo)

        ### Assert ###
        self.assertEqual(self.baseline_tasktree, self.working_tasktree)

    @skip("Test covers use case that is now possibly deprecated.")
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
        self.baseline_tasktree.append(
            self.baseline_tasktree.get_node(self.baseline_tasktree.ROOT_PATH),
            expected_tasklist_foo)

        ### Act ###
        self.working_tasktree.add_entity(tasklist_foo)

        ### Assert ###
        self.assertEqual(self.baseline_tasktree, self.working_tasktree)

    @skip("Test covers use case that is now possibly deprecated.")
    def test_all_entity_ids(self):
        """Test the entity_ids property of TaskTree, ensuring that it
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
            TaskTree.entity_ids property.
        """
        ### Arrange ###
        self.working_tasktree.clear()
        
        tasklist_a = TestDataTaskList("A")
        self.working_tasktree.add_entity(tasklist_a)
        
        task_b = TestDataTask("B", tasklist_id=tasklist_a.entity_id)        
        self.working_tasktree.add_entity(task_b)
        
        expected_entity_ids = set([tasklist_a.entity_id, task_b.entity_id])

        ### Assert ###
        self.assertEqual(expected_entity_ids, self.working_tasktree.entity_ids)

    @skip("Test covers use case that is now possibly deprecated.")
    def test_all_entity_ids_updated(self):
        """Test the entity_ids property of TaskTree, ensuring that it
        is maintained as the TaskTree changes.

        Arrange:
            - Clear the TaskTree under test.
            - Create task data TaskList A and Task B, and add them to the 
            TaskTree.
            - Create a set of expected entity IDs reflecting the task data 
            added to TaskTree.
        Assert:
            - That the expected IDs set is equal to the test fixture's
            TaskTree.entity_ids property.
        """
        ### Arrange ###
        tasktree = TaskTree()
        
        tasklist_a = TestDataTaskList("a")
        tasktree.add_entity(tasklist_a)
        task_aa = TestDataTask("a-a", tasklist_id=tasklist_a.entity_id)        
        tasktree.add_entity(task_aa)
        task_aaa = TestDataTask("a-a-a", tasklist_id=tasklist_a.entity_id, parent_id=task_aa.entity_id)        
        tasktree.add_entity(task_aaa)
        
        tasklist_b = TestDataTaskList("b")
        tasktree.add_entity(tasklist_b)
        task_ba = TestDataTask("b-a", tasklist_id=tasklist_b.entity_id)        
        tasktree.add_entity(task_ba)
        
        expected_entity_ids = set([tasklist_b.entity_id, task_ba.entity_id])
        
        ### Act ###
        tasktree.remove_entity(tasklist_a)

        ### Assert ###
        self.assertEqual(expected_entity_ids, tasktree.entity_ids)

    @skip("Test covers use case that is now possibly deprecated.")
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
        """
        TODO: This is not a very good test. Shouldn't it involve setting up
        a new TaskTree, rather than relying on the test fixture?
        
        If this test stands, it needs to be fixed somewhat because occasionally 
        it fails. I'm assuming that because the failures are intermittent, 
        they are probably due to updated date property comparisons.
        """
        ### Arrange ###        
        expected_tasklist_a = self.baseline_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id("a"))
        expected_task_ab = self.baseline_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*list("ab")))
        expected_task_abc = self.baseline_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*list("abc")))

        ### Act ###
        actual_tasklist_a = self.working_tasktree.get((0,))
        actual_task_ab = self.working_tasktree.get((0, 1))
        actual_task_abc = self.working_tasktree.get((0, 1, 2))

        ### Assert ###
        self.assertEqual(expected_tasklist_a, actual_tasklist_a)
        self.assertEqual(expected_task_ab, actual_task_ab)
        self.assertEqual(expected_task_abc, actual_task_abc)

    @skip("Test covers use case that is now possibly deprecated.")
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
        self.working_tasktree.clear()
        
        tasklist_a = TestDataTaskList("A")
        self.working_tasktree.add_entity(tasklist_a)
        
        task_b = TestDataTask("B", tasklist_id=tasklist_a.entity_id)        
        self.working_tasktree.add_entity(task_b)
        
        task_c = TestDataTask("C", tasklist_id=tasklist_a.entity_id)        
        self.working_tasktree.add_entity(task_c)
        
        expected_tasks = {task_b.entity_id:task_b, task_c.entity_id:task_c}

        ### Act ###
        actual_tasks = self.working_tasktree.get_tasks_for_tasklist(tasklist_a)

        ### Assert ###
        self.assertEqual(expected_tasks, actual_tasks)

    @skip("Test covers use case that is now possibly deprecated.")
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
        self.working_tasktree.clear()
        
        tasklist_a = TestDataTaskList("A")
        self.working_tasktree.add_entity(tasklist_a)
        
        tasklist_b = TestDataTaskList("B")
        self.working_tasktree.add_entity(tasklist_b)
        
        tasklist_c = TestDataTaskList("C")
        self.working_tasktree.add_entity(tasklist_c)
        
        expected_tasklists = {tasklist_a.entity_id:tasklist_a,
            tasklist_b.entity_id:tasklist_b,
            tasklist_c.entity_id:tasklist_c}

        ### Act ###
        actual_tasklists = self.working_tasktree.tasklists

        ### Assert ###
        self.assertEqual(expected_tasklists, actual_tasklists)

    @skip("Test covers use case that is now possibly deprecated.")
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
        expected_tasklist_a = self.baseline_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id("A"))

        ### Act ###
        actual_tasklist_a = self.working_tasktree.get_entity_for_id(expected_tasklist_a.entity_id)

        ### Assert ###
        now_timestamp = datetime.now()
        expected_tasklist_a.updated_date = actual_tasklist_a.updated_date = now_timestamp
        self.assertEqual(expected_tasklist_a, actual_tasklist_a)

    @skip("Test covers use case that is now possibly deprecated.")
    def test_get_entity_task(self):
        """Test that searching the TaskTree for an entity ID belonging to a
        Task will return that Task instance.

        Act:
            Search for a Task with the entity ID of the expected Task C.
        Assert:
            That the found Task is equal to the expected Task.
        """
        ### Arrange ###        
        expected_tasklist_a = self.baseline_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id("A"))
        expected_task_c = self.baseline_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id("C"))

        ### Act ###
        actual_task_c = self.working_tasktree.get_entity_for_id(expected_task_c.entity_id)

        ### Assert ###
        self.assertEqual(expected_task_c, actual_task_c)

    @skip("Test covers use case that is now possibly deprecated.")
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
            self.working_tasktree.get_entity_for_id(expected_bogus_id)

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
            - That child Tasks AA, AB cannot be found via get_entity_for_id.
        """
        ### Arrange ###        
        expected_tasklist_a = self.working_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id("A"))
        expected_task_aa = self.working_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*list("aa")))
        expected_task_ab = self.working_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*list("ab")))
        
        ### Act ###
        self.working_tasktree.remove_entity(expected_tasklist_a)

        ### Assert ###
        with self.assertRaises(UnregisteredEntityError):
            self.working_tasktree.get_entity_for_id(expected_tasklist_a.entity_id)
            
        with self.assertRaises(UnregisteredEntityError):
            self.working_tasktree.get_entity_for_id(expected_task_aa.entity_id)
            
        with self.assertRaises(UnregisteredEntityError):
            self.working_tasktree.get_entity_for_id(expected_task_ab.entity_id)

    @skip("Test covers use case that is now possibly deprecated.")
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
        expected_task_ac = self.baseline_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*list("ac")))
        
        ### Act ###
        self.working_tasktree.remove_entity(expected_task_ac)

        ### Assert ###
        with self.assertRaises(UnregisteredEntityError):
            self.working_tasktree.get_entity_for_id(expected_task_ac.entity_id)
            
        with self.assertRaises(UnregisteredEntityError):
            self.working_tasktree.remove_entity(expected_task_ac)
            
        self.working_tasktree.add_entity(expected_task_ac)
        actual_task_d = self.working_tasktree.get_entity_for_id(expected_task_ac.entity_id)
        self.assertEqual(expected_task_ac, actual_task_d)

    @skip("Test covers use case that is now possibly deprecated.")
    def test_remove_entity_parent_task(self):
        """Test that removing a parent Task from the TaskTree eliminates the 
        Task while preserving the Task's descendant Tasks.
        
        Any direct child Tasks of the deleted Task should move up to take the
        position of the deleted Task under the deleted Task's parent.

        Arrange:
            - Find expected Task AB (parent of Tasks ABA, ABC).
        Act:
            - Delete Task AB.
        Assert:
            - That Task AB cannot be found via TaskTree.get_entity_for_id.
            - That Tasks ABA, AC can be found via TaskTree.get_entity_for_id.
            - That the following Tasks are directly below TaskList A are: AA, 
            ABA, AC.
        """
        ### Arrange ###        
        expected_task_ab = self.working_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*"ab"))
        
        expected_task_aa = copy.deepcopy(
            self.working_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*"aa")))
        
        expected_task_aba = copy.deepcopy(
            self.working_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*"aba")))
        expected_task_aba.parent_id = None
        expected_task_aba.previous_task_id = expected_task_aa.entity_id
        
        expected_task_ac = copy.deepcopy(
            self.working_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*"ac")))
        expected_task_ac.previous_task_id = TestDataEntitySupport.short_title_to_id(*list("abc"))
        
        ### Act ###
        self.working_tasktree.remove_entity(expected_task_ab)

        ### Assert ###
        with self.assertRaises(UnregisteredEntityError):
            self.working_tasktree.get_entity_for_id(expected_task_ab.entity_id)
        
        actual_task_aba = self.working_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*list("aba")))
        self.assertEqual(expected_task_aba, actual_task_aba)
        
        actual_task_ac = self.working_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*list("ac")))
        self.assertEqual(expected_task_ac, actual_task_ac)

    @skip("Test covers use case that is now possibly deprecated.")        
    def test_remove_task_great_grandchild_survives(self):
        """Test that deleting Tasks from a Task hierarchy chain only deletes 
        the targeted Tasks, and no untargeted descendants. 
        
        For instance, in the simple tree:
        -tl-a
            -t-b
                -t-c
                    -t-d
                        -t-e
        
        Deleting Tasks c, d should produce this result (t-e 
        becomes child of great grandparent t-b):
        -tl-a
            -t-b
                -t-e
        
        Arrange:
            - Create actual/initial TaskTree.
            - Create expected TaskTree by cloning initial TaskTree.
            - Update expected TaskTree to mirror final expected tree 
            architecture.
        Act:
            - Delete Tasks c, d from actual TaskTree.
        Assert:
            - That expected and actual TaskTrees are identical.
        """
        ### Arrange ###
        tl_a = TestDataTaskList('a')
        t_b = TestDataTask('b', tasklist_id=tl_a.entity_id)
        t_c = TestDataTask('c', tasklist_id=tl_a.entity_id, parent_id=t_b.entity_id)
        t_d = TestDataTask('d', tasklist_id=tl_a.entity_id, parent_id=t_c.entity_id)
        t_e = TestDataTask('e', tasklist_id=tl_a.entity_id, parent_id=t_d.entity_id)
        
        expected_t_b = copy.deepcopy(t_b)
        expected_t_e = copy.deepcopy(t_e)
        expected_t_e.parent_id = expected_t_b.entity_id
        
        expected_tasktree = TaskTree()
        expected_tasktree.add_entity(copy.deepcopy(tl_a))  
        expected_tasktree.add_entity(expected_t_b)
        expected_tasktree.add_entity(expected_t_e)
        
        actual_tasktree = TaskTree()
        actual_tasktree.add_entity(tl_a)
        actual_tasktree.add_entity(t_b)
        actual_tasktree.add_entity(t_c)
        actual_tasktree.add_entity(t_d)
        actual_tasktree.add_entity(t_e)
                
        ### Act ###        
        actual_tasktree.remove_entity(t_c)
        actual_tasktree.remove_entity(t_d)
        
        ### Assert ###
        self.assertEqual(expected_tasktree, actual_tasktree)

    @skip("Test covers use case that is now possibly deprecated.")
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
        expected_tasklist_a = self.baseline_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id("A"))
        expected_entity_node = self.working_tasktree.get_node((0, 0))

        ### Act ###
        actual_entity_node = self.working_tasktree.find_node_for_entity(
            expected_tasklist_a)

        ### Assert ###
        self.assertEqual(expected_entity_node, actual_entity_node)

    @skip("Test covers use case that is now possibly deprecated.")
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
            self.baseline_tasktree.get_entity_for_id("c"))
        expected_task_c.title = "updated"

        ### Act ###
        preop_task_c = self.working_tasktree.get_entity_for_id(expected_task_c.entity_id)
        self.working_tasktree.update_entity(expected_task_c)
        postop_task_c = self.working_tasktree.get_entity_for_id(expected_task_c.entity_id)

        ### Assert ###
        self.assertNotEqual(expected_task_c, preop_task_c)
        self.assertEqual(expected_task_c, postop_task_c)
#------------------------------------------------------------------------------ 

class TaskTreeReorderTest(PopulatedTaskTreeTestSupport, unittest.TestCase):        
    def test_reorder_up_task(self):
        """Test that the reorder up operation properly repositions Tasks
        among their sibling group.
                
        Arrange:
            - Find expected Tasks a-a-b, a-a-c.
            - Create a new list of expected children for Task a-a.
        Act:
            - Find actual Tasks a-a-b, a-a-c and reorder them up.
        Assert:
            - Tasks a-a-b, a-a-c are located at the expected paths (0,0,0) 
            and (0,0,1).
            - Task a-a has the expected children, in the expected order.
        """
        ### Arrange ###
        actual_task_aab = self.find_task(self.working_tasktree, *'aab')
        actual_task_aac = self.find_task(self.working_tasktree, *'aac')
        
        actual_task_aa = self.find_task(self.working_tasktree, *'aa')
        
        expected_task_aa_children = [
            self.find_task(self.working_tasktree, *'aab'),
            self.find_task(self.working_tasktree, *'aac'),
            self.find_task(self.working_tasktree, *'aaa')]
        
        ### Act ###
        self.working_tasktree.reorder_task_up(actual_task_aab, actual_task_aac)
        
        ### Assert ###
        self.assertEqual((0, 0, 0),
            self.find_task(self.working_tasktree, *'aab').path)
        self.assertEqual((0, 0, 1),
            self.find_task(self.working_tasktree, *'aac').path)
        
        self.assertEqual(expected_task_aa_children, actual_task_aa.children)
        
    def test_reorder_down_task(self):
        """Test that the reorder down operation properly repositions Tasks
        among their sibling group.
        
        Arrange:
            - Find expected Tasks a-a-a, a-a-b.
            - Create a new list of expected children for Task a-a.
        Act:
            - Find actual Tasks a-a-a, a-a-b and reorder them down.
        Assert:
            - Tasks a..c from working TaskTree are identical to expected
            Tasks.  
        """
        ### Arrange ###
        actual_task_aaa = self.find_task(self.working_tasktree, *'aaa')
        actual_task_aab = self.find_task(self.working_tasktree, *'aab')
        
        actual_task_aa = self.find_task(self.working_tasktree, *'aa')
        
        expected_task_aa_children = [
            self.find_task(self.working_tasktree, *'aac'),
            self.find_task(self.working_tasktree, *'aaa'),
            self.find_task(self.working_tasktree, *'aab')]
        
        ### Act ###
        self.working_tasktree.reorder_task_down(actual_task_aaa, actual_task_aab)
        
        ### Assert ###
        self.assertEqual((0, 0, 1),
            self.find_task(self.working_tasktree, *'aaa').path)
        self.assertEqual((0, 0, 2),
            self.find_task(self.working_tasktree, *'aab').path)
        
        self.assertEqual(expected_task_aa_children, actual_task_aa.children)
        
    def test_promote_task_single(self):
        """Test that the promote operation properly moves the targeted Task 
        to before the sibling of its parent under its pre-promotion 
        grandparent.
        
        Arrange:
            - Find expected Tasks a-a, a-a-a, TaskList a.
            - Create new lists of expected children for TaskList a and Task 
            a-a.
        Act:
            - Find actual Task a-a-a and promote it.
        Assert:
            - Task a-a-a is located at the expected path (0,1).
            - TaskList a and Task a-a have the expected children, in the 
            expected order.
        """
        ### Arrange ###
        actual_task_aaa = self.find_task(self.working_tasktree, *'aaa')
        actual_task_aa = self.find_task(self.working_tasktree, *'aa')
        actual_tasklist_a = self.find_tasklist(self.working_tasktree, 'a')
        
        expected_tasklist_a_children = [
            self.find_task(self.working_tasktree, *'aa'),
            self.find_task(self.working_tasktree, *'aaa'),
            self.find_task(self.working_tasktree, *'ab'),
            self.find_task(self.working_tasktree, *'ac')]
        expected_task_aa_children = [
            self.find_task(self.working_tasktree, *'aab'),
            self.find_task(self.working_tasktree, *'aac')]
        
        ### Act ###
        self.working_tasktree.promote(actual_task_aaa)
        
        ### Assert ###
        self.assertEqual((0, 1),
            self.find_task(self.working_tasktree, *'aaa').path)
        
        self.assertEqual(expected_tasklist_a_children, actual_tasklist_a.children)
        self.assertEqual(expected_task_aa_children, actual_task_aa.children)
    
    def test_promote_task_multiple(self):
        """Test that the promote operation properly moves the targeted set of
        Tasks.
                
        Arrange:
            - Find expected Tasks a-a-a, a-a-c, a-a, and TaskList a.
            - Create new lists of expected children for TaskList a and Task 
            a-a.
        Act:
            - Find actual Tasks a-a-a, a-a-c and promote them.
        Assert:
            - Tasks a-a-b, a-a-c are located at the expected paths (0,1) 
            and (0,2).
            - Task a-a and TaskList a have the expected children, in the 
            expected order.
        """
        ### Arrange ###
        actual_task_aaa = self.find_task(self.working_tasktree, *'aaa')
        actual_task_aac = self.find_task(self.working_tasktree, *'aac')    
        actual_task_aa = self.find_task(self.working_tasktree, *'aa')
        actual_tasklist_a = self.find_tasklist(self.working_tasktree, 'a')    
        
        expected_tasklist_a_children = [
            self.find_task(self.working_tasktree, *'aa'),
            self.find_task(self.working_tasktree, *'aaa'),
            self.find_task(self.working_tasktree, *'aac'),
            self.find_task(self.working_tasktree, *'ab'),
            self.find_task(self.working_tasktree, *'ac')]
        expected_task_aa_children = [
            self.find_task(self.working_tasktree, *'aab')]
                        
        ### Act ###
        self.working_tasktree.promote(actual_task_aaa, actual_task_aac)
        
        ### Assert ###
        self.assertEqual((0, 1),
            self.find_task(self.working_tasktree, *'aaa').path)
        self.assertEqual((0, 2),
            self.find_task(self.working_tasktree, *'aac').path)
        
        self.assertEqual(expected_tasklist_a_children, actual_tasklist_a.children)
        self.assertEqual(expected_task_aa_children, actual_task_aa.children)
    
    def test_demote_task_single(self):
        """Test that the demote operation properly moves the targeted Task to
        become the last (lowest ordered) direct child of its previous 
        preceeding sibling.
        
        Arrange:
            - Find expected Tasks a-a, a-b, TaskList a.
            - Create new lists of expected children for TaskList a and Task 
            a-a.
        Act:
            - Find actual Task a-b and demote it.
        Assert:
            - Task a-b is located at the expected path (0,0,3).
            - TaskList a and Task a-a have the expected children, in the 
            expected order.
        """
        ### Arrange ###
        actual_task_ab = self.find_task(self.working_tasktree, *'ab')
        actual_task_aa = self.find_task(self.working_tasktree, *'aa')
        actual_tasklist_a = self.find_tasklist(self.working_tasktree, 'a')
        
        expected_tasklist_a_children = [
            self.find_task(self.working_tasktree, *'aa'),
            self.find_task(self.working_tasktree, *'ac')]
        expected_task_aa_children = [
            self.find_task(self.working_tasktree, *'aaa'),
            self.find_task(self.working_tasktree, *'aab'),
            self.find_task(self.working_tasktree, *'aac'),
            self.find_task(self.working_tasktree, *'ab')]
        
        ### Act ###
        self.working_tasktree.demote(actual_task_ab)
        
        ### Assert ###
        self.assertEqual((0, 0, 3),
            self.find_task(self.working_tasktree, *'ab').path)
        
        self.assertEqual(expected_tasklist_a_children, actual_tasklist_a.children)
        self.assertEqual(expected_task_aa_children, actual_task_aa.children)
    
    """
    TODO: This test still randomly fails. Frustratingly, every 
    debug/step-through attempt has resulted in a successful test outcome.
    """
    def test_demote_task_multiple(self):
        """Test that the demote operation properly moves the targeted set of
        Tasks.
                
        Arrange:
            - Find expected Tasks a-a-b, a-a-c, a-a, a-a-a.
            - Create new lists of expected children for Tasks a-a and a-a-a.
        Act:
            - Find actual Tasks a-a-b, a-a-c and demote them.
        Assert:
            - Tasks a-a-b, a-a-c are located at the expected paths (0,0,0,0) 
            and (0,0,0,1).
            - Tasks a-a and Task a-a-a have the expected children, in the 
            expected order.
        """
        ### Arrange ###
        actual_task_aab = self.find_task(self.working_tasktree, *'aab')
        actual_task_aac = self.find_task(self.working_tasktree, *'aac')
        
        actual_task_aa = self.find_task(self.working_tasktree, *'aa')
        actual_task_aaa = self.find_task(self.working_tasktree, *'aaa')
        
        expected_task_aa_children = [
            self.find_task(self.working_tasktree, *'aaa')]
        expected_task_aaa_children = [
            self.find_task(self.working_tasktree, *'aab'),
            self.find_task(self.working_tasktree, *'aac')]
        
        ### Act ###
        self.working_tasktree.demote(actual_task_aab, actual_task_aac)
        
        ### Assert ###
        self.assertEqual((0, 0, 0, 0),
            self.find_task(self.working_tasktree, *'aab').path)
        self.assertEqual((0, 0, 0, 1),
            self.find_task(self.working_tasktree, *'aac').path)
        
        self.assertEqual(expected_task_aa_children, actual_task_aa.children)
        self.assertEqual(expected_task_aaa_children, actual_task_aaa.children)
#------------------------------------------------------------------------------
s#------------------------------------------------------------------------------ 
        
class TaskTreeComparator(object):
    @classmethod
    def find_added_ids(cls, baseline_tree, altered_tree):
        # Find all entity IDs that are present in the altered tree but not in
        # the baseline tree.
        added_ids = altered_tree.entity_ids - baseline_tree.entity_ids
        
        return added_ids
    
    @classmethod
    def find_deleted_ids(cls, baseline_tree, altered_tree):
        # Find all entity IDs that were present in the baseline tree but are
        # missing in the altered tree.
        deleted_ids = baseline_tree.entity_ids - altered_tree.entity_ids
        
        return deleted_ids
    
    @classmethod
    def find_updated_ids(cls, baseline_tree, altered_tree):
        # Begin with a list of all IDs that are in both Trees.
        common_ids = baseline_tree.entity_ids & altered_tree.entity_ids
        
        updated_ids = set()
        for entity_id in common_ids:
            # For each common entity ID, pull the entity from both trees and
            # compare if they are equal.
            baseline_entity = baseline_tree.get_entity_for_id(entity_id)
            altered_entity = altered_tree.get_entity_for_id(entity_id)
            
            updated_ignored_props = baseline_entity._get_comparable_properties()
            updated_ignored_props.remove('updated_date')
            
            if not DeclaredPropertiesComparable.compare(
                baseline_entity.treeless_value, altered_entity.treeless_value, updated_ignored_props):
                updated_ids.add(entity_id)
                
        return updated_ids
#------------------------------------------------------------------------------ 

class TaskTreeComparatorTest(PopulatedTaskTreeTestSupport, unittest.TestCase):
    def setUp(self):
        PopulatedTaskTreeTestSupport.setUp(self)

        # Create the TaskTreeComparator that will be under test.
        self.comparator = TaskTreeComparator()

        self._register_fixtures(self.comparator)
    
    def test_find_added(self):
        """Test that the TaskTreeComparator can identify any new entities added
        to a TaskTree.

        Four new entities will be added, as detailed below in the Arrange 
        section.

        Arrange:
            - Add a TaskList D to current TaskTree.
            - Add Tasks D-A-A, D-A-B to TaskList D in current TaskTree.
            - Add Task G to TaskList A, Task A-A in current TaskTree.
            - Create a new set representing the IDs of the new entities.
        Act:
            - Use TaskTreeComparator.find_added to locate all task data that
            was added during the Arrange phase.
        Assert:
            - That the expected and actual sets of added entity IDs are
            identical.
        """
        ### Arrange ###
        tasklist_a = self.working_tasktree.get_entity_for_id("a")
        task_aa = self.working_tasktree.get_entity_for_id(TestDataEntitySupport.short_title_to_id(*list("aa")))
        task_g = TestDataTask(task_aa, "g")
        
        tasklist_d = TestDataTaskList(self.working_tasktree, "d")
        task_daa = TestDataTask(tasklist_d, *list("daa"))
        task_dab = TestDataTask(tasklist_d, *list("dab"))
                        
        expected_added_ids = set([tasklist_d.entity_id, task_g.entity_id,
            task_daa.entity_id, task_dab.entity_id])

        ### Act ###
        actual_added_ids = self.comparator.find_added_ids(self.baseline_tasktree,
            self.working_tasktree)

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
        actual_added_ids = self.comparator.find_added_ids(self.baseline_tasktree,
            self.working_tasktree)

        ### Assert ###
        self.assertEqual(set(), actual_added_ids)

    def test_find_deleted_tasks(self):
        """Test that the TaskTreeComparator can identify any entities that 
        were removed from a TaskTree.

        Arrange:
            - Remove Tasks A-A,A-C from the TaskTree.
            - Create a new set representing the IDs of the removed entities.
        Act:
            - Use TaskTreeComparator.find_removed to locate all task data that
            was removed during the Arrange phase.
        Assert:
            - That the expected and actual sets of added entity IDs are
            identical.
        """
        ### Arrange ###
        task_aa = self.working_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*list("aa")))
        task_ac = self.working_tasktree.get_entity_for_id(
            TestDataEntitySupport.short_title_to_id(*list("ac")))
        
        self.working_tasktree.remove_entity(task_aa)
        self.working_tasktree.remove_entity(task_ac)
        
        expected_deleted_ids = set([task_aa.entity_id, task_ac.entity_id])

        ### Act ###
        actual_deleted_ids = self.comparator.find_deleted_ids(self.baseline_tasktree,
            self.working_tasktree)

        ### Assert ###
        self.assertEqual(expected_deleted_ids, actual_deleted_ids)
#------------------------------------------------------------------------------ 

class TaskTreeComparatorFindUpdatedTest(PopulatedTaskTreeTestSupport, unittest.TestCase):
    def setUp(self):
        PopulatedTaskTreeTestSupport.setUp(self)

        # Create the TaskTreeComparator that will be under test.
        self.comparator = TaskTreeComparator()

        self._register_fixtures(self.comparator)
        
    def test_find_updated_task_tasklist_title(self):
        """Test that the TaskTreeComparator can identify any entities in a 
        TaskTree that have updated title properties.

        TaskList a and Task a-b will have their title props updated to 
        "updated". A new TaskList Foo will also be added to the working tree
        before the comparison is made. TaskList Foo should _not_ appear in the
        list of updated IDs (only in the added IDs comparison). 

        Arrange:
            - Find entities TaskList a, Task a-b in working TaskTree.
            - Update the titles of each entity.
            - Create new TaskList Foo, and add it to the working TaskTree.
            - Create list of expected updated entity IDs.
        Act:
            - Use TaskTreeComparator.find_updated_id to locate the entity IDs
            of every entity that was changed between the two TaskTrees.
        Assert:
            - That the expected and actual sets of updated entity IDs are
            identical.
        """
        ### Arrange ###
        tasklist_a = self.find_tasklist(self.working_tasktree, 'a')
        task_b = self.find_task(self.working_tasktree, *list('ab'))
        update_title = "updated"
        tasklist_a.title = update_title
        task_b.title = update_title
        
        self.working_tasktree.update_entity(tasklist_a)
        self.working_tasktree.update_entity(task_b)
                
        TestDataTaskList(self.working_tasktree, 'foo')
        
        expected_updated_ids = set([tasklist_a.entity_id, task_b.entity_id])

        ### Act ###
        actual_updated_ids = self.comparator.find_updated_ids(
            self.baseline_tasktree, self.working_tasktree)

        ### Assert ###
        self.assertEqual(expected_updated_ids, actual_updated_ids)
        
    def test_find_updated_task_due_date(self):
        """Test that the TaskTreeComparator can identify any Tasks in a 
        TaskTree that have updated due date properties.

        Tasks c-a-c, a-c-c will have their title props updated to "updated".

        Arrange:
            - Find entities Task c-a-c, Task a-c-c in working TaskTree.
            - Update the due date property of each entity.
            - Create list of expected updated entity IDs.
        Act:
            - Use TaskTreeComparator.find_updated_id to locate the entity IDs
            of every entity that was changed between the two TaskTrees.
        Assert:
            - That the expected and actual sets of updated entity IDs are
            identical.
        """
        ### Arrange ###
        task_cac = self.find_task(self.working_tasktree, *list('cac'))
        task_acc = self.find_task(self.working_tasktree, *list('acc'))
        task_cac.due_date = datetime(1982, 2, 3)
        task_acc.due_date = datetime(1984, 02, 10) 
        
        self.working_tasktree.update_entity(task_cac)
        self.working_tasktree.update_entity(task_acc)
        
        expected_updated_ids = set([task_cac.entity_id, task_acc.entity_id])

        ### Act ###
        actual_updated_ids = self.comparator.find_updated_ids(
            self.baseline_tasktree, self.working_tasktree)

        ### Assert ###
        self.assertEqual(expected_updated_ids, actual_updated_ids)
        
    def test_find_updated_task_status(self):
        """Test that the TaskTreeComparator can identify any Tasks in a 
        TaskTree that have updated task status properties.
        
        The Task status property (task_status) indicates whether the Task has been 
        completed (or not).

        Task c-a-c will have its task status changed to "completed". Task 
        a-c-c will have its task status changed from "needs action" to
        "completed" and back to "needs action". Only Task c-a-c should be
        indicated as an entity that's been updated.

        Arrange:
            - Find entities Task c-a-c, Task a-c-c in working TaskTree.
            - Update the task status of Task c-a-c, a-c-c to "completed".
            - Update the task status of Task a-c-c to "needs action".
            - Create list of expected updated entity IDs (just Task c-a-c).
        Act:
            - Use TaskTreeComparator.find_updated_id to locate the entity IDs
            of every entity that was changed between the two TaskTrees.
        Assert:
            - That the expected and actual sets of updated entity IDs are
            identical.
        """
        ### Arrange ###
        task_cac = self.find_task(self.working_tasktree, *list('cac'))
        task_acc = self.find_task(self.working_tasktree, *list('acc'))
        
        task_cac.task_status = TaskStatus.COMPLETED
        task_acc.task_status = TaskStatus.COMPLETED 
        
        self.working_tasktree.update_entity(task_cac)
        self.working_tasktree.update_entity(task_acc)
        
        task_acc.task_status = TaskStatus.NEEDS_ACTION
        self.working_tasktree.update_entity(task_acc)
        
        expected_updated_ids = set([task_cac.entity_id])

        ### Act ###
        actual_updated_ids = self.comparator.find_updated_ids(
            self.baseline_tasktree, self.working_tasktree)

        ### Assert ###
        self.assertEqual(expected_updated_ids, actual_updated_ids)
        
    @skip(DISABLED_WORKING_OTHER_TESTS)
    def test_find_updated_ignores_reordering(self):
        """Test that the TaskTreeComparator will not consider reordered 
        tasks to be updated. 

        Arrange:
            - Find Task a-a-b in working TaskTree.
            - Promote Task a-a-b.
        Act:
            - Use TaskTreeComparator.find_updated_id to locate the entity IDs
            any updated entity IDs. This should not find anything.
        Assert:
            - That the actual set of updated entity IDs is empty.
        """
        ### Arrange ###
        task_cac = self.find_task(self.working_tasktree, *list('aab'))
        
        self.working_tasktree.promote_task(task_cac)

        ### Act ###
        actual_updated_ids = self.comparator.find_updated_ids(
            self.baseline_tasktree, self.working_tasktree)

        ### Assert ###
        self.assertEqual(set(), actual_updated_ids)
#------------------------------------------------------------------------------

@unittest.skip("Ordering broken with Task refactor.")
class TaskTreeComparatorFindReorderedTest(PopulatedTaskTreeTestSupport, unittest.TestCase):
    def setUp(self):
        PopulatedTaskTreeTestSupport.setUp(self)

        # Create the TaskTreeComparator that will be under test.
        self.comparator = TaskTreeComparator()

        self._register_fixtures(self.comparator)
        
    def test_find_reorder_up_updated_task(self):
        """Test that the TaskTreeComparator can identify any Tasks in a 
        TaskTree that have updated tree positions due to a reorder operation.
         
        Tasks a-b, a-c will have their positions switched. The resulting 
        relative branch of the tree will have this structure:
        
        - tl-a
            - t-a-a
                - [Unchanged]
            - t-a-c
                - t-a-c-a
                - t-a-c-b
                - t-a-c-c
            - t-a-b
                - t-a-b-a
                - t-a-b-b
                - t-a-b-c

        Arrange:
            - Find entities Tasks a-b, a-c in working TaskTree.
            - Reorder up Task a-c.
            - Create list of expected updated entity IDs.
        Act:
            - Use TaskTreeComparator.find_updated_id to locate the entity IDs
            of every entity that was changed between the two TaskTrees.
        Assert:
            - That the expected and actual sets of updated entity IDs are
            identical.
        """
        ### Arrange ###
        task_ab = self.find_task(self.working_tasktree, *list('ab'))
        task_ac = self.find_task(self.working_tasktree, *list('ac'))

        self.working_tasktree.reorder_task_up(task_ac)
        
        expected_updated_ids = set([task_ab.entity_id, task_ac.entity_id])

        ### Act ###
        actual_updated_ids = self.comparator.find_updated_ids(
            self.baseline_tasktree, self.working_tasktree)

        ### Assert ###
        self.assertEqual(expected_updated_ids, actual_updated_ids)
        
    def test_find_reorder_down_updated_task(self):
        """Test that the TaskTreeComparator can identify any Tasks in a 
        TaskTree that have updated tree positions due to a reorder operation.
         
        Tasks a-b, a-c will have their positions switched. The resulting 
        relative branch of the tree will have this structure:
        
        - tl-a
            - t-a-a
                - [Unchanged]
            - t-a-c
                - t-a-c-a
                - t-a-c-b
                - t-a-c-c
            - t-a-b
                - t-a-b-a
                - t-a-b-b
                - t-a-b-c

        Arrange:
            - Find entities Tasks a-b, a-c in working TaskTree.
            - Reorder down Task a-b.
            - Create list of expected updated entity IDs.
        Act:
            - Use TaskTreeComparator.find_updated_id to locate the entity IDs
            of every entity that was changed between the two TaskTrees.
        Assert:
            - That the expected and actual sets of updated entity IDs are
            identical.
        """
        ### Arrange ###
        task_ab = self.find_task(self.working_tasktree, *list('ab'))
        task_ac = self.find_task(self.working_tasktree, *list('ac'))

        self.working_tasktree.reorder_task_down(task_ab)
        
        expected_updated_ids = set([task_ab.entity_id, task_ac.entity_id])

        ### Act ###
        actual_updated_ids = self.comparator.find_updated_ids(
            self.baseline_tasktree, self.working_tasktree)

        ### Assert ###
        self.assertEqual(expected_updated_ids, actual_updated_ids)
        
    def test_find_demote_updated_task(self):
        """Test that the TaskTreeComparator can identify any Tasks in a 
        TaskTree that have updated tree positions due to a reorder operation.
         
        Task a-b will be demoted. The resulting 
        relative branch of the tree will have this structure:
        
        - tl-a
            - t-a-a
                - [Unchanged]
                - t-a-b
                    - t-a-b-a
                    - t-a-b-b
                    - t-a-b-c
            - t-a-c
                - t-a-c-a
                - t-a-c-b
                - t-a-c-c

        Arrange:
            - Find entities Tasks a-b, a-c in working TaskTree.
            - Demote Task a-b.
            - Create list of expected updated entity IDs.
        Act:
            - Use TaskTreeComparator.find_updated_id to locate the entity IDs
            of every entity that was changed between the two TaskTrees.
        Assert:
            - That the expected and actual sets of updated entity IDs are
            identical.
        """
        ### Arrange ###
        task_ab = self.find_task(self.working_tasktree, *'ab')
        task_ac = self.find_task(self.working_tasktree, *'ac')

        self.working_tasktree.demote(task_ab)
        
        expected_updated_ids = set([task_ab.entity_id, task_ac.entity_id])

        ### Act ###
        actual_updated_ids = self.comparator.find_updated_ids(
            self.baseline_tasktree, self.working_tasktree)

        ### Assert ###
        self.assertEqual(expected_updated_ids, actual_updated_ids)
        
    def test_find_promote_updated_task(self):
        """Test that the TaskTreeComparator can identify any Tasks in a 
        TaskTree that have updated tree positions due to a reorder operation.
         
        Task a-b-a will be promoted. The resulting 
        relative branch of the tree will have this structure:
        
        - tl-a
            - t-a-a
                - [Unchanged]
            - t-a-b
                - t-a-b-b
                - t-a-b-c
            - t-a-b-a
            - t-a-c
                - t-a-c-a
                - t-a-c-b
                - t-a-c-c

        Arrange:
            - Find entities Tasks a-b-a, a-b-b, a-c in working TaskTree.
            - Promote Task a-b.
            - Create list of expected updated entity IDs.
        Act:
            - Use TaskTreeComparator.find_updated_id to locate the entity IDs
            of every entity that was changed between the two TaskTrees.
        Assert:
            - That the expected and actual sets of updated entity IDs are
            identical.
        """
        ### Arrange ###
        task_aba = self.find_task(self.working_tasktree, *list('aba'))
        task_abb = self.find_task(self.working_tasktree, *list('abb'))
        task_ac = self.find_task(self.working_tasktree, *list('ac'))

        self.working_tasktree.promote(task_aba)
        
        expected_updated_ids = set([task_aba.entity_id, task_abb.entity_id, task_ac.entity_id])

        ### Act ###
        actual_updated_ids = self.comparator.find_updated_ids(
            self.baseline_tasktree, self.working_tasktree)

        ### Assert ###
        self.assertEqual(expected_updated_ids, actual_updated_ids)
#------------------------------------------------------------------------------ 

class TaskDataError(Exception):
    def __init__(self, message):
        Exception.__init__(self, "Corrupt task data: " + message) 
#------------------------------------------------------------------------------ 

class UpdateTaskStatusTest(ManagedFixturesTestSupport, unittest.TestCase):
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
        tasktree = TaskTree()
        tasklist_a = TestDataTaskList(tasktree, 'a')
        task_aa = TestDataTask(tasklist_a, *'aa')
        task_aaa = TestDataTask(task_aa, *'aaa')
        task_aab = TestDataTask(task_aa, *'aab', task_status=TaskStatus.COMPLETED)
        
        ### Act ###
        tasktree.update_task_status(task_aaa, TaskStatus.COMPLETED)
        tasktree.update_task_status(task_aab, TaskStatus.NEEDS_ACTION)
        
        ### Assert ###
        self.assertEqual(tasktree.get_entity_for_id(task_aaa.entity_id).task_status,
            TaskStatus.COMPLETED)
        self.assertEqual(tasktree.get_entity_for_id(task_aab.entity_id).task_status,
            TaskStatus.NEEDS_ACTION)
        
    def test_update_task_status_parent_task(self):
        """Test changing the status of a parent Task from Needs Action to 
        Complete, checking to ensure that child Tasks are similarly updated.
        
        Arrange:
            - Create TaskTreeService backed by mock Task/List services
            populated with TaskList A, Tasks AA, AAA, AAB.
        Act:
            - Update the task status of Task AA to be Completed.
        Assert:
            - Tasks AA, AAA, AAB as retrieved from the TaskTree, all have 
            identical task statuses of Completed.
        """
        ### Arrange ###
        tasktree = TaskTree()
        tasklist_a = TestDataTaskList(tasktree, 'a')
        task_aa = TestDataTask(tasklist_a, *'aa')
        task_aaa = TestDataTask(task_aa, *'aaa')
        task_aab = TestDataTask(task_aa, *'aab', task_status=TaskStatus.COMPLETED)
        
        ### Act ###
        tasktree.update_task_status(task_aa, TaskStatus.COMPLETED)
        
        ### Assert ###
        self.assertEqual(tasktree.get_entity_for_id(task_aa.entity_id).task_status,
            TaskStatus.COMPLETED)
        self.assertEqual(tasktree.get_entity_for_id(task_aaa.entity_id).task_status,
            TaskStatus.COMPLETED)
        self.assertEqual(tasktree.get_entity_for_id(task_aab.entity_id).task_status,
            TaskStatus.COMPLETED)
        
    def test_update_task_status_child_task_updates_parent(self):
        """Test changing the status of a child Task from Completed to Needs 
        Action will also similarly update the status of any parent Tasks.
        
        Arrange:
            - Create TaskTreeService backed by mock Task/List services
            populated with TaskList A, Tasks AA, AAA, AAB.
        Act:
            - Update the task status of Task AAA to be Completed.
        Assert:
            - Tasks AA, AAA, AAB as retrieved from the TaskTree, have task 
            statuses of Needs Action, Needs Action, and Completed, 
            respectively.
        """
        ### Arrange ###
        tasktree = TaskTree()
        tasklist_a = TestDataTaskList(tasktree, 'a')
        task_aa = TestDataTask(tasklist_a, *'aa', task_status=TaskStatus.COMPLETED)
        task_aaa = TestDataTask(task_aa, *'aaa', task_status=TaskStatus.COMPLETED)
        task_aab = TestDataTask(task_aa, *'aab', task_status=TaskStatus.COMPLETED)
        
        ### Act ###
        tasktree.update_task_status(task_aaa, TaskStatus.NEEDS_ACTION)
        
        ### Assert ###
        self.assertEqual(tasktree.get_entity_for_id(task_aa.entity_id).task_status,
            TaskStatus.NEEDS_ACTION)
        self.assertEqual(tasktree.get_entity_for_id(task_aaa.entity_id).task_status,
            TaskStatus.NEEDS_ACTION)
        self.assertEqual(tasktree.get_entity_for_id(task_aab.entity_id).task_status,
            TaskStatus.COMPLETED)
#------------------------------------------------------------------------------

