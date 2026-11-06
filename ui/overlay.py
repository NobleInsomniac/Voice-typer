import math
import random
import time
from collections import deque

import objc
from AppKit import (
    NSAffineTransform,
    NSApplication,
    NSBackingStoreBuffered,
    NSBezierPath,
    NSColor,
    NSCompositingOperationClear,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSGraphicsContext,
    NSPanel,
    NSRectFillUsingOperation,
    NSScreen,
    NSStatusWindowLevel,
    NSView,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from Foundation import NSMakeRect, NSString, NSTimer
from PyObjCTools import AppHelper

PILL_W, PILL_H = 180, 40
MARGIN = 14  # room around the pill so the pop-up overshoot isn't clipped
COLS = 15  # columns of wave / digits
FPS = 30
PUSH_INTERVAL = 0.06  # seconds between new samples entering the wave
BAR_COLOR = (0.35, 0.85, 1.0)
BIT_COLOR = (0.3, 1.0, 0.55)
BALL_SIZE = 44
READY_SECONDS = 1.8  # how long the "ready" ball stays up

# spring used for the pop-up (slight overshoot) and the dismissal (no overshoot)
POP_STIFFNESS, POP_DAMPING = 170.0, 19.0
HIDE_STIFFNESS, HIDE_DAMPING = 190.0, 27.0


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _draw_ball(view, color):
    """Black ball with a green tick that draws itself on."""
    cx, cy = PILL_W / 2, PILL_H / 2
    r = BALL_SIZE / 2
    ball = NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(cx - r, cy - r, BALL_SIZE, BALL_SIZE))
    color(0.08, 0.08, 0.08, 0.92).setFill()
    ball.fill()
    color(1.0, 1.0, 1.0, 0.14).setStroke()
    ball.setLineWidth_(1.0)
    ball.stroke()

    pts = [(cx - 9, cy), (cx - 3, cy - 6.5), (cx + 9.5, cy + 8)]
    lens = [math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2])]
    left = _clamp(view.tick_p) * sum(lens)
    tick = NSBezierPath.bezierPath()
    tick.moveToPoint_(pts[0])
    for i in range(2):
        seg = min(left, lens[i])
        if seg <= 0:
            break
        f = seg / lens[i]
        tick.lineToPoint_((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f,
                           pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f))
        left -= seg
    r_, g_, b_ = BIT_COLOR
    color(r_, g_, b_, 1.0).setStroke()
    tick.setLineWidth_(3.5)
    tick.setLineCapStyle_(1)  # round
    tick.setLineJoinStyle_(1)
    tick.stroke()


class _PillView(NSView):
    """Pill: sound wave on the left that turns into 1s and 0s on the right.

    While processing, the whole pill becomes a flickering bit stream with a
    highlight sweeping across it.
    """

    def initWithFrame_(self, frame):
        self = objc.super(_PillView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.level_fn = lambda: 0.0
        self.font = NSFont.monospacedSystemFontOfSize_weight_(12, 0.6)
        self.appear = 0.0  # spring position: 0 hidden .. 1 fully shown
        self.velocity = 0.0
        self.target = 0.0
        self.reset()
        return self

    def reset(self):
        # index 0 is the newest sample (left); it drifts right and ages into a bit
        self.samples = deque([[0.0, 0] for _ in range(COLS)], maxlen=COLS)
        self.elapsed = 0.0
        self.processing = False
        self.proc = 0.0  # 0 = recording look .. 1 = processing look
        self.phase = 0.0
        self.ball = False  # True = "ready" ball instead of the pill
        self.tick_p = 0.0  # how much of the tick has been drawn
        self.hide_at = None

    def finished_hiding(self):
        return self.target == 0.0 and self.appear <= 0.03

    def tick(self):
        dt = 1.0 / FPS
        k, c = (POP_STIFFNESS, POP_DAMPING) if self.target else (HIDE_STIFFNESS, HIDE_DAMPING)
        self.velocity += (k * (self.target - self.appear) - c * self.velocity) * dt
        self.appear += self.velocity * dt

        if self.ball:
            if self.appear > 0.7:
                self.tick_p = min(1.0, self.tick_p + 0.09)
            if self.hide_at is not None and time.monotonic() >= self.hide_at:
                self.target, self.hide_at = 0.0, None
        elif self.processing:
            self.proc = min(1.0, self.proc + 0.12)
            self.phase += 0.35
            for s in self.samples:
                if random.random() < 0.07:
                    s[1] ^= 1
        else:
            self.elapsed += dt
            if self.elapsed >= PUSH_INTERVAL:
                self.elapsed = 0.0
                level = _clamp(self.level_fn()) * random.uniform(0.75, 1.0)
                self.samples.appendleft([level, random.getrandbits(1)])
        self.setNeedsDisplay_(True)

    def isOpaque(self):
        return False

    def drawRect_(self, rect):
        b = self.bounds()
        NSRectFillUsingOperation(b, NSCompositingOperationClear)
        scale = 0.85 + 0.15 * max(self.appear, 0.0)  # grows from 85%, never from a point
        alpha = _clamp(self.appear)
        rise = (1.0 - _clamp(self.appear)) * -10  # drifts up into place / sinks on exit
        if alpha <= 0.0:
            return

        def color(r, g, bl, a):
            return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, bl, a * alpha)

        NSGraphicsContext.saveGraphicsState()
        t = NSAffineTransform.transform()
        t.translateXBy_yBy_(b.size.width / 2, b.size.height / 2 + rise)
        t.scaleBy_(scale)
        t.translateXBy_yBy_(-PILL_W / 2, -PILL_H / 2)
        t.concat()

        if self.ball:
            _draw_ball(self, color)
            NSGraphicsContext.restoreGraphicsState()
            return

        w, h = PILL_W, PILL_H
        pill = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSMakeRect(0.5, 0.5, w - 1, h - 1), h / 2, h / 2
        )
        color(0.08, 0.08, 0.08, 0.92).setFill()
        pill.fill()
        color(1.0, 1.0, 1.0, 0.14).setStroke()
        pill.setLineWidth_(1.0)
        pill.stroke()

        pad = h / 2
        step = (w - 2 * pad) / COLS
        mid = h / 2
        for i, (level, bit) in enumerate(self.samples):
            x = pad + step * (i + 0.5)
            wave_f = _clamp((i - COLS * 0.35) / (COLS * 0.25))  # 0 = wave, 1 = digit
            f = max(wave_f, self.proc)

            if f < 0.98:
                bar_h = 4 + level * (h - 16)
                r, g, bl = BAR_COLOR
                color(r, g, bl, 1 - f).setFill()
                NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                    NSMakeRect(x - 1.5, mid - bar_h / 2, 3, bar_h), 1.5, 1.5
                ).fill()

            if f > 0.02:
                sweep = 0.5 + 0.5 * math.sin(self.phase - i * 0.6)
                bright = (1 - self.proc) * level + self.proc * sweep
                r, g, bl = BIT_COLOR
                col = color(r, g, bl, f * (0.35 + 0.65 * bright))
                text = NSString.stringWithString_(str(bit))
                attrs = {NSFontAttributeName: self.font, NSForegroundColorAttributeName: col}
                size = text.sizeWithAttributes_(attrs)
                text.drawAtPoint_withAttributes_((x - size.width / 2, mid - size.height / 2), attrs)

        NSGraphicsContext.restoreGraphicsState()


