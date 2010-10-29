'''
Created on Jun 2, 2009

@author: guillaume.aubert@gmail.com
'''
import copy

import nms_common.parser.common.validator_const as const 

from nms_common.utils.logging_utils import LoggerFactory

from nms_common.parser.exceptions import ParserError

import nms_common.parser.common.time as parser_time
from nms_production_engine_api import product_dict_const
from nms_common.parser.common import validator_const




class SemanticValidationError(ParserError):
    """Semantic Validation Errors"""
    
    
    def __init__(self, a_msg):
        super(SemanticValidationError, self).__init__(a_msg, None, -1, -1) 

# pylint: disable-msg=R0903,R0201        
   
class DateRule(object):
    """
       The Time Rule
    """
    
    @classmethod
    def check(cls, a_type, a_prod_keys, a_prod_dict, a_original_dict): # pylint: disable-msg=W0613
        """
           check that the rules are respected for this type of parameter.
           The default does nothing
           Args:
                a_type           : the type treated
                a_prod_keys      : the different env var names
                a_prod_dict      : a product directory
                a_original_dict  : the original dictionary with the original parameters
        """
        time  = a_prod_dict.get(const.DATE_K, None)
        
        
        if not time:
            raise SemanticValidationError("The %s product needs a TIME env variable" %(a_original_dict['TYPE']))
        
        try:
            start = time['START']
            end   = time['END']
            start_datetime = parser_time.imsdate_to_datetime(start)
            end_datetime   = parser_time.imsdate_to_datetime(end)
        except Exception, err:
            msg = "The start date [%s] or end date [%s] is invalid and not following the IMS Format.\n Received Error - %s"\
                  % (time['START'], time['END'], err)
            raise SemanticValidationError(msg)
        
        # transform CTBTO time in date time
        # check the end is > to start
        # replace text time with the object
        if end_datetime < start_datetime :
            raise SemanticValidationError("The end date %s is before the start date %s."%(start, end))
        
        # replace text time with the datetime objects
        a_prod_dict[const.DATE_K]['START'] = start_datetime
        a_prod_dict[const.DATE_K]['END']   = end_datetime
        
        a_prod_keys.remove(const.DATE_K)

class FloatRule(object):
    """
       Rule to handle Float conversion for a range
    """
    #dict containing the min and max for each type
    MINMAX = {
                   'DEPTH'              : { 'MIN' : 0.0, 'MAX' : 4000}, # 4000 is more than the earth radix
                   'DEPTHMINUSERROR'    : { 'MIN' : 0.0, 'MAX' : 4000},
                   'MAG'                : { 'MIN' : 0.0, 'MAX' : 12.0},
                   'MBMINUSMS'          : { 'MIN' : 0.0, 'MAX' : 12.0},
                 }
    
    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        """ removeRule (remove it from the prod_keys dict 
            Args:
                a_env      : the type treated
                a_prod_keys : the different env var names
                a_prod_dict : a product directory  
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        the_val = a_prod_dict.get(a_env, None)
        
        if not the_val:
            raise SemanticValidationError("The %s product needs a %s env variable" %(a_original_dict['TYPE'], a_env))
        
        # if val is a dict then it is a range
        if isinstance(the_val, dict):
            the_min = a_prod_dict[a_env]['START']
            the_max = a_prod_dict[a_env]['END']
            the_val['START'] = cls._convert_to_float(a_original_dict['TYPE'], a_env, the_min)
            the_val['END'] = cls._convert_to_float(a_original_dict['TYPE'], a_env, the_max)
        else:
            the_val = cls._convert_to_float(a_prod_dict['TYPE'], a_env, a_prod_dict[a_env])
        
        #remove it from keys to treat
        a_prod_keys.remove(a_env)

    @classmethod
    def _convert_to_float(cls, a_product_type, a_type, a_value):
        """
           convert the values into floats. and check
           
           Args:
                a_product_type : Product_type used in case of error
                a_type         : DEPTH or MAG or ...
                a_value        : the value to convert
        """
        the_value = 0.0
        
        if  a_value in ('MIN','MAX'):
            return cls.MINMAX[a_type][a_value]
        else:
            try:
                the_value = float(a_value)
            except ValueError, v_err:
                LoggerFactory.get_logger('RequestSemanticValidator')\
                .error("Cannot convert %s in float. %s is not a numerical value.\n Err %s" %(a_type, a_value, v_err))
                raise SemanticValidationError("Cannot convert %s in float. %s is not a numerical value" %(a_type, a_value))
        
        if the_value < cls.MINMAX[a_type]['MIN'] or the_value > cls.MINMAX[a_type]['MAX']:
            raise SemanticValidationError("values for parameter %s of product %s should be between %s and %s"\
                                           %(a_type, a_product_type, cls.MINMAX[a_type]['MIN'], cls.MINMAX[a_type]['MAX'])) 
    
        return the_value

class LatLonRule(object):
    """
       The LatLon Rule. Check that lat is between 
    """
   
    
    MIN     = {
                const.LAT_K : -90.0 ,
                const.LON_K : -180.0 ,
              }
    
    MAX     = { 
                const.LAT_K : 90.0 ,
                const.LON_K : 180.0 ,
              }
    
    
    @classmethod
    def _convert_to_float(cls, a_type, a_value):
        """
           convert the lat or lon value to a float type
           
           Args:
                a_type      : LAT or LON
                a_value     : the value to convert
        """
        
        if   a_value == 'MIN':
            return cls.MIN[a_type]
        elif a_value == 'MAX':
            return cls.MAX[a_type]
        else:
            try:
                return float(a_value)
            except ValueError, v_err:
                LoggerFactory.get_logger('RequestSemanticValidator')\
                .error("Cannot convert %s in float. %s is not a numerical value.\n Err %s" %(a_type, a_value, v_err))
                raise SemanticValidationError("Cannot convert %s in float. %s is not a numerical value" %(a_type, a_value))
    
    
    @classmethod
    def check(cls, a_type, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        """
           check that the rules are respected for this type of parameter.
           Checks: Lat between 90 (North) and -90 (South) deg and that start <= end
                   Lon between 180 (East) and -180 (West) deg and that start <= end
                   there is lat and lon value
                   there is no stalist with lat-lon
           
           Args:
                a_type      : the type treated
                a_prod_keys : the different env var names
                a_prod_dict : a product directory
        """
        
        
        
        lat = a_prod_dict.get(const.LAT_K, None)
        lon = a_prod_dict.get(const.LON_K, None)
        
        if not lat or not lon:
            raise SemanticValidationError("The %s product needs a lat and a lon env variable (one is missing)" %(a_original_dict['TYPE']))
        
        #check that there is no stalist
        sta_list = a_prod_dict.get(const.STALIST_K, None)
        
        if sta_list:
            raise SemanticValidationError("The %s product cannot have sta_list and a lat or lon env variable in the same request message"\
                                           %(a_original_dict['TYPE']))
            
        # do the lat-lon checking 
        lat_start = cls._convert_to_float(const.LAT_K, lat['START'])
        lat_end   = cls._convert_to_float(const.LAT_K, lat['END'])
        
        
        if not (-90 <= lat_start <= 90) or not (-90 <= lat_end <= 90):
            raise SemanticValidationError("End or start latitude of product %s should be between -90 and 90 degrees"\
                                           %(a_original_dict['TYPE'])) 
        
        if lat_start > lat_end:
            raise SemanticValidationError("Start latitude of product %s is superior to end latitude"\
                                           %(a_original_dict['TYPE'])) 
        
        # do the lat-lon checking
        # do the lat-lon checking 
        lon_start = cls._convert_to_float(const.LON_K, lon['START'])
        lon_end   = cls._convert_to_float(const.LON_K, lon['END'])
       
        if not (-180 <= lon_start <= 180) or not (-180 <= lon_end <= 180):
            raise SemanticValidationError("End or start longitude of product %s has to be between -180 and 180 degrees"\
                                          %(a_original_dict['TYPE'])) 
        
        if lon_start > lon_end:
            raise SemanticValidationError("Start longitude of product %s is superior to end latitude"\
                                           %(a_original_dict['TYPE']))
        
        # remove types
        a_prod_keys.remove(const.LAT_K)
        a_prod_keys.remove(const.LON_K)
        
        #do the necessary dict transformation
        cls.transform(a_prod_dict, lat_start, lat_end, lon_start, lon_end)
    
    @classmethod
    def transform(cls, a_prod_dict, a_lat_start, a_lat_end, a_lon_start, a_lon_end):
        """ Transform the returned directory to formatted according to the Generic Data structure
            that is common to both new language and IMS2.0 language
            Args: 
                a_prod_dict : a product directory
                a_lat_start : latitude start  component
                a_lat_end   : latitude stop   component
                a_lon_start : longitude start component
                a_lon_end   : longitude stop  component
               
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        loc_dict = { 
                      const.TYPE_K : 'GEO',
                      const.LAT_K  : { 'START' : a_lat_start, 'END' : a_lat_end },
                      const.LON_K  : { 'START' : a_lon_start, 'END' : a_lon_end },
                   }
        
        a_prod_dict['LOC'] = loc_dict
        
        # remove lat and lon from prod_dict
        del a_prod_dict[const.LAT_K]
        del a_prod_dict[const.LON_K]
        

