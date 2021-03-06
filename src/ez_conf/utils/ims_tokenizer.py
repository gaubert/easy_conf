'''
Created on May 16, 2009

@author: guillaume.aubert@ctbto.org
'''
import re

from nms_common.parser.common.regex_util import group, maybe
from nms_common.parser.exceptions import ParserError

# pylint: disable-msg=R0903,R0902,R0201,R0913,R0912       

class LexerError(ParserError):
    """LexerError Class"""
    
    def __init__(self, a_msg, a_line, a_line_num, a_pos, a_suggest = ""):
        
        super(LexerError, self).__init__(a_msg, a_line, a_line_num, a_pos, a_suggest)
    
    
class IllegalCharacterError(LexerError):
    """IllegalCharacterError Class"""

    def __init__(self, a_line, a_line_num, a_pos, a_suggest = ""):
        
        msg = "Illegal Character %s in Line %d, position %d."% (a_line[a_pos], a_line_num, a_pos)
        
        super(IllegalCharacterError, self).__init__(msg, a_line, a_line_num, a_pos, a_suggest)
        
        self._instrumented_line  = a_line[:a_pos] + "(ERR)=>" + a_line[a_pos:]

class BadTokenError(LexerError):
    """ BadTokenError Exception """
    
    def __init__(self, a_line, a_line_num, a_pos, a_expected_token_types, a_found_token): #IGNORE:R0913
        
        msg = "Found Token with type %s and value [%s] in Line %s, position %s. Was expecting %s."\
              % (a_found_token.type, a_found_token.value, a_line_num, a_pos, a_expected_token_types)

        super(BadTokenError, self).__init__(msg, a_line, a_line_num, a_pos)
         
         
class NonExistingTokenError(LexerError):
    """ NonExistingToken exception """
    
    def __init__(self, a_msg):
        super(NonExistingTokenError, self).__init__(a_msg, None, -1, -1)

class TokensNotFoundError(LexerError):
    """ TokensNotFoundError exception """
    def __init__(self, a_msg):
        super(TokensNotFoundError, self).__init__(a_msg, None, -1, -1)

class BadTokenizedStringError(LexerError):
    """ Bad tokenized string exception """
    def __init__(self, a_msg):
        super(BadTokenizedStringError, self).__init__(a_msg, None, -1, -1)


class TokenNames(object):   #IGNORE:WR0903
    """ 
       Utility Class to get all token names
    """
    def __init__(self):
        pass
    
    def __getattr__(self, a_name):
        """ to be used to check if a token exist """
        if a_name not in  TokenCreator.get_all_tokens():
            raise Exception("No token with name %s has been registered"%(a_name))
        
        return a_name
    
    def get_all_tokens(self):
        """ get all registered tokens 
        
            Returns: List of registered existing tokens
        """
        
        return TokenCreator.get_all_tokens()
    

class TokenCreator(object):
    """ Class used to host the Grammar Tokens.
        this class needs to be instanciated to use the __getattr__ facility
    """ 
    # singleton instance
    __instance    = None
    
    HEAD          = 'HEAD'
    TAIL          = 'TAIL'
    KEYWORD       = 'KEYWORD'
    SHI_PRODUCT   = 'SHI_PRODUCT'
    RAD_PRODUCT   = 'RAD_PRODUCT'
    TEST_PRODUCT  = 'TEST_PRODUCT'
    
    SUBSCRIPTION_COMMAND = 'SUBSCR_COMMAND'
    
    TOKEN_NAMES  = TokenNames()
    
    _head            = []
    _tail            = []
    _keywords        = []
    _shi_products    = []
    _rad_products    = []
    
    _test_products   = []
        
    _static_tokens   = []
    
    _subscr_commands  = []
        
    #init Token RE
    _tokens_re       = {}
        
    # create token types
    _token_family    = { HEAD   : _head,  TAIL : _tail, \
                         KEYWORD : _keywords, SHI_PRODUCT : _shi_products, \
                         RAD_PRODUCT : _rad_products, TEST_PRODUCT : _test_products,
                         SUBSCRIPTION_COMMAND: _subscr_commands 
                       }
    @classmethod
    def register_token(cls, a_name, a_re, a_family):
        """ register a token with its associated regexpr
            
            Args:
               a_name : Token name
               a_re   : Token regular expression
               a_family : Token type (HEAD or KEYWORD or SHI_PRODUCT or RAD_PRODUCT or TAIL)
        
        """
        
        if a_family not in cls._token_family:
            raise Exception("No token type with name %s has been registered"%(a_name))
        else:
            cls._token_family[a_family].append(a_name)
            cls._tokens_re[a_name] = a_re
    
    @classmethod
    def register_static_token(cls, a_name):
        """ used to register token such as sub tokens or static token that will not be matched by the tokenizer.
            For example MIN, MAX, WCID, DATA
        """
        cls._static_tokens.append(a_name)
        
    @classmethod
    def get_token_family(cls, a_token):
        """ return the family of a token (important for the matching error) """
        
        for (t_type, type_list) in cls._token_family.items():
            if a_token in type_list:
                return t_type
    
    @classmethod
    def token_has_family(cls, a_token, a_type_list):
        """ True if a token has a particular type (important for the matching error)""" 
        for (t_type, t_list) in cls._token_family.items():
            if a_token in t_list:
                return True if t_type in a_type_list else False            
        
        return False
    
    @classmethod
    def get_ordered_tokens_list(cls):
        """ return ordered list of matchable tokens. 
            This is used to follow the precedence rules defined when registering the token
        """
        #TODO refactoring use on ordered dictionary for the token families
        return cls._head + cls._keywords + cls._shi_products + cls._rad_products + cls._test_products + cls._subscr_commands + cls._tail
    
    @classmethod
    def get_tokens_re(cls):
        """ return the dictionary of tokens regexpr """
        return cls._tokens_re
    
    @classmethod
    def get_tokens_with_type(cls, a_type):
        """ get all tokens for a particular type 
        
        
            Return: list of token with the passed type
        """
        
        if a_type not in cls._token_family:
            raise Exception("Token type %s doesn't exist"%(a_type))
        
        return cls._token_family[a_type]
    
    @classmethod
    def get_all_tokens(cls):
        """ return the full list of tokens """
        return cls._static_tokens + cls.get_ordered_tokens_list()
    
    @classmethod
    def is_a_product(cls, a_token):
        """ check that it is a product 
        
            :param a_token: the token to check 
        
            :returns: True if it is a RAD or SHI product False otherwise
        """
        
        if cls.get_token_family(a_token) in (cls.SHI_PRODUCT, cls.RAD_PRODUCT):
            return True
        else:
            return False
    
    
