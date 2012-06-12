"""
Created on Apr 9, 2012

@author: Clay Carpenter
"""
from gi.repository import Gtk, GdkPixbuf
import unittest
from coggrinder.entities.tasks import TaskList, Task, TaskStatus, TaskDataSorter
from coggrinder.resources.icons import task_tree
from coggrinder.entities.tasktree import TaskTreeComparator
from coggrinder.services.task_services import UnregisteredEntityError
import copy
from logging import debug
from coggrinder.entities.tree import NodeRelationshipError

class TaskTreeStore(Gtk.TreeStore):
    PATH_SEPARATOR = ":"
    
    def __init__(self):
        Gtk.TreeStore.__init__(self, str, str, GdkPixbuf.Pixbuf)

        # TODO: Better document keys, values, uses.
        # This index allows us to quickly look up where in the tree a given
        # entity is.
        self.entity_path_index = dict()
        
        self.is_updating_tree = False

    def build_tree(self, tasktree):
        """Build a Gtk.TreeStore model representing all of the user's 
        task data (TaskLists and Tasks).

        TaskLists will always be first-level nodes, while Tasks will always be
        at least second-level nodes or deeper.

        Args:
            tasktree: The TaskTree that contains the task data.
        Returns:
            A dict that maps entity (both TaskList and Task) ID keys to
            their path (as a str) in the TreeModel.
        """        
        # Prevent events that are fired due to updates made to the TreeStore
        # from being responded to.
        self.is_updating_tree = True
        
        # Reset the entity id-tree path registry. 
        self._clear_entity_path_index()
        
        # Reset (clear) current tree model.
        self.clear() 
                       
        # Get the depth-1 child nodes of the TaskTree. Each of these will hold
        # a TaskList reference.
        tasktree_root_node = tasktree.get_root_node()
        for tasklist_node in tasktree_root_node.children:            
            self._build_tasktree_branch(tasktree, tasklist_node, None)        

        # Rebuild the entity-path index (cleared before the TreeStore was built).
        self._rebuild_entity_path_index(tasktree)        
        debug("Post-build/expand state:\n{0}".format(self))
        
        self.is_updating_tree = False
        
    def _build_tasktree_branch(self, tasktree, current_node, parent_node_iter, insert_position=None):        
        # Collect the entity data into a TreeView-compatible list, and then
        # add the row to the tree under the parent node.
        entity = current_node.value
        row_model_data = TaskTreeStoreNode(entity).row_data
        
        if insert_position is not None:
            entity_iter = self.insert(parent_node_iter, insert_position, row_model_data)
        else:
            entity_iter = self.append(parent_node_iter, row_model_data)
        
        # Recursively add all descendants of this current node.
        for child_node in current_node.children:
            self._build_tasktree_branch(tasktree, child_node, entity_iter)   
            
    def _find_parent_iter(self, new_entity_node):        
        parent_treepath = self._get_treestore_path(new_entity_node.parent)
        
        if parent_treepath is not None:
            return self.get_iter_from_string(parent_treepath)
        else:
            return None
            
    def _get_treestore_path(self, entity_node):
        no_root_path = entity_node.path[1:]
        
        if no_root_path:
            return ":".join([str(x) for x in entity_node.path[1:]])
        else:
            return None

    def get_entity(self, tree_path):
        """Retrieves the entity targeted by the specified tree path.

        Args:
            tree_path: The path to the target entity, in the form of "0:0:0".

        Returns:
            The entity (Task or TaskList) at the provided path, or None if the
            path does not point to a valid tree node.
        """
        assert isinstance(tree_path, str), "Tree path provided must be a string in the form of '0:0:0'"

        raise NotImplementedError()

    def add_tasklist(self, tasklist, tasks=None):
        """Creates a new task tree branch for the TaskList and its associated
        Tasks.

        The TaskList will be the root of the new tree branch, with all of the
        belonging Tasks filling out the rest of the branch.

        Args:
            tasklist: The TaskList to add to the task tree. This will become
            a first level node in the tree.
            tasks: A dict containing all Tasks belonging to the TaskList. Keys
            should be the entity id, and values should be the associated
            entity. Defaults to None.
        """
        # Add the tasklist as a direct descendant of the root of the task tree.
        tasklist_iter = self.append(self._root, TaskTreeStoreNode(tasklist).row_data)

        # Recursively build the task tree with the given tasks.
        if tasks is not None:
            self._build_tree_from_tasks(tasks, tasklist_iter)

    def add_entity(self, tasktree, entity):
        # Find the new node's position in the TaskTree (task data set).
        new_entity_node = tasktree.find_node_for_entity(entity)
        
        # Find the parent TreeIter for the new path.
        parent_iter = self._find_parent_iter(new_entity_node)
        
        # Get the insert position for the new row. This will be identical to 
        # the child index of the new TaskTree node. 
        insert_position = new_entity_node.child_index
        
        # Insert a new GtkTreeStore row/node.
        new_node_iter = self.insert(parent_iter, insert_position, 
            TaskTreeStoreNode(entity).row_data)
            
    def get_entity_id_for_path(self, tree_path):
        if tree_path in self.entity_path_index.values():
            key_index = self.entity_path_index.values().index(tree_path)
            return self.entity_path_index.keys()[key_index]
        else:
            raise KeyError(
                "Could not find an entity registered with Gtk tree path {0}".format(
                tree_path))

    def get_path_for_entity_id(self, entity_id):
        try:
            return self.entity_path_index[entity_id]
        except KeyError:
            raise UnregisteredEntityError(entity_id)
        
    def get_path_for_entity(self, entity):
        return self.get_path_for_entity_id(entity.entity_id)

    def get_entity_for_path(self, tasktree, tree_path):
        entity_id = self.get_entity_id_for_path(tree_path)

        entity = tasktree.get_entity_for_id(entity_id)

        return entity
    
    def get_iter_for_entity(self, entity):
        tree_path = self.get_path_for_entity(entity)
        
        return self.get_iter(tree_path)
        
    def _is_tasklist_iter(self, tree_iter):
        if self.iter_depth(tree_iter) == 0:
            return True
        
        return False
    
    def _register_entity(self, entity, treepath):
        self.entity_path_index[entity.entity_id] = str(treepath)
        
    def _deregister_entity(self, entity):
        del self.entity_path_index[entity.entity_id]
    
    def _clear_entity_path_index(self):
        self.entity_path_index = dict()

    def _rebuild_entity_path_index(self, tasktree):        
        self._clear_entity_path_index()
        
        for entity_id in tasktree.all_entity_ids:
            tasktree_node = tasktree.find_node_for_entity_id(entity_id)
            entity_treepath = self._get_treestore_path(tasktree_node)
            
            self.entity_path_index[entity_id] = entity_treepath
            
    def _validate_entity_path_index(self, tasktree):
        # Check for matching sets of registered entity IDs.
        if tasktree.all_entity_ids != set(self.entity_path_index.keys()):
            raise EntityPathIndexError(
                "TaskTree and entity-path index have different sets of registered entity IDs.")
            
        # Check that each entity registered has a TreeStore path that is 
        # equivalent to the TaskTree node path.
        for entity_id in tasktree.all_entity_ids:
            tasktree_node = tasktree.find_node_for_entity_id(entity_id)
            expected_treepath = self._get_treestore_path(tasktree_node)
            
            if expected_treepath != self.get_path_for_entity_id(entity_id):
                raise EntityPathIndexError(
                    "Entity with ID '{id}' has path in TaskTree of {tasktree_path}, while entity-path registry has path recorded as {treestore_path}".format(
                        id=entity_id,tasktree_path=expected_treepath, treestore_path = self.get_path_for_entity_id()))

    def __str__(self):
        return self._create_branch_str()

    def __repr__(self):
        return self.__str__()

    def _create_branch_str(self, node_iter=None, depth=0, indent=4):
        if node_iter is None:
            # If no node iter is provided, use the root node iter.
            node_iter = self.get_iter_first()
            
            if node_iter is None:
                return "<Empty TaskTreeStore>"
        
        branches_str = list()
        while node_iter != None:               
            # Collect node information.
            node_path = self.get_path(node_iter)
            entity_id = self.get_value(node_iter, TaskTreeStoreNode.ENTITY_ID)
            label = self.get_value(node_iter, TaskTreeStoreNode.LABEL)
            if label is None:
                label = "<Empty title>"
            node_values_str = "'{label}' - id: '{entity_id}'".format(
                entity_id=entity_id, label=label)
            
            # Create the node info debug string.
            node_str = "{indent} - {path} - {value}\n".format(
                indent="".center(depth * indent), path=node_path, value=node_values_str)
            branches_str.append(node_str)
                      
            if self.iter_has_child(node_iter):
                child_iter = self.iter_children(node_iter)
                
                branches_str.append(self._create_branch_str(
                    node_iter=child_iter, depth=depth + 1, indent=indent))
            
            node_iter = self.iter_next(node_iter)
        
        return "".join(branches_str)
