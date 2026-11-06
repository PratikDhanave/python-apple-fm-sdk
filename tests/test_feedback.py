# For licensing see accompanying LICENSE file.
# Copyright (C) 2026 Apple Inc. All Rights Reserved.

"""Unit tests for LanguageModelFeedback and LanguageModelSession.log_feedback_attachment (#5)."""

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import apple_fm_sdk as fm


@fm.generable("Structured desired summary")
class _DesiredSummary:
    headline: str = fm.guide("Short headline")
    score: int = fm.guide("Quality score")


def test_feedback_aliases_and_enum_members():
    assert fm.LanguageModelFeedback.Sentiment is fm.LanguageModelFeedbackSentiment
    assert fm.LanguageModelFeedback.Issue is fm.LanguageModelFeedbackIssue
    assert (
        fm.LanguageModelFeedback.Issue.Category is fm.LanguageModelFeedbackIssueCategory
    )

    assert set(fm.LanguageModelFeedbackSentiment.__members__.keys()) == {
        "POSITIVE",
        "NEGATIVE",
        "NEUTRAL",
    }
    assert set(fm.LanguageModelFeedbackIssueCategory.__members__.keys()) == {
        "UNHELPFUL",
        "TOO_VERBOSE",
        "DID_NOT_FOLLOW_INSTRUCTIONS",
        "INCORRECT",
        "STEREOTYPE_OR_BIAS",
        "SUGGESTIVE_OR_SEXUAL",
        "VULGAR_OR_OFFENSIVE",
        "TRIGGERED_GUARDRAIL_UNEXPECTEDLY",
    }


def test_feedback_issue_validation_and_immutability():
    issue = fm.LanguageModelFeedback.Issue(
        category=fm.LanguageModelFeedback.Issue.Category.TRIGGERED_GUARDRAIL_UNEXPECTEDLY,
        explanation="Unexpected guardrail on harmless input",
    )
    assert issue.to_dict() == {
        "category": int(
            fm.LanguageModelFeedbackIssueCategory.TRIGGERED_GUARDRAIL_UNEXPECTEDLY
        ),
        "explanation": "Unexpected guardrail on harmless input",
    }

    issue_without_explanation = fm.LanguageModelFeedbackIssue(
        category=fm.LanguageModelFeedbackIssueCategory.UNHELPFUL
    )
    assert issue_without_explanation.to_dict() == {
        "category": int(fm.LanguageModelFeedbackIssueCategory.UNHELPFUL)
    }

    with pytest.raises(FrozenInstanceError):
        issue.explanation = "mutated"  # type: ignore[misc]

    with pytest.raises(TypeError, match="LanguageModelFeedbackIssueCategory"):
        fm.LanguageModelFeedbackIssue(category=0)  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="explanation must be a str or None"):
        fm.LanguageModelFeedbackIssue(
            category=fm.LanguageModelFeedbackIssueCategory.INCORRECT,
            explanation=123,  # type: ignore[arg-type]
        )


def test_log_feedback_attachment_minimal_and_with_issues():
    session = fm.LanguageModelSession(instructions="You are a concise assistant.")

    minimal_bytes = session.log_feedback_attachment()
    assert isinstance(minimal_bytes, bytes)
    assert len(minimal_bytes) > 0

    issues = [
        fm.LanguageModelFeedback.Issue(
            category=cat,
            explanation=f"Explanation for {cat.name}",
        )
        for cat in fm.LanguageModelFeedbackIssueCategory
    ]
    detailed_bytes = session.log_feedback_attachment(
        sentiment=fm.LanguageModelFeedback.Sentiment.NEGATIVE,
        issues=issues,
    )
    decoded_text = detailed_bytes.decode("utf-8")
    assert "Explanation for TRIGGERED_GUARDRAIL_UNEXPECTEDLY" in decoded_text
    assert "You are a concise assistant." in decoded_text


@pytest.mark.asyncio
async def test_log_feedback_attachment_from_existing_transcript_and_desired_outputs():
    transcript_path = Path(__file__).parent / "tester_schemas" / "test_transcript.json"
    transcript_dict = json.loads(transcript_path.read_text(encoding="utf-8"))
    transcript = await fm.Transcript.from_dict(transcript_dict)
    session = fm.LanguageModelSession.from_transcript(transcript)

    # 1. Plain-text desired output via desired_output and desired_response_text
    text_attachment = session.log_feedback_attachment(
        sentiment=fm.LanguageModelFeedbackSentiment.NEUTRAL,
        desired_output="2 * 6 = 12",
    )
    assert b"2 * 6 = 12" in text_attachment
    assert b"2 multiplied by 6 equals 12." in text_attachment

    explicit_text_attachment = session.log_feedback_attachment(
        sentiment=fm.LanguageModelFeedbackSentiment.POSITIVE,
        desired_response_text="12",
    )
    assert len(explicit_text_attachment) > 0

    # 2. Structured desired output via @fm.generable and GeneratedContent (including empty dict)
    desired_generable = _DesiredSummary(headline="Math tutor answer", score=5)
    generable_attachment = session.log_feedback_attachment(
        sentiment=fm.LanguageModelFeedbackSentiment.POSITIVE,
        desired_output=desired_generable,
    )
    assert b"Math tutor answer" in generable_attachment

    content = fm.GeneratedContent({"headline": "Direct content", "score": 4})
    content_attachment = session.log_feedback_attachment(
        desired_response_content=content,
    )
    assert b"Direct content" in content_attachment

    empty_content_attachment = session.log_feedback_attachment(
        desired_output=fm.GeneratedContent({}),
    )
    assert len(empty_content_attachment) > 0

    # 3. Transcript entry dictionary desired output
    response_entry = dict(transcript_dict["transcript"]["entries"][-1])
    response_entry["contents"] = [
        {"id": "0", "type": "text", "text": "Desired transcript entry text"}
    ]
    entry_attachment = session.log_feedback_attachment(
        sentiment=fm.LanguageModelFeedbackSentiment.NEGATIVE,
        desired_output=response_entry,
    )
    assert b"Desired transcript entry text" in entry_attachment


def test_log_feedback_attachment_error_validation():
    session = fm.LanguageModelSession()

    with pytest.raises(ValueError, match="at most one"):
        session.log_feedback_attachment(
            desired_output="a",
            desired_response_text="b",
        )

    with pytest.raises(ValueError, match="at most one"):
        session.log_feedback_attachment(
            desired_response_text="a",
            desired_response_content=fm.GeneratedContent({"k": "v"}),
        )

    with pytest.raises(TypeError, match="sentiment"):
        session.log_feedback_attachment(sentiment="negative")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="issues"):
        session.log_feedback_attachment(issues="not-a-list")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="LanguageModelFeedbackIssue"):
        session.log_feedback_attachment(issues=["not-an-issue"])  # type: ignore[list-item]

    with pytest.raises(TypeError, match="desired_output"):
        session.log_feedback_attachment(desired_output=12345)  # type: ignore[arg-type]

    with pytest.raises(fm.DecodingFailureError):
        session.log_feedback_attachment(desired_output={"invalid_entry": True})
