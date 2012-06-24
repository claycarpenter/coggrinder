'''
Created on Apr 27, 2012

@author: Clay Carpenter
'''

import unittest
from logging import debug

class DeclaredPropertiesComparable(object):
    '''Simply compares between two objects, using declared properties.
    '''
    def _get_comparable_properties(self):
        return self.__dict__.keys()

    def __eq__(self, other):
        """Compares the equality of this object with another, based upon a
        set of declared comparable properties.

        In the case of a circular reference between two objects (i.e., A.other
        = B and B.other = A), the property is ignored.

        Circular reference in a parent-child relationship:
            A.child = B
            B.parent = A
            C.child = D
            D.parent = C

        If I get rid of other.comparing, can I detect this circular reference?

        A.child = B
        B.parent = C
        C.child = D
        D.parent = A

        I think so, because it all wraps back to A eventually...


        Args:
            other: The other object to compare this object to.
        Returns:
            True if the objects have equal values for all of their declared
            comparable properties; false otherwise.
        """
        are_equal = True
        
        # Test if one or both of the comparable objects are None. If both are, 
        # return True, otherwise the objects are different.
        if self is None or other is None:
            return self is other

        # TODO: Can this be accomplished without setting a comparing flag on 
        # other?
        try:
            if self._comparing == other._comparing:
                # In a loop, exit immediately with True.
                return True
        except AttributeError:
            # Objects lack comparing flag, add it.
            self._comparing = True
            
            try:
                other._comparing = True
            except AttributeError:
                # Other object is a built-in class, and self is not. They 
                # are not equal.
                return False

        # Simple shortcut in case of identity comparison.
        if self is not other:
            comparable_prop_names = self._get_comparable_properties()

            if comparable_prop_names != other._get_comparable_properties():
                are_equal = False
            else:
                for property_name in comparable_prop_names:
                    try:
                        self_value = getattr(self, property_name)
                        other_value = getattr(other, property_name)
                    except AttributeError:
                        are_equal = False
                        break

                    # Protect against infinite recursion occurring because of circular
                    # references between two objects.
                    if self_value is not other and other_value is not self:
                        if self_value != other_value:
                            are_equal = False
                            debug("Equality test difference -> prop: {0}, self val: '{1}', other: '{2}' --- self: {3} --- other: {4}".format(
                                property_name, self_value, other_value, self, other))
                            break

            # Clear the comparing flag on other.            
            del other._comparing

        del self._comparing

        return are_equal

    def __ne__(self, other):
        return not self.__eq__(other)
#------------------------------------------------------------------------------ 

class DeclaredPropertiesComparableTest(unittest.TestCase):
    def test_blank_vs_blank(self):
        """Test that two blank DCP objects are equal.

        Act:
            Create a pair of blank DCP objects.
        Assert:
            That two newly created DCP objects are equal.
        """
        ### Act ###
        comparable_one = DeclaredPropertiesComparable()
        comparable_two = DeclaredPropertiesComparable()

        ### Assert ###
        self.assertEqual(comparable_one, comparable_two)

    def test_blank_vs_populated(self):
        """Test that a blank DCP is not equal to a DCP with a property value
        set.

        Act:
            Create a blank DCP object.
            Create a second DCP object and give its property "a" a value of
            1.
        Assert:
            That the two DCP objects are _not_ equal.
        """
        ### Act ###
        comparable_one = DeclaredPropertiesComparable()
        comparable_two = DeclaredPropertiesComparable()
        comparable_two.a = 1

        ### Assert ###
        self.assertNotEqual(comparable_one, comparable_two)

    def test_populated_vs_populated_identical(self):
        """Test that two DCPs with a property value set to identical values
        are equal.

        Act:
            Create a two DCP objects and give each a property "a" with a value
            of 1.
        Assert:
            That the two DCP objects are equal.
        """
        ### Act ###
        comparable_one = DeclaredPropertiesComparable()
        comparable_one.a = 1
        comparable_two = DeclaredPropertiesComparable()
        comparable_two.a = 1

        ### Assert ###
        self.assertEqual(comparable_one, comparable_two)

    def test_populated_vs_populated_different(self):
        """Test that two DCPs with a property value set to different values
        are not equal.

        Act:
            Create a two DCP objects and give each a property "a" with a value
            of 1 and 2, respectively.
        Assert:
            That the two DCP objects are equal.
        """
        ### Act ###
        comparable_one = DeclaredPropertiesComparable()
        comparable_one.a = 1
        comparable_two = DeclaredPropertiesComparable()
        comparable_two.a = 2

        ### Assert ###
        self.assertNotEqual(comparable_one, comparable_two)

    def test_simple_circular_reference(self):
        """Test that a two DCPs with a property value set to reference the
        other are equal and don't cause an infinite recursion loop.

        Act:
            Create two DCP objects and give each a property "circular" with
            a value that references the other DCP.
        Assert:
            That the two DCP objects are equal.
        """
        ### Act ###
        comparable_one = DeclaredPropertiesComparable()
        comparable_two = DeclaredPropertiesComparable()
        comparable_one.circular = comparable_two
        comparable_two.circular = comparable_one

        ### Assert ###
        self.assertEqual(comparable_one, comparable_two)

    def test_parent_child_circular_reference(self):
        """Test that two DCPs with circular parent-child relationships are
        equal.

        Act:
            Create two sets of DCP objects with parent-child relationships and
            identical "a" property values of 1.
        Assert:
            That the two DCP parent and child object pairs are equal.
        """
        ### Act ###
        comparable_parent_one = DeclaredPropertiesComparable()
        comparable_parent_one.a = 1
        comparable_child_one = DeclaredPropertiesComparable()
        comparable_parent_one.child = comparable_child_one
        comparable_child_one.parent = comparable_parent_one

        comparable_parent_two = DeclaredPropertiesComparable()
        comparable_parent_two.a = 1
        comparable_child_two = DeclaredPropertiesComparable()
        comparable_parent_two.child = comparable_child_two
        comparable_child_two.parent = comparable_parent_two

        ### Assert ###
        # There shouldn't be any difference between the following two equality
        # tests.
        self.assertEqual(comparable_parent_one, comparable_parent_two)
        self.assertEqual(comparable_child_one, comparable_child_two)

    def test_complex_circular_reference(self):
        """Test that a pair of DCPs using a complex circular reference
        involving cross-referencing parent-child relationships are _not_ equal.

        This is the reference architecture for the test:
        a.child = b
        b.parent = c
        c.child = d
        d.parent = a

        In this case, comparing a to b and c to d should determine that they're
        not equal.

        TODO: Pretty sure these two objects should be considered different.

        Act:
            Create a four DCP objects, setting up the complex circular
            reference documented above.
        Assert:
            That the DCP pairs a and b, c and d are _not_ equal.
        """
        ### Act ###
        a = DeclaredPropertiesComparable()
        b = DeclaredPropertiesComparable()
        c = DeclaredPropertiesComparable()
        d = DeclaredPropertiesComparable()

        a.child = b
        b.parent = c
        c.child = d
        d.parent = a

        ### Assert ###
        self.assertNotEqual(a, b)
        self.assertNotEqual(c, d)
#------------------------------------------------------------------------------
