"""Platform and source type enumerations for SourceOS."""

from enum import Enum


class Platform(str, Enum):
    RSS = "rss"
    WEBSITE = "website"
    YOUTUBE = "youtube"
    PODCAST = "podcast"


class SourceType(str, Enum):
    RSS_FEED = "rss_feed"
    WEBSITE_LIST = "website_list"
    YOUTUBE_CHANNEL = "youtube_channel"
    PODCAST = "podcast"


class SourceStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    ARCHIVED = "archived"


class ItemStatus(str, Enum):
    DISCOVERED = "discovered"
    FETCHED = "fetched"
    FAILED = "failed"
    SKIPPED = "skipped"


class JobType(str, Enum):
    MONITOR = "monitor"
    FETCH = "fetch"
    EXPORT = "export"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class MediaType(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"
    PDF = "pdf"


class ErrorCode(str, Enum):
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    HTTP_4XX = "HTTP_4XX"
    HTTP_5XX = "HTTP_5XX"
    PARSE_ERROR = "PARSE_ERROR"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    UNKNOWN = "UNKNOWN"
