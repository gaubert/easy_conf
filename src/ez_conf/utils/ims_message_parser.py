'''
Created on May 13, 2009

@author: guillaume.aubert@ctbto.org

'''
from nms_common.parser import exceptions
import StringIO
import copy
import re

import nms_common.parser.common.validator_const as const
from nms_common.parser.exceptions import ParserError
from nms_common.parser.ims20_language.ims_tokenizer import IMSTokenizer, ENDMARKERToken, TokenCreator
from nms_common.parser.ims20_language.ims_semantic_validator import RequestSemanticValidator,\
    SubscriptionSemanticValidator
from nms_production_engine_api import product_dict_const
import nms_common.parser.ims20_language.ims_tokenizer as ims_tokenizer
from nms_common.utils.logging_utils import LoggerFactory



# pylint: disable-msg=R0201

class ParsingError(ParserError):
    """Syntax Parsing Errors"""
    
    c_STANDARD_ERROR_MSG = "Next keyword should be %s but instead was '%s' (keyword type %s)"
    
    @classmethod
    def create_std_error_msg(cls, a_user_friendly_keyword, a_token):
        """ 
           Create the standard Error message.
           
           Args:
               message: the message to parse
               
            Returns:
               return 
        
            Raises:
               exception
           
        """
        return cls.c_STANDARD_ERROR_MSG % (a_user_friendly_keyword, a_token.value, a_token.type)
    
    def __init__(self, a_msg, a_suggestion, a_token):
        
        self._token      = a_token
        
        msg = a_msg
        
        if a_token != None:
            # manage the endmarker case if token.begin = -1
            msg = exceptions.PARSER_ERROR_MESSAGE % \
                    (self._token.line_num, self._token.begin if (self._token.begin != -1) else 'EOF', a_msg)
            
        super(ParsingError, self).__init__(msg, a_token.parsed_line, \
                               a_token.line_num, a_token.begin, \
                               a_suggestion)
    
    @property
    def instrumented_line(self):
        """ return the line with a cursor on the error """
        instrumented_line  = self._line[:self._pos] + "[ERR]=>" + self._line[self._pos:] 
        return instrumented_line   

