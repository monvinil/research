"""Derived analytics layer — transforms raw connector data into computed indicators."""

from .timeseries import TimeSeriesAnalyzer
from .cross_correlation import CrossCorrelator
from .composite_indices import CompositeIndexBuilder
from .structural import StructuralAnalyzer
from .methodology import MethodologyTracker
from .cross_synthesis import CrossDomainSynthesizer
from .business_rotation import BusinessRotationEngine

__all__ = [
    'TimeSeriesAnalyzer', 'CrossCorrelator',
    'CompositeIndexBuilder', 'StructuralAnalyzer',
    'MethodologyTracker', 'CrossDomainSynthesizer',
    'BusinessRotationEngine',
]
