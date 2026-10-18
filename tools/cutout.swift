// Person/subject cutout via macOS Vision (subject lifting), no network.
// Usage: swift tools/cutout.swift <dir-with-jpgs> <out-dir>
// Writes <name>.png (RGBA, same size, background transparent) for every .jpg.
import Foundation
import Vision
import CoreImage

let args = CommandLine.arguments
guard args.count == 3 else { print("usage: cutout.swift <in-dir> <out-dir>"); exit(1) }
let inDir = URL(fileURLWithPath: args[1]), outDir = URL(fileURLWithPath: args[2])
try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
let files = try FileManager.default.contentsOfDirectory(at: inDir, includingPropertiesForKeys: nil)
    .filter { $0.pathExtension.lowercased() == "jpg" }
    .sorted { $0.lastPathComponent < $1.lastPathComponent }
let ctx = CIContext()
let srgb = CGColorSpace(name: CGColorSpace.sRGB)!
var missed = 0
for f in files {
    let handler = VNImageRequestHandler(url: f)
    let req = VNGenerateForegroundInstanceMaskRequest()
    try handler.perform([req])
    let out = outDir.appendingPathComponent(f.deletingPathExtension().lastPathComponent + ".png")
    guard let obs = req.results?.first else { missed += 1; continue }
    let buf = try obs.generateMaskedImage(ofInstances: obs.allInstances, from: handler, croppedToInstancesExtent: false)
    try ctx.writePNGRepresentation(of: CIImage(cvPixelBuffer: buf), to: out, format: .RGBA8, colorSpace: srgb)
}
print("cutouts:", files.count - missed, "/", files.count, missed > 0 ? "(no subject in \(missed))" : "")
