"""
Created on Mar 18, 2012

@author: Clay Carpenter
"""

from datetime import datetime
import unittest
import uuid
import coggrinder.utilities
from coggrinder.entities.properties import EntityProperty, RFC3339Converter, IntConverter, BooleanConverter, TaskStatus, TaskStatusConverter
from coggrinder.utilities import GoogleKeywords
from coggrinder.entities.tree import TreeNode

class TaskList(TreeNode):
    _ARGUMENT_FAIL_MESSAGE = "Provided {0} argument must be of type {1}"
    _KEY_VALUE_MESSAGE = "{key}: {value}"
    
    _properties = (
            EntityProperty("entity_id", GoogleKeywords.ID),
            EntityProperty("title", GoogleKeywords.TITLE),
            EntityProperty("updated_date", GoogleKeywords.UPDATED,
                RFC3339Converter())
        )

    def __init__(self, parent, entity_id=None, title="", updated_date=None, children=None):
        TreeNode.__init__(self, parent, value=self)
        
        # Create a default UUID entity ID if none is provided.
        if entity_id is None:
            entity_id = str(uuid.uuid4())
            
        self.entity_id = entity_id

        self.title = title

        if updated_date is None:
            updated_date = datetime.now()
            
        # Strip the timestamp down to just date (year, month, day) and 
        # a time that includes hours, minutes, and seconds. Microseconds and
        # any timezone info are not preserved.            
        self.updated_date = datetime(updated_date.year, updated_date.month, updated_date.day,
            updated_date.hour, updated_date.minute, updated_date.second)

    @property
    def tasklist(self):
        return self
    
    def attach_to_parent(self, parent, child_index=None):
        try:
            # Locate the root node of the TaskTree this TaskList is 
            # being attached to. If the provided parent reference is not a 
            # Tree-type object, an AttributeError will be raised.
            parent = parent.root_node
        except AttributeError:
            # The provided parent has no root_node property, raise an error.
            raise ValueError("Parent of a TaskList must be a TaskTree.")
        
        TreeNode.attach_to_parent(self, parent, child_index=child_index)

    @classmethod
    def from_str_dict(cls, str_dict):
        # Create a new blank entity.
        entity = cls._create_blank_entity()

        # Loop through each property, converting each string representation 
        # into the correct "object" value for the property.
        for prop in cls._get_properties():
            # For each property, lookup the value of the property in the string
            # dict.
            if str_dict.has_key(prop.str_dict_key):
                # Key is present, convert to object value.
                str_value = str_dict[prop.str_dict_key]

                # Using the property's specific converter, convert from the string 
                # representation to the object value.
                obj_value = prop.from_str(str_value)

                # Push the object value into the new entity's corresponding property.
                entity.__dict__[prop.entity_key] = obj_value

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
        
        return comparable_properties
    
    def __str__(self):
        str_dict = self.to_str_dict()
        ordered_entity_info = self._ordered_entity_info(str_dict)
        
        return "<" + ("; ".join(ordered_entity_info)) + ">"

    def __repr__(self):
        return self.__str__()
    
    def __lt__(self, other):        
        if self.title.lower() < other.title.lower():
            return True
        elif self.title == other.title:
            return self.entity_id.lower() < self.entity_id.lower()
        
        return False
    
    def __gt__(self, other):
        return not self.__lt__(other)
#------------------------------------------------------------------------------ 

class TaskListTest(unittest.TestCase):
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

        self.assertEqual(entity_1, entity_2)

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
        )

    def __init__(self, parent, entity_id=None, title="", updated_date=None,
            task_status=TaskStatus.NEEDS_ACTION):
        super(Task, self).__init__(parent, entity_id, title, updated_date)
        
        self.task_status = task_status

        # Establish default properties.
        self.notes = None
        self.due_date = None
        self.completed_date = None
        self.is_deleted = None
        self.is_hidden = None
                
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
        return self.tasklist.entity_id

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
        base_properties = TaskList._get_comparable_properties(self)
        
        return base_properties

    @classmethod
    def _create_blank_entity(cls):
        entity = Task(None)

        return entity
    
    def __lt__(self, other):
        if self.child_index == other.child_index:
            return super(Task, self).__lt__(other)
        
        # Check for an "undefined" position. This is indicated by a zero value,
        # and such positions should be considered _greater_ than any other
        # defined position value.
        if self.child_index == None:
            return False
        
        if other.child_index == None:
            return True
        
        if self.child_index < other.child_index:
            return True
        
        return False
    
    def __gt__(self, other):
        return not self.__lt__(other)
    
    def attach_to_parent(self, parent, child_index=None):
        # Directly call TreeNode's attach_to_parent implementation, avoiding
        # the implementation used by TaskList.        
        TreeNode.attach_to_parent(self, parent, child_index=child_index)
#------------------------------------------------------------------------------ 

