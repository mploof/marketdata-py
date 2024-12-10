import os
import re
from datetime import date, timedelta, datetime
import json
from typing import Dict, List

from loguru import logger
import pandas as pd

from marketdata.client import MarketDataClient
from marketdata.client_async import MarketDataAsyncClient
from marketdata.client_params import OptionsQuoteParams, OptionsChainParams
       
class MarketDataManager:
    
    def __init__(self, cache_dir: str="./data/cache"):
        self.client = MarketDataClient()
        self.client_async = MarketDataAsyncClient()
        self.candle_cache = {}
        self.first_available_cache = {}
        
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        if not os.path.exists(f"{cache_dir}/candles"):
            os.makedirs(f"{cache_dir}/candles")
    
    def validate_resolution(self, resolution: str):
        # Validate the input resolution
        pattern = re.compile(r"(\d+[MHWDY]?\b)")
        if not pattern.match(resolution):
            logger.error("Invalid resolution format. Must be in the format <number>[MHDWY]")
            return False
        return True
    
    def get_first_available_date(self, symbol: str, resolution: str):
        # Get the first available date for the symbol
        # This is useful for determining the earliest date that we can get data for
        # for a given symbol
        
        if not self.validate_resolution(resolution):
            logger.error("Invalid resolution format. Must be in the format <number>[MHDWY]")
            raise ValueError("Invalid resolution format. Must be in the format <number>[MHDWY]")
        
        if symbol not in self.first_available_cache:
        
            if not os.path.exists(f"./data/cache/candles/_first_available_{symbol}.json"):
                return None
            
            with open(f"./data/cache/candles/_first_available_{symbol}.json", "rb") as f:
                first_available = json.load(f)
                self.first_available_cache[symbol] = first_available
        
        first_available_date = self.first_available_cache[symbol].get(resolution, None)
        if first_available_date:
            return date.fromisoformat(first_available_date)
            
    def set_first_available_date(self, symbol: str, resolution: str, date: date):
        # Set the first available date for the symbol
        # This is useful for determining the earliest date that we can get data for
        # for a given symbol
        
        if not self.validate_resolution(resolution):
            logger.error("Invalid resolution format. Must be in the format <number>[MHDWY]")
            raise ValueError("Invalid resolution format. Must be in the format <number>[MHDWY]")
        
        if symbol not in self.first_available_cache:
            self.first_available_cache[symbol] = {}
        
        self.first_available_cache[symbol][resolution] = date.isoformat()
        
        with open(f"./data/cache/candles/_first_available_{symbol}.json", "w", encoding="utf-8") as f:
            # Serialize the date object to a string
            out_str = json.dumps(self.first_available_cache[symbol])
            # Write the string to the file
            f.write(out_str)
            
    
    def get_stock_candles(
        self,
        symbols: List[str],
        resolution: str,
        from_date: date | datetime,
        to_date: date | datetime | None = None,
        friendly_names=True,
        use_cache=True
    ) -> Dict[str, tuple[pd.DataFrame, int]]:
        if isinstance(from_date, datetime):
            from_date = from_date.date()
        if isinstance(to_date, datetime):
            to_date = to_date.date()
        
        if to_date is None:
            to_date = date.today()
            
        if from_date > to_date:
            logger.error("from_date cannot be after to_date")
            raise ValueError("from_date cannot be after to_date")
            # return {symbol: None for symbol in symbols}        
        
        if to_date > date.today():
            to_date = date.today()
        
        # Adjust for weekends and Mondays before 6pm
        if to_date.weekday() == 5:
            to_date -= timedelta(days=1)
        elif to_date.weekday() == 6:
            to_date -= timedelta(days=2)
        elif to_date.weekday() == 0 and datetime.now().time() < datetime.strptime("18:00", "%H:%M").time():
            to_date -= timedelta(days=3)
        
        self.validate_resolution(resolution)
        
        results = {}
        symbols_to_fetch = []
        
        for symbol in symbols:
            first_available_date = self.get_first_available_date(symbol, resolution)
            if first_available_date and from_date < first_available_date:
                logger.warning(f"Adjusting request date for {symbol} to available data from {first_available_date}")
                symbol_from_date = first_available_date
            else:
                symbol_from_date = from_date
            
            # Check in-memory cache
            cached_data = self.candle_cache.get(f"{symbol}_{resolution}", None)
            if cached_data:
                cached_from_date = cached_data["from_date"]
                cached_to_date = cached_data["to_date"]
                if isinstance(cached_from_date, str):
                    cached_from_date = date.fromisoformat(cached_from_date)
                if isinstance(cached_to_date, str):
                    cached_to_date = date.fromisoformat(cached_to_date)
                if symbol_from_date >= cached_from_date and to_date <= cached_to_date:
                    results[symbol] = cached_data["data"]
                                
            # Check file cache if not in memory
            if symbol not in results:
                file_list = [f for f in os.listdir("./data/cache/candles") if f.startswith(f"{symbol}_{resolution}")]
                for f in file_list:
                    parts = f.split("_")
                    from_date_file, to_date_file = map(date.fromisoformat, [parts[2], parts[3].split(".")[0]])
                    if symbol_from_date >= from_date_file and to_date <= to_date_file:
                        df = pd.read_parquet(f"./data/cache/candles/{f}")
                        self.candle_cache[f"{symbol}_{resolution}"] = \
                        {
                            "data": df,
                            "from_date": symbol_from_date,
                            "to_date": to_date_file
                        }
                        results[symbol] = df
                        break
            
            # If not found in cache, add to list to update via API request
            if symbol not in results:
                symbols_to_fetch.append(symbol)
        
        # Update symbols that were not found in the available cache
        if symbols_to_fetch:            
            self._update_candle_cache(symbols_to_fetch, resolution)
            for symbol in symbols_to_fetch:
                if symbol not in results:
                    results[symbol] = None
                else:
                    results[symbol] = self.candle_cache[f"{symbol}_{resolution}"]["data"]
        
        # Process each dataframe
        for symbol, df in results.items():
            if df is not None:
                
                if first_available_date is None:                    
                    try:
                        actual_from_date = df.at[0, 't']
                        self.set_first_available_date(symbol, resolution, date.fromisoformat(actual_from_date))
                    except AttributeError as e:
                        logger.error(f"Failed to set first available date for {symbol}")
                        logger.error(df)
                        raise e
                    
                if self.get_first_available_date(symbol, resolution) > from_date:
                    logger.warning(f"Requested data is not available for {symbol} from {from_date}. Using first available data from {self.get_first_available_date(symbol, resolution)} instead.")
                
                try:                    
                    if 't' in df.columns:                        
                        df.set_index('t', inplace=True)
                except AttributeError as e:
                    logger.error(f"Failed to set index for {symbol}")
                    raise e
                except KeyError as e:
                    print(results['SPY'])
                    raise e
                
                # Filter the data to the requested date range
                df = df[(df.index >= from_date.isoformat()) & (df.index <= to_date.isoformat())]
                df.reset_index(inplace=True)
                
                if friendly_names:
                    df = df.rename(columns={'t': 'datetime', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'})
                
                results[symbol] = df
        
        return results
    
    def _update_candle_cache(self, symbols: List[str], resolution: str):
        
        logger.debug(f"Updating cache for {symbols} with resolution {resolution}")
        
        # Since we are updating the cache we want to fetch all available data
        from_date = date(2000, 1, 1)
        to_date = date.today()        
    
        fetched_data = self.client_async.get_stock_candles_parallel(symbols, resolution, from_date, to_date)
        for symbol, (data, status_code) in fetched_data.items():
            if data.get("s") == "no_data":
                logger.warning(f"No data available for {symbol} for resolution {resolution} and date range {from_date} to {to_date}")
                continue
            elif data.get("s") == "error":
                logger.error(f"Error fetching data for {symbol} for resolution {resolution} and date range {from_date} to {to_date}")
                logger.error(data)
                continue
            elif 200 <= status_code < 300:
                logger.info(f"Candle cache updated for {symbol} for resolution {resolution} and date range {from_date} to {to_date}")
                df = pd.DataFrame(data)
                actual_from_date = df.at[0, 't']
                actual_to_date = df.at[df.index[-1], 't']
                self.set_first_available_date(symbol, resolution, date.fromisoformat(actual_from_date))
                
                # Delete old files for this symbol and resolution
                old_files = [f for f in os.listdir(f"./data/cache/candles") if f.startswith(f"{symbol}_{resolution}")]
                for f in old_files:
                    os.remove(f"./data/cache/candles/{f}")
                
                # Write the data to the file cache
                df.to_parquet(f"./data/cache/candles/{symbol}_{resolution}_{actual_from_date}_{actual_to_date}.parquet")
                
                # And put the data into the in-memory cache
                self.candle_cache[f"{symbol}_{resolution}"] = {
                    "from_date": actual_from_date,
                    "to_date": actual_to_date,
                    "data": df
                }
            else:
                logger.error(f"Unknown status code for {symbol} for resolution {resolution} and date range {from_date} to {to_date}")
                logger.error(data)
                logger.error(status_code)
                raise ValueError(f"Unknown status code for {symbol} for resolution {resolution} and date range {from_date} to {to_date}")
    
    
    def get_option_chains(self, params: List[OptionsChainParams]) -> List[dict]:
        """
        Fetch options chains for multiple symbols in parallel.

        Args:
            params (List[OptionsChainParams]): A list of OptionsChainParams objects 
                                            specifying the options chains to retrieve.

        Returns:
            Dict[str, pd.DataFrame]: A dictionary where each key is a UUID (string) 
            generated for the request, and each value is a pandas DataFrame 
            containing the options chain data for the corresponding request.
            The UUID can be used to match the returned data with the input parameters.
        """
        return self.client_async.get_options_chains_parallel(params)

    def get_options_quotes(self, params: List[OptionsQuoteParams]) -> Dict[str, pd.DataFrame]:
        """
        Fetch options quotes for multiple options in parallel.

        Args:
            params (List[OptionsQuoteParams]): A list of OptionsQuoteParams objects 
                                            specifying the options quotes to retrieve.

        Returns:
            Dict[str, pd.DataFrame]: A dictionary where each key is the option symbol (string) 
            for which quotes were requested, and each value is dictionary with "data" and "status_code"
            values. "data" is a pandas DataFrame containing the quote data for that option symbol, 
            and "status_code" is the HTTP status code for the request.
        """
        return self.client_async.get_options_quotes_parallel(params)
    
    def get_api_call_count(self):
        return self.client.api_calls + self.client_async.api_calls
    
    
                    
if __name__ == "__main__":
    # mdm = MarketDataManager(API_KEY)

    # df, status_code = mdm.get_stock_candles("AAPL", "1D", date(2020, 1, 1))
    # logger.debug(df)
    # logger.debug(f"Status Code: {status_code}")
    # assert 200 <= status_code < 300
    pass