# register all tokens

# add static tokens
TokenCreator.register_static_token('ENDMARKER')

TokenCreator.register_static_token('MAX')

TokenCreator.register_static_token('MIN')

TokenCreator.register_static_token('WCID')

TokenCreator.register_static_token('DATA')

#register matchable tokens

#date time                   
DATETIME_RE = re.compile(r'((17|18|19|[2-9][0-9])\d\d)[-/.](0[1-9]|1[012]|[1-9])[-/.](0[1-9]|[12][0-9]|3[01]|[1-9])([tT ]?([0-1][0-9]|2[0-3]|[0-9])([:]?([0-5][0-9]|[0-9]))?([:]([0-5][0-9]|[0-9]))?([.]([0-9])+)?)?') # pylint: disable-msg=C0301
TokenCreator.register_token('DATETIME', DATETIME_RE, TokenCreator.HEAD)

#Add all keywords
# BOOLEAN Tokens
TRUE      = r'TRUE'
FALSE     = r'FALSE'
BOOLEAN   = group(TRUE, FALSE)

BOOLEAN_RE = re.compile(BOOLEAN,re.IGNORECASE)
TokenCreator.register_token('BOOLEAN', BOOLEAN_RE, TokenCreator.KEYWORD)

# BEGIN 
BEGIN_RE      = re.compile('BEGIN', re.IGNORECASE)
TokenCreator.register_token('BEGIN', BEGIN_RE, TokenCreator.KEYWORD)
# STOP
STOP_RE       = re.compile('STOP', re.IGNORECASE)
TokenCreator.register_token('STOP', STOP_RE, TokenCreator.KEYWORD)
# TO
TO_RE         = re.compile('TO', re.IGNORECASE)
TokenCreator.register_token('TO', TO_RE, TokenCreator.KEYWORD)
# OF
OF_RE         = re.compile('OF', re.IGNORECASE)
TokenCreator.register_token('OF', OF_RE, TokenCreator.KEYWORD)
# PART
PART_RE         = re.compile('PART', re.IGNORECASE)
TokenCreator.register_token('PART', PART_RE, TokenCreator.KEYWORD)
# MSGTYPE
MSGTYPE_RE    = re.compile('MSG_TYPE', re.IGNORECASE)
TokenCreator.register_token('MSGTYPE', MSGTYPE_RE, TokenCreator.KEYWORD)
# MSGID
MSGID_RE      = re.compile('MSG_ID', re.IGNORECASE)
TokenCreator.register_token('MSGID', MSGID_RE, TokenCreator.KEYWORD)
# LAT
LAT_RE        = re.compile('LAT', re.IGNORECASE)
TokenCreator.register_token('LAT', LAT_RE, TokenCreator.KEYWORD)
# LON
LON_RE        = re.compile('LON', re.IGNORECASE)
TokenCreator.register_token('LON', LON_RE, TokenCreator.KEYWORD)
# REFID
REFID_RE      = re.compile('REF_ID', re.IGNORECASE)
TokenCreator.register_token('REFID', REFID_RE, TokenCreator.KEYWORD)
# APPLICATION
APPLICATION_RE       = re.compile('APPLICATION', re.IGNORECASE)
TokenCreator.register_token('APPLICATION', APPLICATION_RE, TokenCreator.KEYWORD)
# EMAIL
EMAIL_RE      = re.compile('E-MAIL', re.IGNORECASE)
TokenCreator.register_token('EMAIL', EMAIL_RE, TokenCreator.KEYWORD)
# FTP
FTP_RE      = re.compile('FTP', re.IGNORECASE)
TokenCreator.register_token('FTP', FTP_RE, TokenCreator.KEYWORD)
#TIMESTAMP
TIMESTAMP_RE        = re.compile('TIME_STAMP', re.IGNORECASE)
TokenCreator.register_token('TIMESTAMP', TIMESTAMP_RE, TokenCreator.KEYWORD)
# TIME
TIME_RE       = re.compile('TIME', re.IGNORECASE)
TokenCreator.register_token('TIME', TIME_RE, TokenCreator.KEYWORD)
# STALIST
STALIST_RE    = re.compile('STA_LIST', re.IGNORECASE)
TokenCreator.register_token('STALIST', STALIST_RE, TokenCreator.KEYWORD)
# BULL_TYPE
BULLTYPE_RE   = re.compile('BULL_TYPE', re.IGNORECASE)
TokenCreator.register_token('BULLTYPE', BULLTYPE_RE, TokenCreator.KEYWORD)
#MAGTYPE
MAGTYPE_RE    = re.compile('MAG_TYPE', re.IGNORECASE)
TokenCreator.register_token('MAGTYPE', MAGTYPE_RE, TokenCreator.KEYWORD)
#MAGPREFMB
MAGPREFMB_RE    = re.compile('MAGPREF_MB', re.IGNORECASE)
TokenCreator.register_token('MAGPREFMB', MAGPREFMB_RE, TokenCreator.KEYWORD)
#MAGPREFMS
MAGPREFMS_RE    = re.compile('MAGPREF_MS', re.IGNORECASE)
TokenCreator.register_token('MAGPREFMS', MAGPREFMS_RE, TokenCreator.KEYWORD)
# MAG
MAG_RE        = re.compile('MAG', re.IGNORECASE)
TokenCreator.register_token('MAG', MAG_RE, TokenCreator.KEYWORD)
#CHANLIST
CHANLIST_RE   = re.compile('CHAN_LIST', re.IGNORECASE)
TokenCreator.register_token('CHANLIST', CHANLIST_RE, TokenCreator.KEYWORD)
#RELATIVE_TO
RELATIVETO_RE = re.compile('RELATIVE_TO', re.IGNORECASE)
TokenCreator.register_token('RELATIVETO', RELATIVETO_RE, TokenCreator.KEYWORD)
# HELP
HELP_RE       = re.compile('HELP', re.IGNORECASE)
TokenCreator.register_token('HELP', HELP_RE, TokenCreator.KEYWORD)
# PRODID
PRODID_RE     = re.compile('PROD_ID', re.IGNORECASE)
TokenCreator.register_token('PRODID', PRODID_RE, TokenCreator.KEYWORD)
#EVENTLIST
EVENTLIST_RE   = re.compile('EVENT_LIST', re.IGNORECASE)
TokenCreator.register_token('EVENTLIST', EVENTLIST_RE, TokenCreator.KEYWORD)
#ARRIVALLIST
ARRIVALLIST_RE   = re.compile('ARRIVAL_LIST', re.IGNORECASE)
TokenCreator.register_token('ARRIVALLIST', ARRIVALLIST_RE, TokenCreator.KEYWORD)
#GROUPBULLLIST
GROUPBULLLIST_RE   = re.compile('GROUP_BULL_LIST', re.IGNORECASE)
TokenCreator.register_token('GROUPBULLLIST', GROUPBULLLIST_RE, TokenCreator.KEYWORD)
#ORIGINLIST
ORIGINLIST_RE   = re.compile('ORIGIN_LIST', re.IGNORECASE)
TokenCreator.register_token('ORIGINLIST', ORIGINLIST_RE, TokenCreator.KEYWORD)
#BEAMLIST
BEAMLIST_RE   = re.compile('BEAM_LIST', re.IGNORECASE)
TokenCreator.register_token('BEAMLIST', BEAMLIST_RE, TokenCreator.KEYWORD)
#AUXLIST
AUXLIST_RE   = re.compile('AUX_LIST', re.IGNORECASE)
TokenCreator.register_token('AUXLIST', AUXLIST_RE, TokenCreator.KEYWORD)
#COMLIST
COMMLIST_RE   = re.compile('COMM_LIST', re.IGNORECASE)
TokenCreator.register_token('COMMLIST', COMMLIST_RE, TokenCreator.KEYWORD)
#DEPTH_CONF
DEPTHCONF_RE   = re.compile('DEPTH_CONF', re.IGNORECASE)
TokenCreator.register_token('DEPTHCONF', DEPTHCONF_RE, TokenCreator.KEYWORD)
#DEPTH_KVALUE
DEPTHKVALUE_RE   = re.compile('DEPTH_KVALUE', re.IGNORECASE)
TokenCreator.register_token('DEPTHKVALUE', DEPTHKVALUE_RE, TokenCreator.KEYWORD)
#DEPTHTHRESH
DEPTHTHRESH_RE   = re.compile('DEPTH_THRESH', re.IGNORECASE)
TokenCreator.register_token('DEPTHTHRESH', DEPTHTHRESH_RE, TokenCreator.KEYWORD)
#DEPTHMINUSERROR
DEPTHMINUSERROR_RE   = re.compile('DEPTH_MINUS_ERROR', re.IGNORECASE)
TokenCreator.register_token('DEPTHMINUSERROR', DEPTHMINUSERROR_RE, TokenCreator.KEYWORD)
#DEPTH
DEPTH_RE      = re.compile('DEPTH', re.IGNORECASE)
TokenCreator.register_token('DEPTH', DEPTH_RE, TokenCreator.KEYWORD)
#EVENT_STA_DIST
EVENTSTADIST_RE      = re.compile('EVENT_STA_DIST', re.IGNORECASE)
TokenCreator.register_token('EVENTSTADIST', EVENTSTADIST_RE, TokenCreator.KEYWORD)
#MB_MINUS_MS
MBMINUSMS_RE      = re.compile('MB_MINUS_MS', re.IGNORECASE)
TokenCreator.register_token('MBMINUSMS', MBMINUSMS_RE, TokenCreator.KEYWORD)
#MSERR
MSERR_RE      = re.compile('MS_ERR', re.IGNORECASE)
TokenCreator.register_token('MSERR', MSERR_RE, TokenCreator.KEYWORD)
#MINMB
MINMB_RE      = re.compile('MIN_MB', re.IGNORECASE)
TokenCreator.register_token('MINMB', MINMB_RE, TokenCreator.KEYWORD)
#HYDROCPTHRESH
HYDROCPTHRESH_RE      = re.compile('HYDRO_CP_THRESH', re.IGNORECASE)
TokenCreator.register_token('HYDROCPTHRESH', HYDROCPTHRESH_RE, TokenCreator.KEYWORD)
#HYDROTETHRESH
HYDROTETHRESH_RE      = re.compile('HYDRO_TE_THRESH', re.IGNORECASE)
TokenCreator.register_token('HYDROTETHRESH', HYDROTETHRESH_RE, TokenCreator.KEYWORD)
#LOCCONF
LOCCONF_RE            = re.compile('LOC_CONF', re.IGNORECASE)
TokenCreator.register_token('LOCCONF', LOCCONF_RE, TokenCreator.KEYWORD)
#MBERR
MBERR_RE              = re.compile('MB_ERR', re.IGNORECASE)
TokenCreator.register_token('MBERR', MBERR_RE, TokenCreator.KEYWORD)
#MBMSCONF
MBMSCONF_RE           = re.compile('MBMS_CONF', re.IGNORECASE)
TokenCreator.register_token('MBMSCONF', MBMSCONF_RE, TokenCreator.KEYWORD)
#MBMSSLOPE
MBMSSLOPE_RE          = re.compile('MBMS_SLOPE', re.IGNORECASE)
TokenCreator.register_token('MBMSSLOPE', MBMSSLOPE_RE, TokenCreator.KEYWORD)
#MBMSTHRESH
MBMSTHRESH_RE         = re.compile('MBMS_THRESH', re.IGNORECASE)
TokenCreator.register_token('MBMSTHRESH', MBMSTHRESH_RE, TokenCreator.KEYWORD)
#MINDPSNRPP
MINDPSNRPP_RE         = re.compile('MIN_DP_SNR_PP', re.IGNORECASE)
TokenCreator.register_token('MINDPSNRPP', MINDPSNRPP_RE, TokenCreator.KEYWORD)
#MINDPSNRSP
MINDPSNRSP_RE         = re.compile('MIN_DP_SNR_SP', re.IGNORECASE)
TokenCreator.register_token('MINDPSNRSP', MINDPSNRSP_RE, TokenCreator.KEYWORD)
#MINMOVEOUTPP
MINMOUVEOUTPP_RE      = re.compile('MIN_MOUVEOUT_PP', re.IGNORECASE)
TokenCreator.register_token('MINMOUVEOUTPP', MINMOUVEOUTPP_RE, TokenCreator.KEYWORD)
#MINMOVEOUTPP
MINMOUVEOUTSP_RE      = re.compile('MIN_MOUVEOUT_SP', re.IGNORECASE)
TokenCreator.register_token('MINMOUVEOUTSP', MINMOUVEOUTSP_RE , TokenCreator.KEYWORD)
#MINNDEF
MINNDEF_RE             = re.compile('MIN_NDEF', re.IGNORECASE)
TokenCreator.register_token('MINNDEF', MINNDEF_RE , TokenCreator.KEYWORD)
#MINNDPPP
MINNDPPP_RE            = re.compile('MIN_NDP_PP', re.IGNORECASE)
TokenCreator.register_token('MINNDPPP', MINNDPPP_RE , TokenCreator.KEYWORD)
#MINNDEF
MINNDPSP_RE            = re.compile('MIN_NDP_SP', re.IGNORECASE)
TokenCreator.register_token('MINNDPSP', MINNDPSP_RE , TokenCreator.KEYWORD)
#MINNSTAMS
MINNSTAMS_RE            = re.compile('MIN_NSTA_MS', re.IGNORECASE)
TokenCreator.register_token('MINNSTAMS', MINNSTAMS_RE , TokenCreator.KEYWORD)
#MINNSTAMS
MINWDEPTHTHRESH_RE      = re.compile('MIN_WDEPTH_THRESH', re.IGNORECASE)
TokenCreator.register_token('MINWDEPTHTHRESH', MINWDEPTHTHRESH_RE , TokenCreator.KEYWORD)
#REGCONF
REGCONF_RE              = re.compile('REG_CONF', re.IGNORECASE)
TokenCreator.register_token('REGCONF', REGCONF_RE , TokenCreator.KEYWORD)

