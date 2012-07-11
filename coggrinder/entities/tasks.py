"""
Created on Mar 18, 2012

@author: Clay Carpenter
"""

from datetime import datetime
import unittest
from unittest import skip
import uuid
import coggrinder.utilities
from coggrinder.entities.properties import EntityProperty, RFC3339Converter, IntConverter, BooleanConverter, TaskStatus, TaskStatusConverter
from coggrinder.utilities import GoogleKeywords
from coggrinder.entities.tree import TreeNode
import string
from coggrinder.core.test import DISABLED_WORKING_OTHER_TESTS, USE_CASE_DEPRECATED
import json

class SortedTaskDataChildrenSupport(object):
    def add_child(self, child, child_index=None):
        if child_index is not None:
            super(SortedTaskDataChildrenSupport, self).add_child(child, child_index=child_index)
        else:
            try:
                if child.position is not None:
                    # New child is a Task-like entity and has a defined 
                    # position.
                    # Order by position, placing any Tasks with defined 
                    # positions before those that have undefined positions.
                    for sibling_index, sibling in enumerate(self.children):
                        if sibling.position is None or child.position < sibling.position:
                            # Sibling either has no position or has a higher
                            # position value (and therefore a lower ordering)
                            # than the new child. Insert the new child before
                            # the sibling.
                            child_index = sibling_index
                            break
                            
                # If the new child is a Task-like entity without a defined
                # position, the child_index value will still be None. This
                # will insert the new Task at the end of the sibling group.
                super(SortedTaskDataChildrenSupport, self).add_child(child, child_index=child_index)
            except AttributeError:
                # New child is a TaskList-type entity.
                for sibling_index, sibling in enumerate(self.children):
                    if child.treeless_value < sibling.treeless_value:
                        child_index = sibling_index
                        break
                
                # If the new TaskList has a title with a higher lexicographical
                # ordering, it will reach this point with a child_index value 
                # that is still None. This will add the new TaskList to the
                # end (lowest order) of the sibling group (self.children). 
                super(SortedTaskDataChildrenSupport, self).add_child(child, child_index=child_index)
#------------------------------------------------------------------------------

class TaskList(SortedTaskDataChildrenSupport, TreeNode):
    _ARGUMENT_FAIL_MESSAGE = "Provided {0} argument must be of type {1}"
    _KEY_VALUE_MESSAGE = "{key}: {value}"
    
    _properties = (
            EntityProperty("persistence_id", GoogleKeywords.ID),
            EntityProperty("title", GoogleKeywords.TITLE),
            EntityProperty("updated_date", GoogleKeywords.UPDATED,
                RFC3339Converter())
        )

    def __init__(self, parent, entity_id=None, title="", updated_date=None, 
        children=None, persistence_id=None, is_persisted=False):
        # Initialize TaskList properties first so that they're available during
        # the comparison operations used in the add_child method.
        if entity_id is None:
            self.local_id = TaskList.create_entity_id()
        else:
            self.local_id = None
            
        self.persistence_id = persistence_id            
        self.entity_id = entity_id
        self.title = title
        
        self.is_persisted = is_persisted

        if updated_date is None:
            updated_date = datetime.now()
            
        # Strip the timestamp down to just date (year, month, day) and 
        # a time that includes hours, minutes, and seconds. Microseconds and
        # any timezone info are not preserved.            
        self.updated_date = datetime(updated_date.year, updated_date.month, 
            updated_date.day, updated_date.hour, updated_date.minute, updated_date.second)
                
        TreeNode.__init__(self, parent, value=self)

    @property
    def entity_id(self):
        if self.persistence_id:
            return self.persistence_id
        else:
            return self.local_id
        
    @entity_id.setter
    def entity_id(self, value):
        self.persistence_id = value

    @property
    def tasklist(self):
        return self
    
    @property
    def treeless_value(self):        
        return self.clean_clone()
    
    @staticmethod
    def create_entity_id():
        return str(uuid.uuid4())

    @classmethod
    def from_str_dict(cls, str_dict):
        # Create a new blank entity.
        entity = cls._create_blank_entity()

        entity.update_from_str_dict(str_dict)
                
        # Return the (hopefully completed) entity.
        return entity

    @classmethod
    def _create_blank_entity(cls):
        """
        A hook method that creates an avenue for subclasses to provide their 
        own "blank" entities.
        """
        entity = TaskList(None)

        return entity

    """
    TODO: This method seems pointless.
    Leaving it here because there are bigger priorities to tackel first.
    """
    @classmethod
    def _get_properties(cls):            
        return cls._properties

    def to_str_dict(self, include_none_values=False):
        # Create a blank string dict.
        str_dict = dict()

        # Loop through each property, converting the property value to string
        # representations.
        for prop in self._get_properties():
            # Ensure the property has an associated value.
            if self.__dict__.has_key(prop.entity_key):
                # Identify the property value.
                obj_value = self.__dict__[prop.entity_key]

                # Only add the value to the str dict if the value isn't None, or
                # none values are specified to be included.
                if obj_value != None or include_none_values:
                    # Convert the property value to a string representation.
                    str_value = prop.to_str(obj_value)

                    # Push that string representation into the string dict.
                    str_dict[prop.str_dict_key] = str_value

        return str_dict

    def to_insert_dict(self):
        # Create base dict.
        entity_dict = self.to_str_dict()

        # Further filter down to just the insert compatible properties.
        keywords = coggrinder.utilities.GoogleKeywords
        filter_keys = (keywords.TITLE,)

        entity_dict = coggrinder.utilities.DictUtilities.filter_dict(entity_dict, filter_keys)

        return entity_dict
    
    def update_from_str_dict(self, str_dict):
        # Loop through each property, converting each string representation 
        # into the correct "object" value for the property.
        for prop in self._get_properties():
            # For each property, lookup the value of the property in the string
            # dict.
            if str_dict.has_key(prop.str_dict_key):
                # Key is present, convert to object value.
                str_value = str_dict[prop.str_dict_key]

                # Using the property's specific converter, convert from 
                # the string representation to the object value.
                obj_value = prop.from_str(str_value)

                # Push the object value into the new entity's 
                # corresponding property.
                setattr(self, prop.entity_key, obj_value)
                
        return self
    
    def _ordered_entity_info(self, str_dict):
        prop_values = list()
        for prop in self._get_properties():
            try:
                prop_value = str_dict[prop.str_dict_key]
                prop_values.append(TaskList._KEY_VALUE_MESSAGE.format(
                    key=prop.entity_key, value=prop_value))
            except KeyError:
                # Property isn't defined in this str dict, which is (usually?)
                # ok.
                pass
        
        return prop_values

    # TODO: Rename this method?
    def _get_filter_keys(self):
        keywords = coggrinder.utilities.GoogleKeywords
        filter_keys = (("entity_id", keywords.ID), keywords.TITLE, keywords.UPDATED)

        return filter_keys

    """
    TODO: Should this be a class method, or an instance method?
    """
    def _get_comparable_properties(self):
        comparable_properties = list()
        for prop in self._get_properties():
            comparable_properties.append(prop.entity_key)
            
        """
        TODO: This implementation might be a bit redundant considering what
        TreeNode (parent class) already produces.
        """
        comparable_properties.append("children")
        comparable_properties.append("parent")
        comparable_properties.append("is_persisted")
        
        return comparable_properties
    
    def __str__(self):
        str_dict = self.to_str_dict()
        ordered_entity_info = self._ordered_entity_info(str_dict)
        
        return "<" + ("; ".join(ordered_entity_info)) + ">"

    def __repr__(self):
        return self.__str__()
    
    def __lt__(self, other):      
        try:  
            if self.title.lower() < other.title.lower():
                return True
            elif self.title == other.title:
                return self.entity_id.lower() < self.entity_id.lower()
            
            return False
        except AttributeError:
            return NotImplemented
    
    def __gt__(self, other):
        return not self.__lt__(other)
