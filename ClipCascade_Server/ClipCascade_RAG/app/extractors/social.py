import logging
import re
from urllib.parse import urlparse

from app.extractors.base import ContentExtractor, ExtractionError
from app.extractors.hermes import ask_tweet_content
from app.extractors.ytdlp import YtDlpExtractor
from app.models import ContentType, ExtractedContent, MediaItem

logger = logging.getLogger(__name__)

TWEET_PATH = re.compile(r"/([^/]+)/status/(\d+)")
SOCIAL_HOSTS = re.compile(
    r"(^|\.)(x\.com|twitter\.com|fxtwitter\.com|instagram\.com|kkinstagram\.com)$",
    re.IGNORECASE,
)


class SocialPostExtractor(ContentExtractor):
    """Posts on x.com / instagram.com (including fxtwitter/kkinstagram mirrors).

    Tweets go through the Hermes chat-completions endpoint (HERMES_API_BASE_URL),
    which fetches the post and returns its text and author. Instagram falls
    back to yt-dlp, which can read public posts/reels and their captions.
    """

    def __init__(self) -> None:
        self._ytdlp = YtDlpExtractor()

    def supports(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return bool(SOCIAL_HOSTS.search(host))

    def extract(self, url: str) -> ExtractedContent:
        host = (urlparse(url).hostname or "").lower()
        if "instagram" in host:
            return self._extract_instagram(url)
        return self._extract_tweet(url)

    def _extract_tweet(self, url: str) -> ExtractedContent:
        if not TWEET_PATH.search(urlparse(url).path):
            raise ExtractionError(f"not a recognizable tweet URL: {url}")

        tweet = ask_tweet_content(url)
        content = ExtractedContent(
            source_url=url,
            content_type=ContentType.POST,
            text=tweet.text,
            title=None,
            author=tweet.author,
        )
        content.media.extend(MediaItem(url=u, kind="image") for u in tweet.image_urls)
        if tweet.video_url:
            content.media.append(MediaItem(url=tweet.video_url, kind="video"))
            content.content_type = ContentType.VIDEO
        elif content.media:
            content.content_type = ContentType.IMAGE
        return content

    def _extract_instagram(self, url: str) -> ExtractedContent:
        # kkinstagram is a mirror; normalize back to the real host for yt-dlp.
        real = re.sub(r"(?i)kkinstagram\.com", "instagram.com", url)
        content = self._ytdlp.extract(real)
        content.source_url = url
        return content
