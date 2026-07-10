import json
import re
from playwright.async_api import async_playwright

def find_key_in_dict(obj, target_key):
    """
    Recursively find all values associated with target_key in a nested dict/list structure.
    """
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == target_key:
                results.append(v)
            else:
                results.extend(find_key_in_dict(v, target_key))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(find_key_in_dict(item, target_key))
    return results

def extract_posts_from_html(html_content: str) -> list[dict]:
    # Extract all application/json scripts
    json_scripts = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html_content, re.DOTALL)

    unique_posts = {}

    for script_content in json_scripts:
        script_content = script_content.strip()
        if not script_content:
            continue
        try:
            data = json.loads(script_content)
            # Find all thread_items occurrences
            thread_items_lists = find_key_in_dict(data, "thread_items")

            for items_list in thread_items_lists:
                if not isinstance(items_list, list):
                    continue
                for item in items_list:
                    if not isinstance(item, dict) or "post" not in item:
                        continue
                    post_data = item["post"]
                    if not isinstance(post_data, dict):
                        continue

                    post_id = post_data.get("id")
                    if not post_id:
                        continue

                    # Extract fields
                    code = post_data.get("code")
                    user = post_data.get("user", {})
                    username = user.get("username")
                    display_name = user.get("full_name") or username
                    timestamp = post_data.get("taken_at")

                    caption = post_data.get("caption") or {}
                    text = caption.get("text", "")

                    # Extract media if present
                    media_urls = []
                    # 1. Carousel media
                    carousel = post_data.get("carousel_media") or []
                    for c in carousel:
                        img_versions = c.get("image_versions2", {}).get("candidates", [])
                        if img_versions:
                            media_urls.append(img_versions[0].get("url"))

                    # 2. Single Image
                    if not media_urls:
                        img_versions = post_data.get("image_versions2", {}).get("candidates", [])
                        if img_versions:
                            media_urls.append(img_versions[0].get("url"))

                    # 3. Video
                    videos = post_data.get("video_versions") or []
                    if videos:
                        media_urls.append(videos[0].get("url"))

                    unique_posts[post_id] = {
                        "id": post_id,
                        "code": code,
                        "username": username,
                        "display_name": display_name,
                        "text": text,
                        "timestamp": timestamp,
                        "url": f"https://www.threads.com/@{username}/post/{code}" if username and code else None,
                        "media_urls": media_urls
                    }
        except Exception:
            pass

    # Sort posts by timestamp descending
    sorted_posts = sorted(unique_posts.values(), key=lambda x: x["timestamp"] or 0, reverse=True)
    return sorted_posts

async def scrape_user_posts(username: str) -> list[dict]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 1000},
            locale="en-US"
        )

        page = await context.new_page()
        url = f"https://www.threads.com/@{username}"

        try:
            await page.goto(url, wait_until="load", timeout=30000)
            await page.wait_for_timeout(4000)

            # Dismiss login modal by pressing Escape
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)

            # Get HTML content
            content = await page.content()

            posts = extract_posts_from_html(content)
            # Filter posts to ensure we only return posts belonging to the target username
            filtered_posts = [p for p in posts if p["username"] and p["username"].lower() == username.lower()]
            return filtered_posts

        finally:
            await browser.close()