#------------------------------------------------------------------------------ 

class TaskListTest(unittest.TestCase):
    """
    TODO: This test really needs some cleanup work done.
    """
    def test_creation(self):
        # This should work.
        TaskList(None, entity_id="aljkdfkj", title="Title")
        
        # Using a string as an updated_date timestamp should fail.
        with self.assertRaises(AttributeError):
            TaskList(None, entity_id="aljkdfkj", title="Title", updated_date=29)

        # Using a real datetime object for the updated_date timestamp should work.
        last_updated = datetime.now()
        TaskList(None, entity_id="aljkdfkj", title="Title", updated_date=last_updated)

    def test_equality(self):
        entity_id = "1"
        title = "Title"
        updated_date = datetime.now()
        entity_1 = TaskList(None, entity_id=entity_id, title=title, updated_date=updated_date)
        entity_2 = TaskList(None, entity_id=entity_id, title=title, updated_date=updated_date)
        
        persisted_tasklist = TaskList(None, entity_id=entity_id, title=title, updated_date=updated_date, is_persisted=True)
        transient_tasklist = TaskList(None, entity_id=entity_id, title=title, updated_date=updated_date, is_persisted=False)

        self.assertEqual(entity_1, entity_2)
        self.assertNotEqual(persisted_tasklist, transient_tasklist)
        
    def test_compare_different_object(self):
        """Test equality against another type of object (a dict, in this case).
        
        Arrange:
            - Create "other object" dict.
            - Create TaskList A.        
        Assert:
            - That Other is not equal to TaskList A.
            - That Other can be compared to TaskList A without raising an 
            error.
        """
        ### Arrange ###
        other = {'name':'John', 'age':35}
        tl_a = TaskList(None, title="A")
        
        ### Assert ###
        self.assertNotEqual(other, tl_a)
        self.assertLess(tl_a, other)
        self.assertGreater(other, tl_a)

    def test_ordering_comparison(self):        
        """Test the greater than and lesser than comparison operators.
        
        This tests the entity's implementation of the Python 
        customization/"magic" methods __gt__ and __lt__. Ordering should be 
        based upon a case-insensitive, lexicographical comparison of the
        entities titles.
        
        Arrange:
            - Create entities Foo, Bar, barber, "" (empty), and "_special_char". 
        Assert:
            - That the following comparisons are true:
                - Foo > Bar
                - Bar < barber
                - "" < Bar
                - "_special_char" < Bar
                - "" < "_special_char"
        """    
        ### Arrange ###
        entity_foo = TaskList(None, title="Foo")
        entity_bar = TaskList(None, title="Bar")
        entity_barber = TaskList(None, title="Barber")
        entity_empty = TaskList(None, title="")
        entity_special_char = TaskList(None, title="_special_char")

        ### Assert ###
        self.assertGreater(entity_foo, entity_bar)
        self.assertLess(entity_bar, entity_barber)
        self.assertLess(entity_empty, entity_bar)
        self.assertLess(entity_special_char, entity_bar)
        self.assertLess(entity_empty, entity_special_char)
        
    def test_sort_collection(self):
        """Verify that a collection of BaseTaskEntities sorts in the 
        correct order.
        
        Arrange:
            - Create BaseTaskEntities.
            - Create a collection of expected, sorted BaseTaskEntities.
            - Create a collection of unordered BaseTaskEntities.            
        Act:
            - Create the actual sorted collection of BaseTaskEntities.
        Assert:
            - That the expected sorted and actual sorted TaskList 
            collections are equal.
        """    
        ### Arrange ###
        foo = TaskList(None, title="foo")
        bar = TaskList(None, title="bar")
        baz = TaskList(None, title="Baz")
        
        expected_sorted_entities = [bar, baz, foo]
        input_entities = [foo, bar, baz]
        
        ### Act ###
        actual_sorted_entities = sorted(input_entities)
        
        ### Assert ###
        self.assertEqual(expected_sorted_entities, actual_sorted_entities)

    def test_from_str_dict(self):
        expected_entity = TaskList(None, entity_id="1",
            title="Test List Title",
            updated_date=datetime(2012, 3, 10, 3, 30, 06))
        rfc_timestamp = "2012-03-10T03:30:06.000Z"

        keywords = coggrinder.utilities.GoogleKeywords
        entity_dict = {keywords.ID:expected_entity.entity_id,
            keywords.TITLE:expected_entity.title,
            keywords.UPDATED:rfc_timestamp}

        result_entity = TaskList.from_str_dict(entity_dict)

        self.assertEqual(expected_entity, result_entity)
        
    """
    TODO: Update/complete test doc.
    """
    def test_update_from_str_dict(self):
        """
        
        Arrange:
            - Create a new TaskList.
        Act:
            - Update the TaskList with a mock insert request response.
        Assert:
            - That the TaskList has been updated with the mock information.
        """
        ### Arrange ###
        mock_insert_response_str = '''{
            "kind": "tasks#taskList",
            "id": "MTM3ODEyNTc4OTA1OTU2NzE3NTM6MTk3NDg0OTU5Mjow",
            "etag": "-kSxjsniVV6Hn53-kChReeLNJUE/C-2Y15dCA_rEUUo1IGBfAfOcI-Q",
            "title": "mock insert",
            "updated": "2012-07-08T22:08:26.000Z",
            "selfLink": "https://www.googleapis.com/tasks/v1/users/@me/lists/MTM3ODEyNTc4OTA1OTU2NzE3NTM6MTk3NDg0OTU5Mjow"
        }'''
        insert_result_str_dict = json.loads(mock_insert_response_str)
        tl_new = TaskList(None, title="TL New")
        
        ### Act ###
        tl_new.update_from_str_dict(insert_result_str_dict)
        
        ### Assert ###
        self.assertEqual(tl_new.entity_id, insert_result_str_dict["id"])
        
        updated_date = datetime.strptime(insert_result_str_dict["updated"],"%Y-%m-%dT%H:%M:%S.000Z")
        self.assertEqual(tl_new.updated_date, updated_date)

    def test_to_dict(self):
        entity = TaskList(None, entity_id="1",
            title="Test List Title",
            updated_date=datetime(2012, 3, 10, 3, 30, 06))
        rfc_timestamp = "2012-03-10T03:30:06.000Z"

        keywords = coggrinder.utilities.GoogleKeywords
        expected_dict = {keywords.ID:entity.entity_id,
            keywords.TITLE:entity.title,
            keywords.UPDATED:rfc_timestamp}

        result_dict = entity.to_str_dict()

        self.assertEqual(expected_dict, result_dict)

    def test_to_insert_dict(self):
        entity = TaskList(None, entity_id="1", title="Test List Title")

        keywords = coggrinder.utilities.GoogleKeywords
        expected_dict = {keywords.TITLE:entity.title}

        result_dict = entity.to_insert_dict()

        self.assertEqual(expected_dict, result_dict)
