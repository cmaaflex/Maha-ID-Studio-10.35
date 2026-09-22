# MAHA ID SOFTWARE 10.35

Separate development successor to the original 10.33 customer build. Original 10.33 backup must never be overwritten.
10.35 preserves the original six-panel home design and original portrait splash. Demo cards use supplied assets, marked as samples with no usable QR code.

Printing uses job-local Windows printer/paper/orientation, 90 x 57 mm card rectangles, independent DPI axes, calibrated output, and printable-area validation without automatic shrinking.
The review workspace retains the original layout. Photo confirmation is tracked against geometry.

The standalone Remover starts with no selected version and scans exact version-specific targets. Registry backup is mandatory before deletion, with optional Windows restore point. Scan modes expand only explicitly identified targets. Original ZIPs and personal documents are excluded. Legacy shared settings/shortcuts are preserved when ownership is ambiguous. Windows-wide historical-trace erasure is not promised.

Settings, installer ID, shortcut and install directory are isolated from 10.33.
Run `python -m unittest discover -s tests -v`, then `python tests/ui_gate.py`.
The Windows workflow builds portable, remover, setup and customer ZIP and checks startup before release.
Physical printer testing is still required with the user's printer/media for ruler verification.
