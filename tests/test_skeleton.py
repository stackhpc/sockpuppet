#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from sockpuppet.skeleton import fib

__author__ = "Will Szumski"
__copyright__ = "Will Szumski"
__license__ = "apache"


def test_fib():
    assert fib(1) == 1
    assert fib(2) == 1
    assert fib(7) == 13
    with pytest.raises(AssertionError):
        fib(-10)
