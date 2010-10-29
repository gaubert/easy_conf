'''
Created on Jun 18, 2009

@author: guillaume.aubert@ctbto.org

Constants for the NL and IMS2.0 Validator
'''

# result Dict constants
PRODUCTFAMILY       = 'PRODUCTFAMILY'
PRODUCTTYPE         = 'PRODUCTTYPE'
TECHNOLOGYTYPE      = 'TECHNOLOGYTYPE'
TECHNOLOGYFAMILY    = 'TECHNOLOGYFAMILY'
FILTER              = 'FILTER'

# IMS2.0 keys
FORMAT_K      = 'FORMAT'
TYPE_K        = 'TYPE'
SUBFORMAT_K   = 'SUBFORMAT'
BULLTYPE_K    = 'BULLTYPE'
MAGTYPE_K     = 'MAGTYPE'
MAG_K         = 'MAG'
DATE_K        = 'DATE'
LAT_K         = 'LAT'
LON_K         = 'LON'
STALIST_K     = 'STALIST'
RELATIVETO_K  = 'RELATIVETO'
SUBTYPE_K     = 'SUBTYPE'
STATIONS_K    = 'STATIONS'

#Subscription constants
FREQUENCY_K     = 'FREQUENCY'
SUBSCRLIST_K    = 'SUBSCRLIST'
SUBSCRNAME_K    = 'SUBSCRNAME'
PRODIDLIST_K    = 'PRODIDLIST'
SUB_COMMAND_K   = 'COMMAND'
SUB_PRODUCT_DESC_K = 'SUB_PRODUCT_DESC'
#Subscription commands values
UNSUBSCRIBE_V   = 'UNSUBSCRIBE'
SUBSCR_PROD_V   = 'SUBSCRPROD'

# List of supported magnitudes
SUPPORTED_MAG = [ "MB", "MS", "ML" ]