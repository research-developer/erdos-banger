"""Unit tests for retry logic (DEBT-033)."""

import pytest
import requests
import responses
from responses import matchers

from erdos.core.retry import (
    fetch_with_retry,
    is_retryable_status_code,
)


class TestIsRetryableStatusCode:
    """Tests for is_retryable_status_code."""

    def test_429_is_retryable(self) -> None:
        """429 Too Many Requests should be retryable."""
        assert is_retryable_status_code(429) is True

    def test_500_is_retryable(self) -> None:
        """500 Internal Server Error should be retryable."""
        assert is_retryable_status_code(500) is True

    def test_502_is_retryable(self) -> None:
        """502 Bad Gateway should be retryable."""
        assert is_retryable_status_code(502) is True

    def test_503_is_retryable(self) -> None:
        """503 Service Unavailable should be retryable."""
        assert is_retryable_status_code(503) is True

    def test_504_is_retryable(self) -> None:
        """504 Gateway Timeout should be retryable."""
        assert is_retryable_status_code(504) is True

    def test_200_not_retryable(self) -> None:
        """200 OK should not be retryable."""
        assert is_retryable_status_code(200) is False

    def test_400_not_retryable(self) -> None:
        """400 Bad Request should not be retryable (client error)."""
        assert is_retryable_status_code(400) is False

    def test_404_not_retryable(self) -> None:
        """404 Not Found should not be retryable."""
        assert is_retryable_status_code(404) is False

    def test_401_not_retryable(self) -> None:
        """401 Unauthorized should not be retryable."""
        assert is_retryable_status_code(401) is False


