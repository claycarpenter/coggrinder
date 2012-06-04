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

import inspect
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
    
class EventInfo(object):    
    def __init__(self, event_name):
        self.event_name = event_name
        
    def __eq__(self, other):
        try:
            return self.event_name == other.event_name
        except AttributeError:
            return NotImplemented
        
    def __repr__(self):
        return "<EventInfo - name: {event_name};>".format(event_name=self.event_name)
#------------------------------------------------------------------------------

def eventAware(klazz):    
    class NewWrapper(object):
        def __init__(self, wrapped_func):
            self.wrapped_func = wrapped_func

        def __get__(self, instance, instance_type):        
            return self
            
        def __call__(self, *args, **kwargs):
            return self.wrapped_func(*args, **kwargs)
    
    # Replace the actual/original class new_wrapper function with the wrapped version.
    klazz.__new__ = NewWrapper(klazz.__new__)
        
    original_init = klazz.__init__
    def init_wrapper(instance, *args, **kwargs):
        result = original_init(instance, *args, **kwargs)
        
        # Collect all methods on this instance.
        all_methods = inspect.getmembers(instance, inspect.ismethod)
        
        # Find the methods that have EventInfo metadata.
        # method[1] is the instancemethod portion of a tuple returned by
        # getmembers (method[0] is the name to which the method is bound to).
        event_listener_methods = [method[1] for method in all_methods if hasattr(method[1], 'event_info')]
        
        for event_listener_method in event_listener_methods:
            EventRegistry.register_listener(event_listener_method,
                event_listener_method.event_info.event_name)
        
        return result
    
    klazz.__init__ = init_wrapper
    
    # Return the modified class definition.
    return klazz
#------------------------------------------------------------------------------

class eventListener(object):
    def __init__(self, event_name):        
        self._event_name = event_name
        
    def __call__(self, wrapped_function):                
        # Create wrapper to execute wrapped function.
        def listener(*args, **kwargs):
            return wrapped_function(*args, **kwargs)
        
        listener.event_info = EventInfo(self._event_name)  
        
        return listener
#------------------------------------------------------------------------------

class EventRegistry(object):
    _LISTENER_REGISTRY = dict()
    
    @classmethod
    def create_notifier_callback(cls, event_name):        
        def notifying_callback(*args, **kwargs):
            # Create a new EventInfo to transmit the event data.
            event_info = EventInfo(event_name)
            
            # Notify the EventRegistry of the event.
            EventRegistry.notify(event_info)
        
        return notifying_callback

    @classmethod
    def register_listener(cls, listener, event_name):        
        registry_entry = EventRegistry.ListenerRegistryEntry(listener, event_name)
        
        try:
            EventRegistry._LISTENER_REGISTRY[registry_entry.event_name].append(registry_entry)
        except KeyError:
            EventRegistry._LISTENER_REGISTRY[registry_entry.event_name] = [registry_entry]

    @classmethod
    def notify(cls, event_info):
        try:
            # Iterate over the listeners registered for the provided event
            # name, notifying each in turn.
            for listener in EventRegistry._LISTENER_REGISTRY[event_info.event_name]:
                listener.notify(event_info)
        except KeyError:
            # This is fine, just indicates that there are no registered 
            # listeners for the event.
            return
        
    class ListenerRegistryEntry(object):
        def __init__(self, listener, event_name):
            self.listener = listener
            self.event_name = event_name  
            
        def notify(self, event_info):
                self.listener(event_info)           
    
    @classmethod
    def deregister_event_listeners(cls, event_name):
        try:
            del EventRegistry._LISTENER_REGISTRY[event_name]
        except KeyError:
            # This is fine, just indicates that there are no registered 
            # listeners for the event.
            return
#------------------------------------------------------------------------------

class EventRegistryTestSupport(object):
    EVENT_NAME = "event_test"
    
    def setUp(self):
        # Clear the EventRegistry for the test event name.
        EventRegistry.deregister_event_listeners(EventRegistryTestSupport.EVENT_NAME)
    
    def tearDown(self):
        # Clear the EventRegistry for the test event name.
        EventRegistry.deregister_event_listeners(EventRegistryTestSupport.EVENT_NAME)
#------------------------------------------------------------------------------

class EventTest(EventRegistryTestSupport, unittest.TestCase):    
    class Listener(object):
        def __init__(self):
            self.event_info = None
            
        def listen(self, event_info):
            self.event_info = event_info
    
    def test_eventregistry_notify_listen(self):
        ### Arrange ###
        listener_1 = EventTest.Listener()
        EventRegistry.register_listener(listener_1.listen, EventRegistryTestSupport.EVENT_NAME)
        
        listener_2 = EventTest.Listener()
        EventRegistry.register_listener(listener_2.listen, EventRegistryTestSupport.EVENT_NAME)
        
        expected_event_info = EventInfo(EventRegistryTestSupport.EVENT_NAME)
        
        ### Act ###
        EventRegistry.notify(expected_event_info)
        
        ### Assert ###
        self.assertEqual(expected_event_info, listener_1.event_info)
        self.assertEqual(expected_event_info, listener_2.event_info)
    
    def test_notifying_callback(self):
        ### Arrange ###
        expected_event_info = EventInfo(EventRegistryTestSupport.EVENT_NAME)
        
        listener = EventTest.Listener()
        EventRegistry.register_listener(listener.listen, EventRegistryTestSupport.EVENT_NAME)
        
        ### Act ###
        notifying_callback = EventRegistry.create_notifier_callback(
            EventRegistryTestSupport.EVENT_NAME)
        
        # This should call the listener and pass to it the event info.
        notifying_callback()
        
        ### Assert ###
        self.assertEqual(expected_event_info, listener.event_info)
        
    def test_registry_clear(self):
        ### Arrange ###
        listener_1 = EventTest.Listener()
        EventRegistry.register_listener(listener_1.listen, EventRegistryTestSupport.EVENT_NAME)
        
        expected_event_info = EventInfo(EventRegistryTestSupport.EVENT_NAME)
        
        ### Act ###
        EventRegistry.deregister_event_listeners(EventRegistryTestSupport.EVENT_NAME)
        
        EventRegistry.notify(expected_event_info)
        
        ### Assert ###
        self.assertIsNone(listener_1.event_info)        
#------------------------------------------------------------------------------

class EventAwareEventListenerTest(EventRegistryTestSupport, unittest.TestCase):    
    @eventAware
    class DecoratedListener(object):
        def __init__(self):
            self.event_info = None
        
        @eventListener(event_name="event_test")
        def listen(self, event_info):
            self.event_info = event_info
    
    def test_eventlistener(self):
        ### Arrange ###
        listener_1 = EventAwareEventListenerTest.DecoratedListener()        
        listener_2 = EventAwareEventListenerTest.DecoratedListener()
        
        expected_event_info = EventInfo(EventRegistryTestSupport.EVENT_NAME)
        
        ### Act ###
        EventRegistry.notify(expected_event_info)
        
        ### Assert ###
        self.assertEqual(expected_event_info, listener_1.event_info)
        self.assertEqual(expected_event_info, listener_2.event_info)
#------------------------------------------------------------------------------