#------------------------------------------------------------------------------ 

class Task(TaskList):
    _properties = TaskList._get_properties() + (
            EntityProperty("notes", GoogleKeywords.NOTES),
            EntityProperty("task_status", GoogleKeywords.STATUS, TaskStatusConverter()),
            EntityProperty("due_date", GoogleKeywords.DUE, RFC3339Converter()),
            EntityProperty("completed_date", GoogleKeywords.COMPLETED, RFC3339Converter()),
            EntityProperty("is_deleted", GoogleKeywords.DELETED, BooleanConverter()),
            EntityProperty("is_hidden", GoogleKeywords.HIDDEN, BooleanConverter()),
            EntityProperty("parent_id", GoogleKeywords.PARENT),
            EntityProperty("position", GoogleKeywords.POSITION, IntConverter())
        )

    def __init__(self, parent, entity_id=None, tasklist_id=None, title="",
        updated_date=None, task_status=TaskStatus.NEEDS_ACTION,
        parent_id=None, position=None, persistence_id=None, is_persisted=False):        
        self.task_status = task_status
        self.position = position

        # Establish default properties.
        self.notes = None
        self.due_date = None
        self.completed_date = None
        self.is_deleted = None
        self.is_hidden = None
        
        # If a parent ref has been provided, copy the ID and TaskList ID into
        # the corresponding attributes.
        try:
            # Only set the parent ID if the parent is _not_ a TaskList.
            if hasattr(parent, "parent_id"):
                parent_id = parent.entity_id    
            
            tasklist_id = parent.tasklist.entity_id
        except AttributeError:
            # This is fine, simply indicating that a proper parent ref wasn't
            # provided.
            pass
        
        self.parent_id = parent_id            
        self.tasklist_id = tasklist_id
        
        super(Task, self).__init__(parent, entity_id, title, updated_date, persistence_id=persistence_id, is_persisted=is_persisted)
        
    @property
    def parent_id(self):
        if self.parent is not None and hasattr(self.parent, "task_status"):
            return self.parent.entity_id
        
        return self._parent_id
    
    @parent_id.setter
    def parent_id(self, parent_id):
        # Make sure that if this Task is linked to a parent Task, the
        # updated ID matches that of the linked Task. Note that Task's that
        # are direct children of their belonging TaskList have undefined 
        # (None) parent values.
        """
        TODO: This needs a test to validate its behavior.
        """
        try:
            if self.parent is not None:
                assert parent_id == self.parent.entity_id
        except AttributeError:
            # Parent-child relationship has not been established.
            # Set the parent_id to be None.
            pass
            
        self._parent_id = parent_id
                
    @property
    def tasklist(self):
        try:
            return self.parent.tasklist
        except AttributeError:
            # This should happen in the case of an unattached Task (self.parent
            # will be None).
            return None
        
    @property
    def tasklist_id(self):
        if self.tasklist is not None:
            return self.tasklist.entity_id
        
        return self._tasklist_id
    
    @tasklist_id.setter
    def tasklist_id(self, tasklist_id):
        # Make sure that if this Task is linked to a parent TaskList, the
        # updated ID matches that of the linked TaskList.
        """
        TODO: This needs a test to validate its behavior.
        """
        if self.tasklist is not None:
            assert tasklist_id == self.tasklist.entity_id
            
        self._tasklist_id = tasklist_id
        
    def _get_filter_keys(self):
        base_keys = super(Task, self)._get_filter_keys()

        keywords = coggrinder.utilities.GoogleKeywords
        taskitem_keys = (keywords.COMPLETED, keywords.NOTES, keywords.POSITION,
            keywords.PARENT, keywords.STATUS)

        taskitem_keys = taskitem_keys + base_keys

        return taskitem_keys

    """
    TODO: This needs to be better defined, so that it actually tests equality
    on all relevant attributes.
    """
    def _get_comparable_properties(self):
        comparable_properties = list()
        for prop in self._get_properties():
            comparable_properties.append(prop.entity_key)

        """
       TODO: Shouldn't this also include/compare parent_id?
       """           
        comparable_properties.append("tasklist_id")   
        comparable_properties.append("is_persisted")
        
        return comparable_properties
    
    @classmethod
    def _create_blank_entity(cls):
        entity = Task(None)

        return entity
    
    def __lt__(self, other):
        if self.child_index == other.child_index and self.position == other.position:
            return super(Task, self).__lt__(other)
        
        # Prefer to order based on child index.
        if self.child_index is not None:
            # Order by child index.
            try:                
                if other.child_index is None:
                    return True
                
                if self.child_index == other.child_index:
                    return super(Task, self).__lt__(other)
                
                return self.child_index < other.child_index
            except AttributeError:
                return NotImplemented
            
            return False
        else:
            # Order by position.
            try:
                # Check for an "undefined" position. This is indicated by a zero value,
                # and such positions should be considered _greater_ than any other
                # defined position value.
                if self.position == other.position:
                    return super(Task, self).__lt__(other)
                
                if self.position is None:
                    return False                
                elif other.position is None:
                    return True

                return self.position < other.position
            except AttributeError:
                # In the case of comparisons against another Task-type entity 
                # that lacks a position property, defer to sorting the Tasks
                # by the basic Task implementation (currently by child index).
                return NotImplemented 
        
        raise ValueError("Could not compare the two operands {this} and {other}".format(this=self, other=other))
    
    def __gt__(self, other):
        return not self.__lt__(other)
