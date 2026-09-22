import AppKit
import SwiftUI
import Security

// Inter Bold B, outlined from rsms/inter (wght 700, opsz 14), inside a square.
// The vector outline needs no installed font. See docs/INTER-LICENSE.txt.
enum BCUIcon {
    private static func letter() -> CGPath {
        let path = CGMutablePath()
        path.move(to: CGPoint(x: 134.642, y: 0.000))
        path.addLine(to: CGPoint(x: 134.642, y: 1490.000))
        path.addLine(to: CGPoint(x: 726.359, y: 1490.000))
        path.addQuadCurve(to: CGPoint(x: 999.249, y: 1440.550), control: CGPoint(x: 889.919, y: 1490.000))
        path.addQuadCurve(to: CGPoint(x: 1163.208, y: 1304.840), control: CGPoint(x: 1108.578, y: 1391.100))
        path.addQuadCurve(to: CGPoint(x: 1217.838, y: 1107.419), control: CGPoint(x: 1217.838, y: 1218.579))
        path.addQuadCurve(to: CGPoint(x: 1182.758, y: 953.509), control: CGPoint(x: 1217.838, y: 1018.979))
        path.addQuadCurve(to: CGPoint(x: 1087.318, y: 846.450), control: CGPoint(x: 1147.678, y: 888.039))
        path.addQuadCurve(to: CGPoint(x: 950.079, y: 787.400), control: CGPoint(x: 1026.958, y: 804.860))
        path.addLine(to: CGPoint(x: 950.079, y: 772.320))
        path.addQuadCurve(to: CGPoint(x: 1108.478, y: 724.590), control: CGPoint(x: 1034.118, y: 768.860))
        path.addQuadCurve(to: CGPoint(x: 1229.338, y: 600.670), control: CGPoint(x: 1182.838, y: 680.320))
        path.addQuadCurve(to: CGPoint(x: 1275.838, y: 410.499), control: CGPoint(x: 1275.838, y: 521.020))
        path.addQuadCurve(to: CGPoint(x: 1218.128, y: 200.130), control: CGPoint(x: 1275.838, y: 293.100))
        path.addQuadCurve(to: CGPoint(x: 1046.639, y: 53.580), control: CGPoint(x: 1160.418, y: 107.160))
        path.addQuadCurve(to: CGPoint(x: 764.418, y: 0.000), control: CGPoint(x: 932.859, y: 0.000))
        path.closeSubpath()
        path.move(to: CGPoint(x: 440.197, y: 251.157))
        path.addLine(to: CGPoint(x: 703.801, y: 251.157))
        path.addQuadCurve(to: CGPoint(x: 900.003, y: 303.037), control: CGPoint(x: 838.382, y: 251.157))
        path.addQuadCurve(to: CGPoint(x: 961.623, y: 439.498), control: CGPoint(x: 961.623, y: 354.918))
        path.addQuadCurve(to: CGPoint(x: 931.183, y: 551.309), control: CGPoint(x: 961.623, y: 502.619))
        path.addQuadCurve(to: CGPoint(x: 844.742, y: 627.740), control: CGPoint(x: 900.743, y: 600.000))
        path.addQuadCurve(to: CGPoint(x: 711.641, y: 655.481), control: CGPoint(x: 788.742, y: 655.481))
        path.addLine(to: CGPoint(x: 440.197, y: 655.481))
        path.closeSubpath()
        path.move(to: CGPoint(x: 440.197, y: 864.079))
        path.addLine(to: CGPoint(x: 680.721, y: 864.079))
        path.addQuadCurve(to: CGPoint(x: 797.912, y: 887.479), control: CGPoint(x: 746.141, y: 864.079))
        path.addQuadCurve(to: CGPoint(x: 879.583, y: 954.340), control: CGPoint(x: 849.682, y: 910.880))
        path.addQuadCurve(to: CGPoint(x: 909.483, y: 1058.061), control: CGPoint(x: 909.483, y: 997.801))
        path.addQuadCurve(to: CGPoint(x: 851.703, y: 1190.203), control: CGPoint(x: 909.483, y: 1139.402))
        path.addQuadCurve(to: CGPoint(x: 686.721, y: 1241.003), control: CGPoint(x: 793.922, y: 1241.003))
        path.addLine(to: CGPoint(x: 440.197, y: 1241.003))
        path.closeSubpath()
        return path
    }

    static func draw(_ size: CGFloat, template: Bool) -> NSImage {
        let image = NSImage(size: NSSize(width: size, height: size))
        image.lockFocus()
        let scale = size / 24
        let canvas = NSAffineTransform()
        canvas.scale(by: scale)
        canvas.concat()
        let tile = NSBezierPath(rect: NSRect(x: 1.5, y: 1.5, width: 21, height: 21))
        if !template {
            NSColor.black.setFill()
            tile.fill()
        }
        let ink = template ? NSColor.black : NSColor.white
        ink.setStroke()
        tile.lineWidth = 1.5
        tile.lineJoinStyle = .miter
        tile.stroke()
        let mark = letter()
        let bounds = mark.boundingBoxOfPath
        let factor = 13.5 / bounds.height
        var placement = CGAffineTransform(a: factor, b: 0, c: 0, d: factor,
                                          tx: 12 - bounds.midX * factor, ty: 12 - bounds.midY * factor)
        if let context = NSGraphicsContext.current?.cgContext,
           let centered = mark.copy(using: &placement) {
            context.setFillColor(ink.cgColor)
            context.addPath(centered)
            context.fillPath()
        }
        image.unlockFocus()
        image.isTemplate = template
        return image
    }
}

struct RouterHealth: Decodable {
    let service: String
    let home: String
    let models: Int
}

struct UsageReport: Decodable {
    let periodDays: Int
    let generatedAt: String
    let pricingCatalogFetchedAt: String
    let ledgerStatus: String
    let warnings: [String]
    let summary: UsageTotals
    let models: [String: UsageTotals]
}

struct UsageTotals: Decodable {
    let displayName: String?
    let records: Int
    let desktopRequests: Int
    let legacyRecords: Int
    let inputTokens: Int
    let cachedInputTokens: Int
    let outputTokens: Int
    let reasoningOutputTokens: Int
    let totalTokens: Int
    let reportedCostUsd: Double
    let estimatedCostUsd: Double
    let knownCostUsd: Double
    let totalCostUsd: Double?
    let costSource: String
    let unpricedRecords: Int
}

struct UsageRow: Identifiable {
    let id: String
    let totals: UsageTotals
    var name: String { totals.displayName ?? id }
}

enum DesktopPage: String, CaseIterable, Identifiable {
    case overview = "Overview", setup = "Setup", models = "Models", account = "Account"
    case agents = "Agents", traffic = "Routing", usage = "Usage", settings = "Settings"
    var id: String { rawValue }
    var icon: String {
        switch self {
        case .overview: return "square.grid.2x2"
        case .setup: return "sparkles"
        case .models: return "cube"
        case .account: return "key"
        case .agents: return "person.2"
        case .traffic: return "arrow.triangle.branch"
        case .usage: return "chart.bar"
        case .settings: return "gearshape"
        }
    }
}

