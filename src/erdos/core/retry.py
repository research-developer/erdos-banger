"""Retry logic for transient network failures.

This module provides retry-wrapped HTTP functions for GET and POST requests
with exponential backoff for transient errors (timeouts, connection errors,
and retryable HTTP status codes like 429 and 5xx).

Functions:
    fetch_with_retry: GET request with retry
    post_with_retry: POST request with retry
    get_retry_delay: Calculate backoff delay (public for testing)
    is_retryable_status_code: Check if status code warrants retry
"""

import logging
import time

import requests

from erdos.core.constants import (
    RETRY_BASE_DELAY,
    RETRY_MAX_ATTEMPTS,
    RETRY_MAX_DELAY,
    RETRYABLE_STATUS_CODES,
)


logger = logging.getLogger(__name__)


def is_retryable_status_code(status_code: int) -> bool:
    """Check if an HTTP status code warrants a retry.

    Args:
        status_code: HTTP status code.

    Returns:
        True if the status code is retryable (429, 5xx), False otherwise.
    """
    return status_code in RETRYABLE_STATUS_CODES


def get_retry_delay(attempt: int, response: requests.Response | None) -> float:
    """Calculate the delay before the next retry attempt.

    Uses exponential backoff with a cap. For 429 responses, respects
    the Retry-After header if present.

    Args:
        attempt: The current attempt number (0-indexed).
        response: The HTTP response, if available.

    Returns:
        Delay in seconds.
    """
    # Check for Retry-After header on 429
    if response is not None and response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), RETRY_MAX_DELAY)
            except ValueError:
                pass  # Fall through to exponential backoff

    # Exponential backoff: base * 2^attempt, capped at max
    delay = RETRY_BASE_DELAY * (2**attempt)
    return float(min(delay, RETRY_MAX_DELAY))


def fetch_with_retry(
    url: str,
    *,
    timeout: float,
    max_attempts: int = RETRY_MAX_ATTEMPTS,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> requests.Response:
    """Fetch a URL with retry logic for transient failures.

    Retries on:
    - Timeout errors
    - Connection errors
    - HTTP 429 (rate limit) - respects Retry-After header
    - HTTP 5xx (server errors)

    Does not retry on:
    - HTTP 4xx (client errors except 429)

    Args:
        url: URL to fetch.
        timeout: HTTP timeout in seconds.
        max_attempts: Maximum number of attempts (default: 3).
        params: Optional query parameters.
        headers: Optional HTTP headers.

    Returns:
        requests.Response on success.

    Raises:
        requests.Timeout: If all retries fail due to timeout.
        requests.ConnectionError: If all retries fail due to connection error.
        requests.HTTPError: If request fails with non-retryable status or
            all retries exhausted.
    """
    last_error: Exception | None = None
    last_response: requests.Response | None = None

    for attempt in range(max_attempts):
        try:
            with requests.get(
                url, params=params, headers=headers, timeout=timeout
            ) as response:
                # Check for retryable status codes
                if is_retryable_status_code(response.status_code):
                    last_response = response
                    if attempt < max_attempts - 1:
                        delay = get_retry_delay(attempt, response)
                        logger.debug(
                            "Retry %d/%d for %s: HTTP %d, waiting %.1fs",
                            attempt + 1,
                            max_attempts,
                            url,
                            response.status_code,
                            delay,
                        )
                        time.sleep(delay)
                        continue
                    # Last attempt failed - raise HTTPError
                    response.raise_for_status()

                # Non-retryable status codes (including success)
                response.raise_for_status()
                return response

        except (requests.Timeout, requests.ConnectionError) as e:
            last_error = e
            if attempt < max_attempts - 1:
                delay = get_retry_delay(attempt, None)
                logger.debug(
                    "Retry %d/%d for %s: %s, waiting %.1fs",
                    attempt + 1,
                    max_attempts,
                    url,
                    type(e).__name__,
                    delay,
                )
                time.sleep(delay)
                continue
            raise

        except requests.HTTPError:
            # Non-retryable HTTP error - don't retry
            raise

    # Should not reach here, but handle edge case
    if last_error is not None:
        raise last_error
    if last_response is not None:
        last_response.raise_for_status()
    raise requests.RequestException("Max retries exceeded")


def post_with_retry(
    url: str,
    *,
    timeout: float,
    json_payload: dict[str, object] | None = None,
    max_attempts: int = RETRY_MAX_ATTEMPTS,
    headers: dict[str, str] | None = None,
) -> requests.Response:
    """POST to a URL with retry logic for transient failures.

    Retries on:
    - Timeout errors
    - Connection errors
    - HTTP 429 (rate limit) - respects Retry-After header
    - HTTP 5xx (server errors)

    Does not retry on:
    - HTTP 4xx (client errors except 429)

    Args:
        url: URL to POST to.
        timeout: HTTP timeout in seconds.
        json_payload: Optional JSON body to send.
        max_attempts: Maximum number of attempts (default: 3).
        headers: Optional HTTP headers.

    Returns:
        requests.Response on success.

    Raises:
        requests.Timeout: If all retries fail due to timeout.
        requests.ConnectionError: If all retries fail due to connection error.
        requests.HTTPError: If request fails with non-retryable status or
            all retries exhausted.
    """
    last_error: Exception | None = None
    last_response: requests.Response | None = None

    for attempt in range(max_attempts):
        try:
            response = requests.post(
                url, json=json_payload, headers=headers, timeout=timeout
            )

            # Check for retryable status codes
            if is_retryable_status_code(response.status_code):
                last_response = response
                if attempt < max_attempts - 1:
                    delay = get_retry_delay(attempt, response)
                    logger.debug(
                        "Retry %d/%d for POST %s: HTTP %d, waiting %.1fs",
                        attempt + 1,
                        max_attempts,
                        url,
                        response.status_code,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                # Last attempt failed - raise HTTPError
                response.raise_for_status()

            # Non-retryable status codes (including success)
            response.raise_for_status()
            return response

        except (requests.Timeout, requests.ConnectionError) as e:
            last_error = e
            if attempt < max_attempts - 1:
                delay = get_retry_delay(attempt, None)
                logger.debug(
                    "Retry %d/%d for POST %s: %s, waiting %.1fs",
                    attempt + 1,
                    max_attempts,
                    url,
                    type(e).__name__,
                    delay,
                )
                time.sleep(delay)
                continue
            raise

        except requests.HTTPError:
            # Non-retryable HTTP error - don't retry
            raise

    # Should not reach here, but handle edge case
    if last_error is not None:
        raise last_error
    if last_response is not None:
        last_response.raise_for_status()
    raise requests.RequestException("Max retries exceeded")