class Overlay:
    """Small always-on-top indicator that never takes keyboard focus.

    show() -> recording look, processing() -> bit-stream look, hide() -> dismiss.
    All three are safe to call from any thread.
    """

    def __init__(self, level_fn):
        NSApplication.sharedApplication()

        win_w, win_h = PILL_W + 2 * MARGIN, PILL_H + 2 * MARGIN
        screen = NSScreen.mainScreen().visibleFrame()
        x = screen.origin.x + (screen.size.width - win_w) / 2
        y = screen.origin.y + 24 - MARGIN
        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, win_w, win_h),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        self.panel.setOpaque_(False)
        self.panel.setBackgroundColor_(NSColor.clearColor())
        self.panel.setHasShadow_(False)  # a window shadow wouldn't follow the pop animation
        self.panel.setLevel_(NSStatusWindowLevel)
        self.panel.setFloatingPanel_(True)
        self.panel.setHidesOnDeactivate_(False)
        self.panel.setIgnoresMouseEvents_(True)
        self.panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary
            | NSWindowCollectionBehaviorStationary
        )

        self.view = _PillView.alloc().initWithFrame_(NSMakeRect(0, 0, win_w, win_h))
        self.view.level_fn = level_fn
        self.panel.setContentView_(self.view)
        self._timer = None

    def show(self):
        AppHelper.callAfter(self._show)

    def processing(self):
        AppHelper.callAfter(self._processing)

    def ready(self):
        """Brief black ball with a green tick: the model is loaded."""
        AppHelper.callAfter(self._ready)

    def hide(self):
        AppHelper.callAfter(self._hide)

    def _ensure_timer(self):
        if self._timer is None:
            self._timer = NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
                1.0 / FPS, True, lambda _t: self._on_tick()
            )

    def _on_tick(self):
        self.view.tick()
        if self.view.finished_hiding():
            self._timer.invalidate()
            self._timer = None
            self.panel.orderOut_(None)

    def _show(self):
        if self.view.appear <= 0.05:  # not already on screen: start from a clean slate
            self.view.reset()
        self.view.ball = False
        self.view.hide_at = None
        self.view.processing = False
        self.view.proc = 0.0
        self.view.target = 1.0
        self.panel.orderFrontRegardless()
        self._ensure_timer()

    def _ready(self):
        if self.view.appear > 0.05:  # something is already showing; don't interrupt it
            return
        self.view.reset()
        self.view.ball = True
        self.view.hide_at = time.monotonic() + READY_SECONDS
        self.view.target = 1.0
        self.panel.orderFrontRegardless()
        self._ensure_timer()

    def _processing(self):
        self.view.processing = True

    def _hide(self):
        self.view.target = 0.0
        self._ensure_timer()
