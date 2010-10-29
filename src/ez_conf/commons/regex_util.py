'''
Created on Jun 12, 2009

@author: guillaume.aubert@ctbto.org
'''



# functor tools to assemble tokens
def group(*choices)   : 
    """ group functor """
    return '(' + '|'.join(choices) + ')'
    
def any(*choices)     :  #IGNORE:W0622
    """ any functor """
    return group(*choices) + '*' #IGNORE:W0142

def maybe(*choices)   : 
    """ maybe functor """
    return group(*choices) + '?' #IGNORE:W0142