# ACK to activate/deactivate acknowledgment
ACK_RE                  = re.compile('ACK', re.IGNORECASE)
TokenCreator.register_token('ACK', ACK_RE , TokenCreator.KEYWORD)

#SUBSCRIPTION keywords
FREQ_RE                 = re.compile('FREQ', re.IGNORECASE)
TokenCreator.register_token('FREQ', FREQ_RE, TokenCreator.KEYWORD)

IMMEDIATE_RE            = re.compile('IMMEDIATE', re.IGNORECASE)
TokenCreator.register_token('IMMEDIATE', IMMEDIATE_RE, TokenCreator.KEYWORD)

DAILY_RE            = re.compile('DAILY', re.IGNORECASE)
TokenCreator.register_token('DAILY', DAILY_RE, TokenCreator.KEYWORD)

CUSTOM_RE               = re.compile('CUSTOM', re.IGNORECASE)
TokenCreator.register_token('CUSTOM', CUSTOM_RE, TokenCreator.KEYWORD)

CONTINUOUS_RE           = re.compile('CONTINUOUS', re.IGNORECASE)
TokenCreator.register_token('CONTINUOUS', CONTINUOUS_RE, TokenCreator.KEYWORD)


SEND_EMPTY_RE           = re.compile('SEND_EMPTY', re.IGNORECASE)
TokenCreator.register_token('SENDEMPTY', SEND_EMPTY_RE, TokenCreator.KEYWORD)

