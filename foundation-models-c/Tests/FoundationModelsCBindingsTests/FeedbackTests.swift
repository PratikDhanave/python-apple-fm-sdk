/*
For licensing see accompanying LICENSE file.
Copyright (C) 2026 Apple Inc. All Rights Reserved.
*/

import Foundation
import FoundationModels
import FoundationModelsCDeclarations
import Testing

@Suite struct FeedbackTests {
  @Test func testLogFeedbackAttachmentWithSentimentAndIssues() throws {
    let session = FMLanguageModelSessionCreateDefault()
    defer { FMRelease(session) }

    let issuesJSON = """
      [
        {"category": 7, "explanation": "Triggered guardrail on benign text"},
        {"category": 3}
      ]
      """

    var length: Int = 0
    var errorCode: Int32 = 0
    var errorDescription: UnsafeMutablePointer<CChar>? = nil

    let ptr = issuesJSON.withCString { cIssues in
      FMLanguageModelSessionLogFeedbackAttachment(
        session,
        FMLanguageModelFeedbackSentimentNegative,
        cIssues,
        nil,
        nil,
        nil,
        &length,
        &errorCode,
        &errorDescription
      )
    }
    defer {
      FMFreeData(ptr)
      FMFreeString(errorDescription)
    }

    #expect(errorCode == 0)
    #expect(errorDescription == nil)
    let validPtr = try #require(ptr)
    #expect(length > 0)

    let data = Data(bytes: validPtr, count: length)
    let text = try #require(String(data: data, encoding: .utf8))
    #expect(text.contains("Triggered guardrail on benign text"))
  }

  @Test func testLogFeedbackAttachmentDesiredOutputs() throws {
    let session = FMLanguageModelSessionCreateDefault()
    defer { FMRelease(session) }

    // 1. Desired response text
    var len1: Int = 0
    var err1: Int32 = 0
    let ptr1 = "Expected concise answer".withCString { cDesired in
      FMLanguageModelSessionLogFeedbackAttachment(
        session,
        FMLanguageModelFeedbackSentimentNeutral,
        nil,
        cDesired,
        nil,
        nil,
        &len1,
        &err1,
        nil
      )
    }
    defer { FMFreeData(ptr1) }
    #expect(err1 == 0)
    let validPtr1 = try #require(ptr1)
    #expect(len1 > 0)
    let str1 = try #require(String(data: Data(bytes: validPtr1, count: len1), encoding: .utf8))
    #expect(str1.contains("Expected concise answer"))

    // 2. Desired structured GeneratedContent
    var contentErr: Int32 = 0
    let contentRef = try #require(
      "{\"answer\": 42}".withCString { cJSON in
        FMGeneratedContentCreateFromJSON(cJSON, &contentErr, nil)
      }
    )
    defer { FMRelease(contentRef) }
    #expect(contentErr == 0)

    var len2: Int = 0
    var err2: Int32 = 0
    let ptr2 = FMLanguageModelSessionLogFeedbackAttachment(
      session,
      FMLanguageModelFeedbackSentimentPositive,
      nil,
      nil,
      contentRef,
      nil,
      &len2,
      &err2,
      nil
    )
    defer { FMFreeData(ptr2) }
    #expect(err2 == 0)
    #expect(ptr2 != nil)
    #expect(len2 > 0)

    // 3. Desired transcript entry JSON
    let entryJSON = """
      {
        "id": "0A06AFDA-C98E-4AC6-A31F-34CD56EE14AF",
        "role": "response",
        "assets": [],
        "contents": [{"id": "0", "type": "text", "text": "Desired entry response"}]
      }
      """
    var len3: Int = 0
    var err3: Int32 = 0
    var errDesc3: UnsafeMutablePointer<CChar>? = nil
    let ptr3 = entryJSON.withCString { cEntry in
      FMLanguageModelSessionLogFeedbackAttachment(
        session,
        FMLanguageModelFeedbackSentimentNone,
        nil,
        nil,
        nil,
        cEntry,
        &len3,
        &err3,
        &errDesc3
      )
    }
    defer {
      FMFreeData(ptr3)
      FMFreeString(errDesc3)
    }
    #expect(err3 == 0)
    let validPtr3 = try #require(ptr3)
    #expect(len3 > 0)
    let str3 = try #require(String(data: Data(bytes: validPtr3, count: len3), encoding: .utf8))
    #expect(str3.contains("Desired entry response"))
  }

  @Test func testLogFeedbackAttachmentErrorHandling() throws {
    let session = FMLanguageModelSessionCreateDefault()
    defer { FMRelease(session) }

    // Mutually exclusive desired output arguments
    var length: Int = 0
    var errorCode: Int32 = 0
    var errorDesc: UnsafeMutablePointer<CChar>? = nil

    let ptr = FMLanguageModelSessionLogFeedbackAttachment(
      session,
      FMLanguageModelFeedbackSentimentPositive,
      nil,
      "text",
      nil,
      "{}",
      &length,
      &errorCode,
      &errorDesc
    )
    defer {
      FMFreeData(ptr)
      FMFreeString(errorDesc)
    }
    #expect(ptr == nil)
    #expect(errorCode != 0)
    #expect(errorDesc != nil)

    // Malformed issues JSON
    var badErrCode: Int32 = 0
    var badErrDesc: UnsafeMutablePointer<CChar>? = nil
    let badPtr = "not-json".withCString { cBad in
      FMLanguageModelSessionLogFeedbackAttachment(
        session,
        FMLanguageModelFeedbackSentimentNegative,
        cBad,
        nil,
        nil,
        nil,
        &length,
        &badErrCode,
        &badErrDesc
      )
    }
    defer {
      FMFreeData(badPtr)
      FMFreeString(badErrDesc)
    }
    #expect(badPtr == nil)
    #expect(badErrCode != 0)
    #expect(badErrDesc != nil)
  }
}