#------------------------------------------------------------------------------ 

class TaskTreeStoreTest(unittest.TestCase):
    @unittest.expectedFailure
    def test_add_entity(self):
        """Test adding a single TaskList to a blank TaskTreeStore.

        Arrange:
            Create blank/empty TaskTreeStore.
            Create a TaskList.

        Act:
            Add the TaskList to the TaskTreeStore.

        Assert:
            Tree path "0" should return the TaskList.
        """
        ### Arrange ###########################################################
        tasktree = TaskTreeStore()
        tasklist = TaskList(entity_id="tl-1")

        ### Act ###############################################################   
        tasktree.add_entity(tasklist)

        ### Assert ############################################################
        self.assertIsNotNone(tasktree.get_entity_for_id("0"))

    @unittest.expectedFailure
    def test_create_blank_tree(self):
        """Test creation of an empty tree.

        Act:
            Create a tree without providing any tasklists or tasks.

        Assert:
            Tree path "0" should return None.
        """
        ### Act ###############################################################
        tasktree = TaskTreeStore()

        ### Assert ############################################################
        self.assertIsNone(tasktree.get_entity_for_id("0"))

    @unittest.expectedFailure
    def test_create_new_tree_from_tasklist(self):
        """Test creation of a tree populated with child tasks, ensuring those
        children are accessible via (Gtk-style) tree path strings.

        Create a tasklist and three child tasks. Child tasks will be provided
        in a dict, keyed by entity id with the values being the tasks
        themselves.

        The tasks will be organized such that tasks A and B are direct
        descendants of the tasklist (i.e., "top-level" tasks) while C is a
        child of A. Task A will be ordered before (higher than) task B.

        Tasks will all be added to the TaskListTree as a single dict, rather
        than individually.

        Arrange:
            Create new, blank tree.
            Create tasklist.
            Create three child tasks, A, B, C. Establish C as child of A.
            Create dict of three tasks (imitating service query result).

        Act:
            Add tasklist and tasks (dict) to the tree.
            Request entity at 0 (expect tasklist)
            Request entity at 0:0 (expect task A)
            Request entity at 0:1 (expect task B)
            Request entity at 0:1:0 (expect task C)

        Assert:
            Actual tasklist and tasks A,B,C are equal to expected objects.
        """
        ### Arrange ###########################################################

        # Create an empty TaskTreeStore.
        tasktree = TaskTreeStore()

        tasklist = TaskList(entity_id="tl-1")

        # Direct children of the tasklist.
        task_a = Task(entity_id="t-a", tasklist_id=tasklist.entity_id,
            title="task a", position=1)
        task_b = Task(entity_id="t-b", tasklist_id=tasklist.entity_id,
            title="task b", position=2)

        # Child of task A.
        task_c = Task(entity_id="t-c", tasklist_id=tasklist.entity_id,
            title="task c", parent_id=task_a.entity_id, position=1)

        # Dict of the three tasks.
        tasks = {task_a.entity_id:task_a, task_b.entity_id:task_b,
            task_c.entity_id:task_c}

        ### Act ###############################################################

        # Populate the tree.
        tasktree.add_tasklist(tasklist, tasks)

        # Retrieve the tasklist and tasks by using their expected tree path 
        # strings.
        actual_tasklist = tasktree.get_entity_for_id("0")
        actual_task_a = tasktree.get_entity_for_id("0:0")
        actual_task_b = tasktree.get_entity_for_id("0:1")
        actual_task_c = tasktree.get_entity_for_id("0:0:0")

        ### Assert ############################################################
        self.assertEqual(
            (tasklist, task_a, task_b, task_c),
            (actual_tasklist, actual_task_a, actual_task_b, actual_task_c))

    @unittest.skip("Disabled due to refactoring.")
    def test_get_entity_tasklist_only(self):
        expected_tasklists = dict()
        tasklist_count = 3
        for i in range(tasklist_count):
            tasklist = TaskList()
            tasklist.entity_id = "tl-{0}".format(i)
            tasklist.title = "TaskList {0}".format(i)

            expected_tasklists[tasklist.entity_id] = tasklist

        task_treestore = TaskTreeStore(expected_tasklists, {})

        actual_tasklists = dict()
        for i in range(tasklist_count):
            actual_tasklist = task_treestore.get_entity_for_id(str(i))
            self.assertIsNotNone(actual_tasklist)

            actual_tasklists[actual_tasklist.entity_id] = actual_tasklist

        self.assertEqual(expected_tasklists, actual_tasklists)

    @unittest.skip("Disabled due to refactoring.")
    def test_get_entity_tasks(self):
        tasklist = TaskList(entity_id="tl-0", title="TaskList 0")
        expected_tasklists = {tasklist.entity_id: tasklist}

        expected_task_l1 = Task(entity_id="t-0", title="Task 0",
            tasklist_id=tasklist.entity_id)

        expected_task_l2 = Task(entity_id="t-1", title="Task 1",
            tasklist_id=tasklist.entity_id, parent_id=expected_task_l1.entity_id)

        expected_tasks = {expected_task_l1.entity_id: expected_task_l1,
            expected_task_l2.entity_id:expected_task_l2}

        task_treestore = TaskTreeStore(expected_tasklists, expected_tasks)

        actual_task_l1 = task_treestore.get_entity_for_id("0:0")
        self.assertEqual(expected_task_l1, actual_task_l1)

        actual_task_l2 = task_treestore.get_entity_for_id("0:0:0")
        self.assertEqual(expected_task_l2, actual_task_l2)