SUBSCR_LIST_RE          = re.compile('SUBSCR_LIST', re.IGNORECASE)
TokenCreator.register_token('SUBSCRLIST', SUBSCR_LIST_RE, TokenCreator.KEYWORD)

SUBSCR_NAME_RE          = re.compile('SUBSCR_NAME', re.IGNORECASE)
TokenCreator.register_token('SUBSCRNAME', SUBSCR_NAME_RE, TokenCreator.KEYWORD)

SUBSCR_PROD_RE          = re.compile('SUBSCR_PROD', re.IGNORECASE)
TokenCreator.register_token('SUBSCRPROD', SUBSCR_PROD_RE, TokenCreator.SUBSCRIPTION_COMMAND)

UNSUBSCRIBE_RE          = re.compile('UNSUBSCRIBE', re.IGNORECASE)
TokenCreator.register_token('UNSUBSCRIBE', UNSUBSCRIBE_RE, TokenCreator.SUBSCRIPTION_COMMAND)

SUBSCR_RESEND_RE        = re.compile('SUBSCR_RESEND', re.IGNORECASE)
TokenCreator.register_token('SUBSCR_RESEND', SUBSCR_RESEND_RE, TokenCreator.KEYWORD)

PRODID_LIST_RE          = re.compile('PRODID_LIST', re.IGNORECASE)
TokenCreator.register_token('PRODIDLIST', PRODID_LIST_RE, TokenCreator.KEYWORD)

# Products

# Test products

TESTPRODUCT_RE   = re.compile('TEST_PRODUCT', re.IGNORECASE)
TokenCreator.register_token('TESTPRODUCT', TESTPRODUCT_RE, TokenCreator.TEST_PRODUCT)

