'''
Created on May 28, 2012

@author: Clay Carpenter
'''

import logging

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
    
    def __init__(self, logging_context=None, level=logging.DEBUG):
        if logging_context is None:
            logging_context = {}
            
        self.logging_context = logging_context
        self.level = level
        
    def __call__(self, wrapped_function):                
        def entryExitLogger(*args, **kwargs):
            log_message = entryExit._TRACE_MESSAGE_FORMAT.format(
                action=TRACE_ENTER, method_name=wrapped_function.__name__, 
                module_name=wrapped_function.__module__)
            logging.log(self.level, log_message, extra=self.logging_context)
            
            result = wrapped_function(*args, **kwargs)
                        
            log_message = entryExit._TRACE_MESSAGE_FORMAT.format(
                action=TRACE_EXIT, method_name=wrapped_function.__name__, 
                module_name=wrapped_function.__module__)
            logging.log(self.level, log_message, extra=self.logging_context)
            
            return result
    
        return entryExitLogger
#------------------------------------------------------------------------------

"""
TODO: This example and the main method that runs a quick test should be 
replaced by a proper unittest test case.
"""
class QuickExample(object):
    @entryExit()
    def traced_method(self, message="Nothing"):
        print "Message: {0}".format(message)      
        
        return "Result of the event execution."
#------------------------------------------------------------------------------

if __name__ == '__main__':    
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("Logging is configured.")
    
    logging.debug("Testing trace log system.")
    example = QuickExample()
    result = example.traced_method()
    result = example.traced_method("Using logger")
    logging.debug("Trace result: {0}".format(result))
    logging.debug("Done... hopefully.")
