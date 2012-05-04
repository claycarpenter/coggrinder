'''
Created on Apr 29, 2012

@author: Clay Carpenter
'''

import mockito

class ManagedFixturesTestSupport(object):
    '''Simple test case utility that managed the fixtures by establishing and 
    cleaning up the declared fixtures for each unit test.
    '''
    def _register_fixtures(self, reset_fixtures=False, *fixtures):
        # TODO: This hasattr test doesn't smell very Pythonic...
        if not hasattr(self,"_fixtures_registry") or reset_fixtures:
            # Reset fixtures registry.
            self._fixtures_registry = list()
        
        for fixture in fixtures:
            self._fixtures_registry.append(fixture)

    def tearDown(self):
        """Clears out any Mockito stubs and deletes any registered test
        fixtures."""
        
        # Clean up any class-level stubbing. This does not override stubbing
        # on individual mock instances, but that is remedied as long as the
        # mock instances are included in the fixtures that will be cleaned up
        # next.
        mockito.unstub()

        # Clean up any declared fixtures.
        while self._fixtures_registry:
            fixture = self._fixtures_registry.pop()
            del fixture
#------------------------------------------------------------------------------ 
