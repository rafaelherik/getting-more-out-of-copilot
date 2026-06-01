from deepturn_agents.sanitization.redactor import redact_text


def test_redact_masks_credentials_emails_and_bearer() -> None:
    text = "api_key=sk_live_12345 user=alice@example.com Authorization=Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    result = redact_text(text)
    assert "alice@example.com" not in result.sanitized_text
    assert "sk_live_12345" not in result.sanitized_text
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result.sanitized_text
    assert result.stats["email"] == 1


def test_redact_masks_high_entropy_tokens() -> None:
    text = "value=Qw7z8Xk2Lm9Np4Rt6Yu1Vb3Hd0Se5Cf8"
    result = redact_text(text)
    assert "Qw7z8Xk2Lm9Np4Rt6Yu1Vb3Hd0Se5Cf8" not in result.sanitized_text
    assert result.stats["entropy"] >= 1
