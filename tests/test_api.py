"""Tests for the Intervals.icu API client."""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import aiohttp

from custom_components.intervals_icu.api import (
    IntervalsIcuApiError,
    IntervalsIcuAuthError,
    IntervalsIcuClient,
    IntervalsIcuNotFoundError,
)


class TestIntervalsIcuClient(unittest.IsolatedAsyncioTestCase):
    """Test the Intervals.icu API client."""

    def setUp(self) -> None:
        self.session = MagicMock(spec=aiohttp.ClientSession)
        self.client = IntervalsIcuClient(
            session=self.session,
            athlete_id="i12345",
            api_key="test-api-key",
        )

    async def test_auth_uses_basic_auth(self) -> None:
        """Test that authentication uses Basic Auth with API_KEY username."""
        self.assertEqual(self.client._auth.login, "API_KEY")
        self.assertEqual(self.client._auth.password, "test-api-key")

    async def test_get_athlete(self) -> None:
        """Test fetching athlete profile."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"id": "i12345", "name": "Test Athlete", "icu_ftp": 250}
        )
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        self.session.request.return_value = mock_response

        result = await self.client.get_athlete()

        self.assertEqual(result["name"], "Test Athlete")
        self.assertEqual(result["icu_ftp"], 250)
        self.session.request.assert_called_once()
        call_args = self.session.request.call_args
        self.assertEqual(call_args[0][0], "GET")
        self.assertIn("/athlete/i12345", call_args[0][1])

    async def test_get_wellness(self) -> None:
        """Test fetching wellness data for a specific date."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"id": "2026-04-12", "weight": 75.0, "restingHR": 52}
        )
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        self.session.request.return_value = mock_response

        result = await self.client.get_wellness(date(2026, 4, 12))

        self.assertEqual(result["weight"], 75.0)
        self.assertEqual(result["restingHR"], 52)
        call_args = self.session.request.call_args
        self.assertIn("/wellness/2026-04-12", call_args[0][1])

    async def test_auth_error_raises(self) -> None:
        """Test that a 401 response raises IntervalsIcuAuthError."""
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        self.session.request.return_value = mock_response

        with self.assertRaises(IntervalsIcuAuthError):
            await self.client.get_athlete()

    async def test_not_found_raises(self) -> None:
        """Test that a 404 response raises IntervalsIcuNotFoundError."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        self.session.request.return_value = mock_response

        with self.assertRaises(IntervalsIcuNotFoundError):
            await self.client.get_wellness(date(2026, 4, 12))

    async def test_get_activities(self) -> None:
        """Test fetching activities."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value=[{"id": "i12345:1", "name": "Morning Ride", "type": "Ride"}]
        )
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        self.session.request.return_value = mock_response

        result = await self.client.get_activities(limit=5)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Morning Ride")
        call_args = self.session.request.call_args
        self.assertIn("/activities", call_args[0][1])

    async def test_get_events(self) -> None:
        """Test fetching events."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value=[
                {"id": 1, "name": "Tempo Run", "category": "WORKOUT", "type": "Run"}
            ]
        )
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        self.session.request.return_value = mock_response

        result = await self.client.get_events(
            oldest=date(2026, 4, 12), newest=date(2026, 4, 19)
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Tempo Run")

    async def test_get_pace_curves(self) -> None:
        """Test fetching pace curves."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "list": [
                    {
                        "id": "all",
                        "type": "PACE",
                        "distance": [400.0, 800.0, 1500.0],
                        "values": [72, 160, 320],
                        "activity_id": ["i12345:1", "i12345:2", "i12345:3"],
                    }
                ],
                "activities": {},
            }
        )
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        self.session.request.return_value = mock_response

        result = await self.client.get_pace_curves(sport="Run", curves="all")

        self.assertEqual(result["list"][0]["values"], [72, 160, 320])
        call_args = self.session.request.call_args
        self.assertIn("/athlete/i12345/pace-curves.json", call_args[0][1])
        self.assertEqual(call_args[1]["params"], {"type": "Run", "curves": "all"})

    async def test_connection_error_raises(self) -> None:
        """Test that connection errors raise IntervalsIcuApiError."""
        self.session.request.side_effect = aiohttp.ClientError("Connection failed")

        with self.assertRaises(IntervalsIcuApiError):
            await self.client.get_athlete()


if __name__ == "__main__":
    unittest.main()
