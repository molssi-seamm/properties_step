#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `properties_step` package."""

import pytest  # noqa: F401
import properties_step  # noqa: F401


def test_construction():
    """Just create an object and test its type."""
    result = properties_step.Properties()
    assert str(type(result)) == "<class 'properties_step.properties.Properties'>"