struct DesktopSnapshot: Decodable {
    struct Model: Decodable, Identifiable {
        let id: String
        let name: String
        let reasoningEffort: String?
    }
    let python: String
    let codexAvailable: Bool
    let cliInstalled: Bool
    let models: [Model]
    let defaultModel: String
    let agentModel: String
    let agentReasoning: String
    let agentLimit: Int
    let agentsManaged: Bool
    let traffic: [String: Double]
}

enum BCUCredentials {
    static let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: "com.codex.openrouter-models", kSecAttrAccount as String: "openrouter-api-key"]
    static func present() -> Bool {
        // Presence only: never retrieve the saved value or prompt just to draw UI.
        var attributes = query
        attributes[kSecReturnAttributes as String] = true
        attributes[kSecUseAuthenticationUI as String] = kSecUseAuthenticationUIFail
        let result = SecItemCopyMatching(attributes as CFDictionary, nil)
        return result == errSecSuccess || result == errSecInteractionNotAllowed
    }
    static func save(_ key: String) -> String? {
        let value = key.trimmingCharacters(in: .whitespacesAndNewlines)
        guard value.hasPrefix("sk-or-"), value.count > 20, !value.contains(where: { $0.isWhitespace }) else {
            return "Enter a complete OpenRouter API key. It should begin with sk-or-."
        }
        let data = Data(value.utf8)
        var result = SecItemUpdate(query as CFDictionary, [kSecValueData as String: data] as CFDictionary)
        if result == errSecItemNotFound {
            // Trust only this app and Apple's existing security helper used by
            // BCU's router/CLI. Never grant access to every application.
            var helper: SecTrustedApplication?
            var app: SecTrustedApplication?
            guard SecTrustedApplicationCreateFromPath("/usr/bin/security", &helper) == errSecSuccess,
                  SecTrustedApplicationCreateFromPath(nil, &app) == errSecSuccess,
                  let helper, let app else { return "Could not create the Keychain access policy." }
            var access: SecAccess?
            guard SecAccessCreate("BCU OpenRouter API key" as CFString, [app, helper] as CFArray, &access) == errSecSuccess,
                  let access else { return "Could not create the Keychain access policy." }
            var item = query
            item[kSecValueData as String] = data
            item[kSecAttrLabel as String] = "Codex OpenRouter API key"
            item[kSecAttrAccess as String] = access
            result = SecItemAdd(item as CFDictionary, nil)
        }
        return result == errSecSuccess ? nil : "Keychain could not save the key (status \(result)). Unlock your login Keychain and try again."
    }
}

struct ModelCatalog: Decodable { let data: [RouterModel] }
struct RouterModel: Decodable, Identifiable {
    let id: String
    let name: String
    let context_length: Int?
    let supported_parameters: [String]?
    let pricing: Price?
    struct Price: Decodable { let prompt: String?; let completion: String? }
    var displayName: String {
        let clean = name.split(separator: ":", maxSplits: 1, omittingEmptySubsequences: false)
        let withoutProvider = clean.count == 2 && clean[1].first == " " ? String(clean[1]).trimmingCharacters(in: .whitespaces) : name
        return withoutProvider.prefix(1).uppercased() + withoutProvider.dropFirst() + " (Openrouter)"
    }
}

final class BCUStore: ObservableObject {
    @Published var enabled = false
    @Published var online = false
    @Published var busy = false
    @Published var notice = ""
    @Published var modelNotice = ""
    @Published var selected = Set<String>()
    @Published var defaultID = ""
    @Published var models: [RouterModel] = []
    @Published var usageReport: UsageReport?
    @Published var usageDays = 30
    @Published var usageBusy = false
    @Published var usageNotice = ""
    @Published var page: DesktopPage = .overview
    @Published var snapshot: DesktopSnapshot?
    @Published var pythonPath: String?
    @Published var checkingRuntime = false
    @Published var hasCredential = false
    @Published var credentialBusy = false
    @Published var commandOutput = ""
    @Published var setupStep = 0
    @Published var loginEnabled = false
    @Published var snapshotNotice = ""
    private var snapshotBusy = false
    private let loginLabel = "com.bobocodexultra.menubar"
    private var selectedMetadata: [RouterModel] = []
    private let home: URL
    let cli: URL

    init() {
        let root = ProcessInfo.processInfo.environment["CODEX_HOME"] ?? NSHomeDirectory() + "/.codex"
        home = URL(fileURLWithPath: root, isDirectory: true)
        let bundled = Bundle.main.resourceURL?.appendingPathComponent("openrouter-codex")
        cli = bundled.flatMap { FileManager.default.fileExists(atPath: $0.path) ? $0 : nil }
            ?? URL(fileURLWithPath: NSHomeDirectory() + "/.local/bin/bobocodexultra")
        reload()
        discoverPython()
    }

