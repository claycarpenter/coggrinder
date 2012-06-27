'''
Created on Apr 11, 2012

@author: Clay Carpenter
'''

import unittest
from unittest import skip
from coggrinder.core.comparable import DeclaredPropertiesComparable
from coggrinder.core.test import USE_CASE_DEPRECATED
import copy

class TreeNode(DeclaredPropertiesComparable):
    """Simple tree node that contains an arbitrary value and allows 
    traversal up (towards root) and down (to children).
    
    The parent node (node above) the node is referred to in the parent
    property. The nodes belonging to this node are held in the children 
    collection. The root node of a tree should contain a None value for the 
    parent reference, and should be the only node in that tree with such a 
    reference. 
    """
    def __init__(self, parent=None, child_index=None, value=None):
        """Create the node with a parent and option value.

        Args:
            parent: The parent TreeNode of this node, or None if the parent
                is the Tree itself (i.e., this is the root node).
            value: The value to be stored at this tree node.
        """
            
        self.value = value
        self.children = list()
        
        self.parent = None
        if parent is not None:
            parent.add_child(self, child_index=child_index)
            
    @property
    def path(self):
        if self.parent is None:
            # Special case for root.
            return ()
        
        # Must try to identify child position via instance identity rather
        # than using list.index() because it appears that the index() method
        # uses equality for testing, which then creates a recursive loop when
        # comparing the path property of two nodes.
        for i in range(0, len(self.parent.children)):
            child = self.parent.children[i]
            if child is self:
                node_index = i
                break
        else:
            raise NodeRelationshipError(parent_node=self.parent)
        
        return self.parent.path + (node_index,)

    @property
    def child_index(self):
        try:
            return self.parent.children.index(self)
        except AttributeError:
            # Parent hasn't been defined yet, therefore simply return None.
            return None
    
    """
    TODO: This lacks test coverage.
    """
    @property
    def child_values(self):
        return [x.value for x in self.children]
    
    @property
    def descendants(self):
        return self._collect_descendants(self)
    
    @staticmethod
    def _collect_descendants(node):
        descendants = list()
        
        # Collect any children and (recursively) any descendants of 
        # those children.
        for child in node.children:
            descendants.append(child)
            
            descendants.extend(child.descendants)
        
        return descendants
    
    def add_child(self, child, child_index=None):
        # Ensure that the value of that the child node contains is not 
        # already in another of this node's children.
        if not child.value in self.child_values:
            # Insert child into the children list.
            if child_index is None:
                self.children.append(child)
            else:
                # This pushes down the node at the indicated child index, if
                # it exists.
                self.children.insert(child_index, child)
        
        # Link the child node to this node.
        child.parent = self
        
        return child
    
    def attach_to_parent(self, parent, child_index=None):
        parent.add_child(self, child_index=child_index)
        
    def has_children(self):
        if self.children:
            return True
        else:
            return False

    def _get_comparable_properties(self):
        return ("parent", "path", "value", "children")

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        try:
            path = self.path
        except NodeRelationshipError as node_rel_err:
            path = "(error in {ancestor})".format(ancestor=node_rel_err.parent_node)
            
        return "<Node at {path}; value: {value}>".format(path=path, value=self.value)
#------------------------------------------------------------------------------ 