class BullTypeRule(object):
    """ 
       BullType Class
    """
   
    
    BULLETIN_CODES = ["SEL1", "SEL2", "SEL3", "REB", "LEB", \
                      "SEB", "SSEB", "NEB", "NSEB", \
                      "IDC_REB", "IDC_SEL1", "IDC_SEL2", "IDC_SEL3", \
                      "IDC_SEB", "IDC_SSEB", "IDC_NSEB", 
                      "IDC_NEB", "IDC_NSEB"]
    
    
    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        """ Check that there is 
            Args: 
                a_env      : the type treated
                a_prod_keys : the different env var names
                a_prod_dict : a product directory  
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        bull_type = a_prod_dict.get(const.BULLTYPE_K, None)
        
        # check if there is a bull_type present
        if not bull_type:
            raise SemanticValidationError("The %s product needs a bull_type env variable" %(a_original_dict['TYPE']))
        
        if bull_type.upper() not in cls.BULLETIN_CODES:
            raise SemanticValidationError("The bull_type env variable %s is not supported, Supported values are %s."\
                                          % (bull_type, cls.BULLETIN_CODES))
       
        a_prod_keys.remove(const.BULLTYPE_K)
        #delete bull type as it should be the product type
        del a_prod_dict[const.BULLTYPE_K]

class SubProductDesc(object):
    """ 
       Dummy rule Class
    """
    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        a_prod_keys.remove(validator_const.SUB_PRODUCT_DESC_K)  
    
class FrequencyRule(object):
    """ 
       Frequency rule Class
    """
    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        """ Check that there is 
            Args: 
                a_env      : the type treated
                a_prod_keys : the different env var names
                a_prod_dict : a product directory  
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        frequency_keyword = a_prod_dict.get(const.FREQUENCY_K, None)
        
        # check if there is a bull_type present
        if not frequency_keyword:
            raise SemanticValidationError("The subscription %s product needs a frequency env variable" % (a_original_dict['TYPE']))
       
        a_prod_keys.remove(const.FREQUENCY_K)

class SubscrListRule(object):
    """
        Subscription list rule, doesn't check anything, used to transform string tokens in integers
    """
    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        subscr_list_string = a_prod_dict.get(const.SUBSCRLIST_K)
        
        subscr_list = [int(string_value) for string_value in subscr_list_string]
        
        a_prod_dict[const.SUBSCRLIST_K] = subscr_list

class SubscriptionCommandRule(object):
    """
        Check if subscr_list or subscr_name are provided
        prodlist_id is not supported
    """
    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        subscr_command = a_prod_dict[const.SUB_COMMAND_K]
        
        if subscr_command not in (const.UNSUBSCRIBE_V, const.SUBSCR_PROD_V):
            raise SemanticValidationError("Command not supported for subscription %s" % subscr_command)
        
        if const.PRODIDLIST_K in a_prod_dict:
            raise SemanticValidationError("%s does not support prodid_list keyword" % subscr_command)
               
        if subscr_command == const.UNSUBSCRIBE_V and \
            not const.SUBSCRLIST_K in a_prod_dict and not const.SUBSCRNAME_K in a_prod_dict:
            
            raise SemanticValidationError("To specify which products or subscriptions you wish to unsubscribe, " \
                                          "one of the following environments is mandatory: SUBSCR_LIST, PRODID_LIST, SUBSCR_NAME.")
    
        if const.SUBSCRLIST_K in a_prod_dict:
            SubscrListRule.check(a_env, a_prod_keys, a_prod_dict, a_original_dict)
            
        a_prod_keys.remove(const.TYPE_K)
        #remove type from dir 
        del a_prod_dict[const.TYPE_K]
                
