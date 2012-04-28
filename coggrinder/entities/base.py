'''
Created on Apr 27, 2012

@author: Clay Carpenter
'''

class ComparableNamedProperties(object):
    '''Simply compares between two objects, using declared properties.
    '''
    def _get_comparable_properties(self):
        return self.__dict__.keys()

    def __eq__(self, other):
        for property_name in self._get_comparable_properties():
            if not (self.__dict__.has_key(property_name) 
                and other.__dict__.has_key(property_name)):
                return False
            
            if self.__dict__[property_name] != other.__dict__[property_name]:
                return False
             
        return True
#------------------------------------------------------------------------------ 
