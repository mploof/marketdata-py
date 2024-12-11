"""
marketdata.app API Client
"""
import os
import sys
from time import time
from urllib.parse import urlencode
import datetime


import pandas as pd
from loguru import logger
import pandas as pd

import aiohttp
from aiohttp import TCPConnector, ClientSession
import asyncio
from typing import Any, Dict, List, Optional, Tuple
import datetime

from marketdata import BasicParams, FromToParams
from marketdata import MARKET_DATA_API_KEY
from marketdata.client_params import OptionsChainParams, OptionsQuoteParams

BASE_URL = 'https://api.marketdata.app/v1/'

class MarketDataAsyncClient:
    
    def __init__(self) -> None:
        self.BASE_URL = 'https://api.marketdata.app/v1/'
        self.api_key = MARKET_DATA_API_KEY
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

    async def handle_response_async(self, response, output):
        try:
            if output == "raw":
                try:
                    return await response.json(), response.status
                except aiohttp.client_exceptions.ContentTypeError as e:
                    logger.error(f"Error getting response: {e}")
                    return await response.text(), response.status
            elif output == "dataframe":
                if 200 <= response.status < 300:
                    json_data = await response.json()
                    df = pd.DataFrame(json_data)
                    try:
                        df.drop(columns=['s'], inplace=True)
                    except KeyError:
                        pass
                    return df, response.status
                else:
                    try:
                        return await response.json(), response.status
                    except Exception as e:
                        logger.error(f"Error getting response: {e}")
                        logger.error(await response.text())
                        exit()
        # Handle the case where the response is not JSON
        except ValueError:
            return await response.text(), response.status
        
        
    # /v1/options/chain/{underlying}/
    async def get_options_chain(self, params: OptionsChainParams):
        """Get options chain for a symbol asynchronously."""

        url = BASE_URL + f'options/chain/{params.underlying}/'
        api_params = params.to_dict()
        if params.basic_params:
            api_params.update(params.basic_params.params)
        if params.from_to_params:
            api_params.update(params.from_to_params.params)

        async with aiohttp.ClientSession() as session:
            for key, value in api_params.items():
                if isinstance(value, bool):
                    api_params[key] = str(value).lower()
                elif isinstance(value, datetime.date):
                    api_params[key] = value.strftime('%Y-%m-%d')
            
            if 'basic_params' in api_params:
                if 'dateformat' in api_params['basic_params']:
                    api_params['dateformat'] = api_params['basic_params']['dateformat']
                if 'date' in api_params['basic_params']:
                    api_params['date'] = api_params['basic_params']['date']
                if 'format' in api_params['basic_params']:
                    api_params['format'] = api_params['basic_params']['format']
                if 'headers' in api_params['basic_params']:
                    api_params['headers'] = api_params['basic_params']['headers']
                if 'limit' in api_params['basic_params']:
                    api_params['limit'] = api_params['basic_params']['limit']
                del api_params['basic_params']
                
            url = f"{url}?{urlencode(api_params)}"
            async with session.get(url, headers=self.headers) as response:
                url_with_token = url + '&token=' + self.api_key
                # logger.debug(f"API call (Option Chain): {url_with_token}")
                data, status_code = await self.handle_response_async(response, params.output)
                if not 200 <= status_code < 300:
                    # logger.error(f"Error fetching options chain for {params.underlying}. Status code: {status_code}")
                    pass

        if isinstance(data, dict) and 's' in data and data.get('s') == 'error':
            logger.error(data)
            return data
        else:
            return data
        

    # /v1/options/quotes/{optionSymbol}/
    async def get_options_quotes(self, params: OptionsQuoteParams):

        url = BASE_URL + f'options/quotes/{params.option_symbol}/'
        api_params = {}
        if params.basic_params:
            api_params.update(params.basic_params.params)
        if params.from_to_params:
            api_params.update(params.from_to_params.params)
        if params.columns:
            api_params['columns'] = params.columns

        async with aiohttp.ClientSession() as session:
            for key, value in api_params.items():
                if isinstance(value, bool):
                    api_params[key] = str(value).lower()
                if isinstance(value, datetime.date):
                    api_params[key] = value.strftime('%Y-%m-%d')
            url_with_params = url + '?' + '&'.join([f'{k}={v}' for k, v in api_params.items()])
            # logger.debug(f"API call (Options Quotes): {url_with_params}")
            async with session.get(url, headers=self.headers, params=api_params) as response:
                data, status_code = await self.handle_response_async(response, params.output)
                if not 200 <= status_code < 300:
                    logger.error(f"Error fetching options quotes for {params.option_symbol}. Status code: {status_code}")
                
        return data


    # /v1/stocks/candles/{resolution}/{symbol}/
    async def get_stock_candles(
        self,
        symbol: str,
        resolution: str = "1D",
        basic_params: Optional[BasicParams] = None,
        from_to_params: Optional[FromToParams] = None,
        columns: Optional[str] = None,
        exchange: Optional[str] = None,
        extended_hours: bool = False,
        exchange_country: str = "US",
        adjust_splits: Optional[bool] = None,
        adjust_dividends: Optional[bool] = None,
        output: str = "dataframe"
    ):
        """Get historical stock candles for a symbol asynchronously."""
        
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

        async with aiohttp.ClientSession() as session:
            for key, value in params.items():
                # Convert boolean values to lowercase strings
                if isinstance(value, bool):
                    value = str(value).lower()
                    params[key] = value
                    
            async with session.get(url, headers=self.headers, params=params) as response:
                # Construct full url with params for logging
                url_with_token = url + '&' + self.api_key
                logger.debug(f"API call (Candles): {url_with_token}")
                data, status_code = await self.handle_response_async(response, output)
                if not 200 <= status_code < 300:
                    logger.error(f"Error fetching candles for {symbol}. Status code: {status_code}")
                return data
            
    def get_stock_candles_parallel(self, symbols: List[str], resolution: str, from_date: datetime.date, to_date: datetime.date, max_concurrent: int = 50) -> Dict[str, pd.DataFrame | None]:
            async def fetch_stock(session, semaphore, symbol) -> Tuple[str, Any, int]:
                async with semaphore:
                    try:
                        data, status = await self.get_stock_candles(
                            symbol,
                            resolution=resolution,
                            basic_params=BasicParams(dateformat="timestamp", format="json"),
                            from_to_params=FromToParams(from_date=from_date, to_date=to_date),
                        )
                        return symbol, data, status
                    except Exception as e:
                        return symbol, None, str(e)

            async def get_price_histories_async() -> Dict[str, Any]:
                connector = TCPConnector(limit=max_concurrent)
                async with ClientSession(connector=connector) as session:
                    semaphore = asyncio.Semaphore(max_concurrent)
                    tasks = [fetch_stock(session, semaphore, symbol) for symbol in symbols]
                    return await asyncio.gather(*tasks)

            if sys.platform.startswith('win'):
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

            start_time = time()
            results = asyncio.run(get_price_histories_async())
            end_time = time()
            execution_time = end_time - start_time

            output = {}
            for symbol, data, status in results:
                if data is not None:
                    output[symbol] = data
                    logger.debug(f"{symbol}: Successfully fetched candles. Status: {status}")
                else:
                    output[symbol] = None
                    logger.warning(f"{symbol}: Failed to fetch candles. Status: {status}")

            logger.debug(f"Fetched candles for {len(symbols)} symbols in {execution_time:.2f} seconds")
            return output   
    
    def get_options_chains_parallel(self, params_list: List[OptionsChainParams], max_concurrent: int = 50) -> List[dict]:
        async def fetch_options_chain(session, params: OptionsChainParams):
            result = await self.get_options_chain(params)
            return params.id, params.underlying, result

        async def get_all_options_chains():
            connector = TCPConnector(limit=max_concurrent)
            async with ClientSession(connector=connector) as session:
                semaphore = asyncio.Semaphore(max_concurrent)
                async def bounded_fetch(params):
                    async with semaphore:
                        return await fetch_options_chain(session, params)
                tasks = [bounded_fetch(params) for params in params_list]
                return await asyncio.gather(*tasks)

        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        results = asyncio.run(get_all_options_chains())
        
        output = []
        for r in results:            
            _, _, data = r
            if data is not None:
                output.append(data)
        return output
    
    def get_options_quotes_parallel(self, params_list: List[OptionsQuoteParams], max_concurrent: int = 50) -> Dict[str, Any]:
        """Get options quotes for multiple option symbols asynchronously.

        Args:
            params_list (List[OptionsQuoteParams]): List of OptionsQuoteParams objects.
            max_concurrent (int, optional): Maximum number of concurrent requests. Defaults to 50.

        Returns:
            Dict[str, Any]: Dictionary containing the option symbol as the key and "data" and "status code" in a dict as the value.
        """
        async def fetch_options_quote(semaphore, params: OptionsQuoteParams):
            async with semaphore:
                result = await self.get_options_quotes(params)
                return params.option_symbol, result

        async def get_all_options_quotes():
            semaphore = asyncio.Semaphore(max_concurrent)
            tasks = [fetch_options_quote(semaphore, params) for params in params_list]
            return await asyncio.gather(*tasks)

        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        results = asyncio.run(get_all_options_quotes())

        output = {}
        for option_symbol, data in results:
            output[option_symbol] = data
        return output
