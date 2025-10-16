"""
Subtheme classifier for documents.

Provides hierarchical classification within primary themes.
Optimized for high-performance batch processing.
"""

from typing import Callable, Dict, List, Optional

from lifearchivist.utils.logging import track

from .base_subtheme_classifier import BaseSubthemeClassifier
from .financial_subtheme_classifier import FinancialSubthemeClassifier
from .healthcare_subtheme_classifier import HealthcareSubthemeClassifier
from .legal_subtheme_classifier import LegalSubthemeClassifier
from .models import SubthemeResult


class SubthemeClassifier:
    """
    Main subtheme classifier with optimized performance.

    Features:
    - Lazy loading of theme-specific classifiers
    - Shared classifier instances for efficiency
    - Support for parallel classification
    - Easy extensibility for new themes
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize the subtheme classifier.

        Args:
            max_workers: Maximum number of threads for parallel classification
        """
        self.max_workers = max_workers
        self._classifiers: Dict[str, BaseSubthemeClassifier] = {}

        # Define available classifiers (lazy loaded)
        # To add a new theme:
        # 1. Create rules in lifearchivist/tools/subtheme_classifier/rules/<theme>/
        # 2. Create a classifier class that inherits from BaseSubthemeClassifier
        # 3. Add it to this dictionary
        # Note: Type is Callable that takes max_workers and returns BaseSubthemeClassifier
        # The subclasses have __init__(max_workers) that calls super().__init__(theme_name, rules, max_workers)
        self._classifier_classes: Dict[str, Callable[[int], BaseSubthemeClassifier]] = {
            "Financial": FinancialSubthemeClassifier,
            "Healthcare": HealthcareSubthemeClassifier,
            "Legal": LegalSubthemeClassifier,
            # Future themes can be added here:
            # "Professional": ProfessionalSubthemeClassifier,
            # "Personal": PersonalSubthemeClassifier,
            # "Travel": TravelSubthemeClassifier,
        }

    def _get_classifier(self, theme: str) -> Optional[BaseSubthemeClassifier]:
        """
        Get or create classifier for a theme (lazy loading).

        Args:
            theme: Primary theme name

        Returns:
            Theme-specific classifier instance
        """
        if theme not in self._classifiers and theme in self._classifier_classes:
            # Create classifier instance with shared max_workers setting
            # The classifier factory takes max_workers and returns an initialized classifier
            # Each subclass (Financial, Healthcare, Legal) has __init__(max_workers) that
            # internally calls super().__init__(theme_name, rules, max_workers)
            classifier_factory = self._classifier_classes[theme]
            self._classifiers[theme] = classifier_factory(self.max_workers)

        return self._classifiers.get(theme)

    @track(operation="subtheme_classification", track_performance=True)
    def classify(
        self, text: str, primary_theme: str, metadata: Optional[Dict] = None
    ) -> SubthemeResult:
        """
        Classify document into subthemes based on primary theme.

        Args:
            text: Document text content
            primary_theme: Already identified primary theme
            metadata: Optional document metadata (filename, mime_type, etc.)

        Returns:
            SubthemeResult with classified subthemes and confidence scores
        """
        # Get classifier for this theme (lazy loaded)
        classifier = self._get_classifier(primary_theme)

        if not classifier:
            return SubthemeResult(
                primary_theme=primary_theme,
                subthemes=[],
                primary_subtheme=None,
                subclassifications=[],
                primary_subclassification=None,
                subclassification_confidence=None,
                confidence_scores={},
                metadata={"reason": "no_classifier_available"},
            )

        # Delegate to theme-specific classifier
        return classifier.classify(text, metadata)

    def get_supported_themes(self) -> List[str]:
        """Get list of themes that support subtheme classification."""
        return list(self._classifier_classes.keys())

    def get_subthemes_for_theme(self, theme: str) -> List[str]:
        """Get list of possible subthemes for a given theme."""
        classifier = self._get_classifier(theme)
        if classifier:
            return classifier.get_supported_subthemes()
        return []
