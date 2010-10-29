'''
Created on May 27, 2009

Module containing IMS Parser Exceptions

@author: guillaume.aubert@ctbto.org
'''

PARSER_ERROR_MESSAGE = "Error[line=%s,pos=%s]: %s."

class ParserError(Exception):
    """ Parsing Base Class"""
    
    def __init__(self, a_msg, a_line = None, a_line_num = None, a_pos = None, a_suggest = None):  # pylint: disable-msg=R0913
        
        super(ParserError, self).__init__()
        self._message           = a_msg
        self._line              = a_line
        self._line_num          = a_line_num
        self._pos               = a_pos
        self._suggestion        = a_suggest
        self._instrumented_line = None

    def _get_message(self): 
        return self._message
    
    def _set_message(self, message): 
        self._message = message
        
    message = property(_get_message, _set_message)
    
    @property
    def instrumented_line(self):
        """ return the prepared line """
        return self._instrumented_line  

    @property
    def suggestion(self):
        """ return suggestion """
        return self._suggestion
    
    @property    
    def line(self):
        """ line accessor """ 
        return self._line
    
    @property
    def line_num(self):
        """ line_num accessor """
        return self._line_num
    
    @property
    def pos(self):
        """ pos accessor """
        return self._pos