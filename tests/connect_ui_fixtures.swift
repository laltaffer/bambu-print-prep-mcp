// Compiled with AX_FIXTURES: this harness never reads or operates a real app.
let detected = [AMSSlot(ams_slot: "A1", material: "PLA"),
    AMSSlot(ams_slot: "A2", material: "PLA"),
    AMSSlot(ams_slot: "B3", material: "PLA"),
    AMSSlot(ams_slot: "G4", material: "PLA"),
    AMSSlot(ams_slot: "HT - A", material: "PETG")]
func mappingCard(_ slot: String, source: String = "PLA", target: String = "PLA") -> Node {
    Node(kAXGroupRole, "", children: [
        Node(kAXGroupRole, "", children: [Node(kAXStaticTextRole, source)]),
        Node(kAXGroupRole, "", children: [Node(kAXStaticTextRole, slot), Node(kAXStaticTextRole, target)])
    ])
}
func fixture(_ slot: String = "A2", printer: String = "Test P2S", cards: [Node]? = nil) -> Node {
    let radioNames = ["On", "Off", "Auto", "On", "Off", "Auto", "On", "Off"]
    var children = [
        Node(kAXHeadingRole, "Send to print"),
        Node(kAXGroupRole, "", children: [Node(kAXStaticTextRole, printer), Node(kAXImageRole, "chevron_down")]),
        Node(kAXGroupRole, "", children: cards ?? [mappingCard(slot)]),
        Node(kAXButtonRole, "confirm", children: [Node(kAXStaticTextRole, "Send")])
    ]
    children += radioNames.enumerated().map {
        Node(kAXGroupRole, "", children: [Node(kAXRadioButtonRole, $0.element)] +
            ([1, 2, 5].contains($0.offset) ? [Node(kAXImageRole, "radio")] : []))
    }
    return Node(kAXGroupRole, "", children: children)
}
func readReview(_ root: Node, _ printer: String = "Test P2S",
    sources: [String] = ["PLA"], slots: [AMSSlot] = detected) throws -> Review {
    try reviewSnapshot(root, printer, sources, slots)
}
func mustRefuse(_ body: () throws -> Void) {
    do { try body(); fatalError("Expected refusal") } catch {}
}
let parsed = try readReview(fixture(), "Test P2S")
assert(parsed.filament_mappings[0].ams_slot == "A2")
assert(parsed.filament_mappings[0].material == "PLA")
assert(parsed.timelapse == "Off")
assert(parsed.bed_leveling == "Auto")
assert(parsed.flow_calibration == "Auto")
mustRefuse { _ = try readReview(fixture(), "Other P2S") }
mustRefuse { _ = try readReview(fixture("?"), "Test P2S") }
let multi = fixture()
multi.children[2].children.append(mappingCard("B3"))
mustRefuse { _ = try readReview(multi, "Test P2S") }
let strayUnresolved = fixture(cards: [mappingCard("A2"), mappingCard("?", target: "?")])
mustRefuse { _ = try readReview(strayUnresolved) }
let unset = fixture()
unset.children.removeLast()
mustRefuse { _ = try readReview(unset, "Test P2S") }
let noIndicators = fixture()
for option in noIndicators.children where option.all.contains(where: { $0.role == kAXRadioButtonRole }) {
    option.children = option.children.filter { $0.role != kAXImageRole }
}
mustRefuse { _ = try readReview(noIndicators, "Test P2S") }
let doubleChecked = fixture()
doubleChecked.children[4].children.append(Node(kAXImageRole, "radio"))
mustRefuse { _ = try readReview(doubleChecked, "Test P2S") }
let ambiguous = fixture()
ambiguous.children.append(Node(kAXButtonRole, "confirm", children: [Node(kAXStaticTextRole, "Send")]))
mustRefuse { _ = try readReview(ambiguous, "Test P2S") }
let plateRoot = Node(kAXGroupRole, "", children: [
    Node(kAXPopUpButtonRole, "", children: [Node(kAXStaticTextRole, "cube.gcode.3mf")]),
    Node(kAXButtonRole, "", children: [Node(kAXStaticTextRole, "1")]),
    Node(kAXGroupRole, "", children: ["Compatible Printer:", "P2S", "Bed type:", "PEI",
        "Filaments:", "PLA", "Nozzle Diameter:", "0.4", "Time:", "9m", "Weight:", "0.15g"]
        .map { Node(kAXStaticTextRole, $0) })
])
let plateMetadata = try plateInfo(plateRoot, "cube.gcode.3mf")
assert(plateMetadata.info.contains("Nozzle Diameter: 0.4"))
mustRefuse { _ = try plateInfo(plateRoot, "different.gcode.3mf") }
let otherPrinter = fixture(printer: "Other P2S")
otherPrinter.children.append(Node(kAXGroupRole, "", children: [Node(kAXStaticTextRole, "Test P2S")]))
mustRefuse { _ = try readReview(otherPrinter, "Test P2S") }
plateRoot.children.append(Node(kAXPopUpButtonRole, "", children: [Node(kAXStaticTextRole, "other.gcode.3mf")]))
mustRefuse { _ = try plateInfo(plateRoot, "cube.gcode.3mf") }
plateRoot.children.removeLast()
plateRoot.children.append(Node(kAXGroupRole, "", children: ["Compatible Printer:", "Other",
    "Bed type:", "PEI", "Filaments:", "PETG", "Nozzle Diameter:", "0.6", "Time:", "1m", "Weight:", "1g"]
    .map { Node(kAXStaticTextRole, $0) }))
