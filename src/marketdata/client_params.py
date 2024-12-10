import copy
from dataclasses import asdict, dataclass
import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


class BasicParams:
    """This class is used to create the basic parameters for the API calls. 
        These parameters are common to all the API calls.
    """
    
    def __init__(
        self,
        lookup_date: datetime.date | None = None,
        dateformat: str = "timestamp",
        human: bool = False,
        offset: int | None = None,
        limit: int = 500,
        format: str = "json",
        data_headers: bool = True,
    ):
        """Initializes the BasicParams class with the basic parameters for the API calls.

        Args:
            lookup_date (date, optional): Specific date to lookup. Defaults to None.
            dateformat (str, optional): The dateformat parameter allows you specify the format you wish to receive date and time information in. "timestamp", "spreadsheet", "unix". Defaults to "timestamp".
            human (bool, optional): se human-readable attribute names in the JSON or CSV output instead of the standard camelCase attribute names. Defaults to False.
            offset (int, optional): Used with limit to allow you to implement pagination in your application. Offset returns values starting at a certain value. Defaults to None.
            limit (int, optional): Limit the number of results for a particular API call or override an endpoint's default limits to get more data. Defaults to 500.
            format (str, optional): The format parameter allows you to specify the format you wish to receive the data in. "json", "csv". Defaults to "json".
            data_headers (bool, optional): Used to turn off headers when using CSV output. Defaults to None.
        """
        self.params = {}
        if lookup_date:
            self.params['date'] = lookup_date.strftime('%Y-%m-%d')
        if dateformat:
            self.params['dateformat'] = dateformat
        if human:
            self.params['human'] = human
        if offset:
            self.params['offset'] = offset
        if limit:
            self.params['limit'] = limit
        if format:
            self.params['format'] = format
        if data_headers:
            self.params['headers'] = data_headers

    def __str__(self) -> str:
        return str(self.params)
    
    def to_dict(self) -> Dict[str, Any]:
        return self.params
                
class FromToParams:
    """
    This class is used to create the from and to parameters for the API calls.
    These are used with API calls that can select a range of dates.
    """
    
    def __init__(
        self,
        from_date: datetime.date | None = None,
        to_date: datetime.date | None = None,
        countback: int | None = None,
    ):
        """Initializes the FromToParams class with the from and to dates and countback.

        Args:
            from_date (date, optional): Limit the status to dates after from (inclusive). Should be combined with to to create a range. Defaults to None.
            to_date (date, optional): Limit the status to dates before to (inclusive). Should be combined with from to create a range. Defaults to None.
            countback (int, optional): Countback will fetch a number of dates before (to the left of) to. If you use from, countback is not required. Defaults to None.
        """
        self.params = {}
        if from_date:
            self.params['from'] = from_date.strftime('%Y-%m-%d')
        if to_date:
            self.params['to'] = to_date.strftime('%Y-%m-%d')
        if countback:
            self.params['countback'] = countback
            
    def __str__(self) -> str:
        return str(self.params)
    
    def to_dict(self) -> Dict[str, Any]:
        return self.params
    
@dataclass
class OptionsChainParams:
    underlying: str
    basic_params: Optional[BasicParams] = None
    from_to_params: Optional[FromToParams] = None
    expiration: Optional[datetime.date] = None
    month: Optional[int] = None
    year: Optional[int] = None
    weekly: Optional[bool] = None
    monthly: Optional[bool] = None
    quarterly: Optional[bool] = None
    dte: Optional[int] = None    
    feed: Optional[str] = None  # "live" or "cached"        
    side: str = "both"
    range: str = "all"
    strike: Optional[float] = None
    strikeLimit: Optional[int] = None
    minOpenInterest: Optional[int] = None
    minVolume: Optional[int] = None
    maxBidAskSpread: Optional[float] = None
    maxBidAskSpreadPct: Optional[float] = None
    nonstandard: bool = False
    columns: Optional[str] = None
    output: str = "dataframe"
    id: str = str(uuid4())
    use_cache: bool = False

    def to_dict(self):
        def serialize(v):
            try:
                return v.to_dict()
            except AttributeError:
                if isinstance(v, (datetime.date, UUID)):
                    return str(v)
                return v

        out = {k: serialize(v) for k, v in asdict(self).items() if v is not None}
        del out['id']
        del out['use_cache']
        return out

    def make_copy(self, **kwargs) -> 'OptionsChainParams':
        new_params = copy.deepcopy(self)
        
        # Update the new object with the provided overrides
        for key, value in kwargs.items():
            if hasattr(new_params, key):
                setattr(new_params, key, value)
            else:
                raise ValueError(f"Invalid parameter: {key}")
            
        # Create a new UUID for the new object
        new_params.id = uuid4()
                
        return new_params

@dataclass
class OptionsQuoteParams:
    option_symbol: str
    basic_params: Optional[BasicParams] = None
    from_to_params: Optional[FromToParams] = None
    columns: Optional[str] = None
    output: str = "dataframe"
    use_cache: bool = False

    def to_dict(self):
        out = {k: v for k, v in asdict(self).items() if v is not None}
        del out['use_cache']
        return out

    def make_copy(self, **kwargs) -> 'OptionsQuoteParams':
        new_params = copy.deepcopy(self)
        
        # Update the new object with the provided overrides
        for key, value in kwargs.items():
            if hasattr(new_params, key):
                setattr(new_params, key, value)
            else:
                raise ValueError(f"Invalid parameter: {key}")
            
        return new_params