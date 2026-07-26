"""Environment-driven settings.

Kept intentionally small — every tunable here maps to an SSM Parameter Store
entry in the AWS deployment (see README) so on-call can adjust behavior
without a redeploy.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ARRIVIA_", env_file=".env")

    service_name: str = "arrivia-travel-recommendations"
    log_level: str = "INFO"

    # Downstream call resilience
    downstream_timeout_seconds: float = 1.5
    downstream_max_retries: int = 2
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_reset_seconds: float = 30.0

    # Partner config is read rarely-changing rules — cache aggressively but
    # boundedly, and never serve a stale entry past this window.
    partner_config_cache_ttl_seconds: float = 300.0
    partner_config_max_staleness_seconds: float = 900.0

    # Fail-safe defaults applied when a partner's rules are unknown/unreachable.
    fallback_max_recommendations: int = 1
    fallback_excluded_categories: list[str] = ["cruise", "package"]

    # Chaos knobs for local failure-mode testing (see README "Verification").
    mock_member_service_failure_rate: float = 0.0
    mock_partner_config_failure_rate: float = 0.0


settings = Settings()