class TaskTest(unittest.TestCase):
    """
    TODO: This test case probably needs to include a couple of tests to ensure
    that equality comparisons (eq, ne) are working properly.
    """
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
#------------------------------------------------------------------------------ 

class GoogleServicesTask(Task):
    _properties = Task._get_properties() + (
            EntityProperty("parent_id", GoogleKeywords.PARENT),
            EntityProperty("position", GoogleKeywords.POSITION, IntConverter())
        )

    def __init__(self, parent, parent_id=None, position=None, **kwargs):
        super(GoogleServicesTask, self).__init__(parent, **kwargs)
        
        self.parent_id = parent_id
        self.position = position
    
    @classmethod
    def _create_blank_entity(cls):
        entity = GoogleServicesTask(None)

        return entity

    def _get_comparable_properties(self):
        base_properties = Task._get_comparable_properties(self)
        base_properties.append("parent_id")
        base_properties.append("position")
        
        return base_properties
    
    def __lt__(self, other):
        try:
            if self.position == other.position:
                return super(Task, self).__lt__(other)
            
            # Check for an "undefined" position. This is indicated by a zero value,
            # and such positions should be considered _greater_ than any other
            # defined position value.
            if self.position == None:
                return False
            
            if other.position == None:
                return True
            
            if self.position < other.position:
                return True
        except AttributeError:
            # In the case of comparisons against another Task-type entity 
            # that lacks a position property, defer to sorting the Tasks
            # by the basic Task implementation (currently by child index).
            return Task.__lt__(self, other) 
        
        return False
#------------------------------------------------------------------------------

class GoogleServicesTaskTest(unittest.TestCase):        
    def assertRichComparison(self, lesser, greater):
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
        entity_1 = GoogleServicesTask(None, position=1)
        entity_02 = GoogleServicesTask(None, position=02)
        entity_3403 = GoogleServicesTask(None, position=3403)
        entity_undefined = GoogleServicesTask(None)
        entity_undefined_foo = GoogleServicesTask(None, title="Foo")
        entity_undefined_bar = GoogleServicesTask(None, title="Bar")

        ### Assert ###
        self.assertRichComparison(entity_1, entity_02)
        self.assertRichComparison(entity_02, entity_3403)
        self.assertRichComparison(entity_1, entity_undefined)
        self.assertRichComparison(entity_3403, entity_undefined)
        self.assertRichComparison(entity_undefined_bar, entity_undefined_foo)
        
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
        """Verify that a collection of Tasks sorts in the correct order.
        
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
        tasklist = TaskList(None, title="Parent TaskList")
        gtask_1 = GoogleServicesTask(tasklist, title="gtask 1", position=1)
        task_1 = Task(tasklist, title="task 1")
        gtask_2 = GoogleServicesTask(tasklist, title="gtask 2", position=2)
        
        expected_sorted_tasks = [gtask_1, task_1, gtask_2]
        input_tasks = [gtask_2, gtask_1, task_1]
        
        ### Act ###
        actual_sorted_tasks = sorted(input_tasks)
        
        ### Assert ###
        self.assertEqual(expected_sorted_tasks, actual_sorted_tasks)

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

        TaskList.__init__(self, parent, entity_id=entity_id, title=title,
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

        Task.__init__(self, parent, entity_id=entity_id, title=title,
            updated_date=datetime.now(), **kwargs)
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
        expected_id = "a"

        ### Act ###
        actual_task_a = TestDataTask(None, "A")

        ### Assert ###
        self.assertEqual(expected_long_title, actual_task_a.title)
        self.assertEqual(expected_id, actual_task_a.entity_id)
#------------------------------------------------------------------------------ 

class UpdatedDateIgnoredTestDataTaskList(TestDataTaskList, UpdatedDateFilteredTaskList):
    pass
#------------------------------------------------------------------------------ 

class UpdatedDateIgnoredTestDataTask(TestDataTask, UpdatedDateFilteredTask):
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

class EntityList(list):
    def get_entity_for_id(self, entity_id):
        matching_entities = [x for x in self if x.entity_id == entity_id]
        
        return matching_entities[0]
#------------------------------------------------------------------------------

class EntityListTest(unittest.TestCase):
    def test_get_entity_for_id_found(self):
        """Test that the get_entity_for_id method can find the correct entity
        given an entity ID to search for.
        
        Arrange:
            - Create a new EntityList.
            - Create an expected TaskList.
        Act:
            - Locate the actual TaskList.
        Assert:
            - Actual and expected TaskLists are identical.
        """
        ### Arrange ###
        entity_id = "tasklist-id"
        expected_tasklist = TaskList(None, entity_id=entity_id, title="TaskList")
        entity_list = EntityList([expected_tasklist])
        
        ### Act ###
        actual_tasklist = entity_list.get_entity_for_id(entity_id)
        
        ### Assert ###
        self.assertEqual(expected_tasklist, actual_tasklist)
#------------------------------------------------------------------------------