# SHI products
#BULLETIN
BULLETIN_RE      = re.compile('BULLETIN', re.IGNORECASE)
TokenCreator.register_token('BULLETIN', BULLETIN_RE, TokenCreator.SHI_PRODUCT)
#WAVEFORM
WAVEFORM_RE      = re.compile('WAVEFORM', re.IGNORECASE)
TokenCreator.register_token('WAVEFORM', WAVEFORM_RE, TokenCreator.SHI_PRODUCT)
#SLSD
SLSD_RE          = re.compile('SLSD', re.IGNORECASE)
TokenCreator.register_token('SLSD', SLSD_RE, TokenCreator.SHI_PRODUCT)
# ARRIVAL
ARRIVAL_RE       = re.compile('ARRIVAL', re.IGNORECASE)
TokenCreator.register_token('ARRIVAL', ARRIVAL_RE, TokenCreator.SHI_PRODUCT)
#STA_STATUS
STASTATUS_RE    = re.compile('STA_STATUS', re.IGNORECASE)
TokenCreator.register_token('STASTATUS', STASTATUS_RE, TokenCreator.SHI_PRODUCT)
#CHAN_STATUS
CHANSTATUS_RE   = re.compile('CHAN_STATUS', re.IGNORECASE)
TokenCreator.register_token('CHANSTATUS', CHANSTATUS_RE, TokenCreator.SHI_PRODUCT)
#CHANNEL
CHANNEL_RE       = re.compile('CHANNEL', re.IGNORECASE)
TokenCreator.register_token('CHANNEL', CHANNEL_RE, TokenCreator.SHI_PRODUCT)
#WAVE_MISSION
WAVEMISSION_RE  = re.compile('WAVE_MISSION', re.IGNORECASE)
TokenCreator.register_token('WAVEMISSION', WAVEMISSION_RE, TokenCreator.SHI_PRODUCT)
#WAVE_QUALITY
WAVEQUALITY_RE  = re.compile('WAVE_QUALITY', re.IGNORECASE)
TokenCreator.register_token('WAVEQUALITY', WAVEQUALITY_RE, TokenCreator.SHI_PRODUCT)
#STATION
STATION_RE       = re.compile('STATION', re.IGNORECASE)
TokenCreator.register_token('STATION', STATION_RE, TokenCreator.SHI_PRODUCT)
#EVENT
EVENT_RE         = re.compile('EVENT', re.IGNORECASE)
TokenCreator.register_token('EVENT', EVENT_RE, TokenCreator.SHI_PRODUCT)
#EXECSUM
EXECSUM_RE       = re.compile('EXECSUM', re.IGNORECASE)
TokenCreator.register_token('EXECSUM', EXECSUM_RE, TokenCreator.SHI_PRODUCT)
#COMMENT
COMMENT_RE       = re.compile('COMMENT', re.IGNORECASE)
TokenCreator.register_token('COMMENT', COMMENT_RE, TokenCreator.SHI_PRODUCT)
#COMM_STATUS
COMMSTATUS_RE    = re.compile('COMM_STATUS', re.IGNORECASE)
TokenCreator.register_token('COMMSTATUS', COMMSTATUS_RE, TokenCreator.SHI_PRODUCT)
#ORIGIN
ORIGIN_RE        = re.compile('ORIGIN', re.IGNORECASE)
TokenCreator.register_token('ORIGIN', ORIGIN_RE, TokenCreator.SHI_PRODUCT)
#OUTAGE
OUTAGE_RE        = re.compile('OUTAGE', re.IGNORECASE)
TokenCreator.register_token('OUTAGE', OUTAGE_RE, TokenCreator.SHI_PRODUCT)
#RESPONSE
RESPONSE_RE      = re.compile('RESPONSE', re.IGNORECASE)
TokenCreator.register_token('RESPONSE', RESPONSE_RE, TokenCreator.SHI_PRODUCT)
#DETBKPHD
DETBKPHD_RE      = re.compile('DETBKPHD', re.IGNORECASE)
TokenCreator.register_token('DETBKPHD', DETBKPHD_RE, TokenCreator.RAD_PRODUCT)
#GASBKPHD
GASBKPHD_RE      = re.compile('GASBKPHD', re.IGNORECASE)
TokenCreator.register_token('GASBKPHD', GASBKPHD_RE, TokenCreator.RAD_PRODUCT)
#BLANKPHD
BLANKPHD_RE      = re.compile('BLANKPHD', re.IGNORECASE)
TokenCreator.register_token('BLANKPHD', BLANKPHD_RE, TokenCreator.RAD_PRODUCT)
#CALIBPHD
CALIBPHD_RE      = re.compile('CALIBPHD', re.IGNORECASE)
TokenCreator.register_token('CALIBPHD', CALIBPHD_RE, TokenCreator.RAD_PRODUCT)
#QCPHD
QCPHD_RE         = re.compile('QCPHD', re.IGNORECASE)
TokenCreator.register_token('QCPHD', QCPHD_RE, TokenCreator.RAD_PRODUCT)
#SPHDP
SPHDP_RE         = re.compile('SPHDP', re.IGNORECASE)
TokenCreator.register_token('SPHDP', SPHDP_RE, TokenCreator.RAD_PRODUCT)
#SPHDF
SPHDF_RE         = re.compile('SPHDF', re.IGNORECASE)
TokenCreator.register_token('SPHDF', SPHDF_RE, TokenCreator.RAD_PRODUCT)
#RLR
RLR_RE           = re.compile('RLR', re.IGNORECASE)
TokenCreator.register_token('RLR', RLR_RE, TokenCreator.RAD_PRODUCT)
#ARR
ARR_RE           = re.compile('ARR', re.IGNORECASE)
TokenCreator.register_token('ARR', ARR_RE, TokenCreator.RAD_PRODUCT)
#ARR
RRR_RE           = re.compile('RRR', re.IGNORECASE)
TokenCreator.register_token('RRR', RRR_RE, TokenCreator.RAD_PRODUCT)
#ALERTFLOW
ALERTFLOW_RE     = re.compile('ALERT_FLOW', re.IGNORECASE)
TokenCreator.register_token('ALERTFLOW', ALERTFLOW_RE, TokenCreator.RAD_PRODUCT)
#ALERT_SYSTEM
ALERTSYSTEM_RE   = re.compile('ALERT_SYSTEM', re.IGNORECASE)
TokenCreator.register_token('ALERTSYSTEM', ALERTSYSTEM_RE, TokenCreator.RAD_PRODUCT)
#ALERT_TEMP
ALERTTEMP_RE     = re.compile('ALERT_TEMP', re.IGNORECASE)
TokenCreator.register_token('ALERTTEMP', ALERTTEMP_RE, TokenCreator.RAD_PRODUCT)
#ALERT_TEMP
ALERTUPS_RE      = re.compile('ALERT_UPS', re.IGNORECASE)
TokenCreator.register_token('ALERTUPS', ALERTUPS_RE, TokenCreator.RAD_PRODUCT)
#MET
MET_RE           = re.compile('MET', re.IGNORECASE)
TokenCreator.register_token('MET', MET_RE, TokenCreator.RAD_PRODUCT)
#DETECTION
DETECTION_RE           = re.compile('DETECTION', re.IGNORECASE)
TokenCreator.register_token('DETECTION', DETECTION_RE, TokenCreator.RAD_PRODUCT)
#RNPS
RNPS_RE          = re.compile('RNPS', re.IGNORECASE)
TokenCreator.register_token('RNPS', RNPS_RE, TokenCreator.RAD_PRODUCT)
#SSREB
SSREB_RE         = re.compile('SSREB', re.IGNORECASE)
TokenCreator.register_token('SSREB', SSREB_RE, TokenCreator.RAD_PRODUCT)
#NETWORK
NETWORK_RE       = re.compile('NETWORK', re.IGNORECASE)
TokenCreator.register_token('NETWORK', NETWORK_RE, TokenCreator.RAD_PRODUCT)
#RMSSOH
RMSSOH_RE        = re.compile('RMSSOH', re.IGNORECASE)
TokenCreator.register_token('RMSSOH', RMSSOH_RE, TokenCreator.RAD_PRODUCT)

#Deprecated ?
#ARMR
ARMR_RE          = re.compile('ARMR', re.IGNORECASE)
TokenCreator.register_token('ARMR', ARMR_RE, TokenCreator.RAD_PRODUCT)
#FPEB
FPEB_RE          = re.compile('FPEB', re.IGNORECASE)
TokenCreator.register_token('FPEB', FPEB_RE, TokenCreator.RAD_PRODUCT)

# the rest in tail
# MSGFORMAT
MSGFORMAT_RE = re.compile(r'[A-Za-z]{3}(\d+\.\d+)')
TokenCreator.register_token('MSGFORMAT', MSGFORMAT_RE, TokenCreator.TAIL)


# EMAIL Address regexpr as defined in RFC 2822 (do not support square brackets and double quotes)
EMAILADDR_RE = re.compile("[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", re.IGNORECASE) # pylint: disable-msg=C0301      
TokenCreator.register_token('EMAILADDR', EMAILADDR_RE, TokenCreator.TAIL)