    func reload() {
        hasCredential = BCUCredentials.present()
        loginEnabled = FileManager.default.fileExists(atPath: loginAgent.path)
        enabled = FileManager.default.fileExists(atPath: home.appendingPathComponent("bcu/state.json").path)
        if let data = try? Data(contentsOf: home.appendingPathComponent("openrouter-codex-selection.json")),
           let state = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            let entries = state["models"] as? [[String: Any]] ?? []
            selected = Set(entries.compactMap { $0["id"] as? String })
            selectedMetadata = entries.compactMap { entry -> RouterModel? in
                guard let id = entry["id"] as? String else { return nil }
                return RouterModel(id: id, name: entry["name"] as? String ?? id,
                                   context_length: entry["context_length"] as? Int,
                                   supported_parameters: ["tools"], pricing: nil)
            }
            defaultID = state["default"] as? String ?? ""
        }
        var request = URLRequest(url: URL(string: "http://127.0.0.1:11435/_bcu/health")!)
        request.timeoutInterval = 2
        let expectedHome = home.resolvingSymlinksInPath().path
        URLSession.shared.dataTask(with: request) { [weak self] data, _, _ in
            let health = data.flatMap { try? JSONDecoder().decode(RouterHealth.self, from: $0) }
            DispatchQueue.main.async { self?.online = health?.home == expectedHome && health?.service == "bcu" }
        }.resume()
    }

    func browse() {
        let url = URL(string: "https://openrouter.ai/api/v1/models?sort=most-popular&supported_parameters=tools")!
        URLSession.shared.dataTask(with: url) { [weak self] data, _, error in
            let catalog = data.flatMap { try? JSONDecoder().decode(ModelCatalog.self, from: $0) }
            DispatchQueue.main.async {
                if let catalog {
                    let live = catalog.data.filter { ($0.supported_parameters ?? []).contains("tools") }
                    let known = Set(live.map(\.id))
                    self?.models = live + (self?.selectedMetadata.filter { !known.contains($0.id) } ?? [])
                    self?.modelNotice = "\(self?.models.count ?? 0) tool-capable models · choose any number"
                } else {
                    self?.modelNotice = "Could not load OpenRouter's catalog. Showing saved selections; check your connection."
                    if self?.models.isEmpty == true { self?.models = self?.selectedMetadata ?? [] }
                    _ = error
                }
            }
        }.resume()
    }

    func run(_ arguments: [String], completion: ((Bool) -> Void)? = nil) {
        guard !busy else { return }
        guard pythonPath != nil else { notice = "Install Python 3.14+ in Setup first."; completion?(false); return }
        busy = true
        notice = "Working…"
        let process = cliProcess(arguments)
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let output = Pipe()
            process.standardOutput = output
            process.standardError = output
            do {
                try process.run()
                let detail = String(data: output.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
                process.waitUntilExit()
                DispatchQueue.main.async {
                    self?.busy = false
                    self?.commandOutput = String(detail.suffix(12000))
                    self?.notice = process.terminationStatus == 0 ? "Done. " + String(detail.suffix(450)) : String(detail.suffix(700))
                    self?.reload()
                    self?.loadSnapshot()
                    completion?(process.terminationStatus == 0)
                }
            } catch {
                DispatchQueue.main.async { self?.busy = false; self?.notice = "BCU could not start its bundled CLI. Check Setup."; completion?(false) }
            }
        }
    }

    private func cliProcess(_ arguments: [String]) -> Process {
        let process = Process()
        // Finder/login launches do not inherit an interactive shell's Python.
        if let python = pythonPath,
           FileManager.default.isExecutableFile(atPath: python) {
            process.executableURL = URL(fileURLWithPath: python)
            process.arguments = [cli.path, "--no-color", "--no-animate"] + arguments
        } else {
            process.executableURL = cli
            process.arguments = ["--no-color", "--no-animate"] + arguments
        }
        var environment = ProcessInfo.processInfo.environment
        environment["CODEX_HOME"] = home.path
        environment["PATH"] = (pythonPath.map { URL(fileURLWithPath: $0).deletingLastPathComponent().path + ":" } ?? "") + NSHomeDirectory() + "/.local/bin:/opt/homebrew/bin:/usr/local/bin:" + (environment["PATH"] ?? "/usr/bin:/bin")
        process.environment = environment
        return process
    }

    func discoverPython() {
        guard !checkingRuntime else { return }
        checkingRuntime = true
        let hint = Bundle.main.infoDictionary?["BCUPythonExecutable"] as? String
        let candidates = [hint, NSHomeDirectory() + "/.local/bin/python3",
            "/opt/homebrew/bin/python3.14", "/opt/homebrew/bin/python3", "/usr/local/bin/python3.14",
            "/usr/local/bin/python3", "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"]
            .compactMap { $0 }
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            var found: String?
            for candidate in candidates where FileManager.default.isExecutableFile(atPath: candidate) {
                let check = Process()
                check.executableURL = URL(fileURLWithPath: candidate)
                check.arguments = ["-I", "-c", "import sys; sys.exit(0 if sys.version_info >= (3,14) else 1)"]
                check.standardOutput = FileHandle.nullDevice
                check.standardError = FileHandle.nullDevice
                do {
                    try check.run()
                    DispatchQueue.global().asyncAfter(deadline: .now() + 4) { if check.isRunning { check.terminate() } }
                    check.waitUntilExit()
                    if check.terminationStatus == 0 { found = candidate; break }
                } catch { continue }
            }
            let discovered = found
            DispatchQueue.main.async {
                self?.pythonPath = discovered
                self?.checkingRuntime = false
                self?.loadSnapshot()
            }
        }
    }

    func loadSnapshot() {
        guard pythonPath != nil, !snapshotBusy else { return }
        snapshotBusy = true
        let process = cliProcess(["app", "status"])
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = FileHandle.nullDevice
        DispatchQueue.global(qos: .utility).async { [weak self] in
            var result: DesktopSnapshot?
            do {
                try process.run()
                DispatchQueue.global().asyncAfter(deadline: .now() + 15) { if process.isRunning { process.terminate() } }
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                process.waitUntilExit()
                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase
                if process.terminationStatus == 0 { result = try? decoder.decode(DesktopSnapshot.self, from: data) }
            } catch { }
            let loaded = result
            DispatchQueue.main.async {
                self?.snapshotBusy = false
                if let loaded { self?.snapshot = loaded; self?.snapshotNotice = "" }
                else { self?.snapshotNotice = "Settings could not be read. Run Check prerequisites in Setup for details." }
            }
        }
    }

    func saveCredential(_ key: String, completion: @escaping (String?) -> Void) {
        guard !credentialBusy else { return }
        credentialBusy = true
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let error = BCUCredentials.save(key)
            DispatchQueue.main.async {
                self?.credentialBusy = false
                self?.reload()
                completion(error)
            }
        }
    }

    private var loginAgent: URL { URL(fileURLWithPath: NSHomeDirectory() + "/Library/LaunchAgents/" + loginLabel + ".plist") }
    func setLogin(_ enabled: Bool) {
        do {
            let manager = FileManager.default
            if manager.fileExists(atPath: loginAgent.path) {
                let data = try Data(contentsOf: loginAgent)
                guard let existing = try PropertyListSerialization.propertyList(from: data, format: nil) as? [String: Any],
                      existing["Label"] as? String == loginLabel else {
                    notice = "Login item is not owned by BCU; it was left unchanged."; return
                }
                if !enabled { try manager.removeItem(at: loginAgent) }
            }
            if enabled {
                guard let executable = Bundle.main.executableURL?.path else { return }
                guard !executable.hasPrefix("/Volumes/") && !executable.contains("/AppTranslocation/") else {
                    notice = "Move BCU to Applications and reopen it before enabling launch at login."; return
                }
                let data = try PropertyListSerialization.data(fromPropertyList: [
                    "Label": loginLabel, "ProgramArguments": [executable, "--background"],
                    "RunAtLoad": true, "KeepAlive": false, "EnvironmentVariables": ["CODEX_HOME": home.path]
                ], format: .xml, options: 0)
                try manager.createDirectory(at: loginAgent.deletingLastPathComponent(), withIntermediateDirectories: true)
                try data.write(to: loginAgent, options: .atomic)
                try manager.setAttributes([.posixPermissions: 0o600], ofItemAtPath: loginAgent.path)
            }
            reload()
        } catch { notice = "Could not change launch at login: \(error.localizedDescription)" }
    }

    func openCodex() {
        if let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.openai.codex") {
            NSWorkspace.shared.open(url)
        } else { notice = "Codex Desktop was not found. Install it before enabling BCU." }
    }

    func loadUsage(refreshPrices: Bool = false) {
        guard !usageBusy else { return }
        guard pythonPath != nil else { usageNotice = "Install Python 3.14+ in Setup first."; return }
        usageBusy = true
        usageNotice = ""
        let process = cliProcess(["usage", "--json", "--days", String(usageDays),
                                  refreshPrices ? "--refresh-prices" : "--offline"])
        let output = Pipe()
        process.standardOutput = output
        process.standardError = FileHandle.nullDevice
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            do {
                try process.run()
                DispatchQueue.global().asyncAfter(deadline: .now() + 45) {
                    if process.isRunning { process.terminate() }
                }
                // Drain while the CLI runs so a large model report cannot fill
                // the pipe and deadlock waitUntilExit().
                let data = output.fileHandleForReading.readDataToEndOfFile()
                process.waitUntilExit()
                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase
                let report = process.terminationStatus == 0 ? try? decoder.decode(UsageReport.self, from: data) : nil
                DispatchQueue.main.async {
                    self?.usageBusy = false
                    if let report { self?.usageReport = report }
                    else { self?.usageNotice = "Could not load usage. Try bobocodexultra usage --offline in Terminal, or reinstall the CLI." }
                }
            } catch {
                DispatchQueue.main.async {
                    self?.usageBusy = false
                    self?.usageNotice = "BCU CLI could not start. Run bobocodexultra install, then reopen this window."
                }
            }
        }
    }
}

