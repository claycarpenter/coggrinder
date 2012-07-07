"""
Created on Apr 27, 2012

@author: Clay Carpenter
"""

import unittest
from logging import debug

class DeclaredPropertiesComparable(object):
    """Simply compares between two objects, using declared properties."""
    def _get_comparable_properties(self):
        """Simple default implementation uses all mappings in the instance's
        __dict__ attribute.        
        """
        return self.__dict__.keys()
    
    @classmethod
    def compare(cls, first, second, comparable_properties):
        """Compares the equality of this object with another, based upon the
        set of provided comparable properties.

        In the case of a circular reference between two objects (i.e., A.second
        = B and B.second = A), the property is ignored.

        Circular reference in a parent-child relationship:
            A.child = B
            B.parent = A
            C.child = D
            D.parent = C

        If I get rid of second.comparing, can I detect this circular reference?

            A.child = B
            B.parent = C
            C.child = D
            D.parent = A

        I think so, because it all wraps back to A eventually...

        Args:
            first: The first object under comparison.
            second: The second (other) object under comparison.
            comparable_properties: An iterable that generates a sequence of 
            str property names that should be consider when comparing the
            equality of arguments first and second.
        Returns:
            True if the objects have equal values for all of their declared
            comparable properties; false otherwise.
        """
        are_equal = True
        
        # Test if one or both of the comparable objects are None. If both are, 
        # return True, otherwise the objects are different.
        if first is None or second is None:
            return first is second

        # TODO: Can this be accomplished without setting a comparing flag on 
        # second?
        try:
            if first._comparing == second._comparing:
                # In a loop, exit immediately with True.
                return True
        except AttributeError:
            # Objects lack comparing flag, add it.
            first._comparing = True
            
            try:
                second._comparing = True
            except AttributeError:
                # second object is a built-in class, first is not. They 
                # are not equal.
                return False

        # Simple shortcut in case of identity comparison.
        if first is not second:
            for property_name in comparable_properties:
                try:
                    first_value = getattr(first, property_name)
                    second_value = getattr(second, property_name)
                except AttributeError:
                    debug("Attribute error while trying to compare equality on property: '{0}'".format(property_name))
                    
                    are_equal = False
                    break

                # Protect against infinite recursion occurring because of circular
                # references between two objects.
                if first_value is not second and second_value is not first:
                    if first_value != second_value:
                        are_equal = False
                        debug("Equality test difference -> prop: {property_name}, first value: '{first_value}', second: '{second_value}' --- first: {first} --- second: {second}".format(
                            property_name=property_name, first_value=first_value, second_value=second_value, first=first, second=second))
                        break

            # Clear the comparing flag on second.            
            del second._comparing

        del first._comparing

        return are_equal

    def __eq__(self, other):
        return self.compare(self, other, self._get_comparable_properties())

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
        
    def test_compare_as_classmethod(self):
        """Test the compare functionality as a class/static method.
        
        Arrange:
        
        Act:
        
        Assert:
                
        """
        ### Arrange ###
        class Person(object):
            def __init__(self, name, age, hobby):
                self.name = name
                self.age = age
                self.hobby = hobby
        
        john = Person('John', 35, 'Sailing')
        mary = Person('Mary', 24, 'Running')
        john2 = Person('John', 35, 'Cooking')
        
        comparable_properties = ['name','age']
        all_properties = comparable_properties + ['hobby']
        
        ### Assert ###
        self.assertTrue(
            DeclaredPropertiesComparable.compare(john, john2, comparable_properties))
        self.assertFalse(
            DeclaredPropertiesComparable.compare(john, john2, all_properties))
        self.assertFalse(
            DeclaredPropertiesComparable.compare(john, mary, comparable_properties))
#------------------------------------------------------------------------------
