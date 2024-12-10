"""
marketdata.app API Client
"""
import os
from time import time
from urllib.parse import urlencode
import requests
import datetime
import json
import hashlib
 
import numpy as np
import pandas as pd
from loguru import logger
import pandas as pd

from marketdata.client_params import BasicParams, FromToParams, OptionsChainParams
from marketdata.credentials import MARKET_DATA_API_KEY

BASE_URL = 'https://api.marketdata.app/v1/'

class MarketDataClient:
    
    def __init__(self) -> None:
        self.BASE_URL = 'https://api.marketdata.app/v1/'
        self.api_key = MARKET_DATA_API_KEY
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        self.cache_list = {}
        self.api_calls = 0
    
    def handle_response(self, response, output):
        try:
            if output == "raw":
                return response.json(), response.status_code
            elif output == "dataframe":
                if 200 <= response.status_code < 300:
                    df = pd.DataFrame(response.json())
                    try:
                        df.drop(columns=['s'], inplace=True)
                    except KeyError:
                        pass
                    return df, response.status_code
                else:
                    return response.json(), response.status_code                
        # Handle the case where the response is not JSON
        except ValueError:
            return response.text, response.status_code
    
    def check_cache(self, sub_dir, **kwargs):
        
        if sub_dir == None or sub_dir == "":
            raise ValueError("sub_dir must be specified")
        
        key = self.construct_cache_key(**kwargs)
        df, status_code = self.load_from_cache(key, sub_dir)
        return df, status_code, key
        
    
    def construct_cache_key(self, **kwargs):
        # Sort the kwargs by key to ensure consistent ordering
        sorted_kwargs = sorted(kwargs.items(), key=lambda x: x[0])
        
        def serialize_object(obj):
            if isinstance(obj, (datetime.date, datetime.datetime)):
                return obj.isoformat()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64, 
                                np.uint8, np.uint16, np.uint32, np.uint64)):
                return int(obj)
            elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
                return float(obj)
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif hasattr(obj, '__dict__'):
                return {key: serialize_object(value) for key, value in obj.__dict__.items()}
            else:
                return str(obj)
        
        # Sort the kwargs by key to ensure consistent ordering
        sorted_kwargs = sorted(kwargs.items(), key=lambda x: x[0])
        
        # Serialize each value in the sorted kwargs
        serialized_kwargs = [(k, serialize_object(v)) for k, v in sorted_kwargs]
        
        # Convert the serialized kwargs into a JSON string
        try:
            kwargs_json = json.dumps(serialized_kwargs)
        except TypeError as e:
            # If JSON serialization fails, use string representation as fallback
            kwargs_json = str(serialized_kwargs)
        
        # Create a hash of the JSON string
        hash_object = hashlib.md5(kwargs_json.encode())
        cache_key = hash_object.hexdigest()
        
        return cache_key
    
    def load_from_cache(self, cache_key, sub_dir):
        
        if sub_dir == None or sub_dir == "":
            raise ValueError("sub_dir must be specified")
        
        cache_path = os.path.join('./data/cache', sub_dir)
        
        start_time = time()
        if not os.path.exists(cache_path):
            os.makedirs(cache_path)
            
        if cache_key in self.cache_list:
            # logger.debug(f"Found data in cache dictionary: {cache_key}")
            data = pd.read_parquet(self.cache_list[cache_key])
            if not data.empty:
                status_code = 250
                # logger.info(f"Loaded data from cache: {cache_key} in {time() - start_time:.2f} seconds")
                return data, status_code

        if not cache_key in self.cache_list:
            # Check if the cache file exists in the cache directory
            key_path = f'{cache_path}/{cache_key}.parquet'
            if os.path.exists(key_path):
                self.cache_list[cache_key] = key_path
                logger.debug(f"Found data in cache file list: {cache_key}")
                
                try:
                    # Read the file from the cache
                    data = pd.read_parquet(key_path)
                    if not data.empty:
                        status_code = 250
                    else:
                        status_code = 402
                except Exception as e:
                    logger.debug(f"Error reading cache file: {e}, returning as JSON")
                    with open(f'{cache_path}/{cache_key}.json', 'r') as f:
                        data = json.load(f)
                        if data.get('s') == 'no_data':
                            status_code = 402
                        elif data.get('s') == 'error':
                            status_code = 500
                        else:
                            status_code = 250                
  
                # logger.info(f"Loaded data from cache: {cache_key} in {time() - start_time:.2f} seconds")
                return data, status_code
            
        return pd.DataFrame(), 402
    
    def save_to_cache(self, data, cache_key, sub_dir):
        
        if sub_dir == None or sub_dir == "":
            raise ValueError("sub_dir must be specified")
        
        cache_path = os.path.join('./data/cache', sub_dir)
        
        if not os.path.exists(cache_path):
            os.makedirs(cache_path)
        
        if isinstance(data, pd.DataFrame):
            data.to_parquet(f'{cache_path}/{cache_key}.parquet')
        else:
            with open(f'{cache_path}/{cache_key}.json', 'w') as f:
                json.dump(data, f)
        # logger.debug(f"Saved data to cache: {cache_key}")
        
    # /v1/funds/candles/{resolution}/{symbol}/
    def get_fund_candles(
        self,
        resolution: str,
        symbol: str,
        basic_params: BasicParams | None = None,
        from_to_params: FromToParams | None = None,
        columns: str = None,
        output = "dataframe"
    ):
        url = BASE_URL + f'funds/candles/{resolution}/{symbol}/'
        params = {}
        
        if basic_params:
            params.update(basic_params.params)
        if from_to_params:
            params.update(from_to_params.params)
        if columns:
            params['columns'] = columns
        
        response = requests.get(url, headers=self.headers, params=params)
        self.api_calls += 1
        return self.handle_response(response, output)

    # /v1/indices/candles/{resolution}/{symbol}/
    def get_index_candles(
        self,
        resolution: str,
        symbol: str,
        basic_params: BasicParams | None = None,
        from_to_params: FromToParams | None = None,
        columns: str = None,
        output = "dataframe"
    ):
        url = BASE_URL + f'indices/candles/{resolution}/{symbol}/'
        params = {}
        
        if basic_params:
            params.update(basic_params.params)
        if from_to_params:
            params.update(from_to_params.params)
        if columns:
            params['columns'] = columns
        
        response = requests.get(url, headers=self.headers, params=params)
        self.api_calls += 1
        return self.handle_response(response, output)

    # /v1/indicies/quotes/{symbol}/
    def get_index_quote(
        self,
        symbol: str,
        basic_params: BasicParams | None = None,
        columns: str = None,
        output = "dataframe"
    ):
        url = BASE_URL + f'indices/quotes/{symbol}/'
        params = {}
        
        if basic_params:
            params.update(basic_params.params)
        if columns:
            params['columns'] = columns
        
        # Remove the lookup_date parameter if it exists
        if isinstance(basic_params, dict) and basic_params.get('lookup_date'):
            del basic_params['lookup_date']
            logger.warning("The lookup_date parameter is not supported for this endpoint. It will be ignored.")
        
        response = requests.get(url, headers=self.headers, params=params)
        self.api_calls += 1
        return self.handle_response(response, output)
            
    # /v1/markets/status/
    def get_markets_status(
        self,
        basic_params: BasicParams | None = None,
        from_to_params: FromToParams | None = None,
        country: str = "US",
        output = "dataframe"
    ) -> dict | str:
        """Get market status ("open" or "closed") for a date or range of dates.

        Args:
            
            basic_params (BasicParams, optional): See BasicParams class. Defaults to None.
            from_to_params (FromToParams, optional): See FromToParams class. Defaults to None.
            country (str, optional): Use to specify the country of the exchange. Use the two digit ISO 3166 country code. Defaults to "US".
            output (str, optional): The output format. Can be "dataframe", which is a pandas dataframe or "raw", which is the raw JSON response. Defaults to "dataframe".
            
        Returns:
            dict, str: Returns the raw data and the status code.
        """
        url = BASE_URL + 'markets/status/'
        
        params = {}
        if basic_params:
            params.update(basic_params.params)
        if from_to_params:
            params.update(from_to_params.params)
        params['country'] = country
        
        response = requests.get(url, headers=self.headers, params=params)
        self.api_calls += 1
        return self.handle_response(response, output)
        
    # /v1/options/chain/{underlying}/
    def get_options_chain(self, params: OptionsChainParams, use_cache: bool = True):
        """Get options chain for a symbol.

        Args:
            params (OptionsChainParams): An object containing all the parameters for the options chain request.

        Returns:
            dict, str: Returns the raw data as a dictionary or an error message.
        """

        if use_cache:
            cached_data, status_code, cache_key = self.check_cache(
                sub_dir="options_chain",
                method_name="get_options_chain",
                **params.to_dict()
            )
        else:
            cached_data = pd.DataFrame()
            status_code = 402
            cache_key = None
            
        if not cached_data.empty:
            logger.debug(f"Returning cached data for {cache_key}")
            return cached_data, status_code

        url = BASE_URL + f'options/chain/{params.underlying}/'
        request_params = params.to_dict()

        # Remove 'underlying' and 'id' from request_params as they're not needed in the API call
        request_params.pop('underlying', None)
        request_params.pop('id', None)

        # Handle nested objects
        if params.basic_params:
            request_params.update(params.basic_params.params)
            request_params.pop('basic_params', None)
        if params.from_to_params:
            request_params.update(params.from_to_params.params)
            request_params.pop('from_to_params', None)

        logger.warning(f"Debug - Full URL: {url}?{urlencode(request_params)}")
        url = f"{url}?{urlencode(request_params)}"
        response = requests.get(url, headers=self.headers)
        self.api_calls += 1
        data, status_code = self.handle_response(response, params.output)
        
        # Save the data to the cache
        self.save_to_cache(data, cache_key, "options_chain")
        return data, status_code

    # /v1/options/expirations/{underlying}/
    def get_options_expirations(
        self,
        underlying: str,
        basic_params: BasicParams | None = None,
        strike: float | None = None,
        columns: str = None,
        output = "dataframe"
    ):
        url = BASE_URL + f'options/expirations/{underlying}/'
        params = {}
        if basic_params:
            params.update(basic_params.params)
        if strike:
            params['strike'] = strike
        if columns:
            params['columns'] = columns
        
        response = requests.get(url, headers=self.headers, params=params)
        self.api_calls += 1
        return self.handle_response(response, output)
    

    # /v1/options/lookup/{userInput}/
    # This doesn't work in the Swagger UI, so not implemented here
        

    # /v1/options/quotes/{optionSymbol}/
    def get_options_quotes(
        self,
        option_symbol: str,
        basic_params: BasicParams | None = None,
        from_to_params: FromToParams | None = None,
        columns: str = None,
        output = "dataframe",
        use_cache: bool = True
    ):
        
        if use_cache:
            cached_data, status_code, cache_key = self.check_cache(
                sub_dir="options_quotes",
                method_name="get_options_quotes",
                option_symbol=option_symbol,
                basic_params=basic_params,
                from_to_params=from_to_params,
                columns=columns,
                output=output
            )
        else:
            cached_data = pd.DataFrame()
            status_code = 402
            cache_key = None
        
        if not cached_data.empty:
            logger.debug(f"Returning cached data for {cache_key}")
            return cached_data, status_code

        url = BASE_URL + f'options/quotes/{option_symbol}/'
        params = {}
        if basic_params:
            params.update(basic_params.params)
        if from_to_params:
            params.update(from_to_params.params)
        if columns:
            params['columns'] = columns

        response = requests.get(url, headers=self.headers, params=params)
        self.api_calls += 1
        data, status_code = self.handle_response(response, output)
        if isinstance(data, pd.DataFrame):
            # Save the data to the cache
            self.save_to_cache(data, cache_key, "options_quotes")
        return data, status_code
        

    # /v1/options/strikes/{underlying}/
    def get_options_strikes(
        self,
        underlying: str,
        basic_params: BasicParams | None = None,
        expiration_date: datetime.date | None = None,
        columns: str = None,
        output: str = "dataframe"
    ):
        """Get a list of current or historical options strikes for an underlying
        symbol. If no optional parameters are used, the endpoint returns the 
        strikes for every expiration in the chain.

        Args:
            underlying (str): The underlying ticker symbol for the options chain you wish to lookup. Ticker Formats: (TICKER, TICKER.EX, EXCHANGE:TICKER)
            basic_params (BasicParams | None, optional): See BasicParams class. Defaults to None.
            expiration_date (datetime.date | None, optional): Limit the strikes to a specific expiration date. Defaults to None.
            columns (str, optional): Limits the results and only request the columns you need. The most common use of this feature is to embed a single numeric result from one of the end points in a spreadsheet cell.. Defaults to None.
            output (str, optional): The output format. Can be "dataframe", which is a pandas dataframe or "raw", which is the raw JSON response. Defaults to "dataframe".

        Returns:
            _type_: _description_
        """
        url = BASE_URL + f'options/strikes/{underlying}/'
        params = {}
        if basic_params:
            params.update(basic_params.params)
        if expiration_date:
            params['expiration'] = expiration_date.strftime('%Y-%m-%d')
        if columns:
            params['columns'] = columns
            
        response = requests.get(url, headers=self.headers, params=params)
        self.api_calls += 1
        return self.handle_response(response, output)
    

    # /v1/stocks/bulkcandles/{resolution}/
    def get_bulk_stock_candles(
        self,
        symbols: list[str],
        basic_params: BasicParams | None = None,
        from_to_params: FromToParams | None = None,
        exchange: str = None,
        country: str = "US",
        snapshot: bool = False,
        adjust_splits: bool = None,
        adjust_dividends: bool = None,
        columns: str = None,
        output = "dataframe"
    ):
        """This seems to be incorrectly implemented in the API. Can't get
        it to work and the Swagger UI gives invalid input fields.
        """
        url = BASE_URL + f'stocks/bulkcandles/daily/'
        params = {}
        if basic_params:
            params.update(basic_params.params)
        if from_to_params:
            params.update(from_to_params.params)
        if exchange:
            params['exchange'] = exchange
        if adjust_splits:
            params['adjust_splits'] = adjust_splits
        if adjust_dividends:
            params['adjust_dividends'] = adjust_dividends
        if columns:
            params['columns'] = columns
        params['symbols'] = ','.join(symbols)
        params['country'] = country
        params['snapshot'] = snapshot
        
        response = requests.get(url, headers=self.headers, params=params)
        self.api_calls += 1
        return self.handle_response(response, output)

    # /v1/stocks/bulkquotes/
    def get_bulk_stock_quotes(
        self,
        symbols: list[str],
        basic_params: BasicParams | None = None,
        columns: str = None,
        output = "dataframe"
    ):
        url = BASE_URL + 'stocks/bulkquotes/'
        params = {}
        if basic_params:
            params.update(basic_params.params)
        if columns:
            params['columns'] = columns
        params['symbols'] = ','.join(symbols)
        
        # If the lookup_date is in the params, remove it
        if isinstance(basic_params, dict) and basic_params.get('lookup_date'):
            del basic_params['lookup_date']
            logger.warning("The lookup_date parameter is not supported for this endpoint. It will be ignored.")
        
        response = requests.get(url, headers=self.headers, params=params)
        # TODO: Verify that this is actually counted as a single API call
        self.api_calls += 1
        return self.handle_response(response, output)

    # /v1/stocks/candles/{resolution}/{symbol}/
    def get_stock_candles(
        self,
        symbol: str,
        resolution: str = "1D",
        basic_params: BasicParams | None = None,
        from_to_params: FromToParams | None = None,
        columns: str = None,
        exchange: str = None,
        extended_hours: bool = False,
        exchange_country: str = "US",
        adjust_splits: bool = None,
        adjust_dividends: bool = None,
        output = "dataframe"
    ):
        """Get historical stock candles for a symbol.
        
        Args:
            symbol (str): The company's ticker symbol. If no exchange is specified, by default a US exchange will be assumed. You may embed the exchange in the ticker symbol using the Yahoo Finance or TradingView formats. Ticker Formats: (TICKER, TICKER.EX, EXCHANGE:TICKER)
            resolution (str, optional): The duration of each candle. Minutely Resolutions: (1, 3, 5, 15, 30, 45, ...) Hourly Resolutions: (H, 1H, 2H, ...) Daily Resolutions: (D, 1D, 2D, ...) Weekly Resolutions: (W, 1W, 2W, ...) Monthly Resolutions: (M, 1M, 2M, ...) Yearly Resolutions:(Y, 1Y, 2Y, ...)'). Defaults to "1D".
            basic_params (BasicParams, optional): See BasicParams class. Defaults to None.
            from_to_params (FromToParams, optional): See FromToParams class. Defaults to None.
            columns (str, optional): Limits the results and only request the columns you need. The most common use of this feature is to embed a single numeric result from one of the end points in a spreadsheet cell.. Defaults to None.
            exchange (str, optional): Use to specify the exchange of the ticker. This is useful when you need to specify stock that quotes on several exchanges with the same symbol. You may specify the exchange using the EXCHANGE ACRONYM, MIC CODE, or two digit YAHOO FINANCE EXCHANGE CODE. If no exchange is specified symbols will be matched to US exchanges first.. Defaults to None.
            extended_hours (bool, optional): Include extended hours trading sessions when returning intraday candles. Daily resolutions never return extended hours candles. Defaults to False.
            exchange_country (str, optional): Specify the country of the exchange (not the country of the company) in conjunction with the symbol argument. This argument is useful when you know the ticker symbol and the country of the exchange, but not the exchange code. Use the two digit ISO 3166 country code. Defaults to "US".
            adjust_splits (bool, optional): Adjust historical data for for historical splits and reverse splits. Market Data uses the CRSP methodology for adjustment. Daily candles default: true. Intraday candles default: false.
            adjust_dividends (bool, optional): Adjust candles for dividends. Market Data uses the CRSP methodology for adjustment. Daily candles default: true. Intraday candles default: false.
            output (str, optional): The output format. Can be "dataframe", which is a pandas dataframe or "raw", which is the raw JSON response. Defaults to "dataframe".
        Returns:
            _type_: _description_
        """
        
        url = BASE_URL + f'stocks/candles/{resolution}/{symbol}/'
        params = {}
        if basic_params:
            params.update(basic_params.params)
        if from_to_params:
            params.update(from_to_params.params)
            
        options = {
            'columns': columns,
            'exchange': exchange,
            'extended_hours': extended_hours,
            'exchange_country': exchange_country,
            'adjust_splits': adjust_splits,
            'adjust_dividends': adjust_dividends
        }
        
        # Update params with non-None options
        for key, value in options.items():
            if value is not None:
                params[key] = value

        response = requests.get(url, headers=self.headers, params=params)
        self.api_calls += 1
        return self.handle_response(response, output)
    
    # /v1/stocks/earnings/{symbol}/
    def get_earnings(
            self,
            symbol: str,
            basic_params: BasicParams | None = None,
            from_to_params: FromToParams | None = None,
            report: str = None,
            columns: str = None,
            output: str = "dataframe"
        ):
        url = BASE_URL + f'stocks/earnings/{symbol}/'
        params = {}

        # Unpack parameters from objects if they are not None
        if basic_params:
            params.update(basic_params.params)
        if from_to_params:
            params.update(from_to_params.params)

        # Update params with other optional parameters if they are not None
        optional_params = {'report': report, 'columns': columns}
        params.update({k: v for k, v in optional_params.items() if v is not None})
        
        response = requests.get(url, headers=self.headers, params=params)
        self.api_calls += 1
        return self.handle_response(response, output)

    # /v1/stocks/news/{symbol}/
    def get_stock_news(
        self,
        symbol: str,
        basic_params: BasicParams = None,
        from_to_params: FromToParams = None,
        output = "dataframe"
    ):
        url = BASE_URL + f'stocks/news/{symbol}/'
        params = {}
        
        if basic_params:
            params.update(basic_params.params)
        if from_to_params:
            params.update(from_to_params.params)
        
        response = requests.get(url, headers=self.headers, params=params)
        self.api_calls += 1
        return self.handle_response(response, output)

    # /v1/stocks/quotes/{symbol}/
    def get_stock_quote(
        self,
        symbol: str,
        basic_params: BasicParams = None,
        columns: str = None,
        output = "dataframe"
    ):
        url = BASE_URL + f'stocks/quotes/{symbol}/'
        params = {}
        
        if basic_params:
            params.update(basic_params.params)
        if columns:
            params['columns'] = columns
        
        # This is one of the few API calls that does not have a lookup_date,
        # so we need to remove it if it exists
        if isinstance(basic_params, dict) and basic_params.get('lookup_date'):
            del basic_params['lookup_date']
        
        response = requests.get(url, headers=self.headers, params=params)
        self.api_calls += 1
        return self.handle_response(response, output)
    