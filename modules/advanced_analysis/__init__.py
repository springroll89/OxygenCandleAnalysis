#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级分析模块包 - 完整版
"""

from .kinetics_analyzer import KineticsAnalyzer
from .spc_controller import SPCController
from .ml_predictor import MLPredictor
from .fault_diagnostics import FaultDiagnosticSystem
from .doe_designer import DOEDesigner
from .cost_analyzer import CostAnalyzer

__version__ = '1.0.0'

__all__ = [
    'KineticsAnalyzer',
    'SPCController',
    'MLPredictor',
    'FaultDiagnosticSystem',
    'DOEDesigner',
    'CostAnalyzer'
]