class TreeNodeTest(unittest.TestCase):
    def test_descendants_empty_tree(self):
        """Test that the descendants property of a child-less TreeNode 
        produces an empty collection.
        
        Arrange:
            - Create a child-less TreeNode.
        Assert:
            - That the actual descendants equals an empty list.
        """
        ### Arrange ###
        childless_treenode = TreeNode()
        
        ### Assert ###
        self.assertEqual(list(), childless_treenode.descendants)
            
    def test_descendants_populated_tree(self):
        """Test that the descendants property of a parent TreeNode produces a
        collection that includes all descendant child TreeNodes.
        
        Arrange:
            - Create TreeNode root.
            - Create child nodes leaf A, leaf B, leaf AA.            
        Assert:
            - That the actual descendants contains all added nodes.
        """
        ### Arrange ###
        root = TreeNode(value="root")
        leaf_a = TreeNode(root, value="leaf a")
        leaf_aa = TreeNode(leaf_a, value="leaf aa")
        leaf_b = TreeNode(root, value="leaf b")
        
        expected_descendants = [leaf_a, leaf_aa, leaf_b]
        
        ### Assert ###
        self.assertEqual(expected_descendants, root.descendants)
            
    def test_attach_to_parent_no_duplicates(self):
        """Test that attaching a TreeNode to its parent only results in a 
        single entry in the parents children collection, no matter how many 
        times the method is called.
        
        Arrange:
            - Create TreeNode root.
            - Create child node leaf A.            
        Act:
            - Set leaf A to refer to root as parent.
            - Attach leaf A to root twice.
        Assert:
            - Node root only has a single child registered, and that it is the 
            leaf A.
        """
        ### Arrange ###
        root = TreeNode(value="root")
        leaf_a = TreeNode(None, value="leaf a")        
        
        expected_children = [leaf_a]
        
        ### Act ###
        leaf_a.parent = root
        leaf_a.attach_to_parent(root)
        leaf_a.attach_to_parent(root)
        
        ### Assert ###
        self.assertEqual(expected_children, root.children)
            
    def test_add_child(self):
        """Test that adding a child to an existing TreeNode creates the proper
        references between the parent and child, and that multiple add_child
        operations with the same child and parent nodes involved results in 
        a single reference between the nodes.
        
        Proper references mean that the parent is aware of the child, the 
        child is in the children collection of the parent, and that the child
        is aware of the parent.
        
        Arrange:
            - Create TreeNode root.
            - Create child node leaf A.            
        Act:
            - Add child node leaf A to parent node root twice.
        Assert:
            - Node root only has a single child registered, and that it is the 
            leaf A.
            - That node root's children include leaf A, and that leaf A points
            to node root as its parent.
        """
        ### Arrange ###
        root = TreeNode(value="root")
        leaf_a = TreeNode(None, value="leaf a")        
        
        expected_children = [leaf_a]
        
        ### Act ###
        root.add_child(leaf_a)
        root.add_child(leaf_a)
        
        ### Assert ###
        self.assertEqual(expected_children, root.children)
        self.assertIs(root.children[0], leaf_a)
        self.assertIs(leaf_a.parent, root)
#------------------------------------------------------------------------------

