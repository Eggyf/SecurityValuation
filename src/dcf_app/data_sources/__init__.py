"""Fuentes externas v2 (EDGAR, mercado, tasas, Damodaran) y caché en disco."""

from dcf_app.data_sources.base import (
    DataSourceConfigError,
    DataSourceError,
    DataSourceResult,
    FilingsProvider,
    InvalidTickerError,
    MarketDataProvider,
    NetworkError,
    RateLimitError,
    RatesProvider,
)
from dcf_app.data_sources.cache import CacheManager, CacheTTL
from dcf_app.data_sources.damodaran import DamodaranProvider, get_damodaran_beta, get_damodaran_erp
from dcf_app.data_sources.edgar import (
    EdgarProvider,
    edgar_provider,
    get_cik_from_ticker,
    get_edgar_provider,
    get_latest_filing,
    get_latest_filing_info,
)
from dcf_app.data_sources.market import FmpMarketProvider, get_market_data
from dcf_app.data_sources.rates import (
    FredRatesProvider,
    get_risk_free_rate,
    get_risk_free_rate_full,
)

__all__ = [
    "CacheManager",
    "CacheTTL",
    "DamodaranProvider",
    "DataSourceConfigError",
    "DataSourceError",
    "DataSourceResult",
    "EdgarProvider",
    "FilingsProvider",
    "FmpMarketProvider",
    "FredRatesProvider",
    "InvalidTickerError",
    "MarketDataProvider",
    "NetworkError",
    "RateLimitError",
    "RatesProvider",
    "edgar_provider",
    "get_cik_from_ticker",
    "get_damodaran_beta",
    "get_damodaran_erp",
    "get_edgar_provider",
    "get_latest_filing",
    "get_latest_filing_info",
    "get_market_data",
    "get_risk_free_rate",
    "get_risk_free_rate_full",
]