#------------------------------------------------------------------------------ 

class EntityPathIndexError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
#------------------------------------------------------------------------------ 

class TaskTreeStoreNode(object):
    ENTITY_ID = 0
    LABEL = 1
    ICON = 2
    
    # Create icons needed to present the task tree.
    LIST_IMAGE = Gtk.Image.new_from_file(task_tree.FILES["folder.png"]).get_pixbuf()
    TASK_COMPLETE_IMAGE = Gtk.Image.new_from_file(task_tree.FILES["checkmark.png"]).get_pixbuf()
    TASK_INCOMPLETE_IMAGE = Gtk.Image.new_from_file(task_tree.FILES["checkbox_unchecked.png"]).get_pixbuf()

    def __init__(self, entity):
        self.row_data = list()
        self.row_data.insert(TaskTreeStoreNode.ENTITY_ID, entity.entity_id)
        self.row_data.insert(TaskTreeStoreNode.LABEL, entity.title)

        if isinstance(entity, TaskList):
            icon = self.LIST_IMAGE
        elif isinstance(entity, Task):
            if entity.task_status == TaskStatus.COMPLETED:
                icon = self.TASK_COMPLETE_IMAGE
            else:
                icon = self.TASK_INCOMPLETE_IMAGE
        else:
            raise ValueError("Cannot determine type of provided entity {0}".format(entity))

        self.row_data.insert(TaskTreeStoreNode.ICON, icon)
#------------------------------------------------------------------------------ 
