"""Tests for substrate color shift simulator."""

import pytest

from mcp_print.tools.substrate import substrate_simulator


class TestBasicShifts:
    def test_glossy_minimal_shift(self) -> None:
        result = substrate_simulator(c=50, m=30, y=20, k=10, substrate="glossy_coated")
        assert result["delta_e_from_original"] < 5

    def test_newsprint_large_shift(self) -> None:
        result = substrate_simulator(c=50, m=30, y=20, k=10, substrate="newsprint")
        assert result["delta_e_from_original"] > 3

    def test_kraft_tint_visible(self) -> None:
        result = substrate_simulator(c=0, m=0, y=0, k=0, substrate="kraft")
        sim = result["simulated"]
        # Kraft tint adds m=6, y=15, k=8 — should be clearly nonzero
        assert sim["m"] > 0
        assert sim["y"] > 0
        assert sim["k"] > 0


class TestDotGain:
    def test_dot_gain_increases_values(self) -> None:
        result = substrate_simulator(c=50, m=50, y=50, k=50, substrate="uncoated")
        sim = result["simulated"]
        assert sim["c"] > 50
        assert sim["m"] > 50
        assert sim["y"] > 50
        assert sim["k"] > 50

    def test_clamping_at_100(self) -> None:
        result = substrate_simulator(c=95, m=95, y=95, k=95, substrate="newsprint")
        sim = result["simulated"]
        assert sim["c"] <= 100
        assert sim["m"] <= 100
        assert sim["y"] <= 100
        assert sim["k"] <= 100

    def test_zero_cmyk_only_tint_and_absorption(self) -> None:
        result = substrate_simulator(c=0, m=0, y=0, k=0, substrate="glossy_coated")
        sim = result["simulated"]
        # Dot gain on 0 is 0, but absorption adds to K
        assert sim["k"] >= 0
        # Glossy has no tint
        assert sim["c"] == 0
        assert sim["m"] == 0
        assert sim["y"] == 0


class TestPureBlack:
    def test_pure_black_dot_gain(self) -> None:
        result = substrate_simulator(c=0, m=0, y=0, k=100, substrate="uncoated")
        sim = result["simulated"]
        # K=100 with dot gain formula: 100 + gain * 100 * (1-1) = 100
        # No dot gain at extremes (100%), but tint and absorption still apply
        assert sim["k"] == 100  # dot gain 0 at 100%, absorption on (100-100)=0


class TestMidtoneDotGain:
    def test_midtone_higher_gain_than_extreme(self) -> None:
        mid = substrate_simulator(c=50, m=0, y=0, k=0, substrate="uncoated")
        low = substrate_simulator(c=10, m=0, y=0, k=0, substrate="uncoated")
        # At 50%, gain effect should be stronger than at 10%
        mid_shift = mid["simulated"]["c"] - 50
        low_shift = low["simulated"]["c"] - 10
        assert mid_shift > low_shift


class TestAllSubstrates:
    def test_all_substrates_produce_valid_output(self) -> None:
        for sub in ("glossy_coated", "matte_coated", "uncoated", "newsprint", "kraft", "recycled"):
            result = substrate_simulator(c=40, m=30, y=20, k=10, substrate=sub)
            assert result["substrate"] == sub
            assert result["delta_e_from_original"] >= 0
            sim = result["simulated"]
            for ch in ("c", "m", "y", "k"):
                assert 0 <= sim[ch] <= 100


class TestAllMethods:
    def test_all_methods_produce_valid_output(self) -> None:
        for method in ("offset", "digital", "flexo"):
            result = substrate_simulator(
                c=40, m=30, y=20, k=10,
                substrate="uncoated", print_method=method,
            )
            assert result["print_method"] == method
            assert result["delta_e_from_original"] >= 0

    def test_digital_less_shift_than_offset(self) -> None:
        digital = substrate_simulator(c=50, m=30, y=20, k=10, substrate="uncoated", print_method="digital")
        offset = substrate_simulator(c=50, m=30, y=20, k=10, substrate="uncoated", print_method="offset")
        assert digital["delta_e_from_original"] < offset["delta_e_from_original"]


class TestDeltaE:
    def test_delta_e_consistency(self) -> None:
        result = substrate_simulator(c=50, m=30, y=20, k=10, substrate="glossy_coated")
        assert isinstance(result["delta_e_from_original"], float)
        assert result["delta_e_from_original"] >= 0


class TestWarnings:
    def test_minimal_shift_warning(self) -> None:
        result = substrate_simulator(c=10, m=5, y=5, k=0, substrate="glossy_coated", print_method="digital")
        assert "Minimal" in result["warning"] or "Noticeable" in result["warning"]

    def test_high_shift_warning(self) -> None:
        result = substrate_simulator(c=50, m=40, y=30, k=20, substrate="newsprint", print_method="flexo")
        # Newsprint + flexo = large shift
        assert "shift" in result["warning"].lower()


class TestOutputStructure:
    def test_hex_present(self) -> None:
        result = substrate_simulator(c=50, m=30, y=20, k=10, substrate="uncoated")
        assert result["original"]["hex"].startswith("#")
        assert result["simulated"]["hex"].startswith("#")

    def test_adjustments_present(self) -> None:
        result = substrate_simulator(c=50, m=30, y=20, k=10, substrate="uncoated")
        adj = result["adjustments"]
        assert "dot_gain_applied" in adj
        assert "absorption_k_added" in adj
        assert "tint_offsets" in adj


class TestValidation:
    def test_cmyk_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="c must be between"):
            substrate_simulator(c=110, m=0, y=0, k=0)

    def test_negative_cmyk_raises(self) -> None:
        with pytest.raises(ValueError, match="m must be between"):
            substrate_simulator(c=0, m=-5, y=0, k=0)

    def test_unknown_substrate_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown substrate"):
            substrate_simulator(c=50, m=30, y=20, k=10, substrate="canvas")

    def test_unknown_method_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown print_method"):
            substrate_simulator(c=50, m=30, y=20, k=10, print_method="gravure")