class IMSParser(object):
    """ create tokens for parsing the grammar. 
        This class is a wrapper around the python tokenizer adapt to the DSL that is going to be used.
    """
    
    # Class members
    TOKEN_NAMES   = TokenCreator.TOKEN_NAMES
    
    c_SHI_PRODUCTS  = TokenCreator.get_tokens_with_type(TokenCreator.SHI_PRODUCT)
   
    c_TEST_PRODUCTS = TokenCreator.get_tokens_with_type(TokenCreator.TEST_PRODUCT)
   
    # rad products + Help
    c_RAD_PRODUCTS = TokenCreator.get_tokens_with_type(TokenCreator.RAD_PRODUCT) + [TOKEN_NAMES.HELP]
    
    #List of all type of products
    c_ALL_PRODUCTS = c_SHI_PRODUCTS + c_RAD_PRODUCTS + c_TEST_PRODUCTS
    
    #Commands detection
    c_SUBSCR_COMMANDS = [TOKEN_NAMES.UNSUBSCRIBE, TOKEN_NAMES.SUBSCRPROD]
    c_ALL_COMMANDS = c_SUBSCR_COMMANDS
    
    # all this keywords expect a simple number param
    c_SIMPLE_NUMBER_PARAMS = [TOKEN_NAMES.DEPTHCONF, TOKEN_NAMES.DEPTHTHRESH, TOKEN_NAMES.DEPTHKVALUE, \
                              TOKEN_NAMES.HYDROCPTHRESH, TOKEN_NAMES.HYDROTETHRESH, TOKEN_NAMES.LOCCONF, \
                              TOKEN_NAMES.MBERR, TOKEN_NAMES.MBMSCONF, TOKEN_NAMES.MBMSSLOPE, \
                              TOKEN_NAMES.MBMSTHRESH, TOKEN_NAMES.MINDPSNRPP ,TOKEN_NAMES.MINDPSNRSP, \
                              TOKEN_NAMES.MINMB, TOKEN_NAMES.MINMOUVEOUTPP, TOKEN_NAMES.MINMOUVEOUTSP, \
                              TOKEN_NAMES.MINNDEF, TOKEN_NAMES.MINNDPPP, TOKEN_NAMES.MINNDPSP, \
                              TOKEN_NAMES.MINNSTAMS,TOKEN_NAMES.MINWDEPTHTHRESH, TOKEN_NAMES.MSERR, \
                              TOKEN_NAMES.REGCONF]
    
    # all this keyword expect a list of ID or number
    c_LIST_PARAMS         = [TOKEN_NAMES.STALIST, TOKEN_NAMES.CHANLIST, TOKEN_NAMES.EVENTLIST, \
                             TOKEN_NAMES.ARRIVALLIST, TOKEN_NAMES.BEAMLIST, TOKEN_NAMES.AUXLIST,\
                             TOKEN_NAMES.COMMLIST, TOKEN_NAMES.GROUPBULLLIST, TOKEN_NAMES.ORIGINLIST, \
                             TOKEN_NAMES.MAGTYPE,
                             #Subscrition
                             TOKEN_NAMES.SUBSCRLIST, TOKEN_NAMES.PRODIDLIST,
                             ]
    
    #regexp to guess if it is an IMS2.0 language
    IMS20_GUESS      = '(?P<begin>BEGIN)|(?P<end>STOP)|(?P<msgtype>MSG_TYPE)|(?P<msgid>MSG_ID)'
    IMS20_GUESS_RE   = re.compile(IMS20_GUESS, re.IGNORECASE)    
                
    
    def __init__(self):
        """ constructor """
        
        self._tokenizer = IMSTokenizer()
        
        # io stream
        self._io_prog   = None
        
        self.__log__ = LoggerFactory.get_logger(self)

        self._request_semantic_validator = RequestSemanticValidator()
        
        self._subscription_semantic_validor = SubscriptionSemanticValidator()

        
    def get_message_type(self, a_message):
        """Extract the message type : subscription or request"""
        message_type = None
        if self.is_parsable(a_message):
            for line in a_message.split('\n'):
                msg_type_token  = ims_tokenizer.MSGTYPE_RE.search(line)
                if msg_type_token is not None:
                    message_type_match = ims_tokenizer.ID_RE.search(line.strip()[len(msg_type_token.group()):])
                    message_type = message_type_match.group()
                    break;
            if message_type is None:
                raise ParserError("No message type in the IMS2.0 message %s" % a_message)
        else:
            raise ParserError("Message is not an IMS2.0 message %s" % a_message)
        return message_type
        
    def is_parsable(self, a_message):
        """ GUESS it is a IMS2.0 request message or not.
            
            Args:
              a_message: a string message to parse
               
            Returns:
               return 
        
            Raises:
               exception 
        """ 
        io_msg           = StringIO.StringIO(a_message)
        
        #confidence number
        conf_nb = 0
        
        #for the moment give the same confidence to all matched element
        # in the future we could different each keyword
        for line in io_msg:
            matched          = self.__class__.IMS20_GUESS_RE.search(line)
            if matched:
                conf_nb += 100
        
        #need at least two keywords
        return True if conf_nb >= 200 else False
    
    def get_header_on_error(self, a_message):
        """ return essential info in case of error
            
            Args:
              a_message: the message to parse
               
            Returns:
               return 
        
            Raises:
               exception 
        """
        return IMSTokenizer.get_header_on_error(a_message)
            
    
    def parse_str(self, message):
        """ parsed the passed message.
        
            Args:
               message: a string message to parse
               
            Returns:
               return 
        
            Raises:
               exception 
        """ 
        # For the moment the message is always a string
        io_prog = StringIO.StringIO(message)
         
        self._tokenizer.set_io_prog(io_prog)
        
        return self._parse()

    @classmethod
    def create_printable_prod_dict(cls, a_product_list):
        """ 
           create a readable and understandable productlist.
           This is maint to be printed on the user trace
        """
        
        res = ""
        cpt = 1
        
        
        for prod_dict in a_product_list:
            
            if cpt == 1:
                res += "[Product %d]\n" % (cpt)
            else:
                res += "\n[Product %d]\n" % (cpt)
            
            keys = copy.deepcopy(prod_dict.keys())
            
            product_classification_keys = [const.TECHNOLOGYFAMILY, const.TECHNOLOGYTYPE, const.PRODUCTFAMILY, const.PRODUCTTYPE] 
            product_classification_t    = " == Product Classification:\n   - Techno Fam   : %s,\n"\
                                          + "   - Techno Type  : %s,\n   - Product Fam  : %s,\n   - Product Type : %s,\n"
            
            
            
            #remove mandatory classification keys
            for key in product_classification_keys:
                keys.remove(key)
            
            product_classification = product_classification_t % (prod_dict[const.TECHNOLOGYFAMILY],
                                                                 prod_dict[const.TECHNOLOGYTYPE], 
                                                                 prod_dict[const.PRODUCTFAMILY],
                                                                 prod_dict[const.PRODUCTTYPE])
              
            # add FILTER if there is one
            if const.FILTER in keys:
                product_classification += "   - Filter  : %s,\n" % (prod_dict[const.FILTER])
                keys.remove(const.FILTER)
    
            res += product_classification
            
            product_constraints = "\n == Product Constraints:\n"
            
            #left keys are constraints
            for key in keys:
                val = prod_dict[key]
                
                # special case dates to convert them in a readable format
                if key == const.DATE_K:
                    product_constraints += "   - %s  : { 'START': %s, 'END' : %s }\n" % (key, val['START'], val['END'])
                else:  
                    product_constraints += "   - %s  : %s,\n" % (key, val)
            
            res += product_constraints
            
            cpt += 1
        
        return res
    
    def parse(self, io_stream):
        """ parsed an io_stream object.
        
            Args:
               io_stream: an io stream (file, or StringIO)
               
            Returns:
               A tuple (understood request, request dictionary)
        
            Raises:
               exception 
        """ 
        self._tokenizer.set_io_prog(io_stream)
        
        
        begin = self._tokenizer._io_prog_offset
        end   = self._tokenizer._file_pos
        
        return (self._tokenizer.get_tokenized_string(begin, end), self._parse())
      
    def parse_and_validate(self, io_stream):  
        """ tokenize, parsed and validate an io_stream object.
        
            Args:
               message: a message string
               
            Returns:
               return a tuple (understood request, 
        
            Raises:
               exception 
        """
        self._tokenizer.set_io_prog(io_stream)
        parse_dict = self._parse()
        
        if parse_dict['MSGINFO']['TYPE'] == 'subscription':
            result = self._subscription_semantic_validor.check_request(parse_dict)
        elif parse_dict['MSGINFO']['TYPE'] == 'request':
            result = self._request_semantic_validator.check_request(parse_dict)
        else:
            raise ParsingError("User request type not supported : %s" % parse_dict['MSGINFO']['TYPE'])
        
        self.__log__.info("IMS 2.0 request successfully parsed")
        
        begin = self._tokenizer._io_prog_offset
        end   = self._tokenizer._file_pos
        
        return (self._tokenizer.get_tokenized_string(begin, end), result)

    def parse_and_validate_str(self, a_message):  
        """ tokenize, parsed and validate an io_stream object.
        
            Args:
               io_stream: an io stream (file, or StringIO)
               
            Returns:
               A tuple (understood request, request dictionary)
        
            Raises:
               exception 
        """
        io_prog = StringIO.StringIO(a_message)
        
        return self.parse_and_validate(io_prog) 
        
    
    def _parse(self):
        """ private parsing method .
        
            Args:
               program: the program to parse
               
            Returns:
               The request dictionary 
        
            Raises:
               exception 
        """
        result_dict = self._parse_header_message()
        
        # 3 choices from there: data, request or subscription message
        req_type = result_dict['MSGINFO']['TYPE']
        
        if   req_type == 'request':
            result_dict.update(self._parse_request_message())
        elif req_type == 'subscription':
            result_dict.update(self._parse_subscription_message())
        elif req_type == 'data':
            result_dict.update(self._parse_data_message())
        else:
            raise ParsingError("unknown request type %s. contact the NMS administrator.\n"\
                               % (req_type), None, self._tokenizer.current_token())
        
        return result_dict
    
    def _parse_header_message(self): # pylint: disable-msg=R0912  
        """ Read the 4 first lines that are considered as the "header of the message".
            This will help finding the message type
        
            Args: None
               
            Returns:
               return a dictionary of parsed values 
        
            Raises:
               exception 
        """
        result = {
                   'MSGINFO'    : { 'LANGUAGE' : 'IMSLANGUAGE'},
                   'ACK'        : True, #ACK default value in IMS Language
                   'TARGETINFO' : {},
                 }
        
        # might need to advance until a BEGIN token
        # for the moment check if the first token is a begin
        token = self._tokenizer.next()
        
        # look for line 1 BEGIN message_format
        # format: begin message_format
        if token.type != IMSParser.TOKEN_NAMES.BEGIN:
            raise ParsingError(ParsingError.create_std_error_msg('a begin', token), \
                               'The begin line is missing or not well formatted', token)
    
        token = self._tokenizer.next()
        
        # look for a message_format
        if token.type != IMSParser.TOKEN_NAMES.MSGFORMAT:
            raise ParsingError(ParsingError.create_std_error_msg('a msg format id (ex:ims2.0)', token), \
                               'The begin line is not well formatted', token)
            
        result['MSGINFO']['FORMAT'] = token.value.lower()
        
        #eat next line characters
        token = self._tokenizer.consume_while_next_token_in([IMSParser.TOKEN_NAMES.NEWLINE])
        
        # line 2: get the message type
        # format: msg_type request
        if token.type != IMSParser.TOKEN_NAMES.MSGTYPE:
            raise ParsingError(ParsingError.create_std_error_msg('a msg_type', token), \
                               'The msg_type id line is missing', token)
            
        token = self._tokenizer.next()
        
        if token.type != IMSParser.TOKEN_NAMES.ID:
            raise ParsingError(ParsingError.create_std_error_msg('a id', token), \
                               'The msg_type id is missing or the msg_type line is mal-formated', token)
        
        result['MSGINFO']['TYPE'] = token.value.lower()
         
        #eat next line characters
        token = self._tokenizer.consume_while_next_token_in([IMSParser.TOKEN_NAMES.NEWLINE])
        
        # line 3: get the message id
        # format: msg_id id_string [source]
        if token.type != IMSParser.TOKEN_NAMES.MSGID:
            raise ParsingError(ParsingError.create_std_error_msg('a msg_id', token), \
                               'The msg_id line is missing', token)
            
        token = self._tokenizer.next()
        
        # next token is an ID 
        if token.type not in (IMSParser.TOKEN_NAMES.ID, IMSParser.TOKEN_NAMES.NUMBER, \
                              IMSParser.TOKEN_NAMES.EMAILADDR, IMSParser.TOKEN_NAMES.DATETIME, \
                              IMSParser.TOKEN_NAMES.DATA):
            raise ParsingError(ParsingError.create_std_error_msg('an id', token), \
                               'The msg_id line is missing the id or is not well formatted', token)
            
        result['MSGINFO']['ID'] = token.value
        
        token = self._tokenizer.next()
        
        # it can be a source or a NEWLINE
        
        # this is a source and source format 3-letter country code followed by _ndc (ex: any_ndc)
        if token.type in (IMSParser.TOKEN_NAMES.ID, IMSParser.TOKEN_NAMES.EMAILADDR, \
                          IMSParser.TOKEN_NAMES.DATETIME, IMSParser.TOKEN_NAMES.DATA, \
                          IMSParser.TOKEN_NAMES.NUMBER):
            result['MSGINFO']['SOURCE'] = token.value 
            
            # go to next token
            self._tokenizer.next()
                     
        elif token.type != IMSParser.TOKEN_NAMES.NEWLINE:
            raise ParsingError(ParsingError.create_std_error_msg('a newline or a source', token), \
                               'The msg_id line is not well formatted', token)
        
        #eat current and next line characters
        token = self._tokenizer.consume_while_current_token_in([IMSParser.TOKEN_NAMES.NEWLINE])
        
        #optional it could now be the optional REF_ID
        if token.type == IMSParser.TOKEN_NAMES.REFID:
            result['MSGINFO']['REFID'] = self._parse_ref_id_line()
            token = self._tokenizer.current_token()
        
        #optional PRODID. 
        if token.type == IMSParser.TOKEN_NAMES.PRODID:
            result['MSGINFO']['PRODID'] = self._parse_prod_id_line()
            token = self._tokenizer.current_token()
        
        # optional line APPLICATION (always after REFID and PRODID)
        if token.type == IMSParser.TOKEN_NAMES.APPLICATION:
            
            # next token should be a ID (Bulletin type)
            token = self._tokenizer.next()
                
            if token.type not in (IMSParser.TOKEN_NAMES.ID, IMSParser.TOKEN_NAMES.NUMBER) :
                raise ParsingError(ParsingError.create_std_error_msg('an id or a number', token), \
                                   'The Application name is not what was expected', token)

            result['MSGINFO']['APPLICATION'] = token.value
            
            #eat next line characters
            token = self._tokenizer.consume_while_next_token_in([IMSParser.TOKEN_NAMES.NEWLINE])
            
            
        # line 4 or 5: e-mail foo.bar@domain_name
        # look for an EMAIL keyword
        # this is optional if there is no TARGET then use the sender email as target
        if token.type in  (IMSParser.TOKEN_NAMES.EMAIL, IMSParser.TOKEN_NAMES.FTP) :
            result['TARGETINFO']['TYPE'] = token.type
            
            token = self._tokenizer.next()
            # look for the EMAILADDR
            if token.type != IMSParser.TOKEN_NAMES.EMAILADDR: 
                raise ParsingError(ParsingError.create_std_error_msg('an email address', token), \
                     
                                   'The email address might be missing or is malformated', token)
            
            #create DATA dir and fill in values
            result['TARGETINFO']['DATA']              = { }
            
            result['TARGETINFO']['DATA']['EMAILADDR'] = token.value.lower()
            
            #eat next line characters
            token = self._tokenizer.consume_while_next_token_in([IMSParser.TOKEN_NAMES.NEWLINE])
        
        # optional ACK to activate or deactivate acknowlegdment
        if token.type  == IMSParser.TOKEN_NAMES.ACK:
            
            token = self._tokenizer.next()
            
            result['ACK'] = token.value
            
            #eat next line characters
            self._tokenizer.consume_while_next_token_in([IMSParser.TOKEN_NAMES.NEWLINE])
        
        return result
    
    def _parse_prod_id_line(self):
        """ Parse a prod_id line
        
            Args: None
               
            Returns:
               return a dictionary of pased values 
        
            Raises:
               exception 
        """ 
        result_dict = {}
        
        token = self._tokenizer.next()
        
        if token.type not in (IMSParser.TOKEN_NAMES.NUMBER):
            raise ParsingError(ParsingError.create_std_error_msg('a number', token), \
                               'The prod_id line is missing a product_id or it is not well formatted', token)
         
        result_dict['PRODID'] = token.value
        
        token = self._tokenizer.next()
        
        if token.type not in (IMSParser.TOKEN_NAMES.NUMBER):
            raise ParsingError(ParsingError.create_std_error_msg('a number', token), \
                               'The prod_id line is missing a delivery_id or it is not well formatted', token)
         
        result_dict['DELIVERYID'] = token.value
        
        #eat current and next line characters
        self._tokenizer.consume_while_next_token_in([IMSParser.TOKEN_NAMES.NEWLINE])
        
        return result_dict

    def _parse_ref_id_line(self):
        """ Parse a ref_id line
        
            Args: None
               
            Returns:
               return a dictionary of pased values 
        
            Raises:
               exception 
        """ 
        result_dict = {}
        
        token = self._tokenizer.next()
        
        if token.type not in (IMSParser.TOKEN_NAMES.ID, IMSParser.TOKEN_NAMES.NUMBER):
            raise ParsingError(ParsingError.create_std_error_msg('an id', token), \
                               'The ref_id line is missing a ref_src or it is not well formatted', token)
         
        result_dict['REFSTR'] = token.value
        
        token = self._tokenizer.next()
        
        # could be the optional ref_src
        if token.type in (IMSParser.TOKEN_NAMES.ID, IMSParser.TOKEN_NAMES.NUMBER):
            result_dict['REFSRC'] = token.value
            token = self._tokenizer.next()
        
        # now the [part seq_num [of tot_num]]
        if token.type == IMSParser.TOKEN_NAMES.PART:
            
            #get the seq num val
            token = self._tokenizer.next()
            
            if token.type not in (IMSParser.TOKEN_NAMES.ID, IMSParser.TOKEN_NAMES.NUMBER):
                raise ParsingError(ParsingError.create_std_error_msg('an id', token), \
                                   "The ref_id line is missing a the seq_num in the \'part\'"+\
                                   " construct: ref_id ref_str [ref_src] [part seq_num [of tot_num]]", \
                                   token)
            
            result_dict['SEQNUM'] = token.value
            
            # look for OF token
            token = self._tokenizer.next()
            
            if token.type == IMSParser.TOKEN_NAMES.OF:
                
                # get the tot_num val
                token = self._tokenizer.next()
                
                if token.type not in (IMSParser.TOKEN_NAMES.ID, IMSParser.TOKEN_NAMES.NUMBER):
                    raise ParsingError(ParsingError.create_std_error_msg('an id', token), \
                                       "The ref_id line is missing a the tot_num in the \'of\'"+\
                                       " construct: ref_id ref_str [ref_src] [part seq_num [of tot_num]]", \
                                       token)
            
                result_dict['TOTNUM'] = token.value
                
                #go to next
                token = self._tokenizer.next()
        # it can then only be a new line
        elif token.type != IMSParser.TOKEN_NAMES.NEWLINE:
            raise ParsingError(ParsingError.create_std_error_msg('an id, a part or a new line ', token), \
                               "The ref_id line is mal formatted."+\
                               " It should follow ref_id ref_str [ref_src] [part seq_num [of tot_num]]",\
                                token)
             
        #eat current and next line characters
        self._tokenizer.consume_while_current_token_in([IMSParser.TOKEN_NAMES.NEWLINE])
        
        return result_dict
    
    def _parse_request_message(self): # pylint: disable-msg=R0912,R0915  
        """ Parse Radionuclide and SHI request messages
        
            Args: None
               
            Returns:
               return a dictionary of pased values 
        
            Raises:
               exception 
        """ 
        result_list = []
        product_list_dict = {product_dict_const.PRODUCTLIST: result_list}
        product     = {}
        
        token = self._tokenizer.current_token()
        
        # For the moment look for the different possible tokens
        while token.type != IMSParser.TOKEN_NAMES.STOP and token.type != IMSParser.TOKEN_NAMES.ENDMARKER:
            # if it is a new product
            if token.type in IMSParser.c_ALL_PRODUCTS:

                product.update(self._parse_complex_product(token))
            
                # add create product dict in result list
                result_list.append(product)
                
                # create a new product from the previous one
                # it will only be added if we have a new product type
                # Used to override parameters between products
                product = copy.deepcopy(product)
            
            # time keyword
            elif token.type == IMSParser.TOKEN_NAMES.TIME:
               
                product['DATE'] = self._parse_time()
                   
            # bull_type 
            # they both expect an ID
            elif token.type in (IMSParser.TOKEN_NAMES.BULLTYPE,\
                                IMSParser.TOKEN_NAMES.MAGPREFMB, \
                                IMSParser.TOKEN_NAMES.MAGPREFMS):
                
                t_type = token.type
                
                # next token should be a ID (Bulletin type)
                token = self._tokenizer.next()
                
                if token.type != IMSParser.TOKEN_NAMES.ID:
                    raise ParsingError(ParsingError.create_std_error_msg('a id', token), \
                                       'The bull_type id qualifying type of bulletin requested is missing', token)

                product[t_type] = token.value
                
                self._tokenizer.consume_while_next_token_in([IMSParser.TOKEN_NAMES.NEWLINE])
            #RELATIVE_TO origin | event | bulletin or ID
            elif token.type == IMSParser.TOKEN_NAMES.RELATIVETO:
               
                # next token should be a ID (Bulletin type)
                token = self._tokenizer.consume_next_tokens([IMSParser.TOKEN_NAMES.ORIGIN, \
                                                             IMSParser.TOKEN_NAMES.EVENT, \
                                                             IMSParser.TOKEN_NAMES.BULLETIN, \
                                                             IMSParser.TOKEN_NAMES.ID])
                
                product[IMSParser.TOKEN_NAMES.RELATIVETO] = token.value

                self._tokenizer.consume_while_next_token_in([IMSParser.TOKEN_NAMES.NEWLINE])   
                                 
            # mag , depth, eventstadist, depthminuserror mbminusms keyword
            elif token.type in (IMSParser.TOKEN_NAMES.MAG, IMSParser.TOKEN_NAMES.DEPTH,\
                                IMSParser.TOKEN_NAMES.EVENTSTADIST, IMSParser.TOKEN_NAMES.DEPTHMINUSERROR,\
                                IMSParser.TOKEN_NAMES.MBMINUSMS):
               
                product[token.type] = self._parse_range(token) 
                
            #LAT or LON
            elif token.type in (IMSParser.TOKEN_NAMES.LAT,IMSParser.TOKEN_NAMES.LON):
                
                product[token.type] = self._parse_latlon(token.type)
                
            elif token.type in IMSParser.c_LIST_PARAMS:
                                
                product.update(self._parse_list(token))
            #DEPTHCONF, DEPTHKVALUE, DEPTHTHRESHOLD
            elif token.type in IMSParser.c_SIMPLE_NUMBER_PARAMS:
                
                t_type = token.type
                 
                # next token should be a number (depth conf)
                token = self._tokenizer.next()
                
                if token.type != IMSParser.TOKEN_NAMES.NUMBER:
                    raise ParsingError(ParsingError.create_std_error_msg('a number', token), \
                                       'The depth paramter (conf, kvalue or threshold) number is missing', token)

                product[t_type] = token.value
                
                self._tokenizer.consume_while_next_token_in([IMSParser.TOKEN_NAMES.NEWLINE])
            #TIMESTAMP peculiarity
            elif token.type == IMSParser.TOKEN_NAMES.TIMESTAMP:
                
                product['TIMESTAMP'] = True  
                 
                # go to the next token
                token = self._tokenizer.next()
                                      
            else:
                raise ParsingError('Unknown or misplaced keyword "%s" (keyword type %s)' % (token.value, token.type), \
                                   'Request mal-formatted', token)

            # eat any left NEWLINE token
            token = self._tokenizer.consume_while_current_token_in([IMSParser.TOKEN_NAMES.NEWLINE])
            
        # check if we have a stop
        if token.type != IMSParser.TOKEN_NAMES.STOP:
            raise ParsingError('End of request reached without encountering a stop keyword', \
                               'Stop keyword missing or truncated request', token)
        
        return product_list_dict
    
    def _parse_list(self, a_token):
        """ Parse a station list or a channel list.
            l = a,b,c,d
        
            Args: a_token: The token that defines the type (STALIST or CHANLIST)
               
            Returns:
               return a dictionary of parsed values 
        
            Raises:
               exception 
        """ 
        res_dict = {}
        
        tok_type  = a_token.type
         
        lst = []
        
        while True:
            
            token = self._tokenizer.next() 
        
            #should find an ID
            if token.type in (IMSParser.TOKEN_NAMES.ID, IMSParser.TOKEN_NAMES.WCID, IMSParser.TOKEN_NAMES.NUMBER):
            
                lst.append(token.value)
                
                # should find a COMMA or NEWLINE
                # IF COMMA loop again else leave loop
                token = self._tokenizer.consume_next_tokens([IMSParser.TOKEN_NAMES.COMMA, \
                                                             IMSParser.TOKEN_NAMES.NEWLINE])
                
                if token.type == IMSParser.TOKEN_NAMES.NEWLINE:
                    #leave the loop
                    break
            else:
                raise ParsingError(ParsingError.create_std_error_msg('a list id', token), \
                                   'The list line is not well formatted', token)
  
        # if goes here then there is something in stations
        res_dict[tok_type] = lst
        
        return res_dict  
               
    def _parse_complex_product(self, a_token):
        """ Parse complex products either SHI or Radionuclide
            Args: a_token: token
               
            Returns:
               return a dictionary of pased values 
        
            Raises:
               exception 
        """
        res_dict = {}
        
        # get product type
        res_dict['TYPE'] = a_token.type
        
        token = self._tokenizer.next()
        
        if token.type == IMSParser.TOKEN_NAMES.NEWLINE:
            return res_dict
        
        # first try to consume the SUBTYPE if there is any
        # in that case, there is a subtype (only for SLSD and arrivals)
        elif token.type == IMSParser.TOKEN_NAMES.COLON:
            
            token = self._tokenizer.consume_next_token(IMSParser.TOKEN_NAMES.ID)
            res_dict['SUBTYPE'] = token.value
            
            # go to next token
            token = self._tokenizer.next()
                    
        #if we have a new line our job is over 
        if token.type == IMSParser.TOKEN_NAMES.NEWLINE:
            return res_dict
        
        if token.type == IMSParser.TOKEN_NAMES.MSGFORMAT:
            res_dict['FORMAT'] = token.value
            
            #get the next token
            token = self._tokenizer.next()
            
            # if this is a COLON then there is a subformat
            if token.type == IMSParser.TOKEN_NAMES.COLON:
                token = self._tokenizer.next()
                if token.type == IMSParser.TOKEN_NAMES.ID:
                    
                    res_dict['SUBFORMAT'] = token.value
                    
                    #consume next NEWLINE token
                    self._tokenizer.consume_next_token(IMSParser.TOKEN_NAMES.NEWLINE)
                else:
                    raise ParsingError(ParsingError.create_std_error_msg('a subformat value', token), \
                                       'The line [product_type format[:subformat]] (ex:waveform ims2.0:cm6)' +\
                                       ' is incorrect', token)
            # to accept format subformat (format space subformat)
            elif token.type == IMSParser.TOKEN_NAMES.ID:
                res_dict['SUBFORMAT'] = token.value
                #consume next NEWLINE token
                self._tokenizer.consume_next_token(IMSParser.TOKEN_NAMES.NEWLINE)  
            # it could be a NEWLINE and there is no subformat
            elif token.type != IMSParser.TOKEN_NAMES.NEWLINE:
                raise ParsingError(ParsingError.create_std_error_msg('a subformat value or a new line', token), \
                                   'The subformat or format part of the line [product_type format:[subformat]]'+\
                                   ' (ex:waveform ims2.0:cm6) is not well formatted', token)
        else:
            raise ParsingError(ParsingError.create_std_error_msg('a newline or a msg format (ex:ims2.0)', token), \
                               'The line [product_type format[:subformat]] (ex:waveform ims2.0:cm6)'+\
                               ' is incorrect', token)
            
        return res_dict  
    
    def _parse_range(self, a_token):
        """ parse a range of values.
            range keyword [min] to [max]
        
            Args: a_token: The token that defines the type 
        """
        res_dict = {}
        
        tok_type = a_token.type
        
        token = self._tokenizer.next() 
        
        if token.type == IMSParser.TOKEN_NAMES.NUMBER:  
            
            res_dict['START'] = token.value
            
            # try to consume the next token that should be TO
            self._tokenizer.consume_next_token(IMSParser.TOKEN_NAMES.TO)
        
        elif token.type == IMSParser.TOKEN_NAMES.TO:
            # add the  value because begin value has been omitted
            res_dict['START'] = IMSParser.TOKEN_NAMES.MIN 
        else:
            raise ParsingError(ParsingError.create_std_error_msg('a number or to', token), \
                               'The %s line is not well formatted'% (tok_type), token)
            
        token = self._tokenizer.next()
        
        # it can be either NUMBER (ENDMAG) or NEWLINE (this means that it will magnitude max)
        if token.type == IMSParser.TOKEN_NAMES.NUMBER:
            res_dict['END'] = token.value
            
            #consume new line
            self._tokenizer.consume_next_token(IMSParser.TOKEN_NAMES.NEWLINE)
            
        elif token.type == IMSParser.TOKEN_NAMES.NEWLINE:
            res_dict['END'] = IMSParser.TOKEN_NAMES.MAX 
        else:
            raise ParsingError(ParsingError.create_std_error_msg('a number or newline', token), \
                               'The %s line is not well formatted'% (tok_type), token)
        
        #go to next token
        self._tokenizer.next()
       
        return res_dict    
        
    def _parse_latlon(self, a_type):
        """ Parse latlon component.
            It should be a lat range lat [min] to [max]
        
            Args: a_type : LAT or LON
               
            Returns:
               return a dictionary of pased values 
        
            Raises:
               exception 
        """
        res_dict = {}
        
        token = self._tokenizer.next()
        
        # negative number
        if token.type == IMSParser.TOKEN_NAMES.MINUS:
            
            #expect a number
            token = self._tokenizer.consume_next_token(IMSParser.TOKEN_NAMES.NUMBER)
            
            res_dict['START'] = '-%s' % (token.value)
            
            # try to consume the next token that should be TO
            self._tokenizer.consume_next_token(IMSParser.TOKEN_NAMES.TO)
        # positive number
        elif token.type == IMSParser.TOKEN_NAMES.NUMBER:
            
            res_dict['START'] = token.value
            
            # try to consume the next token that should be TO
            self._tokenizer.consume_next_token(IMSParser.TOKEN_NAMES.TO)
        # no min value    
        elif token.type == IMSParser.TOKEN_NAMES.TO:
            # add the min value because begin value has been omitted
            res_dict['START'] = IMSParser.TOKEN_NAMES.MIN 
        else:
            raise ParsingError(ParsingError.create_std_error_msg('a number or to', token), \
                               'The %s line is not well formatted' % (a_type), token)
            
        token = self._tokenizer.next()
        
        # it can be either NUMBER (ENDMAG) or NEWLINE (this means that it will magnitude max)
        if   token.type == IMSParser.TOKEN_NAMES.MINUS:
            
            #expect a number
            token = self._tokenizer.consume_next_token(IMSParser.TOKEN_NAMES.NUMBER)
            
            res_dict['END'] = '-%s'% (token.value)
            
            # try to consume the next token that should be TO
            #go to next token
            self._tokenizer.next()
            
        elif token.type == IMSParser.TOKEN_NAMES.NUMBER:
            
            res_dict['END'] = token.value
            
            #consume new line
            self._tokenizer.consume_next_token(IMSParser.TOKEN_NAMES.NEWLINE)
            
        elif token.type == IMSParser.TOKEN_NAMES.NEWLINE:
            
            res_dict['END'] = IMSParser.TOKEN_NAMES.MAX 
        else:
            raise ParsingError(ParsingError.create_std_error_msg('a number or to', token), \
                               'The %s line is not well formatted' % (a_type), token)
            
        #go to next token
        self._tokenizer.next()
       
        return res_dict
            
    def _parse_time(self):
        """ Parse time component.
            It should be a time range time [date1[time1]] to [date2[time2]]
        
            Args: None
               
            Returns:
               return a dictionary of pased values 
        
            Raises:
               exception 
        """
        time_dict = {}
        
        token = self._tokenizer.next()
        
        if token.type != IMSParser.TOKEN_NAMES.DATETIME:
            raise ParsingError(ParsingError.create_std_error_msg('a datetime', token), \
                               'The time line is incorrect. The datetime value is probably malformatted or missing.'\
                               , token)
            
        time_dict['START'] = token.value
        
        token = self._tokenizer.next()
        # it should be a TO
        if token.type != IMSParser.TOKEN_NAMES.TO:
            raise ParsingError(ParsingError.create_std_error_msg('a to', token), \
                               'The to keyword is missing in the line time', token)
            
        token = self._tokenizer.next()
        if token.type != IMSParser.TOKEN_NAMES.DATETIME:
            raise ParsingError(ParsingError.create_std_error_msg('a datetime', token), \
                               'The time line is incorrect. The datetime value is probably malformatted or missing.'\
                               , token)
            
        time_dict['END'] = token.value
        
        #consume at least a NEWLINE
        self._tokenizer.consume_next_token(IMSParser.TOKEN_NAMES.NEWLINE)
        
        return time_dict
        
    def _parse_subscription_message(self):
        """ Parse Radionuclide and SHI request messages
        
            Args: None
               
            Returns:
               return a dictionary of pased values 
        
            Raises:
               exception 
        """ 
        
        #The dictionary of subscription products or commands
        result_dict         = {}
        #The list of processed products
        product_list        = []
        #The list of processed commands
        command_list        = []
        #The current element being parsed (command or product)
        current_element     = {}
        
        token = self._tokenizer.current_token()
        
        last_file_position = self._tokenizer.file_pos() - len(token._parsed_line)
        
        # For the moment look for the different possible tokens
        while token.type != IMSParser.TOKEN_NAMES.STOP and token.type != IMSParser.TOKEN_NAMES.ENDMARKER:
           
            # if it is a new current_element deep copy the current info
            if token.type in IMSParser.c_ALL_PRODUCTS:
    
                current_element.update(self._parse_complex_product(token))
                
                current_file_position = self._tokenizer.file_pos()
                
                product_desc = self._tokenizer.get_tokenized_string(last_file_position, current_file_position)
                
                current_element[product_dict_const.SUB_PRODUCT_DESC] = product_desc
                
                # add create current_element dict in result list
                product_list.append(current_element)
                if product_dict_const.PRODUCTLIST not in result_dict:
                    result_dict.update({product_dict_const.PRODUCTLIST: product_list})
                            
                
                
                # create a new current_element from the previous one
                # it will only be added if we have a new current_element type
                # Used to override parameters between products
                current_element = copy.deepcopy(current_element)
            
            elif token.type in IMSParser.c_ALL_COMMANDS:
                #Add the command key in the current element dict
                current_element.update({
                                            product_dict_const.COMMAND  : token.type,
                                            product_dict_const.TYPE     : product_dict_const.COMMAND
                                       })
                
                #Add this command in the list of commands returned in the result dict
                command_list.append(current_element)
                if product_dict_const.COMMANDLIST not in result_dict:
                    result_dict.update({product_dict_const.COMMANDLIST: command_list})
                
                #Re initialize the command dictionnary for the next command to be parsed
                current_element = {}
                
                #Go to next token
                self._tokenizer.consume_while_next_token_in([IMSParser.TOKEN_NAMES.NEWLINE])
                
            # time keyword
            elif token.type == IMSParser.TOKEN_NAMES.TIME:
               
                current_element['DATE'] = self._parse_time()
                   
            # bull_type 
            # they both expect an ID
            elif token.type in (IMSParser.TOKEN_NAMES.BULLTYPE,\
                                IMSParser.TOKEN_NAMES.MAGPREFMB, \
                                IMSParser.TOKEN_NAMES.MAGPREFMS,
                                IMSParser.TOKEN_NAMES.SUBSCRNAME):
                
                t_type = token.type
                
                # next token should be a ID (Bulletin type)
                token = self._tokenizer.next()
                
                if token.type != IMSParser.TOKEN_NAMES.ID:
                    raise ParsingError(ParsingError.create_std_error_msg('a id', token), \
                                       'The bull_type id qualifying type of bulletin requested is missing', token)

                current_element[t_type] = token.value
                
                self._tokenizer.consume_while_next_token_in([IMSParser.TOKEN_NAMES.NEWLINE])
            #RELATIVE_TO origin | event | bulletin or ID
            elif token.type == IMSParser.TOKEN_NAMES.RELATIVETO:
               
                # next token should be a ID (Bulletin type)
                token = self._tokenizer.consume_next_tokens([IMSParser.TOKEN_NAMES.ORIGIN, \
                                                             IMSParser.TOKEN_NAMES.EVENT, \
                                                             IMSParser.TOKEN_NAMES.BULLETIN, \
                                                             IMSParser.TOKEN_NAMES.ID])
                
                current_element[IMSParser.TOKEN_NAMES.RELATIVETO] = token.value

                self._tokenizer.consume_while_next_token_in([IMSParser.TOKEN_NAMES.NEWLINE])   
                                 
            # mag , depth, eventstadist, depthminuserror mbminusms keyword
            elif token.type in (IMSParser.TOKEN_NAMES.MAG, IMSParser.TOKEN_NAMES.DEPTH,\
                                IMSParser.TOKEN_NAMES.EVENTSTADIST, IMSParser.TOKEN_NAMES.DEPTHMINUSERROR,\
                                IMSParser.TOKEN_NAMES.MBMINUSMS):
               
                current_element[token.type] = self._parse_range(token) 
                
            #LAT or LON
            elif token.type in (IMSParser.TOKEN_NAMES.LAT,IMSParser.TOKEN_NAMES.LON):
                
                current_element[token.type] = self._parse_latlon(token.type)
                
            elif token.type in IMSParser.c_LIST_PARAMS:
                                
                current_element.update(self._parse_list(token))
            #DEPTHCONF, DEPTHKVALUE, DEPTHTHRESHOLD
            elif token.type in IMSParser.c_SIMPLE_NUMBER_PARAMS:
                
                t_type = token.type
                 
                # next token should be a number (depth conf)
                token = self._tokenizer.next()
                
                if token.type != IMSParser.TOKEN_NAMES.NUMBER:
                    raise ParsingError(ParsingError.create_std_error_msg('a number', token), \
                                       'The depth paramter (conf, kvalue or threshold) number is missing', token)

                current_element[t_type] = token.value
                
                self._tokenizer.consume_while_next_token_in([IMSParser.TOKEN_NAMES.NEWLINE])
            #TIMESTAMP peculiarity
            elif token.type == IMSParser.TOKEN_NAMES.TIMESTAMP:
                current_element['TIMESTAMP'] = True  
                 
                # go to the next token
                token = self._tokenizer.next()
            #Specific parser rule to manage (custom, immediate, ... frequencies)
            elif token.type == IMSParser.TOKEN_NAMES.FREQ:
                t_type = token.type
                
                # next token should be a ID (Bulletin type)
                token = self._tokenizer.next()
                
                current_element[product_dict_const.SUB_FREQUENCY] = {product_dict_const.SUB_POLICY: token.value}
                
                #CUSTOM frequency policy should define a parameter, looking for it
                if token.type == IMSParser.TOKEN_NAMES.CUSTOM:
                    token = self._tokenizer.next()
                    
                    #Test expected type for custom policy parameter
                    if token.type != IMSParser.TOKEN_NAMES.ID:
                        raise ParsingError(ParsingError.create_std_error_msg('a id', token), \
                                           'The custom frequency parameter should be an id', token)
                        
                    current_element[product_dict_const.SUB_FREQUENCY].update({product_dict_const.SUB_VALUE: token.value})
                    
                #Check the frequency policy is correctly defined
                elif token.type not in (IMSParser.TOKEN_NAMES.IMMEDIATE, IMSParser.TOKEN_NAMES.CONTINUOUS, IMSParser.TOKEN_NAMES.DAILY, IMSParser.TOKEN_NAMES.CUSTOM):
                        raise ParsingError(ParsingError.create_std_error_msg('IMMEDIATE, DAILY, CONTINUOUS, or CUSTOM ', token), \
                                           'Unknown frequency policy, should be: IMMEDIATE, DAILY, CONTINUOUS, or CUSTOM ', token)
                        
                        
                self._tokenizer.consume_while_next_token_in([IMSParser.TOKEN_NAMES.NEWLINE])
                
            else:
                raise ParsingError('Unknown or misplaced keyword "%s" (keyword type %s)' % (token.value, token.type), \
                                   'Request mal-formatted', token)

            # eat any left NEWLINE token
            token = self._tokenizer.consume_while_current_token_in([IMSParser.TOKEN_NAMES.NEWLINE])
        
            
        # check if we have a stop
        if token.type != IMSParser.TOKEN_NAMES.STOP:
            raise ParsingError('End of request reached without encountering a stop keyword', \
                               'Stop keyword missing or truncated request', token)
        
        return result_dict
    
    def _parse_data_message(self):
        """ Parse Radionuclide and SHI request messages
        
            Args: None
               
            Returns:
               return a dictionary of pased values 
        
            Raises:
               exception 
        """ 
        raise ParsingError("_parse_data_message is currently not implemented", "No suggestion", ENDMARKERToken(100))
       