class TestFetchWithRetry:
    """Tests for fetch_with_retry function."""

    @responses.activate
    def test_success_on_first_try(self) -> None:
        """fetch_with_retry succeeds on first attempt."""
        url = "https://api.example.com/test"
        responses.add(responses.GET, url, json={"result": "success"}, status=200)

        response = fetch_with_retry(url, timeout=10.0)

        assert response.status_code == 200
        assert response.json() == {"result": "success"}
        assert len(responses.calls) == 1

    @responses.activate
    def test_retry_on_timeout_then_success(self) -> None:
        """fetch_with_retry retries on timeout and eventually succeeds."""
        url = "https://api.example.com/test"

        # First call times out
        responses.add(responses.GET, url, body=requests.Timeout("timed out"))
        # Second call succeeds
        responses.add(responses.GET, url, json={"result": "success"}, status=200)

        response = fetch_with_retry(url, timeout=10.0, max_attempts=3)

        assert response.status_code == 200
        assert len(responses.calls) == 2

    @responses.activate
    def test_retry_on_connection_error_then_success(self) -> None:
        """fetch_with_retry retries on connection error and eventually succeeds."""
        url = "https://api.example.com/test"

        # First call has connection error
        responses.add(
            responses.GET, url, body=requests.ConnectionError("connection refused")
        )
        # Second call succeeds
        responses.add(responses.GET, url, json={"result": "success"}, status=200)

        response = fetch_with_retry(url, timeout=10.0, max_attempts=3)

        assert response.status_code == 200
        assert len(responses.calls) == 2

    @responses.activate
    def test_retry_on_500_then_success(self) -> None:
        """fetch_with_retry retries on 500 error and eventually succeeds."""
        url = "https://api.example.com/test"

        # First call returns 500
        responses.add(responses.GET, url, body="Server Error", status=500)
        # Second call succeeds
        responses.add(responses.GET, url, json={"result": "success"}, status=200)

        response = fetch_with_retry(url, timeout=10.0, max_attempts=3)

        assert response.status_code == 200
        assert len(responses.calls) == 2

    @responses.activate
    def test_retry_on_429_respects_retry_after_header(self) -> None:
        """fetch_with_retry respects Retry-After header on 429."""
        url = "https://api.example.com/test"

        # First call returns 429 with Retry-After header
        responses.add(
            responses.GET,
            url,
            body="Rate limited",
            status=429,
            headers={"Retry-After": "1"},
        )
        # Second call succeeds
        responses.add(responses.GET, url, json={"result": "success"}, status=200)

        response = fetch_with_retry(url, timeout=10.0, max_attempts=3)

        assert response.status_code == 200
        assert len(responses.calls) == 2

    @responses.activate
    def test_no_retry_on_404(self) -> None:
        """fetch_with_retry does not retry on 404 (permanent error)."""
        url = "https://api.example.com/test"
        responses.add(responses.GET, url, body="Not Found", status=404)

        with pytest.raises(requests.HTTPError) as exc_info:
            fetch_with_retry(url, timeout=10.0, max_attempts=3)

        assert exc_info.value.response is not None
        assert exc_info.value.response.status_code == 404
        assert len(responses.calls) == 1

    @responses.activate
    def test_no_retry_on_400(self) -> None:
        """fetch_with_retry does not retry on 400 (client error)."""
        url = "https://api.example.com/test"
        responses.add(responses.GET, url, body="Bad Request", status=400)

        with pytest.raises(requests.HTTPError) as exc_info:
            fetch_with_retry(url, timeout=10.0, max_attempts=3)

        assert exc_info.value.response is not None
        assert exc_info.value.response.status_code == 400
        assert len(responses.calls) == 1

    @responses.activate
    def test_max_retries_exceeded_raises_last_error(self) -> None:
        """fetch_with_retry raises exception after max retries exceeded."""
        url = "https://api.example.com/test"

        # All calls timeout
        for _ in range(3):
            responses.add(responses.GET, url, body=requests.Timeout("timed out"))

        with pytest.raises(requests.Timeout):
            fetch_with_retry(url, timeout=10.0, max_attempts=3)

        assert len(responses.calls) == 3

    @responses.activate
    def test_max_retries_exceeded_with_500_raises_http_error(self) -> None:
        """fetch_with_retry raises HTTPError after max retries on 500."""
        url = "https://api.example.com/test"

        # All calls return 500
        for _ in range(3):
            responses.add(responses.GET, url, body="Server Error", status=500)

        with pytest.raises(requests.HTTPError) as exc_info:
            fetch_with_retry(url, timeout=10.0, max_attempts=3)

        assert exc_info.value.response is not None
        assert exc_info.value.response.status_code == 500
        assert len(responses.calls) == 3

    @responses.activate
    def test_passes_headers_and_params(self) -> None:
        """fetch_with_retry passes headers and params to request."""
        url = "https://api.example.com/test"
        responses.add(
            responses.GET,
            url,
            json={"result": "success"},
            status=200,
            match=[
                matchers.query_param_matcher({"key": "value"}),
                matchers.header_matcher({"X-Custom": "header"}),
            ],
        )

        response = fetch_with_retry(
            url,
            timeout=10.0,
            params={"key": "value"},
            headers={"X-Custom": "header"},
        )

        assert response.status_code == 200

    @responses.activate
    def test_default_max_attempts_is_3(self) -> None:
        """fetch_with_retry defaults to 3 max attempts."""
        url = "https://api.example.com/test"

        # All calls timeout
        for _ in range(3):
            responses.add(responses.GET, url, body=requests.Timeout("timed out"))

        with pytest.raises(requests.Timeout):
            fetch_with_retry(url, timeout=10.0)

        # Default is 3 attempts
        assert len(responses.calls) == 3

    @responses.activate
    def test_single_attempt_with_max_attempts_1(self) -> None:
        """fetch_with_retry makes single attempt when max_attempts=1."""
        url = "https://api.example.com/test"
        responses.add(responses.GET, url, body=requests.Timeout("timed out"))

        with pytest.raises(requests.Timeout):
            fetch_with_retry(url, timeout=10.0, max_attempts=1)

        assert len(responses.calls) == 1
