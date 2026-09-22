# MAHA ID SOFTWARE 10.33

- Added the premium reference-based Home screen with the six approved English/Hinglish layout names.
- Added isolated, geometry-stable hover animation and red/cyan layout selection outlines.
- Replaced the unsupported printer-properties call with native Windows/manufacturer preferences and guarded print confirmation.
- Added bounded background loading, lazy preview work, cancellation, caching and centered red/cyan processing feedback.
- Hardened A4 card and portrait detection, review blocking, manual correction and batch photo-box tools.
- Added responsive output/review dialogs, atomic multi-format saving and the verified safe remover workflow.

# Maha ID Studio 10.31 (historical)

- Added a responsive Save Final Output dialog with filename, folder, format and 600/1200-DPI selection.
- Replaced the clipped Photo Review warning with a scrollable card list and fixed action footer.
- Preserved splash artwork aspect ratio while filling the screen; no blur, duplicate layer or letterbox.
- Hardened card-boundary scoring against contours that cross into the next A4 row.
- Excluded low-confidence photos from the explicit Continue With Valid Cards workflow.
- Made raster exports atomic and verified before replacing the destination file.
- Added always-visible Apply Changes & Exit controls and safe Apply To All Photos enhancement copying without overwriting individual crop boxes.
- Added Apply Bounding Box To All Selected using normalized Front-relative coordinates for mixed source resolutions.
- Added layout-matched thumbnail preview, saved Photo Box presets and one-step batch bounding-box Undo.
- Synchronized application, remover, installer, EXE metadata and workflow release tag at 10.31.

# Maha ID Studio 10.30

- Rebuilt the responsive Home tiles with final English and Hinglish labels.
- Removed startup Home/white flash and shortened splash to real loading states.
- Cached the cinematic background and reduced full-resolution preview copies.
- Unified batch import with refined Front/Back border detection.
- Moved batch photo detection off the UI thread and added review-before-output blocking.
- Corrected A4 Front-only raster export so it never creates Back pages.
- Added a responsive safe Remover with restore-point option, restart cleanup and reports.
- Deep Clean is report-only; personal JPG/PDF/output is never auto-selected.

# Maha ID Studio 10.23

- Added 4 CARD A4: four locked front+back pairs per A4, each side exactly
  90 × 57 mm, with independent horizontal and vertical spacing controls.
- Added A4 page-group headings and P1-01/P2-01 indicators in the card list.
- Added A4 layout Undo/Redo, Auto Fit, pair locking and safe overflow limits.
- Added short Hinglish help under main actions and automatic problem/solution
  messages for file, print and save failures.
- Added Windows per-monitor DPI awareness for 125%, 150% and 200% displays.
- Unified Home, Crop, Batch/A4 Review and Printer Profile under one reusable
  midnight-blue, electric-cyan and red cinematic theme.
- Replaced the mixed orange/purple/green control palette with consistent
  action colours, high-contrast text, neon selection states and dark panels.
- Updated the splash to the approved identity-preserving 4K artwork.
- Removed the composite/feather splash path: one artwork now fills the window
  edge-to-edge without inset frames or blurred side bands.
- Kept the rounded animated cyan loading component as a separate non-blocking
  overlay.
- Synchronized application, Windows EXE, installer and release metadata at
  version 10.23.

# Maha ID Studio 10.15

- Added a branded Windows Setup wizard with SEEMA DIGITAL artwork.
- Added Desktop and Start Menu shortcuts, clean uninstall metadata and icon.
- Added a clean professional customer ZIP with portable EXE, Setup EXE,
  instructions, exact print settings, logo, splash and SHA-256 checksums.
- Preserved all crop, enhancement, preview, A4/4x6 and batch-print features.

# Maha ID Print Studio 10.14

- Replaced the generated person-containing edge fill with a verified studio-only background, eliminating the duplicate hand/body artifact.
- Upgraded the progress bar to four-layer neon rendering: outer aura, electric track, cyan core and animated white shimmer.
- Applied the SD icon as the default icon to root, splash, crop, review and print-position windows.
- Added a Windows one-file build with embedded assets, version metadata, icon and GUI subsystem; release output contains only `Maha ID Studio.exe`.

## 10.13

- Opening artwork remains centred while a dedicated cinematic PC/printer studio background fills every monitor edge.
- Rebuilt loading as a compact rounded glass panel with cyan neon glow, smooth animation, moving highlight, percentage and status text.
- Progress placement now uses the real maximized client area, so it stays above the Windows taskbar and never gets clipped.
- Main-window transitions hide the previous workspace before opening the next and restore it maximized only after the child closes.
- Splash foreground edges are feathered into the extended studio scene to avoid solid strips and hard seams.

## 10.12

- Added automatic portrait-boundary refinement for the green Photo box.
- Enlarged Front, Back and Photo previews in both crop and batch/A4 review.
- Added cached smart previews and debounced redraw for smoother performance.
- Added a silent VBS/PYW launcher so normal startup does not open CMD.
- Changed workflow navigation so only one main work window is visible at a time.

## 10.11
- Converted the working desktop app into a maintainable Python package.
- Added stable production and backward-compatible launchers.
- Added automated exact-size PDF and feature-regression tests.
- Added a test-gated standalone Windows EXE build.
- Added Start Menu installation and an optional Inno Setup project.
- Preserved crop, enhancement, preview, print, PDF, A4 positioning, printer profile and splash functionality.
- Bundled the large multi-resolution SEEMA DIGITAL SD icon.

## 10.33 - Responsive UI + Exact A4 Geometry
- Home artwork now uses an aspect-ratio-safe centered contain layout over a full-screen background, preventing header/tile clipping at Windows DPI scaling.
- Premium 3x2 Home remains fixed under hover; cyan hover outline does not reflow neighboring tiles.
- A4 Front/Back 10-card default grid changed to exact physical target: 10 mm side margins, 10 mm horizontal gap, 3 mm top/bottom margins, 1.5 mm vertical gap.
- PDF A4 pages are authored at exactly 210 x 297 mm in PDF points instead of deriving page geometry from raster DPI.
- 4x6 PDF pages are authored at exactly 4 x 6 inches.
- Existing low-confidence photo detection review gate and manual re-detection workflow retained.
- 10.33 remains the untouched release baseline; this source is the 10.33 development successor.
