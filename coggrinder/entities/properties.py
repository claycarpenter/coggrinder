"""
Created on Mar 22, 2012

@author: Clay Carpenter
"""

import unittest
import datetime
import re

class EntityProperty(object):
    def __init__(self, entity_key, str_dict_key, converter=None, is_required=False):
        self.entity_key = entity_key
        self.str_dict_key = str_dict_key
        self.is_required = is_required
        
        # The default converter is a StrConverter.
        if converter is None:
            converter = StrConverter()
        self.converter = converter
    
    def from_str(self, str_value):
        return self.converter.from_str(str_value)  
    
    def to_str(self, obj_value):
        return self.converter.to_str(obj_value)
    
    def __str__(self):
        return "Converter: ({0}, {1}, {2})".format(self.entity_key, self.str_dict_key, self.converter)
    
    def __repr__(self):
        return self.__str__()          
#------------------------------------------------------------------------------ 

class PropertyConverter(object):
    _ABSTRACT_ERROR_MESSAGE = "Abstract method cannot be called."
    
    def from_str(self, str_value):
        raise NotImplementedError(PropertyConverter._ABSTRACT_ERROR_MESSAGE)
    
    def to_str(self, obj_value):
        raise NotImplementedError(PropertyConverter._ABSTRACT_ERROR_MESSAGE)
#------------------------------------------------------------------------------ 

class StrConverter(PropertyConverter):    
    def from_str(self, str_value):
        # Clean the incoming string of leading or trailing whitespace.
        str_value = str_value.strip()
        
        # If the string value is blank, consider it equivalent to None.
        if str_value == "":
            obj_value = None
        else:
            obj_value = str(str_value)
                        
        return obj_value
    
    def to_str(self, obj_value):
        # If the object value is None, keep it as None--don't convert back to 
        # an empty string.
        if obj_value is None:
            str_value = None
        else:
            str_value = str(obj_value)
            
            # Clean the outgoing string of leading or trailing whitespace.
            str_value = str_value.strip()
            
            # If the result is an emtpy string, return None instead.
            if str_value == "":
                str_value = None
                    
        return str_value
#------------------------------------------------------------------------------ 

class StrConverterTest(unittest.TestCase):        
        
    def test_to_str_empty(self):
        obj_value = ""
        
        str_value = StrConverter().to_str(obj_value)
        
        self.assertEqual(None, str_value)     
        
    def test_from_empty_str(self):
        # Blank/empty string; should be interpreted as None.
        str_value = ""
        
        # Convert the (empty) string to it's object value (None).
        obj_value = StrConverter().from_str(str_value)
        
        self.assertIsNone(obj_value)
        
    def test_to_str_none_value(self):
        obj_value = None
        
        str_value = StrConverter().to_str(obj_value)
        
        self.assertEqual(None, str_value)
#------------------------------------------------------------------------------ 

class RFC3339Converter(PropertyConverter):
    """            
    This convertor ignores the microsecond and timezone values.
    """
    _RFC3339_REGEX = r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\."
    _DATE_FORMAT = ""

    # TODO: This doesn't count blank strings as None, and vice versa.
    def to_str(self, obj_value):
        # Check if the value is None, in which case return a None object. 
        # An empty string cannot be used here because Google will balk at emtpy 
        # strings provided for date properties.
        if obj_value is None:
            str_value = None
        else:
            # Ensure that a proper datetime object has been provided
            assert isinstance(obj_value, datetime.datetime)
            
            # Ask datetime to convert the date to an RFC3339-formatted timestamp.
            str_value = obj_value.strftime("%Y-%m-%dT%H:%M:%S")
            
            # Add blank microsecond and default timezone values.
            str_value = str_value + ".000Z"
            
        # Return the string timestamp representation.
        return str_value

    def from_str(self, str_value):        
        # If the string is blank/emtpy (after trimming), interpret it as None.
        if str_value == "" or str_value is None:
            obj_value = None
        else:
            # Trim any leading or trailing whitespace.
            str_value = str_value.strip()
            
            # Remove the trailing microsecond and timezone information from the 
            # timestamp.    
            match_result = re.match(RFC3339Converter._RFC3339_REGEX, str_value)
            assert match_result is not None, "Could not parse the provided timestamp: {0}".format(str_value)
            stripped_timestamp = match_result.groups()[0]
            
            # Convert the timestamp (now stripped of microsecond and timezone info)
            # into a datetime object.
            obj_value = datetime.datetime.strptime(stripped_timestamp,
                "%Y-%m-%dT%H:%M:%S")
        
        return obj_value
#------------------------------------------------------------------------------ 

