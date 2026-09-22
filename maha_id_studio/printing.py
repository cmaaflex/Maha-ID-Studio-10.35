"""Job-local Windows printer settings and physical card placement."""
from dataclasses import dataclass
import math

CARD_MM = (90.0, 57.0)
PX_PER_MM = 300 / 25.4


@dataclass(frozen=True)
class Paper:
    code: int
    name: str
    width_mm: float
    height_mm: float


@dataclass(frozen=True)
class Device:
    dpi_x: int
    dpi_y: int
    width: int
    height: int
    printable_width: int
    printable_height: int
    offset_x: int
    offset_y: int


def calibration_factors(measured_width, measured_height):
    values = (float(measured_width), float(measured_height))
    if any(not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('Enter positive measured dimensions in millimetres.')
    factors = tuple(target / value for target, value in zip(CARD_MM, values))
    if any(not .8 <= f <= 1.2 for f in factors):
        raise ValueError('Measurement differs by more than 20%. Check paper and driver scaling first.')
    return factors


def placement_plan(page, device, correction=(1.0, 1.0)):
    """Return source crops and GDI rectangles; never shrink to fit a page."""
    rects = page.info.get('card_rects')
    if not rects:
        raise ValueError('Card geometry is missing. Reopen the layout preview before printing.')
    cx, cy = correction
    if any(not math.isfinite(v) or not .8 <= v <= 1.2 for v in correction):
        raise ValueError('Invalid printer calibration. Reset calibration and retry.')
    if min(device.dpi_x, device.dpi_y, device.width, device.height,
           device.printable_width, device.printable_height) <= 0:
        raise ValueError('Printer reported invalid page dimensions.')
    # Preserve layout position on its own paper; center a smaller layout on larger paper.
    layout_w, layout_h = page.info['layout_mm']
    paper_w = device.width * 25.4 / device.dpi_x
    paper_h = device.height * 25.4 / device.dpi_y
    origin_x = (paper_w - layout_w) / 2
    origin_y = (paper_h - layout_h) / 2
    plan = []
    for rect in rects:
        x, y, right, bottom = rect
        if x < 0 or y < 0 or right > page.width or bottom > page.height or right <= x or bottom <= y:
            raise ValueError('A card extends outside the layout. Reset its position before printing.')
        left = round((origin_x + x / PX_PER_MM * cx) * device.dpi_x / 25.4) - device.offset_x
        top = round((origin_y + y / PX_PER_MM * cy) * device.dpi_y / 25.4) - device.offset_y
        width = round(90 * cx * device.dpi_x / 25.4)
        height = round(57 * cy * device.dpi_y / 25.4)
        target = (left, top, left + width, top + height)
        if left < 0 or top < 0 or target[2] > device.printable_width or target[3] > device.printable_height:
            raise ValueError('90 × 57 mm cards do not fit the selected paper/printable margins. '
                             'Choose a larger paper, change orientation or adjust the layout. Nothing was scaled or printed.')
        for _, previous in plan:
            # A one-dot rounding tolerance permits cards touching with zero gap.
            if min(target[2], previous[2]) - max(left, previous[0]) > 1 and min(target[3], previous[3]) - max(top, previous[1]) > 1:
                raise ValueError('Cards overlap after positioning/calibration. Increase the gap before printing.')
        plan.append((rect, target))
    return plan


def printer_capabilities(name):
    import win32print
    handle = win32print.OpenPrinter(name)
    try:
        info = win32print.GetPrinter(handle, 2)
        port = info['pPortName']
        codes = win32print.DeviceCapabilities(name, port, 2)
        names = win32print.DeviceCapabilities(name, port, 16)
        sizes = win32print.DeviceCapabilities(name, port, 3)
        papers = [Paper(code, label.strip(), (size['x'] if isinstance(size, dict) else size[0]) / 10,
                        (size['y'] if isinstance(size, dict) else size[1]) / 10)
                  for code, label, size in zip(codes, names, sizes)]
        if not papers:
            raise ValueError('This driver did not report paper sizes. Install the manufacturer Windows driver.')
        return papers, info['pDevMode']
    finally:
        win32print.ClosePrinter(handle)


def configured_device(name, paper, orientation):
    import win32con, win32print, win32ui, win32gui
    handle = win32print.OpenPrinter(name)
    try:
        info = win32print.GetPrinter(handle, 2)
        mode = info['pDevMode']
        mode.Fields &= ~(win32con.DM_PAPERLENGTH | win32con.DM_PAPERWIDTH)
        mode.Fields |= win32con.DM_PAPERSIZE | win32con.DM_ORIENTATION | win32con.DM_SCALE | win32con.DM_COPIES
        mode.PaperSize = paper.code
        mode.Orientation = 2 if orientation == 'Landscape' else 1
        mode.Scale = 100
        mode.Copies = 1
        result = win32print.DocumentProperties(0, handle, name, mode, mode, win32con.DM_IN_BUFFER | win32con.DM_OUT_BUFFER)
        if result < 0 or mode.PaperSize != paper.code or mode.Orientation != (2 if orientation == 'Landscape' else 1) or mode.Scale != 100:
            raise ValueError('Printer driver rejected the selected paper/orientation/100% scale. No output sent.')
        dc = win32ui.CreateDCFromHandle(win32gui.CreateDC('WINSPOOL', name, mode))
        device = Device(*(dc.GetDeviceCaps(getattr(win32con, key)) for key in
                          ('LOGPIXELSX', 'LOGPIXELSY', 'PHYSICALWIDTH', 'PHYSICALHEIGHT',
                           'HORZRES', 'VERTRES', 'PHYSICALOFFSETX', 'PHYSICALOFFSETY')))
        expected = (paper.height_mm, paper.width_mm) if orientation == 'Landscape' else (paper.width_mm, paper.height_mm)
        actual = (device.width * 25.4 / device.dpi_x, device.height * 25.4 / device.dpi_y)
        if any(abs(a - b) > 2 for a, b in zip(actual, expected)):
            dc.DeleteDC()
            raise ValueError('Printer returned a different physical paper size. Check its driver settings.')
        return dc, device, info.get('Status', 0)
    finally:
        win32print.ClosePrinter(handle)


def print_pages(pages, name, paper, orientation, correction=(1., 1.), validate_only=False):
    import win32print
    from PIL import ImageWin
    dc, device, status = configured_device(name, paper, orientation)
    started = False
    try:
        blocked = sum(getattr(win32print, k, 0) for k in
                      ('PRINTER_STATUS_OFFLINE', 'PRINTER_STATUS_ERROR', 'PRINTER_STATUS_PAUSED', 'PRINTER_STATUS_PAPER_OUT'))
        if status & blocked:
            raise ValueError('Printer is offline, paused, out of paper or reports an error.')
        if not pages:
            raise ValueError('Select a page or cards before printing.')
        plans = [placement_plan(page, device, correction) for page in pages]
        if validate_only:
            return device
        dc.StartDoc('SEEMA DIGITAL — 90 x 57 mm cards')
        started = True
        for page, plan in zip(pages, plans):
            dc.StartPage()
            for crop, target in plan:
                ImageWin.Dib(page.crop(crop).convert('RGB')).draw(dc.GetHandleOutput(), target)
            dc.EndPage()
        dc.EndDoc()
        started = False
        return device
    except Exception:
        if started:
            dc.AbortDoc()
        raise
    finally:
        dc.DeleteDC()


def print_dialog(app, parent, pages):
    from tkinter import Toplevel, Frame, Label, StringVar, Button, ttk, simpledialog, messagebox
    from .application import available_windows_printers, apply_cinematic_theme, _center_dialog, scroll_panel, open_windows_printer_properties
    dialog = Toplevel(parent)
    dialog.title('Print — exact 90 × 57 mm cards')
    dialog.transient(parent)
    dialog.grab_set()
    outer, body = scroll_panel(dialog, width=590)
    outer.pack(fill='both', expand=True)
    printer = StringVar()
    paper_name = StringVar()
    orientation = StringVar(value='Portrait')
    summary = StringVar(value='Loading installed printers…')
    state = {'papers': [], 'busy': False, 'correction': (1., 1.), 'generation': 0}
    controls = []
    for title, var in (('Printer', printer), ('Paper', paper_name), ('Orientation', orientation)):
        Label(body, text=title, anchor='w').pack(fill='x')
        control = ttk.Combobox(body, textvariable=var, state='readonly')
        control.pack(fill='x', pady=(2, 8))
        controls.append(control)
    controls[2].configure(values=('Portrait', 'Landscape'))
    Label(body, textvariable=summary, justify='left', anchor='w', wraplength=530).pack(fill='x', pady=8)
    send = Button(body, text='PRINT NOW — EXACT 90 × 57 mm', state='disabled')
    send.pack(fill='x', pady=8)
    Label(body,text='Selected paper par print hoga. Card ki final physical size 90 × 57 mm rahegi.',wraplength=530).pack(fill='x',pady=4)

    def profile_key():
        return '|'.join((printer.get(), paper_name.get(), orientation.get()))

    def update(*_):
        if not dialog.winfo_exists():
            return
        saved = app.read_settings().get('printer_calibration', {}).get(profile_key(), (1., 1.))
        try:
            factors=tuple(float(v) for v in saved)
            if len(factors)!=2 or any(not math.isfinite(v) or not .8<=v<=1.2 for v in factors):raise ValueError()
        except (ValueError,TypeError):factors=(1.,1.)
        state['correction'] = factors
        x, y = state['correction']
        layout = ' / '.join(sorted({p.info.get('layout_name', f'{p.info["layout_mm"][0]:g} × {p.info["layout_mm"][1]:g} mm') for p in pages}))
        summary.set(f'Printer: {printer.get() or "Choose printer"}\nPaper: {paper_name.get() or "Choose paper"}\n'
                    f'Orientation: {orientation.get()}\nLayout: {layout} • {len(pages)} page(s)\n'
                    f'Card output: 90 × 57 mm LOCKED\nScaling: Exact Physical Size • Fit/shrink: OFF\n'
                    f'Calibration X/Y: {x * 100:.2f}% / {y * 100:.2f}%\n'
                    'Is button se har card ka target physical size 90 × 57 mm rahega.')
        send.configure(state='normal' if paper_name.get() and not state['busy'] else 'disabled')

    def select_printer(*_):
        state['generation'] += 1
        generation = state['generation']
        name = printer.get()
        paper_name.set('')
        state['papers'] = []
        send.configure(state='disabled')
        summary.set('Reading printer paper sizes…')
        def ready(result, error):
            if not dialog.winfo_exists() or generation != state['generation']:
                return
            if error:
                summary.set(str(error))
                return
            papers, mode = result
            state['papers'] = papers
            controls[1].configure(values=[f'{p.name} — {p.width_mm:g} × {p.height_mm:g} mm' for p in papers])
            orientation.set('Landscape' if mode.Orientation == 2 else 'Portrait')
            update()
        app.run_background(lambda: printer_capabilities(name), ready)

    def calibrate(reset=False):
        if not paper_name.get():
            messagebox.showinfo('Select Paper', 'Choose a printer and paper first.', parent=dialog)
            return
        if reset:
            factors = (1., 1.)
        else:
            w = simpledialog.askfloat('Printer Calibration', 'Measure a card printed at uncalibrated 100% scale.\nActual width in mm (target 90):', parent=dialog, minvalue=1)
            if w is None: return
            h = simpledialog.askfloat('Printer Calibration', 'Actual height in mm (target 57):', parent=dialog, minvalue=1)
            if h is None: return
            try: factors = calibration_factors(w, h)
            except ValueError as exc:
                messagebox.showerror('Calibration', str(exc), parent=dialog)
                return
        settings = app.read_settings()
        settings.setdefault('printer_calibration', {})[profile_key()] = factors
        app.write_settings(settings)
        update()

    def submit():
        if state['busy'] or not paper_name.get(): return
        chosen = state['papers'][controls[1].current()]
        name, direction, factors = printer.get(), orientation.get(), state['correction']
        state['busy'] = True
        app.printing = True
        send.configure(state='disabled')
        for control in controls: control.configure(state='disabled')
        summary.set('Validating physical dimensions and printable margins…')
        def validated(device, error):
            if error:
                finished(None, error)
                return
            summary.set('Sending exact-size pages to the selected printer…')
            app.run_background(lambda: print_pages(pages, name, chosen, direction, factors), finished)
        def finished(result, error):
            state['busy'] = False
            app.printing = False
            for control in controls: control.configure(state='readonly')
            update()
            if error:
                messagebox.showwarning('Print Validation', str(error), parent=dialog)
            else:
                messagebox.showinfo('Print Sent', f'{len(pages)} page(s) sent to {name}.', parent=dialog)
                dialog.destroy()
        app.run_background(lambda: print_pages(pages, name, chosen, direction, factors, True), validated)

    send.configure(command=submit)
    Button(body, text='PRINTER DRIVER SETTINGS', command=lambda: open_windows_printer_properties(dialog, printer.get()) if printer.get() and not state['busy'] else None).pack(fill='x', pady=2)
    Button(body, text='CALIBRATE PRINTER', command=calibrate).pack(fill='x', pady=2)
    Button(body, text='RESET CALIBRATION — 100%', command=lambda: calibrate(True)).pack(fill='x', pady=2)
    def close():
        if not state['busy']: dialog.destroy()
    Button(body, text='CANCEL', command=close).pack(fill='x', pady=2)
    dialog.protocol('WM_DELETE_WINDOW', close)
    controls[0].bind('<<ComboboxSelected>>', select_printer)
    controls[1].bind('<<ComboboxSelected>>', update)
    controls[2].bind('<<ComboboxSelected>>', update)
    apply_cinematic_theme(dialog)
    _center_dialog(dialog, parent, 610, 650)
    def loaded(names, error):
        if not dialog.winfo_exists(): return
        if error: summary.set(str(error))
        else:
            controls[0].configure(values=names)
            summary.set('Choose a printer, paper and orientation.' if names else 'No Windows printers installed.')
    app.run_background(available_windows_printers, loaded)
