"""
Created on Mar 20, 2012

@author: Clay Carpenter
"""

import unittest
import logging 

class GoogleKeywords(object):
    # Base properties
    ID = "id"
    ETAG = "etag"
    TITLE = "title"
    UPDATED = "updated"
    
    # Result collection properties
    ITEMS = "items"
    
    # TaskItem properties
    COMPLETED = "completed"
    DELETED = "deleted"
    DUE = "due"
    HIDDEN = "hidden"
    NOTES = "notes"
    POSITION = "position"
    PARENT = "parent"
    STATUS = "status"
    
"""
TODO: Should this class actually just be a FilteringDict class that extends
the builtin dict type?

TODO: Is this class even necessary? Should be able to dict filtering by making
sets from the dict keys and then finding the intersection of those sets.
"""    
class DictUtilities(object):    
    @classmethod
    def filter_dict(cls, orig_dict, keys, strict=False):
        filtered_dict = {}
        
        # Cycle through the keys list, adding each key found in both the 
        # arguments list and the original dictionary to the new filtered 
        # dictionary.
        for key in keys:
            # Each entry in the keys list can be either a string or a tuple, in
            # which case it becomes a mapping pair, with the first value 
            # pointing to the key in the original dict, and the second key to 
            # the destination in the filtered dict.
            if isinstance(key, str):
                filtered_key = orig_key = key
            elif isinstance(key, tuple):
                orig_key = key[0]
                filtered_key = key[1]
            else:
                error_message = "Keys must be provided as either strings or tuple mappings."
                raise KeyError(error_message)
                            
            if orig_dict.has_key(orig_key):
                filtered_dict[filtered_key] = orig_dict[orig_key]
            else:
                if strict:
                    error_message = "Could not find required key {0} in original dict.".format(orig_key) 
                    raise KeyError(error_message)
               
        return filtered_dict
#------------------------------------------------------------------------------ 

class DictUtilitiesTest(unittest.TestCase):
    year_key = "year"
    month_key = "month"
    day_key = "day" 
        
    def test_filter_dict(self):       
        orig_dict = {self.year_key:2012, self.month_key:3, self.day_key:21,
            "hour":13, "minute":6, "second":19}
        
        filter_keys = (self.year_key, self.month_key, self.day_key)
        filtered_dict = DictUtilities.filter_dict(orig_dict, filter_keys)
        
        self.assertEqual(len(filtered_dict), len(filter_keys))
        self.assert_filtered_dict_matches(orig_dict, filtered_dict)
    
    def test_filter_dict_strict(self):       
        orig_dict = {self.year_key:2012, self.month_key:3, self.day_key:21,
            "hour":13, "minute":6, "second":19}
        
        filter_keys = (self.year_key, self.month_key, self.day_key, "new_key")
                
        with self.assertRaises(KeyError):
            DictUtilities.filter_dict(orig_dict, filter_keys, strict=True)
    
    def test_filter_dict_invalid_key_type(self):       
        orig_dict = {self.year_key:2012, self.month_key:3, self.day_key:21,
            "hour":13, "minute":6, "second":19}
        
        filter_keys = (self.year_key, self.month_key, self.day_key, 2)
                
        with self.assertRaises(KeyError):
            DictUtilities.filter_dict(orig_dict, filter_keys)            
            
    def test_filter_dict_with_mapping(self):
        orig_dict = {self.year_key:2012, self.month_key:3, self.day_key:21,
            "hour":13, "minute":6, "second":19}
        
        filter_keys = (self.year_key, ("hour", "24hr_time"))
        
        filtered_dict = DictUtilities.filter_dict(orig_dict, filter_keys)
        
        for key in filter_keys:
            if isinstance(key, str):
                orig_key = filter_key = key
            elif isinstance(key, tuple):
                orig_key = key[0]
                filter_key = key[1]
                
            self.assertTrue(filtered_dict.has_key(filter_key),
                "Unable to find mapped key '{0}' in filtered dict.".format(filter_key))
            
            self.assertEqual(orig_dict[orig_key], filtered_dict[filter_key])
    
    def assert_filtered_dict_matches(self, orig_dict, filtered_dict):
        for key in filtered_dict.keys():
            # Make sure the original dict contains the filtered key.
            self.assertTrue(orig_dict.has_key(key))
            
            # Check that the key is equal in both the original and filtered
            # dicts.
            self.assertEqual(orig_dict[key], filtered_dict[key])        
#------------------------------------------------------------------------------ 

class TraceLogUtils(object):
    TRACE_START="TRACE - START"
    TRACE_EXIT="TRACE - EXIT"
    
    @staticmethod
    def trace_start(message=None):
        if message is not None:
            message = " - " + message
            
        logging.debug(TraceLogUtils.TRACE_START + message)
    
    @staticmethod
    def trace_exit(message=None):
        if message is not None:
            message = " - " + message
            
        logging.debug(TraceLogUtils.TRACE_EXIT + message)
#------------------------------------------------------------------------------ 