struct UsageView: View {
    @ObservedObject var store: BCUStore
    @State private var search = ""
    @State private var sorting = "Tokens"
    private func money(_ amount: Double) -> String { String(format: "$%.6f", amount) }

    private var rows: [UsageRow] {
        let all = (store.usageReport?.models ?? [:]).map { UsageRow(id: $0.key, totals: $0.value) }
        let filtered = all.filter { search.isEmpty || ($0.name + " " + $0.id).localizedCaseInsensitiveContains(search) }
        return filtered.sorted {
            switch sorting {
            case "Name": return $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending
            case "Cost": return ($0.totals.knownCostUsd, $0.id) > ($1.totals.knownCostUsd, $1.id)
            default: return ($0.totals.totalTokens, $0.id) > ($1.totals.totalTokens, $1.id)
            }
        }
    }

    private func metric(_ label: String, _ value: String, _ note: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(label).font(.caption).foregroundStyle(.secondary)
            Text(value).font(.title3.bold()).monospacedDigit().lineLimit(1).minimumScaleFactor(0.7)
            Text(note).font(.caption2).foregroundStyle(.secondary)
        }.frame(maxWidth: .infinity, alignment: .leading).padding(12)
            .background(Color.primary.opacity(0.045)).clipShape(RoundedRectangle(cornerRadius: 10))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Image(nsImage: BCUIcon.draw(30, template: false)).resizable().frame(width: 30, height: 30)
                VStack(alignment: .leading, spacing: 3) {
                    Text("Usage & Costs").font(.title2.bold())
                    Text("OpenRouter activity through BCU").font(.subheadline).foregroundStyle(.secondary)
                }
                Spacer()
                if store.usageBusy { ProgressView().controlSize(.small) }
                Button("Refresh") { store.loadUsage() }.disabled(store.usageBusy)
                Button("Refresh Prices") { store.loadUsage(refreshPrices: true) }.disabled(store.usageBusy)
                    .help("Fetch OpenRouter's public pricing catalog for records without reported costs. No API key or model call.")
            }
            HStack {
                Picker("Period", selection: $store.usageDays) {
                    Text("24 hours").tag(1)
                    Text("7 days").tag(7)
                    Text("30 days").tag(30)
                    Text("All time").tag(0)
                }.pickerStyle(.segmented).frame(width: 340).disabled(store.usageBusy)
                Spacer()
                Text("Native ChatGPT / Ollama excluded").font(.caption).foregroundStyle(.secondary)
            }
            if !store.usageNotice.isEmpty {
                Text(store.usageNotice).font(.callout).foregroundStyle(.orange)
            }
            if let report = store.usageReport, report.periodDays == store.usageDays {
                let summary = report.summary
                HStack(spacing: 10) {
                    metric("Recorded tokens", summary.totalTokens.formatted(), "Input + output; includes cached tokens")
                    metric("Reported cost", money(summary.reportedCostUsd), "From provider responses")
                    metric("Estimated cost", money(summary.estimatedCostUsd), "Catalog fallback only")
                    metric("Known cost", money(summary.knownCostUsd), summary.costSource == "partial" ? "Partial subtotal" : "Reported + estimated")
                }
                HStack(spacing: 18) {
                    Text("Input \(summary.inputTokens.formatted())")
                    Text("Cached \(summary.cachedInputTokens.formatted())")
                    Text("Output \(summary.outputTokens.formatted())")
                    Text("Reasoning \(summary.reasoningOutputTokens.formatted()) included")
                }.font(.caption).monospacedDigit().foregroundStyle(.secondary)
                Text("\(summary.desktopRequests.formatted()) desktop requests · \(summary.legacyRecords.formatted()) legacy CLI records")
                    .font(.caption).foregroundStyle(.secondary)
                ForEach(report.warnings, id: \.self) { warning in
                    Label(warning, systemImage: "exclamationmark.triangle").font(.caption).foregroundStyle(.orange)
                }
                HStack {
                    TextField("Search models", text: $search).textFieldStyle(.roundedBorder)
                    Picker("Sort", selection: $sorting) {
                        ForEach(["Tokens", "Cost", "Name"], id: \.self) { Text($0) }
                    }.frame(width: 170)
                }
                if report.models.isEmpty {
                    VStack(spacing: 8) {
                        Image(systemName: "chart.bar.xaxis").font(.largeTitle).foregroundStyle(.secondary)
                        Text("No recorded usage for this period").font(.headline)
                        Text("Completed OpenRouter responses appear here when they include usage counters.")
                            .font(.caption).foregroundStyle(.secondary)
                    }.frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    Table(rows) {
                        TableColumn("Model") { row in
                            VStack(alignment: .leading, spacing: 3) {
                                Text(row.name).fontWeight(.medium)
                                Text(row.id).font(.caption).foregroundStyle(.secondary)
                            }.padding(.vertical, 3)
                        }.width(min: 220, ideal: 290)
                        TableColumn("Input") { row in Text(row.totals.inputTokens.formatted()).monospacedDigit() }.width(min: 90, ideal: 105)
                        TableColumn("Output") { row in Text(row.totals.outputTokens.formatted()).monospacedDigit() }.width(min: 75, ideal: 85)
                        TableColumn("Total") { row in Text(row.totals.totalTokens.formatted()).monospacedDigit() }.width(min: 90, ideal: 105)
                        TableColumn("Known cost") { row in Text(money(row.totals.knownCostUsd)).monospacedDigit() }.width(min: 95, ideal: 105)
                        TableColumn("Source") { row in Text(row.totals.costSource.capitalized).foregroundStyle(.secondary) }.width(min: 65, ideal: 80)
                    }
                }
                Text("Pricing catalog: \(report.pricingCatalogFetchedAt). Estimates use catalog prices, not historical invoices.")
                    .font(.caption2).foregroundStyle(.secondary).textSelection(.enabled)
            } else {
                Text(store.usageBusy ? "Reading local usage…" : "Refresh to load usage.")
                    .foregroundStyle(.secondary).frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }.padding(18).frame(minWidth: 860, minHeight: 590)
            .onAppear { store.loadUsage() }
            .onChange(of: store.usageDays) { _ in store.loadUsage() }
    }
}

struct ManagerView: View {
    @ObservedObject var store: BCUStore
    @State private var search = ""
    @State private var sort = "Popular"
    private let modes = ["Popular", "Name", "Context", "Selected"]

