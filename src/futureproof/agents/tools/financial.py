"""Financial tools for currency conversion and PPP comparison."""

import json

from langchain_core.tools import tool

from futureproof.mcp.pool import call_tool


def _financial(tool_name: str, args: dict) -> dict:
    """Call financial MCP via pool, return parsed result."""
    try:
        result = call_tool("financial", tool_name, args)
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
        from_currency: Source currency code (e.g., "ARS", "EUR")
        to_currency: Target currency code (default: "USD")

    Never guess or fabricate exchange rates — always use this
    tool. Supports 170+ currencies including ARS, BRL, MXN,
    CLP, COP, PEN.
    """
    data = _financial(
        "convert_currency",
        {
            "amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
        },
    )

    if "error" in data:
        return f"Currency conversion error: {data['error']}"

    converted = data.get("converted", 0)
    rate = data.get("rate", 0)
    date = data.get("date", "")

    return (
        f"{from_currency} {amount:,.2f} = "
        f"{to_currency} {converted:,.2f}\n"
        f"Rate: 1 {from_currency} = {rate} {to_currency}\n"
        f"Updated: {date}"
    )


@tool
def compare_salary_ppp(
    salary: float,
    currency: str,
    country: str,
    target_countries: list[str] | None = None,
) -> str:
    """Compare a salary across countries using exchange rates and PPP.

    Args:
        salary: Annual salary amount
        currency: Currency code of the salary (e.g., "ARS", "EUR")
        country: Country where the salary is earned
        target_countries: Countries to compare purchasing power
            against. Defaults to ["United States"] if not provided.
            Pass multiple countries for relocation comparison
            (e.g., ["United States", "Spain", "Germany"]).

    Shows the nominal USD conversion and purchasing-power-adjusted
    equivalents for each target country. Use this for cross-country
    salary comparison — it reveals the real value of a salary beyond
    just the exchange rate.
    """
    targets = target_countries or ["United States"]

    # Step 1: Convert to USD
    forex = _financial(
        "convert_currency",
        {
            "amount": salary,
            "from_currency": currency,
            "to_currency": "USD",
        },
    )

    if "error" in forex:
        return f"Currency conversion error: {forex['error']}"

    nominal_usd = forex.get("converted", 0)
    rate = forex.get("rate", 0)

    # Step 2: Get PPP factor for source country
    source_ppp = _financial(
        "get_ppp_factor", {"country": country},
    )
    source_ratio = (
        source_ppp.get("ppp_ratio")
        if "error" not in source_ppp
        else None
    )

    parts = [
        f"**Salary comparison: "
        f"{currency} {salary:,.0f} ({country})**",
        "",
        f"Nominal USD value: **USD {nominal_usd:,.2f}**",
        f"Exchange rate: 1 {currency} = {rate} USD",
    ]

    if source_ratio is None:
        parts.append(
            f"\nNote: PPP data not available for {country}."
            f" Nominal conversion only."
        )
        return "\n".join(parts)

    source_year = source_ppp.get("year", "")

    # Step 3: Get PPP for each target and build comparison
    comparisons: list[tuple[str, float]] = []
    failed: list[str] = []

    for target in targets:
        target_ppp = _financial(
            "get_ppp_factor", {"country": target},
        )
        target_ratio = (
            target_ppp.get("ppp_ratio")
            if "error" not in target_ppp
            else None
        )
        if target_ratio is not None:
            ppp_adjusted = nominal_usd * (
                target_ratio / source_ratio
            )
            comparisons.append((target, ppp_adjusted))
        else:
            failed.append(target)

    if comparisons:
        parts.extend([
            "", "**Purchasing power equivalents:**", "",
        ])

        # Table header
        parts.append(
            "| Country | PPP Equivalent | vs Nominal |"
        )
        parts.append(
            "|---------|---------------|------------|"
        )

        for target, ppp_adjusted in comparisons:
            multiplier = (
                ppp_adjusted / nominal_usd
                if nominal_usd
                else 0
            )
            parts.append(
                f"| {target} | USD {ppp_adjusted:,.0f} "
                f"| {multiplier:.1f}x |"
            )

        parts.extend([
            "",
            f"This means {currency} {salary:,.0f} in "
            f"{country} buys roughly what "
            f"USD {comparisons[0][1]:,.0f} buys in "
            f"{comparisons[0][0]}.",
            f"(PPP data: {source_year})",
        ])

    if failed:
        parts.append(
            f"\nNo PPP data available for: "
            f"{', '.join(failed)}"
        )

    return "\n".join(parts)
