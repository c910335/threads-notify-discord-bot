# pylint: disable=missing-module-docstring,protected-access

import unittest
from unittest import mock

import scraper


class ScraperTest(unittest.IsolatedAsyncioTestCase):
    """Test cases for Threads profile HTML and state structure parsing."""

    def test_find_key_in_dict(self) -> None:
        """Verifies recursion find key searches dictionaries and lists correctly."""
        data_dict = {
            "a": 1,
            "b": [
                {"c": 2, "target": "found1"},
                {"d": {"target": "found2"}},
            ],
            "target": "found3",
        }
        results = scraper.find_key_in_dict(data_dict, "target")
        self.assertEqual(len(results), 3)
        self.assertIn("found1", results)
        self.assertIn("found2", results)
        self.assertIn("found3", results)

    def test_extract_media_single_image(self) -> None:
        """Verifies media candidate URL extraction for single images."""
        post_data = {
            "image_versions2": {
                "candidates": [
                    {"url": "https://example.com/img1_large.jpg"},
                    {"url": "https://example.com/img1_small.jpg"},
                ]
            }
        }
        urls = scraper._extract_media(post_data)  # pylint: disable=protected-access
        self.assertEqual(urls, ["https://example.com/img1_large.jpg"])

    def test_extract_media_carousel(self) -> None:
        """Verifies media candidate URL extraction for carousels."""
        post_data = {
            "carousel_media": [
                {
                    "image_versions2": {
                        "candidates": [{"url": "https://example.com/slide1.jpg"}]
                    }
                },
                {
                    "image_versions2": {
                        "candidates": [{"url": "https://example.com/slide2.jpg"}]
                    }
                },
            ]
        }
        urls = scraper._extract_media(post_data)  # pylint: disable=protected-access
        self.assertEqual(
            urls, ["https://example.com/slide1.jpg", "https://example.com/slide2.jpg"]
        )

    def test_parse_post_correctly(self) -> None:
        """Verifies parsing a raw GraphQL post into a structured PostDict."""
        raw_post = {
            "id": "333444",
            "code": "CodeABC",
            "taken_at": 1700000000,
            "user": {
                "username": "tester",
                "full_name": "Test User",
            },
            "caption": {
                "text": "Check this out!",
            },
            "video_versions": [
                {"url": "https://example.com/video.mp4"}
            ],
        }
        parsed = scraper._parse_post(raw_post)  # pylint: disable=protected-access
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["id"], "333444")
        self.assertEqual(parsed["code"], "CodeABC")
        self.assertEqual(parsed["username"], "tester")
        self.assertEqual(parsed["display_name"], "Test User")
        self.assertEqual(parsed["text"], "Check this out!")
        self.assertEqual(parsed["timestamp"], 1700000000)
        self.assertEqual(
            parsed["url"], "https://www.threads.com/@tester/post/CodeABC"
        )
        self.assertEqual(parsed["media_urls"], ["https://example.com/video.mp4"])

    def test_extract_posts_from_html(self) -> None:
        """Verifies extracting and sorting posts from JSON script tags inside HTML."""
        mock_html = """
        <html>
            <head><title>Threads Test</title></head>
            <body>
                <script type="application/json">
                {
                    "require": [
                        [
                            ["RelayPrefetchProvider"],
                            "thread_items",
                            [],
                            {
                                "thread_items": [
                                    {
                                        "post": {
                                            "id": "post_older",
                                            "code": "OldCode",
                                            "taken_at": 1600000000,
                                            "user": {"username": "tester", "full_name": "Test User"},
                                            "caption": {"text": "First post"}
                                        }
                                    }
                                ]
                            }
                        ]
                    ]
                }
                </script>
                <script type="application/json">
                {
                    "thread_items": [
                        {
                            "post": {
                                "id": "post_newer",
                                "code": "NewCode",
                                "taken_at": 1700000000,
                                "user": {"username": "tester", "full_name": "Test User"},
                                "caption": {"text": "Second post"}
                            }
                        }
                    ]
                }
                </script>
            </body>
        </html>
        """
        posts = scraper.extract_posts_from_html(mock_html)
        self.assertEqual(len(posts), 2)
        # Should be sorted newer first
        self.assertEqual(posts[0]["id"], "post_newer")
        self.assertEqual(posts[1]["id"], "post_older")

    def test_extract_posts_with_identical_timestamps(self) -> None:
        """Verifies sorting by numerical ID when timestamps are identical."""
        mock_html = """
        <html>
            <body>
                <script type="application/json">
                {
                    "thread_items": [
                        {
                            "post": {
                                "id": "1000_123",
                                "code": "Code1",
                                "taken_at": 1500000000,
                                "user": {"username": "tester"},
                                "caption": {"text": "Older post in thread"}
                            }
                        },
                        {
                            "post": {
                                "id": "2000_123",
                                "code": "Code2",
                                "taken_at": 1500000000,
                                "user": {"username": "tester"},
                                "caption": {"text": "Newer post in thread"}
                            }
                        }
                    ]
                }
                </script>
            </body>
        </html>
        """
        posts = scraper.extract_posts_from_html(mock_html)
        self.assertEqual(len(posts), 2)
        # Should be sorted newest first (i.e., ID 2000 first)
        self.assertEqual(posts[0]["id"], "2000_123")
        self.assertEqual(posts[1]["id"], "1000_123")

    def test_get_numerical_id(self) -> None:
        """Verifies _get_numerical_id parsing behavior."""
        self.assertEqual(scraper._get_numerical_id({"id": "12345_678"}), 12345)  # pylint: disable=protected-access
        self.assertEqual(scraper._get_numerical_id({"id": "abc_678"}), 0)  # pylint: disable=protected-access
        self.assertEqual(scraper._get_numerical_id({"id": ""}), 0)  # pylint: disable=protected-access
        self.assertEqual(scraper._get_numerical_id({}), 0)  # pylint: disable=protected-access

    async def test_scrape_user_posts_with_mock_playwright(self) -> None:
        """Verifies scrape_user_posts lifecycle using context borrowing."""
        mock_browser = mock.AsyncMock()
        mock_context = mock.MagicMock()
        mock_page = mock.MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page = mock.AsyncMock(return_value=mock_page)
        mock_context.__aenter__ = mock.AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = mock.AsyncMock()

        mock_page.goto = mock.AsyncMock()
        mock_page.keyboard = mock.MagicMock()
        mock_page.keyboard.press = mock.AsyncMock()
        mock_page.wait_for_selector = mock.AsyncMock()
        mock_page.wait_for_timeout = mock.AsyncMock()
        mock_page.content = mock.AsyncMock(return_value="<html>Mock HTML</html>")
        mock_page.close = mock.AsyncMock()

        with mock.patch("scraper.extract_posts_from_html") as mock_extract:
            mock_extract.return_value = [
                {
                    "id": "123",
                    "code": "Code123",
                    "username": "tester",
                    "display_name": "Test User",
                    "text": "Hello",
                    "timestamp": 1600000000,
                    "url": "https://www.threads.com/@tester/post/Code123",
                    "media_urls": [],
                }
            ]
            posts = await scraper.scrape_user_posts(mock_browser, "tester")
            self.assertEqual(len(posts), 1)
            self.assertEqual(posts[0]["username"], "tester")
            mock_browser.new_context.assert_called_once()
            mock_page.goto.assert_called_once_with(
                "https://www.threads.com/@tester",
                wait_until="load",
                timeout=30000,
            )
            mock_page.wait_for_timeout.assert_called_once_with(500)
            mock_page.close.assert_called_once()

    async def test_scrape_user_posts_handles_selector_timeout(self) -> None:
        """Verifies scrape_user_posts falls back to wait_for_timeout on selector timeout."""
        mock_browser = mock.AsyncMock()
        mock_context = mock.MagicMock()
        mock_page = mock.MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page = mock.AsyncMock(return_value=mock_page)
        mock_context.__aenter__ = mock.AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = mock.AsyncMock()

        mock_page.goto = mock.AsyncMock()
        mock_page.keyboard = mock.MagicMock()
        mock_page.keyboard.press = mock.AsyncMock()
        mock_page.wait_for_selector = mock.AsyncMock(side_effect=Exception("Timeout"))
        mock_page.wait_for_timeout = mock.AsyncMock()
        mock_page.content = mock.AsyncMock(return_value="<html>Mock HTML</html>")
        mock_page.close = mock.AsyncMock()

        with mock.patch("scraper.extract_posts_from_html", return_value=[]):
            posts = await scraper.scrape_user_posts(mock_browser, "tester")
            self.assertEqual(posts, [])
            mock_browser.new_context.assert_called_once()
            mock_page.wait_for_selector.assert_called_once()
            self.assertEqual(
                mock_page.wait_for_timeout.call_args_list,
                [mock.call(1000), mock.call(500)],
            )
            mock_page.close.assert_called_once()

    def test_parser_defensive_checks(self) -> None:
        """Verifies defensive checks and invalid payloads handling in parser."""
        # 1. _parse_post with non-dict input
        self.assertIsNone(scraper._parse_post("not a dict"))  # pylint: disable=protected-access

        # 2. _parse_post with missing id
        self.assertIsNone(scraper._parse_post({"code": "C123"}))  # pylint: disable=protected-access

        # 3. extract_posts_from_html with invalid JSON, empty, or malformed structures
        mock_html = """
        <html>
            <!-- empty script -->
            <script type="application/json">   </script>

            <!-- invalid JSON -->
            <script type="application/json">{invalid}</script>

            <!-- thread_items is not a list -->
            <script type="application/json">
            {"thread_items": "should_be_list"}
            </script>

            <!-- item in thread_items list is not a dict or missing post -->
            <script type="application/json">
            {"thread_items": ["not_a_dict", {"missing_post": true}]}
            </script>
        </html>
        """
        posts = scraper.extract_posts_from_html(mock_html)
        self.assertEqual(posts, [])


if __name__ == "__main__":
    unittest.main()
