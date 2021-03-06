'''
Created on Apr 11, 2012

@author: Clay Carpenter
'''

import unittest

class Tree(object):
    ROOT_PATH = (0,)
    PATH_SEPARATOR = ":"

    def __init__(self):
        self.children = list()
        self.path = ()

    # TODO: What's the difference between append and insert?
    def append(self, parent_node, value):
        new_node = TreeNode(value=value)

        return self.append_node(parent_node, new_node)

    def append_node(self, parent_node, new_node):
        if not parent_node:
            # An empty parent node implies the tree is the parent.
            parent_node = self

            if self.children:
                # If the tree already has a root node, raise an error.
                raise DuplicateRootError()

        new_child_index = len(parent_node.children)
        new_node.path = parent_node.path + (new_child_index,)
        new_node.parent = parent_node

        parent_node.children.append(new_node)

        return new_node

    @staticmethod
    def build_str_from_path(*path_indices):
        """Constructs a tree path from the list of indices.

        Always assumes an implied root node (0), and calling the method without
        any path indices will generate the root node address.

        Args:
            path_indices: Iterable collection of individual path indices. Must
                be able to convert to string values.
        """
        tree_path = str(Tree.ROOT_PATH[0])

        for path_index in path_indices:
            tree_path += Tree.PATH_SEPARATOR + str(path_index)

        return tree_path

    @staticmethod
    def build_path_from_str(path_string=None):
        """Build a path from the tree path string representation.

        The root node is implied, and will be added to the resulting path
        index set regardless of the arguments.

        Args:
            path_string: The string representation of the tree path. Should not
                include the root node index, as this is implied. Defaults to
                None.
        """
        path_indices = Tree.ROOT_PATH

        if path_string is not None:
            branch_indices = path_string.split(":")
            for index in branch_indices:
                path_indices += (int(index),)

        return path_indices

    def has_children(self, node_indices):
        node = self.get_node(node_indices)

        if node is None:
            raise NodeNotFoundError(node_indices)

        return node.has_children()

    def has_siblings(self, node_indices):
        node = self.get_node(node_indices)
        assert node.parent is not None

        if len(node.parent.children) > 1:
            return True
        else:
            return False

    def has_path(self, node_indices):
        node = self.get_node(node_indices, must_find=False)

        if node is not None:
            return True
        else:
            return False

    def demote(self, *nodes):
        self._validate_reorganization_nodes(*nodes)

        # Check to ensure the root node is not included in the collection of 
        # nodes to be promoted.
        if self.get_node(Tree.ROOT_PATH) in nodes:
            raise RootReorganizationError()

        # Sort all nodes by parent.
        sorted_nodes = self._sort_nodes_by_parent(*nodes)

        # Perform demotion operations in the context of each sibling group.
        for parent_node in sorted_nodes:
            if len(parent_node.children) > 1:
                # Create a set to collect adjacent selected nodes. Adjacent 
                # selected nodes will be demoted as a group below the lowest 
                # order adjacent unselected node.
                adjacent_selected_nodes = set()

                # Walk the list of all sibling nodes (_not_ just the
                # selected nodes) backwards (lowest order to highest).
                for sibling_node in reversed(parent_node.children):
                    if sibling_node in nodes:
                        # The sibling is selected for demotion, add it to the
                        # adjacent selected nodes set.
                        adjacent_selected_nodes.add(sibling_node)
                    else:
                        if adjacent_selected_nodes:
                            # Make all of the adjacent selected nodes children
                            # of this sibling.
                            for selected_node in adjacent_selected_nodes:
                                self.move_node(sibling_node, selected_node)

                            # Reset the adjacent selected nodes collection.
                            adjacent_selected_nodes.clear()

    def get(self, node_indices):
        node = self.get_node(node_indices)

        if node is None:
            raise NodeNotFoundError(node_indices)

        return node.value

    def get_parent_node(self, node_indices):
        """Find the parent of the specified node address.

        This will be the node addressed by all but the final index in the
        full node address.

        Args:
            node_indices: # TODO: Finish this documentation.
        """
        parent_node_address = node_indices[:-1]

        if parent_node_address:
            parent_node = self.get_node(parent_node_address)

            if parent_node is None:
                raise NodeNotFoundError(parent_node_address)
        else:
            # The "parent node" is the tree itself.            
            parent_node = self

        return parent_node

    def get_node(self, node_indices, must_find=True):
        """Finds the node addressed by the given indices.

        Args:
            node_indices: List of node indices that point to a node within the
                tree. Must be convertible to type int. Should always begin
                with the root node (0).
        Returns:
            The TreeNode if it can be found. If no node is found, then None is
            returned.
        """
        assert node_indices, "A node address must be provided."

        try:
            node = self
            for index in node_indices:
                node = node.children[int(index)]
        except IndexError:
            node = None

        if must_find and node is None:
            raise NodeNotFoundError(node_indices)

        return node

    def insert(self, node_indices, value=None):
        assert node_indices, "A node address must be provided."

        new_node = self.insert_node(node_indices)

        new_node.value = value

        return new_node

    def insert_node(self, node_indices):
        assert node_indices, "A node address must be provided."

        parent_node_address = node_indices[:-1]
        child_index = node_indices[-1]

        parent_node = self.get_parent_node(node_indices)

        # Ensure that there is only one root to the tree.
        if parent_node is self and parent_node.children:
                raise DuplicateRootError()

        if child_index < 0 or child_index > len(parent_node.children):
            raise IndexError("Node index {0} is not valid for the parent at path {1}".format(child_index, parent_node_address))

        child_node = TreeNode(parent_node, node_indices)
        parent_node.children.insert(child_index, child_node)

        # Update the paths of any moved nodes.
        for index in range(child_index, len(parent_node.children)):
            updated_node = parent_node.children[index]
            updated_node.path = parent_node.path + (index,)

        return child_node

    def move_node(self, new_parent_node, node):
        if node is self.get_node(Tree.ROOT_PATH):
            raise RootReorganizationError()

        # Walk up the tree from the new parent node to root, ensuring that 
        # the moving node is not currently a parent of the new parent node.
        parent_node = new_parent_node.parent
        while parent_node is not None and parent_node is not self:
            if parent_node is node:
                raise NodeMoveTargetError(new_parent_node, node)

            parent_node = parent_node.parent

        # Remove the node from its current position.
        self.remove_node(node)

        # Add the moving node to the new parent node's children.
        self.append_node(new_parent_node, node)

        return node

    def promote(self, *nodes):
        self._validate_reorganization_nodes(*nodes)

        # Sort the nodes in order from deepest (longest path) to shallowest
        # (shortest path).
        sorted_nodes = self._sort_nodes_by_depth(*nodes)

        for node in sorted_nodes:
            grandparent_node = node.parent.parent

            # If the node is already a direct descendant of root, don't 
            # promote.
            if grandparent_node is self:
                continue

            self.remove_node(node)
            self.append_node(grandparent_node, node)

    def _sort_nodes_by_depth(self, *nodes):
        sorted_nodes = list()

        for node in nodes:
            # Find the first node in the shortest node that is shallower than 
            # the current node (has a shorter path), and insert the current
            # node _before_ it.
            insert_index = 0
            for sorted_node in sorted_nodes:
                if len(node.path) > len(sorted_node.path):
                    insert_index = sorted_nodes.index(sorted_node)
                    break

            sorted_nodes.insert(insert_index, node)

        return sorted_nodes

    def remove(self, node_indices):
        node = self.get_node(node_indices)
        node = self.remove_node(node)

        return node

    def remove_node(self, node):
        try:
            node.parent.children.remove(node)
        except IndexError:
            raise NodeNotFoundError(node.path)

        return node

    def reorder_down(self, *nodes):
        assert nodes, "Must provide at least one node to reorder down."

        # Sort all nodes by parent.
        sorted_nodes = self._sort_nodes_by_parent(*nodes)

        # For each parent, reorder from back to the front of the list, swapping 
        # pairs of adjacent nodes when the first node is flagged to move 
        # up but the second is _not_.
        for parent_node in sorted_nodes:
            if len(parent_node.children) > 1:
                for i in reversed(range(0, len(parent_node.children) - 1)):
                    current_node = parent_node.children[i]
                    next_node = parent_node.children[i + 1]

                    if current_node in nodes and not next_node in nodes:
                        # Current node is selected to move down, while the
                        # next node is _not_. Swap the node positions.
                        parent_node.children[i] = next_node
                        parent_node.children[i + 1] = current_node

    def reorder_up(self, *nodes):
        assert nodes, "Must provide at least one node to reorder up."

        # Sort all nodes by parent.
        sorted_nodes = self._sort_nodes_by_parent(*nodes)

        # For each parent, reorder from front to back of the list, swapping 
        # pairs of adjacent nodes when the first node is _not_ flagged to move 
        # up but the second is.
        for parent_node in sorted_nodes:
            if len(parent_node.children) > 1:
                for i in range(0, len(parent_node.children) - 1):
                    current_node = parent_node.children[i]
                    next_node = parent_node.children[i + 1]

                    if not current_node in nodes and next_node in nodes:
                        # Current node is not selected to move up, while the
                        # next node is. Swap the node positions.
                        parent_node.children[i] = next_node
                        parent_node.children[i + 1] = current_node

    def _sort_nodes_by_parent(self, *nodes):
        sorted_nodes = dict()

        # Iterate over the nodes collection, adding each node to a list held
        # in the sorted nodes collection under the key of the node's parent.
        for node in nodes:
            # If a list for the node's parent hasn't been created, create one.            
            if not sorted_nodes.has_key(node.parent):
                sorted_nodes[node.parent] = list()

            sorted_nodes[node.parent].append(node)

        return sorted_nodes

    def update(self, node_indices, value):
        node = self.get_node(node_indices)

        if node is None:
            raise NodeNotFoundError(node_indices)

        node.value = value

        return node

    def _validate_reorganization_nodes(self, *nodes):
        assert nodes, "Node reorganization operations must include at least one target node."

        # Check to ensure the root node is not included in the collection of 
        # nodes to be promoted.
        if self.get_node(Tree.ROOT_PATH) in nodes:
            raise RootReorganizationError()