#------------------------------------------------------------------------------ 

class TaskTest(unittest.TestCase):
    """
    TODO: This test case probably needs to include a couple of tests to ensure
    that equality comparisons (eq, ne) are working properly.
    """
    def test_equality(self):
        """Test the equality comparisons by comparing like and unlike Tasks.
        
        Arrange:
            - Create Tasks A, B (identical to A but in different TaskList), 
            A2 (identical to A).
        Assert:
            - That Tasks A and A2 are identical.
            - That Tasks A and B are not identical.
        """
        ### Arrange ###
        t_a = Task(None, entity_id="a", title="a", parent_id=None, position=123,
            task_status=TaskStatus.NEEDS_ACTION, tasklist_id="tl-a")
        t_a_persisted = Task(None, entity_id="a", title="a", parent_id=None, position=123,
            task_status=TaskStatus.NEEDS_ACTION, tasklist_id="tl-a", is_persisted=True)
        t_a2 = Task(None, entity_id=t_a.entity_id, title=t_a.title,
            parent_id=t_a.parent_id, position=t_a.position,
            task_status=t_a.task_status, tasklist_id=t_a.tasklist_id)
        t_b = Task(None, entity_id=t_a.entity_id, title=t_a.title,
            parent_id=t_a.parent_id, position=t_a.position,
            task_status=t_a.task_status, tasklist_id="tl-b")
        
        ### Assert ###
        self.assertEqual(t_a, t_a2)
        self.assertNotEqual(t_a, t_b)
        self.assertNotEqual(t_a, t_a_persisted)
            
    def test_to_str_dict(self):
        task_id = "abcid"
        task_title = "task title"
        task_update_timestamp = "2012-03-10T03:30:06.000Z"
        task_status = TaskStatus.NEEDS_ACTION

        expected_str_dict = {
            GoogleKeywords.ID: task_id,
            GoogleKeywords.TITLE: task_title,
            GoogleKeywords.UPDATED: task_update_timestamp,
            GoogleKeywords.STATUS: task_status
        }

        taskitem = Task(None)
        taskitem.entity_id = task_id
        taskitem.title = task_title
        taskitem.updated_date = datetime(2012, 3, 10, 3, 30, 6)
        taskitem.status = task_status

        actual_str_dict = taskitem.to_str_dict()

        self.assertEqual(expected_str_dict, actual_str_dict)

    def test_from_str_dict_minimal(self):
        task_id = "abcid"
        task_title = "task title"
        task_update_timestamp = "2012-03-10T03:30:06.000Z"
        task_position = "00000000001073741823"
        task_status = TaskStatus.NEEDS_ACTION

        str_dict = {
            GoogleKeywords.ID: task_id,
            GoogleKeywords.TITLE: task_title,
            GoogleKeywords.UPDATED: task_update_timestamp,
            GoogleKeywords.POSITION: task_position,
            GoogleKeywords.STATUS: task_status
        }

        expected_taskitem = Task(None)
        expected_taskitem.entity_id = task_id
        expected_taskitem.title = task_title
        expected_taskitem.updated_date = datetime(2012, 3, 10, 3, 30, 6)
        expected_taskitem.position = 1073741823
        expected_taskitem.status = task_status

        actual_taskitem = Task.from_str_dict(str_dict)

        self.assertEqual(expected_taskitem, actual_taskitem)

    def test_from_str_dict_deleted(self):
        task_id = "abcid"
        task_title = "task title"
        task_update_timestamp = "2012-03-10T03:30:06.000Z"
        task_position = "00000000001073741823"
        task_status = TaskStatus.NEEDS_ACTION
        task_deleted = True

        str_dict = {
            GoogleKeywords.ID: task_id,
            GoogleKeywords.TITLE: task_title,
            GoogleKeywords.UPDATED: task_update_timestamp,
            GoogleKeywords.POSITION: task_position,
            GoogleKeywords.STATUS: task_status,
            GoogleKeywords.DELETED: task_deleted
        }

        expected_taskitem = Task(None)
        expected_taskitem.entity_id = task_id
        expected_taskitem.title = task_title
        expected_taskitem.updated_date = datetime(2012, 3, 10, 3, 30, 6)
        expected_taskitem.position = 1073741823
        expected_taskitem.status = task_status
        expected_taskitem.is_deleted = task_deleted

        actual_taskitem = Task.from_str_dict(str_dict)

        self.assertEqual(expected_taskitem, actual_taskitem)
        
    """
    TODO: Update test documentation.
    """
    def test_tasklist_id(self):
        """Test that the tasklist_id property, if not manually defined, will
        attempt to automatically resolve to the ID of the TaskList parent.
        
        Ensure that this property is established even for "early" clones.
        
        Arrange:
        
        Act:
        
        Assert:
                
        """
        ### Arrange ###
        tl_a = TestDataTaskList(None, 'a')
        t_foo = TestDataTask(tl_a, 'foo')
        t_foo_clone = t_foo.clean_clone()
        
        ### Assert ###
        self.assertEqual(tl_a.entity_id, t_foo.tasklist_id)
        self.assertEqual(tl_a.entity_id, t_foo_clone.tasklist_id)
        
    """
    TODO: Update test documentation.
    """
    def test_parent_id(self):
        """Test that the parent_id property, if not manually defined, will
        attempt to automatically resolve to the ID of the parent (Task or 
        TaskList).
        
        Ensure that this property is established even for "clean" clones.
        
        Arrange:
        
        Act:
        
        Assert:
                
        """
        ### Arrange ###
        t_parent = TestDataTaskList(None, 'parent')
        t_foo = TestDataTask(t_parent, 'foo')
        t_bar = TestDataTask(t_foo, 'bar')
        t_bar_clone = t_bar.clean_clone()
        
        ### Assert ###
        self.assertEqual(None, t_foo.parent_id)
        self.assertEqual(t_foo.entity_id, t_bar.parent_id)
        self.assertEqual(t_foo.entity_id, t_bar_clone.parent_id)
        
    """
    TODO: This test needs to be documented.
    """
    def test_new_task_ordering(self):
        """
        
        Arrange:
        
        Act:
        
        Assert:
                
        """
        ### Arrange ###
        t_parent = Task(None, title="parent")
        
        ### Act ###
        t_1 = Task(t_parent, title="1")
        t_2 = Task(t_parent, title="")
        
        ### Assert ###
        self.assertEqual([t_1, t_2], t_parent.children)