class Tree(TreeNode):
    PATH_SEPARATOR = ":"
    
    def __init__(self, value="<Tree>"):
        TreeNode.__init__(self, parent=None, value=value)
    
    def append(self, parent_node, value):
        """Adds a new TreeNode to the tree, below the indicated parent node.
        
        The new node will be added in the lowest order position under the 
        parent node. This operation will leave the ordering positions of the
        other sibling nodes intact.
        
        Args:
            parent_node: The node that will be the parent of the new child 
                node.
            value: Value to insert into the new node.
        Raises:
            NodeNotFoundError: If the parent node cannot be located.
        Returns:
            Node created by the insert process.
        """
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
        return Tree.PATH_SEPARATOR.join([str(x) for x in path_indices])

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
        path_indices = ()

        if path_string is not None:
            branch_indices = path_string.split(":")
            for index in branch_indices:
                path_indices += (int(index),)

        return path_indices

    def clear(self):
        """Clear the tree of all nodes."""
        self.children = list()

    def has_children(self, node_indices):
        node = self.get_node(node_indices)

        if node is None:
            raise NodeNotFoundError(node_indices)

        return node.has_children()

    def has_path(self, node_indices):
        node = self.get_node(node_indices, must_find=False)

        if node is not None:
            return True
        else:
            return False

    def demote(self, *nodes):
        self._validate_reorganization_nodes(*nodes)

        # Check to ensure the tree itself is not included in the collection of 
        # nodes to be demoted.
        if self in nodes:
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
                            # of this sibling, from highest ordered to lowest 
                            # ordered.
                            moving_nodes = self._sort_nodes_by_depth(*adjacent_selected_nodes)
                            for selected_node in moving_nodes:
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
        """Inserts a new TreeNode with the provided value into the tree at the 
        provided address.
        
        Any sibling nodes of the same parent as this new node that are ordered
        below the indicated address will be moved down one more position to 
        make space for this new node.
        
        Args:
            node_indices: The full path the new node should occupy, in order
                from tree root to the child position index of the node.
            value: Optional value to insert into the new node.
        Raises:
            NodeNotFoundError: If the parent node cannot be located.
        Returns:
            Node created by the insert process.
        """
        assert node_indices, "A node address must be provided."

        new_node = self.insert_node(node_indices)

        new_node.value = value

        return new_node

    def insert_node(self, node_indices, node=None):
        assert node_indices, "A node address must be provided."

        parent_node_address = node_indices[:-1]
        child_index = node_indices[-1]

        parent_node = self.get_parent_node(node_indices)

        # Ensure that there is only one root to the tree.
        if parent_node is self and parent_node.children:
                raise DuplicateRootError()

        if child_index < 0 or child_index > len(parent_node.children):
            raise IndexError("Node index {0} is not valid for the parent at path {1}".format(child_index, parent_node_address))

        if node is None:
            node = TreeNode(parent_node)
        
        parent_node.children.insert(child_index, node)
        node.parent = parent_node

        return node

    def move_node(self, new_parent_node, node, new_child_index=None):
        if node is self:
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
        if new_child_index is None:
            self.append_node(new_parent_node, node)
        else:
            self.insert_node(new_parent_node.path + (new_child_index,), node)

        return node

    def promote(self, *nodes):
        self._validate_reorganization_nodes(*nodes)

        # Sort the nodes in order from deepest (longest path) to shallowest
        # (shortest path).
        sorted_nodes = self._sort_nodes_by_depth(*nodes)

        for node in sorted_nodes:
            grandparent_node = node.parent.parent

            # If the node is already a direct descendant of root, don't 
            # promote (self will be this Tree instance).
            if grandparent_node is self:
                continue
            
            old_parent_index = grandparent_node.children.index(node.parent)
            self.move_node(grandparent_node, node,
                new_child_index=old_parent_index + 1)
        
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
            # Remove the node from the children collection of its parent.
            node_parent = node.parent
            node_parent.children.remove(node)            
            
            # Remove the node's parent reference.
            node.parent = None
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

        # Check to ensure the tree itself is not included in the collection of 
        # nodes to be promoted.
        if self in nodes:
            raise RootReorganizationError()

    def _get_comparable_properties(self):
        return ("children", "path")

    def __str__(self):
        return self._create_branch_str()

    def __repr__(self):
        return self.__str__()

    def _create_branch_str(self, node=None, depth=0, indent=4):
        try:
            if node is None:
                node = self
        except NodeNotFoundError:
            return "<Empty>"

        node_str = "\n{indent} - {path} - {value}".format(
            indent="".center(depth * indent), path=node.path, value=node.value)

        branch_str = list(node_str)
        for child_node in node.children:
            branch_str.append(self._create_branch_str(
                node=child_node, depth=depth + 1, indent=indent))

        return "".join(branch_str)
#------------------------------------------------------------------------------ 

class NodeNotFoundError(Exception):
    def __init__(self, node_path):
        Exception.__init__(self,
            "Node could not be found at path {0}".format(node_path))
#------------------------------------------------------------------------------

class NodeRelationshipError(Exception):
    def __init__(self, message=None, parent_node=None, child_node=None):
        if message is None:
            if parent_node is not None:                
                message = "Parent node {parent} does not contain expected child.".format(parent=parent_node)
            else:
                message = "Node could not identify self in the collection of children held by the node's parent." 
                 
        self.message = message
        self.parent_node = parent_node
        self.child_node = child_node
        
        Exception.__init__(self, message)
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