#------------------------------------------------------------------------------ 

class TreeNode(object):
    """Simple tree node that contains a value and allows traversal up (towards
    root), down (to children), previous and next.
    """
    def __init__(self, parent=None, path=None, value=None):
        """Create the node with a parent and option value.

        Args:
            value: The value to be stored at this tree node.
        """
        self.parent = parent
        self.path = path
        self.value = value

        self.children = list()

    def has_children(self):
        if len(self.children) > 0:
            return True
        else:
            return False

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "[Node at {path}, value: {value}]".format(path=self.path, value=self.value)
#------------------------------------------------------------------------------ 

class NodeNotFoundError(Exception):
    def __init__(self, node_path):
        Exception.__init__(self,
            "Node could not be found at path {0}".format(node_path))
#------------------------------------------------------------------------------

class DuplicateRootError(Exception):
    def __init__(self):
        Exception.__init__(self, "Cannot add another root to the tree.")
#------------------------------------------------------------------------------

class RootReorganizationError(Exception):
    def __init__(self):
        Exception.__init__(self,
            "Cannot reorganize or move the root node of the tree.")
#------------------------------------------------------------------------------

class NodeMoveTargetError(Exception):
    def __init__(self, new_parent_node, node):
        Exception.__init__(self,
            "Cannot move {parent} node to be under the descendant node {child}.".format(parent=new_parent_node, child=node))
        self.new_parent_node = new_parent_node
        self.node = node
#------------------------------------------------------------------------------

