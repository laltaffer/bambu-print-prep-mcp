// Compiled with AX_FIXTURES: this harness never reads or operates a real app.
func fixture(_ slot: String = "A2", printer: String = "Test P2S") -> Node {
    let radioNames = ["On", "Off", "Auto", "On", "Off", "Auto", "On", "Off"]
    var children = [
        Node(kAXHeadingRole, "Send to print"),
        Node(kAXGroupRole, "", children: [Node(kAXStaticTextRole, printer), Node(kAXImageRole, "chevron_down")]),
        Node(kAXStaticTextRole, slot), Node(kAXStaticTextRole, "PLA"),
        Node(kAXButtonRole, "confirm", children: [Node(kAXStaticTextRole, "Send")])
    ]
    children += radioNames.enumerated().map {
        Node(kAXGroupRole, "", children: [Node(kAXRadioButtonRole, $0.element)] +
            ([1, 2, 5].contains($0.offset) ? [Node(kAXImageRole, "radio")] : []))
    }
    return Node(kAXGroupRole, "", children: children)
}
func mustRefuse(_ body: () throws -> Void) {
    do { try body(); fatalError("Expected refusal") } catch {}
}
let parsed = try reviewSnapshot(fixture(), "Test P2S")
assert(parsed["ams_slot"] == "A2")
assert(parsed["material"] == "PLA")
assert(parsed["timelapse"] == "Off")
assert(parsed["bed_leveling"] == "Auto")
assert(parsed["flow_calibration"] == "Auto")
mustRefuse { _ = try reviewSnapshot(fixture(), "Other P2S") }
mustRefuse { _ = try reviewSnapshot(fixture("?"), "Test P2S") }
let multi = fixture()
multi.children.append(Node(kAXStaticTextRole, "A3"))
mustRefuse { _ = try reviewSnapshot(multi, "Test P2S") }
let unset = fixture()
unset.children.removeLast()
mustRefuse { _ = try reviewSnapshot(unset, "Test P2S") }
let noIndicators = fixture()
for option in noIndicators.children where option.all.contains(where: { $0.role == kAXRadioButtonRole }) {
    option.children = option.children.filter { $0.role != kAXImageRole }
}
mustRefuse { _ = try reviewSnapshot(noIndicators, "Test P2S") }
let doubleChecked = fixture()
doubleChecked.children[5].children.append(Node(kAXImageRole, "radio"))
mustRefuse { _ = try reviewSnapshot(doubleChecked, "Test P2S") }
let ambiguous = fixture()
ambiguous.children.append(Node(kAXButtonRole, "confirm", children: [Node(kAXStaticTextRole, "Send")]))
mustRefuse { _ = try reviewSnapshot(ambiguous, "Test P2S") }
let plateRoot = Node(kAXGroupRole, "", children: [
    Node(kAXPopUpButtonRole, "", children: [Node(kAXStaticTextRole, "cube.gcode.3mf")]),
    Node(kAXButtonRole, "", children: [Node(kAXStaticTextRole, "1")]),
    Node(kAXGroupRole, "", children: ["Compatible Printer:", "P2S", "Bed type:", "PEI",
        "Filaments:", "PLA", "Nozzle Diameter:", "0.4", "Time:", "9m", "Weight:", "0.15g"]
        .map { Node(kAXStaticTextRole, $0) })
])
let plateMetadata = try plateInfo(plateRoot, "cube.gcode.3mf")
assert(plateMetadata.contains("Nozzle Diameter: 0.4"))
mustRefuse { _ = try plateInfo(plateRoot, "different.gcode.3mf") }
let otherPrinter = fixture(printer: "Other P2S")
otherPrinter.children.append(Node(kAXGroupRole, "", children: [Node(kAXStaticTextRole, "Test P2S")]))
mustRefuse { _ = try reviewSnapshot(otherPrinter, "Test P2S") }
plateRoot.children.append(Node(kAXPopUpButtonRole, "", children: [Node(kAXStaticTextRole, "other.gcode.3mf")]))
mustRefuse { _ = try plateInfo(plateRoot, "cube.gcode.3mf") }
plateRoot.children.removeLast()
plateRoot.children.append(Node(kAXGroupRole, "", children: ["Compatible Printer:", "Other",
    "Bed type:", "PEI", "Filaments:", "PETG", "Nozzle Diameter:", "0.6", "Time:", "1m", "Weight:", "1g"]
    .map { Node(kAXStaticTextRole, $0) }))
mustRefuse { _ = try plateInfo(plateRoot, "cube.gcode.3mf") }
let changed = fixture("A3")
let changedReview = try reviewSnapshot(changed, "Test P2S")
assert(changedReview != parsed)
func device(_ printer: String, _ progress: String) -> Node {
    Node(kAXGroupRole, "", children: [
        Node(kAXGroupRole, "", children: [Node(linkRole, "My Printers"),
            Node(kAXStaticTextRole, "/"), Node(kAXStaticTextRole, printer)]),
        Node(kAXStaticTextRole, "Online"), Node(kAXStaticTextRole, progress)
    ])
}
let live = "Printing Progress cube.gcode.3mf 0 / 25"
let accepted = try matchingNewJob(device("Test P2S", live), "Test P2S", "cube.gcode.3mf", [])
assert(accepted == live)
mustRefuse { _ = try matchingNewJob(device("Other P2S", live), "Test P2S", "cube.gcode.3mf", []) }
mustRefuse { _ = try matchingNewJob(device("Test P2S", live), "Test P2S", "cube.gcode.3mf", [live]) }
mustRefuse { _ = try matchingNewJob(device("Test P2S", "Printing Progress cube.gcode.3mf_other 0 / 25"),
    "Test P2S", "cube.gcode.3mf", []) }
print("Native review fixtures passed; no app accessed or action performed.")
