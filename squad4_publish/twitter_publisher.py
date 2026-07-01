"""
Twitter publisher — posts a thread with one branded image per tweet via tweepy v4 (API v2).

Requires four secrets in env:
  TWITTER_API_KEY, TWITTER_API_SECRET,
  TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
"""

import logging
import os
import time
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

log = logging.getLogger(__name__)

_INTER_TWEET_DELAY = 2  # seconds between posts to respect rate limits


def _client():
    try:
        import tweepy
    except ImportError:
        raise RuntimeError("tweepy not installed — run: pip install tweepy")

    api_key    = os.getenv("TWITTER_API_KEY", "")
    api_secret = os.getenv("TWITTER_API_SECRET", "")
    acc_token  = os.getenv("TWITTER_ACCESS_TOKEN", "")
    acc_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")

    if not all([api_key, api_secret, acc_token, acc_secret]):
        raise RuntimeError("Missing one or more TWITTER_* env vars")

    # v1.1 client (needed for media upload)
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, acc_token, acc_secret)
    api_v1 = tweepy.API(auth)

    # v2 client (needed for tweet creation with reply threading)
    client_v2 = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=acc_token,
        access_token_secret=acc_secret,
    )
    return api_v1, client_v2


def post_thread(tweets: list[str], images: list[bytes] | None = None) -> bool:
    """
    Post a list of tweet strings as a thread.
    images: list of PNG bytes, one per tweet (optional; length must match tweets).
    Returns True on full success, False on any failure.
    """
    try:
        api_v1, client_v2 = _client()
    except RuntimeError as e:
        log.error("Twitter client init failed: %s", e)
        return False

    previous_id = None
    for i, text in enumerate(tweets):
        media_ids = []
        if images and i < len(images):
            try:
                import io
                media = api_v1.media_upload(filename=f"tweet_{i+1}.png",
                                             file=io.BytesIO(images[i]))
                media_ids = [media.media_id]
            except Exception:
                log.exception("Media upload failed for tweet %d — posting without image", i + 1)

        try:
            kwargs = {"text": text}
            if previous_id:
                kwargs["in_reply_to_tweet_id"] = previous_id
            if media_ids:
                kwargs["media_ids"] = media_ids

            response = client_v2.create_tweet(**kwargs)
            previous_id = response.data["id"]
            log.info("Posted tweet %d/%d (id=%s)", i + 1, len(tweets), previous_id)
        except Exception:
            log.exception("Failed to post tweet %d/%d", i + 1, len(tweets))
            return False

        if i < len(tweets) - 1:
            time.sleep(_INTER_TWEET_DELAY)

    return True
