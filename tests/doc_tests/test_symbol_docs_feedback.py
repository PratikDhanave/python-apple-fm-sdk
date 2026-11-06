# For licensing see accompanying LICENSE file.
# Copyright (C) 2026 Apple Inc. All Rights Reserved.

"""
Test all code snippets from feedback Python library code source documentation.
"""


def test_feedback_module_example():
    """Test from: src/apple_fm_sdk/feedback.py - Module docstring"""
    ##############################################################################
    # From: src/apple_fm_sdk/feedback.py
    # class, function, or other entity name: Module - Creating feedback issues and logging an attachment
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
    ##############################################################################

    assert len(attachment_bytes) > 0


def test_feedback_issue_example():
    """Test from: src/apple_fm_sdk/feedback.py - LanguageModelFeedbackIssue"""
    ##############################################################################
    # From: src/apple_fm_sdk/feedback.py
    # class, function, or other entity name: LanguageModelFeedbackIssue
    import apple_fm_sdk as fm

    issue = fm.LanguageModelFeedbackIssue(
        category=fm.LanguageModelFeedbackIssueCategory.INCORRECT,
        explanation="2 + 2 should equal 4.",
    )
    ##############################################################################

    assert issue.category == fm.LanguageModelFeedbackIssueCategory.INCORRECT


def test_feedback_container_example():
    """Test from: src/apple_fm_sdk/feedback.py - LanguageModelFeedback"""
    ##############################################################################
    # From: src/apple_fm_sdk/feedback.py
    # class, function, or other entity name: LanguageModelFeedback
    import apple_fm_sdk as fm

    sentiment = fm.LanguageModelFeedback.Sentiment.NEGATIVE
    issue = fm.LanguageModelFeedback.Issue(
        category=fm.LanguageModelFeedback.Issue.Category.TOO_VERBOSE,
        explanation="Response repeated the same point three times.",
    )
    ##############################################################################

    assert sentiment == fm.LanguageModelFeedbackSentiment.NEGATIVE
    assert issue.category == fm.LanguageModelFeedbackIssueCategory.TOO_VERBOSE


def test_session_log_feedback_attachment_example():
    """Test from: src/apple_fm_sdk/session.py - LanguageModelSession.log_feedback_attachment"""
    ##############################################################################
    # From: src/apple_fm_sdk/session.py
    # class, function, or other entity name: LanguageModelSession.log_feedback_attachment
    import apple_fm_sdk as fm

    session = fm.LanguageModelSession(instructions="Summarize the provided note.")
    attachment = session.log_feedback_attachment(
        sentiment=fm.LanguageModelFeedback.Sentiment.NEGATIVE,
        issues=[
            fm.LanguageModelFeedback.Issue(
                category=fm.LanguageModelFeedback.Issue.Category.TRIGGERED_GUARDRAIL_UNEXPECTEDLY,
                explanation="Benign input triggered a guardrail violation.",
            )
        ],
        desired_output="A concise one-sentence summary.",
    )
    ##############################################################################

    assert len(attachment) > 0
