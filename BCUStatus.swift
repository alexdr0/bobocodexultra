import AppKit
import SwiftUI

// The status icon and Dock/Applications icon share the same hand-drawn mark:
// a compact circuit-board B with two terminal dots inside a rounded tile.
enum BCUIcon {
    static func draw(_ size: CGFloat, template: Bool) -> NSImage {
        let image = NSImage(size: NSSize(width: size, height: size))
        image.lockFocus()
        let scale = size / 24
        let canvas = NSAffineTransform()
        canvas.scale(by: scale)
        canvas.concat()
        let tile = NSBezierPath(roundedRect: NSRect(x: 1.3, y: 1.3, width: 21.4, height: 21.4), xRadius: 6, yRadius: 6)
        if template {
            NSColor.black.setStroke()
            tile.lineWidth = 1.5
            tile.stroke()
        } else {
            NSColor(calibratedRed: 0.12, green: 0.08, blue: 0.21, alpha: 1).setFill()
            tile.fill()
            NSColor(calibratedRed: 0.40, green: 0.91, blue: 0.93, alpha: 1).setStroke()
            tile.lineWidth = 0.9
            tile.stroke()
        }
        (template ? NSColor.black : NSColor.white).setStroke()
        let mark = NSBezierPath()
        mark.lineWidth = 2.35
        mark.lineCapStyle = .round
        mark.lineJoinStyle = .round
        mark.move(to: NSPoint(x: 7.2, y: 5.3))
        mark.line(to: NSPoint(x: 7.2, y: 18.7))
        mark.line(to: NSPoint(x: 12, y: 18.7))
        mark.curve(to: NSPoint(x: 12, y: 12.2), controlPoint1: NSPoint(x: 17.6, y: 18.7), controlPoint2: NSPoint(x: 17.8, y: 12.2))
        mark.line(to: NSPoint(x: 7.2, y: 12.2))
        mark.line(to: NSPoint(x: 12.3, y: 12.2))
        mark.curve(to: NSPoint(x: 12, y: 5.3), controlPoint1: NSPoint(x: 18.6, y: 12.2), controlPoint2: NSPoint(x: 18.3, y: 5.3))
        mark.line(to: NSPoint(x: 7.2, y: 5.3))
        mark.stroke()
        (template ? NSColor.black : NSColor(calibratedRed: 0.98, green: 0.37, blue: 0.77, alpha: 1)).setFill()
        NSBezierPath(ovalIn: NSRect(x: 17.3, y: 16.65, width: 2.6, height: 2.6)).fill()
        NSBezierPath(ovalIn: NSRect(x: 17.3, y: 4.7, width: 2.6, height: 2.6)).fill()
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
        return withoutProvider.prefix(1).uppercased() + withoutProvider.dropFirst() + " (BCU)"
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
        let path = cli
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let process = Process()
            process.executableURL = path
            process.arguments = ["--no-color", "--no-animate"] + arguments
            process.standardOutput = Pipe()
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
        timer = Timer.scheduledTimer(withTimeInterval: 15, repeats: true) { [weak self] _ in self?.store.reload() }
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
