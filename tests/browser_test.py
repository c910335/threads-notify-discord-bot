"""Unit tests for Playwright browser proxy manager."""

# pylint: disable=protected-access

import unittest
from unittest import mock

import browser


class BrowserTest(unittest.IsolatedAsyncioTestCase):
    """Test cases for the Browser manager in browser.py."""

    async def test_start_stop(self) -> None:
        """Verifies start() and close() manage playwright instances."""
        mock_playwright = mock.MagicMock()
        mock_browser = mock.MagicMock()

        mock_playwright.chromium = mock.MagicMock()
        mock_playwright.chromium.launch = mock.AsyncMock(
            return_value=mock_browser
        )
        mock_browser.close = mock.AsyncMock()
        mock_playwright.stop = mock.AsyncMock()

        async_pw_mock = mock.MagicMock()
        async_pw_mock.start = mock.AsyncMock(return_value=mock_playwright)

        mgr = browser.Browser()
        with mock.patch(
            "browser.async_api.async_playwright", return_value=async_pw_mock
        ):
            # 1. Start browser
            await mgr.start()
            self.assertIsNotNone(mgr._raw_browser)
            self.assertIsNotNone(mgr._playwright)
            mock_playwright.chromium.launch.assert_called_once()
            async_pw_mock.start.assert_called_once()

            # Starting again should be a no-op
            await mgr.start()
            self.assertEqual(mock_playwright.chromium.launch.call_count, 1)

            # 2. Stop browser
            await mgr.close()
            self.assertIsNone(mgr._raw_browser)
            self.assertIsNone(mgr._playwright)
            mock_browser.close.assert_called_once()
            mock_playwright.stop.assert_called_once()

            # Stopping again should be a no-op
            await mgr.close()
            self.assertEqual(mock_browser.close.call_count, 1)

    async def test_new_context(self) -> None:
        """Verifies new_context creates an isolated BrowserContext."""
        mock_playwright = mock.MagicMock()
        mock_browser = mock.MagicMock()
        mock_context = mock.MagicMock()

        mock_playwright.chromium = mock.MagicMock()
        mock_playwright.chromium.launch = mock.AsyncMock(
            return_value=mock_browser
        )
        mock_browser.new_context = mock.AsyncMock(return_value=mock_context)

        async_pw_mock = mock.MagicMock()
        async_pw_mock.start = mock.AsyncMock(return_value=mock_playwright)

        mgr = browser.Browser()
        with mock.patch(
            "browser.async_api.async_playwright", return_value=async_pw_mock
        ):
            # Test lazy initialization inside new_context
            ctx = await mgr.new_context()
            self.assertEqual(ctx, mock_context)
            mock_browser.new_context.assert_called_once()
            # Assert default options are passed to new_context
            mock_browser.new_context.assert_called_with(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 1000},
                locale="en-US",
            )


if __name__ == "__main__":
    unittest.main()
