'''
Created on May 28, 2012

@author: Clay Carpenter
'''

import logging

TRACE_START="TRACE - START"
TRACE_EXIT="TRACE - EXIT"

def trace_start(message=None):
    if message is not None:
        logging.debug(TRACE_START + " - " + message)    
    else:
        logging.debug(TRACE_START)

def trace_exit(message=None):
    if message is not None:
        logging.debug(TRACE_EXIT + " - " + message)    
    else:
        logging.debug(TRACE_EXIT)
