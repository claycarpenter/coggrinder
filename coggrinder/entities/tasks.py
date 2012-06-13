"""
Created on Mar 18, 2012

@author: Clay Carpenter
"""

from datetime import datetime
import unittest
import uuid
import coggrinder.utilities
from coggrinder.core.comparable import DeclaredPropertiesComparable
from coggrinder.entities.properties import EntityProperty, RFC3339Converter, IntConverter, BooleanConverter, TaskStatus, TaskStatusConverter
from coggrinder.utilities import GoogleKeywords

class BaseTaskEntity(DeclaredPropertiesComparable):
    _ARGUMENT_FAIL_MESSAGE = "Provided {0} argument must be of type {1}"
    _KEY_VALUE_MESSAGE = "{key}: {value}"
    
    _properties = (
            EntityProperty("entity_id", GoogleKeywords.ID),
            EntityProperty("title", GoogleKeywords.TITLE),
            EntityProperty("updated_date", GoogleKeywords.UPDATED,
                RFC3339Converter())
        )
    _props_initialized = False

    def __init__(self, entity_id=None, title="", updated_date=None, children=None):
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
        entity = BaseTaskEntity()

        return entity

    @classmethod
    def _get_properties(cls):
        if not cls._props_initialized:
            cls._props_initialized = True
            
        return BaseTaskEntity._properties

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
                prop_values.append(BaseTaskEntity._KEY_VALUE_MESSAGE.format(
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

    def _get_comparable_properties(self):
        comparable_properties = list()
        for prop in self._get_properties():
            comparable_properties.append(prop.entity_key)
        
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

class BaseTaskEntityTest(unittest.TestCase):
    def test_creation(self):
        # This should work.
        BaseTaskEntity("aljkdfkj", "Title")

        # Using a string as an updated_date timestamp should fail.
        with self.assertRaises(AttributeError):
            BaseTaskEntity("aljkdfkj", "Title", 29)

        # Using a real datetime object for the updated_date timestamp should work.
        last_updated = datetime.now()
        BaseTaskEntity("aljkdfkj", "Title", last_updated)

    def test_equality(self):
        entity_id = "1"
        title = "Title"
        updated_date = datetime.now()
        entity_1 = BaseTaskEntity(entity_id, title, updated_date=updated_date)
        entity_2 = BaseTaskEntity(entity_id, title, updated_date=updated_date)

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
        entity_foo = BaseTaskEntity(title="Foo")
        entity_bar = BaseTaskEntity(title="Bar")
        entity_barber = BaseTaskEntity(title="Barber")
        entity_empty = BaseTaskEntity(title="")
        entity_special_char = BaseTaskEntity(title="_special_char")

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
            - That the expected sorted and actual sorted BaseTaskEntity 
            collections are equal.
        """    
        ### Arrange ###
        foo = BaseTaskEntity(title="foo")
        bar = BaseTaskEntity(title="bar")
        baz = BaseTaskEntity(title="Baz")
        
        expected_sorted_entities = [bar, baz, foo]
        input_entities = [foo, bar, baz]
        
        ### Act ###
        actual_sorted_entities = sorted(input_entities)
        
        ### Assert ###
        self.assertEqual(expected_sorted_entities, actual_sorted_entities)

    def test_from_str_dict(self):
        expected_entity = BaseTaskEntity(entity_id="1",
            title="Test List Title",
            updated_date=datetime(2012, 3, 10, 3, 30, 06))
        rfc_timestamp = "2012-03-10T03:30:06.000Z"

        keywords = coggrinder.utilities.GoogleKeywords
        entity_dict = {keywords.ID:expected_entity.entity_id,
            keywords.TITLE:expected_entity.title,
            keywords.UPDATED:rfc_timestamp}

        result_entity = BaseTaskEntity.from_str_dict(entity_dict)

        self.assertEqual(expected_entity, result_entity)

    def test_to_dict(self):
        entity = BaseTaskEntity(entity_id="1",
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
        entity = BaseTaskEntity(entity_id="1", title="Test List Title")

        keywords = coggrinder.utilities.GoogleKeywords
        expected_dict = {keywords.TITLE:entity.title}

        result_dict = entity.to_insert_dict()

        self.assertEqual(expected_dict, result_dict)
#------------------------------------------------------------------------------ 

class TaskList(BaseTaskEntity):
    """
    This class is little more than a marker class intended to make it more 
    clear whether a TaskList or Task entity is being used. A TaskList is 
    otherwise (functionally) identical to the BaseTaskEntity class. 
    """
    @classmethod
    def _create_blank_entity(cls):
        # A tasklist is basically a BaseTaskEntity, but the 
        # _create_blank_entity method is overridden here in order to create
        # an object that is an instance of type TaskList.
        entity = TaskList()

        return entity

#------------------------------------------------------------------------------ 

class Task(BaseTaskEntity):
    _properties = (
            EntityProperty("parent_id", GoogleKeywords.PARENT),
            EntityProperty("position", GoogleKeywords.POSITION, IntConverter()),
            EntityProperty("notes", GoogleKeywords.NOTES),
            EntityProperty("task_status", GoogleKeywords.STATUS, TaskStatusConverter()),
            EntityProperty("due_date", GoogleKeywords.DUE, RFC3339Converter()),
            EntityProperty("completed_date", GoogleKeywords.COMPLETED, RFC3339Converter()),
            EntityProperty("is_deleted", GoogleKeywords.DELETED, BooleanConverter()),
            EntityProperty("is_hidden", GoogleKeywords.HIDDEN, BooleanConverter()),
        )
    _props_initialized = False

    def __init__(self, tasklist_id=None, entity_id=None, title="", updated_date=None,
            parent_id=None, task_status=TaskStatus.NEEDS_ACTION,
            position=None, previous_task_id=None):
        super(Task, self).__init__(entity_id, title, updated_date)

        self.parent_id = parent_id
        self.task_status = task_status
        self.tasklist_id = tasklist_id
        self.previous_task_id = previous_task_id

        # Establish default properties.
        self.notes = None
        self.due_date = None
        self.completed_date = None
        self.is_deleted = None
        self.is_hidden = None
        self.position = position

    def _get_filter_keys(self):
        base_keys = super(Task, self)._get_filter_keys()

        keywords = coggrinder.utilities.GoogleKeywords
        taskitem_keys = (keywords.COMPLETED, keywords.NOTES, keywords.POSITION,
            keywords.PARENT, keywords.STATUS)

        taskitem_keys = taskitem_keys + base_keys

        return taskitem_keys

    @classmethod
    def _get_properties(cls):        
        # Check the class initialization variable to see whether the properties
        # have been aggregated already or not.   
        if not cls._props_initialized:
            # Properties have not been initialized, so work recursively up the
            # inheritance chain to grab all ancestor properties.
            super_properties = super(Task, cls)._get_properties()

            # Aggregate those properties along with this class' particular
            # property definitions.
            cls._properties = super_properties + cls._properties            

        # Return combined properties. 
        return cls._properties

    def _get_comparable_properties(self):
        base_properties = BaseTaskEntity._get_comparable_properties(self)
        base_properties.append("previous_task_id")
        
        return base_properties

    def _ordered_entity_info(self, str_dict):
        ordered_entity_info = BaseTaskEntity._ordered_entity_info(self, str_dict)
                
        ordered_entity_info.append(BaseTaskEntity._KEY_VALUE_MESSAGE.format(
            key="previous_task_id", value=self.previous_task_id))
        
        return ordered_entity_info

    @classmethod
    def _create_blank_entity(cls):
        entity = Task()

        return entity
    
    def __lt__(self, other):
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
        
        return False
    
    def __gt__(self, other):
        return not self.__lt__(other)
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
        task_position = "1073741823"
        task_status = TaskStatus.NEEDS_ACTION

        expected_str_dict = {
            GoogleKeywords.ID: task_id,
            GoogleKeywords.TITLE: task_title,
            GoogleKeywords.UPDATED: task_update_timestamp,
            GoogleKeywords.POSITION: task_position,
            GoogleKeywords.STATUS: task_status
        }

        taskitem = Task()
        taskitem.entity_id = task_id
        taskitem.title = task_title
        taskitem.updated_date = datetime(2012, 3, 10, 3, 30, 6)
        taskitem.position = 1073741823
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

        expected_taskitem = Task()
        expected_taskitem.entity_id = task_id
        expected_taskitem.title = task_title
        expected_taskitem.updated_date = datetime(2012, 3, 10, 3, 30, 6)
        expected_taskitem.position = 1073741823
        expected_taskitem.status = task_status

        actual_taskitem = Task.from_str_dict(str_dict)

        self.assertEqual(expected_taskitem, actual_taskitem)

    def test_ordering_comparison(self):        
        """Test the greater than and lesser than comparison operators.
        
        This tests Task's implementation of the Python 
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
            - Create Tasks "1", "02", "3403", "0" (undefined), "0" but with a
            title defined of Foo and Bar. 
        Assert:
            - That the following comparisons are true:
                - 02 > 1
                - 02 < 3403
                - 0 > 1
                - 0 > 3403
                - 0 Foo > 0 Bar 
        """    
        ### Arrange ###
        entity_1 = Task(position=1)
        entity_02 = Task(position=02)
        entity_3403 = Task(position=3403)
        entity_undefined = Task()
        entity_undefined_foo = Task(title="Foo")
        entity_undefined_bar = Task(title="Bar")

        ### Assert ###
        self.assertRichComparison(entity_1, entity_02)
        self.assertRichComparison(entity_02, entity_3403)
        self.assertRichComparison(entity_1, entity_undefined)
        self.assertRichComparison(entity_3403, entity_undefined)
        self.assertRichComparison(entity_undefined_bar, entity_undefined_foo)
        
    def test_sort_collection(self):
        """Verify that a collection of Tasks sorts in the correct order.
        
        Arrange:
            - Create Tasks.
            - Create a collection of expected, sorted Tasks.
            - Create a collection of unordered Tasks.            
        Act:
            - Calculate the actual sorted collection of Tasks.
        Assert:
            - That the expected sorted and actual sorted Task collections 
            are equal.
        """    
        ### Arrange ###
        task_one = Task(title="one", position=1)
        task_two = Task(title="two", position=2)
        task_three = Task(title="three", position=3)
        
        expected_sorted_tasks = [task_one, task_two, task_three]
        input_tasks = [task_two, task_one, task_three]
        
        ### Act ###
        actual_sorted_tasks = sorted(input_tasks)
        
        ### Assert ###
        self.assertEqual(expected_sorted_tasks, actual_sorted_tasks)
        
    def assertRichComparison(self, lesser, greater):
        self.assertNotEqual(greater, lesser)
        self.assertGreater(greater, lesser)
        self.assertLess(lesser, greater)
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
    def __init__(self, *short_title_sections, **kwargs):
        # Create a full title from the provided short title.
        title = TestDataEntitySupport.create_full_title(self.__class__, *short_title_sections)

        # Create an entity id from the short title sections.
        entity_id = TestDataEntitySupport.short_title_to_id(*short_title_sections)

        TaskList.__init__(self, entity_id=entity_id, title=title,
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
        actual_tasklist_a = TestDataTaskList("A")

        ### Assert ###
        self.assertEqual(expected_long_title, actual_tasklist_a.title)
        self.assertEqual(expected_id, actual_tasklist_a.entity_id)
#------------------------------------------------------------------------------ 

class TestDataTask(Task):
    def __init__(self, *short_title_sections, **kwargs):
        # Create a full title from the provided short title.
        title = TestDataEntitySupport.create_full_title(self.__class__, *short_title_sections)

        # Create an entity id from the short title sections.
        entity_id = TestDataEntitySupport.short_title_to_id(*short_title_sections)

        Task.__init__(self, entity_id=entity_id, title=title,
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
        actual_task_a = TestDataTask("A")

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

"""
TODO: This class doesn't appear to be used--candidate for cruft removal.
"""
class TaskDataSorter(object):
    @classmethod
    def sort_task_data(cls, task_data):
        # Group all of the entities in the task data by their direct parents.
        # TaskLists, which have no parent, will be grouped by None. 
        task_data_by_parent = dict()
        for entity in task_data:
            parent_entity_id = cls._find_direct_parent(entity)
            
            try:
                task_data_by_parent[parent_entity_id].append(entity)
            except (KeyError, AttributeError):
                task_data_by_parent[parent_entity_id] = [entity]
        
        # Sort the task entities recursively.
        sorted_task_data = cls._sort_recursively(task_data_by_parent, None)        
        
        return sorted_task_data
    
    @classmethod
    def sort_task_data_subset(cls, task_data, subset_entity_ids):
        sorted_task_data = cls.sort_task_data(task_data)
        
        sorted_task_data_subset = list()
        for task_data_entity in sorted_task_data:
            if task_data_entity.entity_id in subset_entity_ids:
                sorted_task_data_subset.append(task_data_entity) 
        
        return sorted_task_data_subset
    
    @classmethod
    def _sort_recursively(cls, task_data_by_parent, parent_id):        
        # Get all entities belonging to the current parent_id.
        try:
            child_entities = task_data_by_parent[parent_id]
            
            # Iterate through the sorted entities, adding each to the sorted
            # task data list before recursively adding the entity's children.        
            sorted_task_data = list()
            for child_entity in sorted(child_entities):
                sorted_task_data.append(child_entity)
                
                sorted_children = cls._sort_recursively(task_data_by_parent, child_entity.entity_id)
                if sorted_children:
                    sorted_task_data.extend(sorted_children)
            
            return sorted_task_data
        except KeyError:
            # The specified parent entity has no child entities.
            return []        
    
    @classmethod
    def _find_direct_parent(cls, entity):        
        try:
            parent_entity_id = entity.parent_id
            
            if parent_entity_id is None:
                parent_entity_id = entity.tasklist_id
                
            return parent_entity_id
        except AttributeError:
            # Entity is a TaskList, parent ID is None.
            return None
#------------------------------------------------------------------------------ 

class TaskDataSorterTest(unittest.TestCase):        
    def test_sort_task_data_tasklists_only(self):
        """Verify the TaskDataSorter sorting a collection of task data that 
        contains only TaskLists.
        
        Arrange:
            - Create TaskLists.
            - Create a collection of expected, sorted TaskLists.
            - Create a collection of unordered TaskLists.            
        Act:
            - Retrieve the actual sorted collection of TaskLists 
            from TaskDataSorter.
        Assert:
            - That the expected sorted and actual sorted TaskList collections 
            are equal.
        """    
        ### Arrange ###
        tasklist_foo = TestDataTaskList("foo")
        tasklist_bar = TestDataTaskList("bar")
        tasklist_baz = TestDataTaskList("Baz")
        
        expected_sorted_task_data = [tasklist_bar, tasklist_baz, tasklist_foo]
        input_task_data = [tasklist_foo, tasklist_bar, tasklist_baz]
        
        ### Act ###
        actual_sorted_task_data = TaskDataSorter.sort_task_data(input_task_data)
        
        ### Assert ###
        self.assertEqual(expected_sorted_task_data, actual_sorted_task_data)
        
    def test_sort_task_data_simple_tree(self):
        """Verify the TaskDataSorter sorting a collection of task data that 
        a simple task data tree.
        
        Test tree architecture:
        - tl-a
            - t-a-a
            - t-a-b
        - tl-b
            - t-b-a
                - t-b-a-a        
        
        Arrange:
            - Create task data entities.
            - Create a collection of expected, sorted subset entities.
            - Create a collection of unordered TaskLists.            
        Act:
            - Retrieve the actual sorted collection of TaskLists 
            from TaskDataSorter.
        Assert:
            - That the expected sorted and actual sorted TaskList collections 
            are equal.
        """    
        ### Arrange ###
        tasklist_a = TestDataTaskList("a")
        tasklist_b = TestDataTaskList("b")

        task_aa = TestDataTask("a-a", tasklist_id=tasklist_a.entity_id, position=1)
        task_ab = TestDataTask("a-b", tasklist_id=tasklist_a.entity_id, position=2)

        task_ba = TestDataTask("b-a", tasklist_id=tasklist_b.entity_id, position=1)
        task_bba = TestDataTask("b-b-a", tasklist_id=tasklist_b.entity_id,
            parent_id=task_ba.entity_id, position=1)
        
        input_task_data = [task_ba, tasklist_b, tasklist_a, task_aa, task_bba, task_ab]
        expected_sorted_task_data = [tasklist_a, task_aa, task_ab, tasklist_b, task_ba, task_bba]
        
        ### Act ###
        actual_sorted_task_data = TaskDataSorter.sort_task_data(input_task_data)
        
        ### Assert ###
        self.assertEqual(expected_sorted_task_data, actual_sorted_task_data)
        
    def test_sort_task_data_subset_simple_tree(self):
        """Verify the TaskDataSorter finding a subset of ordered entities 
        amongst a large task data set.
        
        Test tree architecture:        
        - tl-a
            - t-a-a
            - t-a-b
        - tl-b
            - t-b-a
                - t-b-a-a        
        
        Arrange:
            - Create task data entities.
            - Create a collection of expected, sorted entities.
            - Create a collection of unordered task data.            
        Act:
            - Retrieve the actual sorted subset collection of task data 
            from TaskDataSorter.
        Assert:
            - That the expected sorted and actual sorted subset collections 
            are equal.
        """    
        ### Arrange ###
        tasklist_a = TestDataTaskList("a")
        tasklist_b = TestDataTaskList("b")

        task_aa = TestDataTask("a-a", tasklist_id=tasklist_a.entity_id, position=1)
        task_ab = TestDataTask("a-b", tasklist_id=tasklist_a.entity_id, position=2)

        task_ba = TestDataTask("b-a", tasklist_id=tasklist_b.entity_id, position=1)
        task_bba = TestDataTask("b-b-a", tasklist_id=tasklist_b.entity_id,
            parent_id=task_ba.entity_id, position=1)
        
        input_task_data = [task_ba, tasklist_b, tasklist_a, task_aa, task_bba, task_ab]
        task_data_subset_ids = [x.entity_id for x in [tasklist_a, task_aa, task_bba]]
        expected_task_data_subset = [tasklist_a, task_aa, task_bba]
        
        ### Act ###
        actual_task_data_subset = TaskDataSorter.sort_task_data_subset(input_task_data, task_data_subset_ids)
        
        ### Assert ###
        self.assertEqual(expected_task_data_subset, actual_task_data_subset)
#------------------------------------------------------------------------------