#------------------------------------------------------------------------------ 

"""
TODO: This class is unnecessary at this point, and needs to be removed.
"""
class GoogleServicesTask(Task):
    def __init__(self, parent, tasklist_id=None, parent_id=None, position=None, **kwargs):
        # GoogleServicesTasks are always persisted.
        super(GoogleServicesTask, self).__init__(parent, parent_id=parent_id,
            tasklist_id=tasklist_id, position=position, is_persisted=True, **kwargs)
    
    @classmethod
    def _create_blank_entity(cls):
        entity = GoogleServicesTask(None)

        return entity
#------------------------------------------------------------------------------

class GoogleServicesTaskTest(unittest.TestCase):        
    def assertLesserGreaterRichComparison(self, lesser, greater):
        self.assertNotEqual(greater, lesser)
        self.assertGreater(greater, lesser)
        self.assertLess(lesser, greater)
        
    def test_from_str_dict_minimal(self):
        """Test converting a dict of str values into a GoogleServiceTask 
        instance.
        
        This dict of str values imitates the results of a query to Google's
        Task Service.
        
        Arrange:
        
        Act:
        
        Assert:
                
        """
        ### Arrange ###
        task_id = "abcid"
        task_title = "task title"
        task_update_timestamp = "2012-03-10T03:30:06.000Z"
        task_position = "00000000001073741823"
        task_status = TaskStatus.NEEDS_ACTION
        task_parent_id = "parent-id"

        str_dict = {
            GoogleKeywords.ID: task_id,
            GoogleKeywords.TITLE: task_title,
            GoogleKeywords.UPDATED: task_update_timestamp,
            GoogleKeywords.POSITION: task_position,
            GoogleKeywords.STATUS: task_status,
            GoogleKeywords.PARENT: task_parent_id
        }

        expected_taskitem = GoogleServicesTask(None)
        expected_taskitem.entity_id = task_id
        expected_taskitem.title = task_title
        expected_taskitem.updated_date = datetime(2012, 3, 10, 3, 30, 6)
        expected_taskitem.position = 1073741823
        expected_taskitem.status = task_status
        expected_taskitem.parent_id = task_parent_id
        
        ### Act ###
        actual_taskitem = GoogleServicesTask.from_str_dict(str_dict)
        
        ### Assert ###
        self.assertEqual(expected_taskitem, actual_taskitem)
        
    def test_ordering_comparison(self):        
        """Test the greater than and lesser than comparison operators.
        
        This tests GoogleServicesTask's implementation of the Python 
        customization/"magic" methods __gt__ and __lt__. Ordering should be 
        based upon a case-insensitive, lexicographical comparison of the
        Task's position, if they have a defined position. 
        
        A position of zero 
        should be considered as undefined and _greater_ than any other defined
        position. This allows for new Tasks to be created without defining a 
        position value while still ordering them at the lowest position among
        their Task sibling group. 
        
        If the positions are equal, the comparison 
        should be between the lexicographical ordering of the title.
        
        Arrange:
            - Create GoogleServicesTasks "1", "02", "3403", "0" (undefined), 
            "0" but with a title defined of Foo and Bar. 
        Assert:
            - That the following comparisons are true:
                - 02 > 1
                - 02 < 3403
                - 0 > 1
                - 0 > 3403
                - 0 Foo > 0 Bar 
        """    
        ### Arrange ###
        gstask_1 = GoogleServicesTask(None, position=1)
        gstask_02 = GoogleServicesTask(None, position=02)
        gstask_3403 = GoogleServicesTask(None, position=3403)
        gstask_undefined = GoogleServicesTask(None)
        gstask_undefined_foo = GoogleServicesTask(None, title="Foo")
        gstask_undefined_bar = GoogleServicesTask(None, title="Bar")
        task_empty = Task(None, title="")

        ### Assert ###
        self.assertLesserGreaterRichComparison(gstask_1, gstask_02)
        self.assertLesserGreaterRichComparison(gstask_02, gstask_3403)
        self.assertLesserGreaterRichComparison(gstask_1, gstask_undefined)
        self.assertLesserGreaterRichComparison(gstask_3403, gstask_undefined)
        self.assertLesserGreaterRichComparison(gstask_undefined_bar, gstask_undefined_foo)
        self.assertLesserGreaterRichComparison(gstask_1, task_empty)
        
    def test_sort_collection(self):
        """Verify that a collection of GoogleServiceTasks sort in the 
        correct order.
        
        Arrange:
            - Create GoogleServicesTasks.
            - Create a collection of expected, sorted Tasks.
            - Create a collection of unordered Tasks.            
        Act:
            - Calculate the actual sorted collection of Tasks.
        Assert:
            - That the expected sorted and actual sorted GoogleServicesTask collections 
            are equal.
        """    
        ### Arrange ###
        task_one = GoogleServicesTask(None, title="one", position=1)
        task_two = GoogleServicesTask(None, title="two", position=2)
        task_three = GoogleServicesTask(None, title="three", position=3)
        
        expected_sorted_tasks = [task_one, task_two, task_three]
        input_tasks = [task_two, task_one, task_three]
        
        ### Act ###
        actual_sorted_tasks = sorted(input_tasks)
        
        ### Assert ###
        self.assertEqual(expected_sorted_tasks, actual_sorted_tasks)
        
    def test_sort_heterogenous_collection(self):
        """Verify that the addition of a new Task to a sibling group that 
        contains only GoogleServicesTasks will be properly ordered at the
        bottom of the sibling group.
        
        Arrange:
            - Create Parent TaskList and GoogleServicesTasks 1, 2.
            - Create an index value where the new Task should be found.
        Act:
            - Create the new Task.
        Assert:
            - Compare the newly created Task with the child that is ordered
            at the bottom of the Parent TaskList children sibling group. 
        """    
        ### Arrange ###
        tasklist = TaskList(None, title="Parent TaskList")
        gtask_1 = GoogleServicesTask(tasklist, title="gtask 1", position=1)
        gtask_2 = GoogleServicesTask(tasklist, title="gtask 2", position=2)
        expected_new_task_child_index = len(tasklist.children)
        
        ### Act ###        
        new_task = Task(tasklist, title="")
        
        ### Assert ###
        self.assertEqual(new_task, tasklist.children[expected_new_task_child_index])

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
    def __init__(self, parent, *short_title_sections, **kwargs):
        # Create a full title from the provided short title.
        title = TestDataEntitySupport.create_full_title(self.__class__, *short_title_sections)

        # Create an entity id from the short title sections.
        entity_id = TestDataEntitySupport.short_title_to_id(*short_title_sections)
        if not entity_id:
            entity_id = TaskList.create_entity_id()
            
        super(TestDataTaskList, self).__init__(parent, entity_id=entity_id, title=title,
            updated_date=datetime.now(), **kwargs)
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
        expected_id = "a"

        ### Act ###
        actual_tasklist_a = TestDataTaskList(None, "A")

        ### Assert ###
        self.assertEqual(expected_long_title, actual_tasklist_a.title)
        self.assertEqual(expected_id, actual_tasklist_a.entity_id)