    private var visible: [RouterModel] {
        let words = search.lowercased().split(separator: " ")
        let matches = store.models.filter { model in
            words.allSatisfy { word in (model.name + " " + model.id).lowercased().contains(word) }
        }
        switch sort {
        case "Name": return matches.sorted { $0.displayName.localizedCaseInsensitiveCompare($1.displayName) == .orderedAscending }
        case "Context": return matches.sorted { ($0.context_length ?? 0) > ($1.context_length ?? 0) }
        case "Selected": return matches.sorted { (store.selected.contains($0.id) ? 0 : 1, $0.displayName) < (store.selected.contains($1.id) ? 0 : 1, $1.displayName) }
        default: return matches
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(nsImage: BCUIcon.draw(30, template: false)).resizable().frame(width: 30, height: 30)
                VStack(alignment: .leading) {
                    Text("BCU Models").font(.title2.bold())
                    Text("\(store.selected.count) selected · native ChatGPT and Ollama stay available").foregroundStyle(.secondary)
                }
                Spacer()
                Button("Refresh") { store.browse(); store.reload() }
            }
            HStack {
                TextField("Search model or provider", text: $search)
                    .textFieldStyle(.roundedBorder)
                Picker("Sort", selection: $sort) { ForEach(modes, id: \.self) { Text($0) } }
                    .frame(width: 170)
            }
            List(visible) { model in
                HStack(spacing: 12) {
                    Button {
                        store.run(["model", store.selected.contains(model.id) ? "remove" : "add", model.id])
                    } label: {
                        Image(systemName: store.selected.contains(model.id) ? "checkmark.circle.fill" : "circle")
                            .foregroundStyle(store.selected.contains(model.id) ? .mint : .secondary)
                    }.buttonStyle(.plain).disabled(store.busy || store.defaultID == model.id)
                    VStack(alignment: .leading, spacing: 3) {
                        Text(model.displayName).fontWeight(.medium)
                        Text(model.id).font(.caption.monospaced()).foregroundStyle(.secondary)
                    }
                    Spacer()
                    if store.selected.contains(model.id) {
                        Picker("Reasoning", selection: Binding(
                            get: { store.snapshot?.models.first(where: { $0.id == model.id })?.reasoningEffort ?? "high" },
                            set: { store.run(["reasoning", $0, "--model", model.id]) }
                        )) {
                            Text("Low").tag("low"); Text("Medium").tag("medium"); Text("High").tag("high")
                        }.labelsHidden().frame(width: 95).disabled(store.busy)
                            .help("Default thinking effort. Reopen Codex to refresh its selector.")
                    }
                    if store.defaultID == model.id { Text("Default").font(.caption).foregroundStyle(.mint) }
                    else if store.selected.contains(model.id) {
                        Button("Make default") { store.run(["model", "default", model.id]) }.disabled(store.busy)
                    }
                    if let context = model.context_length { Text("\(context / 1000)k").font(.caption).foregroundStyle(.secondary) }
                }.padding(.vertical, 3)
            }
            HStack {
                Text(store.modelNotice).font(.caption).foregroundStyle(.secondary).lineLimit(2)
                Spacer()
                Text("Changes refresh BCU immediately; reopen Codex for the picker.").font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(18)
        .frame(minWidth: 680, minHeight: 530)
        .onAppear { store.browse(); store.reload() }
    }
}

struct BCUCard<Content: View>: View {
    @ViewBuilder var content: Content
    var body: some View {
        VStack(alignment: .leading, spacing: 14) { content }
            .frame(maxWidth: .infinity, alignment: .leading).padding(20)
            .background(Color(nsColor: .controlBackgroundColor))
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.primary.opacity(0.07), lineWidth: 1))
    }
}

struct PaneHeader: View {
    let title: String
    let subtitle: String
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.system(size: 28, weight: .semibold))
            Text(subtitle).foregroundStyle(.secondary)
        }.padding(.bottom, 12)
    }
}

struct DesktopRoot: View {
    @ObservedObject var store: BCUStore
    @AppStorage("bcuAppearance") private var appearance = "system"
    var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 5) {
                HStack(spacing: 10) {
                    Image(nsImage: BCUIcon.draw(29, template: false))
                    Text("BCU").font(.title2.weight(.semibold))
                }.padding(.horizontal, 12).padding(.vertical, 22)
                ForEach(DesktopPage.allCases) { page in
                    Button { store.page = page } label: {
                        HStack(spacing: 11) {
                            Image(systemName: page.icon).frame(width: 19)
                            Text(page.rawValue)
                            Spacer()
                        }.padding(.horizontal, 12).padding(.vertical, 10)
                            .background(store.page == page ? Color.primary.opacity(0.08) : .clear)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    }.buttonStyle(.plain)
                }
                Spacer()
                Label(store.enabled && store.online ? "Connected" : store.enabled ? "Router offline" : "Native mode",
                      systemImage: store.enabled && store.online ? "circle.fill" : "circle")
                    .font(.caption).foregroundStyle(.secondary).padding(12)
                Text("Bobo Codex Ultra").font(.caption2).foregroundStyle(.tertiary).padding(.horizontal, 12).padding(.bottom, 10)
            }.padding(.horizontal, 10).frame(width: 170)
                .background(Color(nsColor: .windowBackgroundColor))
            Divider()
            VStack(spacing: 0) {
                if store.page == .models { ManagerView(store: store) }
                else if store.page == .usage { UsageView(store: store) }
                else {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 18) {
                            switch store.page {
                            case .overview: OverviewView(store: store)
                            case .setup: SetupView(store: store)
                            case .account: AccountView(store: store)
                            case .agents: AgentsView(store: store)
                            case .traffic: RoutingView(store: store)
                            case .settings: SettingsView(store: store)
                            default: EmptyView()
                            }
                        }.padding(32).frame(maxWidth: 850, alignment: .leading).frame(maxWidth: .infinity)
                    }
                }
                if !store.snapshotNotice.isEmpty {
                    Text(store.snapshotNotice).font(.caption).foregroundStyle(.orange).padding(10)
                }
                if store.busy || !store.notice.isEmpty {
                    Divider()
                    HStack(alignment: .top) {
                        if store.busy { ProgressView().controlSize(.small) }
                        Text(store.busy ? "Working…" : store.notice).font(.caption).foregroundStyle(.secondary)
                            .lineLimit(4).textSelection(.enabled)
                        Spacer()
                        if !store.busy { Button { store.notice = "" } label: { Image(systemName: "xmark") }.buttonStyle(.plain) }
                    }.padding(12)
                }
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
        }.frame(minWidth: 1050, minHeight: 670)
            .preferredColorScheme(appearance == "system" ? nil : appearance == "dark" ? .dark : .light)
    }
}

