import AppKit
import SwiftUI

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
    @Published var selected = Set<String>()
    @Published var defaultID = ""
    @Published var models: [RouterModel] = []
    @Published var usageReport: UsageReport?
    @Published var usageDays = 30
    @Published var usageBusy = false
    @Published var usageNotice = ""
    private var selectedMetadata: [RouterModel] = []
    private let home: URL
    let cli: URL

    init() {
        let root = ProcessInfo.processInfo.environment["CODEX_HOME"] ?? NSHomeDirectory() + "/.codex"
        home = URL(fileURLWithPath: root, isDirectory: true)
        cli = URL(fileURLWithPath: NSHomeDirectory() + "/.local/bin/bobocodexultra")
        reload()
    }

    func reload() {
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
                    self?.notice = "\(self?.models.count ?? 0) tool-capable models · choose any number"
                } else {
                    self?.notice = "Could not load OpenRouter's catalog. Check your connection."
                    _ = error
                }
            }
        }.resume()
    }

    func run(_ arguments: [String]) {
        guard !busy else { return }
        busy = true
        notice = "Working…"
        let process = cliProcess(arguments)
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            process.standardOutput = FileHandle.nullDevice
            let errors = Pipe()
            process.standardError = errors
            do {
                try process.run()
                process.waitUntilExit()
                let detail = String(data: errors.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
                DispatchQueue.main.async {
                    self?.busy = false
                    self?.notice = process.terminationStatus == 0 ? "Saved. Reopen Codex to refresh its model picker." : String(detail.prefix(320))
                    self?.reload()
                }
            } catch {
                DispatchQueue.main.async { self?.busy = false; self?.notice = "BCU CLI is unavailable. Run bobocodexultra install." }
            }
        }
    }

    private func cliProcess(_ arguments: [String]) -> Process {
        let process = Process()
        // Finder/login launches do not inherit an interactive shell's Python.
        if let python = Bundle.main.infoDictionary?["BCUPythonExecutable"] as? String,
           FileManager.default.isExecutableFile(atPath: python) {
            process.executableURL = URL(fileURLWithPath: python)
            process.arguments = [cli.path, "--no-color", "--no-animate"] + arguments
        } else {
            process.executableURL = cli
            process.arguments = ["--no-color", "--no-animate"] + arguments
        }
        var environment = ProcessInfo.processInfo.environment
        environment["CODEX_HOME"] = home.path
        environment["PATH"] = NSHomeDirectory() + "/.local/bin:/opt/homebrew/bin:/usr/local/bin:" + (environment["PATH"] ?? "/usr/bin:/bin")
        process.environment = environment
        return process
    }

    func loadUsage(refreshPrices: Bool = false) {
        guard !usageBusy else { return }
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
                    if store.defaultID == model.id { Text("Default").font(.caption).foregroundStyle(.mint) }
                    else if store.selected.contains(model.id) {
                        Button("Make default") { store.run(["model", "default", model.id]) }.disabled(store.busy)
                    }
                    if let context = model.context_length { Text("\(context / 1000)k").font(.caption).foregroundStyle(.secondary) }
                }.padding(.vertical, 3)
            }
            HStack {
                Text(store.notice).font(.caption).foregroundStyle(.secondary).lineLimit(2)
                Spacer()
                Text("Changes refresh BCU immediately; reopen Codex for the picker.").font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(18)
        .frame(minWidth: 680, minHeight: 530)
        .onAppear { store.browse(); store.reload() }
    }
}

