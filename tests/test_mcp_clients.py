"""Tests for MCP clients (HTTP-based, mocked responses)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fu7ur3pr00f.mcp.base import MCPToolResult
from fu7ur3pr00f.mcp.factory import MCPClientFactory

# =============================================================================
# Factory Tests
# =============================================================================


class TestMCPClientFactory:
    def test_create_known_client(self):
        client = MCPClientFactory.create("financial")
        assert client is not None

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown MCP server"):
            MCPClientFactory.create("nonexistent")  # type: ignore[arg-type]

    def test_all_12_types_registered(self):
        clients = MCPClientFactory._get_clients()
        assert len(clients) == 12
        expected = {
            "github",
            "hn",
            "tavily",
            "jobspy",
            "remoteok",
            "himalayas",
            "jobicy",
            "devto",
            "stackoverflow",
            "weworkremotely",
            "remotive",
            "financial",
        }
        assert set(clients.keys()) == expected

    def test_availability_checkers_match_clients(self):
        clients = MCPClientFactory._get_clients()
        checkers = MCPClientFactory.AVAILABILITY_CHECKERS
        assert set(clients.keys()) == set(checkers.keys())

    def test_no_auth_clients_always_available(self):
        no_auth = [
            "remoteok",
            "himalayas",
            "jobicy",
            "devto",
            "weworkremotely",
            "remotive",
            "stackoverflow",
            "financial",
        ]
        for server_type in no_auth:
            assert (
                MCPClientFactory.is_available(server_type)  # type: ignore[arg-type]
                is True
            )


# =============================================================================
# Financial Client Tests (no auth, safe to test)
# =============================================================================


class TestFinancialClient:
    @pytest.mark.asyncio
    async def test_list_tools(self):
        from fu7ur3pr00f.mcp.financial_client import FinancialMCPClient

        client = FinancialMCPClient()
        tools = await client.list_tools()
        assert "convert_currency" in tools
        assert "get_ppp_factor" in tools

    @pytest.mark.asyncio
    async def test_convert_currency_mocked(self):
        from fu7ur3pr00f.mcp.financial_client import FinancialMCPClient

        client = FinancialMCPClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": "success",
            "rates": {"EUR": 0.92, "GBP": 0.79},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_ensure_client") as mock_ensure:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_ensure.return_value = mock_http

            result = await client._tool_convert_currency(
                {"amount": 100, "from_currency": "USD", "to_currency": "EUR"}
            )
        assert isinstance(result, MCPToolResult)
        assert not result.is_error


# =============================================================================
# RemoteOK Client Tests
# =============================================================================


class TestRemoteOKClient:
    @pytest.mark.asyncio
    async def test_list_tools(self):
        from fu7ur3pr00f.mcp.remoteok_client import RemoteOKMCPClient

        client = RemoteOKMCPClient()
        tools = await client.list_tools()
        assert len(tools) >= 1


# =============================================================================
# Himalayas Client Tests
# =============================================================================


class TestHimalayasClient:
    @pytest.mark.asyncio
    async def test_list_tools(self):
        from fu7ur3pr00f.mcp.himalayas_client import HimalayasMCPClient

        client = HimalayasMCPClient()
        tools = await client.list_tools()
        assert len(tools) >= 1


# =============================================================================
# DevTo Client Tests
# =============================================================================


class TestDevToClient:
    @pytest.mark.asyncio
    async def test_list_tools(self):
        from fu7ur3pr00f.mcp.devto_client import DevToMCPClient

        client = DevToMCPClient()
        tools = await client.list_tools()
        assert "search_articles" in tools


# =============================================================================
# StackOverflow Client Tests
# =============================================================================


class TestStackOverflowClient:
    @pytest.mark.asyncio
    async def test_list_tools(self):
        from fu7ur3pr00f.mcp.stackoverflow_client import StackOverflowMCPClient

        client = StackOverflowMCPClient()
        tools = await client.list_tools()
        assert len(tools) >= 1


# =============================================================================
# HN Client Tests
# =============================================================================


class TestHNClient:
    @pytest.mark.asyncio
    async def test_list_tools(self):
        from fu7ur3pr00f.mcp.hn_client import HackerNewsMCPClient

        client = HackerNewsMCPClient()
        tools = await client.list_tools()
        assert "search_hn" in tools or len(tools) >= 1