"""
TODO: Many of these tests were altered during the root_node property removal.
While the tests run accurately, their documentation in most cases has not been
updated.
"""
class PopulatedTreeTest(unittest.TestCase):
    """Test creating, populating, and addressing paths in trees."""
    def test_create_empty_tree(self):
        """Create an empty tree, lacking even a root node.

        Act:
            - Create empty tree.
        Assert:
            - Tree has no children.
        """
        ### Act ###############################################################   
        tree = Tree()

        ### Assert ############################################################
        self.assertFalse(tree.children)

    def test_tree_insert_root(self):
        """Create a tree with only a root node.

        Arrange:
            - Create a value to store (string "root").
        Act:
            - Create a new tree.
            - Insert value into tree at root (path 0).
        Assert:
            - Tree has the root node as a child.
            - Root node exists (is not None) and has the expected value.
            - Root node has no children.
            - The root node's parent is (not just equals) the tree.
        """
        ### Arrange ###########################################################
        expected_value = "child"

        ### Act ###############################################################   
        tree = Tree()
        child_node = TreeNode(tree, value=expected_value)

        ### Assert ############################################################
        self.assertEqual(expected_value, tree.get(child_node.path))
        self.assertEqual((0,), child_node.path)
        self.assertIs(tree, child_node.parent)
        self.assertIs(child_node, tree.children[0])

    def test_add_leaf_tree_node(self):
        """Create a tree with a root node and a single leaf node.

        Act:
            - Create a new tree.
            - Create new root and child leaf nodes.
        Assert:
            - That the leaf node exists.
            - That the leaf's node parent and grandparent are root node and 
            tree, respectively (is comparison, not equals). 
        """
        ### Act ###############################################################   
        tree = Tree()
        root_node = TreeNode(tree, value="root")
        leaf_node = TreeNode(root_node, value="leaf")

        ### Assert ############################################################
        self.assertIs(tree.get_node(leaf_node.path), leaf_node)
        self.assertIs(root_node, leaf_node.parent)
        self.assertIs(tree, leaf_node.parent.parent)
        self.assertIs(leaf_node, root_node.children[0])

    @skip(USE_CASE_DEPRECATED)
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

    @skip(USE_CASE_DEPRECATED)
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

    @skip("Test may no longer be relevant.")
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
            Create the expected path tuple ([1, 3, 4]).
        Act:
            Generate a path list from the string "1:3:4".
        Assert:
            The generated path list equals expected path tuple.
        """
        ### Arrange ###########################################################
        expected_leaf_path = (1, 3, 4)

        ### Act ###############################################################   
        actual_leaf_path = Tree.build_path_from_str("1:3:4")

        ### Assert ############################################################
        self.assertEqual(expected_leaf_path, actual_leaf_path)

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
        expected_path = "1:3:4"

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
        node_a = TreeNode(tree, value="A")
        node_b = TreeNode(node_a, value="B")

        ### Act ###
        tree.move_node(node_a, node_b)

        ### Assert ###
        self.assertEqual(node_b, tree.get_node((0, 0)))

    def test_move_node_root(self):
        """Test moving the root of a tree.

        Test tree architecture:
        - 0

        Arrange:
            Create blank tree.
        Assert:
            Attempting a move operation on the tree raises an error.
        """
        ### Arrange ###
        tree = Tree()

        ### Assert ###        
        with self.assertRaises(RootReorganizationError):
            tree.move_node(tree, tree)

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
        node_a = TreeNode(tree, value="A")
        node_b = TreeNode(node_a, value="B")
        expected_node_b_path = (1,)

        ### Act ###
        tree.move_node(tree, node_b)

        ### Assert ###
        self.assertEqual(tree, node_b.parent)
        self.assertEqual(expected_node_b_path, node_b.path)
        self.assertEqual(node_b, tree.get_node(expected_node_b_path))

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
        node_a = TreeNode(tree, value="A")
        node_b = TreeNode(node_a, value="B")

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
        leaf_node = TreeNode(parent=tree, value="leaf")
        
        expected_leaf_node_path = (0,)
        

        ### Act ###############################################################   
        tree.remove_node(leaf_node)

        ### Assert ############################################################
        with self.assertRaises(NodeNotFoundError):
            tree.get(expected_leaf_node_path)
        self.assertFalse(tree.children)

    @unittest.skip("Disabling due to possible deprecation after Tree/Task refactoring.")
    def test_remove_node_leaf(self):
        """Test removing a leaf node (via remove_node).

        Test tree architecture:
        - root
            - A
            - B

        Arrange:
            - Create blank Tree.
            - Create TreeNodes root, A, B.
            - Create expected Tree with nodes root, B.
        Act:
            - Remove TreeNode A.
        Assert:
            - Node at path 0,1 is TreeNode B.
            - The expected and actual Trees are identical.
        """
        ### Arrange ###
        tree = Tree()
        tree.insert(Tree.ROOT_PATH, "root")
        actual_node_a = tree.insert(Tree.ROOT_PATH + (0,), "A")
        tree.insert(Tree.ROOT_PATH + (1,), "B")
        
        expected_tree = Tree()
        expected_tree.insert(Tree.ROOT_PATH, "root")
        expected_node_b = expected_tree.insert(Tree.ROOT_PATH + (0,), "B")

        ### Act ###
        tree.remove_node(actual_node_a)

        ### Assert ###
        first_child_node = tree.get_node(expected_node_b.path)
        self.assertEqual(expected_node_b, first_child_node) 
        self.assertEqual(expected_tree, tree)

    @unittest.skip("Disabling due to possible deprecation after Tree/Task refactoring.")
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
            Accessing root node raises NodeNotFoundError.
            Accessing leaf node raises NodeNotFoundError.
        """
        ### Arrange ###########################################################
        tree = Tree()
        tree.insert(Tree.ROOT_PATH)
        tree.insert(Tree.ROOT_PATH + (0,))

        ### Act ###############################################################   
        tree.remove(Tree.ROOT_PATH)

        ### Assert ############################################################
        with self.assertRaises(NodeNotFoundError):
            tree.get(Tree.ROOT_PATH)
        with self.assertRaises(NodeNotFoundError):
            tree.get(Tree.ROOT_PATH + (0,))

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

        ### Assert ############################################################
        with self.assertRaises(NodeNotFoundError):
            tree.remove((0,))

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

        ### Assert ############################################################
        with self.assertRaises(NodeNotFoundError):
            tree.update((0,), None)

    def test_set_node_value(self):
        """Test setting a node's value.

        Arrange:
            Create blank tree.
            Create child node.
            Create expected value of "child".
        Act:
            Store initial value of child node (should be default insert value).
            Set value of child node to expected value "child".
        Assert:
            Child node contains expected value.
        """
        ### Arrange ###########################################################
        tree = Tree()
        child_node = tree.add_child(TreeNode(value=""))
        expected_value = "child"

        ### Act ###############################################################   
        tree.update(child_node.path, expected_value)

        ### Assert ############################################################
        self.assertEqual(expected_value, tree.get(child_node.path))

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
        tree.add_child(TreeNode(value="leaf"))

        ### Assert ############################################################
        self.assertTrue(tree.has_path((0,)))

    def test_has_path_nonexistent_node(self):
        """Test if the tree recognizes an invalid node address.

        Arrange:
            Create blank tree.
            Create root node.
        Assert:
            Tree reports it _does not_ have node at the node path 0.
        """
        ### Arrange ###########################################################
        tree = Tree()
        nonexistent_leaf_path = (0,)

        ### Assert ############################################################
        self.assertFalse(tree.has_path(nonexistent_leaf_path))

    @skip(USE_CASE_DEPRECATED)
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
    
    @skip(USE_CASE_DEPRECATED)
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

    @skip(USE_CASE_DEPRECATED)
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

    @skip(USE_CASE_DEPRECATED)
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

    @skip(USE_CASE_DEPRECATED)
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

    @skip("Test may no longer be relevant.")
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

    @skip("Test may no longer be relevant.")
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

    def test_clear(self):
        """Test clearing the tree of all nodes.

        Test tree architecture:
        - <Tree>
            - 0

        Arrange:
            Create blank tree.
            Create and add leaf node.
        Act:
            Clear the tree.
        Assert:
            Accessing root, leaf nodes raise NodeNotFoundError.
            That the tree has no children.
        """
        ### Arrange ###
        tree = Tree()
        tree.add_child(TreeNode(value="0"))

        ### Act ###   
        tree.clear()

        ### Assert ###
        with self.assertRaises(NodeNotFoundError):
            tree.get((0,))

        self.assertFalse(tree.children)
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
                    - F
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
        self.node_f = self.tree.append(self.node_c, "F")

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
            self.tree.promote(self.tree)

    def test_promote_single_node_no_previous_siblings(self):
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

    def test_promote_single_node_with_siblings(self):
        """Test promoting node E.

        This should result in node E being a sibling of nodes D, F (directly under
        C) and ordered below D but above F.

        Resulting tree architecture:
        - root
            - A
                - B
                    - C
                        - D
                        - E
                        - F

        Act:
            - Promote node E.
        Assert:
            - Node E (0,0,0,1) is directly below C in the second position, behind
            D (0,0,0,0,0).
            - Node F is ordered below E (0,0,0,0,2).
        """
        ### Act ###
        actual_node_e = self.tree.get_node(self.node_e.path)
        self.tree.promote(actual_node_e)

        ### Assert ###
        self.assertEqual(self.node_d, self.tree.get_node((0, 0, 0, 0, 0)))
        self.assertEqual(self.node_e, self.tree.get_node((0, 0, 0, 0, 1)))
        self.assertEqual(self.node_f, self.tree.get_node((0, 0, 0, 0, 2)))

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
        """Test promoting nodes C, E.

        This should result in nodes B and C being siblings directly under A,
        with C ordered after B. Nodes D and E should be a direct children of
        C, with E ordered after D.

        Resulting tree architecture:
        - root
            - A
                - B
                    - C
                        - D
                            - E
                        - F
        
        
        - root
            - A
                - B
                - C
                    - D
                    - E
                    - F

        Act:
            Promote nodes C, E.
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
            self.tree.demote(self.tree)

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

class TreeEqualityTest(unittest.TestCase):
    def test_empty_vs_empty(self):
        """Test the equality of two newly created, empty Trees.

        Act:
            Create two Trees.
        Assert:
            That the two Trees are equal.
        """
        ### Act ###
        tree_one = Tree()
        tree_two = Tree()

        ### Assert ###
        self.assertEqual(tree_one, tree_two)

    def test_empty_vs_identity(self):
        """Test that a Tree is equal to itself.

        Act:
            Create one Tree.
        Assert:
            That the Tree is equal to itself.
        """
        ### Act ###
        tree_one = Tree()

        ### Assert ###
        self.assertEqual(tree_one, tree_one)

    def test_empty_vs_root_populated(self):
        """Test that an empty Tree is not equal to a Tree populated with a
        root node.

        Act:
            Create an empty Tree.
            Create a second Tree.
            Populate second Tree with root node.
        Assert:
            That the empty and populated trees are _not_ equal.
        """
        ### Act ###
        tree_empty = Tree()
        tree_root_populated = Tree()
        tree_root_populated.append(None, "root")

        ### Assert ###
        self.assertNotEqual(tree_empty, tree_root_populated)

    def test_populated_different_root_node_values(self):
        """Test that two Tree objects are not equal if they have different root
        node values.

        Act:
            Create Tree one, and populate with root node with value
            "root 1".
            Create Tree two, and populate with root node with value
            "root 2".
        Assert:
            That the empty and populated trees are _not_ equal.
        """
        ### Act ###
        tree_one = Tree()
        tree_one.append(None, "root 1")
        tree_two = Tree()
        tree_two.append(None, "root 2")

        ### Assert ###
        self.assertNotEqual(tree_one, tree_two)

    def test_populated_different_node_ordering(self):
        """Test that two Tree objects are not equal if their node populations
        have identical values and general architecture, but have a different
        ordering.

        Tree AB:
        - root
            - A
            - B

        Tree BA:
        - root
            - B
            - A

        Act:
            Create Trees AB and BA, and populate them as shown in above
            example.
        Assert:
            That Trees AB and BA are _not_ equal.
        """
        ### Arrange ###
        root_value = "root"
        a_value = "A"
        b_value = "B"

        ### Act ###
        tree_one = Tree()
        root = tree_one.append(None, root_value)
        tree_one.append(root, a_value)
        tree_one.append(root, b_value)

        tree_two = Tree()
        root = tree_two.append(None, root_value)
        tree_two.append(root, b_value)
        tree_two.append(root, a_value)

        ### Assert ###
        self.assertNotEqual(tree_one, tree_two)

    def test_populated_vs_populated(self):
        """Test that two Trees with multi-level architectures are equal if
        their node populations have identical values and architecture,
        including node sibling ordering.

        Trees one and two:
        - root
            - A
            - B

        Act:
            Create Trees one and two, and populate them as shown in above
            example.
        Assert:
            That Trees one and two are equal.
        """
        ### Arrange ###
        root_value = "root"
        a_value = "A"
        b_value = "B"

        ### Act ###
        tree_one = Tree()
        root = tree_one.append(None, root_value)
        tree_one.append(root, a_value)
        tree_one.append(root, b_value)

        tree_two = Tree()
        root = tree_two.append(None, root_value)
        tree_two.append(root, a_value)
        tree_two.append(root, b_value)

        ### Assert ###
        self.assertEqual(tree_one, tree_two)
#------------------------------------------------------------------------------ 

class TreeNodeEqualityTest(unittest.TestCase):
    def test_equality_identity(self):
        """Test that a TreeNode is equal to itself.

        Act:
            Create one TreeNode.
        Assert:
            That the TreeNode is equal to itself.
        """
        ### Act ###
        treenode_one = TreeNode()

        ### Assert ###
        self.assertEqual(treenode_one, treenode_one)

    def test_equality_identical(self):
        """Test that two TreeNodes with identical property values are equal.

        Arrange:
            Establish expected parent, path, value property values.
        Act:
            Create TreeNodes one and two with expected values.
        Assert:
            That the two TreeNodes are equal.
        """
        ### Arrange ###
        expected_parent = None
        expected_value = "root"

        ### Act ###
        treenode_one = TreeNode(parent=expected_parent, value=expected_value)
        treenode_two = TreeNode(parent=expected_parent, value=expected_value)

        ### Assert ###
        self.assertEqual(treenode_one, treenode_two)

    def test_equality_different_values(self):
        """Test that two TreeNodes with different property values are not
        equal.

        Arrange:
            Establish expected parent, value property values sets for
            both nodes.
        Act:
            Create TreeNode one with expected values.
            Create TreeNode two with second set of expected values.
        Assert:
            That the two TreeNodes are _not_ equal.
        """
        ### Arrange ###
        expected_parent = None
        expected_value_one = "root 1"
        expected_value_two = "root 2"

        ### Act ###
        treenode_one = TreeNode(parent=expected_parent,
            value=expected_value_one)
        treenode_two = TreeNode(parent=expected_parent,
            value=expected_value_two)

        ### Assert ###
        self.assertNotEqual(treenode_one, treenode_two)

    def test_child_ordering_different(self):
        """Test that two TreeNodes architectures that are identical except for
        the ordering of the children are not equal.

        The TreeNodes will have these architectures:

        One:
        - root
            - A
            - B

        Two:
        -root
            - B
            - A

        Arrange:
            Establish expected parent and value property values sets for
            all nodes.
        Act:
            Create both TreeNode architectures as documented above.
        Assert:
            That the two TreeNodes are _not_ equal.
        """
        ### Arrange ###
        parent_value = "root"
        a_value = "a"
        b_value = "b"

        ### Act ###
        tn_one_parent = TreeNode(parent=None, value=parent_value)
        tn_one_a = TreeNode(parent=tn_one_parent, value=a_value)
        tn_one_b = TreeNode(parent=tn_one_parent, value=b_value)
#        tn_one_parent.children.append(tn_one_a)
#        tn_one_parent.children.append(tn_one_b)

        tn_two_parent = TreeNode(parent=None, value=parent_value)
        tn_two_b = TreeNode(parent=tn_two_parent, value=b_value)
        tn_two_a = TreeNode(parent=tn_two_parent, value=a_value)
#        tn_two_parent.children.append(tn_two_b)
#        tn_two_parent.children.append(tn_two_a)

        ### Assert ###
        self.assertNotEqual(tn_one_parent, tn_two_parent)
#------------------------------------------------------------------------------ 

def node_clean_clone(tree_node):
    # Temporarily clear the tree_node's parent and children properties. 
    # Clearing those properties before the deep copy is executed prevents
    # the system from making an unnecessary copy of the entire tree to 
    # which tree_node belongs to (which  would happen should it have to 
    # follow the parent and children refs).
    orig_parent = tree_node.parent
    orig_children = [x for x in tree_node.children]
    tree_node.parent = None
    del tree_node.children[:]
    
    # Make a complete clone of the tree_node, without the parent and children
    # properties defined.
    clone = copy.deepcopy(tree_node)
    
    # Reset the tree_node's parent and children properties.
    tree_node.parent = orig_parent
    tree_node.children.extend(orig_children)

    return clone
#------------------------------------------------------------------------------

class NodeCleanCloneTest(unittest.TestCase):
    def test_node_clean_clone(self):
        """Test that the node_clean_clone function properly copies the 
        value of a TreeNode while removing the parent and child references
        held by the original.
        
        Arrange:
            - Create expected value.
            - Create parent, original, and child TreeNodes. Give the original
            TreeNode (which will be the clone target) the expected value.
        Act:
            - Clone the original TreeNode.
        Assert:
            - That the parent and children properties of the actual cloned 
            TreeNode are empty.
            - That the actual cloned TreeNode contains the expected value, but
            that value is not the same instance as was provided.
        """
        ### Arrange ###
        expected_value = {1:'a', 2:'b'}
        parent_treenode = TreeNode(value="parent")
        original_treenode = TreeNode(parent=parent_treenode, value=expected_value)
        child_treenode = TreeNode(parent=original_treenode, value="child")
        
        ### Act ###
        actual_clone_treenode = node_clean_clone(original_treenode)
        
        ### Assert ###
        self.assertIsNone(actual_clone_treenode.parent)
        self.assertEqual([],actual_clone_treenode.children)
        
        self.assertEqual(expected_value, actual_clone_treenode.value)
        self.assertIsNot(expected_value, actual_clone_treenode.value)
#------------------------------------------------------------------------------