#------------------------------------------------------------------------------ 

class TestDataTask(Task):
    def __init__(self, parent, *short_title_sections, **kwargs):
        # Create a full title from the provided short title.
        title = TestDataEntitySupport.create_full_title(self.__class__, *short_title_sections)

        # Create an entity id from the short title sections.
        entity_id = TestDataEntitySupport.short_title_to_id(*short_title_sections)
        if not entity_id:
            entity_id = TaskList.create_entity_id()

        super(TestDataTask, self).__init__(parent, entity_id=entity_id, title=title,
            updated_date=datetime.now(), **kwargs)
#------------------------------------------------------------------------------ 

class TestDataTaskTest(unittest.TestCase):
    def test_create_test_task(self):
        """Test the creation of a simple TestDataTask.

        Ensure that the provided short title is properly converted into a
        long title, and the ID is automatically generated from the full title.

        Arrange:
            - Create expected long title "TestDataTask A".
            - Create expected entity ID "testdatatask-a".
        Act:
            - Create new TestDataTask A with short title of "A".
        Assert:
            - That TestDataTask A has the expected long title and entity
            ID.
        """
        ### Arrange ###
        expected_long_title = "TestDataTask A"
        expected_id = "a"

        ### Act ###
        actual_task_a = TestDataTask(None, "A")

        ### Assert ###
        self.assertEqual(expected_long_title, actual_task_a.title)
        self.assertEqual(expected_id, actual_task_a.entity_id)
