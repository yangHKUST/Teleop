# UMI OpenArm UI design

Reference: `../awesome-design-md/design-md/linear.app/DESIGN.md` for layered panels,
8px button radii, 12px panels, restrained #5E6AD2 action accents and hairline borders.
Notion reference informs light surfaces, not marketing illustration.
Warp reference informs monospace diagnostic output, not headline typography.
Chinese fonts use installed Noto Sans CJK with system fallback; no proprietary brand fonts.

Leave the upper-left header blank. Top selectors are left/right/dual, output and theme.
Lock arm/output/viewer selection while a session or observed children are alive.
No sidebar or progress strip. Left: session-owned RViz, read-only to robot control.
Right: per-side statuses, launch options and output terminal. Bottom: six fixed controls.
Use text plus color for feedback. Never show unavailable feedback as zero.

The terminal is read-only, selects/copies text and accepts only a pending original
confirmation Enter or supported original runtime keys. No command entry.
Teach/developer content comes verbatim from existing PTY output; telemetry cards
read original JSON logs. Do not implement an alternative IK, mapping, rate controller
or safety policy. Default VIO windows off. Ctrl+C in terminal copies selection;
normal exit is the exit button or closing the UI.

First-frame RViz embedding is conditional on X11 and session ownership. An unavailable
render surface must not block teleoperation. Demonstration mode never starts hardware.

The model viewport now owns an isolated read-only RViz process. Static default pose
uses dedicated display-only TF topics, never the actual joint_states/control topics.
Live pose selection requires fresh complete seven-joint feedback per arm. Stale
feedback freezes the last measured pose and is visibly labeled. Hardware startup
failure does not remove the complete default model.
