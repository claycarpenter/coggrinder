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
    _properties = (
            EntityProperty("entity_id", GoogleKeywords.ID), 
            EntityProperty("title", GoogleKeywords.TITLE),
            EntityProperty("updated_date", GoogleKeywords.UPDATED,
                RFC3339Converter()),
            EntityProperty("e_tag", GoogleKeywords.ETAG), # Tracking this property may not be necessary as the updated (date) can be used instead.
        )
    _props_initialized = False

    def __init__(self, entity_id=None, title="", updated_date=None, children=None):
        if entity_id is not None:
            assert isinstance(entity_id, str), \
                BaseTaskEntity._ARGUMENT_FAIL_MESSAGE.format("entity_id", "str")
        else:
            entity_id = str(uuid.uuid4())
            
        self.entity_id = entity_id

        if title is not None:
            assert isinstance(title, str), \
                BaseTaskEntity._ARGUMENT_FAIL_MESSAGE.format("title", "str")
        self.title = title

        if updated_date is not None:
            assert isinstance(updated_date, datetime), \
            BaseTaskEntity._ARGUMENT_FAIL_MESSAGE.format("updated_date", "datetime")

            # Strip the timestamp down to just date (year, month, day) and 
            # a time that includes hours, minutes, and seconds. Microseconds and
            # any timezone info are not preserved.            
            updated_date = datetime(updated_date.year, updated_date.month, updated_date.day,
                updated_date.hour, updated_date.minute, updated_date.second)

        self.updated_date = updated_date
        
        self.e_tag = None

        # If children is None, initialize to an empty list.
        if children is None:
            self.children = []
        else:
            self.children = children

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
                prop_values.append("{key}: {value}".format(
                    key=prop.entity_key, value=prop_value))
            except KeyError:
                # Property isn't defined in this str dict, which is (usually?)
                # ok.
                pass
        
        return ", ".join(prop_values)

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
        return str(self._ordered_entity_info(str_dict))

    def __repr__(self):
        return self.__str__()
    
    def __lt__(self, other):
        if self.title.lower() < other.title.lower():
            return True
        
        return False
    
    def __gt__(self, other):
        return not self.__lt__(other)
#------------------------------------------------------------------------------ 

class BaseTaskEntityTest(unittest.TestCase):
    def test_creation(self):
        # This should work.
        BaseTaskEntity("aljkdfkj", "Title")

        # Using a string as an updated_date timestamp should fail.
        with self.assertRaises(AssertionError):
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

    def __init__(self, tasklist_id=None, entity_id=None, title="", updated_date=None,
            children=None, parent_id=None, task_status=TaskStatus.NEEDS_ACTION,
            position=0):
        super(Task, self).__init__(entity_id, title, updated_date, children)

        self.parent_id = parent_id
        self.task_status = task_status
        self.tasklist_id = tasklist_id

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
            cls._properties = cls._properties + super_properties            

        # Return combined properties. 
        return cls._properties

    @classmethod
    def _create_blank_entity(cls):
        entity = Task()

        return entity
    
    def __lt__(self, other):
        # Check for an "undefined" position. This is indicated by a zero value,
        # and such positions should be considered _greater_ than any other
        # defined position value.
        if self.position == 0:
            return False
        
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
        
        Arrange:
            - Create Tasks "1", "02", "3403", "0" (undefined). 
        Assert:
            - That the following comparisons are true:
                - 02 > 1
                - 02 < 3403
                - 0 > 1
                - 0 > 3403
        """    
        ### Arrange ###
        entity_1 = Task(position=1)
        entity_02 = Task(position=02)
        entity_3403 = Task(position=3403)
        entity_undefined = Task()

        ### Assert ###
        self.assertGreater(entity_02, entity_1)
        self.assertLess(entity_02, entity_3403)
        self.assertGreater(entity_undefined, entity_1)
        self.assertGreater(entity_undefined, entity_3403)
#------------------------------------------------------------------------------ 