class TreePopulateTest(unittest.TestCase):
    """Test creating, populating, and addressing paths in trees."""
    def test_create_empty_tree(self):
        """Create an empty tree, lacking even a root node.

        Act:
            Create empty tree.
            Access root node (tree path "0").
        Assert:
            Tree has no children.
            Accessing path 0 (root) raises a NodeNotFoundError.
        """
        ### Act ###############################################################   
        tree = Tree()

        ### Assert ############################################################
        self.assertFalse(tree.has_path(Tree.ROOT_PATH))
        with self.assertRaises(NodeNotFoundError):
            tree.get(Tree.ROOT_PATH)

    def test_tree_insert_root(self):
        """Create a tree with only a root node.

        Arrange:
            Create a value to store (string "root").
        Act:
            Create a new tree.
            Insert value into tree at root (path 0).
        Assert:
            Tree has children.
            Root node exists (is not None) and has the expected value.
            Root node has no children.
        """
        ### Arrange ###########################################################
        expected_value = "root"

        ### Act ###############################################################   
        tree = Tree()
        root_node = tree.insert(Tree.ROOT_PATH, expected_value)

        ### Assert ############################################################
        self.assertTrue(tree.has_path(Tree.ROOT_PATH))
        self.assertEqual(expected_value, tree.get(Tree.ROOT_PATH))
        self.assertEqual(Tree.ROOT_PATH, root_node.path)

    def test_tree_node_default_value(self):
        """Create a tree with a single node, but allow default value to be
        used.

        Act:
            Create a new tree.
            Insert into tree at path 0, without providing a value.
        Assert:
            Root node exists (is not None) and has the expected default value
            of None.
        """
        ### Act ###############################################################   
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)

        ### Assert ############################################################
        self.assertIsNone(tree.get(Tree.ROOT_PATH))

    def test_tree_insert_root_twice(self):
        """Ensure tree raises DuplicateRootError if there are more than one root node
        insert requests.

        Arrange:
            Create a tree with a root node.
        Act,Assert:
            Inserting second node (at "0") raises DuplicateRootError. (specific type of
            exception?)
        """
        ### Arrange ###########################################################
        tree = Tree()
        tree.insert(Tree.ROOT_PATH, None)

        ### Assert ############################################################
        with self.assertRaises(DuplicateRootError):
            tree.insert(Tree.ROOT_PATH, None)

    def test_create_three_node_tree(self):
        """Create a tree with the following architecture:
        - N0
            - N0:0
            - N0:1

        Arrange:
            Create values to store in the two level-1 nodes (use tree path as
            expected value).
        Act:
            Create a new tree.
            Create a root node, store no value.
            Create two nodes below root, with expected values.
        Assert:
            Root node has children.
            Paths 0:0, 0:1 retrieve expected values.
        """
        ### Arrange ###########################################################
        n0_0_path = Tree.ROOT_PATH + (0,)
        n0_1_path = Tree.ROOT_PATH + (1,)

        ### Act ###############################################################
        tree = Tree()
        tree.insert(Tree.ROOT_PATH, None)
        tree.insert(n0_0_path, n0_0_path)
        tree.insert(n0_1_path, n0_1_path)

        ### Assert ############################################################
        self.assertTrue(tree.has_children(Tree.ROOT_PATH))
        self.assertEqual(n0_0_path, tree.get(n0_0_path))
        self.assertEqual(n0_1_path, tree.get(n0_1_path))

    def test_build_path_from_str_no_args(self):
        """Test building a list of path indices from a string path
        representation.

        The result should be a path with a single index that points to the
        root node.

        Arrange:
            Create the expected path tuple (0,).
        Act:
            Generate a path without any arguments.
        Assert:
            The generated path equals the root path: 0.
        """
        ### Arrange ###########################################################
        expected_root_path = Tree.ROOT_PATH

        ### Act ###############################################################   
        actual_root_path = Tree.build_path_from_str()

        ### Assert ############################################################
        self.assertEqual(expected_root_path, actual_root_path)

    def test_build_path_from_str_three_indices(self):
        """Test building a path indices list from a string path
        representing a third-level node.

        The result should be a tuple with four indices.

        Arrange:
            Create the expected path tuple ([0, 1, 3, 4]).
        Act:
            Generate a path list from the string "1:3:4".
        Assert:
            The generated path list equals [0, 1, 3, 4].
        """
        ### Arrange ###########################################################
        expected_leaf_path = (0, 1, 3, 4)

        ### Act ###############################################################   
        actual_leaf_path = Tree.build_path_from_str("1:3:4")

        ### Assert ############################################################
        self.assertEqual(expected_leaf_path, actual_leaf_path)

    def test_build_str_from_path_no_args(self):
        """Test building a string from a path without any arguments.

        The result should be a path string that points to the root node.

        Arrange:
            Create the expected path string.
        Act:
            Generate a path without any arguments.
        Assert:
            The generated path equals the root path: 0.
        """
        ### Arrange ###########################################################
        expected_root_path = "0"

        ### Act ###############################################################   
        actual_root_path = Tree.build_str_from_path()

        ### Assert ############################################################
        self.assertEqual(expected_root_path, actual_root_path)

    def test_build_str_from_path_three_levels(self):
        """Assert that building a path string with arguments creates the
        expected node address(es), and that the address generated includes
        an implied root node address.

        Arrange:
            Create the expected path string.
        Act:
            Generate a path string for a path with three indices (plus implied
            root).
        Assert:
            The resulting path includes all three arguments, properly
            separated (":"), and prefixed by the root node address.
        """
        ### Arrange ###########################################################
        expected_path = "0:1:3:4"

        ### Act ###############################################################   
        actual_path = Tree.build_str_from_path(1, 3, 4)

        ### Assert ############################################################
        self.assertEqual(expected_path, actual_path)

    def test_move_node_noop(self):
        """Test moving a leaf node to the same position it already occupies.

        Test tree architecture:
        - 0
            - 0:0

        Arrange:
            Create blank tree.
            Create root node.
            Create leaf node.
        Act:
            Move leaf node to the same position it's already in.
        Assert:
            Leaf node is still in position 0,0.
        """
        ### Arrange ###
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)
        leaf_node_path = Tree.ROOT_PATH + (0,)
        leaf_node = tree.insert(leaf_node_path)

        ### Act ###
        tree.move_node(tree.get_node(Tree.ROOT_PATH), leaf_node)

        ### Assert ###
        self.assertEqual(leaf_node, tree.get_node(leaf_node_path))

    def test_move_node_root(self):
        """Test moving the root of a tree.

        Test tree architecture:
        - 0

        Arrange:
            Create blank tree.
            Create root node.
        Assert:
            Attempting a move operation on the root node raises an error.
        """
        ### Arrange ###
        tree = Tree()
        root = tree.insert(Tree.ROOT_PATH)

        ### Assert ###        
        with self.assertRaises(RootReorganizationError):
            tree.move_node(Tree.ROOT_PATH, root)

    def test_move_node_leaf(self):
        """Test moving a leaf node.

        Test tree architecture:
        - root
            - A
                -B

        Arrange:
            Create blank tree.
            Create root,A,B nodes.
        Act:
            Move node B to be direct child of root.
        Assert:
            Node B's parent is root.
            Node B's path is updated (0,1).
            Node at (0,1) is node B.
        """
        ### Arrange ###
        tree = Tree()
        root = tree.insert(Tree.ROOT_PATH)
        node_a = tree.append(root, "A")
        node_b = tree.append(node_a, "B")

        ### Act ###
        tree.move_node(root, node_b)

        ### Assert ###
        self.assertEqual(root, node_b.parent)
        self.assertEqual((0, 1), node_b.path)
        self.assertEqual(node_b, tree.get_node((0, 1)))

    def test_move_node_descendant(self):
        """Test moving a branch node to one of its descendants.

        Test tree architecture:
        - root
            - A
                - B

        Arrange:
            Create blank tree.
            Create root,A,B nodes.
        Assert:
            Attempting to move node A to be a child of B raises an error.
        """
        ### Arrange ###
        tree = Tree()
        root = tree.insert(Tree.ROOT_PATH)
        node_a = tree.append(root, "A")
        node_b = tree.append(node_a, "B")

        ### Assert ###
        with self.assertRaises(NodeMoveTargetError):
            tree.move_node(node_b, node_a)

    def test_remove_leaf(self):
        """Test removing a leaf node (via remove).

        Test tree architecture:
        - 0
            - 0:0

        Arrange:
            Create blank tree.
            Create root node.
            Create leaf node.
        Act:
            Remove leaf node.
        Assert:
            Accessing leaf node raises NodeNotFoundError.
            Root node no longer has children.
        """
        ### Arrange ###########################################################
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)
        leaf_node_path = Tree.ROOT_PATH + (0,)
        tree.insert(leaf_node_path)

        ### Act ###############################################################   
        tree.remove(leaf_node_path)

        ### Assert ############################################################
        with self.assertRaises(NodeNotFoundError):
            tree.get(leaf_node_path)
        self.assertFalse(tree.has_children(Tree.ROOT_PATH))

    def test_remove_node_leaf(self):
        """Test removing a leaf node (via remove_node).

        Test tree architecture:
        - 0
            - 0:0

        Arrange:
            Create blank tree.
            Create root node.
            Create leaf node.
        Act:
            Remove leaf node.
        Assert:
            Accessing leaf node raises NodeNotFoundError.
            Root node no longer has children.
        """
        ### Arrange ###########################################################
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)
        leaf_node_path = Tree.ROOT_PATH + (0,)
        tree.insert(leaf_node_path)

        ### Act ###############################################################   
        leaf_node = tree.get_node(leaf_node_path)
        tree.remove_node(leaf_node)

        ### Assert ############################################################
        with self.assertRaises(NodeNotFoundError):
            tree.get(leaf_node_path)
        self.assertFalse(tree.has_children(Tree.ROOT_PATH))

    def test_remove_root(self):
        """Test removing the root node of a tree with a leaf node.

        Test tree architecture:
        - 0
            - 0:0

        Arrange:
            Create blank tree.
            Create root node.
            Create leaf node.
        Act:
            Remove root node.
        Assert:
            Accessing leaf node raises NodeNotFoundError.
            Accessing root node raises NodeNotFoundError.
        """
        ### Arrange ###########################################################
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)
        tree.insert(Tree.ROOT_PATH + (0,))

        ### Act ###############################################################   
        tree.remove(Tree.ROOT_PATH)

        ### Assert ############################################################
        with self.assertRaises(NodeNotFoundError):
            tree.get(Tree.ROOT_PATH + (0,))
            tree.get(Tree.ROOT_PATH)

    def test_remove_nonexistent_node(self):
        """Test removing a nonexistent node.

        This should cause an error to be raised.

        Test tree architecture:
        - 0

        Arrange:
            Create blank tree.
            Create root node.
        Assert:
            Removing nonexistent node raises NodeNotFoundError.
        """
        ### Arrange ###########################################################
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)

        ### Assert ############################################################
        with self.assertRaises(NodeNotFoundError):
            tree.remove(Tree.ROOT_PATH + (0,))

    def test_set_nonexistent_node(self):
        """Test setting the value on a nonexistent node.

        This should cause an error to be raised.

        Test tree architecture:
        - 0

        Arrange:
            Create blank tree.
            Create root node.
        Assert:
            Setting a value on a nonexistent node raises NodeNotFoundError.
        """
        ### Arrange ###########################################################
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)

        ### Assert ############################################################
        with self.assertRaises(NodeNotFoundError):
            tree.update(Tree.ROOT_PATH + (0,), None)

    def test_set_node_value(self):
        """Test setting a node's value.

        Arrange:
            Create blank tree.
            Create root node.
            Create expected value of "root".
        Act:
            Store initial value of root node (should be default insert value).
            Set value of root node to expected value "root".
        Assert:
            Root node contains expected value.
        """
        ### Arrange ###########################################################
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)
        expected_value = "root"

        ### Act ###############################################################   
        tree.get(Tree.ROOT_PATH)
        tree.update(Tree.ROOT_PATH, expected_value)

        ### Assert ############################################################
        self.assertEqual(expected_value, tree.get(Tree.ROOT_PATH))

    def test_has_path_existing_node(self):
        """Test if the tree recognizes a valid node address.

        Arrange:
            Create blank tree.
            Create root node (with the default value).
        Assert:
            Tree reports it does have a node at the root node path.
        """
        ### Arrange ###########################################################
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)

        ### Assert ############################################################
        self.assertTrue(tree.has_path(Tree.ROOT_PATH))

    def test_has_path_nonexistent_node(self):
        """Test if the tree recognizes an invalid node address.

        Arrange:
            Create blank tree.
            Create root node.
        Assert:
            Tree reports it _does not_ have node at the node path 0:0.
        """
        ### Arrange ###########################################################
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)
        nonexistent_leaf_path = Tree.ROOT_PATH + (0,)

        ### Assert ############################################################
        self.assertFalse(tree.has_path(nonexistent_leaf_path))

    def test_has_children_childless_node(self):
        """Test if the tree recognizes a childless node.

        Arrange:
            Create blank tree.
            Create root node.
        Assert:
            Tree reports the root node _does not_ have children.
        """
        ### Arrange ###########################################################
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)

        ### Assert ############################################################
        self.assertFalse(tree.has_children(Tree.ROOT_PATH))

    def test_has_children_parent_node(self):
        """Test if the tree recognizes a parent (with children) node.

        Arrange:
            Create blank tree.
            Create root node.
            Create a leaf node child of the root.
        Assert:
            Tree reports the root node does have children.
        """
        ### Arrange ###########################################################
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)
        tree.insert(Tree.ROOT_PATH + (0,))

        ### Assert ############################################################
        self.assertTrue(tree.has_children(Tree.ROOT_PATH))

    def test_has_siblings_only_child_node(self):
        """Test if the tree recognizes a node lacking siblings.

        Arrange:
            Create blank tree.
            Create root node.
            Create a leaf node child of the root.
        Assert:
            Tree reports the leaf node _does not_ have siblings.
        """
        ### Arrange ###########################################################
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)
        leaf_node_address = Tree.ROOT_PATH + (0,)
        tree.insert(leaf_node_address)

        ### Assert ############################################################
        self.assertFalse(tree.has_siblings(leaf_node_address))

    def test_has_siblings_node_with_siblings(self):
        """Test if the tree recognizes a node with siblings.

        Arrange:
            Create blank tree.
            Create root node.
            Create a two leaf node children of the root.
        Assert:
            Tree reports that both leaf nodes do have siblings.
        """
        ### Arrange ###########################################################
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)
        n0_0_path = Tree.ROOT_PATH + (0,)
        n0_1_path = Tree.ROOT_PATH + (1,)
        tree.insert(n0_0_path)
        tree.insert(n0_1_path)

        ### Assert ############################################################
        self.assertTrue(tree.has_siblings(n0_0_path))
        self.assertTrue(tree.has_siblings(n0_1_path))

    def test_insert_occupied_position(self):
        """Ensure inserting into an occupied position bumps up the current
        occupant node into the next higher position.

        Initial tree:
        - None
            - val 1

        Expected result tree:
        - None
            - val 2
            - val 1

        Arrange:
            Create blank tree.
            Create root node.
            Create expected values for the two leaf children.
        Act:
            Insert leaf child at position 0:0 with value val 1.
            Insert leaf child at position 0:0 with value val 2.
        Assert:
            The node at position 0:0 has value val 2.
            The node at position 0:1 has value val 1.
            Nodes at positions 0:0,0:1 have updated paths.
        """
        ### Arrange ###########################################################
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)
        n0_0_path = Tree.ROOT_PATH + (0,)
        n0_1_path = Tree.ROOT_PATH + (1,)
        expected_val_1 = "val 1"
        expected_val_2 = "val 2"

        ### Act ###############################################################
        tree.insert(n0_0_path, expected_val_1)
        tree.insert(n0_0_path, expected_val_2)

        ### Assert ############################################################
        self.assertEqual(expected_val_2, tree.get(n0_0_path))
        self.assertEqual(expected_val_1, tree.get(n0_1_path))
        self.assertEqual(n0_0_path, tree.get_node(n0_0_path).path)
        self.assertEqual(n0_1_path, tree.get_node(n0_1_path).path)

    def test_insert_position_out_of_bounds(self):
        """Ensure inserting into an "out of bounds" position raises an error.

        An "out of bounds" position is higher than the number of children (as
        the index starts at 0), or a negative number.

        Arrange:
            Create blank tree.
            Create root node.
            Create leaf node.
        Assert:
            Inserting a node at a negative position raises an IndexError.
            Inserting a node at position 0:2 (when there is only one other child
            node) raises an IndexError.
        """
        ### Arrange ###
        tree = Tree()
        tree.insert(Tree.ROOT_PATH, "root")
        tree.insert(Tree.ROOT_PATH + (0,), "0:0")

        ### Assert ###
        with self.assertRaises(IndexError):
            tree.insert(Tree.ROOT_PATH + (-1,), "0:-1")
            tree.insert(Tree.ROOT_PATH + (2,), "0:2")

    def test_insert_root_sibling(self):
        """Ensure inserting a sibling to the root node causes a failure.

        Arrange:
            Create blank tree.
            Create root node.
        Assert:
            Inserting a node at position 1 (would be a sibling to the root
            node) raises an IndexError.
        """
        ### Arrange ###
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)

        ### Assert ###
        with self.assertRaises(DuplicateRootError):
            tree.insert((1,))

    def test_append_root(self):
        """Append a root element to an empty tree.

        Arrange:
            Create blank tree.
        Act:
            Append new node to tree without specifying a path (creating a root
            node).
        Assert:
            The tree now has a root node with the expected value.
        """
        ### Arrange ###
        tree = Tree()
        expected_value = "root"

        ### Act ###
        tree.append((), expected_value)

        ### Assert ###
        self.assertTrue(tree.has_path(Tree.ROOT_PATH))
        self.assertEqual(expected_value, tree.get(Tree.ROOT_PATH))

    def test_append_second_root(self):
        """Append another root element to a populated tree.

        Arrange:
            Create blank tree.
            Append a root node.
        Assert:
            Verifying that appending a second root node to the tree raises an
            error.
        """
        ### Arrange ###
        tree = Tree()
        expected_value = "root"

        ### Act ###
        tree.append((), expected_value)

        ### Assert ###
        self.assertTrue(tree.has_path(Tree.ROOT_PATH))
        self.assertEqual(expected_value, tree.get(Tree.ROOT_PATH))

    def test_append_small_tree(self):
        """Use append to build a small, populated tree.

        Attempting to create this tree:
        - N0
            - N1
                - N1.1
                - N1.2
            - N2

        Arrange:
            Create blank tree.
        Act:
            Append nodes to create small tree.
        Assert:
            Verifying that appending a second root node to the tree raises an
            error.
        """
        ### Arrange ###
        tree = Tree()
        root_value = "n0"
        n1_value = "n1"
        n1_1_value = "n1_1"
        n1_2_value = "n1_2"
        n1_3_value = "n1_3"
        n2_value = "n2"

        ### Act ###        
        root = tree.append(None, root_value)

        n1 = tree.append(root, n1_value)
        tree.append(n1, n1_1_value)
        tree.append(n1, n1_2_value)
        tree.append(n1, n1_3_value)

        tree.append(root, n2_value)

        ### Assert ###
        self.assertEqual(root_value, tree.get((0,)))
        self.assertEqual(n1_value, tree.get((0, 0)))
        self.assertEqual(n1_1_value, tree.get((0, 0, 0)))
        self.assertEqual(n1_2_value, tree.get((0, 0, 1)))
        self.assertEqual(n1_3_value, tree.get((0, 0, 2)))
        self.assertEqual(n2_value, tree.get((0, 1)))

    def test_append_node_small_tree(self):
        """Use append to build a small, populated tree using append_node.

        Attempting to create this tree:
        - N0
            - N1
            - N2

        Arrange:
            Create blank tree.
        Act:
            Append nodes to create small tree.
        Assert:
            Verifying that appending a second root node to the tree raises an
            error.
        """
        ### Arrange ###
        tree = Tree()
        root_value = "n0"
        n1_value = "n1"
        n2_value = "n2"

        ### Act ###        
        root = tree.append_node(None, TreeNode(value=root_value))

        tree.append_node(root, TreeNode(value=n1_value))
        tree.append_node(root, TreeNode(value=n2_value))

        ### Assert ###
        self.assertEqual(root_value, tree.get((0,)))
        self.assertEqual(n1_value, tree.get((0, 0)))
        self.assertEqual(n2_value, tree.get((0, 1)))
