"""
Created on Apr 9, 2012

@author: Clay Carpenter
"""
from gi.repository import Gtk, GdkPixbuf
import unittest
from coggrinder.entities.tasks import TaskList, Task, TaskStatus
from coggrinder.resources.icons import task_tree

class TaskTreeStore(Gtk.TreeStore):
    def __init__(self):
#        self.store = Gtk.TreeStore(str, str, GdkPixbuf.Pixbuf)
        Gtk.TreeStore.__init__(self, str, str, GdkPixbuf.Pixbuf)

        # TODO: Document keys, values, uses.
        self.entity_path_index = dict()

    def build_tree(self, tasktree):
        """Build a tree representing all of the user's task data (TaskLists and
        Tasks).

        TaskLists will always be first-level nodes, while Tasks will always be
        at least second-level nodes or deeper.

        Args:
            tasktree: The TaskTree that contains the task data.
        Returns:
            A dict that maps entity (both TaskList and Task) ID keys to
            their path (as a str) in the TreeModel.
        """
        # Reset the entity id-tree path registry. 
        self.entity_path_index = dict()
        
        # Access the TaskTree using node methods, TreeNode info.
        
        # Get the depth-1 child nodes of the TaskTree. Each of these will hold
        # a TaskList reference.
        tasktree_root_node = tasktree.get_root_node()
        for tasklist_node in tasktree_root_node.children:            
            self._build_task_tree(tasktree, tasklist_node)
            
        return self.entity_path_index
        
    def _build_task_tree(self, tasktree, current_node, parent_node_iter=None):        
        # Collect the entity data into a TreeView-compatible list, and then
        # add the row to the tree under the parent node.
        entity = current_node.value
        row_model_data = TreeNode(entity).row_data
        entity_iter = self.append(parent_node_iter, row_model_data)
        
        # Add the TaskList to the path index.
        treepath = self.get_path(entity_iter)
        self.entity_path_index[entity.entity_id] = treepath.to_string()
        
        # Recursively add all descendants of this current node.
        for child_node in current_node.children:
            self._build_task_tree(tasktree, child_node, entity_iter)       

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
        tasklist_iter = self.append(self._root, TreeNode(tasklist).row_data)

        # Recursively build the task tree with the given tasks.
        if tasks is not None:
            self._build_tree_from_tasks(tasks, tasklist_iter)

    def add_entity(self, entity, parent_iter=None):
        new_node_iter = self.append(parent_iter, TreeNode(entity).row_data)
        self.entity_path_index[entity.entity_id] = self.get_string_from_iter(new_node_iter)

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
            entity_id = self.get_value(node_iter, TreeNode.ENTITY_ID)
            label = self.get_value(node_iter, TreeNode.LABEL)
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

class TreeNode(object):
    ENTITY_ID = 0
    LABEL = 1
    ICON = 2

    def __init__(self, entity):
        self.row_data = list()
        self.row_data.insert(TreeNode.ENTITY_ID, entity.entity_id)
        self.row_data.insert(TreeNode.LABEL, entity.title)

        # Create icons needed to present the task tree.
        self.list_image = Gtk.Image.new_from_file(task_tree.FILES["folder.png"])
        self.task_complete_image = Gtk.Image.new_from_file(task_tree.FILES["checkmark.png"])
        self.task_incomplete_image = Gtk.Image.new_from_file(task_tree.FILES["checkbox_unchecked.png"])

        list_icon = self.list_image.get_pixbuf()
        checked_icon = self.task_complete_image.get_pixbuf()
        unchecked_icon = self.task_incomplete_image.get_pixbuf()

        if isinstance(entity, TaskList):
            icon = list_icon
        elif isinstance(entity, Task):
            if entity.task_status == TaskStatus.COMPLETED:
                icon = checked_icon
            else:
                icon = unchecked_icon
        else:
            raise ValueError("Cannot determine type of provided entity {0}".format(entity))

        self.row_data.insert(TreeNode.ICON, icon)
#------------------------------------------------------------------------------ 

class TaskListTree(object):
    """
    TODO:
    -- Would be great if this supported the same path strings as the
    Gtk.TreeStore objects ("0", "1:0", "2:4:1", etc.)

    ...hmmm... or maybe this should just be a better extension of the
    TaskTreeStore.
    """
    def __init__(self, tasklist):
        self.tasklist = tasklist
#        if tasks is None:
#            self.tasks = dict()
#        else:
#            self.tasks = tasks            
#------------------------------------------------------------------------------

class TaskListTreeTest(unittest.TestCase):
    @unittest.skip("May not be necessary...")
    def test_create_new_tree_from_tasklist(self):
        """
        Create a tasklist and three child tasks. Child tasks will be provided
        in a dict, keyed by entity id with the values being the tasks
        themselves.

        The tasks will be organized such that tasks A and B are direct
        descendants of the tasklist (i.e., "top-level" tasks) while C is a
        child of A. Task A will be ordered before (higher than) task B.

        Tasks will all be added to the TaskListTree as a single dict, rather
        than individually.
        """
        tasklist = TaskList(entity_id="tl-1")

        # Direct children of the tasklist.
        task_a = Task(entity_id="t-a", tasklist_id=tasklist.entity_id, title="task a", position=1)
        task_b = Task(entity_id="t-b", tasklist_id=tasklist.entity_id, title="task b", position=2)

        # Child of task A.
        task_c = Task(entity_id="t-c", tasklist_id=tasklist.entity_id, title="task c", parent_id=task_a.entity_id, position=1)

        # Dict of the three tasks.
        tasks = {task_a.entity_id:task_a, task_b.entity_id:task_b, task_c.entity_id:task_c}

        # Create and populate the tasklist tree.
        tl_tree = TaskListTree(tasklist)
        tl_tree.add_tasks(tasks)

        # 
#        tl_tree.

        self.assertTrue(False)
#------------------------------------------------------------------------------ 
