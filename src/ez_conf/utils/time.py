'''
Created on Jun 4, 2009

@author: guillaume.aubert@ctbto.org

common functions and object used in the IMS2.0 parsing process

'''
import re
import datetime
import nms_common.utils.time_utils as common_time

IMSDATETIME_PATTERN  = r'(?P<date>(?P<year>(18|19|[2-5][0-9])\d\d)[-/.](?P<month>(0[1-9]|1[012]|[1-9]))[-/.](?P<day>(0[1-9]|[12][0-9]|3[01]|[1-9])))([tT ]?(?P<time>([0-1][0-9]|2[0-3]|[0-9])([:]?([0-5][0-9]|[0-9]))?([:]([0-5][0-9]|[0-9]))?([.]([0-9])+)?))?' # pylint: disable-msg=C0301
IMSDATETIME_RE       = re.compile(IMSDATETIME_PATTERN)

NLDATETIME_PATTERN  = r'(?P<date>(?P<year>(18|19|[2-5][0-9])\d\d)[-/.]?(?P<month>(0[1-9]|1[012]|[1-9]))[-/.]?(?P<day>(0[1-9]|[12][0-9]|3[01]|[1-9])))([tT ]?(?P<time>([0-1][0-9]|2[0-3]|[0-9])([:]?([0-5][0-9]|[0-9]))?([:]([0-5][0-9]|[0-9]))?([.]([0-9])+)?))?' # pylint: disable-msg=C0301
NLDATETIME_RE       = re.compile(NLDATETIME_PATTERN)

class InvalidDateError(Exception):
    """ Invalid IMS Date Error exception """
    def __init__(self, a_msg):
        super(InvalidDateError, self).__init__(a_msg)

def imsdate_to_datetime(a_date_str):
    """ Return datetime from the ims dates
        
        Args: a_date_str : a ims2.0 formatted date string
               
        Returns: a DateTime Object
        
        Raises:
            exception InvalidIMSDateError if this is an unvalid date
    """
    
    matched = IMSDATETIME_RE.match(a_date_str)
        
    if matched:
        
        the_year   = int(matched.group('year'))
        the_month  = int(matched.group('month'))
        the_day    = int(matched.group('day'))
            
        the_time = matched.group('time')
            
        if the_time:
            the_microsec = 0
            
            # if we have milliseconds
            pos = the_time.find('.')
            if pos >= 0:
                fracsec = the_time[pos:]
                the_time = the_time[:pos]
                the_microsec = int(float(fracsec)*1e6)
            else:
                the_microsec = 0
                
            time_list = the_time.split(":")
            if len(time_list) == 1:
                # there is only one value and according the reg expr it has to be an hour
                the_h   = int(time_list[0])
                the_min = 0
                the_sec = 0
            elif len(time_list) == 2:
                #min and hours 
                the_h   = int(time_list[0])
                the_min = int(time_list[1])
                the_sec = 0
            elif len(time_list) == 3:
                #min and hours 
                the_h   = int(time_list[0])
                the_min = int(time_list[1])
                the_sec = int(time_list[2])
            else:
                raise InvalidDateError("The time part of the date %s is not following the IMS2.0 date format" %(a_date_str))
        else:
            the_h        = 0
            the_min      = 0
            the_sec      = 0
            the_microsec = 0
              
        return datetime.datetime(the_year, the_month, the_day,  the_h, the_min, the_sec, the_microsec, tzinfo = common_time.UTC_TZ)
    else:
        raise InvalidDateError("The date %s is not a valid IMS2.0 date (could be out of range :1799<date<6000)" %(a_date_str))

def nldate_to_datetime(a_date_str):
    """ Return datetime from the NL dates
        
        Args: a_date_str : a NL formatted date string
               
        Returns: a DateTime Object
        
        Raises:
            exception InvalidIMSDateError if this is an unvalid date
    """
    
    matched = NLDATETIME_RE.match(a_date_str)
        
    if matched:
        
        the_year   = int(matched.group('year'))
        the_month  = int(matched.group('month'))
        the_day    = int(matched.group('day'))
            
        the_time = matched.group('time')
            
        if the_time:
            the_microsec = 0
            
            # if we have milliseconds
            pos = the_time.find('.')
            if pos >= 0:
                fracsec = the_time[pos:]
                the_time = the_time[:pos]
                the_microsec = int(float(fracsec)*1e6)
            else:
                the_microsec = 0
                
            time_list = the_time.split(":")
            if len(time_list) == 1:
                # there is only one value and according the reg expr it has to be an hour
                the_h   = int(time_list[0])
                the_min = 0
                the_sec = 0
            elif len(time_list) == 2:
                #min and hours 
                the_h   = int(time_list[0])
                the_min = int(time_list[1])
                the_sec = 0
            elif len(time_list) == 3:
                #min and hours 
                the_h   = int(time_list[0])
                the_min = int(time_list[1])
                the_sec = int(time_list[2])
            else:
                raise InvalidDateError("The time part of the date %s is not following the NL date format" %(a_date_str))
        else:
            the_h        = 0
            the_min      = 0
            the_sec      = 0
            the_microsec = 0
              
        return datetime.datetime(the_year, the_month, the_day,  the_h, the_min, the_sec, the_microsec, common_time.UTC_TZ)

    else:
        raise InvalidDateError("The date %s is not a valid NL date" %(a_date_str))
           
           