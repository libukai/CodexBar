import Foundation
@testable import CodexBarCore

struct CostUsageTestEnvironment {
    let root: URL
    let cacheRoot: URL
    let codexSessionsRoot: URL

    init() throws {
        self.root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        self.cacheRoot = self.root.appendingPathComponent("cache")
        self.codexSessionsRoot = self.root.appendingPathComponent("codex-home/sessions")
        try FileManager.default.createDirectory(at: self.cacheRoot, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: self.codexSessionsRoot, withIntermediateDirectories: true)
    }

    func cleanup() {
        try? FileManager.default.removeItem(at: self.root)
    }

    func makeLocalNoon(year: Int, month: Int, day: Int) throws -> Date {
        var components = DateComponents()
        components.year = year
        components.month = month
        components.day = day
        components.hour = 12
        guard let date = Calendar.current.date(from: components) else {
            throw NSError(domain: "CostUsageTestEnvironment", code: 1)
        }
        return date
    }

    func isoString(for date: Date) -> String {
        ISO8601DateFormatter().string(from: date)
    }

    func jsonl(_ records: [[String: Any]]) throws -> String {
        try records.map {
            try String(decoding: JSONSerialization.data(withJSONObject: $0, options: [.sortedKeys]), as: UTF8.self)
        }.joined(separator: "\n") + "\n"
    }

    func writeCodexSessionFile(day: Date, filename: String, contents: String) throws -> URL {
        let parts = Calendar.current.dateComponents([.year, .month, .day], from: day)
        let directory = self.codexSessionsRoot.appendingPathComponent(
            String(format: "%04d/%02d/%02d", parts.year!, parts.month!, parts.day!))
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let file = directory.appendingPathComponent(filename)
        try contents.write(to: file, atomically: true, encoding: .utf8)
        return file
    }
}
