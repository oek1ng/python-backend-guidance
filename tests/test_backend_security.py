import os
import time
from pathlib import Path

import jwt
import pytest

from tests.contracts import ReadOwnedFile, VerifyToken


@pytest.mark.contract("confine-file-access")
class TestFileConfinement:
    def test_symlink_cannot_escape_directory(
        self, implementation: ReadOwnedFile, tmp_path: Path
    ) -> None:
        root = tmp_path / "uploads"
        root.mkdir()
        secret = tmp_path / "secret"
        _ = secret.write_bytes(b"secret")
        (root / "link").symlink_to(secret)
        fd = os.open(root, os.O_RDONLY)
        try:
            with pytest.raises(OSError):
                _ = implementation(fd, "link")
            with pytest.raises(ValueError):
                _ = implementation(fd, "../secret")
        finally:
            os.close(fd)

    def test_regular_flat_file_can_be_read(
        self, implementation: ReadOwnedFile, tmp_path: Path
    ) -> None:
        _ = (tmp_path / "file").write_bytes(b"data")
        fd = os.open(tmp_path, os.O_RDONLY)
        try:
            assert implementation(fd, "file") == b"data"
        finally:
            os.close(fd)


@pytest.mark.contract("verify-token-claims")
class TestTokens:
    key: str = "test-only-signing-key-with-at-least-sixty-four-bytes-for-HS384-tests"

    def token(
        self,
        *,
        signing_key: str | None = None,
        algorithm: str = "HS256",
        **changes: str | float,
    ) -> str:
        payload: dict[str, str | float] = {
            "sub": "alice",
            "iss": "https://issuer.example",
            "aud": "backend",
            "exp": time.time() + 60,
        }
        payload.update(changes)
        return jwt.encode(
            payload,
            self.key if signing_key is None else signing_key,
            algorithm=algorithm,
        )

    def test_wrong_signature_is_rejected(self, implementation: VerifyToken) -> None:
        token = self.token(signing_key="different-test-signing-key-at-least-32-bytes")

        with pytest.raises(jwt.InvalidSignatureError):
            _ = implementation(token, self.key)

    def test_wrong_token_issuer_is_rejected(self, implementation: VerifyToken) -> None:
        token = self.token(iss="https://untrusted.example")

        with pytest.raises(jwt.InvalidIssuerError):
            _ = implementation(token, self.key)

    def test_unapproved_algorithm_is_rejected(
        self, implementation: VerifyToken
    ) -> None:
        token = self.token(algorithm="HS384")

        with pytest.raises(jwt.InvalidAlgorithmError):
            _ = implementation(token, self.key)

    def test_wrong_token_audience_is_rejected(
        self, implementation: VerifyToken
    ) -> None:
        with pytest.raises(jwt.InvalidAudienceError):
            _ = implementation(self.token(aud="other-service"), self.key)

    def test_valid_signed_token_is_accepted(self, implementation: VerifyToken) -> None:
        assert implementation(self.token(), self.key)["sub"] == "alice"

    def test_expired_token_is_rejected(self, implementation: VerifyToken) -> None:
        with pytest.raises(jwt.ExpiredSignatureError):
            _ = implementation(self.token(exp=1), self.key)

    @pytest.mark.parametrize("claim", ["exp", "iss", "aud", "sub"])
    def test_required_claim_cannot_be_omitted(
        self, implementation: VerifyToken, claim: str
    ) -> None:
        payload: dict[str, str | float] = {
            "sub": "alice",
            "iss": "https://issuer.example",
            "aud": "backend",
            "exp": time.time() + 60,
        }
        del payload[claim]
        token = jwt.encode(payload, self.key, algorithm="HS256")

        with pytest.raises(jwt.MissingRequiredClaimError):
            _ = implementation(token, self.key)