struct OverviewView: View {
    @ObservedObject var store: BCUStore
    @State private var confirmRouting = false
    var body: some View {
        PaneHeader(title: "Your models. One place.", subtitle: "OpenRouter, native ChatGPT, and Ollama—side by side in Codex.")
        BCUCard {
            HStack {
                VStack(alignment: .leading, spacing: 8) {
                    Label(store.enabled ? "Shared routing is on" : "Native routing", systemImage: "point.3.connected.trianglepath.dotted")
                        .font(.headline)
                    Text(store.enabled ? "\(store.selected.count) OpenRouter models · \(store.online ? "local router ready" : "router unavailable")" : "BCU is not overriding your native endpoint.")
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Button(store.enabled ? "Turn off…" : "Enable…") { confirmRouting = true }.disabled(store.busy || store.pythonPath == nil)
            }
            Divider()
            HStack {
                Button("Open Codex") { store.openCodex() }
                Button("Manage models") { store.page = .models }
                Button("View usage") { store.page = .usage }
            }
        }
        BCUCard {
            Text("Get comfortable").font(.headline)
            Text("Use Setup to install the CLI and connect your account. Then choose your models and reasoning defaults, set up subagents, and tune request limits—all here.")
                .foregroundStyle(.secondary)
            Button("Open setup assistant") { store.page = .setup }
        }
        BCUCard {
            Text("Designed to stay out of the way").font(.headline)
            Text("Closing this window keeps the menu icon available. Quitting BCU closes the desktop app and icon, but leaves the independent router running. Turning routing off restores your previous native configuration.")
                .foregroundStyle(.secondary)
        }
        Text("Model and reasoning changes may require reopening Codex. BCU does not change native ChatGPT billing or allowances.")
            .font(.caption).foregroundStyle(.secondary)
            .alert(store.enabled ? "Restore native routing?" : "Enable shared routing?", isPresented: $confirmRouting) {
                Button("Cancel", role: .cancel) { }
                Button("Continue") { store.run([store.enabled ? "off" : "on"]) }
            } message: { Text("Wait for active requests to finish first. BCU preserves unrelated Codex settings and keeps recovery backups.") }
    }
}

struct SetupView: View {
    @ObservedObject var store: BCUStore
    @State private var checked = false
    @State private var confirmEnable = false
    private let steps = ["Welcome", "Check", "Install", "Connect", "Models", "Enable", "Finish"]
    var body: some View {
        PaneHeader(title: "Make yourself at home.", subtitle: "A few small steps. Your native models and existing BCU history stay intact.")
        HStack(spacing: 7) {
            ForEach(steps.indices, id: \.self) { index in
                VStack(spacing: 6) {
                    Capsule().fill(index <= store.setupStep ? Color.primary : Color.primary.opacity(0.1)).frame(height: 3)
                    Text(steps[index]).font(.caption2).foregroundStyle(index == store.setupStep ? .primary : .secondary)
                }
            }
        }.padding(.bottom, 16)
        BCUCard {
            switch store.setupStep {
            case 0:
                Text("One app, one menu icon.").font(.title2.weight(.semibold))
                Text("This assistant checks your Mac, installs the global CLI, connects OpenRouter through Keychain, and lets you opt into shared Codex routing. Nothing is enabled without your choice.")
                Text("Move Bobo Codex Ultra into Applications before continuing. Python 3.14+ and Codex are required; BCU does not silently download or execute installers.").foregroundStyle(.secondary)
                Button("Get started") { store.setupStep = 1 }.buttonStyle(.borderedProminent)
            case 1:
                Text("Check your Mac").font(.title2.weight(.semibold))
                Label(store.pythonPath == nil ? "Python 3.14+ not found" : "Python 3.14+ ready", systemImage: store.pythonPath == nil ? "exclamationmark.circle" : "checkmark.circle")
                Label(store.snapshot?.codexAvailable == true ? "Codex CLI found" : "Codex CLI not found", systemImage: store.snapshot?.codexAvailable == true ? "checkmark.circle" : "exclamationmark.circle")
                HStack {
                    Link("Get Python", destination: URL(string: "https://www.python.org/downloads/macos/")!)
                    Link("Codex setup guide", destination: URL(string: "https://developers.openai.com/codex/cli/")!)
                    Button("Detect again") { checked = false; store.discoverPython() }.disabled(store.checkingRuntime)
                }
                Button("Check prerequisites") { store.run(["setup", "--check"]) { checked = $0 } }
                    .disabled(store.pythonPath == nil || store.busy)
                if checked { Button("Continue") { store.setupStep = 2 }.buttonStyle(.borderedProminent) }
            case 2:
                Text("Install the command-line tools").font(.title2.weight(.semibold))
                Text("Install bobocodexultra and its companion files in ~/.local/bin. Prepare model metadata without changing your desktop routing or reading a saved key. No administrator password is needed.")
                Text("If ~/.local/bin is not on your shell PATH, add it in your shell settings. The desktop app works without that change.").font(.caption).foregroundStyle(.secondary)
                Button("Install & prepare") {
                    store.run(["install"]) { ok in
                        if ok { store.run(["auth", "prepare"]) { if $0 { store.setupStep = 3 } } }
                    }
                }.buttonStyle(.borderedProminent).disabled(store.busy || store.pythonPath == nil)
            case 3:
                AccountView(store: store, compact: true)
                Button("Continue") { store.setupStep = 4 }.disabled(!store.hasCredential || store.credentialBusy)
            case 4:
                Text("Choose your models").font(.title2.weight(.semibold))
                Text("\(store.selected.count) models are selected. Browse the catalog, add or remove models, and choose each model’s default reasoning level. Return to Setup when you’re ready.")
                Button("Open model manager") { store.page = .models }
                Button("Use this lineup") { store.setupStep = 5 }.disabled(store.selected.isEmpty)
            case 5:
                Text("Connect to Codex").font(.title2.weight(.semibold))
                Text("Shared mode starts the local router and adds OpenRouter models alongside native ChatGPT and Ollama. BCU saves a recovery backup. Finish active model requests before enabling or restarting it.")
                if store.enabled && store.online {
                    Label("Shared routing is already running", systemImage: "checkmark.circle")
                    Button("Continue") { store.setupStep = 6 }
                } else {
                    Button("Enable shared routing…") { confirmEnable = true }.buttonStyle(.borderedProminent)
                        .disabled(store.busy || !store.hasCredential)
                }
                Button("Leave routing unchanged for now") { store.setupStep = 6 }.buttonStyle(.plain)
            default:
                Text("You’re all set.").font(.title2.weight(.semibold))
                Text("Reopen Codex after enabling shared mode or changing its model lineup. You can configure subagents in Agents; this is optional and never happens silently.")
                Toggle("Launch BCU at login", isOn: Binding(get: { store.loginEnabled }, set: { store.setLogin($0) }))
                HStack {
                    Button("Set up agents") { store.page = .agents }
                    Button("Open Codex") { store.openCodex() }
                    Button("Finish") { UserDefaults.standard.set(true, forKey: "bcuSetupCompleted"); store.page = .overview }
                        .buttonStyle(.borderedProminent)
                }
            }
        }
        if store.setupStep > 0 { Button("Back") { store.setupStep -= 1 }.disabled(store.busy || store.credentialBusy) }
        Text("API calls can incur OpenRouter charges. Setup does not make a billed model call.").font(.caption).foregroundStyle(.secondary)
            .alert("Enable BCU routing?", isPresented: $confirmEnable) {
                Button("Cancel", role: .cancel) { }
                Button("Enable") { store.run(["on"]) { if $0 { store.setupStep = 6 } } }
            } message: { Text("This changes Codex’s endpoint and starts or restarts BCU’s local router. Continue after active requests finish.") }
    }
}

struct AccountView: View {
    @ObservedObject var store: BCUStore
    var compact = false
    @State private var key = ""
    @State private var message = ""
    var body: some View {
        if !compact { PaneHeader(title: "Account", subtitle: "One connection. Safely stored on your Mac.") }
        VStack(alignment: .leading, spacing: 16) {
            Label(store.hasCredential ? "OpenRouter key is saved" : "Connect OpenRouter", systemImage: store.hasCredential ? "checkmark.shield" : "key")
                .font(.headline)
            Text("Enter or replace your API key. BCU saves it directly in macOS Keychain, never in a config file, command argument or log. Your saved key is never displayed.").foregroundStyle(.secondary)
            SecureField("OpenRouter API key", text: $key).textFieldStyle(.roundedBorder).disabled(store.credentialBusy)
                .onSubmit { save() }
            HStack {
                Button(store.credentialBusy ? "Saving…" : "Save to Keychain") { save() }.disabled(key.isEmpty || store.credentialBusy)
                Link("Open OpenRouter", destination: URL(string: "https://openrouter.ai/settings/keys")!)
            }
            if !message.isEmpty { Text(message).font(.callout).textSelection(.enabled) }
            Text("macOS may ask permission when updating an existing Keychain item. Saving a key does not enable routing or make a model call.").font(.caption).foregroundStyle(.secondary)
        }.padding(compact ? 0 : 20)
            .onDisappear { key = "" }
    }
    private func save() {
        guard !key.isEmpty, !store.credentialBusy else { return }
        let entered = key
        key = ""
        message = ""
        store.saveCredential(entered) { error in message = error ?? "Saved securely in Keychain." }
    }
}

struct AgentsView: View {
    @ObservedObject var store: BCUStore
    @State private var model = ""
    @State private var reasoning = "high"
    @State private var limit = 2
    var body: some View {
        PaneHeader(title: "Agents", subtitle: "Set a default for Codex subagents. Codex still manages delegation.")
        BCUCard {
            Text(store.snapshot?.agentsManaged == true ? "BCU-managed defaults" : "Native or manually configured defaults").font(.headline)
            if let active = store.snapshot, !active.agentModel.isEmpty { Text("Current: \(active.agentModel) · \(active.agentReasoning) · limit \(active.agentLimit)").font(.caption).foregroundStyle(.secondary) }
            Picker("Default model", selection: $model) {
                Text("Choose a model").tag("")
                ForEach(store.snapshot?.models ?? []) { Text($0.name).tag($0.id) }
            }
            Picker("Reasoning", selection: $reasoning) {
                Text("Low").tag("low"); Text("Medium").tag("medium"); Text("High").tag("high")
            }.pickerStyle(.segmented)
            Stepper("Maximum concurrent subagents: \(limit)", value: $limit, in: 1...16)
            HStack {
                Button("Save agent defaults") { store.run(["agents", "setup", "--model", model, "--reasoning", reasoning, "--limit", String(limit)]) }
                    .disabled(store.busy || model.isEmpty)
                Button("Restore previous defaults") { store.run(["agents", "restore"]) }.disabled(store.busy || store.snapshot?.agentsManaged != true)
            }
            Text("BCU backs up previous values and preserves unrelated settings. Explicit custom-agent settings take precedence. Reopen Codex after changes.").font(.caption).foregroundStyle(.secondary)
        }.onAppear { load() }
            .onChange(of: store.snapshot?.defaultModel) { _ in if model.isEmpty { load() } }
    }
    private func load() {
        guard let state = store.snapshot else { return }
        model = state.models.contains(where: { $0.id == state.agentModel }) ? state.agentModel : state.defaultModel
        reasoning = ["low", "medium", "high"].contains(state.agentReasoning) ? state.agentReasoning : "high"
        limit = min(16, max(1, state.agentLimit))
    }
}

struct RoutingView: View {
    @ObservedObject var store: BCUStore
    @State private var values: [String: Double] = [:]
    @State private var confirmRestart = false
    private let fields: [(String, String)] = [
        ("openrouter_concurrency", "OpenRouter requests"), ("openrouter_model_concurrency", "OpenRouter requests per model"),
        ("native_concurrency", "Native requests"), ("native_model_concurrency", "Native requests per model"),
        ("queue_limit", "Waiting requests per route"), ("request_timeout", "Queue / retry budget (seconds)"),
        ("max_attempts", "Maximum attempts"), ("body_budget_mb", "Buffered request memory (MB)"),
        ("backoff_base", "Initial backoff (seconds)"), ("backoff_max", "Maximum backoff (seconds)"), ("jitter", "Retry jitter (seconds)")]
    var body: some View {
        PaneHeader(title: "Routing", subtitle: "Give busy conversations room to work. Keep provider limits in mind.")
        BCUCard {
            Text("Concurrency & recovery").font(.headline)
            ForEach(fields, id: \.0) { key, label in
                HStack {
                    Text(label)
                    Spacer()
                    TextField(label, value: Binding(get: { values[key] ?? 0 }, set: { values[key] = $0 }), format: .number)
                        .labelsHidden().textFieldStyle(.roundedBorder).frame(width: 110)
                }
            }
            HStack {
                Button("Save limits") {
                    let decimal = Set(["request_timeout", "backoff_base", "backoff_max", "jitter"])
                    let settings = fields.map { key, _ in
                        let value = values[key] ?? 0
                        return key + "=" + (decimal.contains(key) || value.rounded() != value ? String(value) : String(format: "%.0f", value))
                    }
                    store.run(["app", "traffic"] + settings)
                }.disabled(store.busy || values.isEmpty)
                Button("Reload saved") { values = store.snapshot?.traffic ?? [:] }
                Button("Apply / restart router…") { confirmRestart = true }.disabled(store.busy || !store.enabled)
            }
            Text("Saving validates and backs up limits, but does not interrupt active calls. Apply only when requests are idle. Higher concurrency can worsen upstream throttling; retries cannot create provider capacity.")
                .font(.caption).foregroundStyle(.secondary)
        }
        BCUCard {
            Text("Diagnostics").font(.headline)
            HStack {
                Button("Inspect traffic") { store.run(["traffic"]) }.disabled(store.busy)
                Button("Run doctor") { store.run(["doctor"]) }.disabled(store.busy)
            }
            if !store.commandOutput.isEmpty {
                Text(store.commandOutput).font(.caption.monospaced()).textSelection(.enabled)
            }
        }.onAppear { values = store.snapshot?.traffic ?? [:] }
            .onChange(of: store.snapshot?.python) { _ in if values.isEmpty { values = store.snapshot?.traffic ?? [:] } }
            .alert("Restart the router?", isPresented: $confirmRestart) {
                Button("Cancel", role: .cancel) { }
                Button("Apply saved limits") { store.run(["on"]) }
            } message: { Text("This can interrupt active model calls. Continue only when conversations are idle. Unsaved edits above are not applied.") }
    }
}

struct SettingsView: View {
    @ObservedObject var store: BCUStore
    @AppStorage("bcuAppearance") private var appearance = "system"
    var body: some View {
        PaneHeader(title: "Settings", subtitle: "A quiet companion for your desktop.")
        BCUCard {
            Picker("Appearance", selection: $appearance) {
                Text("System").tag("system"); Text("Light").tag("light"); Text("Dark").tag("dark")
            }.pickerStyle(.segmented)
            Toggle("Launch BCU at login", isOn: Binding(get: { store.loginEnabled }, set: { store.setLogin($0) }))
            Text("Login launches keep the window closed. The menu icon and desktop settings share one app; closing the window does not stop the router.").font(.caption).foregroundStyle(.secondary)
        }
        BCUCard {
            Text("Installation").font(.headline)
            Text(store.pythonPath == nil ? "Python 3.14+ not found" : "Python runtime ready").foregroundStyle(.secondary)
            Button("Open setup assistant") { store.page = .setup }
            Button("Repair CLI from this app") { store.run(["install"]) }.disabled(store.busy || store.pythonPath == nil)
            Text("The app contains BCU’s public source, not a copy of your private configuration. Existing credentials remain in macOS Keychain.").font(.caption).foregroundStyle(.secondary)
        }
        BCUCard {
            Text("Bobo Codex Ultra · 0.3.0").font(.headline)
            HStack {
                Link("Documentation", destination: URL(string: "https://github.com/alexdr0/bobocodexultra#readme")!)
                Link("Releases", destination: URL(string: "https://github.com/alexdr0/bobocodexultra/releases")!)
            }
            Text("Independent software; not affiliated with OpenAI, OpenRouter, or Ollama. This build is locally signed, not notarized by Apple.").font(.caption).foregroundStyle(.secondary)
        }
    }
}

final class StatusApp: NSObject, NSApplicationDelegate, NSMenuDelegate, NSWindowDelegate {
    private let store = BCUStore()
    private var item: NSStatusItem!
    private var window: NSWindow?
    private var timer: Timer?