#------------------------------------------------------------------------------

class BaseTreeReorganizationTest(unittest.TestCase):
    def tearDown(self):
        del self.tree
#------------------------------------------------------------------------------ 

class TreeReorderTest(BaseTreeReorganizationTest):
    """
    Assume the following tree for this test case group:
    - root
        - A
            - C
            - D
            - E
        - B
    """
    def setUp(self):
        """Create a simple tree, as outlined in the class docstring."""
        self.tree = Tree()

        self.root = self.tree.append(None, "root")

        self.node_a = self.tree.append(self.root, "A")
        self.node_c = self.tree.append(self.node_a, "C")
        self.node_d = self.tree.append(self.node_a, "D")
        self.node_e = self.tree.append(self.node_a, "E")

        self.node_b = self.tree.append(self.root, "B")

    def test_reorder_up_noop(self):
        """Attempt to reorder up a node that is already at the front of the
        sibling group.

        Act:
            Reorder up node C.
        Assert:
            Node C is still at the front of the list.
        """
        ### Act ###
        actual_node_c = self.tree.get_node(self.node_c.path)
        self.tree.reorder_up(actual_node_c)

        ### Assert ###
        self.assertIs(self.node_c, self.tree.get_node((0, 0, 0)))

    def test_reorder_down_noop(self):
        """Attempt to reorder down a node that is already at the back of the
        sibling group.

        Act:
            Reorder down node E.
        Assert:
            Node E is still at the back of the list.
        """
        ### Act ###
        actual_node_e = self.tree.get_node(self.node_e.path)
        self.tree.reorder_down(actual_node_e)

        ### Assert ###
        self.assertIs(self.node_e, self.tree.get_node((0, 0, 2)))

    def test_reorder_up_single(self):
        """Attempt to reorder up a node that is in the middle of the
        sibling group.

        Act:
            Reorder up node D.
        Assert:
            Node D is at the front of the list (0,0,0).
            Node C is in the middle of the list (0,0,1).
        """
        ### Act ###
        actual_node_d = self.tree.get_node(self.node_d.path)
        self.tree.reorder_up(actual_node_d)

        ### Assert ###
        self.assertEqual(self.node_d, self.tree.get_node((0, 0, 0)))
        self.assertEqual(self.node_c, self.tree.get_node((0, 0, 1)))

    def test_reorder_down_single(self):
        """Attempt to reorder down a node that is in the middle of the
        sibling group.

        Act:
            Reorder down node D.
        Assert:
            Node E is in the middle of the list (0,0,1).
            Node D is at the back of the list (0,0,2).
        """
        ### Act ###
        actual_node_d = self.tree.get_node(self.node_d.path)
        self.tree.reorder_down(actual_node_d)

        ### Assert ###
        self.assertEqual(self.node_e, self.tree.get_node((0, 0, 1)))
        self.assertEqual(self.node_d, self.tree.get_node((0, 0, 2)))

    def test_reorder_up_multiple_all_move(self):
        """Attempt to reorder up all nodes within a sibling group.

        Act:
            Reorder up nodes C,D,E.
        Assert:
            Node order remains the same (C,D,E are at expected and original
            addresses).
        """
        ### Act ###
        actual_c_node = self.tree.get_node(self.node_c.path)
        actual_d_node = self.tree.get_node(self.node_d.path)
        actual_e_node = self.tree.get_node(self.node_e.path)
        self.tree.reorder_up(actual_c_node, actual_d_node, actual_e_node)

        ### Assert ###
        self.assertEqual(self.node_c, self.tree.get_node((0, 0, 0)))
        self.assertEqual(self.node_d, self.tree.get_node((0, 0, 1)))
        self.assertEqual(self.node_e, self.tree.get_node((0, 0, 2)))

    def test_reorder_down_multiple_all_move(self):
        """Attempt to reorder down all nodes within a sibling group.

        Act:
            Reorder down nodes C,D,E.
        Assert:
            Node order remains the same (C,D,E are at expected and original
            addresses).
        """
        ### Act ###
        actual_c_node = self.tree.get_node(self.node_c.path)
        actual_d_node = self.tree.get_node(self.node_d.path)
        actual_e_node = self.tree.get_node(self.node_e.path)
        self.tree.reorder_down(actual_c_node, actual_d_node, actual_e_node)

        ### Assert ###
        self.assertEqual(self.node_c, self.tree.get_node((0, 0, 0)))
        self.assertEqual(self.node_d, self.tree.get_node((0, 0, 1)))
        self.assertEqual(self.node_e, self.tree.get_node((0, 0, 2)))

    def test_reorder_up_multiple_some_move(self):
        """Attempt to reorder up some nodes from within the same sibling group.

        Act:
            Reorder up nodes D,E.
        Assert:
            Node order is now D,E,C.
        """
        ### Act ###
        actual_d_node = self.tree.get_node(self.node_d.path)
        actual_e_node = self.tree.get_node(self.node_e.path)
        self.tree.reorder_up(actual_d_node, actual_e_node)

        ### Assert ###
        self.assertEqual(self.node_d, self.tree.get_node((0, 0, 0)))
        self.assertEqual(self.node_e, self.tree.get_node((0, 0, 1)))
        self.assertEqual(self.node_c, self.tree.get_node((0, 0, 2)))

    def test_reorder_down_multiple_some_move(self):
        """Attempt to reorder down some nodes from within the same sibling
        group.

        Act:
            Reorder down nodes C,D.
        Assert:
            Node order is now E,C,D.
        """
        ### Act ###
        actual_c_node = self.tree.get_node(self.node_c.path)
        actual_d_node = self.tree.get_node(self.node_d.path)
        self.tree.reorder_down(actual_c_node, actual_d_node)

        ### Assert ###
        self.assertEqual(self.node_e, self.tree.get_node((0, 0, 0)))
        self.assertEqual(self.node_c, self.tree.get_node((0, 0, 1)))
        self.assertEqual(self.node_d, self.tree.get_node((0, 0, 2)))

    def test_reorder_up_multiple_different_parents(self):
        """Attempt to reorder up a group of nodes from different parents.

        Act:
            Reorder up nodes B,D.
        Assert:
            Node order below root is now B,A.
            Node order below A is now D,C,E.
        """
        ### Act ###
        actual_b_node = self.tree.get_node(self.node_b.path)
        actual_d_node = self.tree.get_node(self.node_d.path)
        self.tree.reorder_up(actual_b_node, actual_d_node)

        ### Assert ###
        self.assertEqual(self.node_b, self.tree.get_node((0, 0)))
        self.assertEqual(self.node_a, self.tree.get_node((0, 1)))

        self.assertEqual(self.node_d, self.tree.get_node((0, 1, 0)))
        self.assertEqual(self.node_c, self.tree.get_node((0, 1, 1)))
        self.assertEqual(self.node_e, self.tree.get_node((0, 1, 2)))

    def test_reorder_down_multiple_different_parents(self):
        """Attempt to reorder down a group of nodes from different parents.

        Act:
            Reorder down nodes A,D.
        Assert:
            Node order below root is now B,A.
            Node order below A is now C,E,D.
        """
        ### Act ###
        actual_a_node = self.tree.get_node(self.node_a.path)
        actual_d_node = self.tree.get_node(self.node_d.path)
        self.tree.reorder_down(actual_a_node, actual_d_node)

        ### Assert ###
        self.assertEqual(self.node_b, self.tree.get_node((0, 0)))
        self.assertEqual(self.node_a, self.tree.get_node((0, 1)))

        self.assertEqual(self.node_c, self.tree.get_node((0, 1, 0)))
        self.assertEqual(self.node_e, self.tree.get_node((0, 1, 1)))
        self.assertEqual(self.node_d, self.tree.get_node((0, 1, 2)))
