"""
Twitter publisher — tweepy v4 (OAuth 1.0a + API v2).

post_thread()    — tweet 1 gets hero image, tweets 2-N are plain text replies.
                   Returns (success: bool, tweet_1_id: str | None).
post_hot_take()  — standalone tweet with hot-take card image
post_poll()      — standalone poll tweet (no image; Twitter renders the poll widget)
"""

import io
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

    missing = [name for name, val in [
        ("TWITTER_API_KEY", api_key),
        ("TWITTER_API_SECRET", api_secret),
        ("TWITTER_ACCESS_TOKEN", acc_token),
        ("TWITTER_ACCESS_TOKEN_SECRET", acc_secret),
    ] if not val]
    if missing:
        raise RuntimeError(f"Missing Twitter env vars: {', '.join(missing)}")

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


def post_thread(tweets: list[str], hero_image: bytes | None = None) -> tuple[bool, str | None]:
    """
    Post a thread. Tweet 1 gets hero_image (if provided); tweets 2-N are text only.
    Returns (success, tweet_1_id) — tweet_1_id is None on failure.
    """
    try:
        api_v1, client_v2 = _client()
    except RuntimeError as e:
        log.error("Twitter client init failed: %s", e)
        return False, None

    previous_id = None
    tweet_1_id = None

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
            if i == 0:
                tweet_1_id = str(previous_id)
            log.info("Posted tweet %d/%d (id=%s)", i + 1, len(tweets), previous_id)
        except Exception:
            log.exception("Failed to post tweet %d/%d", i + 1, len(tweets))
            return False, None

        if i < len(tweets) - 1:
            time.sleep(_INTER_TWEET_DELAY)

    return True, tweet_1_id


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


def get_tweet_impressions(tweet_ids: list[str]) -> dict[str, int]:
    """
    Fetch public_metrics for a list of tweet IDs.
    Returns {tweet_id: impression_count}. Missing IDs get 0.
    """
    if not tweet_ids:
        return {}
    try:
        _, client_v2 = _client()
    except RuntimeError as e:
        log.error("Twitter client init failed: %s", e)
        return {tid: 0 for tid in tweet_ids}

    results = {}
    try:
        import tweepy
        response = client_v2.get_tweets(
            ids=tweet_ids,
            tweet_fields=["public_metrics"],
        )
        for tweet in (response.data or []):
            metrics = tweet.get("public_metrics") or {}
            results[str(tweet["id"])] = metrics.get("impression_count", 0)
    except Exception:
        log.exception("Failed to fetch tweet metrics")
    for tid in tweet_ids:
        results.setdefault(tid, 0)
    return results


def pin_tweet(tweet_id: str) -> bool:
    """
    Pin a tweet to the authenticated user's profile.
    Requires Basic tier ($100/month) or above; falls back gracefully on 403.
    """
    try:
        _, client_v2 = _client()
    except RuntimeError as e:
        log.error("Twitter client init failed: %s", e)
        return False

    try:
        me = client_v2.get_me()
        user_id = me.data["id"]
        client_v2.pin_tweet(tweet_id=tweet_id, id=user_id)
        log.info("Pinned tweet %s", tweet_id)
        return True
    except Exception as e:
        log.warning("Pin tweet failed (may need Basic tier): %s", e)
        return False