class RFC3339ConverterTest(unittest.TestCase):        
    def test_from_str(self):
        # RFC3339-formatted timestamp.
        rfc_timestamp = "2012-03-10T03:30:06.000Z"
        
        # Convert the timestamp to a datetime object.
        datetime_timestamp = RFC3339Converter().from_str(rfc_timestamp)
        
        # Check for validity.    
        self.assertEqual(datetime_timestamp.year, 2012)
        self.assertEqual(datetime_timestamp.month, 3)
        self.assertEqual(datetime_timestamp.day, 10)
        self.assertEqual(datetime_timestamp.hour, 3)
        self.assertEqual(datetime_timestamp.minute, 30)
        self.assertEqual(datetime_timestamp.second, 6)
        
    def test_from_str_empty(self):
        # Blank timestamp string; should be interpreted as None.
        rfc_timestamp = ""
        
        # Convert the timestamp to a datetime object.
        datetime_timestamp = RFC3339Converter().from_str(rfc_timestamp)
        
        self.assertIsNone(datetime_timestamp)
        
    def test_from_str_none(self):
        # None value for the timestamp (i.e., undefined/ignored property value)
        rfc_timestamp = None
        
        # Convert the timestamp to a datetime object.
        datetime_timestamp = RFC3339Converter().from_str(rfc_timestamp)
        
        self.assertIsNone(datetime_timestamp)
        
    def test_to_str(self):        
        date_timestamp = datetime.datetime(2012, 3, 10, 3, 30, 6)
        
        rfc_timestamp = RFC3339Converter().to_str(date_timestamp)
        
        self.assertEqual("2012-03-10T03:30:06.000Z", rfc_timestamp)
        
    def test_to_str_none_value(self):
        date_timestamp = None
        
        rfc_timestamp = RFC3339Converter().to_str(date_timestamp)
        
        self.assertEqual(None, rfc_timestamp)
#------------------------------------------------------------------------------ 

class IntConverter(PropertyConverter):
    def from_str(self, str_value):
        # Clean the incoming string of leading or trailing whitespace.
        str_value = str_value.strip()
                
        if str_value == "":
            # If the string value is blank, consider it equivalent to None.
            obj_value = None
        else:
            # Convert the string to an int value.
            obj_value = int(str_value)
                        
        return obj_value
    
    def to_str(self, obj_value):                
        if obj_value is None:
            # If the object value is None, convert it to a blank/empty string.
            str_value = ""
        else:
            # Ensure that a proper int value has been provided.            
            assert isinstance(obj_value, int), "Provided property object value must be of type int."
            
            # Convert the integer to its string representation.
            str_value = str(obj_value)
                    
        return str_value
#------------------------------------------------------------------------------ 

class IntConverterTest(unittest.TestCase):
    def test_from_str(self):
        str_value = "12103"
        expected_obj_value = 12103
        
        actual_obj_value = IntConverter().from_str(str_value)
        
        self.assertEqual(expected_obj_value, actual_obj_value)
        
    def test_from_empty_str(self):
        str_value = ""
        expected_obj_value = None
        
        actual_obj_value = IntConverter().from_str(str_value)
        
        self.assertEqual(expected_obj_value, actual_obj_value)
    
    def test_from_invalid_str(self):
        str_value = "1.5"
        
        with self.assertRaises(ValueError):
            IntConverter().from_str(str_value)
        
    def test_to_str(self):
        obj_value = 121044
        expected_str_value = "121044"
        
        actual_str_value = IntConverter().to_str(obj_value)
        
        self.assertEqual(expected_str_value, actual_str_value)
        
    def test_to_str_none_value(self):
        obj_value = None
        expected_str_value = ""
        
        actual_str_value = IntConverter().to_str(obj_value)
        
        self.assertEqual(expected_str_value, actual_str_value)
    
    def test_to_str_float_value(self):
        obj_value = 1.5
        
        with self.assertRaises(AssertionError):
            IntConverter().to_str(obj_value)
#------------------------------------------------------------------------------ 

class BooleanConverter(PropertyConverter):
    def from_str(self, str_value):
        # Check to see if the conversion has already been done. This can happen
        # if the data transmission framework automatically does these 
        # conversions before the information is sent to the entity.
        if type(str_value) == bool:
            obj_value = str_value
        else:
            # Clean the incoming string of leading or trailing whitespace.
            str_value = str_value.strip()
                    
            if str_value == "":
                # If the string value is blank, consider it equivalent to False.
                obj_value = False
            else:
                # Convert the string to a normalized/parseable format.
                str_value = str_value.lower()
                
                # If the normalized string is equal to "true", the object value is
                # True. Otherwise, it will be False.
                if str_value == "true":
                    obj_value = True
                elif str_value == "false":
                    obj_value = False
                else:
                    raise ValueError("Boolean property values must be represented in a string as either 'true' or 'false'.")
                        
        return obj_value
    
    def to_str(self, obj_value):                
        if obj_value is None:
            # If the object value is None, represent it as False.
            str_value = str(False).lower()
        else:
            # Ensure that a proper bool value has been provided.            
            assert isinstance(obj_value, bool), "Provided property object value must be of type bool."
            
            # Convert the bool to its string representation, and then convert
            # that representation to all lowercase characters.
            str_value = str(obj_value).lower()
                    
        return str_value