final class StatusApp: NSObject, NSApplicationDelegate, NSMenuDelegate {
    private let store = BCUStore()
    private var item: NSStatusItem!
    private var window: NSWindow?
    private var usageWindow: NSWindow?
    private var timer: Timer?
    private let loginLabel = "com.bobocodexultra.menubar"
    private var loginAgent: URL { URL(fileURLWithPath: NSHomeDirectory() + "/Library/LaunchAgents/" + loginLabel + ".plist") }

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        item.button?.image = BCUIcon.draw(18, template: true)
        item.button?.toolTip = "Bobo Codex Ultra"
        let menu = NSMenu()
        menu.delegate = self
        item.menu = menu
        timer = Timer.scheduledTimer(withTimeInterval: 15, repeats: true) { [weak self] _ in
            self?.store.reload()
            if self?.usageWindow?.isVisible == true { self?.store.loadUsage() }
        }
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
        let toggle = NSMenuItem(title: store.enabled ? "Turn Off Shared Mode" : "Turn On Shared Mode", action: #selector(toggleMode), keyEquivalent: "")
        toggle.target = self; toggle.isEnabled = !store.busy
        menu.addItem(toggle)
        let manage = NSMenuItem(title: "Manage Models…", action: #selector(showModels), keyEquivalent: "m")
        manage.target = self
        menu.addItem(manage)
        let usage = NSMenuItem(title: "Usage & Costs…", action: #selector(showUsage), keyEquivalent: "u")
        usage.target = self
        menu.addItem(usage)
        let account = NSMenuItem(title: "Enter OpenRouter Key…", action: #selector(openLogin), keyEquivalent: "")
        account.target = self
        menu.addItem(account)
        menu.addItem(.separator())
        let openCodex = NSMenuItem(title: "Open Codex Desktop", action: #selector(openCodex), keyEquivalent: "")
        openCodex.target = self; menu.addItem(openCodex)
        let login = NSMenuItem(title: "Launch at Login", action: #selector(toggleLogin), keyEquivalent: "")
        login.target = self; login.state = FileManager.default.fileExists(atPath: loginAgent.path) ? .on : .off
        menu.addItem(login)
        let docs = NSMenuItem(title: "Documentation", action: #selector(openDocs), keyEquivalent: "")
        docs.target = self; menu.addItem(docs)
        menu.addItem(.separator())
        let quit = NSMenuItem(title: "Quit BCU Menu", action: #selector(quitMenu), keyEquivalent: "q")
        quit.target = self; menu.addItem(quit)
        item.button?.alphaValue = store.enabled ? 1 : 0.55
    }

    @objc private func toggleMode() { store.run([store.enabled ? "off" : "on"]) }
    @objc private func showModels() {
        if window == nil {
            let controller = NSHostingController(rootView: ManagerView(store: store))
            let created = NSWindow(contentViewController: controller)
            created.title = "BCU · Manage Models"
            created.setContentSize(NSSize(width: 770, height: 590))
            created.center()
            created.isReleasedWhenClosed = false
            window = created
        }
        window?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
    @objc private func openLogin() {
        let escaped = store.cli.path.replacingOccurrences(of: "'", with: "'\\''")
        let terminalCommand = "'\(escaped)' login"
        let appleString = terminalCommand.replacingOccurrences(of: "\\", with: "\\\\").replacingOccurrences(of: "\"", with: "\\\"")
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
        process.arguments = ["-e", "tell application \"Terminal\" to do script \"\(appleString)\""]
        try? process.run()
    }
    @objc private func showUsage() {
        if usageWindow == nil {
            let controller = NSHostingController(rootView: UsageView(store: store))
            let created = NSWindow(contentViewController: controller)
            created.title = "BCU · Usage & Costs"
            created.setContentSize(NSSize(width: 960, height: 650))
            created.center()
            created.isReleasedWhenClosed = false
            usageWindow = created
        }
        store.loadUsage()
        usageWindow?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
    @objc private func openCodex() {
        let path = "/Applications/ChatGPT.app"
        if FileManager.default.fileExists(atPath: path) { NSWorkspace.shared.open(URL(fileURLWithPath: path)) }
        else { store.notice = "Codex desktop app was not found in /Applications."; showModels() }
    }
    @objc private func toggleLogin() {
        let manager = FileManager.default
        if manager.fileExists(atPath: loginAgent.path) {
            guard let data = try? Data(contentsOf: loginAgent),
                  let plist = try? PropertyListSerialization.propertyList(from: data, format: nil) as? [String: Any],
                  plist["Label"] as? String == loginLabel else { return }
            try? manager.removeItem(at: loginAgent)
        } else {
            let executable = Bundle.main.executableURL?.path ?? ""
            guard !executable.isEmpty else { return }
            let root = ProcessInfo.processInfo.environment["CODEX_HOME"] ?? NSHomeDirectory() + "/.codex"
            let data = try? PropertyListSerialization.data(fromPropertyList: [
                "Label": loginLabel, "ProgramArguments": [executable], "RunAtLoad": true,
                "KeepAlive": false, "EnvironmentVariables": ["CODEX_HOME": root]
            ], format: .xml, options: 0)
            try? manager.createDirectory(at: loginAgent.deletingLastPathComponent(), withIntermediateDirectories: true)
            if let data { try? data.write(to: loginAgent, options: .atomic); try? manager.setAttributes([.posixPermissions: 0o600], ofItemAtPath: loginAgent.path) }
        }
    }
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