class MagSibblingsRule(object):
    """ 
       Checks the 2 MAG sibblings MAG and MAG_TYPE are there.
       If they are not error.
       For MAG, the rule does a float checking and for MAG_TYPE checks that the type exists
    """
   
    
    MAG_TYPES  = const.SUPPORTED_MAG
    
    
    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        """ Check that there is 
            Args: 
                a_env      : the type treated
                a_prod_keys : the different env var names
                a_prod_dict : a product directory  
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        mag_types = a_prod_dict.get(const.MAGTYPE_K, None)
        mag       = a_prod_dict.get(const.MAG_K, None)
        
        # check if there is a mag present
        if not mag:
            raise SemanticValidationError("The %s product needs a mag env variable as there is a mag_type variable in the request" %(a_original_dict['TYPE']))
        
        # check if there is a mag_type present
        if not mag_types:
            raise SemanticValidationError("The %s product needs a mag_type env variable as there is a mag variable in the request" %(a_original_dict['TYPE']))
        
        # MAG_TYPE checkings
        tr_types = []
        
        for m_type in mag_types:
            if m_type.upper() not in cls.MAG_TYPES:
                raise SemanticValidationError("The mag_type env variable %s is not supported. Supported values are %s."\
                                          % (m_type, cls.MAG_TYPES))
            else:
                tr_types.append(m_type.upper())
       
        a_prod_keys.remove(const.MAGTYPE_K)
        
        a_prod_dict[const.MAGTYPE_K] = tr_types
        
        # MAG checkings: Run the float checkings
        FloatRule.check(const.MAG_K, a_prod_keys, a_prod_dict , a_original_dict)

class MagTypeRule(object):
    """ 
       MagType Class. Checks if its sibbling MAG is there otherwise error
    """
   
    
    MAG_TYPES  = const.SUPPORTED_MAG
    
    
    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        """ Check that there is 
            Args: 
                a_env      : the type treated
                a_prod_keys : the different env var names
                a_prod_dict : a product directory  
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        mag_types = a_prod_dict.get(const.MAGTYPE_K, None)
        
        tr_types = []
        # check if there is a bull_type present
        if not mag_types:
            raise SemanticValidationError("The %s product needs a mag_type env variable" %(a_original_dict['TYPE']))
        
        # should also have a mag value
        if not a_prod_dict.get(const.MAG_K, None):
            raise SemanticValidationError("as there is a mag_type, the %s product needs a mag env variable" %(a_original_dict['TYPE']))
        
        for m_type in mag_types:
            if m_type.upper() not in cls.MAG_TYPES:
                raise SemanticValidationError("The mag_type env variable %s is not supported. Supported values are %s."\
                                          % (m_type, cls.MAG_TYPES))
            else:
                tr_types.append(m_type.upper())
       
        a_prod_keys.remove(const.MAGTYPE_K)
        
        a_prod_dict[const.MAGTYPE_K] = tr_types
        