#------------------------------------------------------------------------------

class TreePromoteTest(unittest.TestCase):
    """Test the promotion functions of the Tree class with a simple tree
    architecture where no nodes have siblings.

    Assume the following tree for this test case group:
    - root
        - A
            - B
                - C
                    - D
                        - E
    """
    def setUp(self):
        """Create a simple tree, as outlined in the class docstring."""
        self.tree = Tree()

        self.root = self.tree.append(None, "root")

        self.node_a = self.tree.append(self.root, "A")
        self.node_b = self.tree.append(self.node_a, "B")
        self.node_c = self.tree.append(self.node_b, "C")
        self.node_d = self.tree.append(self.node_c, "D")
        self.node_e = self.tree.append(self.node_d, "E")

    def test_promote_noop(self):
        """Test promoting node A.

        This should result in a no-op, as node A is already directly beneath
        the root node.

        Act:
            Promote node A.
        Assert:
            Node A is still directly below root (0,0).
        """
        ### Act ###
        actual_node_a = self.tree.get_node(self.node_a.path)
        self.tree.promote(actual_node_a)

        ### Assert ###
        self.assertEqual(self.node_a, self.tree.get_node((0, 0)))

    def test_promote_root(self):
        """Test promoting the root node.

        This should result in an error, as the root node is not allowed to be
        promoted.

        Assert:
            Promoting root node causes RootReorganizationError.
        """
        ### Assert ###
        with self.assertRaises(RootReorganizationError):
            self.tree.promote(self.root)

    def test_promote_single_node(self):
        """Test promoting node B.

        This should result in node B being a sibling of node A (directly under
        root) and ordered below A.

        Resulting tree architecture:
        - root
            - A
            - B
                - C
                    - D
                        - E

        Act:
            Promote node B
        Assert:
            Node A is still directly below root and in the first position
            (0,0).
            Node B is directly below root in the second position, behind
            node A (0,1).
            Node C is a direct child of B (0,1,0).
        """
        ### Act ###
        actual_node_b = self.tree.get_node(self.node_b.path)
        self.tree.promote(actual_node_b)

        ### Assert ###
        self.assertEqual(self.node_a, self.tree.get_node((0, 0)))
        self.assertEqual(self.node_b, self.tree.get_node((0, 1)))
        self.assertEqual(self.node_c, self.tree.get_node((0, 1, 0)))

    def test_promote_multiple_adjacent_nodes(self):
        """Test promoting nodes C,D.

        This should result in nodes B and C being siblings directly under A,
        with C ordered after B. D should be a direct child of B.

        Resulting tree architecture:
        - root
            - A
                - B
                    - D
                        - E
                - C

        Act:
            Promote nodes C,D.
        Assert:
            Node B is still directly below A and in the first position
            (0,0,0).
            Node C is directly below A in the second position, behind
            node B (0,0,1).
            Node D is a direct child of B (0,1,0,0).
        """
        ### Act ###
        actual_node_c = self.tree.get_node(self.node_c.path)
        actual_node_d = self.tree.get_node(self.node_d.path)
        self.tree.promote(actual_node_c, actual_node_d)

        ### Assert ###
        self.assertEqual(self.node_b, self.tree.get_node((0, 0, 0)))
        self.assertEqual(self.node_c, self.tree.get_node((0, 0, 1)))
        self.assertEqual(self.node_d, self.tree.get_node((0, 0, 0, 0)))

    def test_promote_multiple_separate_nodes(self):
        """Test promoting nodes C,E.

        This should result in nodes B and C being siblings directly under A,
        with C ordered after B. Nodes D and E should be a direct childredn of
        C, with E ordered after D.

        Resulting tree architecture:
        - root
            - A
                - B
                - C
                    - D
                    - E

        Act:
            Promote nodes C,D.
        Assert:
            Node B is still directly below A and in the first position
            (0,0,0).
            Node C is directly below A in the second position, behind
            node B (0,0,1).
            Node D is a direct child of B (0,1,0,0).
        """
        ### Act ###
        actual_node_c = self.tree.get_node(self.node_c.path)
        actual_node_e = self.tree.get_node(self.node_e.path)
        self.tree.promote(actual_node_c, actual_node_e)

        ### Assert ###
        self.assertEqual(self.node_c, self.tree.get_node((0, 0, 1)))
        self.assertEqual(self.node_d, self.tree.get_node((0, 0, 1, 0)))
        self.assertEqual(self.node_e, self.tree.get_node((0, 0, 1, 1)))
