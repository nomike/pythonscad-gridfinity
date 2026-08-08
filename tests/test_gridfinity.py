"""Tests for the public Gridfinity API and core specifications."""

from __future__ import annotations

import importlib
import importlib.metadata
from importlib.metadata import PackageNotFoundError

import pytest

import gridfinity
from gridfinity import (
    BASEPLATE_STYLES,
    HEIGHT_MODES,
    LIP_STYLES,
    SCREW_STYLES,
    TAB_STYLES,
    Compartment,
    GridfinityBaseplate,
    GridfinityBin,
    GridfinitySpec,
    GridfinityVaseBin,
    HoleOptions,
    block_base_hole,
    cut_chamfered_cylinder,
    hole_pattern,
    refined_hole,
)


def test_public_exports_and_version():
    assert gridfinity.__all__
    assert set(gridfinity.__all__) <= set(dir(gridfinity))
    assert gridfinity.__version__
    assert isinstance(gridfinity.__version__, str)


def test_version_falls_back_when_distribution_missing(monkeypatch):
    def raise_not_found(_name: str) -> str:
        raise PackageNotFoundError

    with monkeypatch.context() as context:
        context.setattr(importlib.metadata, "version", raise_not_found)
        importlib.reload(gridfinity)
        assert gridfinity.__version__ == "0.0.0+unknown"

    importlib.reload(gridfinity)


def test_style_and_mode_constants():
    assert "thin" in BASEPLATE_STYLES
    assert "weighted" in BASEPLATE_STYLES
    assert "none" in SCREW_STYLES
    assert "full" in TAB_STYLES
    assert "normal" in LIP_STYLES
    assert "units" in HEIGHT_MODES


def test_gridfinity_spec_key_dimensions():
    assert GridfinitySpec.GRID_SIZE == 42.0
    assert GridfinitySpec.HEIGHT_UNIT == 7.0
    assert pytest.approx(3.25) == GridfinitySpec.MAGNET_HOLE_RADIUS
    assert pytest.approx(13.0) == GridfinitySpec.HOLE_FROM_CENTER
    assert (
        pytest.approx(
            GridfinitySpec.BASE_TOP_RADIUS - GridfinitySpec.BASE_PROFILE[3][0]
        )
        == GridfinitySpec.BASE_BOTTOM_RADIUS
    )
    assert (
        GridfinitySpec.STACKING_LIP_PROFILE[3][1] == GridfinitySpec.STACKING_LIP_HEIGHT
    )


def test_hole_options_validation():
    assert HoleOptions(magnet_hole=True).has_any_hole is True
    assert HoleOptions().has_any_hole is False

    with pytest.raises(ValueError, match="mutually exclusive"):
        HoleOptions(magnet_hole=True, refined_hole=True)


def test_compartment_validation():
    Compartment(0, 0, 1, 1)

    with pytest.raises(ValueError, match="must be positive"):
        Compartment(0, 0, 0, 1)

    with pytest.raises(ValueError, match="tab_style"):
        Compartment(0, 0, 1, 1, tab_style="invalid")


def test_public_classes_are_constructible():
    assert GridfinityBaseplate(1, 1) is not None
    assert GridfinityBin(1, 1, 3) is not None
    assert GridfinityVaseBin(1, 1, 3) is not None


def test_low_level_helpers_are_callable():
    assert callable(block_base_hole)
    assert callable(hole_pattern)
    assert callable(refined_hole)
    assert callable(cut_chamfered_cylinder)
