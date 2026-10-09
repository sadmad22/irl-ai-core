from __future__ import annotations

import pytest

from scripts.run_p6_real_e2e import _writer_instructions


def test_p6_prompt_targets_the_five_observed_grounding_failure_modes():
    prompt = _writer_instructions(7)

    assert "Return exactly 7 section items" in prompt
    assert "preserve the recorded category" in prompt
    assert "Do not infer reader behavior or purchases" in prompt
    assert 'Coverage details should also be compared' in prompt
    assert 'the article uses evidence for' in prompt
    assert "Preserve source-specific terminology" in prompt


def test_p6_prompt_builder_rejects_an_empty_section_contract():
    with pytest.raises(ValueError, match="at least one input section"):
        _writer_instructions(0)