#------------------------------------------------------------------------------ 

class TreeDemoteTest(BaseTreeReorganizationTest):
    """Test the demotion functions of the Tree class with a simple, multi-level
    tree.

    Assume the following tree for this test case group:
    - root
        - A
            - C
            - D
            - E
        - B
            - F
            - G
    """
    def setUp(self):
        """Create a simple tree, as outlined in the class docstring."""
        self.tree = Tree()

        self.root = self.tree.append(None, "root")

        self.node_a = self.tree.append(self.root, "A")
        self.node_c = self.tree.append(self.node_a, "C")
        self.node_d = self.tree.append(self.node_a, "D")
        self.node_e = self.tree.append(self.node_a, "E")

        self.node_b = self.tree.append(self.root, "B")
        self.node_f = self.tree.append(self.node_b, "F")
        self.node_g = self.tree.append(self.node_b, "G")

    def test_demote_noop(self):
        """Test demoting node C.

        This should result in a no-op, as node C has no siblings below which it
        can be demoted.

        Act:
            Demote node C.
        Assert:
            Node C is still directly below node A, and in the first position
            (0,0,1).
        """
        ### Act ###
        actual_node_c = self.tree.get_node(self.node_c.path)
        self.tree.demote(actual_node_c)

        ### Assert ###
        self.assertEqual(self.node_c, self.tree.get_node((0, 0, 0)))

    def test_demote_root(self):
        """Test demoting the root node.

        This should result in an error being raised, as no reorganization
        operations are allowed on the root node.

        Assert:
            That demoting the root node raises a RootReorganizationError.
        """
        ### Assert ###
        with self.assertRaises(RootReorganizationError):
            self.tree.demote(self.root)

    def test_demote_single(self):
        """Test demoting node D.

        This should result in node D becoming a child of node C.

        Act:
            Demote node D.
        Assert:
            Node D is directly below node C (0,0,0,0).
            Node at (0,0,0,0) (which should be D) has correct path (0,0,0,0).
        """
        ### Act ###
        actual_node_d = self.tree.get_node(self.node_d.path)
        self.tree.demote(actual_node_d)

        ### Assert ###
        self.assertEqual(self.node_d, self.tree.get_node((0, 0, 0, 0)))
        self.assertEqual((0, 0, 0, 0), self.tree.get_node((0, 0, 0, 0)).path)

    def test_demote_multiple_full_sibling_group(self):
        """Test demoting nodes C,D,E.

        This should result should be a no-op, as those are all of the nodes in
        their sibling group.

        Act:
            Demote nodes C,D,E.
        Assert:
            Node C hasn't moved (0,0,0).
            Node at (0,0,0) has correct path.
            Node D hasn't moved (0,0,1).
            Node at (0,0,1) has correct path.
            Node E hasn't moved (0,0,2).
            Node at (0,0,2) has correct path.
        """
        ### Act ###
        actual_node_c = self.tree.get_node(self.node_c.path)
        actual_node_d = self.tree.get_node(self.node_d.path)
        actual_node_e = self.tree.get_node(self.node_e.path)
        self.tree.demote(actual_node_c, actual_node_d, actual_node_e)

        ### Assert ###
        self.assertEqual(self.node_c, self.tree.get_node((0, 0, 0)))
        self.assertEqual((0, 0, 0), self.tree.get_node((0, 0, 0)).path)

        self.assertEqual(self.node_d, self.tree.get_node((0, 0, 1)))
        self.assertEqual((0, 0, 1), self.tree.get_node((0, 0, 1)).path)

        self.assertEqual(self.node_e, self.tree.get_node((0, 0, 2)))
        self.assertEqual((0, 0, 2), self.tree.get_node((0, 0, 2)).path)

    def test_demote_multiple_different_sibling_groups(self):
        """Test demoting nodes C,E,G.

        This should causes a no-op on C, E to be demoted below D, and G to be
        demoted below F.

        Expected result tree architecture:
        - root
            - A
                - C
                - D
                    - E
            - B
                - F
                    - G

        Act:
            Demote nodes C,E,G.
        Assert:
            Node C hasn't moved (0,0,0).
            Node E is direct child of D (0,0,1,0)
            Node G is direct child of F (0,1,0,0)
        """
        ### Act ###
        actual_node_c = self.tree.get_node(self.node_c.path)
        actual_node_e = self.tree.get_node(self.node_e.path)
        actual_node_g = self.tree.get_node(self.node_g.path)
        self.tree.demote(actual_node_c, actual_node_e, actual_node_g)

        ### Assert ###
        self.assertEqual(self.node_c, self.tree.get_node((0, 0, 0)))
        self.assertEqual(self.node_e, self.tree.get_node((0, 0, 1, 0)))
        self.assertEqual(self.node_g, self.tree.get_node((0, 1, 0, 0)))
#------------------------------------------------------------------------------ 
