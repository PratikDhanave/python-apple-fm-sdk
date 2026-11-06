# For licensing see accompanying LICENSE file.
# Copyright (C) 2026 Apple Inc. All Rights Reserved.

"""
Feedback types for serializing language model evaluation and safety reports.

This module mirrors Swift's ``LanguageModelFeedback`` API, enabling Python
applications and evaluation notebooks to record user or developer sentiment
and categorized model issues for submission through Feedback Assistant via
:meth:`~apple_fm_sdk.session.LanguageModelSession.log_feedback_attachment`.

The main classes provided are:

* :class:`LanguageModelFeedback` - Namespace grouping feedback sentiment and issue types
* :class:`LanguageModelFeedbackSentiment` - Enumeration of overall response sentiments
* :class:`LanguageModelFeedbackIssue` - Categorized issue report with optional explanation
* :class:`LanguageModelFeedbackIssueCategory` - Enumeration of model issue categories

Example:
    Creating feedback issues and logging an attachment::

        import apple_fm_sdk as fm

        session = fm.LanguageModelSession(instructions="You are a helpful assistant.")
        issue = fm.LanguageModelFeedback.Issue(
            category=fm.LanguageModelFeedback.Issue.Category.TRIGGERED_GUARDRAIL_UNEXPECTEDLY,
            explanation="Benign prompt triggered a guardrail error.",
        )
        attachment_bytes = session.log_feedback_attachment(
            sentiment=fm.LanguageModelFeedback.Sentiment.NEGATIVE,
            issues=[issue],
            desired_output="Expected a helpful response.",
        )
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, ClassVar


class LanguageModelFeedbackSentiment(IntEnum):
    """Sentiment regarding a foundation model's response.

    Mirrors Swift's ``LanguageModelFeedback.Sentiment``.

    Attributes:
        POSITIVE: A positive sentiment toward the model's response.
        NEGATIVE: A negative sentiment toward the model's response.
        NEUTRAL: A neutral sentiment toward the model's response.
    """

    POSITIVE = 1
    NEGATIVE = 2
    NEUTRAL = 3


class LanguageModelFeedbackIssueCategory(IntEnum):
    """Categories of issues that may occur in a foundation model's response.

    Mirrors Swift's ``LanguageModelFeedback.Issue.Category``.

    Attributes:
        UNHELPFUL: The response was not helpful.
        TOO_VERBOSE: The response was overly verbose.
        DID_NOT_FOLLOW_INSTRUCTIONS: The model did not follow instructions.
        INCORRECT: The model provided factually incorrect output.
        STEREOTYPE_OR_BIAS: The model exhibited stereotype or bias.
        SUGGESTIVE_OR_SEXUAL: The model produced suggestive or sexual output.
        VULGAR_OR_OFFENSIVE: The model produced vulgar or offensive output.
        TRIGGERED_GUARDRAIL_UNEXPECTEDLY: A safety guardrail was triggered unexpectedly.
    """

    UNHELPFUL = 0
    TOO_VERBOSE = 1
    DID_NOT_FOLLOW_INSTRUCTIONS = 2
    INCORRECT = 3
    STEREOTYPE_OR_BIAS = 4
    SUGGESTIVE_OR_SEXUAL = 5
    VULGAR_OR_OFFENSIVE = 6
    TRIGGERED_GUARDRAIL_UNEXPECTEDLY = 7


@dataclass(frozen=True)
class LanguageModelFeedbackIssue:
    """An issue identified with a foundation model's response.

    Mirrors Swift's ``LanguageModelFeedback.Issue``.

    :param category: The category describing the issue.
    :type category: LanguageModelFeedbackIssueCategory
    :param explanation: Optional free-form explanation providing additional context.
    :type explanation: Optional[str]

    Example:
        Creating a feedback issue::

            import apple_fm_sdk as fm

            issue = fm.LanguageModelFeedbackIssue(
                category=fm.LanguageModelFeedbackIssueCategory.INCORRECT,
                explanation="2 + 2 should equal 4.",
            )
    """

    Category: ClassVar[type[LanguageModelFeedbackIssueCategory]] = (
        LanguageModelFeedbackIssueCategory
    )

    category: LanguageModelFeedbackIssueCategory
    explanation: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.category, LanguageModelFeedbackIssueCategory):
            raise TypeError(
                "category must be an instance of LanguageModelFeedbackIssueCategory"
            )
        if self.explanation is not None and not isinstance(self.explanation, str):
            raise TypeError("explanation must be a str or None")

    def to_dict(self) -> dict[str, Any]:
        """Serialize this issue into the dictionary payload expected by C bindings."""
        payload: dict[str, Any] = {"category": int(self.category)}
        if self.explanation is not None:
            payload["explanation"] = self.explanation
        return payload


class LanguageModelFeedback:
    """Container for language model feedback types.

    Mirrors Swift's ``LanguageModelFeedback`` type hierarchy, exposing
    :attr:`Sentiment` (:class:`LanguageModelFeedbackSentiment`) and
    :attr:`Issue` (:class:`LanguageModelFeedbackIssue`).

    Example:
        Using nested Swift-style aliases::

            import apple_fm_sdk as fm

            sentiment = fm.LanguageModelFeedback.Sentiment.NEGATIVE
            issue = fm.LanguageModelFeedback.Issue(
                category=fm.LanguageModelFeedback.Issue.Category.TOO_VERBOSE,
                explanation="Response repeated the same point three times.",
            )
    """

    Sentiment = LanguageModelFeedbackSentiment
    Issue = LanguageModelFeedbackIssue