#------------------------------------------------------------------------------ 

class TestDataGoogleServicesTask(GoogleServicesTask):
    def __init__(self, parent, *short_title_sections, **kwargs):
        # Create a full title from the provided short title.
        title = TestDataEntitySupport.create_full_title(self.__class__, *short_title_sections)

        # Create an entity id from the short title sections.
        entity_id = TestDataEntitySupport.short_title_to_id(*short_title_sections)
        
        # Default to position value in kwargs.
        try:
            position = kwargs["position"]
        except KeyError:
            # Use the short title sections, expected to be single character 
            # ASCII letters, to compute a position. If this assumption about the
            # ASCII letters is incorrect, default to a position of 0.
            try:
                position = self.title_to_position(title)
            except ValueError:
                position = None

        super(TestDataGoogleServicesTask, self).__init__(parent,
            entity_id=entity_id, title=title,
            updated_date=datetime.now(), position=position, **kwargs)
    
    @staticmethod
    def title_to_position(title):
        position = 0
        for char in title:
            try:
                position_index = string.ascii_lowercase.index(char.lower()) + 1
            except ValueError:
                position_index = 0
                
            position = position + position_index
        
        return int(position)
#------------------------------------------------------------------------------ 

class TestDataGoogleServicesTaskTest(unittest.TestCase):
    def test_create_test_task(self):
        """Test the creation of a simple TestDataGoogleServicesTask.

        Ensure that:
        - the provided short title is properly converted into a
        long title
        - the ID is automatically generated from the full title
        - the position is generated from the short title ASCII chars.

        Arrange:
            - Create expected long title "TestDataGoogleServicesTask A-C".
            - Create expected entity ID "testdatagoogleservicestask-a-c".
            - Create expected position value 13.
        Act:
            - Create new TestDataGoogleServicesTask A-C with short title of "A-C".
        Assert:
            - That TestDataTask A has the expected properties:
                - long title
                - entity ID
                - position
        """
        ### Arrange ###
        expected_long_title = "TestDataGoogleServicesTask A-C"
        expected_id = "a-c"
        expected_position = 306

        ### Act ###
        actual_task_a = TestDataGoogleServicesTask(None, *"AC")

        ### Assert ###
        self.assertEqual(expected_long_title, actual_task_a.title)
        self.assertEqual(expected_id, actual_task_a.entity_id)
        self.assertEqual(expected_position, actual_task_a.position)