mustRefuse { _ = try plateInfo(plateRoot, "cube.gcode.3mf") }
let changed = fixture("A1")
let changedReview = try readReview(changed, "Test P2S")
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

// Multiple colors of the same material stay bound to their displayed row order.
let many = fixture(cards: [mappingCard("A2"), mappingCard("B3"), mappingCard("G4"),
    mappingCard("HT - A", source: "PETG", target: "PETG")])
let sources = ["PLA", "PLA", "PLA", "PETG"]
let allMappings = try readReview(many, sources: sources)
assert(allMappings.filament_mappings.map { $0.ams_slot } == ["A2", "B3", "G4", "HT - A"])
assert(allMappings.filament_mappings.map { $0.filament_index } == [1, 2, 3, 4])
assert(allMappings.detected_ams_slots == detected)
let swapped = fixture(cards: [mappingCard("B3"), mappingCard("A2"), mappingCard("G4"),
    mappingCard("HT - A", source: "PETG", target: "PETG")])
let swappedReview = try readReview(swapped, sources: sources)
assert(swappedReview != allMappings)
mustRefuse { _ = try readReview(many, sources: ["PLA"]) }
mustRefuse { _ = try readReview(many, sources: ["PETG", "PLA", "PLA", "PETG"]) }
mustRefuse { _ = try readReview(fixture("Z4")) }
mustRefuse { _ = try readReview(fixture("Ext")) }
mustRefuse { _ = try readReview(fixture(cards: [mappingCard("A2"), mappingCard("?", target: "?")]),
    sources: ["PLA", "PLA"]) }
mustRefuse { _ = try readReview(fixture(), slots: detected + [detected[0]]) }
mustRefuse { _ = try readReview(fixture(), slots: [AMSSlot(ams_slot: "A2", material: "Empty")]) }
let lite = try readReview(fixture("3"), slots: [AMSSlot(ams_slot: "3", material: "PLA")])
assert(lite.filament_mappings[0].ams_slot == "3")
let inventoryRoot = device("Test P2S", "Printing Progress old.gcode.3mf Finished 25 / 25")
inventoryRoot.children.append(Node(kAXGroupRole, "", children: detected.flatMap {
    [Node(kAXStaticTextRole, $0.ams_slot),
        Node(kAXGroupRole, "", children: [Node(kAXStaticTextRole, $0.material), Node(kAXImageRole, "")])]
}))
let inventory = try detectedSlots(inventoryRoot, "Test P2S")
assert(inventory == detected)
inventoryRoot.children.last!.children += [Node(kAXStaticTextRole, "3"),
    Node(kAXGroupRole, "", children: [Node(kAXStaticTextRole, "PLA"), Node(kAXImageRole, "")])]
let mixedInventory = try detectedSlots(inventoryRoot, "Test P2S")
assert(mixedInventory.map { $0.ams_slot } == ["3", "A1", "A2", "B3", "G4", "HT - A"])
inventoryRoot.children.last!.children.append(Node(kAXStaticTextRole, "C1"))
mustRefuse { _ = try detectedSlots(inventoryRoot, "Test P2S") }
let incompleteLite = device("Test P2S", live)
incompleteLite.children.append(Node(kAXGroupRole, "", children: [
    Node(kAXStaticTextRole, "1"),
    Node(kAXGroupRole, "", children: [Node(kAXStaticTextRole, "PLA")]),
    Node(kAXStaticTextRole, "4")
]))
mustRefuse { _ = try detectedSlots(incompleteLite, "Test P2S") }
let wrappedLite = device("Test P2S", live)
wrappedLite.children += [
    Node(kAXGroupRole, "", children: [Node(kAXStaticTextRole, "1"),
        Node(kAXGroupRole, "", children: [Node(kAXStaticTextRole, "PLA")])]),
    Node(kAXGroupRole, "", children: [Node(kAXStaticTextRole, "4")])
]
mustRefuse { _ = try detectedSlots(wrappedLite, "Test P2S") }
print("Multi-AMS review and inventory fixtures passed; no app accessed or action performed.")

// Exercise the production Send orchestration with only the external AX boundary replaced.
// These closures cannot access a real app or perform real UI actions.
let sendSlots = detected + [AMSSlot(ams_slot: "HT - B", material: "PETG")]
let approved = try readReview(many, sources: sources, slots: sendSlots)
let changedLast = fixture(cards: [mappingCard("A2"), mappingCard("B3"), mappingCard("G4"),
    mappingCard("HT - B", source: "PETG", target: "PETG")])
