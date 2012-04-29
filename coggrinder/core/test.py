'''
Created on Apr 29, 2012

@author: Clay Carpenter
'''

import unittest
import mockito

class ManagedFixturesTestCase(unittest.TestCase):
    '''Simple test case that managed the fixtures by establishing and cleaning
    up the declared fixtures for each unit test.
    '''
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName=methodName)       
        
    def _register_fixtures(self, *fixtures):
        for fixture in fixtures:
            self.fxtr.append(fixture)
            
    def setUp(self):
        # A registry of all of the fixtures common to the tests owned by this
        # TestCase.
        self.fxtr = ManagedFixturesTestCase.FixtureRegistry()
    
    def tearDown(self):
        # Clean up any class-level stubbing. This does not override stubbing
        # on individual mock instances, but that is remedied as long as the
        # mock instances are included in the fixtures that will be cleaned up
        # next.
        mockito.unstub()
        
        # Clean up any declared fixtures.
        del self.fxtr
        
    class FixtureRegistry(object):
        """Simple container class to hold arbitrary fixture references."""
#------------------------------------------------------------------------------ 
