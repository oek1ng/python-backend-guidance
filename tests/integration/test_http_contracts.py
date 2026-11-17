from pathlib import Path

import httpx
import pytest

from tests.contracts import (
    FetchBatch,
    FetchDestination,
    FetchPrivate,
    FetchVerified,
    HTTPServer,
    MakeHTTPClient,
    ReadLimited,
    WorkerClient,
)


@pytest.mark.contract("reuse-http-clients")
class TestClientReuse:
    def test_batch_reuses_a_connection(
        self, implementation: FetchBatch, http_server: HTTPServer
    ) -> None:
        start, requests, _ = http_server
        url = start()

        assert implementation([url, url]) == ["ok", "ok"]
        assert len({peer for _, peer, _ in requests}) == 1

    def test_empty_batch_makes_no_requests(
        self, implementation: FetchBatch, http_server: HTTPServer
    ) -> None:
        _, requests, _ = http_server

        assert implementation([]) == []
        assert requests == []


@pytest.mark.contract("set-http-timeouts")
class TestHTTPTimeouts:
    def test_stalled_body_hits_read_timeout(
        self, implementation: MakeHTTPClient, http_server: HTTPServer
    ) -> None:
        start, _, _ = http_server
        url = start()

        with implementation() as client, pytest.raises(httpx.ReadTimeout):
            _ = client.get(url + "/slow")

    def test_exhausted_pool_has_a_wait_budget(
        self, implementation: MakeHTTPClient, http_server: HTTPServer
    ) -> None:
        start, _, _ = http_server
        url = start()
        with implementation() as client, client.stream("GET", url + "/slow"):
            with pytest.raises(httpx.PoolTimeout):
                _ = client.get(url)


@pytest.mark.contract("bound-response-bytes")
class TestResponseLimit:
    def test_decoded_response_is_bounded(
        self, implementation: ReadLimited, http_server: HTTPServer
    ) -> None:
        start, _, _ = http_server
        url = start()
        with httpx.Client(trust_env=False) as client:
            with pytest.raises(ValueError, match="too large"):
                _ = implementation(client, url + "/gzip", limit=100)

    def test_exact_response_limit_is_allowed(
        self, implementation: ReadLimited, http_server: HTTPServer
    ) -> None:
        start, _, _ = http_server
        url = start()
        with httpx.Client(trust_env=False) as client:
            assert implementation(client, url, limit=2) == b"ok"


@pytest.mark.contract("verify-tls")
class TestTLS:
    def test_untrusted_tls_is_rejected(
        self, implementation: FetchVerified, http_server: HTTPServer, tmp_path: Path
    ) -> None:
        import trustme

        start, _, _ = http_server
        url = start(tls=True)
        other_ca = tmp_path / "other.pem"
        trustme.CA().cert_pem.write_to_path(other_ca)

        with pytest.raises(httpx.ConnectError):
            _ = implementation(url, cafile=other_ca)

    def test_explicit_trusted_ca_succeeds(
        self, implementation: FetchVerified, http_server: HTTPServer
    ) -> None:
        start, _, ca = http_server
        url = start(tls=True)

        assert implementation(url, cafile=ca) == "ok"


@pytest.mark.contract("control-redirects")
class TestRedirects:
    def test_credentialed_redirect_is_not_followed(
        self, implementation: FetchPrivate, http_server: HTTPServer
    ) -> None:
        start, requests, _ = http_server
        url = start()
        with httpx.Client(trust_env=False) as client:
            with pytest.raises(ValueError):
                _ = implementation(client, url + "/redirect", "secret")
        assert [path for path, _, _ in requests] == ["/redirect"]

    def test_private_response_is_returned(
        self, implementation: FetchPrivate, http_server: HTTPServer
    ) -> None:
        start, _, _ = http_server
        url = start()
        with httpx.Client(trust_env=False) as client:
            assert implementation(client, url, "secret") == b"ok"


@pytest.mark.contract("restrict-outbound-destinations")
class TestDestinations:
    def test_caller_cannot_supply_an_arbitrary_url(
        self, implementation: FetchDestination, http_server: HTTPServer
    ) -> None:
        start, requests, _ = http_server
        url = start()

        with pytest.raises(KeyError):
            _ = implementation(url + "/private", {"catalog": url})
        assert requests == []

    def test_configured_destination_is_accessible(
        self, implementation: FetchDestination, http_server: HTTPServer
    ) -> None:
        start, _, _ = http_server
        url = start()

        assert implementation("catalog", {"catalog": url}) == b"ok"


@pytest.mark.contract("scope-process-resources")
class TestWorkerResources:
    async def test_worker_client_closes_on_exit(
        self, implementation: WorkerClient, http_server: HTTPServer
    ) -> None:
        start, _, _ = http_server
        url = start()
        async with implementation() as client:
            assert (await client.get(url)).content == b"ok"

        with pytest.raises(RuntimeError):
            await client.get(url)

    async def test_worker_lifespans_do_not_share_a_client(
        self, implementation: WorkerClient
    ) -> None:
        async with implementation() as first, implementation() as second:
            assert first is not second