var sendAttempts = 0
var sendPresses = 0
func assertBlocked(_ expectedMessage: String, info: String = "unused", expires: Double? = nil) {
    do {
        _ = try submitReviewed("Test P2S", "cube.gcode.3mf", approved, info,
            expires ?? Date().timeIntervalSince1970 + 600) { sendAttempts += 1 }
        fatalError("Expected pre-Send rejection")
    } catch let error as UIError {
        assert(error.message == expectedMessage, error.message)
    } catch { fatalError("Unexpected error: \(error)") }
    assert(sendAttempts == 0 && sendPresses == 0)
}
fixtureWindow = { changedLast }
fixturePress = { node in
    if node.texts == ["Send"] { sendPresses += 1 }
    throw UIError(message: "Unexpected action before initial review comparison")
}
assertBlocked("Connect settings changed after approval.")
func reviewWithCancel() -> Node {
    let root = fixture(cards: [mappingCard("A2"), mappingCard("B3"), mappingCard("G4"),
        mappingCard("HT - A", source: "PETG", target: "PETG")])
    root.children.append(Node(kAXButtonRole, "Cancel"))
    return root
}
func deviceWithSlots(_ slots: [AMSSlot]) -> Node {
    let root = device("Test P2S", "Printing Progress old.gcode.3mf Finished 25 / 25")
    root.children.append(Node(kAXGroupRole, "", children: slots.flatMap {
        [Node(kAXStaticTextRole, $0.ams_slot),
            Node(kAXGroupRole, "", children: [Node(kAXStaticTextRole, $0.material), Node(kAXImageRole, "")])]
    }))
    root.children.append(Node(linkRole, "Print"))
    return root
}
let deviceList = Node(kAXGroupRole, "", children: [Node(linkRole, "Devices"),
    Node(linkRole, "Test P2S Bed: 25 Nozzle: 25 Idle")])
for newSlots in [sendSlots.map { $0.ams_slot == "A1" ? AMSSlot(ams_slot: "A1", material: "PETG") : $0 },
    sendSlots.filter { !$0.ams_slot.hasPrefix("B") }] {
    var current = reviewWithCancel()
    fixtureWindow = { current }
    fixturePress = { node in
        if node.label == "Cancel" { current = deviceList }
        else if node.label == "Devices" { current = deviceList }
        else if node.label.hasPrefix("Test P2S Bed:") { current = deviceWithSlots(newSlots) }
        else { fatalError("Unexpected action before inventory comparison") }
    }
    assertBlocked("Detected AMS slots or materials changed after approval.")
}
// Change only the final mapping after the last stable review, just before Send.
let finalPlate = Node(kAXGroupRole, "", children: [
    Node(kAXPopUpButtonRole, "", children: [Node(kAXStaticTextRole, "cube.gcode.3mf")]),
    Node(kAXButtonRole, "", children: [Node(kAXStaticTextRole, "1")]), Node(kAXButtonRole, "Print"),
    Node(kAXGroupRole, "", children: (["Compatible Printer:", "P2S", "Bed type:", "PEI", "Filaments:"] +
        sources + ["Nozzle Diameter:", "0.4", "Time:", "9m", "Weight:", "0.15g"])
        .map { Node(kAXStaticTextRole, $0) })
])
let approvedInfo = try plateInfo(finalPlate, "cube.gcode.3mf").info
var phase = "initial"
var reopenedReads = 0
var changeImmediatelyBeforeSend = true
fixtureWindow = {
    switch phase {
    case "initial": return reviewWithCancel()
    case "list": return deviceList
    case "device": return deviceWithSlots(sendSlots)
    case "plate": return finalPlate
    case "printing": return device("Test P2S", "Printing Progress cube.gcode.3mf 0 / 25")
    default:
        reopenedReads += 1
        return changeImmediatelyBeforeSend && reopenedReads > 3 ? changedLast : reviewWithCancel()
    }
}
fixturePress = { node in
    if node.texts == ["Send"] { sendPresses += 1; phase = "printing"; return }
    if node.label == "Cancel" || node.label == "Devices" { phase = "list" }
    else if node.label.hasPrefix("Test P2S Bed:") { phase = "device" }
    else if node.label == "Print", node.role == linkRole { phase = "plate" }
    else if node.label == "Print", node.role == kAXButtonRole { phase = "reopened" }
    else { fatalError("Unexpected fixture action") }
}
assertBlocked("Connect settings changed immediately before Send.", info: approvedInfo)
changeImmediatelyBeforeSend = false
phase = "initial"
reopenedReads = 0
assertBlocked("Review expired before Send.", info: approvedInfo, expires: 0)
phase = "initial"
reopenedReads = 0
let simulatedAccepted = try submitReviewed("Test P2S", "cube.gcode.3mf", approved, approvedInfo,
    Date().timeIntervalSince1970 + 600) { sendAttempts += 1 }
assert(simulatedAccepted["status"] as? String == "job_accepted")
assert(sendAttempts == 1 && sendPresses == 1)
fixtureWindow = nil
fixturePress = nil
print("Native pre-Send change/refusal fixtures passed; no app accessed or action performed.")
