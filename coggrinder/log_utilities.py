'''
Created on May 28, 2012

@author: Clay Carpenter
'''

import logging
import pprint

TRACE_ENTER = "ENTER"
TRACE_EXIT = "EXIT"

class entryExit(object):
    """This decorator will create log entries as the wrapped method is called
    and finishes.
    
    The log message contains the trace action (entry or exit), as well as the 
    wrapped method name and the module where it was defined.
    
    This decorator should not be used in any production systems due to the
    overhead it adds to each wrapped method call.    
    """
    _TRACE_MESSAGE_FORMAT = "TRACE {action} - module: {module_name}; method: {method_name}"
    
    def __init__(self, show_args=False, show_result=False, logging_context=None, level=logging.DEBUG):        
        if logging_context is None:
            logging_context = {}
            
        self.logging_context = logging_context
        self.level = level    
        self.show_args = show_args
        self.show_result = show_result    
        
    def __call__(self, wrapped_function):                
        def wrapper(*args, **kwargs):     
            log_message = entryExit._TRACE_MESSAGE_FORMAT.format(
                action=TRACE_ENTER, method_name=wrapped_function.__name__,
                module_name=wrapped_function.__module__)
            logging.log(self.level, log_message, extra=self.logging_context)
            
            if self.show_args:
                logging.log(self.level, "Arguments:", extra=self.logging_context)
                logging.log(self.level, pprint.pformat(args), extra=self.logging_context)
                logging.log(self.level, "Keyword Arguments:", extra=self.logging_context)
                logging.log(self.level, pprint.pformat(kwargs), extra=self.logging_context)
                
            result = wrapped_function(*args, **kwargs)
            
            if self.show_result:
                logging.log(self.level, "Result:", extra=self.logging_context)
                logging.log(self.level, pprint.pformat(result), extra=self.logging_context)
                        
            log_message = entryExit._TRACE_MESSAGE_FORMAT.format(
                action=TRACE_EXIT, method_name=wrapped_function.__name__,
                module_name=wrapped_function.__module__)
            logging.log(self.level, log_message, extra=self.logging_context)
            
            return result
        
        return wrapper
#------------------------------------------------------------------------------

"""
TODO: This example and the main method that runs a quick test should be 
replaced by a proper unittest test case.
"""
class Person(object):
    def __init__(self, name):
        self.name = name
        
    @entryExit(show_args=True, show_result=True)
    def wave(self, other_person):
        logging.debug("{self_name} waves at {other_name}".format(self_name=self.name,other_name=other_person.name))      
        
        return True
        
    @entryExit()
    def say_hello(self):
        logging.debug("Hello, my name is {0}".format(self.name))      
        
        return True
    
    @staticmethod
    @entryExit()
    def square(x):
        return x * x
    
    def __repr__(self):
        # Simple representation to make the log records look nicer.
        return "<Person object, name: {name}>".format(name=self.name)
    
    def __str__(self):
        return self.__repr__()
#------------------------------------------------------------------------------

if __name__ == '__main__':    
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("Logging is configured.")
    
    logging.debug("Testing trace log system.")
    
    ann = Person("Ann")
    jon = Person("Jon")
    
    ann.say_hello()
    jon.say_hello()
    
    ann.wave(jon)
    jon.wave(ann)
    
    logging.debug("Square: {0}".format(str(Person.square(8))))
    
    logging.debug("Done.")
