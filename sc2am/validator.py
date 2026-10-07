"""
URL validation utilities for sc2am.
"""

import logging
from typing import List, Tuple
from urllib.parse import unquote, urljoin, urlparse

import requests

logger = logging.getLogger(__name__)


class URLValidator:
    """Validates SoundCloud and other music platform URLs."""

    # Supported platforms
    SUPPORTED_DOMAINS = {
        "soundcloud.com": "SoundCloud",
        "www.soundcloud.com": "SoundCloud",
        "youtube.com": "YouTube",
        "www.youtube.com": "YouTube",
        "youtu.be": "YouTube",
        "spotify.com": "Spotify",
        "www.spotify.com": "Spotify",
    }

    SOUNDCLOUD_TRACK_HELP = (
        "Only SoundCloud track URLs are supported. Please use a URL like "
        "https://soundcloud.com/<artist>/<track>"
    )
    SOUNDCLOUD_PROFILE_ROUTES = {
        "tracks",
        "albums",
        "sets",
        "reposts",
        "likes",
        "spotlight",
        "comments",
    }
    SHARE_HOST = "on.soundcloud.com"
    SHARE_MAX_REQUESTS = 5
    SHARE_TIMEOUT = (3, 5)  # Connect/read timeout in seconds, per request.
    SHARE_HELP = "Please copy a fresh share link or use the direct SoundCloud track URL."

    @staticmethod
    def resolve_track_url(url: str) -> Tuple[bool, str, str]:
        """Resolve share links and return (valid, target_url, platform_or_error).

        Direct URLs retain their existing validation contract and do not use HTTP.
        Only the short-link host is requested; the final track is validated locally
        and later verified by the downloader's single-track extraction preflight.
        """
        if not isinstance(url, str) or not url.strip():
            return False, "", "Please provide a valid URL."
        original = url.strip()
        current = original
        try:
            parsed = urlparse(current)
            if not parsed.scheme:
                current = "https://" + current
                parsed = urlparse(current)
        except ValueError:
            valid, message = URLValidator._validate_direct_url(original)
            return valid, original, message
        if (parsed.hostname or "").lower() != URLValidator.SHARE_HOST:
            valid, message = URLValidator._validate_direct_url(original)
            return valid, original, message

        try:
            seen: set[str] = set()
            for _ in range(URLValidator.SHARE_MAX_REQUESTS + 1):
                parsed = urlparse(current)
                if (
                    parsed.scheme not in {"http", "https"}
                    or parsed.username is not None
                    or parsed.password is not None
                    or parsed.port not in {None, 80 if parsed.scheme == "http" else 443}
                    or any(character.isspace() or ord(character) < 32 for character in current)
                    or (parsed.hostname or "").lower()
                    not in {URLValidator.SHARE_HOST, "soundcloud.com", "www.soundcloud.com"}
                ):
                    return (
                        False,
                        "",
                        (
                            "The SoundCloud share link redirects to an unsupported URL. "
                            + URLValidator.SHARE_HELP
                        ),
                    )
                if (parsed.hostname or "").lower() != URLValidator.SHARE_HOST:
                    valid, message = URLValidator._validate_direct_url(current)
                    return valid, current, message

                # Fragments never reach the server and must not bypass loop detection.
                current = parsed._replace(fragment="").geturl()
                if current in seen:
                    return (
                        False,
                        "",
                        (
                            "The SoundCloud share link contains a redirect loop. "
                            + URLValidator.SHARE_HELP
                        ),
                    )
                if len(seen) >= URLValidator.SHARE_MAX_REQUESTS:
                    break
                seen.add(current)
                # HEAD avoids downloading page bodies, even for expired share links.
                with requests.head(
                    current,
                    allow_redirects=False,
                    timeout=URLValidator.SHARE_TIMEOUT,
                    stream=True,
                ) as response:
                    if response.status_code in {404, 410}:
                        return (
                            False,
                            "",
                            (
                                "The SoundCloud share link has expired or was not found. "
                                + URLValidator.SHARE_HELP
                            ),
                        )
                    if response.status_code not in {301, 302, 303, 307, 308}:
                        return (
                            False,
                            "",
                            (
                                "The SoundCloud share link did not redirect to a track "
                                f"(HTTP {response.status_code}). " + URLValidator.SHARE_HELP
                            ),
                        )
                    location = response.headers.get("Location", "").strip()
                    if not location:
                        return (
                            False,
                            "",
                            (
                                "The SoundCloud share link returned a redirect without a target. "
                                + URLValidator.SHARE_HELP
                            ),
                        )
                    current = urljoin(current, location)

            return (
                False,
                "",
                (
                    "The SoundCloud share link exceeded the redirect limit. "
                    + URLValidator.SHARE_HELP
                ),
            )
        except requests.RequestException:
            logger.exception("SoundCloud share link request failed")
            return (
                False,
                "",
                (
                    "Could not resolve the SoundCloud share link. Check your connection and try again. "
                    + URLValidator.SHARE_HELP
                ),
            )
        except ValueError:
            return (
                False,
                "",
                ("The SoundCloud share link contains an invalid URL. " + URLValidator.SHARE_HELP),
            )

    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str]:
        """Validate a direct track URL or the resolved target of a share link."""
        valid, _, message = URLValidator.resolve_track_url(url)
        return valid, message

    @staticmethod
    def _validate_direct_url(url: str) -> Tuple[bool, str]:
        """
        Validate if URL is a supported music platform.

        Args:
            url: URL to validate

        Returns:
            Tuple of (is_valid, platform_name)
        """
        if not url or not isinstance(url, str):
            return False, "Please provide a valid URL."

        url = url.strip()

        if not url:
            return False, "Please provide a valid URL."

        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
                parsed = urlparse(url)

            if parsed.scheme not in ("http", "https"):
                return False, "Please use a URL that starts with http:// or https://."

            if not parsed.netloc:
                return False, "The URL is missing a domain name."

            domain = (parsed.hostname or "").lower()
            if not domain:
                return False, "The URL is missing a domain name."

            if domain in {"soundcloud.com", "www.soundcloud.com"}:
                path_segments = [segment for segment in parsed.path.split("/") if segment]
                if len(path_segments) != 2:
                    return False, URLValidator.SOUNDCLOUD_TRACK_HELP

                if any(not segment.strip() for segment in path_segments):
                    return False, URLValidator.SOUNDCLOUD_TRACK_HELP

                if unquote(path_segments[1]).lower() in URLValidator.SOUNDCLOUD_PROFILE_ROUTES:
                    return False, URLValidator.SOUNDCLOUD_TRACK_HELP

                return True, "SoundCloud"

            for supported_domain, platform in URLValidator.SUPPORTED_DOMAINS.items():
                if domain == supported_domain:
                    if platform != "SoundCloud":
                        return False, "Only SoundCloud track URLs are supported right now."
                    return True, platform

            return False, "Only SoundCloud track URLs are supported right now."

        except Exception:
            logger.exception("URL validation failed")
            return False, "The URL could not be parsed. Please check the format and try again."

    @staticmethod
    def validate_batch_file(file_path: str) -> Tuple[bool, List[str], List[Tuple[int, str]]]:
        """
        Validate a file containing URLs (one per line).

        Args:
            file_path: Path to file with URLs

        Returns:
            Tuple of (all_valid, valid_urls, errors)
            errors: List of (line_number, error_message)
        """
        valid_urls = []
        errors = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):  # Skip empty lines and comments
                        continue

                    is_valid, target, platform = URLValidator.resolve_track_url(line)
                    if is_valid:
                        valid_urls.append(target)
                    else:
                        errors.append((line_num, platform))

        except FileNotFoundError:
            errors.append((0, "Batch file not found. Please check the file path and try again."))
        except Exception:
            logger.exception("Failed to read batch file")
            errors.append(
                (0, "The batch file could not be read. Please check the file and try again.")
            )

        return len(errors) == 0, valid_urls, errors