# NUMBER
#regular expressions for number
HEXNUMBER   = r'0[xX][\da-fA-F]*[lL]?'
#Octal numbers
OCTNUMBER   = r'0[0-7]*[lL]?'
DECNUMBER   = r'[0-9]\d*[lL]?'
INTNUMBER   = group(DECNUMBER, OCTNUMBER, HEXNUMBER)
EXPONENT    = r'[eE][-+]?\d+'
POINTFLOAT  = group(r'\d+\.\d*', r'\.\d+') + maybe(EXPONENT)
EXPFLOAT    = r'\d+' + EXPONENT
FLOATNUMBER = group(POINTFLOAT, EXPFLOAT)
IMAGNUMBER  = group(r'\d+[jJ]', FLOATNUMBER + r'[jJ]')
NUMBER      = group(IMAGNUMBER, FLOATNUMBER, INTNUMBER)

NUMBER_RE = re.compile(NUMBER)
TokenCreator.register_token('NUMBER', NUMBER_RE, TokenCreator.TAIL)

# ID 
ID_RE       = re.compile(r'[\d/\*A-Za-z_\+=\(\)\<\>]([\w]|[\d/=\<\>:\(\)\.@\*\+-])*')
TokenCreator.register_token('ID', ID_RE, TokenCreator.TAIL)

# SEPARATORS
COMMA_RE     = re.compile(r',')
TokenCreator.register_token('COMMA', COMMA_RE, TokenCreator.TAIL)

COLON_RE     = re.compile(r':')
TokenCreator.register_token('COLON', COLON_RE, TokenCreator.TAIL)

MINUS_RE     = re.compile(r'-')
TokenCreator.register_token('MINUS', MINUS_RE, TokenCreator.TAIL)

# NEWLINE Token
NEWLINE_RE = re.compile(r'\n+|(\r\n)+')
TokenCreator.register_token('NEWLINE', NEWLINE_RE, TokenCreator.TAIL)




class Token(object):
    """ Token object returned by the Tokenizer """
    
    def __init__(self, a_type, a_value, a_begin, a_end, a_line_num, a_parsed_line, a_file_pos=-1): #IGNORE:R0913
        """ constructor """
        self._type         = a_type
        self._value        = a_value
        self._begin        = a_begin
        self._end          = a_end
        self._parsed_line  = a_parsed_line
        self._line_num     = a_line_num
        self._file_pos     = a_file_pos
    
    @property
    def type(self):
        """ Return the token type """
        return self._type

    @property
    def value(self):
        """ Return the token value """
        return self._value
    
    @property
    def begin(self):
        """ Return the token begin """
        return self._begin
    
    @property
    def end(self):
        """ Return the token end """
        return self._end

    @property
    def file_pos(self):
        """ Return file_pos """
        return self._file_pos
    
    @property
    def parsed_line(self):
        """ Return the token line """
        return self._parsed_line
    
    @property
    def line_num(self):
        """ return the line number """
        return self._line_num
    
    def __repr__(self):
        return "Token[type=%s,value={%s},line_num=%s,(begin index,end index)=(%s,%s)"\
                % (self._type, self._value, self._line_num, self._begin, self._end)  

class ENDMARKERToken(Token):
    """ A very special Token: ENDMARKER to signal the end of program """
    
    def __init__(self, a_line_num):
        
        super(ENDMARKERToken, self).__init__(TokenCreator.TOKEN_NAMES.ENDMARKER, None, -1, -1, a_line_num, "")

    @property
    def type(self):
        """ Return the token type """
        return self._type

    @property
    def value(self):
        """ Return the token value """
        return self._value
    
    @property
    def begin(self):
        """ Return the token begin """
        return self._begin
    
    @property
    def end(self):
        """ Return the token end """
        return self._end
    
    @property
    def parsed_line(self):
        """ Return the token line """
        return self._parsed_line
    
    def __repr__(self):
        return "ENDMARKER Token line_num = %d"% (self._line_num)  

# Literals to ignore
IGNORED_LITERALS = " \f\t\v\x0c"
#used to distinguish NUMBERs from IDs
CHARS_FOLLOWING_NUMBER = IGNORED_LITERALS + "\n\r" + ","

CHARS_FOLLOWING_KEYWORD = IGNORED_LITERALS + ":\n\r"



