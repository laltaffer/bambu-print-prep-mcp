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
#if AX_FIXTURES
var fixtureWindow: (() throws -> Node)?
var fixturePress: ((Node) throws -> Void)?
#endif
func window() throws -> Node {
    #if AX_FIXTURES
    guard let read = fixtureWindow else { try fail("No fixture window provided; no app access.") }
    return try read()
    #else
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
    #endif
}
func press(_ node: Node) throws {
    #if AX_FIXTURES
    guard let action = fixturePress else { try fail("No fixture action provided; no app access.") }
    try action(node)
    #else
    guard node.enabled else { try fail("Required Connect control is disabled.") }
    guard AXUIElementPerformAction(node.element, kAXPressAction as CFString) == .success else {
        try fail("Connect did not acknowledge the requested UI action.")
    }
    #endif
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
struct AMSSlot: Codable, Equatable {
    let ams_slot: String
    let material: String
}
struct FilamentMapping: Codable, Equatable {
    // Review order, not an inferred slicer filament ID or color.
    let filament_index: Int
    let source_material: String
    let ams_slot: String
    let material: String
}
struct Review: Codable, Equatable {
    let printer: String
    let filament_mappings: [FilamentMapping]
    let detected_ams_slots: [AMSSlot]
    let timelapse: String
    let bed_leveling: String
    let flow_calibration: String
}
func decode<T: Decodable>(_ value: Any?, as type: T.Type) throws -> T {
    guard let value = value, JSONSerialization.isValidJSONObject(value) else {
        try fail("Missing or unsupported AMS review data. Prepare a fresh review.")
    }
    return try JSONDecoder().decode(type, from: JSONSerialization.data(withJSONObject: value))
}
func jsonObject<T: Encodable>(_ value: T) throws -> Any {
    try JSONSerialization.jsonObject(with: JSONEncoder().encode(value))
}
func isSlot(_ text: String) -> Bool {
    text.range(of: #"^(?:[A-Z]+[1-9][0-9]*|HT - [A-Z]+|[1-4])$"#,
        options: .regularExpression) != nil
}
func isMaterial(_ text: String) -> Bool {
    text.range(of: #"^[A-Za-z][A-Za-z0-9 .+/_()-]{0,63}$"#, options: .regularExpression) != nil &&
        !["Empty", "Unknown"].contains(text)
}
func checkedInventory(_ slots: [AMSSlot]) throws -> [AMSSlot] {
    guard !slots.isEmpty, Set(slots.map { $0.ams_slot }).count == slots.count,
        slots.allSatisfy({ isSlot($0.ams_slot) && !$0.material.isEmpty }) else {
        try fail("Detected AMS slot inventory is empty or ambiguous.")
    }
    return slots.sorted { $0.ams_slot < $1.ams_slot }
}
func detectedSlots(_ root: Node, _ printer: String) throws -> [AMSSlot] {
    _ = try deviceProgress(root, printer)
    // Enumerate every recognized slot label before inspecting its material.
    // Unreadable rows cannot disappear, even when each slot has its own wrapper.
    // AMS lite uses 1...4; unrelated/ambiguous numeric text must fail closed.
    let containers = root.all.filter { parent in
        parent.children.contains { $0.role == kAXStaticTextRole && isSlot($0.label) }
    }
    let slots = try containers.flatMap { parent -> [AMSSlot] in
        try parent.children.enumerated().compactMap { i, label -> AMSSlot? in
            guard label.role == kAXStaticTextRole, isSlot(label.label) else { return nil }
            guard i + 1 < parent.children.count else { try fail("Incomplete detected AMS slot row.") }
            let material = parent.children[i + 1]
            guard material.role == kAXGroupRole, material.texts.count == 1 else {
                try fail("Detected AMS slot material is unreadable.")
            }
            return AMSSlot(ams_slot: label.label, material: material.texts[0])
        }
    }
    return try checkedInventory(slots)
}
func filamentMappings(_ dialog: Node, _ sources: [String], _ slots: [AMSSlot]) throws -> [FilamentMapping] {
    // Match complete cards, never flatten adjacent slots into an unbound list.
    let cards = terminalMatches(dialog) { n in
        return n.role == kAXGroupRole && n.children.count == 2 &&
            n.children[0].role == kAXGroupRole && n.children[0].texts.count == 1 &&
            isMaterial(n.children[0].texts[0]) && n.children[1].role == kAXGroupRole &&
            !n.children[1].texts.isEmpty
    }
    guard !sources.isEmpty, cards.count == sources.count else {
        try fail("Every sliced filament must have one resolved AMS mapping.")
    }
    return try cards.enumerated().map { index, card in
        let text = card.texts
        guard text.count == 3, isSlot(text[1]), isMaterial(text[2]),
            text[0] == sources[index], text[0] == text[2],
            slots.contains(AMSSlot(ams_slot: text[1], material: text[2])) else {
            try fail("Filament mapping differs from the plate or detected AMS inventory.")
        }
        return FilamentMapping(filament_index: index + 1, source_material: text[0],
            ams_slot: text[1], material: text[2])
    }
}
func reviewSnapshot(_ root: Node, _ printer: String, _ sources: [String], _ slots: [AMSSlot]) throws -> Review {
    let dialog = try reviewDialog(root)
    guard !dialog.texts.contains("Left Nozzle"), !dialog.texts.contains("Right Nozzle") else {
        try fail("Multi-nozzle routing is not supported by this adapter.")
    }
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
    let inventory = try checkedInventory(slots)
    return Review(printer: actualPrinter,
        filament_mappings: try filamentMappings(dialog, sources, inventory),
        detected_ams_slots: inventory,
        timelapse: try choice(0..<2, ["On", "Off"]),
        bed_leveling: try choice(2..<5, ["Auto", "On", "Off"]),
        flow_calibration: try choice(5..<8, ["Auto", "On", "Off"]))
}
func stableReview(_ printer: String, _ sources: [String], _ slots: [AMSSlot]) throws -> Review {
    var previous: Review?
    return try waitFor {
        let current = try reviewSnapshot(window(), printer, sources, slots)
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
struct DeviceState {
    let progress: [String]
    let slots: [AMSSlot]
}
func idle(_ printer: String) throws -> DeviceState {
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
    return try waitFor {
        let root = try window()
        return DeviceState(progress: try deviceProgress(root, printer), slots: try detectedSlots(root, printer))
    }
}
struct PlateSnapshot {
    let info: String
    let filaments: [String]
}
func plateInfo(_ root: Node, _ filename: String) throws -> PlateSnapshot {
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
    let texts = panels[0].texts
    guard let start = texts.firstIndex(of: "Filaments:"),
        let end = texts.firstIndex(of: "Nozzle Diameter:"), start + 1 < end else {
        try fail("Plate filament list is missing or ambiguous.")
    }
    let filaments = Array(texts[(start + 1)..<end])
    guard filaments.allSatisfy(isMaterial) else { try fail("Plate materials are unreadable.") }
    return PlateSnapshot(info: info, filaments: filaments)
}
func plate(_ filename: String) throws -> PlateSnapshot {
    try plateInfo(window(), filename)
}
func openReview(_ filename: String) throws -> PlateSnapshot {
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
func submitReviewed(_ printer: String, _ filename: String, _ expected: Review,
    _ info: String, _ expires: Double, onAttempt: () -> Void) throws -> [String: Any] {
    let sources = expected.filament_mappings.map { $0.source_material }
    guard try stableReview(printer, sources, expected.detected_ams_slots) == expected else { try fail("Connect settings changed after approval.") }
    // Check readiness again; reopen and compare the complete review after navigating.
    let device = try idle(printer)
    guard device.slots == expected.detected_ams_slots else {
        try fail("Detected AMS slots or materials changed after approval.")
    }
    let baseline = device.progress
    guard !baseline.contains(where: { $0.hasPrefix("Printing Progress " + filename + " ") }) else {
        try fail("This staged job has already appeared on the printer. Do not repeat it.")
    }
    let printLink = try waitFor { try control(window(), "Print", role: linkRole) }
    try press(printLink)
    let currentInfo = try waitFor { try plate(filename) }
    guard currentInfo.info == info, currentInfo.filaments == sources else { try fail("Plate information changed after approval.") }
    let reviewedInfo = try openReview(filename)
    guard reviewedInfo.info == info, reviewedInfo.filaments == sources else { try fail("Plate metadata changed before opening review.") }
    guard try stableReview(printer, sources, device.slots) == expected else { try fail("Connect settings changed after readiness check.") }
    // Use this final fresh root for BOTH complete settings comparison and the Send control.
    let finalRoot = try window()
    guard try reviewSnapshot(finalRoot, printer, sources, device.slots) == expected else {
        try fail("Connect settings changed immediately before Send.")
    }
    let dialog = try reviewDialog(finalRoot)
    let button = try control(dialog, "Send")
    guard button.texts == ["Send"] else { try fail("Final Send control changed.") }
    guard Date().timeIntervalSince1970 <= expires else { try fail("Review expired before Send.") }
    onAttempt()
    try press(button)  // Exactly one attempt. Never retry or dismiss a further warning.
    do {
        let progress: String = try waitFor {
            try matchingNewJob(window(), printer, filename, baseline)
        }
        return ["status": "job_accepted", "progress": progress, "send_attempted": true]
    } catch {
        return ["status": "submission_unknown", "send_attempted": true,
            "message": "Send was attempted once. Check the printer before any new attempt."]
    }
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
        let device = try idle(printer)
        result = ["status": "idle", "detected_ams_slots": try jsonObject(device.slots)]
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
        let slots = try decode(request["detected_ams_slots"], as: [AMSSlot].self)
        let review = try stableReview(printer, info.filaments, slots)
        result = ["review": try jsonObject(review), "plate_info": info.info]
    case "send":
        guard let filename = request["filename"] as? String,
              let info = request["plate_info"] as? String else { try fail("Missing approved review.") }
        let expected = try decode(request["review"], as: Review.self)
        guard let expires = request["expires_at"] as? Double else { try fail("Missing review expiry.") }
        result = try submitReviewed(printer, filename, expected, info, expires) { attemptedSend = true }
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