#------------------------------------------------------------------------------ 

class UpdatedDateIgnoredTestDataTaskList(TestDataTaskList, UpdatedDateFilteredTaskList):
    pass
#------------------------------------------------------------------------------ 

class UpdatedDateIgnoredTestDataTask(TestDataTask, UpdatedDateFilteredTask):
    pass
#------------------------------------------------------------------------------ 

class UpdatedDateIgnoredTestDataGoogleServicesTask(TestDataGoogleServicesTask, UpdatedDateFilteredTask):
    pass
#------------------------------------------------------------------------------ 

class TestDataEntitySupport(object):
    TITLE_SECTION_DIVIDER = "-"
    
    @staticmethod
    def convert_title_to_id(title):
        # Convert to lowercase.
        entity_id = title.lower()

        # Replace spaces with dashes.
        entity_id = entity_id.replace(" ", "-")

        return entity_id

    @staticmethod
    def create_full_title(entity_class, *short_title_sections):    
        # Get the short name of the entity.
        entity_class_name = entity_class.__name__

        # Create full short title by combining short title sections with a
        # special divider character.
        short_title = TestDataEntitySupport.combine_short_title_sections(*short_title_sections)

        # Create a full title by combining the entity's class name and the
        # short title provided.
        full_title = "{class_name} {short_title}".format(
            class_name=entity_class_name, short_title=short_title)

        return full_title
    
    @staticmethod
    def create_task_data_dict(*task_data_entities):
        """
        TODO: This method currently lacks a (unit) test.
        """
        return {x.entity_id:x for x in task_data_entities}
    
    @staticmethod
    def combine_short_title_sections(*short_title_sections):
        """This method combines all of the short title sections provided into
        a single string, separated by the separator defined under
        TestDataEntitySupport.TITLE_SECTION_DIVIDER.
        
        This method filters out any None values to prevent adjacent title 
        section dividers from appearing in the aggregated string.
        """
        
        # Filter out any None values.
        sections = [x for x in short_title_sections if x is not None]
        
        # Return the non-None sections, combined by the title section 
        #$ separator.
        return TestDataEntitySupport.TITLE_SECTION_DIVIDER.join(sections)
    
    @staticmethod
    def short_title_to_id(*short_title_sections):
        # Combine the short title sections, convert them to all lower case, and
        # use that as the entity ID.
        entity_id = TestDataEntitySupport.combine_short_title_sections(*short_title_sections)
        entity_id = entity_id.lower()
        
        return entity_id
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

    def test_create_task_full_title(self):
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
        actual_full_title = TestDataEntitySupport.create_full_title(Task, "A")

        ### Assert ###
        self.assertEqual(expected_full_title, actual_full_title)

    def test_create_task_full_title_from_sections(self):
        """Test creating a full title for a Task entity from a series of short
        title sections.

        Should produce a full title of "Task A-C-C" from the short title 
        sections 'A','C','C'.

        Arrange:
            - Create expected full title "Task A-C-C".
            - Create short title sections 'A-C-C'.
        Act:
            - Convert the short title sections to the actual full title.
        Assert:
            - That the expected and actual full titles are the same.
        """
        ### Arrange ###
        expected_full_title = "Task A-C-C"
        short_title_sections = ['A', 'C', 'C']
        
        ### Act ###
        actual_full_title = TestDataEntitySupport.create_full_title(Task, *short_title_sections)

        ### Assert ###
        self.assertEqual(expected_full_title, actual_full_title)

    def test_short_title_to_id_from_title_sections(self):
        """Test creating an entity ID for a Task entity from a series of short
        title sections.

        Should produce an entity ID of "a-c-c" from the short title 
        sections 'A','C','C'.

        Arrange:
            - Create expected full title "Task A-C-C".
            - Create short title sections 'A-C-C'.
        Act:
            - Convert the short title sections to the actual entity ID.
        Assert:
            - That the expected and actual entity IDs are the same.
        """
        ### Arrange ###
        expected_id = "a-c-c"
        short_title_sections = ['A', 'C', 'C']
        
        ### Act ###
        actual_id = TestDataEntitySupport.short_title_to_id(*short_title_sections)

        ### Assert ###
        self.assertEqual(expected_id, actual_id)
#------------------------------------------------------------------------------ 
