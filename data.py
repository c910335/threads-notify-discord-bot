import json
import os
import shutil
import tempfile
from threading import Lock

class DataStore:
    DATA_FILE = "data.json"
    SEEN_FILE = "seen_posts.json"

    def __init__(self):
        self.lock = Lock()
        self.subscriptions = []
        self.seen_posts = {}
        # Cache of username -> display_name from last scrape
        self.display_names: dict[str, str] = {}
        self.load()

    def load(self):
        with self.lock:
            # Load Subscriptions
            if os.path.exists(self.DATA_FILE):
                try:
                    with open(self.DATA_FILE, "r", encoding="utf-8") as f:
                        self.subscriptions = json.load(f)
                except Exception as e:
                    print(f"Error loading subscriptions: {e}")
                    self.subscriptions = []
            else:
                self.subscriptions = []

            # Load Seen Posts Cache
            if os.path.exists(self.SEEN_FILE):
                try:
                    with open(self.SEEN_FILE, "r", encoding="utf-8") as f:
                        self.seen_posts = json.load(f)
                except Exception as e:
                    print(f"Error loading seen posts cache: {e}")
                    self.seen_posts = {}
            else:
                self.seen_posts = {}

    def _safe_write(self, filepath, data):
        # Atomic write using a tempfile and rename
        dir_name = os.path.dirname(os.path.abspath(filepath))
        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
            json.dump(data, tf, indent=2, ensure_ascii=False)
            tf.flush()
            temp_path = tf.name
        try:
            shutil.move(temp_path, filepath)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    def save_subscriptions(self):
        with self.lock:
            try:
                self._safe_write(self.DATA_FILE, self.subscriptions)
                print("Subscriptions data saved.")
            except Exception as e:
                print(f"Failed to save subscriptions: {e}")

    def save_seen_posts(self):
        with self.lock:
            try:
                self._safe_write(self.SEEN_FILE, self.seen_posts)
                print("Seen posts data saved.")
            except Exception as e:
                print(f"Failed to save seen posts: {e}")

    # Subscriptions helper methods
    def add_subscription(
        self,
        username: str,
        channel_id: int,
        server_id: int,
        message: str,
        mention: str,
        overwrite: bool,
    ) -> bool:
        username = username.strip().lower()

        # Check if already subscribed in this channel
        existing = None
        for sub in self.subscriptions:
            if sub["username"] == username and sub["channel_id"] == channel_id:
                existing = sub
                break

        if existing:
            if not overwrite:
                return False
            # Update existing
            existing["message"] = message
            existing["mention"] = mention
            existing["server_id"] = server_id
        else:
            # Create new
            self.subscriptions.append({
                "username": username,
                "channel_id": channel_id,
                "server_id": server_id,
                "message": message,
                "mention": mention,
            })

        self.save_subscriptions()
        return True

    def remove_subscription(self, username: str, channel_id: int) -> bool:
        username = username.strip().lower()
        original_len = len(self.subscriptions)
        self.subscriptions = [
            sub for sub in self.subscriptions
            if not (sub["username"] == username and sub["channel_id"] == channel_id)
        ]

        if len(self.subscriptions) < original_len:
            self.save_subscriptions()

            # Clean up seen posts if no channels subscribe to this user anymore
            all_usernames = {sub["username"] for sub in self.subscriptions}
            if username not in all_usernames and username in self.seen_posts:
                del self.seen_posts[username]
                self.save_seen_posts()

            return True
        return False

    def list_subscriptions(self, channel_id: int) -> list[dict]:
        return [sub for sub in self.subscriptions if sub["channel_id"] == channel_id]

    def get_all_sub_usernames(self) -> set[str]:
        return {sub["username"] for sub in self.subscriptions}

    def get_subscriptions_for_user(self, username: str) -> list[dict]:
        return [sub for sub in self.subscriptions if sub["username"] == username]

    # Seen posts helpers
    def is_post_seen(self, username: str, post_id: str) -> bool:
        username = username.strip().lower()
        return post_id in self.seen_posts.get(username, [])

    def mark_post_seen(self, username: str, post_id: str):
        username = username.strip().lower()
        if username not in self.seen_posts:
            self.seen_posts[username] = []
        if post_id not in self.seen_posts[username]:
            self.seen_posts[username].append(post_id)
            self.save_seen_posts()

    def init_user_seen_posts(self, username: str, post_ids: list[str]):
        username = username.strip().lower()
        if username not in self.seen_posts:
            self.seen_posts[username] = list(post_ids)
            self.save_seen_posts()

    # Display name cache
    def update_display_name(self, username: str, display_name: str):
        self.display_names[username.strip().lower()] = display_name

    def get_display_name(self, username: str) -> str:
        return self.display_names.get(username.strip().lower(), username)