#------------------------------------------------------------------------------ 

class BooleanConverterTest(unittest.TestCase):
    def test_from_str_false(self):
        str_value = "false"
        expected_obj_value = False
        
        actual_obj_value = BooleanConverter().from_str(str_value)
        
        self.assertEqual(expected_obj_value, actual_obj_value)
        
    def test_from_str_true(self):
        str_value = "true"
        expected_obj_value = True
        
        actual_obj_value = BooleanConverter().from_str(str_value)
        
        self.assertEqual(expected_obj_value, actual_obj_value)
        
    def test_from_empty_str(self):
        str_value = ""
        expected_obj_value = False
        
        actual_obj_value = BooleanConverter().from_str(str_value)
        
        self.assertEqual(expected_obj_value, actual_obj_value)
    
    def test_from_invalid_str(self):
        str_value = "garbage"
        
        with self.assertRaises(ValueError):
            BooleanConverter().from_str(str_value)
        
    def test_to_str_false_value(self):
        obj_value = False
        expected_str_value = "false"
        
        actual_str_value = BooleanConverter().to_str(obj_value)
        
        self.assertEqual(expected_str_value, actual_str_value)
        
    def test_to_str_true_value(self):
        obj_value = True
        expected_str_value = "true"
        
        actual_str_value = BooleanConverter().to_str(obj_value)
        
        self.assertEqual(expected_str_value, actual_str_value)
        
    def test_to_str_none_value(self):
        obj_value = None
        expected_str_value = "false"
        
        actual_str_value = BooleanConverter().to_str(obj_value)
        
        self.assertEqual(expected_str_value, actual_str_value)
#------------------------------------------------------------------------------ 
  
class TaskStatus(object):
    NEEDS_ACTION = "needsAction"
    COMPLETED = "completed"
#------------------------------------------------------------------------------ 

class TaskStatusConverter(PropertyConverter):
    def from_str(self, str_value):
        # Clean the incoming string of leading or trailing whitespace.
        str_value = str_value.strip()
                
        if str_value == "":
            # If the string value is blank, interpret it as None.
            # Note: looking at the Google API docs, this case doesn't seem 
            # possible.
            obj_value = None
        elif str_value == TaskStatus.COMPLETED:
            obj_value = TaskStatus.COMPLETED
        elif str_value == TaskStatus.NEEDS_ACTION:
            obj_value = TaskStatus.NEEDS_ACTION
        else:
            raise ValueError("Could not interpret the task status value.")
                    
        return obj_value
    
    def to_str(self, obj_value):        
        if obj_value is None:
            # If the object value is None, represent it as an empty string ("").
            str_value = ""
        elif obj_value == TaskStatus.COMPLETED or obj_value == TaskStatus.NEEDS_ACTION:
            str_value = str(obj_value)
        else:
            raise ValueError("Object value cannot be recognized as a valid TaskStatus state.")
        
        return str_value
#------------------------------------------------------------------------------ 

class TaskStatusConverterTest(unittest.TestCase):
    def _confirm_from_str(self, converter_type, str_value, expected_obj_value):
        actual_obj_value = converter_type().from_str(str_value)
        
        self.assertEqual(actual_obj_value, expected_obj_value)
        
    def _confirm_to_str(self, converter_type, obj_value, expected_str_value):
        actual_str_value = converter_type().to_str(obj_value)
        
        self.assertEqual(expected_str_value, actual_str_value)
        
    def test_from_str_empty(self):
        str_value = ""
        expected_obj_value = None
        
        self._confirm_from_str(TaskStatusConverter, str_value,
            expected_obj_value)
        
    def test_from_str_needs_action(self):
        str_value = "needsAction"
        expected_obj_value = TaskStatus.NEEDS_ACTION
        
        self._confirm_from_str(TaskStatusConverter, str_value,
            expected_obj_value)
        
    def test_from_str_completed(self):
        str_value = "completed"
        expected_obj_value = TaskStatus.COMPLETED
        
        self._confirm_from_str(TaskStatusConverter, str_value,
            expected_obj_value)
        
    def test_to_str_none(self):
        obj_value = None
        expected_str_value = ""
        
        self._confirm_to_str(TaskStatusConverter, obj_value, expected_str_value)
        
    def test_to_str_completed(self):
        obj_value = TaskStatus.COMPLETED
        expected_str_value = "completed"
        
        self._confirm_to_str(TaskStatusConverter, obj_value, expected_str_value)
        
    def test_to_str_needs_action(self):
        obj_value = TaskStatus.NEEDS_ACTION
        expected_str_value = "needsAction"
        
        self._confirm_to_str(TaskStatusConverter, obj_value, expected_str_value)

    def test_to_str(self):
        return
#------------------------------------------------------------------------------ 
