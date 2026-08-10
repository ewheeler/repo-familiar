"""Static Quarto Application."""

from .analysis import analyze
from .models import AnalysisResult

__all__ = ["AnalysisResult", "analyze"]
