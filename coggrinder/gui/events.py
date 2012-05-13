"""
Created on Apr 4, 2012

@author: Clay Carpenter

Much credit goes to this example:
    http://www.valuedlessons.com/2008/04/events-in-python.html
"""

"""
It would be cool if there was a way to propagate these Events up a widget 
chain. This would allow a container view (i.e., a window) to also serve as a 
registration proxy for a component view (i.e., a toolbar). That way the 
Controller working with the container view wouldn't have to know about the 
view's toolbar implementation; instead reacting only to "domain" events.

Use a decorator to mark methods as event-raising. Then add a "listen_all" 
method (in Event, as static?) that takes an instance as an argument, and loops
through all of the methods of the instance finding any decorated events and
registering propagators?

Something like this:
def raise_event(wrapped_func):
    # Call wrapped function.
    
    # Notify any listeners
    
# This is a decorator factory that creates a decorator, which in turn will
# wrap the given method.
def handle_event(event):
    def decorator(handler_func):
        def wrapper():
            handler_func()
            
            # Do something interesting...
        
        return wrapper
        
    return decorator
    
# This is psuedo-code... not sure how to get methods/decorators dynamically
# at this point.
def listen_all(event_source, listener):
    for method in event_source.methods:
        if method.has_decorator(raise_event):
            method.register_listener(listener)
"""

import unittest

class Event(object):
    """
    Very simple event handler system that allows observers to register a 
    handler function that will be executed after the event has been fired.
    """
    def __init__(self):
        self._listeners = set()
        
    def register(self, listener):
        self._listeners.add(listener)
    
    def deregister(self, listener):
        try:
            self._listeners.remove(listener)
        except:
            raise ValueError("Cannot deregister listener that isn't registered.")
        
    def fire(self, *args, **kwargs):
        for listener in self._listeners:
            listener(*args, **kwargs)
            
    @staticmethod
    def propagate(delegate_event):
        """
        This is a convenience method to create an event that fires itself in 
        response to the wrapped delegate_event's firing.
        """
        propagation_event = Event()
        
#        def event_wrapper(*args, **kwargs):
#            print "Event (propagation) wrapper fired..."
#            delegate_event.fire(*args, **kwargs)
            
        delegate_event.register(propagation_event.fire)
        
        return propagation_event
#------------------------------------------------------------------------------
    
"""
TODO: How do I want the event decorator to work?
"""
class DecoratorTest(unittest.TestCase):
    def test_listener_model_view(self):
        """
        This isn't a great test case, but it gets the job done.
        """
        controller = DecoratorTest.Controller()
        
        self.assertEqual(0, controller.value)
        
        controller.view.button_click()
                
        self.assertEqual(1, controller.value)
        
    class View():
        def __init__(self):
            self.click_event = Event()
            
        def button_click(self):
            self.click_event.fire(self)
    
    class Controller():
        def __init__(self):
            self.view = DecoratorTest.View()
            self.value = 0
            
            # Register event listener.
            self.view.click_event.register(self.handle_button_click)
            
        def handle_button_click(self, button):
            self.value += 1
#------------------------------------------------------------------------------ 