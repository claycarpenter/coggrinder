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
        self.store = Gtk.TreeStore(str, str, GdkPixbuf.Pixbuf)

        self.entity_path_index = dict()
        
    def build_tree(self, tasklists, tasks):
        """ 
        Build a tree representing all of the user's tasklists and tasks.
        Tasklists will always be first-level nodes, while tasks will always be
        at least second-level nodes or deeper.
        
        Args:
            tasklists:
            tasks:
        """
#        self._root
#        self.entity_path_index = dict()
#        
#        # Iterate over the tasklists dict, adding each tasklist to the root. 
#        for tasklist_id in tasklists:
#            tasklist = tasklists[tasklist_id]
#            tasklist_iter = self.append(self._root, TreeNode(tasklist).row_data)
#            
#            # Add tasklist to the path index.
#            self.entity_path_index[tasklist.entity_id] = self.get_path(tasklist_iter).to_string()
#
#            # Find all tasks with this tasklist id and FOO parent id.
#            self._build_tasklist_task_tree(tasks, entity_path_index, tasklist_iter, tasklist_id, None)
#            
#        return entity_path_index
    
    def _build_tree_from_tasks(self, tasks, parent_iter):
        """
        Build a tree for a particular tasklist.
        """
        # Determine which entities remaining in the tasks dict have yet to be 
        # added to the tree by comparing sets of keys in the tasks dict vs
        # those in the entity path index.
        keys_in_tasklist = set(tasks.keys())
        keys_in_tree = set(self.entity_path_index.keys())
        remaining_keys = keys_in_tasklist - keys_in_tree
        
        # Check to see if the parent is a tasklist or task.
        parent_id = self[parent_iter][TreeNode.ENTITY_ID]
        parent = self.entity_path_index[parent_id]
        if isinstance(parent, TaskList):
            parent_id = None
        
        for entity_id in remaining_keys:
            task = tasks[entity_id]
            
            if task.parent_id == parent_id:
                task_iter = self.append(parent_iter, TreeNode(task).row_data)
            
                # Add task to the path index.
                self.entity_path_index[task.entity_id] = self.get_string_from_iter(task_iter)
                
                self._build_tree_from_tasks(tasks, task_iter)  

    def get_entity(self, tree_path):
        """Retrieves the entity targeted by the specified tree path.
        
        Args:
            tree_path: The path to the target entity, in the form of "0:0:0".
        
        Returns:
            The entity (Task or TaskList) at the provided path, or None if the
            path does not point to a valid tree node.
        """
        assert(isinstance(tree_path, str), 
            "Tree path provided must be a string in the form of '0:0:0'")
        
        return None
    
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
        new_node_iter = self.store.append(parent_iter, TreeNode(entity).row_data)
        self.entity_path_index[entity.entity_id] = self.store.get_string_from_iter(new_node_iter)
        
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
        self.assertIsNotNone(tasktree.get_entity("0"))
        
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
        self.assertIsNone(tasktree.get_entity("0"))

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
        actual_tasklist = tasktree.get_entity("0")
        actual_task_a = tasktree.get_entity("0:0")
        actual_task_b = tasktree.get_entity("0:1")
        actual_task_c = tasktree.get_entity("0:0:0")
        
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
            actual_tasklist = task_treestore.get_entity(str(i))
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
        
        actual_task_l1 = task_treestore.get_entity("0:0")
        self.assertEqual(expected_task_l1, actual_task_l1)
        
        actual_task_l2 = task_treestore.get_entity("0:0:0")
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