class IMSTokenizer(object):
    """ 
       Tokenizer for IMS2.0 messages.
    """
    
    #Class member
    # pattern for MSGID
    MSGID_PATTERN          = r'MSG_ID([ \t])+(?P<msgid>[\d/\*A-Za-z_\+=\(\)\<\>]([\w]|[\d/=\<\>:\(\)\.@\*\+-])*)(([ \t])+(?P<msgsource>[\d/\*A-Za-z_\+=\(\)\<\>]([\w]|[\d/=\<\>:\(\)\.@\*\+-])*))?'  
    MSGID_PATTERN_RE       = re.compile(MSGID_PATTERN, re.IGNORECASE)
    
    MSGFORMAT_PATTERN       = r'BEGIN([ \t])+(?P<msgfmt>[A-Za-z]{3}(\d+\.\d+))'
    MSGFORMAT_PATTERN_RE   = re.compile(MSGFORMAT_PATTERN, re.IGNORECASE)
    
    def __init__(self):
        """ constructor """
        
        self._io_prog        = None
        
        # current parsed line
        self._line_num       = -1
        
        # current position in the line
        self._line_pos       = -1
        
        # file-like offset position
        self._file_pos       = -1
        
        # file-like original position (used for having __iter__ returning always the same sequence)
        self._io_prog_offset = -1
        
        # current token
        self._tok            = None
        
        # internal generator on current stream
        # used by the iterator method
        self._gen            = None
        
        #ref on token creator
        self._tok_c  = TokenCreator
    
    @classmethod
    def get_header_on_error(cls, a_message):
        """ return essential info in case of error
            
            Args:
              a_message: the message to parse
               
            Returns:
               return 
        
            Raises:
               exception 
        """
        res = { 'LANGUAGE' : 'IMSLANGUAGE'}
        
        
        
        # catch all exceptions
        try:
            matched = cls.MSGID_PATTERN_RE.search(a_message)
            if matched:
                msgid = matched.group('msgid')
                res['ID'] = msgid
                
                source = matched.group('msgsource')
            
                if source:
                    res['SOURCE'] = source
                
        except Exception:  # pylint: disable-msg=W0703, W0704
            pass
        
        try:
            matched = cls.MSGFORMAT_PATTERN_RE.search(a_message)
            if matched:
                msgfmt = matched.group('msgfmt')
                res['FORMAT'] = msgfmt
        except Exception:  # pylint: disable-msg=W0703, W0704
            pass
         
       
        return res
        
    def set_io_prog(self, a_io_prog):
        """ 
           Pass the io stream to parse and start reading from where it has been positioned 
           Args:
               a_io_prog: file-like object
        """
        self._io_prog        = a_io_prog
        self._io_prog_offset = a_io_prog.tell()
        self._line_num       = 0
        self._line_pos       = 0
        self._file_pos       = -1
        self._tok            = 0
        # reset generator
        self._gen            = None
    
    def set_file_pos(self, a_file_pos):
        """ 
           Set the starting offset in the read io stream (file).
           Reset the generator as the file positio has changed.
           if a_file_pos is None then do not touch anything
           
           Args:
               a_file_pos: If a_file_pos is None then set file_pos to -1 and the stream will not be touched.
                           The generator will start reading from where it is
        """
        #special case do not touch anything and read from where we are
        self._file_pos = a_file_pos if (a_file_pos != None) else -1
        
    def file_pos(self):
        """ return the position of the reading cursor in current file """
        return self._file_pos
    
    def line_pos(self):
        return self._line_pos
    
    def line_num(self):
        """ return the line_num currently read """
        return self._line_num
        
    def io_prog(self):
        """ return the io prog """
        return self._io_prog  
    
    def _get_id_type(self, a_value): #IGNORE:R0201
        """ get the type for a particular free form ID.
            There are 3 different kinds of IDs: 
            - WCID. WildCard ID. if a_value contains a *.
            - DATA. Data in a data message. If len(a_value) > 50 bytes (or chars) and if a_value contains -
            - ID. All the rest 
        
            Args:
               a_value: the a_value
               
            Returns:
               return the found type (WCID or ID or DATA)
        
            Raises:
               None
        """
        if len(a_value) > 50 or re.search('[:/=+\<\>\(\)]', a_value):
            return 'DATA'
        elif a_value.find('*') >= 0:
            return 'WCID'     
        else:
            return 'ID'
    
    def get_tokenized_string(self, begin, end):
        """
           Return the tokenized string. This is what has been understood so far by the parser
           
           Returns:
              return the tokenized string 
        """
        nb_bytes_to_read = end - begin
        
        bytes_read = 0
        the_string = ""
        
        # position io_prog on begin
        self._io_prog.seek(begin)
        
        while True:
            #read x bytes
            dummy = self._io_prog.read(nb_bytes_to_read)
            
            #get number of bytes read
            bytes_read += len(dummy)
            
            the_string += dummy
            
            # dummy if None or if the number of bytes to read as been reached
            # break to reposition as before
            if not dummy or bytes_read >= nb_bytes_to_read:
                break 
        
        #reposition as before
        self._io_prog.seek(end)
        
        if bytes_read != nb_bytes_to_read:
            BadTokenizedStringError("Cannot read the tokenized string. Should have read %d bytes but effectively read %d bytes" \
                                    % (nb_bytes_to_read, bytes_read))
        
        return the_string
    
    
    def _toBoolean(self, val):
        """ 
        Get the boolean value of the provided input.
    
            If the value is a boolean return the value.
            Otherwise check to see if the value is in 
            ["false", "no", "0"]
            and returns True if value is not in the list
        """

        if val is True or val is False:
            return val
    
        falseItems = ["false", "no", "0"]
    
        return not str( val ).strip().lower() in falseItems
            
        
    def _create_tokenize_gen(self, a_starting_pos=-1):
        """ Use a generator to return an iterator on the tokens stream.
            Calling twice the tokenize method will reset the generator and the 
            position on the read stream. You can position the "cursor" on the
            read stream to the desired offset with a_starting_pos
        
            Args:
               a_starting_pos:Where to position the offset on the read stream.
                              If a_starting_pos is -1, do not touch the current stream
               
            Returns:
               return next found token 
        
            Raises:
               exception LexerError if no specified Token found
        """
        ordered_tokens = self._tok_c.get_ordered_tokens_list()
        tokens_re      = self._tok_c.get_tokens_re()
        
        # position 0 in io stream
        if a_starting_pos != -1:
            self._io_prog.seek(a_starting_pos)
        
        for line in self._io_prog:
           
            self._line_num    += 1
        
            self._file_pos = self._io_prog.tell()
            
            self._line_pos, m_max = 0, len(line)
        
            while self._line_pos < m_max:
            
                b_found = False
                # This code provides some short-circuit code for whitespace, tabs, and other ignored characters
                if line[self._line_pos] in IGNORED_LITERALS:
                    self._line_pos += 1
                    continue
            
                #print("Try to match from [%s]\n"%(line[pos:]))
                        
                for key in ordered_tokens:
                    regexp = tokens_re[key]
                    match  = regexp.match(line, self._line_pos)
                    if match:
                       
                        val        = match.group()
                        start, end = self._line_pos, (self._line_pos+len(val)-1)
                        
                        # when it is an ID check if this is a WCID
                        if key == TokenCreator.TOKEN_NAMES.ID:
                            the_type = self._get_id_type(val)
                        # if it is a number check that there is whitespace character behind otherwise 
                        # this isn't a number
                        # it is an ID
                        elif key in (TokenCreator.TOKEN_NAMES.NUMBER, TokenCreator.TOKEN_NAMES.DATETIME):
                            # check that the end of string has not been reached
                            if end + 1 < m_max:
                                next_c = line[end+1]
                                #next character is a char so it is not a number
                                if next_c not in CHARS_FOLLOWING_NUMBER:
                                    #go to next token type to match
                                    continue
                            #this is a number
                            the_type = key    
                        
                        # convert value to a boolean
                        elif key == TokenCreator.TOKEN_NAMES.BOOLEAN:
                            
                            the_type = key
                            
                            val = self._toBoolean(val)
                            
                        elif TokenCreator.token_has_family(key,[TokenCreator.KEYWORD, TokenCreator.SHI_PRODUCT, \
                                                              TokenCreator.RAD_PRODUCT, TokenCreator.TEST_PRODUCT]): 
                            if end + 1 < m_max:
                                next_c = line[end+1]
                                #next character is a char so it is not a special type
                                if next_c not in CHARS_FOLLOWING_KEYWORD:
                                    #go to next token type to match
                                    continue
                                
                            the_type = key
                        
                        else:
                            the_type = key
                        
                        self._tok = Token(the_type, val, start, end, self._line_num, line,  self._file_pos)
                    
                        #update pos
                        self._line_pos = end + 1
                    
                        #print("Token = %s\n"%(self._tok))
                        b_found = True
                    
                        #return token using yield and generator
                        yield self._tok
                        
                        #found on so quit for loop
                        break
            
            
                if not b_found:
                    raise IllegalCharacterError(line, self._line_num, self._line_pos)            
        
        # All lines have been read return ENDMARKER Token
        self._tok = ENDMARKERToken(self._line_num)
        yield self._tok
        
        
    def __iter__(self):
        """ 
            iterator from the begining of the stream.
            If you call twice this method the second iterator will continue to iterate from 
            where the previous one was and it will not create a new one.
            To create a you one, you have to pass the io_prog again. 
        """
        self._gen = self._create_tokenize_gen(self._file_pos)
        
        return self
        
        
    def next(self):
        """
           Return the next token
            
           Returns:
               return next found token 
        """
        
        # if no generator have been created first do it and call next
        if self._gen == None:
            self._gen = self._create_tokenize_gen(self._file_pos)
        
        return self._gen.next() #pylint: disable-msg=E1103
    
    def consume_next_token(self, a_token_type):
        """
           Consume the next token and check that it is the expected type otherwise send an exception
           
           Args:
               a_token_type:  the token type to consume
            
           Returns:
               return the consumed token 
           
           Raises:
               exception  BadTokenError if a Token Type that is not a_token_type is found
        """
        
        tok = self.next()
        
        if tok.type != a_token_type:
            raise BadTokenError(tok.parsed_line, tok.line_num,  tok.begin, a_token_type, tok)
        else:
            return tok
        
    def consume_while_next_token_in(self, a_token_types_list):
        """
           Consume the next tokens as long as they have one of the passed types.
           This means that at least one token with one of the passed types needs to be matched.
           
           Args:
               a_token_types_list: the token types to consume
            
           Returns:
               return the next non matching token 
        """
        
        self.consume_next_tokens(a_token_types_list)
        
        while True:
        
            tok = self.next()
        
            if tok.type not in a_token_types_list:
                return tok
    
    def consume_while_current_token_in(self, a_token_types_list):
        """
           Consume the tokens starting from the current token as long as they have one of the passed types.
           It is a classical token eater. It eats tokens as long as they are the specified type
           
           Args:
               a_token_types_list: the token types to consume
            
           Returns:
               return the next non matching token 
        """
        
        tok = self.current_token()
        
        while tok.type in a_token_types_list:
            tok = self.next()
        
        return tok
        
        
    
    def consume_next_tokens(self, a_token_types_list):
        """
           Consume the one of the next token types given in the list and check that it is the expected type otherwise send an exception
            
           Args:
               a_tokens_list:  the token types to list 
               
           Returns:
               return next token 
           
           Raises:
               exception  BadTokenError if a Token Type that is not in a_token_types_list is found
        """
        
        tok = self.next()
        
        if tok.type not in a_token_types_list:
            raise BadTokenError(tok.parsed_line, tok.line_num, tok.begin, a_token_types_list, tok)
        else:
            return tok
    
    def advance_until(self, a_tokens_list):
        """ 
            Advance in the stream of tokens until one of the desired tokens is found.
            
            
            Args:
               a_tokens_expression: this is list of possible tokens to match.
                                    the corresponding regular expression is used to try matching the token
              
        
            Returns:
               return the matched token
        """
        # check that the list contains know tokens
        tokens_to_match        = []
        has_to_match_endmarker = False
        # last possible cursor position in the current line
        the_max                = -1
        tokens_re              = self._tok_c.get_tokens_re()
        
        
        for tok in a_tokens_list:
            if tokens_re.has_key(tok):
                # ENDMARKER needs to be differentiated
                if tok == TokenCreator.TOKEN_NAMES.ENDMARKER:
                    has_to_match_endmarker = True
                else:
                    tokens_to_match.append(tok)
            else:
                raise NonExistingTokenError("The token named %s doesn't exist"%(tok))
             
        for line in self._io_prog: 
            self._line_num    += 1
        
            self._line_pos, the_max = 0, len(line)
        
            # This code provides some short-circuit code for whitespace, tabs, and other ignored characters
            if line[self._line_pos] in IGNORED_LITERALS:
                self._line_pos += 1
                continue
            
            #print("Try to match from [%s]\n"%(line[pos:]))
                        
            for key in tokens_to_match:
                regexp = tokens_re[key]
                #here search anywhere in the line for the token
                match  = regexp.search(line, self._line_pos)
               
                if match:
                       
                    val        = match.group()
                    start, end = self._line_pos, (self._line_pos+len(val)-1)
                    
                    # when it is an ID check if this is a WCID
                    if key == TokenCreator.TOKEN_NAMES.ID:
                        the_type = self._get_id_type(val)
                    # if it is a number check that there is whitespace character behind otherwise 
                    # this isn't a number
                    # it is an ID
                    elif key in (TokenCreator.TOKEN_NAMES.NUMBER, TokenCreator.TOKEN_NAMES.DATETIME):
                        # check that the end of string has not been reached
                        if end + 1 < the_max:
                            next_c = line[end+1]
                            #next character is a char so it is not a number
                            if next_c not in CHARS_FOLLOWING_NUMBER:
                                #go to next token type to match
                                continue
                        #this is a number
                        the_type = key    
                    
                    # convert value to a boolean
                    elif key == TokenCreator.TOKEN_NAMES.BOOLEAN:
                        
                        the_type = key
                        
                        val = self._toBoolean(val)
                        
                    elif TokenCreator.token_has_family(key,[TokenCreator.KEYWORD, TokenCreator.SHI_PRODUCT, \
                                                          TokenCreator.RAD_PRODUCT, TokenCreator.TEST_PRODUCT]): 
                        if end + 1 < the_max:
                            next_c = line[end+1]
                            #next character is a char so it is not a special type
                            if next_c not in CHARS_FOLLOWING_KEYWORD:
                                #go to next token type to match
                                continue
                            
                        the_type = key
                    
                    else:
                        the_type = key 
                
                    self._tok = Token(the_type, val, start, end, self._line_num, line)
                    
                    #update pos
                    self._line_pos = end +1
                        
                    # compute file_pos and reposition the cursor to this point in the file
                    # like that the stream starts just after the last found token
                    self._file_pos += self._line_pos
                    self._io_prog.seek(self._file_pos)
                    
                    #return token (no generator)
                    return self._tok
            
            self._file_pos = self._io_prog.tell()
            # not found go to next line
                                
        
        # All lines have been read return ENDMARKER Token
        self._tok = ENDMARKERToken(self._line_num)
        self._line_pos = the_max
        self._file_pos = self._io_prog.tell()
        if has_to_match_endmarker:
            return self._tok
        else:
            raise TokensNotFoundError("Could not find any of the following tokens %s"%(a_tokens_list))  
    
    def current_token(self):
        """ 
            return the latest consumed token.
        
            Returns:
               return the latest consumed token. None if there is no token
        """
        return self._tok
              


        
        
        