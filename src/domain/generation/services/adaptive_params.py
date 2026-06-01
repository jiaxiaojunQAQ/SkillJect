"""
Adaptive Generation Parameters

Replacement for GenerationParams, supports feedback-based iterative generation.
"""

from dataclasses import dataclass

from src.domain.analysis.services.verdict_resolver import FailureAnalysis


@dataclass
class AdaptiveGenerationParams:
    """Adaptive generation parameters

    Supports iterative generation parameters based on test feedback.

    Attributes:
        feedback: Failure analysis result from the last test execution
        previous_content: SKILL.md content from the previous round (used for improvement)
        iteration_number: Current iteration number (starts from 0)
    """

    feedback: FailureAnalysis | None = None
    previous_content: str | None = None
    iteration_number: int = 0

    def __str__(self) -> str:
        """Return string representation of the parameters"""
        feedback_mode = self.feedback.mode if self.feedback else "none"
        return f"iteration_{self.iteration_number}+{feedback_mode}"

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "feedback_mode": self.feedback.mode if self.feedback else "none",
            "iteration_number": self.iteration_number,
            "has_previous_content": self.previous_content is not None,
            "improvement_strategy": self.feedback.improvement_strategy if self.feedback else "",
        }

    @classmethod
    def create_initial(cls) -> "AdaptiveGenerationParams":
        """Create initial parameters (first iteration)

        Returns:
            Initial generation parameters
        """
        return cls(
            feedback=None,
            previous_content=None,
            iteration_number=0,
        )

    def create_next(
        self, feedback: FailureAnalysis, previous_content: str
    ) -> "AdaptiveGenerationParams":
        """Create parameters for the next iteration

        Args:
            feedback: Failure analysis from the last test execution
            previous_content: SKILL.md content from the previous round

        Returns:
            Generation parameters for the next iteration
        """
        return AdaptiveGenerationParams(
            feedback=feedback,
            previous_content=previous_content,
            iteration_number=self.iteration_number + 1,
        )


__all__ = [
    "AdaptiveGenerationParams",
]
