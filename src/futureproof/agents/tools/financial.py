"""Financial tools for currency conversion and purchasing power comparison."""

import json

from langchain_core.tools import tool

from ._async import run_async


async def _call_financial(tool_name: str, args: dict) -> dict:
    """Call a financial MCP client tool and return parsed result."""
    from futureproof.mcp.factory import MCPClientFactory

    client = MCPClientFactory.create("financial")
    try:
        async with client:
            result = await client.call_tool(tool_name, args)
            if result.is_error:
                return {"error": result.error_message}
            return json.loads(result.content)
    except Exception as e:
        return {"error": f"{tool_name} failed: {e}"}


@tool
def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str = "USD",
) -> str:
    """Convert between currencies using real-time exchange rates.

    Args:
        amount: Amount to convert
        from_currency: Source currency code (e.g., "ARS", "EUR", "BRL")
        to_currency: Target currency code (default: "USD")

    Never guess or fabricate exchange rates — always use this tool.
    Supports 170+ currencies including ARS, BRL, MXN, CLP, COP, PEN.
    """
    data = run_async(
        _call_financial(
            "convert_currency",
            {
                "amount": amount,
                "from_currency": from_currency,
                "to_currency": to_currency,
            },
        )
    )

    if "error" in data:
        return f"Currency conversion error: {data['error']}"

    converted = data.get("converted", 0)
    rate = data.get("rate", 0)
    date = data.get("date", "")

    return (
        f"{from_currency} {amount:,.2f} = {to_currency} {converted:,.2f}\n"
        f"Rate: 1 {from_currency} = {rate} {to_currency}\n"
        f"Updated: {date}"
    )


@tool
def compare_salary_ppp(
    salary: float,
    currency: str,
    country: str,
    target_country: str = "United States",
) -> str:
    """Compare a salary across countries using both exchange rates and PPP.

    Args:
        salary: Annual salary amount
        currency: Currency code of the salary (e.g., "ARS", "EUR")
        country: Country where the salary is earned (e.g., "Argentina")
        target_country: Country to compare purchasing power against
            (default: "United States")

    Shows both the nominal USD conversion and the purchasing-power-adjusted
    equivalent. Use this for cross-country salary comparison — it reveals
    the real value of a salary beyond just the exchange rate.
    """
    # Step 1: Convert to USD
    forex = run_async(
        _call_financial(
            "convert_currency",
            {"amount": salary, "from_currency": currency, "to_currency": "USD"},
        )
    )

    if "error" in forex:
        return f"Currency conversion error: {forex['error']}"

    nominal_usd = forex.get("converted", 0)
    rate = forex.get("rate", 0)

    # Step 2: Get PPP factor for source country
    source_ppp = run_async(
        _call_financial("get_ppp_factor", {"country": country})
    )

    # Step 3: Get PPP factor for target country
    target_ppp = run_async(
        _call_financial("get_ppp_factor", {"country": target_country})
    )

    parts = [
        f"**Salary comparison: {currency} {salary:,.0f} ({country})**",
        "",
        f"Nominal conversion: USD {nominal_usd:,.2f}",
        f"Exchange rate: 1 {currency} = {rate} USD",
    ]

    source_ratio = source_ppp.get("ppp_ratio") if "error" not in source_ppp else None
    target_ratio = target_ppp.get("ppp_ratio") if "error" not in target_ppp else None

    if source_ratio is not None and target_ratio is not None:
        # PPP adjustment: nominal_usd * (target_ppp / source_ppp)
        ppp_adjusted = nominal_usd * (target_ratio / source_ratio)
        source_year = source_ppp.get("year", "")
        parts.extend([
            "",
            f"**Purchasing power equivalent in {target_country}:"
            f" USD {ppp_adjusted:,.0f}**",
            "",
            f"This means {currency} {salary:,.0f} in {country} buys"
            f" roughly what USD {ppp_adjusted:,.0f} buys in"
            f" {target_country}.",
            f"(PPP data: {source_year})",
        ])
    elif source_ratio is not None:
        parts.extend([
            "",
            f"PPP info: {source_ppp.get('interpretation', 'N/A')}",
            f"(No PPP data available for {target_country})",
        ])
    else:
        parts.append(
            f"\nNote: PPP data not available for {country}."
            f" Nominal conversion only."
        )

    return "\n".join(parts)
