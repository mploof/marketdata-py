import pytest
from datetime import date, datetime, timedelta
import pandas as pd
import os
from marketdata.manager import MarketDataManager
from marketdata.client_params import OptionsChainParams, OptionsQuoteParams, BasicParams, FromToParams
from loguru import logger

@pytest.fixture
def mdm():
    return MarketDataManager()

class TestMarketDataManager:
    
    def test_validate_resolution(self, mdm:MarketDataManager):
        """Test resolution validation"""
        # Valid resolutions
        assert mdm.validate_resolution("1D") == True
        assert mdm.validate_resolution("5M") == True
        assert mdm.validate_resolution("1W") == True
        assert mdm.validate_resolution("1H") == True
        assert mdm.validate_resolution("1Y") == True
        
        # Invalid resolutions
        assert mdm.validate_resolution("DD") == False
        assert mdm.validate_resolution("1X") == False
        assert mdm.validate_resolution("ABC") == False

    def test_get_stock_candles_basic(self, mdm:MarketDataManager):
        """Test basic stock candle retrieval"""
        symbols = ["SPY"]
        resolution = "1D"
        from_date = date.today() - timedelta(days=5)
        to_date = date.today()
        
        results = mdm.get_stock_candles(symbols, resolution, from_date, to_date)

        assert isinstance(results, dict)
        assert "SPY" in results.keys()
        assert isinstance(results["SPY"], pd.DataFrame)
        assert not results["SPY"].empty
        
        # Check column names
        expected_columns = ['t', 'o', 'h', 'l', 'c', 'v']
        assert all(col in results["SPY"].columns for col in expected_columns)

    def test_get_stock_candles_date_validation(self, mdm:MarketDataManager):
        """Test date validation in stock candle retrieval"""
        symbols = ["AAPL"]
        resolution = "1D"
        
        # Test future date handling
        future_date = date.today() + timedelta(days=10)
        results = mdm.get_stock_candles(symbols, resolution, date.today(), future_date)
        assert max(pd.to_datetime(results["AAPL"]['t'])).date() <= date.today()
        
        # Test from_date after to_date
        with pytest.raises(ValueError):
            mdm.get_stock_candles(symbols, resolution, date.today(), date.today() - timedelta(days=1))


    def test_get_stock_candles_multiple_symbols(self, mdm:MarketDataManager):
        """Test retrieving multiple symbols"""
        symbols = ["AAPL", "MSFT", "GOOGL"]
        resolution = "1D"
        from_date = date.today() - timedelta(days=5)
        
        results = mdm.get_stock_candles(symbols, resolution, from_date)
        
        assert len(results) == len(symbols)
        assert all(symbol in results for symbol in symbols)
        assert all(isinstance(results[symbol], pd.DataFrame) for symbol in symbols)

    def test_options_chain_retrieval(self, mdm:MarketDataManager):
        """Test options chain retrieval"""
        params = [
            OptionsChainParams(
                underlying="SPY",
                basic_params=BasicParams(),
                from_to_params=FromToParams()
            )
        ]
        
        results = mdm.get_option_chains(params)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_options_quotes_retrieval(self, mdm:MarketDataManager):
        """Test options quotes retrieval"""
        params = [
            OptionsQuoteParams(
                option_symbol="SPY230630C00400000",
                basic_params=BasicParams()
            )
        ]
        
        results = mdm.get_options_quotes(params)
        assert isinstance(results, dict)
        assert len(results) > 0
