// Person masks via macOS Vision (subject lifting), no network.
// Usage: swift tools/masks.swift <dir-with-jpgs> <out-dir>
// Writes <name>.png (white, alpha = person, same size as the frame) for every .jpg and
// meta.json: per frame [top, cx, width] of the subject's top band (head position for orbit text), or null.
import Foundation
import Vision
import CoreImage

let args = CommandLine.arguments
guard args.count == 3 else { print("usage: masks.swift <in-dir> <out-dir>"); exit(1) }
let inDir = URL(fileURLWithPath: args[1]), outDir = URL(fileURLWithPath: args[2])
try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
let files = try FileManager.default.contentsOfDirectory(at: inDir, includingPropertiesForKeys: nil)
    .filter { $0.pathExtension.lowercased() == "jpg" && !$0.lastPathComponent.hasPrefix("_") }
    .sorted { $0.lastPathComponent < $1.lastPathComponent }
let ctx = CIContext()
let srgb = CGColorSpace(name: CGColorSpace.sRGB)!
var meta: [Any] = []
var missed = 0
for f in files {
    let handler = VNImageRequestHandler(url: f)
    let req = VNGenerateForegroundInstanceMaskRequest()
    try handler.perform([req])
    let out = outDir.appendingPathComponent(f.deletingPathExtension().lastPathComponent + ".png")
    guard let obs = req.results?.first else {
        missed += 1; meta.append(NSNull())
        let img = CIImage(color: .clear).cropped(to: CGRect(x: 0, y: 0, width: 1080, height: 1920))
        try ctx.writePNGRepresentation(of: img, to: out, format: .RGBA8, colorSpace: srgb)
        continue
    }
    let buf = try obs.generateScaledMaskForImage(forInstances: obs.allInstances, from: handler)
    // head band: first row (from the top) with subject pixels, then the subject's extent in the next 160 rows
    CVPixelBufferLockBaseAddress(buf, .readOnly)
    let w = CVPixelBufferGetWidth(buf), h = CVPixelBufferGetHeight(buf), row = CVPixelBufferGetBytesPerRow(buf)
    let base = CVPixelBufferGetBaseAddress(buf)!.assumingMemoryBound(to: UInt8.self)
    func v(_ x: Int, _ y: Int) -> Float { base.advanced(by: y * row + x * 4).withMemoryRebound(to: Float32.self, capacity: 1) { $0.pointee } }
    var top = -1
    for y in stride(from: 0, to: h, by: 4) {
        var hits = 0
        for x in stride(from: 0, to: w, by: 6) where v(x, y) > 0.5 { hits += 1 }
        if hits >= 3 { top = y; break }
    }
    if top >= 0 {
        var lo = w, hi = 0
        for y in stride(from: top, to: min(h, top + 160), by: 4) {
            for x in stride(from: 0, to: w, by: 3) where v(x, y) > 0.5 { lo = min(lo, x); hi = max(hi, x) }
        }
        meta.append([top, (lo + hi) / 2, hi - lo])
    } else { meta.append(NSNull()) }
    CVPixelBufferUnlockBaseAddress(buf, .readOnly)
    let alpha = CIImage(cvPixelBuffer: buf).applyingFilter("CIMaskToAlpha")
    try ctx.writePNGRepresentation(of: alpha, to: out, format: .RGBA8, colorSpace: srgb)
}
try JSONSerialization.data(withJSONObject: meta).write(to: outDir.appendingPathComponent("meta.json"))
print("masks:", files.count - missed, "/", files.count, missed > 0 ? "(no subject in \(missed))" : "")
