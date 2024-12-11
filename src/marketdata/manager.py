import os
import re
from datetime import date, timedelta, datetime
from typing import Dict, List

from loguru import logger
import pandas as pd

from marketdata.client import MarketDataClient
from marketdata.client_async import MarketDataAsyncClient
from marketdata.client_params import OptionsQuoteParams, OptionsChainParams
       
class MarketDataManager:
    
    def __init__(self):
        self.client = MarketDataClient()
        self.client_async = MarketDataAsyncClient()
    
    def validate_resolution(self, resolution: str):
        # Validate the input resolution
        pattern = re.compile(r"(\d+[MHWDY]?\b)")
        if not pattern.match(resolution):
            logger.error("Invalid resolution format. Must be in the format <number>[MHDWY]")
            return False
        return True
    
    def get_stock_candles(
        self,
        symbols: List[str],
        resolution: str,
        from_date: date | datetime,
        to_date: date | datetime | None = None,
        friendly_names=True
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
        
        # Fetch data directly from API for all symbols
        fetched_data = self.client_async.get_stock_candles_parallel(symbols, resolution, from_date, to_date)
        print(fetched_data)
        # Process the fetched data
        for symbol, data in fetched_data.items():
            if data.get("s") == "no_data":
                logger.warning(f"No data available for {symbol}")
                results[symbol] = None
                continue
            elif data.get("s") == "error":
                logger.error(f"Error fetching data for {symbol}")
                logger.error(data)
                results[symbol] = None
                continue
            else:
                results[symbol] = data
        
        return results
    
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

if __name__ == "__main__":
    pass