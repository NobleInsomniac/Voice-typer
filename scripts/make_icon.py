"""Render the app icon (wave turning into 1s and 0s) and write it as an .icns file.

Usage: python make_icon.py OUTPUT.icns
"""
import os
import subprocess
import sys
import tempfile

from AppKit import (
    NSBezierPath,
    NSBitmapImageRep,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSGradient,
    NSGraphicsContext,
    NSPNGFileType,
)
from Foundation import NSMakeRect, NSString

SIZE = 1024


def draw(path: str) -> None:
    rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, SIZE, SIZE, 8, 4, True, False, "NSCalibratedRGBColorSpace", 0, 0
    )
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep))

    # macOS-style rounded square with a margin
    tile = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
        NSMakeRect(100, 100, 824, 824), 185, 185
    )
    NSGradient.alloc().initWithStartingColor_endingColor_(
        NSColor.colorWithCalibratedRed_green_blue_alpha_(0.16, 0.18, 0.24, 1),
        NSColor.colorWithCalibratedRed_green_blue_alpha_(0.04, 0.05, 0.08, 1),
    ).drawInBezierPath_angle_(tile, -90)

    # inner pill
    pill = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(NSMakeRect(190, 392, 644, 240), 120, 120)
    NSColor.colorWithCalibratedWhite_alpha_(1, 0.07).setFill()
    pill.fill()
    NSColor.colorWithCalibratedWhite_alpha_(1, 0.18).setStroke()
    pill.setLineWidth_(4)
    pill.stroke()

    cols, step, x0, mid = 9, 62, 512 - 62 * 4, 512
    heights = [0.35, 0.8, 1.0, 0.6]
    font = NSFont.monospacedSystemFontOfSize_weight_(104, 0.7)
    bits = "01101"
    for i in range(cols):
        x = x0 + step * i
        if i < 4:
            h = 40 + heights[i] * 130
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.35, 0.85, 1.0, 1).setFill()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(x - 11, mid - h / 2, 22, h), 11, 11
            ).fill()
        elif i == 4:
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.3, 1.0, 0.55, 0.9).setFill()
            NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(x - 11, mid - 11, 22, 22)).fill()
        else:
            alpha = 0.55 + 0.1 * (i - 5)
            col = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.3, 1.0, 0.55, alpha)
            text = NSString.stringWithString_(bits[i - 5])
            attrs = {NSFontAttributeName: font, NSForegroundColorAttributeName: col}
            sz = text.sizeWithAttributes_(attrs)
            text.drawAtPoint_withAttributes_((x - sz.width / 2, mid - sz.height / 2), attrs)

    NSGraphicsContext.restoreGraphicsState()
    rep.representationUsingType_properties_(NSPNGFileType, None).writeToFile_atomically_(path, True)


def main(out: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        master = os.path.join(tmp, "master.png")
        draw(master)
        iconset = os.path.join(tmp, "icon.iconset")
        os.mkdir(iconset)
        for base in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                px = base * scale
                name = f"icon_{base}x{base}" + ("@2x" if scale == 2 else "") + ".png"
                subprocess.run(
                    ["sips", "-z", str(px), str(px), master, "--out", os.path.join(iconset, name)],
                    check=True, capture_output=True,
                )
        subprocess.run(["iconutil", "-c", "icns", iconset, "-o", out], check=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv[1])
