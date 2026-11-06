/*
For licensing see accompanying LICENSE file.
Copyright (C) 2026 Apple Inc. All Rights Reserved.
*/

import Foundation
import FoundationModels
@testable import FoundationModelsCBindings
import FoundationModelsCDeclarations
import Synchronization
import Testing

private let activeBridgedToolBits = Mutex<Int>(0)

private func makeMessageSchema() -> FMGenerationSchemaRef {
  let schema = FoundationModelsCDeclarations.FMGenerationSchemaCreate(
    "MessageArgs",
    "Arguments with a message"
  )
  let prop = FoundationModelsCDeclarations.FMGenerationSchemaPropertyCreate(
    "message",
    "Message string",
    "string",
    false
  )
  FoundationModelsCDeclarations.FMGenerationSchemaAddProperty(schema, prop)
  FoundationModelsCDeclarations.FMRelease(prop)
  return schema
}

@Suite(.serialized)
struct BridgedToolTests {
  @Test func testSynchronousFinishCallInsideForeignCallback() async throws {
    let schema = makeMessageSchema()
    defer { FoundationModelsCDeclarations.FMRelease(schema) }

    var errorCode: Int32 = 0
    var errorDescription: UnsafeMutablePointer<CChar>? = nil
    let toolRef = try #require(
      FoundationModelsCDeclarations.FMBridgedToolCreate(
        "sync_tool",
        "Completes synchronously inside foreignCall",
        schema,
        { contentRef, callId in
          let jsonPtr = FoundationModelsCDeclarations.FMGeneratedContentGetJSONString(contentRef)
          let jsonText = jsonPtr.map { String(cString: $0) } ?? ""
          FoundationModelsCDeclarations.FMFreeString(jsonPtr)
          FoundationModelsCDeclarations.FMRelease(contentRef)

          let bits = activeBridgedToolBits.withLock { $0 }
          let tool = UnsafeRawPointer(bitPattern: bits)!
          "sync:\(jsonText)".withCString { cStr in
            FoundationModelsCDeclarations.FMBridgedToolFinishCall(tool, callId, cStr)
          }
        },
        &errorCode,
        &errorDescription
      )
    )
    activeBridgedToolBits.withLock { $0 = Int(bitPattern: toolRef) }
    defer {
      activeBridgedToolBits.withLock { $0 = 0 }
      FoundationModelsCDeclarations.FMRelease(toolRef)
    }

    let bridgedTool = Unmanaged<BridgedTool>.fromOpaque(toolRef).takeUnretainedValue()
    let args = try GeneratedContent(json: "{\"message\": \"hello\"}")
    let output = try await bridgedTool.call(arguments: args)
    #expect(output.contains("sync:"))
    #expect(output.contains("hello"))
  }

  @Test func testParallelImmediateThreadFinishCallsNeverHang() async throws {
    let schema = makeMessageSchema()
    defer { FoundationModelsCDeclarations.FMRelease(schema) }

    var errorCode: Int32 = 0
    var errorDescription: UnsafeMutablePointer<CChar>? = nil
    let toolRef = try #require(
      FoundationModelsCDeclarations.FMBridgedToolCreate(
        "parallel_fast_tool",
        "Completes from detached OS threads immediately",
        schema,
        { contentRef, callId in
          let jsonPtr = FoundationModelsCDeclarations.FMGeneratedContentGetJSONString(contentRef)
          let jsonText = jsonPtr.map { String(cString: $0) } ?? ""
          FoundationModelsCDeclarations.FMFreeString(jsonPtr)
          FoundationModelsCDeclarations.FMRelease(contentRef)

          // Mirrors Python's threading.Thread(target=_run_in_thread).start()
          // racing against BridgedTool.call storing its continuation.
          Thread.detachNewThread {
            let bits = activeBridgedToolBits.withLock { $0 }
            let tool = UnsafeRawPointer(bitPattern: bits)!
            "done:\(callId):\(jsonText)".withCString { cStr in
              FoundationModelsCDeclarations.FMBridgedToolFinishCall(tool, callId, cStr)
            }
          }
        },
        &errorCode,
        &errorDescription
      )
    )
    activeBridgedToolBits.withLock { $0 = Int(bitPattern: toolRef) }
    defer {
      activeBridgedToolBits.withLock { $0 = 0 }
      FoundationModelsCDeclarations.FMRelease(toolRef)
    }

    let bridgedTool = Unmanaged<BridgedTool>.fromOpaque(toolRef).takeUnretainedValue()

    for round in 0..<10 {
      let count = 20
      let results = try await withThrowingTaskGroup(of: (Int, String).self) { group in
        for i in 0..<count {
          group.addTask {
            let args = try GeneratedContent(json: "{\"message\": \"r\(round)_i\(i)\"}")
            let res = try await bridgedTool.call(arguments: args)
            return (i, res)
          }
        }
        var collected: [Int: String] = [:]
        for try await (idx, value) in group {
          collected[idx] = value
        }
        return collected
      }

      #expect(results.count == count)
      for i in 0..<count {
        let value = try #require(results[i])
        #expect(value.contains("r\(round)_i\(i)"))
      }
    }
  }
}
