..
    For licensing see accompanying LICENSE file.
    Copyright (C) 2026 Apple Inc. All Rights Reserved.

LanguageModelFeedback
=====================

This page documents the feedback types used with :meth:`~apple_fm_sdk.LanguageModelSession.log_feedback_attachment` to package transcripts, sentiment, and issue reports for Feedback Assistant.

.. note::
   **Swift Equivalent:** This Python API corresponds to `LanguageModelFeedback <https://developer.apple.com/documentation/foundationmodels/languagemodelfeedback>`_ in the Swift Foundation Models framework.

LanguageModelFeedback
---------------------

.. autoclass:: apple_fm_sdk.LanguageModelFeedback
   :members:
   :undoc-members:

LanguageModelFeedbackSentiment
------------------------------

.. autoclass:: apple_fm_sdk.LanguageModelFeedbackSentiment
   :members:
   :undoc-members:
   :exclude-members: POSITIVE, NEGATIVE, NEUTRAL

LanguageModelFeedbackIssue
--------------------------

.. autoclass:: apple_fm_sdk.LanguageModelFeedbackIssue
   :members:
   :undoc-members:

LanguageModelFeedbackIssueCategory
----------------------------------

.. autoclass:: apple_fm_sdk.LanguageModelFeedbackIssueCategory
   :members:
   :undoc-members:
   :exclude-members: UNHELPFUL, TOO_VERBOSE, DID_NOT_FOLLOW_INSTRUCTIONS, INCORRECT, STEREOTYPE_OR_BIAS, SUGGESTIVE_OR_SEXUAL, VULGAR_OR_OFFENSIVE, TRIGGERED_GUARDRAIL_UNEXPECTEDLY
