"""Financial data MCP client for currency conversion and PPP comparison.

Uses two free APIs (no authentication required):
- ExchangeRate-API: Real-time exchange rates for 170+ currencies
  https://www.exchangerate-api.com/docs/free
- World Bank: Purchasing Power Parity (PPP) conversion factors
  https://api.worldbank.org/v2/
"""

import time
from typing import Any

from ..config import settings
from .base import MCPToolResult
from .http_client import HTTPMCPClient

# Module-level caches (MCP clients are created/destroyed per tool call)
_forex_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_ppp_cache: dict[str, tuple[float, float, str]] = {}  # code -> (ts, ratio, year)

_PPP_CACHE_TTL = 24 * 3600  # 24 hours (annual data)

# Country name -> ISO 3166-1 alpha-3 for World Bank API
_COUNTRY_CODES: dict[str, str] = {
    "argentina": "ARG",
    "australia": "AUS",
    "austria": "AUT",
    "belgium": "BEL",
    "brazil": "BRA",
    "canada": "CAN",
    "chile": "CHL",
    "china": "CHN",
    "colombia": "COL",
    "czech republic": "CZE",
    "denmark": "DNK",
    "finland": "FIN",
    "france": "FRA",
    "germany": "DEU",
    "hungary": "HUN",
    "india": "IND",
    "indonesia": "IDN",
    "ireland": "IRL",
    "israel": "ISR",
    "italy": "ITA",
    "japan": "JPN",
    "mexico": "MEX",
    "netherlands": "NLD",
    "norway": "NOR",
    "peru": "PER",
    "poland": "POL",
    "portugal": "PRT",
    "romania": "ROU",
    "south korea": "KOR",
    "spain": "ESP",
    "sweden": "SWE",
    "switzerland": "CHE",
    "united kingdom": "GBR",
    "united states": "USA",
    "uruguay": "URY",
    # Short forms
    "us": "USA",
    "usa": "USA",
    "uk": "GBR",
}

# ISO alpha-2 -> alpha-3
_ALPHA2_TO_ALPHA3: dict[str, str] = {
    "AR": "ARG",
    "AU": "AUS",
    "AT": "AUT",
    "BE": "BEL",
    "BR": "BRA",
    "CA": "CAN",
    "CL": "CHL",
    "CN": "CHN",
    "CO": "COL",
    "CZ": "CZE",
    "DK": "DNK",
    "FI": "FIN",
    "FR": "FRA",
    "DE": "DEU",
    "HU": "HUN",
    "IN": "IND",
    "ID": "IDN",
    "IE": "IRL",
    "IL": "ISR",
    "IT": "ITA",
    "JP": "JPN",
    "MX": "MEX",
    "NL": "NLD",
    "NO": "NOR",
    "PE": "PER",
    "PL": "POL",
    "PT": "PRT",
    "RO": "ROU",
    "KR": "KOR",
    "ES": "ESP",
    "SE": "SWE",
    "CH": "CHE",
    "GB": "GBR",
    "US": "USA",
    "UY": "URY",
}


def resolve_country_code(country: str) -> str:
    """Resolve country name or code to ISO 3166-1 alpha-3.

    Handles full names ("Argentina"), alpha-2 ("AR"), and alpha-3 ("ARG").
    """
    stripped = country.strip()
    upper = stripped.upper()

    # Already alpha-3
    if len(upper) == 3 and upper.isalpha():
        return upper

    # Alpha-2 lookup
    if len(upper) == 2 and upper.isalpha():
        return _ALPHA2_TO_ALPHA3.get(upper, upper)

    # Full name lookup (case-insensitive)
    return _COUNTRY_CODES.get(stripped.lower(), upper[:3])


class FinancialMCPClient(HTTPMCPClient):
    """Financial data client for forex and PPP.

    Free APIs, no authentication required.
    - Exchange rates: 170+ currencies including ARS, BRL, MXN
    - PPP data: World Bank annual purchasing power parity ratios
    """

    FOREX_URL = "https://open.er-api.com/v6/latest"
    PPP_URL = "https://api.worldbank.org/v2/country"
    PPP_INDICATOR = "PA.NUS.PPPC.RF"

    async def list_tools(self) -> list[str]:
        """List available tools."""
        return ["convert_currency", "get_ppp_factor"]

    async def _tool_convert_currency(
        self, args: dict[str, Any]
    ) -> MCPToolResult:
        """Convert between currencies using real-time rates."""
        amount = float(args.get("amount", 1))
        from_cur = args.get("from_currency", "USD").upper()
        to_cur = args.get("to_currency", "USD").upper()

        client = self._ensure_client()
        now = time.time()

        # Check cache
        cached = _forex_cache.get(from_cur)
        if cached and (now - cached[0]) < settings.forex_cache_hours * 3600:
            data = cached[1]
        else:
            response = await client.get(f"{self.FOREX_URL}/{from_cur}")
            response.raise_for_status()
            data = response.json()

            if data.get("result") != "success":
                return self._format_response(
                    {"error": f"Exchange rate API error: {data.get('result')}"},
                    data,
                    "convert_currency",
                )
            _forex_cache[from_cur] = (now, data)

        rates = data.get("rates", {})
        if to_cur not in rates:
            return self._format_response(
                {"error": f"Currency '{to_cur}' not supported"},
                data,
                "convert_currency",
            )

        rate = rates[to_cur]
        converted = amount * rate

        output = {
            "from": from_cur,
            "to": to_cur,
            "amount": amount,
            "converted": round(converted, 2),
            "rate": rate,
            "date": data.get("time_last_update_utc", ""),
        }
        return self._format_response(output, data, "convert_currency")

    async def _tool_get_ppp_factor(
        self, args: dict[str, Any]
    ) -> MCPToolResult:
        """Get PPP conversion factor for a country."""
        country = args.get("country", "")
        code = resolve_country_code(country)

        now = time.time()

        # Check cache
        cached = _ppp_cache.get(code)
        if cached and (now - cached[0]) < _PPP_CACHE_TTL:
            ppp_ratio, year = cached[1], cached[2]
            output = {
                "country": country,
                "country_code": code,
                "ppp_ratio": ppp_ratio,
                "year": year,
                "interpretation": (
                    f"Price level is {ppp_ratio * 100:.1f}% of the US"
                ),
            }
            return self._format_response(output, {}, "get_ppp_factor")

        client = self._ensure_client()
        url = f"{self.PPP_URL}/{code}/indicator/{self.PPP_INDICATOR}"
        response = await client.get(
            url, params={"format": "json", "per_page": 5}
        )
        response.raise_for_status()
        data = response.json()

        # World Bank returns [metadata, data_array]
        entries = data[1] if len(data) > 1 and data[1] else []

        # Find most recent non-null value
        ppp_ratio = None
        year = None
        for entry in entries:
            if entry.get("value") is not None:
                ppp_ratio = entry["value"]
                year = entry.get("date", "")
                break

        if ppp_ratio is not None:
            _ppp_cache[code] = (now, ppp_ratio, year)

        if ppp_ratio is None:
            output = {
                "country": country,
                "country_code": code,
                "ppp_ratio": None,
                "year": None,
                "interpretation": "No PPP data available",
            }
        else:
            output = {
                "country": country,
                "country_code": code,
                "ppp_ratio": ppp_ratio,
                "year": year,
                "interpretation": (
                    f"Price level is {ppp_ratio * 100:.1f}% of the US"
                ),
            }

        return self._format_response(output, data, "get_ppp_factor")
