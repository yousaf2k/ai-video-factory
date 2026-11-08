"""
LLM request timeouts: per-provider override -> LLM_TIMEOUT -> default, and
provider constructor wiring (local models are the slow ones).
"""
from types import SimpleNamespace

import core.llm_engine as lle


def test_resolve_timeout_precedence():
    assert lle._resolve_timeout(SimpleNamespace(OPENAI_TIMEOUT=0, LLM_TIMEOUT=300), "OPENAI") == 300
    assert lle._resolve_timeout(SimpleNamespace(OPENAI_TIMEOUT=600, LLM_TIMEOUT=300), "OPENAI") == 600
    # 0 / garbage falls through
    assert lle._resolve_timeout(SimpleNamespace(OPENAI_TIMEOUT=0, LLM_TIMEOUT=0), "OPENAI") == 300
    assert lle._resolve_timeout(SimpleNamespace(OPENAI_TIMEOUT="bogus", LLM_TIMEOUT=300), "OPENAI") == 300


def test_local_providers_use_configured_timeout():
    import config
    p = lle.OllamaProvider(api_key="", model="qwen3")
    assert p.timeout == config.LLM_TIMEOUT
    p2 = lle.StrataProvider(api_key="", model="x")
    assert p2.timeout == config.LLM_TIMEOUT
    p3 = lle.LMStudioProvider(api_key="", model="m")
    assert p3.timeout == config.LLM_TIMEOUT


def test_provider_override_wins_via_get_provider():
    import config
    shim = {a: getattr(config, a) for a in dir(config) if a.isupper()}
    shim.update(STRATA_TIMEOUT=900, STRATA_MODEL="x", STRATA_BASE_URL="")
    p = lle.get_provider("strata", config_module=SimpleNamespace(**shim))
    assert p.timeout == 900