class RelativeToRule(object):
    """ 
       RelativeTo Rule check that:
       relative_to origin | event | bulletin
    """
    
    VALUES = ['BULLETIN', 'EVENT', 'ORIGIN']
    
    
    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        """ check the relativeto directive
            Args:
                a_env      : the type treated
                a_prod_keys : the different env var names
                a_prod_dict : a product directory  
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        relativeto = a_prod_dict.get(const.RELATIVETO_K, None)
        
        if not relativeto:
            raise SemanticValidationError("The %s product needs a relative_to env variable" %(a_original_dict['TYPE']))
        
        if relativeto not in cls.VALUES:
            raise SemanticValidationError("relative_to value [%s] should be one of the following values %s" %(relativeto, cls.VALUES))
        
        #remove it
        a_prod_keys.remove(a_env)
        
class StaListRule(object):
    """ 
       Check that StaList contains the right stations (to be done)
       Check that StaList is not mixed with Lat or Lon
    """
    
    STALIST_K = 'STALIST'
    LAT_K     = 'LAT'
    LON_K     = 'LON'
    TYPE_K    = 'TYPE'
    

    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        """ check the relativeto directive
            Args:
                a_env      : the type treated
                a_prod_keys : the different env var names
                a_prod_dict : a product directory  
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        stalist = a_prod_dict.get(const.STALIST_K, None)
        
        if not stalist:
            raise SemanticValidationError("The %s product needs a sta_list env variable" %(a_original_dict['TYPE']))
        
        # check that there is no Lat and Lon with sta_list in the same req
        lat = a_prod_dict.get(const.LAT_K, None)
        lon = a_prod_dict.get(const.LON_K, None)
        
        if lat or lon:
            raise SemanticValidationError("The %s product cannot have sta_list and a lat or lon env variable in the same request message"\
                                           %(a_original_dict['TYPE']))
        
        #remove it
        a_prod_keys.remove(a_env)
        
        cls.transform(a_prod_dict, stalist)
    
    @classmethod
    def transform(cls, a_prod_dict, a_stalist):
        """ Transform the returned directory to formatted according to the Generic Data structure
            that is common to both new language and IMS2.0 language
            Args: 
                a_prod_dict : a product directory
                a_stalist   : latitude component
            
               
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        loc_dict = { 
                      const.TYPE_K        : 'STALIST',
                      const.STATIONS_K   : a_stalist,
                   }
        
        a_prod_dict['LOC'] = loc_dict
        
        # remove lat and lon from prod_dict
        del a_prod_dict[const.STALIST_K]
        
class RemoveEnvRule(object):
    """ 
       Simple Rule that removes the type from the a_prod_keys
    """
    
    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        """ removeRule (remove it from the prod_keys dict 
            Args:
                a_env      : the type treated
                a_prod_keys : the different env var names
                a_prod_dict : a product directory  
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        the_val = a_prod_dict.get(a_env, None)
        
        if not the_val:
            raise SemanticValidationError("The %s product needs a %s env variable" %(a_original_dict['TYPE'], a_env))
        
        #remove it
        a_prod_keys.remove(a_env)

class FilterdWaveformRule(object): 
    """ 
       Filtered SHI Rule: Arrival, Event and Origin product
    """ 
    ARRIVALSUBTYPE = ['AUTOMATIC', 'REVIEWED', 'GROUPED', 'ASSOCIATED', 'UNASSOCIATED'] 
    ARRIVALTYPE    = ['ARRIVAL', 'SLSD']
    FORMAT         = ['IMS2.0',  'GSE2.0']  

    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        """ Check the arrival subtype and format are known.
            Check that there is a bulltype
            Args: 
                a_prod_keys : the different env var names
                a_prod_dict : a product directory
               
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """

        p_type = a_prod_dict.get(const.TYPE_K, None)
        
        if not p_type:
            raise SemanticValidationError("No TYPE defined in the following product dictionary %s" % (a_prod_dict))

        # arrival do some specific checking
        if p_type in cls.ARRIVALTYPE:
            cls.check_arrival_info(a_prod_keys, a_prod_dict)
        
        format   = a_prod_dict.get(const.FORMAT_K, None)
        
        # no format
        if not format:
            a_prod_dict[const.FORMAT_K] = 'IMS2.0' 
        elif format.upper() not in cls.FORMAT:
            raise SemanticValidationError("The %s product does not support the format %s" % (p_type, format))
       
        # need a BULLTYPE
        bull_type = a_prod_dict.get(const.BULLTYPE_K, None)
        
        # check if there is a bull_type present
        if not bull_type:
            raise SemanticValidationError("The %s needs a bull_type env variable" % (p_type) )
        
        # do the necessary transformation
        cls.transform(a_prod_dict, bull_type, p_type)
        
        #remove it
        if format:
            a_prod_keys.remove(const.FORMAT_K)
        
        # remove type
        a_prod_keys.remove(const.TYPE_K)
        
    @classmethod
    def check_arrival_info(cls, a_prod_keys, a_prod_dict):
        """ Check Arrival information
        
            Args: 
                a_prod_keys : the different env var names
                a_prod_dict : a product dictionary
               
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        
        """
        sub_type = a_prod_dict.get(const.SUBTYPE_K, None)
        
        # sub_type is optional
        if sub_type and sub_type.upper() not in cls.ARRIVALSUBTYPE:
            raise SemanticValidationError("Arrivals or SLSDs do not support the subtype %s" % (sub_type))
        
        #remove it
        if sub_type:
            a_prod_keys.remove(const.SUBTYPE_K)
        
    @classmethod
    def transform(cls, a_prod_dict, a_bull_type, a_type):
        """ Transform the returned directory to formatted according to the Generic Data structure
            that is common to both new language and IMS2.0 language
            Args: 
                a_prod_dict : a product dictionary
                a_bull_type : the type of product
                a_type      : the type of filter
               
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        # fill dict with new values
        a_prod_dict[const.TECHNOLOGYFAMILY] = 'SHI'
        a_prod_dict[const.TECHNOLOGYTYPE]   = 'UNKNOWN'
        
        a_prod_dict[const.PRODUCTFAMILY]    = 'BULLETIN'
        a_prod_dict[const.PRODUCTTYPE]      = a_bull_type.upper()
        
        a_prod_dict[const.FILTER]           = a_type.upper()
        
        #remove type and bulltype from dir 
        del a_prod_dict[const.TYPE_K]

        
class WaveformRule(object): 
    """ 
       WaveformRule Class
    """ 
    SUBFORMAT         = ['CM6', 'CM7', 'INT', 'CSF'] 
    FORMAT            = ['IMS1.0', 'IMS2.0',  'GSE2.0'] 
    
    DEFAULT_SUBFORMAT = 'CM6' 
    DEFAULT_FORMAT    = 'IMS2.0' 
    
    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        """ check that the product is there and remove the type and options
            Args: 
                a_prod_keys : the different env var names
                a_prod_dict : a product directory
               
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        format   = a_prod_dict.get(const.FORMAT_K, None)
        
        # no format put a default format
        if not format:
            a_prod_dict[const.FORMAT_K] = cls.DEFAULT_FORMAT  
        elif format.upper() not in cls.FORMAT:
            raise SemanticValidationError("The WAVEFORM product does not support the format %s" % (format))
        else:
            #remove it
            a_prod_keys.remove(const.FORMAT_K)
        
        subformat = a_prod_dict.get(const.SUBFORMAT_K, None)
        
        # no subformat use the default
        if not subformat:
            a_prod_dict[const.SUBFORMAT_K] = cls.DEFAULT_SUBFORMAT  
        elif subformat.upper() not in cls.SUBFORMAT:
            raise SemanticValidationError("The WAVEFORM product does not support the sub format %s:%s" % (format, subformat))
        else:
            # all good remove it
            a_prod_keys.remove(const.SUBFORMAT_K)
        
        cls.transform(a_prod_dict)
        
            # remove type
        a_prod_keys.remove(const.TYPE_K)
    
    @classmethod
    def transform(cls, a_prod_dict):
        """ Transform the returned directory to formatted according to the Generic Data structure
            that is common to both new language and IMS2.0 language
            Args: 
                a_prod_dict : a product dictionary
               
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        # fill dict with new values
        a_prod_dict[const.TECHNOLOGYFAMILY] = 'SHI'
        a_prod_dict[const.TECHNOLOGYTYPE]   = 'UNKNOWN'
        
        a_prod_dict[const.PRODUCTFAMILY]    = 'DATA'
        a_prod_dict[const.PRODUCTTYPE]      = 'WAVEFORM'
         
        #remove type from dir 
        del a_prod_dict[const.TYPE_K]

class BulletinRule(object): 
    """ 
       BulletinRule Class
    """ 
    SUBFORMAT = ['SHORT', 'LONG'] 
    FORMAT    = ['IMS1.0', 'IMS2.0',  'GSE2.0']  
    
    DEFAULT_SUBFORMAT = 'SHORT' 
    DEFAULT_FORMAT    = 'IMS2.0'
    
    
    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        """ check that the product is there and remove the type and options
            Args: 
                a_prod_keys : the different env var names
                a_prod_dict : a product directory
               
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        format   = a_prod_dict.get(const.FORMAT_K, None)
        
        if not format:
            a_prod_dict[const.FORMAT_K] = cls.DEFAULT_FORMAT
        elif format.upper() not in cls.FORMAT:
            raise SemanticValidationError("The BULLETIN product does not support the format %s" % (format))
        else:
            #remove it
            a_prod_keys.remove(const.FORMAT_K)
        
        subformat = a_prod_dict.get(const.SUBFORMAT_K, None)
        
        if subformat: 
            if subformat.upper() not in cls.SUBFORMAT:
                raise SemanticValidationError("The BULLETIN product does not support the sub format %s:%s" % (format, subformat))
        
            #remove it
            a_prod_keys.remove(const.SUBFORMAT_K)
        else:
            #add default sub format 
            a_prod_dict[const.SUBFORMAT_K] = cls.DEFAULT_SUBFORMAT
        
        cls.transform(a_prod_dict)
        
        # remove type
        a_prod_keys.remove(const.TYPE_K)
    
    @classmethod
    def transform(cls, a_prod_dict):
        """ Transform the returned directory to formatted according to the Generic Data structure
            that is common to both new language and IMS2.0 language
            Args: 
                a_prod_dict : a product dictionary
               
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        # fill dict with new values
        a_prod_dict[const.TECHNOLOGYFAMILY] = 'SHI'
        a_prod_dict[const.TECHNOLOGYTYPE]   = 'UNKNOWN'
        
        a_prod_dict[const.PRODUCTFAMILY]    = 'BULLETIN'
        a_prod_dict[const.PRODUCTTYPE]      = a_prod_dict.get(const.BULLTYPE_K, None)
         
        #remove type from dir 
        del a_prod_dict[const.TYPE_K]

class TestProductRule(object):
    """
       Rule for a test product
       No checkings
    """
    
    FORMAT        = ['IMS1.0', 'IMS2.0',  'GSE2.0'] 
    
    
    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        """ check that the product is there and remove the type and options
            Args: 
                a_prod_keys : the different env var names
                a_prod_dict : a product directory
               
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        format   = a_prod_dict.get(const.FORMAT_K, None)
        
        if not format:
            #add default
            a_prod_dict[const.FORMAT_K] = "IMS2.0" 
      
        #remove it
        if format:
            a_prod_keys.remove(const.FORMAT_K)
        
        # remove type
        a_prod_keys.remove(const.TYPE_K)
        
        # do the necessary transformation
        cls.transform(a_prod_dict)
    
    @classmethod
    def transform(cls, a_prod_dict):
        """ Transform the returned directory to formatted according to the Generic Data structure
            that is common to both new language and IMS2.0 language
            Args: 
                a_prod_dict : a product directory
               
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        product_type = a_prod_dict.get(const.TYPE_K, None)
                
        if not product_type:
            raise SemanticValidationError("Fatal error, no type in the current product dictionary %s" % (a_prod_dict))
        
        
        # fill dict with new values
        a_prod_dict[const.TECHNOLOGYFAMILY] = 'TEST'
        a_prod_dict[const.TECHNOLOGYTYPE]   = 'TEST'
        
        a_prod_dict[const.PRODUCTFAMILY]    = 'TEST'
        a_prod_dict[const.PRODUCTTYPE]      = product_type
        
        #remove type from dir 
        del a_prod_dict[const.TYPE_K]

class SimpleWaveformProductRule(object):
    """
       Rule for a simple waveform product
       Check the format
    """
    
    FORMAT        = ['IMS1.0', 'IMS2.0',  'GSE2.0'] 
    
    
    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        """ check that the product is there and remove the type and options
            Args: 
                a_prod_keys : the different env var names
                a_prod_dict : a product directory
               
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        format   = a_prod_dict.get(const.FORMAT_K, None)
        
        if not format:
            #add default
            a_prod_dict[const.FORMAT_K] = "IMS2.0" 
        elif format.upper() not in cls.FORMAT:
            raise SemanticValidationError("%s WAVEFORM product does not support the format %s" % (a_env, format)) 
           
        #remove it
        if format:
            a_prod_keys.remove(const.FORMAT_K)
        
        # remove type
        a_prod_keys.remove(const.TYPE_K)
        
        # do the necessary transformation
        cls.transform(a_prod_dict)
    
    @classmethod
    def transform(cls, a_prod_dict):
        """ Transform the returned directory to formatted according to the Generic Data structure
            that is common to both new language and IMS2.0 language
            Args: 
                a_prod_dict : a product directory
               
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        product_type = a_prod_dict.get(const.TYPE_K, None)
                
        if not product_type:
            raise SemanticValidationError("Fatal error, no type in the current product dictionary %s" % (a_prod_dict))
        
        
        # fill dict with new values
        a_prod_dict[const.TECHNOLOGYFAMILY] = 'SHI'
        a_prod_dict[const.TECHNOLOGYTYPE]   = 'UNKNOWN'
        
        a_prod_dict[const.PRODUCTFAMILY]    = 'UNKNOWN'
        a_prod_dict[const.PRODUCTTYPE]      = product_type
        
        #remove type from dir 
        del a_prod_dict[const.TYPE_K]

class RadionuclideProductRule(object): 
    """ 
       RadionuclideBulletinRule Class
    """ 
    FORMAT        = ['RMS1.0', 'RMS2.0',  'GSE2.0']  
    
    PRODUCTFAMILY  = {
                      'DATA'     : [ 'BLANKPHD', 'CALIBPHD', 'DETBKPHD', 'GASBKPHD', 'QCPHD', 'SPHDP', 'SPHDF'],
                      'BULLETIN' : [ 'ARR', 'RRR', 'RLR', 'RNPS', 'SSREB', 'MET', 'RMSSOH'],
                      'ALERT'    : [ 'ALERTFLOW', 'ALERTSYSTEM', 'ALERTTEMP', 'ALERTUPS' ],
                     }
    
    @classmethod
    def check(cls, a_env, a_prod_keys, a_prod_dict , a_original_dict): # pylint: disable-msg=W0613
        """ check that the product is there and remove the type and options
            Args: 
                a_prod_keys : the different env var names
                a_prod_dict : a product directory
               
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        format   = a_prod_dict.get(const.FORMAT_K, None)
        
        if format and format.upper() not in cls.FORMAT:
            raise SemanticValidationError("The radionuclide Bulletin %s product do not support the format %s" % (a_env, format))
        else:
            #add default
            a_prod_dict[const.FORMAT_K] = "RMS2.0"
            
        #remove it
        if format:
            a_prod_keys.remove(const.FORMAT_K)
        
        # remove type
        a_prod_keys.remove(const.TYPE_K)
        
        cls.transform(a_prod_dict)
    
    @classmethod
    def transform(cls, a_prod_dict):
        """ Transform the returned directory to formatted according to the Generic Data structure
            that is common to both new language and IMS2.0 language
            Args: 
                a_prod_dict : a product directory
               
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        product_type = a_prod_dict.get(const.TYPE_K, None)
                
        if not product_type:
            raise SemanticValidationError("Fatal error, no type in the current product dictionary %s" % (a_prod_dict))
        
        product_fam = None
        
        #get product family
        types = cls.PRODUCTFAMILY.keys()
        for typ in types:
            if product_type in cls.PRODUCTFAMILY[typ]:
                product_fam = typ
                break
        
        if not product_fam:
            raise SemanticValidationError("Unknown product family %s" % (product_fam))
        
        # fill dict with new values
        a_prod_dict[const.TECHNOLOGYFAMILY] = 'RAD'
        a_prod_dict[const.TECHNOLOGYTYPE]   = 'UNKNOWN'
        
        a_prod_dict[const.PRODUCTFAMILY]    = product_fam
        a_prod_dict[const.PRODUCTTYPE]      = product_type
        
        #remove type from dir 
        del a_prod_dict[const.TYPE_K]
        
        
       
# the dict and lists that acts as factory      
REQUIRED_REQUEST_ENV_VAR = {
    'ARRIVAL'         : ['ARRIVAL', 'DATE', 'BULLTYPE'],
    'SLSD'            : ['ARRIVAL', 'DATE', 'BULLTYPE'],
    'WAVEFORM'        : ['WAVEFORM', 'DATE', 'STALIST'],
    'CHANNEL'         : ['CHANNEL'],
    'CHANSTATUS'      : ['CHANSTATUS','DATE'],
    'COMMENT'         : ['COMMENT'],
    'COMMSTATUS'      : ['COMMSTATUS', 'DATE'],
    'EVENT'           : ['EVENT', 'BULLTYPE', 'DATE'],
    
    #simple bulletin
    'BULLETIN'        : ['BULLETIN', 'BULLTYPE', 'DATE'],
    'EXECSUM'         : ['EXECSUM', 'DATE'],
    'NETWORK'         : ['NETWORK'],
    'ORIGIN'          : ['ORIGIN', 'BULLTYPE', 'DATE'],
    'OUTAGE'          : ['OUTAGE', 'DATE'],
    'RESPONSE'        : ['RESPONSE'],
    'STATION'         : ['STATION'],
    'STASTATUS'       : ['STASTATUS','DATE'],
    'DETECTION'       : ['DETECTION', 'DATE'],
    
    
    # Radionuclide
    'ARR'             : ['ARR', 'DATE'],
    'RRR'             : ['RRR', 'DATE'],
    'RLR'             : ['RLR', 'DATE'],
    'RNPS'            : ['RNPS', 'DATE'],
    'SSREB'           : ['SSREB', 'DATE'],
    'MET'             : ['MET', 'DATE'],
    'RMSSOH'          : ['RMSSOH', 'DATE'],
    'BLANKPHD'        : ['BLANKPHD', 'DATE'],
    'CALIBPHD'        : ['CALIBPHD', 'DATE'],
    'DETBKPHD'        : ['DETBKPHD', 'DATE'],
    'GASBKPHD'        : ['GASBKPHD', 'DATE'],
    'QCPHD'           : ['QCPHD', 'DATE'],
    'SPHDP'           : ['SPHDP', 'DATE'],
    'SPHDF'           : ['SPHDF', 'DATE'],
    'ALERTFLOW'       : ['ALERTFLOW', 'DATE'],
    'ALERTSYSTEM'     : ['ALERTSYSTEM', 'DATE'],
    'ALERTTEMP'       : ['ALERTTEMP', 'DATE'],
    'ALERTUPS'        : ['ALERTUPS', 'DATE'],
    
    # Test products
    'TESTPRODUCT'     : ['TESTPRODUCT'],
    
}

SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS = [ 'FREQUENCY', 'SUB_PRODUCT_DESC']
# the dict and lists that acts as factory      
REQUIRED_SUBSCRIPTION_ENV_VAR = {
    #Subscription Commands
    'COMMAND'      : ['SUBSCR_COMMAND'],
                                 
                                 
    'ARRIVAL'         : ['ARRIVAL', 'BULLTYPE'] + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'SLSD'            : ['ARRIVAL', 'BULLTYPE'] + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'WAVEFORM'        : ['WAVEFORM', 'STALIST'] + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'CHANNEL'         : ['CHANNEL']             + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'CHANSTATUS'      : ['CHANSTATUS']          + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'COMMENT'         : ['COMMENT']             + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'COMMSTATUS'      : ['COMMSTATUS']          + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'EVENT'           : ['EVENT', 'BULLTYPE']   + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    
    #simple bulletin
    'BULLETIN'        : ['BULLETIN', 'BULLTYPE']    + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'EXECSUM'         : ['EXECSUM']                 + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'NETWORK'         : ['NETWORK']                 + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'ORIGIN'          : ['ORIGIN', 'BULLTYPE']      + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'OUTAGE'          : ['OUTAGE']                  + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'RESPONSE'        : ['RESPONSE']                + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'STATION'         : ['STATION']                 + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'STASTATUS'       : ['STASTATUS']               + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'DETECTION'       : ['DETECTION']               + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    
    
    # Radionuclide
    'ARR'             : ['ARR', ]                   + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'RRR'             : ['RRR', ]                   + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'RLR'             : ['RLR', ]                   + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'RNPS'            : ['RNPS', ]                  + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'SSREB'           : ['SSREB', ]                 + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'MET'             : ['MET', ]                   + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'RMSSOH'          : ['RMSSOH', ]                + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'BLANKPHD'        : ['BLANKPHD', ]              + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'CALIBPHD'        : ['CALIBPHD', ]              + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'DETBKPHD'        : ['DETBKPHD', ]              + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'GASBKPHD'        : ['GASBKPHD', ]              + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'QCPHD'           : ['QCPHD', ]                 + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'SPHDP'           : ['SPHDP', ]                 + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'SPHDF'           : ['SPHDF', ]                 + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'ALERTFLOW'       : ['ALERTFLOW', ]             + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'ALERTSYSTEM'     : ['ALERTSYSTEM', ]           + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'ALERTTEMP'       : ['ALERTTEMP', ]             + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    'ALERTUPS'        : ['ALERTUPS', ]              + SUBSCRIPTION_PRODUCT_SPECIFIC_ENV_VARS,
    
    # Test products
    'TESTPRODUCT'     : ['TESTPRODUCT'],
}

OPTIONAL_ENV_VAR = {
    'ARRIVAL'       : ['ARRIVALLIST', 'BEAMLIST', 'CHANLIST', 'STALIST', 'TIMESTAMP'], 
    'SLSD'          : ['ARRIVALLIST', 'BEAMLIST', 'CHANLIST', 'STALIST', 'TIMESTAMP'],
    'WAVEFORM'      : ['AUXLIST', 'BEAMLIST', 'CHANLIST','RELATIVETO', 'TIMESTAMP'], 
    'CHANNEL'       : ['AUXLIST', 'CHANLIST', 'LAT', 'LON', 'STALIST', 'TIMESTAMP'],
    'CHANSTATUS'    : ['AUXLIST', 'CHANLIST', 'STALIST','TIMESTAMP'],
    'COMMENT'       : ['ARRIVALLIST', 'EVENTLIST', 'ORIGINLIST', 'STALIST', 'DATE', 'TIMESTAMP' ],
    'COMMSTATUS'    : ['COMMLIST', 'TIMESTAMP' ],
    'EVENT'         : ['DEPTH', 'DEPTHMINUSERROR', 'EVENTLIST', 'EVENTSTADIST', \
                       'GROUPBULLLIST', 'LAT', 'LON', 'MAG', 'MAGTYPE', \
                       'MBMINUSMS', 'STALIST', 'TIMESTAMP' ],
    'BULLETIN'      : ['ARRIVALLIST', 'DEPTH', 'DEPTHMINUSERROR', 'EVENTLIST', 'EVENTSTADIST', \
                       'GROUPBULLLIST', 'LAT', 'LON', 'MAG', 'MAGTYPE', \
                       'MBMINUSMS', 'ORIGINLIST', 'STALIST', 'TIMESTAMP' ],
    'EXECSUM'       : ['DEPTH', 'DEPTHMINUSERROR', 'EVENTLIST', 'EVENTSTADIST', \
                       'LAT', 'LON', 'MAG', 'MAGTYPE', \
                       'ORIGINLIST', 'STALIST', 'TIMESTAMP' ],
    'NETWORK'       : ['STALIST', 'TIMESTAMP'],
    'ORIGIN'        : ['DEPTH', 'DEPTHMINUSERROR', 'EVENTSTADIST', \
                       'LAT', 'LON', 'MAG', 'MAGTYPE', 'MBMINUSMS', \
                       'ORIGINLIST', 'STALIST', 'TIMESTAMP' ],
    'OUTAGE'        : ['AUXLIST', 'CHANLIST', 'STALIST', 'TIMESTAMP'],
    'RESPONSE'      : ['AUXLIST', 'CHANLIST', 'STALIST', 'DATE', 'TIMESTAMP'],
    'STATION'       : ['LAT', 'LON', 'STALIST', 'TIMESTAMP'],
    'STASTATUS'     : ['AUXLIST', 'STALIST', 'TIMESTAMP'],
    'DETECTION'     : ['STALIST', 'LAT', 'LON', 'TIMESTAMP'],
    
    
    # Radionuclide
    'ARR'           : ['STALIST', 'TIMESTAMP'],
    'RRR'           : ['STALIST', 'TIMESTAMP'],
    'RLR'           : ['STALIST', 'TIMESTAMP'],
    'SSREB'         : ['STALIST', 'TIMESTAMP'],
    'ALERTFLOW'     : ['STALIST', 'TIMESTAMP'],
    'ALERTSYSTEM'   : ['STALIST', 'TIMESTAMP'],
    'ALERTTEMP'     : ['STALIST', 'TIMESTAMP'],
    'ALERTUPS'      : ['STALIST', 'TIMESTAMP'],
    'BLANKPHD'      : ['STALIST', 'TIMESTAMP'],
    'CALIBPHD'      : ['STALIST', 'TIMESTAMP'],
    'DETBKPHD'      : ['STALIST', 'TIMESTAMP'],
    'GASBKPHD'      : ['STALIST', 'TIMESTAMP'],
    'QCPHD'         : ['STALIST', 'TIMESTAMP'],
    'SPHDP'         : ['STALIST', 'TIMESTAMP'],
    'SPHDF'         : ['STALIST', 'TIMESTAMP'],
    'MET'           : ['STALIST', 'TIMESTAMP'],
    'RMSSOH'        : ['STALIST', 'TIMESTAMP'],
    'RNPS'          : ['STALIST', 'TIMESTAMP'],
}

ENV_RULES = {
   
    
    # Radionuclide products
    'ARR'               : RadionuclideProductRule.check,
    'RRR'               : RadionuclideProductRule.check,
    'RLR'               : RadionuclideProductRule.check,
    'SSREB'             : RadionuclideProductRule.check,
    'ALERTFLOW'         : RadionuclideProductRule.check,
    'ALERTSYSTEM'       : RadionuclideProductRule.check,
    'ALERTTEMP'         : RadionuclideProductRule.check,
    'ALERTUPS'          : RadionuclideProductRule.check,
    'BLANKPHD'          : RadionuclideProductRule.check,
    'CALIBPHD'          : RadionuclideProductRule.check,
    'DETBKPHD'          : RadionuclideProductRule.check,
    'GASBKPHD'          : RadionuclideProductRule.check,
    'QCPHD'             : RadionuclideProductRule.check,
    'SPHDP'             : RadionuclideProductRule.check,
    'SPHDF'             : RadionuclideProductRule.check,
    'MET'               : RadionuclideProductRule.check,
    'RMSSOH'            : RadionuclideProductRule.check,
    'RNPS'              : RadionuclideProductRule.check,
    
    # Waveform products
    'ARRIVAL'           : FilterdWaveformRule.check,
    'ORIGIN'            : FilterdWaveformRule.check,
    'EVENT'             : FilterdWaveformRule.check,
    'WAVEFORM'          : WaveformRule.check,
    'CHANNEL'           : SimpleWaveformProductRule.check,
    'CHANSTATUS'        : SimpleWaveformProductRule.check,
    'COMMENT'           : SimpleWaveformProductRule.check,
    'COMMSTATUS'        : SimpleWaveformProductRule.check,
    'BULLETIN'          : BulletinRule.check,
    'EXECSUM'           : SimpleWaveformProductRule.check,
    'NETWORK'           : SimpleWaveformProductRule.check,
    'OUTAGE'            : SimpleWaveformProductRule.check,
    'RESPONSE'          : SimpleWaveformProductRule.check,
    'STATION'           : SimpleWaveformProductRule.check,
    'STASTATUS'         : SimpleWaveformProductRule.check,
    'DETECTION'         : SimpleWaveformProductRule.check,
    
    # Test products
    'TESTPRODUCT'       : TestProductRule.check,
    
    # Parameters
    'DATE'              : DateRule.check,                  
    'BULLTYPE'          : BullTypeRule.check,
    'STALIST'           : StaListRule.check,
    'TIMESTAMP'         : RemoveEnvRule.check, 
    'RELATIVETO'        : RelativeToRule.check,
    'LAT'               : LatLonRule.check,
    'LON'               : LatLonRule.check,
    'CHANLIST'          : RemoveEnvRule.check, #simple chanlist for the moment (in the future check if the chan exists
    'BEAMLIST'          : RemoveEnvRule.check,
    'AUXLIST'           : RemoveEnvRule.check,   
    'ORIGINLIST'        : RemoveEnvRule.check,
    'ARRIVALLIST'       : RemoveEnvRule.check,
    'EVENTLIST'         : RemoveEnvRule.check, 
    'COMMLIST'          : RemoveEnvRule.check, 
    'DEPTH'             : FloatRule.check, 
    'DEPTHMINUSERROR'   : FloatRule.check,
    'EVENTSTADIST'      : RemoveEnvRule.check,
    'GROUPBULLLIST'     : RemoveEnvRule.check,
    #'MAG'               : FloatRule.check,MagSibblingsRule
    #'MAGTYPE'           : MagTypeRule.check,
    'MAG'               : MagSibblingsRule.check,
    'MAGTYPE'           : MagSibblingsRule.check,
    'MBMINUSMS'         : FloatRule.check,
    
    #SUBSCRIPTION RULES
    'FREQUENCY'         : FrequencyRule.check,
    'SUBSCRLIST'        : SubscrListRule.check,
    'SUBSCR_COMMAND'    : SubscriptionCommandRule.check,
    'SUB_PRODUCT_DESC'  : SubProductDesc.check        
}

# list of ignored env params
IGNORED_ENV_VARS = [  'DEPTHCONF', 
                      'DEPTHKVALUE', 
                      'DEPTHTHRESH', 
                      'HYDROCPTHRESH', 
                      'HYDROTETHRESH', 
                      'LOCCONF',
                      'MAGPREFMB',
                      'MAGPREFMS',
                      'MBERR',
                      'MBMSCONF',
                      'MBMSSLOPE',
                      'MBMSTHRESH',
                      'MINDPSNRPP',
                      'MINDPSNRSP',
                      'MINMB',
                      'MINMOVEOUTPP',
                      'MINMOVEOUTSP',
                      'MINDEF',
                      'MINNDPPP',
                      'MINND_SP',
                      'MINNSTAMS',
                      'MINWDEPTHTHRESH',
                      'MSERR',
                      'REGCONF']
 
class RequestSemanticValidator(object):
    '''
       The  RequestSemanticValidator is like a RuleEngine
    '''
    def __init__(self):
        '''
        The simple Constructor
        '''
        self.__log__ = LoggerFactory.get_logger(self)
        
        self._required_env_vars = REQUIRED_REQUEST_ENV_VAR
        
    def check_product(self, a_orig_prod_dict):
        """ Check the internal rules for each this particular product
        
            Args: a_orig_dict : original product directory
               
            Returns: the modified product directory
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        
        # clone the prod_dict
        prod_dict = copy.deepcopy(a_orig_prod_dict)
        prod_keys = a_orig_prod_dict.keys()
        
        prod_type = prod_dict.get('TYPE', None)
        
        if prod_type:
            
            # check if prod_type exist
            if not prod_type in self._required_env_vars.keys():
                raise SemanticValidationError("%s is not a IMS2.0 product type" % (prod_type))
            
            self._check_required_env_var(prod_type, prod_keys, prod_dict, a_orig_prod_dict)
             
            self._check_optional_env_var(prod_type, prod_keys, prod_dict, a_orig_prod_dict)
        
        else:
            raise SemanticValidationError("No product type in %s" % (a_orig_prod_dict))
        
        return prod_dict
    
    def check_request(self, a_req_dict):
        """
           Check the internal rules starting from a request dict
           
           Args: a_req_dict  : req dictionary
                 a_prod_dict : dict of products
               
            Returns: None
           
        """
        self.__log__.debug("received request dict = %s\n" % (a_req_dict) )
        #import pprint
        #pp = pprint.PrettyPrinter(depth=6)
        #pp.pprint(a_req_dict)
        
        # deep copy the directory
        result = copy.deepcopy(a_req_dict)
        
        prod_list = a_req_dict.get('PRODUCTLIST', None)
        #list of products
        result_prod_list = []
        
        if prod_list:
            for prod in prod_list:            
                # remove ignored env vars
                prod_keys = prod.keys()
                self._remove_ignored_env_vars(result, prod_keys, prod)
                result_prod_list.append(self.check_product(prod))
                
            result['PRODUCTLIST'] = result_prod_list
            
        else:
            raise SemanticValidationError("There are no products in %s" % (a_req_dict))
        
        return result
      
    def _remove_ignored_env_vars(self, a_req_dict, a_prod_keys, a_prod_dict ):
        """ Remove the env vars that are ignored as they were designed to be used with NSEBs
            Args:
                  a_prod_keys     : keys of the original dict 
                  a_prod_dict     : dict of products
        """ 
        removed = []
        keys = copy.deepcopy(a_prod_keys)
        for env in keys:
            if env in IGNORED_ENV_VARS:
                #remove the key from prod_dict and prod_keys
                removed.append(env)
                
                a_prod_keys.remove(env)
                #remove type from dir 
                del a_prod_dict[env]
                
        if len(removed) > 0:
            a_req_dict["ERROR_MESSAGES"] = ['Ignore the following National Event Bulletin Env variables : %s.' %(', '.join([elem for elem in removed])), ]
    
    def _check_required_env_var(self, a_type, a_prod_keys, a_prod_dict, a_original_dict):
        """ Check the required internal rules for each this particular product    
            Args: a_type          : type of product to check
                  a_prod_keys     : keys of the original dict 
                  a_prod_dict     : dict of products
                  a_original_dict : original product directory
               
            Returns: None
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        # get REQUIRED_REQUEST_ENV_VAR list for each particular type
        required_env = self._required_env_vars[a_type] 
        
        for env in required_env:
            rule = ENV_RULES.get(env, None)
            if rule:
                rule(env, a_prod_keys, a_prod_dict, a_original_dict)
            else:
                raise SemanticValidationError("There is no rules for %s in required env vars" % (env))
            
        
    
    def _check_optional_env_var(self, a_type, a_prod_keys, a_prod_dict , a_original_dict):
        """ Check the optional values   
            Args: a_type          : type of product to check
                  a_prod_keys     : keys of the original dict 
                  a_prod_dict     : dict of products
                  a_original_dict : original product directory
               
            Returns:
        
            Raises:
               exception SemanticValidationError if one of the constraints are not respected
        """
        

        optional_env = OPTIONAL_ENV_VAR.get(a_type, None)
        
        if optional_env:
            # loop over what is left in the a_prod_keys and check if they are in the optional env
            # in the case they are optional env run the corresponding rule
            # the loop is not pythonesc as the encounetered elements are removed from the list by the rules
            while len(a_prod_keys) > 0:
                env = a_prod_keys[0]
                if env in optional_env:
                    rule = ENV_RULES.get(env, None)
                    if rule:
                        rule(env, a_prod_keys, a_prod_dict , a_original_dict)
                    else:
                        raise SemanticValidationError("There is no rules for %s in OPTIONAL_ENV_RULES" % (env))
                else:
                    raise SemanticValidationError("The keyword %s is not supported by the product %s"%(env, a_type))
                
###
###        to finish: 
###        - GROUPBULLLIST Rule : check that it references an existing bulletin
###        - EVENTSTADIST Rule : check that start < end
###        - STALIST Rule : check against the list of stations and depending of the technologie type (rad or shi)
###        - Add complex BULLETIN for IDC_NEB and IDC_NSEB
###        - Manage Range like in DEPTHMINUSERROR with min and max,
###        - Number* (123457*) to be support ?
###        - Depth,MAG param with a number
###        - Add negative numbers in range
###        - if no constraints do not do anything
###        -  if mag_type and no mag default = Mb
###    
                
class SubscriptionSemanticValidator(RequestSemanticValidator):
    
    def __init__(self):
        super(SubscriptionSemanticValidator, self).__init__()
        
        self._required_env_vars = REQUIRED_SUBSCRIPTION_ENV_VAR

    def check_request(self, a_req_dict):
        """
           Check the internal rules starting from a request dict
           
           Args: a_req_dict  : req dictionary
                 a_prod_dict : dict of products
               
            Returns: None
           
        """
        self.__log__.debug("received request dict = %s\n" % (a_req_dict) )
        #import pprint
        #pp = pprint.PrettyPrinter(depth=6)
        #pp.pprint(a_req_dict)
        
        # deep copy the directory
        result = copy.deepcopy(a_req_dict)
        
        prod_list = a_req_dict.get(product_dict_const.PRODUCTLIST, None)
        command_list = a_req_dict.get(product_dict_const.COMMANDLIST, None)
        
        #list of products
        result_prod_list = []
        
        if prod_list:
            for prod in prod_list:
                # remove ignored env vars
                prod_keys = prod.keys()
                self._remove_ignored_env_vars(a_req_dict, prod_keys, prod)
                result_prod_list.append(self.check_product(prod))
                
            result[product_dict_const.PRODUCTLIST] = result_prod_list
        elif command_list:
            for command in command_list:
                result_prod_list.append(self.check_product(command))
                
            result[product_dict_const.COMMANDLIST] = result_prod_list
        else:
            raise SemanticValidationError("There are no products in %s" % (a_req_dict))
        
        return result
