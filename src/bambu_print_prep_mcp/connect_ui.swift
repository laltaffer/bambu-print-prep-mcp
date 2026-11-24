// Narrow macOS Accessibility adapter for the English Bambu Connect review flow.
import AppKit
import ApplicationServices
import Foundation

let linkRole = "AXLink"

struct UIError: Error { let message: String }
func fail(_ message: String) throws -> Never { throw UIError(message: message) }
func attribute(_ e: AXUIElement, _ key: String) -> CFTypeRef? {
    var value: CFTypeRef?
    guard AXUIElementCopyAttributeValue(e, key as CFString, &value) == .success else { return nil }
    return value
}
final class Node {
    let element: AXUIElement
    let role: String
    let label: String
    let enabled: Bool
    var children: [Node] = []
    init(_ element: AXUIElement) {
        self.element = element
        role = attribute(element, kAXRoleAttribute) as? String ?? ""
        let labels = [kAXTitleAttribute, kAXDescriptionAttribute, kAXValueAttribute]
            .compactMap { attribute(element, $0) as? String }
            .filter { !$0.isEmpty && !$0.contains("://") }
        label = labels.first ?? ""
        enabled = (attribute(element, kAXEnabledAttribute) as? NSNumber)?.boolValue ?? true
    }
    #if AX_FIXTURES
    init(_ role: String, _ label: String, children: [Node] = []) {
        element = AXUIElementCreateApplication(0)
        self.role = role; self.label = label
        enabled = true; self.children = children
    }
    #endif
    var all: [Node] { [self] + children.flatMap { $0.all } }
    var texts: [String] { all.filter { $0.role == kAXStaticTextRole }.map { $0.label } }
}
func tree(_ root: AXUIElement) throws -> Node {
    var count = 0
    func read(_ e: AXUIElement, _ depth: Int) throws -> Node {
        count += 1
        guard count <= 3000 && depth <= 40 else { try fail("Connect UI exceeds supported bounds.") }
        let n = Node(e)
        n.children = try (attribute(e, kAXChildrenAttribute) as? [AXUIElement] ?? [])
            .map { try read($0, depth + 1) }
        return n
    }
    return try read(root, 0)
}
func window() throws -> Node {
    guard AXIsProcessTrusted() else {
        try fail("macOS Accessibility access is required for the MCP host; no permission was changed.")
    }
    let apps = NSRunningApplication.runningApplications(withBundleIdentifier: "com.bambulab.bambu-connect")
    guard apps.count == 1 else { try fail("Open exactly one Bambu Connect instance and sign in yourself.") }
    let app = AXUIElementCreateApplication(apps[0].processIdentifier)
    let windows = attribute(app, kAXWindowsAttribute) as? [AXUIElement] ?? []
    let mainWindows = windows.filter {
        let title = attribute($0, kAXTitleAttribute) as? String ?? ""
        return title.hasPrefix("Bambu Connect") &&
            (attribute($0, kAXMinimizedAttribute) as? NSNumber)?.boolValue != true
    }
    guard mainWindows.count == 1 else {
        try fail("Expected one visible Connect main window (found \(mainWindows.count)). Open Connect and close extra main windows.")
    }
    return try tree(mainWindows[0])
}
func press(_ node: Node) throws {
    guard node.enabled else { try fail("Required Connect control is disabled.") }
    guard AXUIElementPerformAction(node.element, kAXPressAction as CFString) == .success else {
        try fail("Connect did not acknowledge the requested UI action.")
    }
}
func control(_ root: Node, _ label: String, role: String = kAXButtonRole) throws -> Node {
    let matches = root.all.filter {
        $0.role == role && ($0.label.lowercased() == label.lowercased() ||
            $0.texts.map { $0.lowercased() } == [label.lowercased()])
    }
    guard matches.count == 1 else { try fail("Connect control is missing or ambiguous: \(label)") }
    return matches[0]
}
func waitFor<T>(_ read: () throws -> T) throws -> T {
    let until = Date().addingTimeInterval(12)
    repeat {
        do { return try read() } catch {
            if Date() >= until { throw error }
            RunLoop.current.run(until: Date().addingTimeInterval(0.15))
        }
    } while true
}
func find(_ root: Node, role: String, text: String) -> [Node] {
    root.all.filter { $0.role == role && $0.label == text }
}
func terminalMatches(_ root: Node, _ predicate: (Node) -> Bool) -> [Node] {
    let candidates = root.all.filter(predicate)
    return candidates.filter { parent in
        !candidates.contains { child in
            child !== parent && parent.all.contains(where: { $0 === child })
        }
    }
}
func selectedPrinter(_ dialog: Node) throws -> String {
    let choices = terminalMatches(dialog) { n in
        n.role == kAXGroupRole && n.texts.count == 1 &&
            n.all.filter { $0.role == kAXImageRole && $0.label == "chevron_down" }.count == 1
    }
    guard choices.count == 1 else { try fail("Selected printer control is missing or ambiguous.") }
    return choices[0].texts[0]
}
func reviewDialog(_ root: Node) throws -> Node {
    // Take the smallest container containing the heading and the actual Send button.
    let candidates = root.all.filter { n in
        !find(n, role: kAXHeadingRole, text: "Send to print").isEmpty &&
        (try? control(n, "Send")) != nil
    }
    guard let n = candidates.last else { try fail("Open Connect's Send to print review dialog.") }
    return n
}
func materialAndSlot(_ dialog: Node) throws -> (String, String) {
    let texts = dialog.texts
    let slots = texts.enumerated().filter { $0.element.range(of: "^[A-Z][1-4]$", options: .regularExpression) != nil }
    guard slots.count == 1, slots[0].offset + 1 < texts.count else {
        try fail("This version supports one filament mapped to one AMS slot only.")
    }
    let material = texts[slots[0].offset + 1]
    guard material.range(of: "^[A-Z][A-Z0-9+ /_-]{0,24}$", options: .regularExpression) != nil else {
        try fail("Connect filament mapping is unresolved.")
    }
    return (material, slots[0].element)
}
func reviewSnapshot(_ root: Node, _ printer: String) throws -> [String: String] {
    let dialog = try reviewDialog(root)
    let actualPrinter = try selectedPrinter(dialog)
    guard actualPrinter == printer else {
        try fail("Selected printer differs from the requested printer.")
    }
    let send = try control(dialog, "Send")
    guard send.enabled, send.texts == ["Send"] else { try fail("Send is not uniquely available.") }
    let radios = dialog.all.filter { $0.role == kAXRadioButtonRole }
    guard radios.count == 8 else { try fail("Connect print options changed or are unsupported.") }
    func choice(_ range: Range<Int>, _ labels: [String]) throws -> String {
        let group = range.map { radios[$0] }
        guard group.map({ $0.label }) == labels else { try fail("Unexpected Connect options layout.") }
        // Connect's AXValue radio numbers do not reliably reflect its checked
        // state. Its selected option exposes a distinct accessible "radio" image
        // beside the radio element. Require that observed indicator in its own
        // one-radio container; never infer a default from zero AXValues.
        let selected = group.filter { radio in
            let parents = dialog.all.filter { n in
                n.role == kAXGroupRole && n.all.contains(where: { $0 === radio }) &&
                    n.all.filter { $0.role == kAXRadioButtonRole }.count == 1
            }
            guard let parent = parents.last else { return false }
            return parent.all.filter { $0.role == kAXImageRole && $0.label == "radio" }.count == 1
        }
        guard selected.count == 1 else {
            try fail("Print options have not settled or selected indicators are unavailable.")
        }
        return selected[0].label
    }
    let (material, slot) = try materialAndSlot(dialog)
    return ["printer": actualPrinter, "material": material, "ams_slot": slot,
        "timelapse": try choice(0..<2, ["On", "Off"]),
        "bed_leveling": try choice(2..<5, ["Auto", "On", "Off"]),
        "flow_calibration": try choice(5..<8, ["Auto", "On", "Off"])]
}
func snapshot(_ printer: String) throws -> [String: String] {
    try reviewSnapshot(window(), printer)
}
func stableReview(_ printer: String) throws -> [String: String] {
    var previous: [String: String]?
    return try waitFor {
        let current = try snapshot(printer)
        guard previous == current else {
            previous = current
            try fail("Waiting for stable Connect options.")
        }
        return current
    }
}
func deviceProgress(_ root: Node, _ printer: String) throws -> [String] {
    let breadcrumbs = terminalMatches(root) { n in
        n.all.contains { $0.role == linkRole && $0.label == "My Printers" } &&
            n.texts.last == printer
    }
    guard breadcrumbs.count == 1, root.texts.contains("Online") else {
        try fail("Expected the requested online printer's device page.")
    }
    let jobs = root.texts.filter { $0.hasPrefix("Printing Progress ") }
    guard jobs.count <= 1 else { try fail("Printer progress is ambiguous.") }
    return jobs
}
func idle(_ printer: String) throws -> [String] {
    let root = try window()
    if (try? reviewDialog(root)) != nil {
        try press(control(try reviewDialog(root), "Cancel"))
    } else if root.texts.contains(where: {
        $0.range(of: #"^You will import the file "job_[a-f0-9]{32}_[a-f0-9]{12}\.gcode\.3mf"\.$"#,
            options: .regularExpression) != nil
    }) {
        // Recover only our own interrupted staged-import dialog, not foreign prompts.
        try press(control(root, "Cancel"))
    }
    let devices = try waitFor { try control(window(), "Devices", role: linkRole) }
    try press(devices)
    let card: Node = try waitFor {
        let root = try window()
        let cards = root.all.filter { $0.role == linkRole && $0.label.hasPrefix(printer + " Bed:") }
        guard cards.count == 1 else { try fail("Requested printer card is missing or ambiguous.") }
        guard cards[0].label.hasSuffix(" Idle") else {
            try fail("Requested printer is not explicitly Idle; no print will be submitted.")
        }
        return cards[0]
    }
    try press(card)
    return try waitFor { try deviceProgress(window(), printer) }
}
func plateInfo(_ root: Node, _ filename: String) throws -> String {
    let choosers = root.all.filter { n in
        n.role == kAXPopUpButtonRole && n.texts.contains { $0.hasSuffix(".gcode.3mf") }
    }
    guard choosers.count == 1, choosers[0].texts == [filename] else {
        try fail("Connect is displaying a different file; stage the approved job again.")
    }
    let fields = ["Compatible Printer", "Bed type", "Filaments", "Nozzle Diameter", "Time", "Weight"]
    let panels = terminalMatches(root) { n in
        let text = n.texts.joined(separator: " ")
        return fields.allSatisfy { text.contains($0) }
    }
    let info = panels.count == 1 ? panels[0].texts.joined(separator: " ")
        .split(whereSeparator: { $0.isWhitespace }).joined(separator: " ")
        : nil
    let plates = root.all.filter {
        $0.role == kAXButtonRole && $0.texts.count == 1 &&
            $0.texts[0].range(of: #"^[1-9][0-9]*$"#, options: .regularExpression) != nil
    }
    guard let info = info, plates.count == 1, plates[0].texts == ["1"] else {
        try fail("Expected one sliced plate with readable compatibility information.")
    }
    return info
}
func plate(_ filename: String) throws -> String {
    try plateInfo(window(), filename)
}
func openReview(_ filename: String) throws -> String {
    let root = try window()
    let info = try plateInfo(root, filename)
    // Bind the Print action to the very same plate snapshot, not a second window read.
    try press(control(root, "Print"))
    _ = try waitFor { try reviewDialog(window()) }
    return info
}
func matchingNewJob(_ root: Node, _ printer: String, _ filename: String, _ baseline: [String]) throws -> String {
    let jobs = try deviceProgress(root, printer)
    let prefix = "Printing Progress " + filename
    guard jobs.count == 1, jobs[0].hasPrefix(prefix + " "),
          !baseline.contains(jobs[0]), !jobs[0].contains("Failed"),
          !jobs[0].contains("Finished ") else { try fail("New job acceptance is not yet visible.") }
    return jobs[0]
}
#if !AX_FIXTURES
let input = FileHandle.standardInput.readDataToEndOfFile()
var attemptedSend = false
do {
    guard let request = try JSONSerialization.jsonObject(with: input) as? [String: Any],
          let action = request["action"] as? String,
          let printer = request["printer"] as? String, !printer.isEmpty else {
        try fail("Invalid Connect adapter request.")
    }
    var result: [String: Any] = [:]
    switch action {
    case "idle":
        _ = try idle(printer)
        result = ["status": "idle"]
    case "stage":
        guard let filename = request["filename"] as? String else { try fail("Missing staged filename.") }
        let expectedText = "You will import the file \"\(filename)\"."
        try waitFor {
            let root = try window()
            guard root.texts.contains(expectedText) else { try fail("Expected exact staged import confirmation.") }
            try press(control(root, "Import Gcode 3MF"))
        }
        _ = try waitFor { try plate(filename) }
        let info = try openReview(filename)
        let review = try stableReview(printer)
        result = ["review": review, "plate_info": info]
    case "send":
        guard let filename = request["filename"] as? String,
              let expected = request["review"] as? [String: String],
              let info = request["plate_info"] as? String else { try fail("Missing approved review.") }
        guard try stableReview(printer) == expected else { try fail("Connect settings changed after approval.") }
        // Check readiness again; reopen and compare the complete review after navigating.
        let baseline = try idle(printer)
        guard !baseline.contains(where: { $0.hasPrefix("Printing Progress " + filename + " ") }) else {
            try fail("This staged job has already appeared on the printer. Do not repeat it.")
        }
        let printLink = try waitFor { try control(window(), "Print", role: linkRole) }
        try press(printLink)
        let currentInfo = try waitFor { try plate(filename) }
        guard currentInfo == info else { try fail("Plate information changed after approval.") }
        let reviewedInfo = try openReview(filename)
        guard reviewedInfo == info else { try fail("Plate metadata changed before opening review.") }
        guard try stableReview(printer) == expected else { try fail("Connect settings changed after readiness check.") }
        // Use this final fresh root for BOTH complete settings comparison and the Send control.
        let finalRoot = try window()
        guard try reviewSnapshot(finalRoot, printer) == expected else {
            try fail("Connect settings changed immediately before Send.")
        }
        let dialog = try reviewDialog(finalRoot)
        let button = try control(dialog, "Send")
        guard button.texts == ["Send"] else { try fail("Final Send control changed.") }
        guard let expires = request["expires_at"] as? Double,
              Date().timeIntervalSince1970 <= expires else { try fail("Review expired before Send.") }
        attemptedSend = true
        try press(button)  // Exactly one attempt. Never retry or dismiss a further warning.
        do {
            let progress: String = try waitFor {
                try matchingNewJob(window(), printer, filename, baseline)
            }
            result = ["status": "job_accepted", "progress": progress, "send_attempted": true]
        } catch {
            result = ["status": "submission_unknown", "send_attempted": true,
                "message": "Send was attempted once. Check the printer before any new attempt."]
        }
    default:
        try fail("Unsupported Connect adapter action.")
    }
    let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
    FileHandle.standardOutput.write(data)
} catch {
    let message = (error as? UIError)?.message ?? "Connect UI operation failed. No automatic retry."
    let data = try! JSONSerialization.data(withJSONObject: ["error": message, "send_attempted": attemptedSend])
    FileHandle.standardOutput.write(data)
    exit(1)
}
#endif
