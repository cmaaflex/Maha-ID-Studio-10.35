SEEMA DIGITAL — MAHA ID SOFTWARE 10.33

BUILD STATUS
- Release: 10.33 (based on verified 10.32 source)
- Development release: 10.33
- Windows target: Windows 10/11 x64
- Owner/personal-use build: no activation key

WINDOWS BUILD
The repository includes .github/workflows/windows-onefile.yml.
On GitHub, Actions builds and verifies:
1. MAHA ID SOFTWARE 10.33.exe
2. MAHA ID SOFTWARE 10.33 Remover.exe
3. MAHA ID SOFTWARE 10.33 Setup.exe
4. Customer release files and SHA-256 checksums

10.33 DESIGN / OUTPUT CHANGES
- DPI-safe Home centering and safe margins.
- Premium balanced 3x2 Home layout.
- Card previews preserve 90:57 aspect ratio.
- Edit & Enhancement grouped below selected Photo Preview.
- Improved printed-photo boundary detection with review protection.
- A4 page geometry is exactly 210 x 297 mm.
- Each A4 card is exactly 90 x 57 mm.
- 10-card layout: 2 x 5, 10 mm left/right margins, 10 mm column gap, 1.5 mm vertical gaps, 3 mm top/bottom margins.
- Front and Back use the same physical-size PDF calculation.
- Existing 4x6, crop, enhancement, batch, save, print and navigation workflows are preserved.

TEST
Run: python -m unittest discover -s tests -v
The GitHub Windows build stops if tests fail.

PRINT
Use Actual Size / 100%. Do not use Fit to Page.
Epson L805: preserve the intended paper size and disable Reduce/Enlarge.
