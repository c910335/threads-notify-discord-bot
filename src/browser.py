"""Playwright browser instance proxy/wrapper."""

from playwright import async_api


class Browser:
    """Wraps a Playwright browser instance, implementing new_context and close."""

    def __init__(self) -> None:
        self._playwright_context: async_api.PlaywrightContextManager | None = None
        self._raw_browser: async_api.Browser | None = None

    async def start(self) -> None:
        """Starts Playwright and launches the Chromium browser."""
        if self._raw_browser is not None:
            return

        self._playwright_context = async_api.async_playwright()
        playwright = await self._playwright_context.start()
        self._raw_browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

    async def close(self) -> None:
        """Closes the browser and stops Playwright."""
        if self._raw_browser is not None:
            await self._raw_browser.close()
            self._raw_browser = None
        if self._playwright_context is not None:
            # pylint: disable=no-member
            await self._playwright_context.stop()
            self._playwright_context = None

    async def new_context(self, **kwargs) -> async_api.BrowserContext:
        """Creates a new BrowserContext using default or custom parameters.

        Args:
            **kwargs: Custom parameters passed to the browser context creation.

        Returns:
            A new BrowserContext instance.
        """
        if self._raw_browser is None:
            await self.start()

        assert self._raw_browser is not None

        options = {
            "user_agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "viewport": {"width": 1280, "height": 1000},
            "locale": "en-US",
        }
        options.update(kwargs)
        return await self._raw_browser.new_context(**options)