    func applicationDidFinishLaunching(_ notification: Notification) {
        if let identifier = Bundle.main.bundleIdentifier,
           let existing = NSRunningApplication.runningApplications(withBundleIdentifier: identifier)
            .first(where: { $0.processIdentifier != ProcessInfo.processInfo.processIdentifier }) {
            existing.activate(options: [.activateAllWindows, .activateIgnoringOtherApps])
            NSApp.terminate(nil)
            return
        }
        NSApp.setActivationPolicy(.accessory)
        installAppMenu()
        item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        item.button?.image = BCUIcon.draw(18, template: true)
        item.button?.toolTip = "Bobo Codex Ultra"
        let menu = NSMenu()
        menu.delegate = self
        item.menu = menu
        timer = Timer.scheduledTimer(withTimeInterval: 15, repeats: true) { [weak self] _ in
            self?.store.reload()
            if self?.window?.isVisible == true {
                self?.store.loadSnapshot()
                if self?.store.page == .usage { self?.store.loadUsage() }
            }
        }
        if !CommandLine.arguments.contains("--background") {
            store.page = UserDefaults.standard.bool(forKey: "bcuSetupCompleted") ? .overview : .setup
            showWindow()
        }
    }

    private func installAppMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem()
        let appMenu = NSMenu(title: "BCU")
        let settings = NSMenuItem(title: "Settings…", action: #selector(showSettings), keyEquivalent: ",")
        settings.target = self
        appMenu.addItem(settings)
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit BCU", action: #selector(quitMenu), keyEquivalent: "q").target = self
        appItem.submenu = appMenu
        main.addItem(appItem)
        let editItem = NSMenuItem()
        let edit = NSMenu(title: "Edit")
        for (title, action, key) in [("Cut", "cut:", "x"), ("Copy", "copy:", "c"), ("Paste", "paste:", "v"), ("Select All", "selectAll:", "a")] {
            edit.addItem(withTitle: title, action: Selector(action), keyEquivalent: key)
        }
        editItem.submenu = edit
        main.addItem(editItem)
        let windowItem = NSMenuItem()
        let windowMenu = NSMenu(title: "Window")
        windowMenu.addItem(withTitle: "Close Window", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
        windowMenu.addItem(withTitle: "Minimize", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        windowItem.submenu = windowMenu
        main.addItem(windowItem)
        NSApp.mainMenu = main
    }

    func menuNeedsUpdate(_ menu: NSMenu) {
        store.reload()
        menu.removeAllItems()
        let heading = NSMenuItem(title: "✦  Bobo Codex Ultra", action: nil, keyEquivalent: "")
        heading.isEnabled = false
        menu.addItem(heading)
        let status = NSMenuItem(title: store.enabled ? "● Shared mode · \(store.online ? "router running" : "router unavailable")" : "○ Native mode · BCU off", action: nil, keyEquivalent: "")
        status.isEnabled = false
        menu.addItem(status)
        menu.addItem(.separator())
        let desktop = NSMenuItem(title: "Open BCU…", action: #selector(showDesktop), keyEquivalent: "")
        desktop.target = self
        menu.addItem(desktop)
        let toggle = NSMenuItem(title: store.enabled ? "Turn Off Shared Mode" : "Turn On Shared Mode", action: #selector(toggleMode), keyEquivalent: "")
        toggle.target = self; toggle.isEnabled = !store.busy
        menu.addItem(toggle)
        let manage = NSMenuItem(title: "Manage Models…", action: #selector(showModels), keyEquivalent: "m")
        manage.target = self
        menu.addItem(manage)
        let usage = NSMenuItem(title: "Usage & Costs…", action: #selector(showUsage), keyEquivalent: "u")
        usage.target = self
        menu.addItem(usage)
        let account = NSMenuItem(title: "Account…", action: #selector(openLogin), keyEquivalent: "")
        account.target = self
        menu.addItem(account)
        menu.addItem(.separator())
        let openCodex = NSMenuItem(title: "Open Codex Desktop", action: #selector(openCodex), keyEquivalent: "")
        openCodex.target = self; menu.addItem(openCodex)
        let login = NSMenuItem(title: "Launch at Login", action: #selector(toggleLogin), keyEquivalent: "")
        login.target = self; login.state = store.loginEnabled ? .on : .off
        menu.addItem(login)
        let docs = NSMenuItem(title: "Documentation", action: #selector(openDocs), keyEquivalent: "")
        docs.target = self; menu.addItem(docs)
        menu.addItem(.separator())
        let quit = NSMenuItem(title: "Quit BCU", action: #selector(quitMenu), keyEquivalent: "q")
        quit.target = self; menu.addItem(quit)
        item.button?.alphaValue = store.enabled ? 1 : 0.55
    }

    @objc private func toggleMode() { store.page = .overview; showWindow() }
    @objc private func showDesktop() { store.page = .overview; showWindow() }
    @objc private func showSettings() { store.page = .settings; showWindow() }
    @objc private func showModels() { store.page = .models; showWindow() }
    private func showWindow() {
        if window == nil {
            let controller = NSHostingController(rootView: DesktopRoot(store: store))
            let created = NSWindow(contentViewController: controller)
            created.title = "Bobo Codex Ultra"
            created.setContentSize(NSSize(width: 1080, height: 730))
            created.titlebarAppearsTransparent = true
            created.delegate = self
            created.center()
            created.isReleasedWhenClosed = false
            window = created
        }
        NSApp.setActivationPolicy(.regular)
        window?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        store.loadSnapshot()
    }
    @objc private func openLogin() {
        store.page = .account
        showWindow()
    }
    @objc private func showUsage() {
        store.page = .usage
        showWindow()
        store.loadUsage()
    }
    @objc private func openCodex() { store.openCodex() }
    @objc private func toggleLogin() { store.setLogin(!store.loginEnabled) }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool { showWindow(); return true }
    func windowWillClose(_ notification: Notification) { NSApp.setActivationPolicy(.accessory) }
    @objc private func openDocs() {
        NSWorkspace.shared.open(URL(string: "https://github.com/alexdr0/bobocodexultra#readme")!)
    }
    @objc private func quitMenu() { NSApp.terminate(nil) }
}

if CommandLine.arguments.count == 3 && CommandLine.arguments[1] == "--export-icon" {
    let image = BCUIcon.draw(1024, template: false)
    if let tiff = image.tiffRepresentation,
       let bitmap = NSBitmapImageRep(data: tiff),
       let png = bitmap.representation(using: .png, properties: [:]) {
        try? png.write(to: URL(fileURLWithPath: CommandLine.arguments[2]))
    }
} else {
    let app = NSApplication.shared
    let delegate = StatusApp()
    app.delegate = delegate
    app.run()
}
