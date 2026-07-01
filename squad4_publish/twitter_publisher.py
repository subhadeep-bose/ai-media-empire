"""
Twitter publisher — tweepy v4 (OAuth 1.0a + API v2).

post_thread()    — tweet 1 gets hero image, tweets 2-6 are plain text replies
post_hot_take()  — standalone tweet with hot-take card image
post_poll()      — standalone poll tweet (no image; Twitter renders the poll widget)
"""

import io
import json
import logging
import os
import time
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

log = logging.getLogger(__name__)

_INTER_TWEET_DELAY = 2  # seconds between posts


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

    auth = tweepy.OAuth1UserHandler(api_key, api_secret, acc_token, acc_secret)
    api_v1 = tweepy.API(auth)
    client_v2 = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=acc_token,
        access_token_secret=acc_secret,
    )
    return api_v1, client_v2


def _upload_image(api_v1, image_bytes: bytes, alt_text: str = "") -> list[str]:
    """Upload PNG bytes via v1.1, set alt text, return [media_id_string]."""
    try:
        media = api_v1.media_upload(filename="card.png", file=io.BytesIO(image_bytes))
        if alt_text:
            try:
                api_v1.create_media_metadata(media.media_id, alt_text=alt_text[:1000])
            except Exception:
                log.warning("Alt text upload failed — continuing without it")
        return [str(media.media_id)]
    except Exception:
        log.exception("Media upload failed — posting without image")
        return []


def post_thread(tweets: list[str], hero_image: bytes | None = None) -> bool:
    """
    Post a thread. Tweet 1 gets hero_image (if provided); tweets 2-N are text only.
    Returns True on full success.
    """
    try:
        api_v1, client_v2 = _client()
    except RuntimeError as e:
        log.error("Twitter client init failed: %s", e)
        return False

    previous_id = None
    for i, text in enumerate(tweets):
        media_ids = []
        if i == 0 and hero_image:
            alt = f"Branded AI/Tech thread card — {text[:200]}"
            media_ids = _upload_image(api_v1, hero_image, alt_text=alt)

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


def post_hot_take(text: str, image: bytes | None = None) -> bool:
    """Post a standalone hot-take tweet with an optional image card."""
    try:
        api_v1, client_v2 = _client()
    except RuntimeError as e:
        log.error("Twitter client init failed: %s", e)
        return False

    media_ids = []
    if image:
        alt = f"Hot take card — {text[:200]}"
        media_ids = _upload_image(api_v1, image, alt_text=alt)

    try:
        kwargs = {"text": text}
        if media_ids:
            kwargs["media_ids"] = media_ids
        response = client_v2.create_tweet(**kwargs)
        log.info("Hot take posted (id=%s)", response.data["id"])
        return True
    except Exception:
        log.exception("Failed to post hot take")
        return False


def post_poll(question: str, options: list[str], duration_hours: int = 24) -> bool:
    """
    Post a standalone poll tweet. No image — Twitter renders the poll widget inline.
    options: 2–4 strings, each ≤25 chars.
    """
    try:
        _, client_v2 = _client()
    except RuntimeError as e:
        log.error("Twitter client init failed: %s", e)
        return False

    options = [o[:25] for o in options[:4]]
    if len(options) < 2:
        log.error("Poll needs at least 2 options")
        return False

    try:
        response = client_v2.create_tweet(
            text=question,
            poll_options=options,
            poll_duration_minutes=duration_hours * 60,
        )
        log.info("Poll posted (id=%s)", response.data["id"])
        return True
    except Exception:
        log.exception("Failed to post poll")
        return False
