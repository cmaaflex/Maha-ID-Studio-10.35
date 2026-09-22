"""SEEMA DIGITAL — Fast Maha ID / MahaSarathi Card Print."""
from __future__ import annotations
import re
import json
import math
import io
import shutil
from pathlib import Path
import sys
import os
import tempfile
import threading
import subprocess
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import base64
import zipfile
from html.parser import HTMLParser
from urllib.parse import unquote
from tkinter import BooleanVar, Button, Canvas, Checkbutton, DoubleVar, Entry, Frame, IntVar, Label, Listbox, Scale, Scrollbar, StringVar, Tk, Toplevel, filedialog, messagebox, simpledialog, ttk
import pymupdf
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps, ImageStat, ImageTk

PACKAGE_DIR = Path(__file__).resolve().parent
APP_DIR = PACKAGE_DIR.parent
ASSET_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR)) / "assets"
OUTPUT_DIR = APP_DIR / "Seema Digital Print Output"
SHEET_SIZE, A4_SIZE, CARD_SIZE = (1200, 1800), (2480, 3508), (1063, 673)
TOP, BOTTOM, WHITE = (69, 35), (69, 708), (255, 255, 255)
PX_PER_MM = 300 / 25.4
EXPORT_DPI = 600
IMPORT_EXTENSIONS = {".pdf",".jpg",".jpeg",".png",".tif",".tiff",".psd",".webp",".bmp",".gif",".avif",".svg",".docx",".xlsx",".pptx",".zip",".html",".htm",".txt",".csv"}
SUPPORTED = [("Universal Maha ID Files", "*.pdf *.jpg *.jpeg *.png *.tif *.tiff *.psd *.webp *.bmp *.gif *.avif *.svg *.docx *.xlsx *.pptx *.zip *.html *.htm *.txt *.csv"), ("PDF Files", "*.pdf"), ("Image Files", "*.jpg *.jpeg *.png *.tif *.tiff *.psd *.webp *.bmp *.gif *.avif *.svg"), ("Office / Archive", "*.docx *.xlsx *.pptx *.zip"), ("All Files", "*.*")]
ADJUSTMENTS = ("Brightness", "Contrast", "Hue", "Saturation", "Exposure", "Shadows", "Highlights", "Sharpness", "Temperature")
APP_VERSION = "10.35"
PRODUCT_NAME = "MAHA ID SOFTWARE"

# One visual system for every workspace and dialog.  These colours are sampled
# from the approved opening artwork: midnight studio blue, electric cyan and
# controlled red highlights.
THEME = {
    "bg": "#020916", "surface": "#071426", "panel": "#0b1d36",
    "panel_alt": "#102744", "canvas": "#050b14", "text": "#f4f8ff",
    "muted": "#9fb6d5", "blue": "#078cff", "cyan": "#21d8ff",
    "red": "#ef2438", "red_dark": "#a70f26", "blue_dark": "#0753a8",
    "green": "#20d68b", "border": "#155eaa", "disabled": "#34445a",
}

def _button_colours(text):
    """Return a predictable action colour instead of per-window random colours."""
    value=(text or "").upper()
    if value in ("SINGLE 4×6","MULTIPLE 4×6","4 CARD A4","A4 ME 5 CARD","A4 FRONT — 10","A4 BACK — 10"):return THEME["red"],THEME["red_dark"]
    if "PRINT" in value:return THEME["red"],THEME["red_dark"]
    if any(word in value for word in ("SAVE","APPLY","LIVE")):return THEME["blue"],THEME["blue_dark"]
    if any(word in value for word in ("EDIT","CROP")):return THEME["red"],THEME["red_dark"]
    if any(word in value for word in ("AUTO","MOVE","POSITION","ROTATE")):return THEME["blue_dark"],THEME["blue"]
    return THEME["panel_alt"],THEME["blue_dark"]

def apply_cinematic_theme(window):
    """Apply the opening-screen palette recursively without removing controls."""
    try:window.configure(bg=THEME["bg"])
    except Exception:pass
    def walk(widget):
        for child in widget.winfo_children():
            name=child.winfo_class()
            try:
                if name in ("Frame","Labelframe"):
                    old=str(child.cget("bg")).lower()
                    colour=THEME["panel"] if old in ("white","#ffffff","#f5f6fa","systembuttonface") or str(child.cget("relief"))!="flat" else THEME["bg"]
                    child.configure(bg=colour,highlightbackground=THEME["border"],highlightcolor=THEME["cyan"])
                elif name=="Label":
                    text=str(child.cget("text")).upper()
                    master_bg=child.master.cget("bg")
                    fg=THEME["red"] if text=="SEEMA DIGITAL" else THEME["cyan"] if any(k in text for k in ("PREVIEW","MAHA ID FAST","MULTIPLE","ACTIVE AREA","PRINTER PROFILE")) else THEME["text"]
                    if text in ("FRONT","BACK","PHOTO"):fg={"FRONT":THEME["red"],"BACK":THEME["cyan"],"PHOTO":THEME["green"]}[text]
                    child.configure(bg=master_bg,fg=fg)
                elif name=="Button":
                    bg,active=_button_colours(child.cget("text"))
                    size=getattr(child,"_cinematic_size",11)
                    child.configure(bg=bg,fg=THEME["text"],activebackground=active,activeforeground="white",relief="flat",bd=0,highlightthickness=0,cursor="hand2",font=("Segoe UI",size),padx=8,pady=5)
                    child._cinematic_bg=bg
                    child.bind("<Configure>",lambda e,w=child:w.configure(wraplength=max(80,e.width-20)))
                    if not hasattr(child,"_cinematic_selected"):child._cinematic_selected=False
                    if not hasattr(child,"_cinematic_persistent"):child._cinematic_persistent=False
                    child.bind("<Button-1>",lambda e,w=child,root=window:select_cinematic_button(root,w),add="+")
                    child.bind("<Enter>",lambda e,w=child,a=active:w.configure(bg=THEME["red_dark"] if getattr(w,"_cinematic_selected",False) else a,highlightbackground=THEME["cyan"]),add="+")
                    child.bind("<Leave>",lambda e,w=child,b=bg:w.configure(bg=THEME["red"] if getattr(w,"_cinematic_selected",False) else b,highlightbackground=THEME["cyan"] if getattr(w,"_cinematic_selected",False) else THEME["blue"]),add="+")
                elif name=="Canvas":
                    old=str(child.cget("bg")).lower();child.configure(bg=THEME["panel"] if old in ("#f5f6fa","white","#ffffff") else THEME["canvas"],highlightbackground=THEME["border"])
                elif name=="Listbox":
                    child.configure(bg=THEME["surface"],fg=THEME["text"],selectbackground=THEME["red"],selectforeground="white",highlightbackground=THEME["border"],highlightcolor=THEME["cyan"],bd=1)
                elif name=="Entry":
                    child.configure(bg=THEME["surface"],fg=THEME["text"],insertbackground=THEME["cyan"],highlightbackground=THEME["border"],highlightcolor=THEME["cyan"])
                elif name=="Checkbutton":
                    child.configure(bg=child.master.cget("bg"),fg=THEME["text"],activebackground=child.master.cget("bg"),activeforeground=THEME["cyan"],selectcolor=THEME["surface"])
                elif name=="Scale":
                    child.configure(bg=child.master.cget("bg"),fg=THEME["text"],troughcolor=THEME["blue_dark"],activebackground=THEME["red"],highlightthickness=1,highlightbackground=THEME["cyan"],sliderrelief="raised",relief="groove",bd=2,width=16,sliderlength=24)
            except Exception:pass
            walk(child)
    walk(window)

def select_cinematic_button(window,selected):
    """Select only true modes/toggles; ordinary action clicks never reflow UI."""
    if not getattr(selected,"_cinematic_persistent",False):return
    def walk(widget):
        for child in widget.winfo_children():
            if child.winfo_class()=="Button":
                child._cinematic_selected=child is selected
                try:child.configure(bg=THEME["red"] if child is selected else getattr(child,"_cinematic_bg",THEME["panel_alt"]),highlightbackground=THEME["cyan"] if child is selected else THEME["blue"])
                except Exception:pass
            walk(child)
    walk(window)

def available_windows_printers():
    """Return installed local/network printer names without changing Windows defaults."""
    if not sys.platform.startswith("win"):return []
    import win32print
    flags=win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    return sorted({row[2] for row in win32print.EnumPrinters(flags) if len(row)>2 and row[2]},key=str.casefold)

def open_windows_printer_properties(parent,printer):
    """Open the selected printer's original Windows page/paper preferences."""
    if not printer:return False
    try:
        import win32con,win32print
        handle=win32print.OpenPrinter(printer)
        try:
            current=win32print.GetPrinter(handle,2).get("pDevMode")
            if current is not None and hasattr(win32print,"DocumentProperties"):
                result=win32print.DocumentProperties(parent.winfo_id(),handle,printer,current,current,win32con.DM_IN_BUFFER|win32con.DM_OUT_BUFFER|win32con.DM_IN_PROMPT)
                return result==getattr(win32con,"IDOK",1)
        finally:win32print.ClosePrinter(handle)
        completed=subprocess.run(["rundll32.exe","printui.dll,PrintUIEntry","/e","/n",printer],check=False,timeout=300,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if completed.returncode not in (0,None):raise RuntimeError(f"Printer preferences return code: {completed.returncode}")
        return completed.returncode==0
    except Exception as exc:
        friendly_problem(parent,"Printer Settings Error",str(exc),"Windows Settings se printer preferences kholkar paper size/orientation set karein.")
        return False


def final_print_preview(parent,pages,paper):
    """Show the exact final pages before any printer job can be sent."""
    if not pages:return False
    dialog=Toplevel(parent);dialog.title("Final Print Preview — SEEMA DIGITAL");dialog.transient(parent);dialog.grab_set();dialog.geometry("980x760");apply_window_icon(dialog)
    answer={"ok":False};index=IntVar(value=0);photo={"value":None}
    Label(dialog,text="FINAL PRINT PREVIEW",font=("Segoe UI",22,"bold"),fg=THEME["red"],bg=THEME["bg"]).pack(fill="x",pady=(12,2))
    info=StringVar();Label(dialog,textvariable=info,font=("Segoe UI",11,"bold"),fg=THEME["cyan"],bg=THEME["bg"]).pack(fill="x")
    guide_tip(dialog,"Tip: Har Page Check Karke Continue To Printer Settings Dabayein")
    image_label=Label(dialog,bg=THEME["canvas"],bd=2,relief="groove");image_label.pack(fill="both",expand=True,padx=18,pady=10)
    def show(delta=0):
        index.set(max(0,min(len(pages)-1,index.get()+delta)));img=pages[index.get()].copy();img.thumbnail((780,570),Image.Resampling.LANCZOS);photo["value"]=ImageTk.PhotoImage(img);image_label.configure(image=photo["value"]);info.set(f"Paper: {paper}  •  Page {index.get()+1} Of {len(pages)}  •  Card: 90×57 mm")
    nav=Frame(dialog,bg=THEME["panel"]);nav.pack(fill="x",padx=18)
    Button(nav,text="◀ Previous Page",command=lambda:show(-1)).pack(side="left",fill="x",expand=True,padx=4)
    Button(nav,text="Next Page ▶",command=lambda:show(1)).pack(side="left",fill="x",expand=True,padx=4)
    def approve():answer["ok"]=True;dialog.destroy()
    Button(nav,text="Continue To Printer Settings",command=approve).pack(side="left",fill="x",expand=True,padx=4)
    Button(nav,text="Cancel Print",command=dialog.destroy).pack(side="left",fill="x",expand=True,padx=4)
    dialog.protocol("WM_DELETE_WINDOW",dialog.destroy);apply_cinematic_theme(dialog);show();parent.wait_window(dialog);return answer["ok"]

def windows_print_images(images,job_name="SEEMA DIGITAL — Maha ID",printer=None,paper=None,orientation="Portrait",correction=(1.,1.)):
    from .printing import print_pages
    if not printer or paper is None:raise ValueError("Choose printer and paper in the Print window.")
    print_pages(images,printer,paper,orientation,correction)
    return printer

def unique_output_path(folder,name,used=None):
    """Never silently overwrite an earlier/customer output with the same name."""
    folder=Path(folder);candidate=folder/name;used=used if used is not None else set();number=2
    while candidate.exists() or str(candidate).casefold() in used:
        candidate=folder/f"{Path(name).stem}_{number}{Path(name).suffix}";number+=1
    used.add(str(candidate).casefold());return candidate

def ensure_output_capacity(folder,estimated_bytes):
    """Fail before encoding when the target drive clearly lacks safe free space."""
    folder=Path(folder);probe=folder if folder.exists() else folder.parent
    free=shutil.disk_usage(probe).free
    required=max(64*1024*1024,int(estimated_bytes*1.35))
    if free<required:raise OSError(f"Disk space kam hai: {required//(1024*1024)} MB free space required")

def guide_tip(parent,text):
    """Readable first-use Hinglish guide: three soft pulses, then stays visible."""
    label=Label(parent,text=text,font=("Segoe UI",9,"bold"),fg=THEME["cyan"],bg=parent.cget("bg"),anchor="center",pady=3)
    label.pack(fill="x")
    def pulse(step=0):
        if not label.winfo_exists():return
        label.configure(fg=THEME["cyan"] if step%2==0 else "#ffffff")
        if step<6:label.after(420,lambda:pulse(step+1))
    label.after(100,pulse);return label

_HOME_BACKGROUND_CACHE={}
def home_background(size):
    """Fast cached premium background; never loop through millions of UI pixels."""
    w,h=max(2,int(size[0])),max(2,int(size[1]));key=(w,h)
    if key in _HOME_BACKGROUND_CACHE:return _HOME_BACKGROUND_CACHE[key]
    gw,gh=min(w,320),min(h,180);image=Image.new("RGB",(gw,gh));pixels=image.load()
    for y in range(gh):
        for x in range(gw):
            nx=x/max(1,gw-1);ny=y/max(1,gh-1);base=round(4+12*(1-ny))
            red=max(0,1-nx*2.2)*max(0,1-abs(ny-.28)*2.2);blue=max(0,(nx-.38)/.62)*max(0,1-abs(ny-.32)*1.8)
            pixels[x,y]=(min(38,base+round(31*red)),min(35,base+round(5*red+10*blue)),min(70,base+round(30*blue)+10))
    result=image.resize((w,h),Image.Resampling.BICUBIC) if image.size!=(w,h) else image
    _HOME_BACKGROUND_CACHE.clear();_HOME_BACKGROUND_CACHE[key]=result
    return result

def action_group(parent,title):
    """Create a professional grouped toolbar with a glowing category outline."""
    outer=Frame(parent,bg=THEME["panel"],bd=2,relief="ridge",highlightthickness=2,highlightbackground=THEME["cyan"],padx=5,pady=4)
    Label(outer,text=title.upper(),font=("Segoe UI",9,"bold"),fg=THEME["cyan"],bg=THEME["panel"]).pack(fill="x")
    body=Frame(outer,bg=THEME["panel"]);body.pack(fill="both",expand=True)
    return outer,body

def action_control(parent,title,help_text,command):
    """One real button: large English action and smaller Hinglish guidance in the same shape."""
    button=Button(parent,text=f"{title.upper()}\n{help_text.title()}",command=command,justify="center")
    button._cinematic_size=10;button.pack(side="left",fill="both",expand=True,padx=3,pady=2)
    return button

def unsaved_changes_dialog(parent,message="Layout Ya Rotation Save Nahi Hua."):
    """Three-choice cinematic dialog; returns save, exit, or cancel."""
    dialog=Toplevel(parent);dialog.title("UNSAVED CHANGES");dialog.transient(parent);dialog.grab_set();dialog.resizable(False,False);apply_window_icon(dialog)
    answer={"value":"cancel"};body=Frame(dialog,bg=THEME["panel"],highlightthickness=3,highlightbackground=THEME["red"],padx=28,pady=22);body.pack(fill="both",expand=True)
    Label(body,text="UNSAVED CHANGES",font=("Segoe UI",20,"bold"),fg=THEME["red"],bg=THEME["panel"]).pack(fill="x")
    Label(body,text=message,font=("Segoe UI",12,"bold"),fg=THEME["text"],bg=THEME["panel"],pady=16).pack(fill="x")
    row=Frame(body,bg=THEME["panel"]);row.pack(fill="x")
    def choose(value):answer["value"]=value;dialog.destroy()
    Button(row,text="SAVE CHANGES",command=lambda:choose("save")).pack(side="left",fill="x",expand=True,padx=4)
    Button(row,text="EXIT WITHOUT SAVING",command=lambda:choose("exit")).pack(side="left",fill="x",expand=True,padx=4)
    Button(row,text="CANCEL",command=lambda:choose("cancel")).pack(side="left",fill="x",expand=True,padx=4)
    apply_cinematic_theme(dialog);dialog.update_idletasks();dialog.geometry("720x250");dialog.protocol("WM_DELETE_WINDOW",dialog.destroy);parent.wait_window(dialog);return answer["value"]

def fill_button_row(frame, minimum_font=10):
    """Make every action in a toolbar share all available horizontal space."""
    buttons=[child for child in frame.winfo_children() if child.winfo_class()=="Button"]
    for button in buttons:
        try:
            button.pack_configure(fill="both",expand=True,padx=3,pady=2)
            button._cinematic_size=max(minimum_font,getattr(button,"_cinematic_size",minimum_font))
        except Exception:pass

class CenterProcessingOverlay:
    """Lightweight, cancellable neon loader shared by non-splash operations."""
    STAGES=("READING PDF","DETECTING CARDS","DETECTING PHOTOS","CREATING PREVIEW","PREPARING OUTPUT","SENDING TO PRINTER")
    def __init__(self,parent,title="PROCESSING FILES",total=1,cancellable=True):
        self.parent=parent;self.total=max(1,total);self.cancel_event=threading.Event();self.phase=0;self.closed=False
        self.window=Toplevel(parent);self.window.title(title);self.window.transient(parent);self.window.resizable(False,False);self.window.configure(bg=THEME["bg"]);apply_window_icon(self.window);self.window.protocol("WM_DELETE_WINDOW",self.cancel if cancellable else lambda:None)
        panel=Frame(self.window,bg=THEME["surface"],highlightthickness=2,highlightbackground=THEME["cyan"],padx=28,pady=18);panel.pack(fill="both",expand=True)
        Label(panel,text=title,font=("Segoe UI",16,"bold"),fg=THEME["text"],bg=THEME["surface"]).pack(fill="x")
        self.canvas=Canvas(panel,width=170,height=150,bg=THEME["surface"],highlightthickness=0);self.canvas.pack(pady=(5,0))
        self.stage=StringVar(value="READING PDF");self.detail=StringVar(value=f"0/{self.total} • Cards process ho rahe hain");self.percent=StringVar(value="0%")
        Label(panel,textvariable=self.stage,font=("Segoe UI",11,"bold"),fg=THEME["cyan"],bg=THEME["surface"]).pack(fill="x");Label(panel,textvariable=self.detail,font=("Segoe UI",10,"bold"),fg=THEME["text"],bg=THEME["surface"]).pack(fill="x",pady=(3,0));Label(panel,textvariable=self.percent,font=("Segoe UI",9,"bold"),fg=THEME["green"],bg=THEME["surface"]).pack(fill="x")
        if cancellable:Button(panel,text="CANCEL PROCESSING",command=self.cancel).pack(fill="x",pady=(12,0));apply_cinematic_theme(self.window)
        self.window.update_idletasks();_center_dialog(self.window,parent,450,390);self.window.lift();self.window.after(0,self._animate)
    def _animate(self):
        if self.closed or not self.window.winfo_exists():return
        self.canvas.delete("ring");cx,cy,r=85,75,50
        for index in range(14):
            angle=2*math.pi*index/14;distance=(index-self.phase)%14;strength=max(45,255-distance*17);colour=f"#{min(255,20+strength//4):02x}{min(255,80+strength//2):02x}{min(255,150+strength//2):02x}" if distance else THEME["red"];x,y=cx+math.cos(angle)*r,cy+math.sin(angle)*r;radius=4+(2 if distance==0 else 0);self.canvas.create_oval(x-radius,y-radius,x+radius,y+radius,fill=colour,outline="",tags="ring")
        self.canvas.create_text(cx,cy,text=self.percent.get(),fill=THEME["text"],font=("Segoe UI",12,"bold"),tags="ring");self.phase=(self.phase+1)%14;self.window.after(55,self._animate)
    def update(self,done,total=None,stage=None,message="Cards process ho rahe hain"):
        if self.closed:return
        total=max(1,total or self.total);done=max(0,min(done,total));self.total=total;self.stage.set(stage if stage in self.STAGES else (stage or self.stage.get()));self.detail.set(f"{done}/{total} • {message}");self.percent.set(f"{round(done*100/total)}%")
    def cancel(self):self.cancel_event.set();self.stage.set("CANCELLING SAFELY");self.detail.set("Current step complete hote hi processing rukegi")
    @property
    def cancelled(self):return self.cancel_event.is_set()
    def close(self):
        self.closed=True
        try:self.window.destroy()
        except Exception:pass

def resource_path(name):
    return ASSET_DIR / name

def set_windows_app_identity():
    """Give the packaged EXE a stable Windows taskbar identity and icon group."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SeemaDigital.MahaID.PrintStudio")
            try:ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
            except Exception:
                try:ctypes.windll.shcore.SetProcessDpiAwareness(2)
                except Exception:ctypes.windll.user32.SetProcessDPIAware()
        except Exception:pass

def themed_message(parent,title,message,kind="info",buttons=("OK",)):
    """One centered cinematic modal for errors, warnings, information and success."""
    parent=parent or (Tk._default_root if hasattr(Tk,"_default_root") else None)
    dialog=Toplevel(parent);dialog.title(title.upper());dialog.transient(parent);dialog.grab_set();dialog.resizable(True,True);apply_window_icon(dialog)
    colours={"error":THEME["red"],"warning":"#ffd34d","info":THEME["cyan"],"success":THEME["green"]}
    accent=colours.get(kind,THEME["cyan"]);answer={"value":None}
    body=Frame(dialog,bg=THEME["panel"],highlightthickness=4,highlightbackground=accent,padx=28,pady=22);body.pack(fill="both",expand=True)
    Label(body,text=title.upper(),font=("Segoe UI",19,"bold"),fg=accent,bg=THEME["panel"]).pack(fill="x")
    content=Frame(body,bg=THEME["panel"]);content.pack(fill="both",expand=True,pady=12)
    text=Label(content,text=message,font=("Segoe UI",11,"bold"),fg=THEME["text"],bg=THEME["panel"],wraplength=650,justify="center",pady=8)
    text.pack(fill="both",expand=True)
    row=Frame(body,bg=THEME["panel"]);row.pack(fill="x",side="bottom")
    for value in buttons:
        Button(row,text=value,command=lambda v=value:(answer.update(value=v),dialog.destroy())).pack(side="left",fill="x",expand=True,padx=5)
    apply_cinematic_theme(dialog);dialog.update_idletasks()
    screen_w=dialog.winfo_screenwidth();screen_h=dialog.winfo_screenheight();w=min(820,max(560,dialog.winfo_reqwidth()));h=min(max(360,dialog.winfo_reqheight()),max(420,screen_h-140))
    if parent:
        x=parent.winfo_rootx()+max(0,(parent.winfo_width()-w)//2);y=parent.winfo_rooty()+max(0,(parent.winfo_height()-h)//2)
    else:x,y=200,150
    dialog.geometry(f"{w}x{h}+{x}+{y}");dialog.minsize(min(w,560),min(h,320));dialog.maxsize(max(640,screen_w-80),max(420,screen_h-80));dialog.protocol("WM_DELETE_WINDOW",lambda:(answer.update(value=buttons[-1]),dialog.destroy()));dialog.bind("<Escape>",lambda _e:(answer.update(value=buttons[-1]),dialog.destroy()));dialog.wait_window()
    return answer["value"]

def friendly_problem(parent,title,problem,solution):
    return themed_message(parent,title,f"Kya Problem Hai:\n{problem}\n\nKya Karein:\n{solution}","error",("CLOSE",))

def _center_dialog(dialog,parent,width,height):
    """Fit a modal inside the usable monitor and center it on its owner."""
    dialog.update_idletasks();sw,sh=dialog.winfo_screenwidth(),dialog.winfo_screenheight()
    width=min(width,max(560,sw-80));height=min(height,max(420,sh-120))
    if parent and parent.winfo_exists():
        x=parent.winfo_rootx()+max(0,(parent.winfo_width()-width)//2);y=parent.winfo_rooty()+max(0,(parent.winfo_height()-height)//2)
    else:x,y=max(0,(sw-width)//2),max(0,(sh-height)//2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")

def photo_geometry(item):
    return tuple(item["boxes"]["front"])+tuple(item["boxes"]["photo"])

def confirm_photo(item):
    box=item["boxes"]["photo"];front=item["boxes"]["front"]
    if not (front[0]<=box[0]<box[2]<=front[2] and front[1]<=box[1]<box[3]<=front[3]):
        raise ValueError("Photo boundary must be entirely inside the front card.")
    item["photo_verified_geometry"]=photo_geometry(item)
    item["photo_review"]=False;item["photo_box_manual"]=True
    item.pop("photo_bypass_geometry",None)

def needs_photo_review(item):
    geometry=photo_geometry(item)
    if item.get("photo_verified_geometry")==geometry or item.get("photo_bypass_geometry")==geometry:return False
    return item.get("photo_review",False) or item.get("photo_confidence",0)<85

def invalidate_photo(item):
    item.pop("photo_verified_geometry",None);item.pop("photo_bypass_geometry",None)
    item["photo_review"]=True

def scroll_panel(parent,width=320):
    outer=Frame(parent,width=width);outer.pack_propagate(False)
    canvas=Canvas(outer,highlightthickness=0);bar=Scrollbar(outer,command=canvas.yview)
    bar.pack(side="right",fill="y");canvas.pack(side="left",fill="both",expand=True);canvas.configure(yscrollcommand=bar.set)
    inner=Frame(canvas,padx=6,pady=6);token=canvas.create_window(0,0,anchor="nw",window=inner)
    inner.bind("<Configure>",lambda _:canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>",lambda e:canvas.itemconfigure(token,width=e.width))
    return outer,inner

def photo_review_dialog(parent,items,bad):
    dialog=Toplevel(parent);dialog.title("PHOTO REVIEW REQUIRED");dialog.transient(parent);dialog.grab_set()
    answer={"value":"CANCEL","index":None}
    Label(dialog,text="PHOTO REVIEW REQUIRED",font=("Segoe UI",18,"bold")).pack(pady=12)
    Label(dialog,text="Select a card, inspect its photo, then confirm or fix the green boundary.",wraplength=560).pack()
    rows=Frame(dialog);rows.pack(fill="both",expand=True,padx=12,pady=8)
    scroll=Scrollbar(rows);scroll.pack(side="right",fill="y")
    listing=Listbox(rows,exportselection=False,yscrollcommand=scroll.set);listing.pack(fill="both",expand=True);scroll.config(command=listing.yview)
    for i in bad:listing.insert("end",items[i].get("source_label",items[i]["path"].name))
    preview=Label(dialog);preview.pack()
    def select(_=None):
        chosen=listing.curselection()
        if not chosen:return
        answer["index"]=bad[chosen[0]]
        image=items[answer["index"]]["photo"].copy();image.thumbnail((180,140))
        preview.image=ImageTk.PhotoImage(image);preview.configure(image=preview.image)
    listing.bind("<<ListboxSelect>>",select)
    def choose(value):
        if value in ("FIX SELECTED PHOTO","CONFIRM PHOTO BOUNDARY") and answer["index"] is None:return
        answer["value"]=value;dialog.destroy()
    actions=Frame(dialog);actions.pack(fill="x",padx=12,pady=8)
    for n,value in enumerate(("FIX SELECTED PHOTO","CONFIRM PHOTO BOUNDARY","REVIEW ALL","CONTINUE WITHOUT FIXING","CANCEL")):
        Button(actions,text=value,command=lambda v=value:choose(v)).grid(row=n//2,column=n%2,sticky="ew",padx=3,pady=3)
    actions.columnconfigure((0,1),weight=1)
    rows.pack_forget();actions.pack_configure(side="bottom");rows.pack(fill="both",expand=True,padx=12,pady=8)
    dialog.bind("<Escape>",lambda _:choose("CANCEL"));dialog.bind("<Return>",lambda _:choose("FIX SELECTED PHOTO"))
    dialog.protocol("WM_DELETE_WINDOW",lambda:choose("CANCEL"));apply_cinematic_theme(dialog);_center_dialog(dialog,parent,640,620);parent.wait_window(dialog)
    return answer

def final_output_dialog(parent,default_name,dpi):
    """Explicit filename/folder/format selector; footer stays fixed at every DPI."""
    dialog=Toplevel(parent);dialog.title("SAVE FINAL OUTPUT");dialog.transient(parent);dialog.grab_set();dialog.resizable(True,True);apply_window_icon(dialog)
    result={"path":None};name=StringVar(value=default_name);folder=StringVar(value=str(OUTPUT_DIR));extension=StringVar(value="JPG");quality=StringVar(value=f"PROFESSIONAL — {dpi} DPI")
    body=Frame(dialog,bg=THEME["panel"],padx=22,pady=16);body.pack(fill="both",expand=True)
    Label(body,text="SAVE FINAL OUTPUT",font=("Segoe UI",20,"bold"),bg=THEME["panel"],fg=THEME["cyan"]).pack(fill="x",pady=(0,12))
    form=Frame(body,bg=THEME["panel"]);form.pack(fill="both",expand=True)
    for row,(label,var) in enumerate((("FILE NAME",name),("OUTPUT FOLDER",folder))):
        Label(form,text=label,font=("Segoe UI",10,"bold"),bg=THEME["panel"],fg=THEME["text"],anchor="w").grid(row=row,column=0,sticky="w",pady=8);Entry(form,textvariable=var,font=("Segoe UI",11)).grid(row=row,column=1,sticky="ew",padx=8,pady=8)
    Button(form,text="CHOOSE FOLDER",command=lambda:(lambda value:folder.set(value) if value else None)(filedialog.askdirectory(parent=dialog,initialdir=folder.get()))).grid(row=1,column=2,sticky="ew")
    Label(form,text="FILE EXTENSION",font=("Segoe UI",10,"bold"),bg=THEME["panel"],fg=THEME["text"],anchor="w").grid(row=2,column=0,sticky="w",pady=8)
    formats=ttk.Combobox(form,textvariable=extension,values=("JPG","JPEG","PNG","TIFF","BMP","WEBP","PDF"),state="readonly",font=("Segoe UI",11));formats.grid(row=2,column=1,sticky="ew",padx=8,pady=8)
    Label(form,text="QUALITY MODE",font=("Segoe UI",10,"bold"),bg=THEME["panel"],fg=THEME["text"],anchor="w").grid(row=3,column=0,sticky="w",pady=8);ttk.Combobox(form,textvariable=quality,values=("PROFESSIONAL — 600 DPI","ARCHIVE MAXIMUM — 1200 DPI"),state="readonly",font=("Segoe UI",11)).grid(row=3,column=1,sticky="ew",padx=8,pady=8)
    Label(form,text="Estimated Size Final Pages Ki Sankhya Aur Format Par Depend Karega",font=("Segoe UI",10,"bold"),bg=THEME["panel"],fg=THEME["muted"]).grid(row=4,column=0,columnspan=3,sticky="w",pady=12);form.grid_columnconfigure(1,weight=1)
    def save():
        clean=re.sub(r'[<>:"/\\|?*]+','_',name.get().strip()).strip('. ')
        if not clean:return
        suffix={"JPG":".jpg","JPEG":".jpeg","PNG":".png","TIFF":".tiff","BMP":".bmp","WEBP":".webp","PDF":".pdf"}[extension.get()]
        result["path"]=Path(folder.get())/(clean+suffix);result["dpi"]=1200 if quality.get().startswith("ARCHIVE") else 600;dialog.destroy()
    footer=Frame(body,bg=THEME["panel"],height=68);footer.pack(fill="x",side="bottom");footer.pack_propagate(False)
    Button(footer,text="SAVE OUTPUT",command=save).pack(side="left",fill="both",expand=True,padx=4);Button(footer,text="OPEN OUTPUT FOLDER",command=lambda:os.startfile(folder.get()) if sys.platform.startswith("win") else None).pack(side="left",fill="both",expand=True,padx=4);Button(footer,text="CANCEL",command=dialog.destroy).pack(side="left",fill="both",expand=True,padx=4)
    dialog.bind("<Escape>",lambda _e:dialog.destroy());dialog.bind("<Return>",lambda _e:save());apply_cinematic_theme(dialog);_center_dialog(dialog,parent,820,520);dialog.minsize(650,440);dialog.wait_window();return result

# Route ordinary Tk notices through the same centered cinematic visual system.
messagebox.showinfo=lambda title,message,**kwargs:themed_message(kwargs.get("parent"),title,message,"info",("CLOSE",))
messagebox.showwarning=lambda title,message,**kwargs:themed_message(kwargs.get("parent"),title,message,"warning",("CLOSE",))
messagebox.showerror=lambda title,message,**kwargs:themed_message(kwargs.get("parent"),title,message,"error",("CLOSE",))
messagebox.askyesno=lambda title,message,**kwargs:themed_message(kwargs.get("parent"),title,message,"warning",("CONTINUE","CANCEL"))=="CONTINUE"

def apply_window_icon(window):
    """Apply the SD icon to this window and all future child windows."""
    try:window.iconbitmap(default=resource_path("Seema_Digital_Print.ico"))
    except Exception:
        try:window.iconbitmap(resource_path("Seema_Digital_Print.ico"))
        except Exception:pass

def full_screen(window):
    """Use Windows maximized mode: full workspace with the taskbar visible."""
    window.update_idletasks()
    try:
        window.state("zoomed")
    except Exception:
        window.geometry(f"{window.winfo_screenwidth()}x{window.winfo_screenheight()-70}+0+0")
    window.minsize(1024, 680)

def show_maximized(window):
    """Reveal a main workspace without letting Tk restore a stale small size."""
    window.deiconify()
    full_screen(window)
    window.lift()
    window.focus_force()

def _ui_font(size):
    """Pillow font for the cinematic splash; packaged Windows font fallback."""
    for name in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"):
        try:return ImageFont.truetype(name, size)
        except OSError:pass
    return ImageFont.load_default()

def cinematic_splash(source, size, panel_height=132, background_source=None):
    """Render one approved image edge-to-edge: no duplicate/blur side layers."""
    width,height=size
    # Deliberately fit the single approved 16:9 artwork to the client area.
    # This guarantees that no letterbox, blurred strip or inset frame appears.
    # Cover crops only surplus outer pixels.  It never changes the aspect ratio,
    # so faces, cards and lettering cannot be pulled wider/taller.
    return ImageOps.fit(source.convert("RGB"),(width,height),method=Image.Resampling.LANCZOS,centering=(.5,.5)).convert("RGBA")

def cinematic_progress_panel(width,height,percent,phase=0):
    percent=max(0,min(100,int(percent)))
    panel=Image.new("RGBA",(width,height),(0,0,0,0));draw=ImageDraw.Draw(panel)
    left,right,top,bottom=24,width-100,16,48
    draw.rounded_rectangle((left,top,right,bottom),radius=16,fill="#06172c",outline="#21d8ff",width=2)
    if percent:
        end=left+(right-left)*percent/100
        draw.rounded_rectangle((left,top,end,bottom),radius=min(16,max(1,(end-left)/2)),fill="#078cff",outline="#21d8ff",width=2)
    draw.text((width-84,16),f"{percent}%",font=_ui_font(23),fill="white")
    draw.text((width//2,76),"Optimizing Maha ID Preview…",anchor="mm",font=_ui_font(17),fill="white")
    return panel

def password_candidates(path: Path):
    """Common e-document password variants, tried without interrupting work."""
    stem=path.stem.strip(); compact=re.sub(r"[^A-Za-z0-9]", "", stem)
    parts=re.findall(r"[A-Za-z]+|\d+", stem)
    values=[stem,stem.lower(),stem.upper(),compact,compact.lower(),compact.upper()]
    # Portal filenames often contain DOB/mobile digits; try every clear digit
    # component, but never guess a person's private information.
    values.extend(part for part in parts if part.isdigit() and 4<=len(part)<=12)
    return list(dict.fromkeys(value for value in values if value))

def open_pdf(path: Path,password=None,allow_prompt=True,parent=None):
    doc=pymupdf.open(path)
    if not doc.needs_pass:return doc
    if password and doc.authenticate(password):return doc
    for password in password_candidates(path):
        if doc.authenticate(password):return doc
    if not allow_prompt:
        doc.close();raise ValueError("PDF password required")
    password=simpledialog.askstring("PDF Password Required", f"{path.name} is password protected. Password likhen:", show="*",parent=parent)
    if password and doc.authenticate(password):return doc
    doc.close()
    raise ValueError("PDF password open nahi hua. Correct password likhkar file dobara select karein.")

class _LocalImageParser(HTMLParser):
    def __init__(self):
        super().__init__();self.sources=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower() in ("img","object","embed"):
            values=dict(attrs);source=values.get("src") or values.get("data")
            if source:self.sources.append(source)

def _render_bytes(data,suffix):
    if suffix==".svg":
        doc=pymupdf.open(stream=data,filetype="svg")
        try:
            pix=doc[0].get_pixmap(matrix=pymupdf.Matrix(4,4),alpha=False)
            return [Image.frombytes("RGB",(pix.width,pix.height),pix.samples)]
        finally:doc.close()
    pages=[]
    with Image.open(io.BytesIO(data)) as img:
        for frame in range(getattr(img,"n_frames",1)):
            img.seek(frame);pages.append(ImageOps.exif_transpose(img).convert("RGB"))
    return pages

def _embedded_document_images(path):
    """Extract original Office images without running macros or external links."""
    pages=[]
    with zipfile.ZipFile(path) as archive:
        members=[n for n in archive.namelist() if "/media/" in n.lower() and Path(n).suffix.lower() in IMPORT_EXTENSIONS]
        if sum(archive.getinfo(n).file_size for n in members)>1024**3:raise ValueError("Office media 1 GB safety limit se bada hai.")
        for name in members:
            try:pages.extend(_render_bytes(archive.read(name),Path(name).suffix.lower()))
            except Exception:continue
    if not pages:raise ValueError("Readable embedded card image nahi mili; file ko PDF export karke retry karein.")
    return pages

def _referenced_local_images(path):
    """Read local/data images only; network and JavaScript are never executed."""
    content=path.read_text(encoding="utf-8",errors="ignore");sources=[]
    if path.suffix.lower() in (".html",".htm"):
        parser=_LocalImageParser();parser.feed(content);sources=parser.sources
    else:sources=re.findall(r'(?i)(?:[A-Z]:[^\\\n\r,";]+|[^\s,";]+)\.(?:jpe?g|png|tiff?|bmp|webp|gif|svg)',content)
    pages=[]
    for source in sources[:500]:
        try:
            if source.startswith("data:image/") and ";base64," in source:
                header,payload=source.split(",",1);suffix="."+header.split("/")[1].split(";")[0].replace("jpeg","jpg")
                pages.extend(_render_bytes(base64.b64decode(payload,validate=True),suffix))
            elif not re.match(r"(?i)^https?://",source):
                candidate=(path.parent/unquote(source.replace("file:///",""))).resolve()
                if candidate.is_file():pages.extend(render_source_pages(candidate))
        except Exception:continue
    if not pages:raise ValueError("Readable local/embedded card image nahi mili.")
    return pages

def render_source_pages(path: Path,password=None) -> list[Image.Image]:
    """Universal safe importer converts every source to common RGB pages."""
    path=Path(path);suffix=path.suffix.lower()
    if suffix not in IMPORT_EXTENSIONS:raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")
    if suffix==".zip":
        pages=[]
        with zipfile.ZipFile(path) as archive:
            infos=[i for i in archive.infolist() if not i.is_dir()]
            if len(infos)>1000 or sum(i.file_size for i in infos)>2*1024**3:raise ValueError("ZIP safety limit exceed hui.")
            with tempfile.TemporaryDirectory(prefix="maha_id_import_") as folder:
                root=Path(folder).resolve()
                for info in infos:
                    target=(root/info.filename).resolve();suffix2=Path(info.filename).suffix.lower()
                    if root not in target.parents or suffix2 not in IMPORT_EXTENSIONS or suffix2==".zip":continue
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with archive.open(info) as src,open(target,"wb") as dst:shutil.copyfileobj(src,dst)
                    try:pages.extend(render_source_pages(target))
                    except Exception:continue
        if not pages:raise ValueError("ZIP me readable Maha ID source nahi mila.")
        return pages
    if suffix in (".docx",".xlsx",".pptx"):return _embedded_document_images(path)
    if suffix in (".html",".htm",".txt",".csv"):return _referenced_local_images(path)
    if suffix==".svg":return _render_bytes(path.read_bytes(),suffix)
    if suffix==".pdf":
        doc=open_pdf(path,password=password,allow_prompt=False)
        try:
            if not doc.page_count:raise ValueError("PDF me koi page nahi hai.")
            pages=[]
            for page in doc:
                pix=page.get_pixmap(matrix=pymupdf.Matrix(300/72,300/72),alpha=False)
                pages.append(Image.frombytes("RGB",(pix.width,pix.height),pix.samples))
            return pages
        finally:doc.close()
    return _render_bytes(path.read_bytes(),suffix)

def render_source(path: Path,password=None) -> Image.Image:
    """Backward-compatible single-page renderer used by detection tests/tools."""
    return render_source_pages(path,password)[0]

def preflight_pdf_password(path:Path,parent=None):
    """Resolve protected PDF passwords on Tk's main thread before background work."""
    if path.suffix.lower()!=".pdf":return None
    doc=pymupdf.open(path)
    try:
        if not doc.needs_pass:return None
        for candidate in password_candidates(path):
            if doc.authenticate(candidate):return candidate
    finally:doc.close()
    return simpledialog.askstring("PDF Password Required",f"{path.name} protected hai. Password likhen:",show="*",parent=parent)

def clamp(box, w, h):
    x1,y1,x2,y2 = box; x1,x2 = sorted((max(0,x1),min(w,x2))); y1,y2 = sorted((max(0,y1),min(h,y2)))
    return x1,y1,max(x1+8,x2),max(y1+8,y2)

def maha_seed(image: Image.Image):
    """Fast MahaSarathi panel detector; upper panel=Front, lower QR panel=Back."""
    small=image.copy(); small.thumbnail((1600,1600),Image.Resampling.BILINEAR); sx,sy=image.width/small.width,image.height/small.height
    try:
        import numpy as np
        ink=np.asarray(small.convert("RGB")).min(axis=2)<245; active=ink.mean(axis=1)>.018; runs=[]; start=None
        for i,value in enumerate(active):
            if value and start is None: start=i
            if start is not None and (not value or i==len(active)-1):
                end=i if not value else i+1
                if end-start>=max(18,small.height//45): runs.append((start,end))
                start=None
        merged=[]
        for run in runs:
            if merged and run[0]-merged[-1][1]<small.height*.035: merged[-1]=(merged[-1][0],run[1])
            else: merged.append(run)
        panels=[]
        for y1,y2 in merged:
            xs=np.where(ink[y1:y2].mean(axis=0)>.010)[0]
            if xs.size:
                x1,x2=int(xs.min()),int(xs.max())+1
                if (x2-x1)/max(1,y2-y1)>=1.15: panels.append((x1,y1,x2,y2))
        if len(panels)>=2:
            return [tuple(round(v*(sx if n%2==0 else sy)) for n,v in enumerate(box)) for box in sorted(panels,key=lambda b:b[1])[:2]]
    except Exception: pass
    w,h=image.size
    return [(round(w*.07),round(h*.06),round(w*.93),round(h*.44)),(round(w*.07),round(h*.50),round(w*.93),round(h*.88))]

def photo_seed(front):
    """Maha ID portrait position: narrow left-side photograph inside Front."""
    x1,y1,x2,y2=front; w,h=x2-x1,y2-y1
    return (round(x1+w*.050),round(y1+h*.135),round(x1+w*.295),round(y1+h*.555))

def refine_photo_box_with_confidence(image,front,preset="MAHA ID / MahaSarathi",custom=None):
    from .detection import detect_photo
    return detect_photo(image,front,preset,custom)

def refine_photo_box(image,front):
    return refine_photo_box_with_confidence(image,front)[0]
def confine(box, outer):
    x1,y1,x2,y2=(int(round(float(value))) for value in box);ox1,oy1,ox2,oy2=(int(round(float(value))) for value in outer)
    return tuple(int(value) for value in clamp((max(ox1,x1),max(oy1,y1),min(ox2,x2),min(oy2,y2)),ox2,oy2))

def map_relative_box(box,source_outer,target_outer):
    """Transfer a crop proportionally between differently sized card fronts."""
    sx1,sy1,sx2,sy2=source_outer;bx1,by1,bx2,by2=box;sw=max(1,sx2-sx1);sh=max(1,sy2-sy1)
    relative=((bx1-sx1)/sw,(by1-sy1)/sh,(bx2-sx1)/sw,(by2-sy1)/sh)
    if not (0<=relative[0]<relative[2]<=1 and 0<=relative[1]<relative[3]<=1):raise ValueError("Crop box must stay inside source card")
    tx1,ty1,tx2,ty2=target_outer;tw=max(1,tx2-tx1);th=max(1,ty2-ty1)
    return confine((round(tx1+relative[0]*tw),round(ty1+relative[1]*th),round(tx1+relative[2]*tw),round(ty1+relative[3]*th)),target_outer)

def photo_layout_signature(image,front):
    """Small identity-free structure signature used only to group card layouts."""
    card=ImageOps.fit(image.crop(front).convert("L"),(32,20),Image.Resampling.BILINEAR)
    # Names and faces vary; mask the portrait/text centre and retain stable
    # logos, header, separator and footer structure.
    draw=ImageDraw.Draw(card);draw.rectangle((1,4,25,15),fill=128)
    edges=card.filter(ImageFilter.FIND_EDGES);values=list(edges.tobytes());median=sorted(values)[len(values)//2]
    return tuple(value>median+8 for value in values)

def matching_photo_layout(source,target,max_difference=.30):
    sf=source["boxes"]["front"];tf=target["boxes"]["front"];sr=(sf[2]-sf[0])/max(1,sf[3]-sf[1]);tr=(tf[2]-tf[0])/max(1,tf[3]-tf[1])
    if abs(sr-tr)/max(sr,.01)>.06:return False
    left=photo_layout_signature(source["page"],sf);right=photo_layout_signature(target["page"],tf)
    return sum(a!=b for a,b in zip(left,right))/max(1,len(left))<=max_difference

def photo_box_batch_preview_dialog(parent,source,candidates,skipped):
    """Scrollable visual proof before a photo box is copied to a batch."""
    dialog=Toplevel(parent);dialog.title("PREVIEW BEFORE APPLY");dialog.transient(parent);dialog.grab_set();dialog.resizable(True,True);apply_window_icon(dialog);answer={"apply":False};photos=[]
    outer=Frame(dialog,bg=THEME["panel"],padx=14,pady=12);outer.pack(fill="both",expand=True)
    Label(outer,text="PREVIEW BEFORE APPLY",font=("Segoe UI",19,"bold"),bg=THEME["panel"],fg=THEME["cyan"]).pack(fill="x")
    Label(outer,text=f"{len(candidates)} Matching Card(s) • {len(skipped)} Different Layout Card(s) Skip Honge",font=("Segoe UI",10,"bold"),bg=THEME["panel"],fg=THEME["text"]).pack(fill="x",pady=(2,8))
    holder=Frame(outer,bg=THEME["surface"]);holder.pack(fill="both",expand=True);canvas=Canvas(holder,bg=THEME["surface"],highlightthickness=0);scroll=Scrollbar(holder,orient="vertical",command=canvas.yview,width=22);canvas.configure(yscrollcommand=scroll.set);canvas.pack(side="left",fill="both",expand=True);scroll.pack(side="right",fill="y")
    rows=Frame(canvas,bg=THEME["surface"]);window=canvas.create_window((0,0),window=rows,anchor="nw")
    def thumbnail(item,box):
        front=item["boxes"]["front"];crop=item["page"].crop(front).convert("RGB");mapped=(box[0]-front[0],box[1]-front[1],box[2]-front[0],box[3]-front[1]);scale=min(260/crop.width,150/crop.height);preview=crop.resize((max(1,round(crop.width*scale)),max(1,round(crop.height*scale))),Image.Resampling.BILINEAR);ImageDraw.Draw(preview).rectangle(tuple(round(v*scale) for v in mapped),outline=THEME["green"],width=3);return preview
    for row,(item,mapped) in enumerate(candidates):
        image=ImageTk.PhotoImage(thumbnail(item,mapped));photos.append(image);Label(rows,image=image,bg=THEME["surface"]).grid(row=row,column=0,padx=8,pady=6);Label(rows,text=item.get("source_label",item["path"].name),font=("Segoe UI",10,"bold"),bg=THEME["surface"],fg=THEME["text"],anchor="w").grid(row=row,column=1,sticky="ew",padx=8)
    for item in skipped:Label(rows,text=f"SKIPPED — {item.get('source_label',item['path'].name)} — Layout Match Nahi Hua",font=("Segoe UI",10,"bold"),bg=THEME["surface"],fg="#ffd34d",anchor="w").grid(column=0,columnspan=2,sticky="ew",padx=8,pady=5)
    rows.grid_columnconfigure(1,weight=1);rows.bind("<Configure>",lambda _e:canvas.configure(scrollregion=canvas.bbox("all")));canvas.bind("<Configure>",lambda e:canvas.itemconfigure(window,width=e.width));canvas.bind_all("<MouseWheel>",lambda e:canvas.yview_scroll(-1 if e.delta>0 else 1,"units"))
    footer=Frame(outer,bg=THEME["panel"],height=68);footer.pack(fill="x",side="bottom",pady=(10,0));footer.pack_propagate(False)
    def close(value=False):answer["apply"]=value;canvas.unbind_all("<MouseWheel>");dialog.destroy()
    Button(footer,text="APPLY TO MATCHING CARDS",command=lambda:close(True)).pack(side="left",fill="both",expand=True,padx=4);Button(footer,text="CANCEL",command=close).pack(side="left",fill="both",expand=True,padx=4)
    dialog.bind("<Escape>",lambda _e:close());dialog.bind("<Return>",lambda _e:close(True));dialog.protocol("WM_DELETE_WINDOW",close);apply_cinematic_theme(dialog);_center_dialog(dialog,parent,980,700);dialog.minsize(700,460);dialog.wait_window();return answer["apply"]

def refine_card_box(image, seed):
    """Remove external white space and snap to the complete 90:57 card boundary."""
    try:
        import cv2, numpy as np
        x1,y1,x2,y2=seed;sw,sh=x2-x1,y2-y1;pad=max(18,round(min(sw,sh)*.10))
        ox,oy=max(0,x1-pad),max(0,y1-pad)
        region=np.asarray(image.crop((ox,oy,min(image.width,x2+pad),min(image.height,y2+pad))).convert("RGB"))
        gray=cv2.cvtColor(region,cv2.COLOR_RGB2GRAY);blur=cv2.GaussianBlur(gray,(5,5),0)
        adaptive=cv2.adaptiveThreshold(blur,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,41,7)
        edges=cv2.Canny(blur,18,95);combined=cv2.bitwise_or(adaptive,edges)
        combined=cv2.morphologyEx(combined,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_RECT,(17,11)),iterations=2)
        contours,_=cv2.findContours(combined,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE);candidates=[]
        expected=90/57
        for contour in contours:
            bx,by,bw,bh=cv2.boundingRect(contour);area=bw*bh;ratio=bw/max(1,bh)
            # A contour spanning the next tightly packed row used to win merely
            # because it had more pixels.  Never allow a candidate materially
            # larger than the seed belonging to this card.
            if area<sw*sh*.42 or bw>sw*1.16 or bh>sh*1.16 or not (1.38<=ratio<=1.92):continue
            cx,cy=ox+bx+bw/2,oy+by+bh/2;distance=abs(cx-(x1+x2)/2)/sw+abs(cy-(y1+y2)/2)/sh
            if distance>.34:continue
            size_error=abs(bw-sw)/sw+abs(bh-sh)/sh
            score=area*(1+max(0,1-abs(ratio-expected)/expected))/(1+distance*4+size_error*3)
            candidates.append((score,(ox+bx,oy+by,ox+bx+bw,oy+by+bh)))
        if candidates:return clamp(max(candidates,key=lambda row:row[0])[1],image.width,image.height)
    except Exception:pass
    return seed

def high_quality_page(image,dpi=EXPORT_DPI):
    scale=float(dpi)/300
    return image.convert("RGB") if abs(scale-1)<.001 else image.convert("RGB").resize((round(image.width*scale),round(image.height*scale)),Image.Resampling.LANCZOS)

def save_image_max(image,path,dpi=EXPORT_DPI):
    """Save selected raster extension at maximum practical quality and verify it."""
    path=Path(path);rendered=high_quality_page(image,dpi);suffix=path.suffix.lower();temporary=path.with_name(f".{path.stem}.partial{suffix}")
    if suffix in (".jpg",".jpeg"):rendered.save(temporary,"JPEG",quality=100,subsampling=0,dpi=(dpi,dpi),optimize=False)
    elif suffix==".png":rendered.save(temporary,"PNG",compress_level=1,dpi=(dpi,dpi))
    elif suffix in (".tif",".tiff"):rendered.save(temporary,"TIFF",compression="tiff_lzw",dpi=(dpi,dpi))
    elif suffix==".bmp":rendered.save(temporary,"BMP",dpi=(dpi,dpi))
    elif suffix==".webp":rendered.save(temporary,"WEBP",lossless=True,quality=100,method=6)
    else:raise ValueError(f"Unsupported output extension: {suffix}")
    with Image.open(temporary) as check:
        if check.size!=rendered.size:raise ValueError("Output verification size mismatch")
        check.verify()
    os.replace(temporary,path)

def tight_crop(image):
    diff=ImageChops.difference(image.convert("RGB"),Image.new("RGB",image.size,WHITE)).convert("L").point(lambda x:255 if x>18 else 0); box=diff.getbbox()
    if not box:return image.convert("RGB")
    return image.crop((max(0,box[0]-5),max(0,box[1]-5),min(image.width,box[2]+5),min(image.height,box[3]+5))).convert("RGB")

def card_field(image):
    source=tight_crop(image)
    if source.height>source.width*1.12: source=source.rotate(90,expand=True)
    fit=ImageOps.contain(source,CARD_SIZE,Image.Resampling.LANCZOS); out=Image.new("RGB",CARD_SIZE,WHITE)
    out.paste(fit,((CARD_SIZE[0]-fit.width)//2,(CARD_SIZE[1]-fit.height)//2)); return out

def default_adjustments():
    return {name: 0 for name in ADJUSTMENTS}

def smart_light_adjustments(image):
    """Adaptive, conservative light correction with highlight protection."""
    sample=image.convert("RGB");sample.thumbnail((320,320),Image.Resampling.BILINEAR);gray=sample.convert("L")
    mean=ImageStat.Stat(gray).mean[0];hist=gray.histogram();pixels=max(1,sum(hist));bright=sum(hist[238:])/pixels;dark=sum(hist[:45])/pixels
    # Strong but protected correction: lift dark ID photos clearly without
    # changing face geometry, skin tone, crop, or identity.
    brightness=max(-12,min(30,round((150-mean)/6.5)))
    exposure=max(-10,min(22,round((142-mean)/8.5)))
    highlights=-24 if bright>.18 else -16 if bright>.08 else -8
    shadows=28 if dark>.20 else 20 if dark>.08 else 10
    contrast=14 if mean<105 else 12 if mean<175 else 7
    saturation=5 if mean<175 else 2
    sharpness=14 if mean<125 else 11
    return {**default_adjustments(),"Brightness":brightness,"Contrast":contrast,"Saturation":saturation,"Exposure":exposure,"Shadows":shadows,"Highlights":highlights,"Sharpness":sharpness}

def adjust_image(image, values):
    """Fast non-destructive tonal correction; it never alters facial geometry."""
    out=image.convert("RGB")
    if values.get("Brightness",0): out=ImageEnhance.Brightness(out).enhance(1+values["Brightness"]/180)
    if values.get("Exposure",0): out=ImageEnhance.Brightness(out).enhance(2**(values["Exposure"]/100))
    if values.get("Contrast",0): out=ImageEnhance.Contrast(out).enhance(1+values["Contrast"]/160)
    if values.get("Saturation",0): out=ImageEnhance.Color(out).enhance(1+values["Saturation"]/180)
    if values.get("Hue",0):
        hsv=out.convert("HSV"); h,s,v=hsv.split(); h=h.point(lambda p:(p+round(values["Hue"]*1.25))%256); out=Image.merge("HSV",(h,s,v)).convert("RGB")
    if values.get("Temperature",0):
        amount=values["Temperature"]/100
        r,g,b=out.split(); r=r.point(lambda p:max(0,min(255,round(p*(1+.16*amount))))); b=b.point(lambda p:max(0,min(255,round(p*(1-.16*amount))))); out=Image.merge("RGB",(r,g,b))
    if values.get("Shadows",0) or values.get("Highlights",0):
        # Gentle global tonal lift/compression: quick enough for a live preview.
        shadows,highlights=values.get("Shadows",0),values.get("Highlights",0)
        out=out.point(lambda p:max(0,min(255,round(p + shadows*(1-p/255)*.45 - highlights*(p/255)*.35))))
    if values.get("Sharpness",0): out=ImageEnhance.Sharpness(out).enhance(1+values["Sharpness"]/55)
    return out

def processed_cards(item):
    """Create final selected crops once, immediately before output generation."""
    page=item["page"]; boxes=item["boxes"]; settings=item.get("adjustments",{})
    front=adjust_image(page.crop(boxes["front"]),settings.get("front",default_adjustments()))
    back=adjust_image(page.crop(boxes["back"]),settings.get("back",default_adjustments()))
    photo_box=boxes["photo"]; photo=adjust_image(page.crop(photo_box),settings.get("photo",default_adjustments()))
    fx1,fy1,fx2,fy2=boxes["front"]; px1,py1,px2,py2=photo_box
    # Photo correction remains limited to the selected photo rectangle.
    if fx1<=px1 and fy1<=py1 and px2<=fx2 and py2<=fy2:
        front.paste(photo,(px1-fx1,py1-fy1))
    return front,back,photo

def safe_4x6_offset(x_mm=0.0,y_mm=0.0):
    """Keep both exact-size cards fully inside the 4x6 sheet."""
    dx=round(float(x_mm)*PX_PER_MM);dy=round(float(y_mm)*PX_PER_MM)
    dx=max(-TOP[0],min(SHEET_SIZE[0]-CARD_SIZE[0]-TOP[0],dx))
    dy=max(-TOP[1],min(SHEET_SIZE[1]-(BOTTOM[1]+CARD_SIZE[1]),dy))
    return dx,dy

def make_4x6(front,back,rotate_back=True,x_offset_mm=0.0,y_offset_mm=0.0,pair_gap_mm=0.0):
    dx,dy=safe_4x6_offset(x_offset_mm,y_offset_mm);gap=max(0,min(round(float(pair_gap_mm)*PX_PER_MM),SHEET_SIZE[1]-TOP[1]-2*CARD_SIZE[1]));dy=max(-TOP[1],min(SHEET_SIZE[1]-(TOP[1]+2*CARD_SIZE[1]+gap),dy));page=Image.new("RGB",SHEET_SIZE,WHITE);page.info.update(layout_mm=(101.6,152.4),card_rects=[]);page.paste(card_field(front),(TOP[0]+dx,TOP[1]+dy))
    back_card=card_field(back.rotate(180,expand=True) if rotate_back else back)
    page.paste(back_card,(BOTTOM[0]+dx,TOP[1]+CARD_SIZE[1]+gap+dy));page.info["card_rects"]=[(TOP[0]+dx,TOP[1]+dy,TOP[0]+dx+CARD_SIZE[0],TOP[1]+dy+CARD_SIZE[1]),(BOTTOM[0]+dx,TOP[1]+CARD_SIZE[1]+gap+dy,BOTTOM[0]+dx+CARD_SIZE[0],TOP[1]+2*CARD_SIZE[1]+gap+dy)];return page

def default_a4_position(index):
    return a4_grid_positions(index+1)[index]

def make_a4(cards,positions=None):
    pages=[]
    for offset in range(0,len(cards),10):
        page=Image.new("RGB",A4_SIZE,WHITE);page.info.update(layout_mm=(210.,297.),card_rects=[]);draw=ImageDraw.Draw(page)
        for slot,card in enumerate(cards[offset:offset+10]):
            absolute=offset+slot;x,y=positions[absolute] if positions and absolute<len(positions) else default_a4_position(absolute)
            x=max(0,min(A4_SIZE[0]-CARD_SIZE[0],round(x)));y=max(0,min(A4_SIZE[1]-CARD_SIZE[1],round(y)));page.paste(card_field(card),(x,y));page.info["card_rects"].append((x,y,x+CARD_SIZE[0],y+CARD_SIZE[1]));draw.rectangle((x,y,x+CARD_SIZE[0]-1,y+CARD_SIZE[1]-1),outline="black",width=2)
        pages.append(page)
    return pages

def a4_grid_positions(count,hgap_mm=10.0,vgap_mm=1.5):
    """Centered exact-card grid; gaps are physical millimetres at 300 DPI."""
    hgap=max(0,min(round(float(hgap_mm)*PX_PER_MM),A4_SIZE[0]-2*CARD_SIZE[0]))
    vgap=max(0,min(round(float(vgap_mm)*PX_PER_MM),(A4_SIZE[1]-5*CARD_SIZE[1])//4))
    # Approved physical geometry: 10 + 90 + 10 + 90 + 10 = 210 mm,
    # and 3 + (5 x 57) + (4 x 1.5) + 3 = 297 mm.
    left=round(10.0*PX_PER_MM);top=round(3.0*PX_PER_MM)
    return [(left+(i%2)*(CARD_SIZE[0]+hgap),top+(i%10//2)*(CARD_SIZE[1]+vgap)) for i in range(count)]

def a4_pair_positions(count,hgap_mm=2.0,vgap_mm=8.0):
    """Positions for four locked front+back card pairs on each A4 page."""
    pair_h=2*CARD_SIZE[1]
    hgap=max(0,min(round(float(hgap_mm)*PX_PER_MM),A4_SIZE[0]-2*CARD_SIZE[0]))
    vgap=max(0,min(round(float(vgap_mm)*PX_PER_MM),A4_SIZE[1]-2*pair_h))
    left=(A4_SIZE[0]-(2*CARD_SIZE[0]+hgap))//2
    top=(A4_SIZE[1]-(2*pair_h+vgap))//2
    return [(left+(i%4%2)*(CARD_SIZE[0]+hgap),top+(i%4//2)*(pair_h+vgap)) for i in range(count)]

def make_a4_pairs(items,hgap_mm=2.0,vgap_mm=8.0,positions=None):
    """Put four Maha ID front/back pairs on A4 without resizing the cards."""
    pages=[]
    default_positions=a4_pair_positions(len(items),hgap_mm,vgap_mm)
    for offset in range(0,len(items),4):
        page=Image.new("RGB",A4_SIZE,WHITE);page.info.update(layout_mm=(210.,297.),card_rects=[]);draw=ImageDraw.Draw(page)
        for slot,item in enumerate(items[offset:offset+4]):
            absolute=offset+slot;x,y=positions[absolute] if positions and absolute<len(positions) else default_positions[absolute]
            x=max(0,min(A4_SIZE[0]-CARD_SIZE[0],round(x)));y=max(0,min(A4_SIZE[1]-2*CARD_SIZE[1],round(y)))
            front=card_field(item["front"]);back=card_field(item["back"].rotate(180,expand=True) if item.get("rotate_back",False) else item["back"])
            page.paste(front,(x,y));page.paste(back,(x,y+CARD_SIZE[1]));page.info["card_rects"].extend([(x,y,x+CARD_SIZE[0],y+CARD_SIZE[1]),(x,y+CARD_SIZE[1],x+CARD_SIZE[0],y+2*CARD_SIZE[1])])
            draw.rectangle((x,y,x+CARD_SIZE[0]-1,y+2*CARD_SIZE[1]-1),outline="black",width=2)
        pages.append(page)
    return pages

def a4_five_pair_positions(count,vgap_mm=1.2):
    """Five horizontal Front+Back pairs per A4, exact size and zero inner gap."""
    pair_w=2*CARD_SIZE[0]
    max_gap=max(0,(A4_SIZE[1]-5*CARD_SIZE[1])//4)
    gap=max(0,min(round(float(vgap_mm)*PX_PER_MM),max_gap))
    left=(A4_SIZE[0]-pair_w)//2
    top=(A4_SIZE[1]-(5*CARD_SIZE[1]+4*gap))//2
    return [(left,top+(i%5)*(CARD_SIZE[1]+gap)) for i in range(count)]

def make_a4_five_pairs(items,vgap_mm=1.2,positions=None):
    """Render 5 Front+Back rows on A4; both sides stay exactly 90 x 57 mm."""
    pages=[];defaults=a4_five_pair_positions(len(items),vgap_mm)
    for offset in range(0,len(items),5):
        page=Image.new("RGB",A4_SIZE,WHITE);page.info.update(layout_mm=(210.,297.),card_rects=[]);draw=ImageDraw.Draw(page)
        for slot,item in enumerate(items[offset:offset+5]):
            absolute=offset+slot;x,y=positions[absolute] if positions and absolute<len(positions) else defaults[absolute]
            x=max(0,min(A4_SIZE[0]-2*CARD_SIZE[0],round(x)));y=max(0,min(A4_SIZE[1]-CARD_SIZE[1],round(y)))
            front=card_field(item["front"]);back=card_field(item["back"].rotate(180,expand=True) if item.get("rotate_back",False) else item["back"])
            page.paste(front,(x,y));page.paste(back,(x+CARD_SIZE[0],y));page.info["card_rects"].extend([(x,y,x+CARD_SIZE[0],y+CARD_SIZE[1]),(x+CARD_SIZE[0],y,x+2*CARD_SIZE[0],y+CARD_SIZE[1])])
            draw.rectangle((x,y,x+2*CARD_SIZE[0]-1,y+CARD_SIZE[1]-1),outline="black",width=2)
            draw.line((x+CARD_SIZE[0],y,x+CARD_SIZE[0],y+CARD_SIZE[1]-1),fill="black",width=2)
        pages.append(page)
    return pages

class FastCropWindow:
    """Only Canvas vectors move while dragging; image processing happens on Save."""
    def __init__(self,app,item,done,selected_items=None,parent=None):
        self.app,self.item,self.done,self.parent=app,item,done,parent
        # Hide the previous workspace before constructing the next one. This
        # prevents a second taskbar window and the small-window resize flash.
        if self.parent:self.parent.withdraw()
        self.window=Toplevel(app.root);self.window.title("SEEMA DIGITAL — Fast Maha ID Crop");full_screen(self.window)
        apply_window_icon(self.window)
        self.active,self.drag,self.start="front",None,(0,0);self.boxes=dict(item["boxes"]);self.boxes.setdefault("photo",photo_seed(self.boxes["front"]));self.rotate_back=BooleanVar(value=item.get("rotate_back",False))
        self.fit_scale=min(760/item["page"].width,650/item["page"].height,1);self.scale=self.fit_scale;self.offset=[12.0,12.0];self.space_down=False;self.pan_start=None;self.pan_origin=None
        self.undo_stack=[];self.redo_stack=[];self.bulk_photo_box_undo=[];self.dirty=False;self.selected_items=selected_items or [item];self.compare_original=False
        self.settings={target:dict(item.get("adjustments",{}).get(target,default_adjustments())) for target in ("front","back","photo")}
        self.opening_state=(dict(self.boxes),{k:dict(v) for k,v in self.settings.items()},self.rotate_back.get())
        topbar=Frame(self.window,padx=8,pady=6);topbar.pack(fill="x")
        Button(topbar,text="← BACK",command=self.cancel).pack(side="left",padx=4)
        Label(topbar,text="CROP / PHOTO REVIEW",font=("Segoe UI",12,"bold")).pack(side="left",padx=8)
        Button(topbar,text="EXIT WITHOUT CHANGES",command=self.cancel).pack(side="right",padx=4)
        Button(topbar,text="APPLY CHANGES & EXIT",command=self.apply).pack(side="right",padx=4)
        area=Frame(self.window);area.pack(fill="both",expand=True,padx=16);self.canvas=Canvas(area,bg="#30343b",highlightthickness=0);self.canvas.pack(side="left",fill="both",expand=True)
        self.canvas.bind("<Button-1>",self.down);self.canvas.bind("<B1-Motion>",self.move);self.canvas.bind("<ButtonRelease-1>",self.up);self.canvas.bind("<Configure>",lambda _:self.fit_view())
        self.canvas.bind("<Control-MouseWheel>",self.zoom_wheel);self.canvas.bind("<Control-Button-4>",lambda e:self.zoom_at(e.x,e.y,1.12));self.canvas.bind("<Control-Button-5>",lambda e:self.zoom_at(e.x,e.y,1/1.12))
        self.window.bind("<KeyPress-space>",self.space_press);self.window.bind("<KeyRelease-space>",self.space_release)
        self.window.bind("<Control-z>",self.undo);self.window.bind("<Control-y>",self.redo)
        for key,delta in (("<Left>",(-1,0)),("<Right>",(1,0)),("<Up>",(0,-1)),("<Down>",(0,1))):self.window.bind(key,lambda e,d=delta:self.nudge(*d))
        # Three fixed work zones keep every important control visible on a
        # 1366x768 laptop: document canvas, enhancement desk and live preview.
        editor_outer,editor=scroll_panel(area,width=300);editor_outer.pack(side="left",fill="y",padx=4)
        # Selected portrait is the visual anchor for enhancement work. Keeping
        # it directly above the controls avoids hunting between side panels.
        self.preview_images={}
        Label(editor,text="SELECTED PHOTO PREVIEW",font=("Segoe UI",10,"bold"),fg=THEME["green"],bg=THEME["panel"]).pack(fill="x")
        self.selected_photo_focus=Label(editor,bg="#20242b",bd=2,relief="groove",height=6);self.selected_photo_focus.pack(fill="x",pady=(2,5))
        Label(editor,text="EDIT & ENHANCEMENT",font=("Segoe UI",14,"bold"),fg=THEME["cyan"],bg=THEME["panel"]).pack(fill="x",pady=(0,3))
        self.state=StringVar();self.action_status=StringVar(value="Ready — koi pending change nahi")
        Label(editor,textvariable=self.state,font=("Segoe UI",11,"bold"),fg=THEME["green"],bg=THEME["panel"]).pack()
        Label(editor,textvariable=self.action_status,font=("Segoe UI",8,"bold"),fg=THEME["text"],bg=THEME["panel"],wraplength=340).pack(pady=(0,5))
        self.adjust_vars={name:IntVar(value=self.settings[self.active][name]) for name in ADJUSTMENTS}
        slider_box=Frame(editor,bg=THEME["surface"],bd=1,relief="solid",padx=7,pady=4);slider_box.pack(fill="x",pady=3)
        for name in ADJUSTMENTS:
            row=Frame(slider_box,bg=THEME["surface"]);row.pack(fill="x")
            Label(row,text=name,width=11,anchor="w",font=("Segoe UI",8,"bold"),bg=THEME["surface"]).pack(side="left")
            scale=Scale(row,from_=-100,to=100,orient="horizontal",showvalue=True,variable=self.adjust_vars[name],length=195,resolution=1)
            scale.pack(side="left",fill="x",expand=True);scale.bind("<ButtonRelease-1>",self.commit_adjustments)
        action_grid=Frame(editor,bg=THEME["panel"]);action_grid.pack(fill="x",pady=4)
        actions=(("✂ AUTO CROP",self.auto),("⚡ SMART AUTO FIX",self.smart_auto_fix),("☀ AUTO LIGHT",self.auto_light),("✨ APPLY PREVIEW",self.apply_enhancements),("APPLY TO ALL PHOTOS",self.apply_to_all_photos),("RESET ACTIVE",self.reset_adjustments))
        for index,(title,command) in enumerate(actions):
            button=Button(action_grid,text=title,command=command);button._cinematic_size=10;button.grid(row=index//2,column=index%2,sticky="nsew",padx=3,pady=3)
        action_grid.grid_columnconfigure(0,weight=1);action_grid.grid_columnconfigure(1,weight=1)
        from .detection import PRESETS,infer_preset
        self.preset_name=StringVar(value=item.get("preset",infer_preset(item["path"].name)))
        self.preset_combo=ttk.Combobox(editor,textvariable=self.preset_name,state="readonly",values=("Auto Detect",)+tuple(PRESETS)+tuple(app.read_settings().get("card_presets",{})))
        self.preset_combo.pack(fill="x");self.preset_combo.bind("<<ComboboxSelected>>",self.preset_changed)
        Button(editor,text="SAVE / RENAME PRESET",command=self.save_card_preset).pack(fill="x",pady=3)
        Button(editor,text="RE-DETECT PHOTO",command=self.redetect_photo).pack(fill="x",pady=3)
        Button(editor,text="CONFIRM PHOTO BOUNDARY",command=self.confirm_photo_boundary).pack(fill="x",pady=3)
        Button(editor,text="PHOTO BOX BATCH TOOLS",command=self.open_photo_box_tools).pack(fill="x",pady=3)
        compare=Button(editor,text="PRESS & HOLD — ORIGINAL / ENHANCED",bg=THEME["blue_dark"],fg="white")
        compare.pack(fill="x",pady=3);compare.bind("<ButtonPress-1>",lambda e:self.set_compare(True));compare.bind("<ButtonRelease-1>",lambda e:self.set_compare(False))
        undo_box=Frame(editor,bg=THEME["surface"],bd=1,relief="solid");undo_box.pack(fill="x",pady=3)
        Button(undo_box,text="↶ UNDO",command=self.undo).pack(side="left",fill="x",expand=True);Button(undo_box,text="REDO ↷",command=self.redo).pack(side="left",fill="x",expand=True,padx=(4,0))
        controls_outer,controls=scroll_panel(area,width=280);controls_outer.pack(side="right",fill="y")
        preview_panel=Frame(controls,bg=THEME["surface"],bd=1,relief="solid",padx=8,pady=6);preview_panel.pack(fill="x");Label(preview_panel,text="SELECTED FILE — LIVE PREVIEW",font=("Segoe UI",11,"bold"),fg=THEME["cyan"],bg=THEME["surface"]).pack(pady=(0,4));self.preview_labels={}
        for name,color in (("front","#ef3e42"),("back","#36a4ff"),("photo","#13a85f")):
            Label(preview_panel,text=name.upper(),fg=color,font=("Segoe UI",9,"bold"),bg=THEME["surface"]).pack(anchor="w")
            preview=Label(preview_panel,bg="#20242b",bd=2,relief="groove");preview.pack(fill="x",pady=(0,8));self.preview_labels[name]=preview
        self.last_rotate=self.rotate_back.get();Checkbutton(controls,text="AUTO ROTATE BACK 180°",variable=self.rotate_back,command=self.rotate_changed).pack(pady=(4,2))
        Label(controls,text="Tip: Ctrl + Mouse Wheel Se Zoom In/Out Karein • Space + Drag Se Pan Karein",font=("Segoe UI",8,"bold"),fg=THEME["cyan"]).pack(pady=(3,2))
        zoom_column=Frame(controls,bg=THEME["panel"]);zoom_column.pack(fill="x",pady=3)
        self.editor_zoom=DoubleVar(value=round(self.scale*100))
        Scale(zoom_column,from_=400,to=25,resolution=5,orient="vertical",variable=self.editor_zoom,length=120,command=lambda value:self.set_zoom_percent(value)).pack()
        Label(zoom_column,text="Ctrl + Mouse Wheel Se Zoom In/Out Karein",font=("Segoe UI",8,"bold"),fg=THEME["cyan"],bg=THEME["panel"],wraplength=245).pack(fill="x")
        viewrow=Frame(controls);viewrow.pack(fill="x",pady=2)
        Button(viewrow,text="FIT",command=self.fit_view,width=6).pack(side="left");Button(viewrow,text="100%",command=self.actual_size,width=6).pack(side="left",padx=3);Button(viewrow,text="RESET",command=self.fit_view,width=6).pack(side="left")
        fill_button_row(viewrow,10)
        Button(controls,text="RESET CROP BOXES",command=self.reset_crop).pack(fill="x",pady=2);Button(controls,text="RESET ALL CHANGES",command=self.reset_all).pack(fill="x",pady=2);Button(controls,text="✓ APPLY CHANGES & RETURN",command=self.apply,font=("Segoe UI",11,"bold")).pack(fill="x",pady=(5,2));Button(controls,text="CANCEL",command=self.cancel).pack(fill="x",pady=2);apply_cinematic_theme(self.window);self.render_page();self.draw();self.update_previews();self.window.protocol("WM_DELETE_WINDOW",self.cancel)
    def cv(self,b):return tuple(round(v*self.scale+(self.offset[0] if n%2==0 else self.offset[1])) for n,v in enumerate(b))
    def inv(self,x,y):return ((x-self.offset[0])/self.scale,(y-self.offset[1])/self.scale)
    def render_page(self):
        page=self.item["page"];scale=self.scale;ox,oy=self.offset
        width=max(40,self.canvas.winfo_width());height=max(40,self.canvas.winfo_height())
        visible=(max(0,int(-ox/scale)),max(0,int(-oy/scale)),min(page.width,math.ceil((width-ox)/scale)),min(page.height,math.ceil((height-oy)/scale)))
        if visible[2]<=visible[0] or visible[3]<=visible[1]:self.canvas.delete("page");self._render_tile=None;return
        cached=getattr(self,"_render_tile",None)
        if cached and cached[0]==scale and cached[1][0]<=visible[0] and cached[1][1]<=visible[1] and cached[1][2]>=visible[2] and cached[1][3]>=visible[3]:
            box=cached[1]
        else:
            margin=round(180/scale)
            box=(max(0,visible[0]-margin),max(0,visible[1]-margin),min(page.width,visible[2]+margin),min(page.height,visible[3]+margin))
            size=(max(1,round((box[2]-box[0])*scale)),max(1,round((box[3]-box[1])*scale)))
            image=page.crop(box).resize(size,Image.Resampling.BILINEAR);self.photo=ImageTk.PhotoImage(image);self._render_tile=(scale,box)
            self.canvas.delete("page");self.canvas.create_image(0,0,anchor="nw",image=self.photo,tags="page")
        self.canvas.coords("page",ox+box[0]*scale,oy+box[1]*scale)
        self.canvas.tag_lower("page")
    def snapshot(self):return (dict(self.boxes),{k:dict(v) for k,v in self.settings.items()},self.rotate_back.get())
    def restore(self,state):
        self.photo_confirmed=False;self.photo_manual_changed=False
        self.boxes={k:tuple(v) for k,v in state[0].items()};self.settings={k:dict(v) for k,v in state[1].items()};self.rotate_back.set(state[2]);self.last_rotate=state[2];self.load_adjustments();self.draw();self.update_previews();self.dirty=True
    def remember(self):self.undo_stack.append(self.snapshot());self.undo_stack=self.undo_stack[-60:];self.redo_stack.clear()
    def undo(self,e=None):
        if self.undo_stack:self.redo_stack.append(self.snapshot());self.restore(self.undo_stack.pop())
        return "break"
    def redo(self,e=None):
        if self.redo_stack:self.undo_stack.append(self.snapshot());self.restore(self.redo_stack.pop())
        return "break"
    def zoom_wheel(self,e):self.zoom_at(e.x,e.y,1.12 if e.delta>0 else 1/1.12);return "break"
    def set_zoom_percent(self,value):
        target=max(self.fit_scale*.55,min(4.0,float(value)/100));cx=max(1,self.canvas.winfo_width())/2;cy=max(1,self.canvas.winfo_height())/2
        old=self.scale
        if abs(target-old)<1e-6:return
        ix,iy=self.inv(cx,cy);self.scale=target;self.offset=[cx-ix*target,cy-iy*target];self.render_page();self.draw()

    def zoom_at(self,x,y,factor):
        old=self.scale;new=max(self.fit_scale*.55,min(4.0,old*factor))
        if abs(new-old)<1e-6:return
        ix,iy=self.inv(x,y);self.scale=new;self.offset=[x-ix*new,y-iy*new];
        if hasattr(self,"editor_zoom"):self.editor_zoom.set(round(new*100))
        self.render_page();self.draw()
    def fit_view(self):
        self.fit_scale=min(max(20,self.canvas.winfo_width()-24)/self.item["page"].width,max(20,self.canvas.winfo_height()-24)/self.item["page"].height,1.)
        self.scale=self.fit_scale;self.offset=[12.0,12.0];self.render_page();self.draw()
    def actual_size(self):
        cx=max(1,self.canvas.winfo_width())/2;cy=max(1,self.canvas.winfo_height())/2;ix,iy=self.inv(cx,cy);self.scale=1.0;self.offset=[cx-ix,cy-iy];self.render_page();self.draw()
    def space_press(self,e=None):self.space_down=True;self.canvas.configure(cursor="fleur");return "break"
    def space_release(self,e=None):self.space_down=False;self.pan_start=None;self.canvas.configure(cursor="");return "break"
    def draw(self):
        self.canvas.delete("box")
        for name,color in (("front","#ef3e42"),("back","#36a4ff"),("photo","#13a85f")):
            x1,y1,x2,y2=self.cv(self.boxes[name]);self.canvas.create_rectangle(x1,y1,x2,y2,outline=color,width=4 if name==self.active else 2,tags="box");self.canvas.create_text(x1+7,y1+12,anchor="w",text=name.upper(),fill=color,font=("Segoe UI",10,"bold"),tags="box")
        self.state.set("ACTIVE: "+self.active.upper())
    def load_adjustments(self):
        for name in ADJUSTMENTS:self.adjust_vars[name].set(self.settings[self.active][name])
    def commit_adjustments(self,event=None):
        before=self.snapshot();new={name:self.adjust_vars[name].get() for name in ADJUSTMENTS}
        if new!=self.settings[self.active]:self.undo_stack.append(before);self.redo_stack.clear();self.settings[self.active]=new;self.dirty=True
        self.action_status.set("Enhancement changed — APPLY pending");self.update_previews()
    def apply_enhancements(self):
        self.commit_adjustments();self.action_status.set(f"{self.active.upper()} enhancements applied to preview")
    def apply_enhancements_selected(self):
        self.commit_adjustments();values=dict(self.settings[self.active])
        for target in self.selected_items:
            target.setdefault("adjustments",{})[self.active]=dict(values)
            target["front"],target["back"],target["photo"]=processed_cards(target)
        self.action_status.set(f"{self.active.upper()} enhancements applied to {len(self.selected_items)} selected file(s)");self.done()
    def apply_to_all_photos(self):
        """Copy only enhancement values; never overwrite another card's crop."""
        if self.active!="photo":
            themed_message(self.window,"SELECT PHOTO FIRST","Photo Tab Ya Green Photo Box Select Karein, Phir Same Enhancement Sabhi Selected Photos Par Lagayein.","warning",("SELECT PHOTO",));self.active="photo";self.load_adjustments();self.draw();self.update_previews();return
        self.commit_adjustments()
        if len(self.selected_items)>1:
            choice=themed_message(self.window,"APPLY TO ALL PHOTOS",f"Current Photo Ki Enhancement {len(self.selected_items)} Selected Photos Par Apply Karein?\n\nHar Photo Ka Crop Box Alag Aur Safe Rahega.","warning",("APPLY TO ALL PHOTOS","CANCEL"))
            if choice!="APPLY TO ALL PHOTOS":return
        values=dict(self.settings["photo"])
        for target in self.selected_items:
            target.setdefault("adjustments",{})["photo"]=dict(values)
            target["front"],target["back"],target["photo"]=processed_cards(target)
        self.item.setdefault("adjustments",{})["photo"]=dict(values);self.action_status.set(f"Same Photo Enhancement {len(self.selected_items)} Selected Photo(s) Par Apply Ho Gayi");self.done()
    def apply_photo_box_to_all(self):
        """Map one Photo box proportionally into every selected Front card."""
        if self.active!="photo":
            themed_message(self.window,"SELECT PHOTO BOX FIRST","Green Photo Box Select Aur Adjust Karein, Phir Bounding Box Sabhi Selected Cards Par Lagayein.","warning",("SELECT PHOTO",));self.active="photo";self.load_adjustments();self.draw();self.update_previews();return
        try:map_relative_box(self.boxes["photo"],self.boxes["front"],self.boxes["front"])
        except ValueError:
            themed_message(self.window,"INVALID PHOTO BOX","Photo Box Front Card Ke Andar Hona Chahiye. Box Sahi Karke Dobara Apply Karein.","error",("REVIEW PHOTO",));return
        candidates=[];skipped=[]
        for target in self.selected_items:
            if matching_photo_layout(self.item,target):candidates.append((target,map_relative_box(self.boxes["photo"],self.boxes["front"],target["boxes"]["front"])))
            else:skipped.append(target)
        if not candidates:
            themed_message(self.window,"NO MATCHING LAYOUT","Selected Cards Me Current Card Jaisa Matching Layout Nahi Mila.","warning",("CLOSE",));return
        if not photo_box_batch_preview_dialog(self.window,self.item,candidates,skipped):return
        undo=[];changed=0
        for target,mapped in candidates:
            undo.append((target,tuple(target["boxes"]["photo"]),target.get("photo_confidence",0),target.get("photo_review",True),target.get("photo_box_manual",False)))
            target["boxes"]["photo"]=mapped;target["photo_confidence"]=100;target["photo_review"]=False;target["photo_box_manual"]=True;confirm_photo(target)
            target["front"],target["back"],target["photo"]=processed_cards(target);changed+=1
        self.bulk_photo_box_undo.append(undo);self.bulk_photo_box_undo=self.bulk_photo_box_undo[-20:]
        self.boxes["photo"]=self.item["boxes"]["photo"];self.dirty=True;self.draw();self.update_previews();self.action_status.set(f"Photo Bounding Box {changed} Selected Card(s) Par Apply Ho Gaya");self.done()
    def open_photo_box_tools(self):
        dialog=Toplevel(self.window);dialog.title("PHOTO BOX BATCH TOOLS");dialog.transient(self.window);dialog.grab_set();dialog.resizable(True,True);apply_window_icon(dialog)
        body=Frame(dialog,bg=THEME["panel"],padx=18,pady=16);body.pack(fill="both",expand=True);Label(body,text="PHOTO BOX BATCH TOOLS",font=("Segoe UI",18,"bold"),bg=THEME["panel"],fg=THEME["cyan"]).pack(fill="x",pady=(0,5));Label(body,text="Photo Box Select Aur Adjust Karein • Preview Check Karein • Phir Matching Cards Par Apply Karein",font=("Segoe UI",10,"bold"),bg=THEME["panel"],fg=THEME["text"],wraplength=650).pack(fill="x",pady=(0,12))
        for title,help_text,command in (("APPLY BOX TO ALL SELECTED","Matching Cards Par Same Relative Box Lagayein",self.apply_photo_box_to_all),("SAVE PHOTO BOX PRESET","Current Layout Ka Corrected Box Save Karein",self.save_photo_box_preset),("LOAD PHOTO BOX PRESET","Current Layout Ka Saved Box Load Karein",self.load_photo_box_preset),("UNDO APPLY TO ALL","Pichhla Batch Box Change Wapas Karein",self.undo_photo_box_to_all)):
            button=Button(body,text=f"{title}\n{help_text}",command=lambda fn=command:(dialog.destroy(),fn()));button._cinematic_size=11;button.pack(fill="x",pady=4)
        Button(body,text="CLOSE",command=dialog.destroy).pack(fill="x",pady=(10,0));dialog.bind("<Escape>",lambda _e:dialog.destroy());apply_cinematic_theme(dialog);_center_dialog(dialog,self.window,720,570);dialog.minsize(620,480)
    def _photo_box_preset_data(self):
        fx1,fy1,fx2,fy2=self.boxes["front"];px1,py1,px2,py2=self.boxes["photo"];fw=max(1,fx2-fx1);fh=max(1,fy2-fy1)
        return [round((px1-fx1)/fw,6),round((py1-fy1)/fh,6),round((px2-fx1)/fw,6),round((py2-fy1)/fh,6)]
    def _photo_layout_key(self):
        bits=photo_layout_signature(self.item["page"],self.boxes["front"]);return f"{round((self.boxes['front'][2]-self.boxes['front'][0])/max(1,self.boxes['front'][3]-self.boxes['front'][1]),2)}:"+"".join("1" if bit else "0" for bit in bits)
    def save_photo_box_preset(self):
        try:data=self._photo_box_preset_data()
        except Exception as exc:friendly_problem(self.window,"PRESET NOT SAVED",str(exc),"Photo Box Front Card Ke Andar Set Karein.");return
        if not (0<=data[0]<data[2]<=1 and 0<=data[1]<data[3]<=1):
            themed_message(self.window,"INVALID PHOTO BOX","Preset Save Karne Se Pehle Photo Box Front Ke Andar Rakhein.","error",("REVIEW PHOTO",));return
        settings=self.app.read_settings();presets=settings.setdefault("photo_box_presets",{});presets[self._photo_layout_key()]={"box":data,"label":"Maha ID Photo Box"}
        if self.app.write_settings(settings):themed_message(self.window,"PHOTO BOX PRESET SAVED","Current Card Layout Ka Photo Box Preset Safely Save Ho Gaya.","success",("CLOSE",))
    def load_photo_box_preset(self):
        preset=self.app.read_settings().get("photo_box_presets",{}).get(self._photo_layout_key())
        if not preset:
            themed_message(self.window,"PRESET NOT FOUND","Is Card Layout Ke Liye Saved Photo Box Preset Nahi Mila.","warning",("CLOSE",));return
        fx1,fy1,fx2,fy2=self.boxes["front"];relative=preset.get("box",[])
        if len(relative)!=4:themed_message(self.window,"INVALID PRESET","Saved Preset Adhura Hai. Naya Preset Save Karein.","error",("CLOSE",));return
        self.remember();fw,fh=fx2-fx1,fy2-fy1;self.boxes["photo"]=confine((fx1+relative[0]*fw,fy1+relative[1]*fh,fx1+relative[2]*fw,fy1+relative[3]*fh),self.boxes["front"]);self.active="photo";self.dirty=True;self.draw();self.load_adjustments();self.update_previews();self.action_status.set("Saved Photo Box Preset Preview Par Load Ho Gaya — Apply Changes & Exit Karein")
    def undo_photo_box_to_all(self):
        if not self.bulk_photo_box_undo:
            themed_message(self.window,"NOTHING TO UNDO","Abhi Koi Apply-To-All Bounding Box Operation Nahi Hai.","info",("CLOSE",));return
        records=self.bulk_photo_box_undo.pop()
        for target,box,confidence,review,manual in records:
            target["boxes"]["photo"]=box;target["photo_confidence"]=confidence;target["photo_review"]=review;target["photo_box_manual"]=manual;target["front"],target["back"],target["photo"]=processed_cards(target)
        self.boxes["photo"]=tuple(self.item["boxes"]["photo"]);self.dirty=True;self.draw();self.update_previews();self.done();self.action_status.set(f"{len(records)} Photo Box Changes Undo Ho Gaye")
    def auto_light(self):
        self.remember()
        preview=self.item["page"].crop(self.boxes[self.active]);self.settings[self.active].update(smart_light_adjustments(preview))
        self.load_adjustments();self.update_previews();self.dirty=True;self.action_status.set(f"{self.active.upper()} Auto Light ready — face identity unchanged")
    def smart_auto_fix(self):
        """One safe click: detect boxes and apply conservative natural light."""
        self.remember();front,back=maha_seed(self.item["page"])
        self.boxes["front"]=refine_card_box(self.item["page"],front);self.boxes["back"]=refine_card_box(self.item["page"],back);self.boxes["photo"]=refine_photo_box(self.item["page"],self.boxes["front"])
        self.settings["photo"].update(smart_light_adjustments(self.item["page"].crop(self.boxes["photo"])))
        self.load_adjustments();self.dirty=True;self.draw();self.update_previews();self.action_status.set("Smart Auto Fix complete — crop + natural photo light ready")
    def set_compare(self,original):
        self.compare_original=bool(original);self.action_status.set("ORIGINAL preview" if original else "ENHANCED preview");self.update_previews()
    def reset_adjustments(self):
        self.remember()
        self.settings[self.active]=default_adjustments();self.load_adjustments();self.update_previews();self.dirty=True
        self.action_status.set("Active enhancement reset — APPLY pending")
    def reset_crop(self):
        self.remember();self.photo_confirmed=False;self.boxes={k:tuple(v) for k,v in self.item.get("original_boxes",self.opening_state[0]).items()};self.dirty=True;self.draw();self.update_previews();self.action_status.set("Crop restored to opening position")
    def reset_all(self):
        self.remember();self.photo_confirmed=False;self.restore((dict(self.item.get("original_boxes",self.opening_state[0])),{k:default_adjustments() for k in ("front","back","photo")},False));self.last_rotate=self.rotate_back.get();self.action_status.set("All changes restored to opening state")
    def rotate_changed(self):
        new=self.rotate_back.get();self.rotate_back.set(self.last_rotate);self.remember();self.rotate_back.set(new);self.last_rotate=new;self.dirty=True;self.update_previews()
    def hit(self,x,y):
        # Photo first: clicking the green rectangle must never also select Front.
        for name in ("photo","front","back"):
            x1,y1,x2,y2=self.cv(self.boxes[name])
            if x1-9<=x<=x2+9 and y1-9<=y<=y2+9:return name
    def down(self,e):
        if self.space_down:
            self.drag="pan";self.pan_start=(e.x,e.y);self.pan_origin=tuple(self.offset);return
        found=self.hit(e.x,e.y)
        if not found:return
        self.remember()
        self.active=found;x1,y1,x2,y2=self.cv(self.boxes[found]);self.drag="move" if min(abs(e.x-x1),abs(e.x-x2),abs(e.y-y1),abs(e.y-y2))>=16 else ("tl" if e.x<(x1+x2)/2 and e.y<(y1+y2)/2 else "tr" if e.y<(y1+y2)/2 else "bl" if e.x<(x1+x2)/2 else "br");self.start=self.inv(e.x,e.y);self.original=self.boxes[found];self.draw();self.load_adjustments();self.update_previews()
    def move(self,e):
        if not self.drag:return
        if self.drag=="pan":
            self.offset=[self.pan_origin[0]+e.x-self.pan_start[0],self.pan_origin[1]+e.y-self.pan_start[1]];self.render_page();self.draw();return
        x,y=self.inv(e.x,e.y);sx,sy=self.start;x1,y1,x2,y2=self.original
        if self.drag=="move":b=(x1+x-sx,y1+y-sy,x2+x-sx,y2+y-sy)
        else:b=(x if "l" in self.drag else x1,y if "t" in self.drag else y1,x if "r" in self.drag else x2,y if "b" in self.drag else y2)
        self.boxes[self.active]=clamp(tuple(round(v) for v in b),self.item["page"].width,self.item["page"].height);self.dirty=True;self.draw()
    def up(self,e):
        was_edit=self.drag and self.drag!="pan";self.photo_manual_changed=bool(was_edit and self.active=="photo") or getattr(self,"photo_manual_changed",False);self.photo_confirmed=False if was_edit else getattr(self,"photo_confirmed",False);self.drag=None;self.pan_start=None
        if was_edit:self.update_previews()
    def nudge(self,dx,dy):
        self.photo_confirmed=False;self.photo_manual_changed=self.active=="photo";self.remember()
        x1,y1,x2,y2=self.boxes[self.active];self.boxes[self.active]=clamp((x1+dx,y1+dy,x2+dx,y2+dy),self.item["page"].width,self.item["page"].height);self.dirty=True;self.draw();self.update_previews()
    def auto(self):
        self.remember()
        front,back=maha_seed(self.item["page"]);self.boxes["front"]=refine_card_box(self.item["page"],front);self.boxes["back"]=refine_card_box(self.item["page"],back);self.boxes["photo"]=refine_photo_box(self.item["page"],self.boxes["front"]);self.dirty=True;self.draw();self.update_previews()
    def update_previews(self):
        """Refresh tiny previews only on select/release, never each mouse move."""
        for name,label in self.preview_labels.items():
            crop=self.item["page"].crop(self.boxes[name]);crop.thumbnail((660,320));crop=crop if self.compare_original else adjust_image(crop,self.settings[name]);crop.thumbnail((330,145) if name!="photo" else (155,155),Image.Resampling.BILINEAR)
            photo=ImageTk.PhotoImage(crop);self.preview_images[name]=photo;label.configure(image=photo)
            if name=="photo" and hasattr(self,"selected_photo_focus"):
                focus=self.item["page"].crop(self.boxes["photo"]);focus.thumbnail((320,210));focus=focus if self.compare_original else adjust_image(focus,self.settings["photo"]);focus.thumbnail((320,105),Image.Resampling.LANCZOS)
                focus_photo=ImageTk.PhotoImage(focus);self.preview_images["photo_focus"]=focus_photo;self.selected_photo_focus.configure(image=focus_photo)
    def apply(self):
        if getattr(self,"applying",False):return
        self.commit_adjustments()
        changed=tuple(self.boxes["photo"])!=tuple(self.item["boxes"]["photo"])
        previous=photo_geometry(self.item)
        candidate=dict(self.item);candidate["boxes"]=dict(self.boxes);candidate["adjustments"]={k:dict(v) for k,v in self.settings.items()}
        if previous!=photo_geometry(candidate):invalidate_photo(candidate)
        if (changed and getattr(self,"photo_manual_changed",False)) or getattr(self,"photo_confirmed",False):
            try:confirm_photo(candidate)
            except ValueError as exc:messagebox.showwarning("Photo Boundary",str(exc),parent=self.window);return
        candidate["rotate_back"]=self.rotate_back.get()
        self.applying=True;self.action_status.set("Applying changes…")
        def ready(result,error):
            self.applying=False
            if error:messagebox.showerror("Apply Changes",str(error),parent=self.window);return
            candidate["front"],candidate["back"],candidate["photo"]=result;self.item.clear();self.item.update(candidate)
            self.window.destroy();self.restore_parent();self.done()
        self.app.run_background(lambda:processed_cards(candidate),ready)
    def preset_changed(self,_=None):
        from .detection import PRESETS
        name=self.preset_name.get();self.item["preset"]=name
        self.photo_confirmed=False;self.photo_manual_changed=False
        custom=dict(PRESETS);custom.update(self.app.read_settings().get("card_presets",{}))
        def ready(result,error):
            if error:messagebox.showwarning("Preset",str(error),parent=self.window);return
            self.remember();self.boxes["photo"]=result[0];self.dirty=True;self.draw();self.update_previews()
        self.app.run_background(lambda:refine_photo_box_with_confidence(self.item["page"],self.boxes["front"],name,custom),ready)
    def save_card_preset(self):
        name=simpledialog.askstring("Save / Rename Preset","Preset name (existing name updates it):",initialvalue=self.preset_name.get(),parent=self.window)
        if not name:return
        fx,fy,fr,fb=self.boxes["front"];x,y,r,b=self.boxes["photo"]
        if not (fx<=x<r<=fr and fy<=y<b<=fb):return
        margin=.04
        bounds=[max(0,(x-fx)/(fr-fx)-margin),max(0,(y-fy)/(fb-fy)-margin),min(1,(r-fx)/(fr-fx)+margin),min(1,(b-fy)/(fb-fy)+margin)]
        settings=self.app.read_settings();settings.setdefault("card_presets",{})[name.strip()]=bounds
        if self.app.write_settings(settings):
            self.preset_combo.configure(values=tuple(self.preset_combo.cget("values"))+(name.strip(),));self.preset_name.set(name.strip())
    def confirm_photo_boundary(self):
        test={"boxes":self.boxes}
        try:confirm_photo(test)
        except ValueError as exc:messagebox.showwarning("Photo Boundary",str(exc),parent=self.window);return
        self.photo_confirmed=True;self.dirty=True;self.action_status.set("PHOTO ✓ VERIFIED — Apply changes to save")
    def redetect_photo(self):
        self.photo_confirmed=False;self.photo_manual_changed=False
        def ready(result,error):
            if error:messagebox.showwarning("Detection",str(error),parent=self.window);return
            self.remember();self.boxes["photo"]=result[0];self.dirty=True;self.draw();self.update_previews()
        self.app.run_background(lambda:refine_photo_box_with_confidence(self.item["page"],self.boxes["front"]),ready)
    def cancel(self):
        if getattr(self,"applying",False):return
        if self.dirty and not messagebox.askyesno("Discard Changes?","Apply nahi kiye gaye crop/settings changes discard karne hain?",parent=self.window):return
        self.window.destroy();self.restore_parent()
    def go_home(self):
        self.cancel()
    def restore_parent(self):
        if self.parent:
            show_maximized(self.parent)

class PrintPositionDialog:
    """Persistent Windows 4x6 position profile; size always stays locked."""
    def __init__(self,app,parent,refresh):
        self.app,self.refresh=app,refresh;self.window=Toplevel(parent);self.window.title("SEEMA DIGITAL — 4×6 Print Position");self.window.transient(parent);self.window.grab_set();self.window.resizable(False,False)
        apply_window_icon(self.window)
        self.x=DoubleVar(value=app.x_offset_mm);self.y=DoubleVar(value=app.y_offset_mm);body=Frame(self.window,padx=22,pady=18);body.pack()
        Label(body,text="EPSON L805 — 4×6 PRINTER PROFILE",font=("Segoe UI",13,"bold"),fg="#123b72").grid(row=0,column=0,columnspan=3,pady=(0,12))
        Label(body,text="Card size is locked at 90 × 57 mm",font=("Segoe UI",10,"bold"),fg="#17643b").grid(row=1,column=0,columnspan=3,pady=(0,12))
        Label(body,text="X position (mm)",anchor="w").grid(row=2,column=0,sticky="w",pady=5);Entry(body,textvariable=self.x,width=10,justify="center").grid(row=2,column=1,padx=8);Label(body,text="− Left / + Right").grid(row=2,column=2,sticky="w")
        Label(body,text="Y position (mm)",anchor="w").grid(row=3,column=0,sticky="w",pady=5);Entry(body,textvariable=self.y,width=10,justify="center").grid(row=3,column=1,padx=8);Label(body,text="− Up / + Down").grid(row=3,column=2,sticky="w")
        Label(body,text="Recommended first test: X 0.0 mm, Y +3.0 mm\nAdobe: Actual Size 100% • Borderless OFF",justify="left",fg="#555").grid(row=4,column=0,columnspan=3,pady=12)
        row=Frame(body);row.grid(row=5,column=0,columnspan=3)
        Button(row,text="LIVE APPLY",command=self.apply,width=13,bg="#287b9e",fg="white").pack(side="left",padx=3);Button(row,text="SAVE PROFILE",command=self.save,width=14,bg="#189451",fg="white").pack(side="left",padx=3);Button(row,text="RESET",command=self.reset,width=10).pack(side="left",padx=3);Button(row,text="CLOSE",command=self.window.destroy,width=10).pack(side="left",padx=3);fill_button_row(row,11);apply_cinematic_theme(self.window)
    def values(self):
        try:return float(self.x.get()),float(self.y.get())
        except Exception:messagebox.showerror("Invalid Position","X/Y me valid number likhen, jaise 0 ya 3.0",parent=self.window);return None
    def apply(self):
        values=self.values()
        if values:self.app.set_print_position(*values,save=False);self.x.set(self.app.x_offset_mm);self.y.set(self.app.y_offset_mm);self.refresh()
    def save(self):
        values=self.values()
        if values:self.app.set_print_position(*values,save=True);self.x.set(self.app.x_offset_mm);self.y.set(self.app.y_offset_mm);self.refresh();messagebox.showinfo("Profile Saved","Windows 4×6 position profile saved.",parent=self.window)
    def reset(self):self.x.set(0.0);self.y.set(0.0);self.app.set_print_position(0,0,save=True);self.refresh()

class BatchReview:
    def __init__(self,app,items,mode):
        self.has_selection=False;self.selection_buttons=[];self.app,self.items,self.mode,self.index=app,items,mode,0;app.root.withdraw();self._a4_pages=None;self.move_cards=False;self.layout_drag=None;self.layout_undo_stack=[];self.layout_redo_stack=[];self.rotation_undo_stack=[];self.layout_dirty=False;self.busy=False;self.window=Toplevel(app.root);self.window.title("SEEMA DIGITAL — Maha ID Batch Review");full_screen(self.window)
        self.hgap_mm=DoubleVar(value=2.0 if mode=="a4pair4" else 0.0 if mode=="a4pair5" else 10.0);self.vgap_mm=DoubleVar(value=8.0 if mode=="a4pair4" else 1.2 if mode=="a4pair5" else 1.5);self.pair_gap_mm=DoubleVar(value=0.0)
        key="a4_pos_pair5" if mode=="a4pair5" else "a4_pos_pair" if mode=="a4pair4" else "a4_pos_back" if mode=="a4back" else "a4_pos_front";self.a4_key=key
        defaults=a4_five_pair_positions(len(items),self.vgap_mm.get()) if mode=="a4pair5" else a4_pair_positions(len(items),self.hgap_mm.get(),self.vgap_mm.get()) if mode=="a4pair4" else a4_grid_positions(len(items),self.hgap_mm.get(),self.vgap_mm.get())
        self.a4_positions=[tuple(item.get(key,defaults[i])) for i,item in enumerate(items)]
        apply_window_icon(self.window)
        title={"4x6":"MULTIPLE 4×6 PREVIEW","a4back":"MULTIPLE A4 BACK — 10 CARDS","a4":"MULTIPLE A4 FRONT — 10 CARDS","a4pair4":"4 CARD A4 — FRONT + BACK PAIRS","a4pair5":"A4 ME 5 CARD — ZERO FRONT/BACK GAP"}[mode]
        topbar=Frame(self.window,bg=THEME["surface"],padx=12,pady=7);topbar.pack(fill="x")
        back_button=Button(topbar,text="← BACK",command=self.go_home,width=11,bg=THEME["red"],fg="white");back_button._cinematic_size=12;back_button.pack(side="left")
        home_button=Button(topbar,text="🏠 HOME",command=self.go_home,width=11,bg=THEME["blue"],fg="white");home_button._cinematic_size=12;home_button.pack(side="left",padx=8)
        titles=Frame(topbar,bg=THEME["surface"]);titles.pack(side="left",fill="x",expand=True)
        Label(titles,text="SEEMA DIGITAL",font=("Arial Black",27,"bold"),fg=THEME["red"],bg=THEME["surface"]).pack()
        Label(titles,text=title,font=("Segoe UI",12,"bold"),fg=THEME["cyan"],bg=THEME["surface"]).pack()
        guide_tip(titles,"Tip: File List Me Kisi Bhi Card Par Click Karein • Ctrl + Mouse Wheel Se Preview Zoom Karein")
        Label(topbar,text="STEP 2/3\nPreview → Edit → Save",font=("Segoe UI",10,"bold"),fg=THEME["green"],bg=THEME["surface"],justify="right").pack(side="right")
        # Reserve this two-row command panel from the BOTTOM before creating
        # the expanding preview. This prevents controls being pushed below the
        # taskbar on 1366x768 and other short displays.
        command_panel=Frame(self.window,bg=THEME["bg"],bd=1,relief="solid",padx=8,pady=5);command_panel.pack(side="bottom",fill="x")
        primary=Frame(command_panel,bg=THEME["bg"]);primary.pack(fill="x",pady=(0,4))
        edit_outer,edit_group=action_group(primary,"EDIT & ENHANCEMENT");edit_outer.pack(side="left",fill="both",expand=True,padx=3)
        action_control(edit_group,"EDIT SELECTED CARD","Selected Card Sudharein",self.edit)
        action_control(edit_group,"AUTO LIGHT","Selected Photos Bright Karein",self.auto_light_selected)
        nav_outer,nav_group=action_group(primary,"PREVIEW & NAVIGATION");nav_outer.pack(side="left",fill="both",expand=True,padx=3)
        action_control(nav_group,"PREVIOUS CARD","Pichhla Card Dekhein",lambda:self.step(-1))
        action_control(nav_group,"NEXT CARD","Agla Card Dekhein",lambda:self.step(1))
        action_control(nav_group,"FIRST CARD","Pehle Card Par Jaayein",lambda:self.step(-len(self.items)))
        action_control(nav_group,"LAST CARD","Aakhri Card Par Jaayein",lambda:self.step(len(self.items)))
        output_outer,output_group=action_group(primary,"JPG OUTPUT");output_outer.pack(side="left",fill="both",expand=True,padx=3)
        action_control(output_group,"SAVE FINAL OUTPUT","Save As JPG / JPEG / PNG / TIFF / BMP / WEBP / PDF",self.save)
        action_control(output_group,"EXPORT QUALITY SETTINGS","Dpi Aur Quality Select Karein",self.choose_export_quality)

        layout_tools=Frame(command_panel,bg=THEME["bg"])
        position_outer,position_group=action_group(layout_tools,"CARD POSITION & ROTATION")
        if mode=="4x6":action_control(position_group,"PRINT POSITION","Print Jagah Set Karein",lambda:PrintPositionDialog(self.app,self.window,self.draw))
        self.move_button=None
        if mode!="4x6":
            self.move_button=action_control(position_group,"ENABLE CARD MOVE","Mouse Se Card Move Karein",self.toggle_move)
            action_control(position_group,"RESET CARD POSITIONS","Default Position Lagayein",self.reset_a4)
            action_control(position_group,"UNDO POSITION","Pichhla Position Wapas Karein",self.layout_undo)
            action_control(position_group,"REDO POSITION","Position Dobara Lagayein",self.layout_redo)
        if mode in ("a4pair5","a4back"):
            action_control(position_group,"ROTATE SELECTED BACK 180°","Selected Back Ko Ghumayein",self.rotate_selected_back)
            action_control(position_group,"UNDO SELECTED ROTATION","Pichhla Rotation Hatayein",self.undo_selected_rotation)
            action_control(position_group,"ROTATE ALL BACKS 180°","Sabhi Back Cards Ghumayein",lambda:self.rotate_all(True))
            action_control(position_group,"RESET ALL ROTATIONS","Sabhi Cards Seedhe Karein",lambda:self.rotate_all(False))

        secondary=Frame(command_panel,bg=THEME["bg"]);secondary.pack(fill="x")
        print_outer,print_group=action_group(secondary,"PRINT");print_outer.pack(side="left",fill="both",expand=True,padx=3)
        action_control(print_group,"PRINT CURRENT PAGE","Current Page Print Karein",self.print_current)
        action_control(print_group,"PRINT SELECTED CARDS","Selected Cards Ek Job Me Print Karein",self.print_selected)
        action_control(print_group,"PRINT ALL PAGES","Sabhi Pages Print Karein",self.print_all)
        pdf_outer,pdf_group=action_group(secondary,"PDF SAVE");pdf_outer.pack(side="left",fill="both",expand=True,padx=3)
        action_control(pdf_group,"SAVE SELECTED PDF","Selected Pages Pdf Me Save Karein",lambda:self.save_pdf(False))
        action_control(pdf_group,"SAVE ALL PDF","Sabhi Pages Ek Pdf Me Save Karein",lambda:self.save_pdf(True))
        gaps=Frame(command_panel);gaps.pack(fill="x",pady=(5,1))
        if mode=="4x6":
            Label(gaps,text="4×6 GAP CONTROL PREVIEW KE LEFT SIDE ME HAI",font=("Segoe UI",8,"bold"),fg=THEME["cyan"]).pack(side="left")
        elif mode=="a4pair5":
            Label(gaps,text="FRONT–BACK GAP: 0 mm LOCKED",font=("Segoe UI",8,"bold"),fg=THEME["green"]).pack(side="left")
            Label(gaps,text="5 CARD GAP — VERTICAL",font=("Segoe UI",8,"bold")).pack(side="left",padx=(18,0));self.vgap_scale=Scale(gaps,from_=0,to=3,resolution=.25,orient="horizontal",variable=self.vgap_mm,length=220,command=lambda v:self.gap_preview());self.vgap_scale.pack(side="left",padx=4)
            Button(gaps,text="AUTO FIT",command=self.auto_fit,width=11).pack(side="left",padx=7);Label(gaps,text="EACH SIDE 90×57 mm LOCKED",fg="#20d68b",font=("Segoe UI",8,"bold")).pack(side="left")
        else:
            Label(gaps,text="CARD GAP  HORIZONTAL",font=("Segoe UI",8,"bold")).pack(side="left");self.hgap_scale=Scale(gaps,from_=0,to=25,resolution=.5,orient="horizontal",variable=self.hgap_mm,length=180,command=lambda v:self.gap_preview());self.hgap_scale.pack(side="left",padx=4)
            Label(gaps,text="VERTICAL",font=("Segoe UI",8,"bold")).pack(side="left",padx=(10,0));self.vgap_scale=Scale(gaps,from_=0,to=50 if mode=="a4pair4" else 3,resolution=.5,orient="horizontal",variable=self.vgap_mm,length=180,command=lambda v:self.gap_preview());self.vgap_scale.pack(side="left",padx=4)
            Button(gaps,text="AUTO FIT",command=self.auto_fit,width=11).pack(side="left",padx=7);Label(gaps,text="PAIR LOCK: ON" if mode=="a4pair4" else "90×57 mm SIZE LOCK: ON",fg="#20d68b",font=("Segoe UI",8,"bold")).pack(side="left")
        Button(gaps,text="SAVE PRESET",command=self.save_layout_preset,width=13).pack(side="right",padx=3);Button(gaps,text="LOAD PRESET",command=self.load_layout_preset,width=13).pack(side="right",padx=3)
        # Every command row fills the complete laptop width; no dead strip is
        # left beside fixed-width buttons when Windows resolution changes.
        fill_button_row(primary,11);fill_button_row(layout_tools,10);fill_button_row(secondary,10)
        self.status=StringVar();Label(command_panel,textvariable=self.status,fg="#123b72",font=("Segoe UI",9,"bold"),anchor="w").pack(fill="x",pady=(5,0))
        body=Frame(self.window);body.pack(fill="both",expand=True,padx=10);left_column=Frame(body,width=315,bg=THEME["panel"],padx=5,pady=5);left_column.pack(side="left",fill="y");left_column.pack_propagate(False);self.list=Listbox(left_column,width=34,font=("Segoe UI",10),selectbackground="#e88d00");self.list.pack(fill="both",expand=True)
        self.list.configure(selectmode="extended",exportselection=False);self.list_row_to_item={};self.item_to_list_row={};per_page=5 if mode=="a4pair5" else 4 if mode=="a4pair4" else 10 if mode!="4x6" else len(items)
        for n,item in enumerate(items):
            if mode!="4x6" and n%per_page==0:self.list.insert("end",f"══ A4 PAGE {n//per_page+1} ══");self.list.itemconfigure("end",fg=THEME["cyan"],selectbackground=THEME["panel_alt"])
            row=self.list.size();position=f"P{n//per_page+1}-{n%per_page+1:02d}" if mode!="4x6" else f"4×6-{n+1:02d}";label=item.get("source_label",item["path"].name);display=label if len(label)<=34 else label[:31]+"…";self.list.insert("end",f"{position}  {display}");self.list_row_to_item[row]=n;self.item_to_list_row[n]=row
        self.list.bind("<<ListboxSelect>>",self.select)
        Button(left_column,text="CLEAR SELECTION",command=self.clear_selection).pack(fill="x")
        compact_outer,compact_group=action_group(left_column,"POSITION & ROTATION");compact_outer.pack(fill="x",pady=(6,2))
        def compact_action(title,help_text,command):
            button=action_control(compact_group,title,help_text,command);button.master.pack_configure(side="top",fill="x");return button
        self.move_button=None
        if mode=="4x6":
            compact_action("PRINT SETTINGS","Printer Aur Position Set Karein",lambda:PrintPositionDialog(self.app,self.window,self.draw))
            Label(compact_group,text="FRONT–BACK GAP",font=("Segoe UI",8,"bold"),fg=THEME["cyan"],bg=THEME["panel"]).pack()
            self.gap_scale=Scale(compact_group,from_=20,to=0,resolution=.5,orient="vertical",variable=self.pair_gap_mm,length=125,command=lambda v:self.gap_preview(),troughcolor=THEME["cyan"],activebackground=THEME["red"]);self.gap_scale.pack()
            Button(compact_group,text="RESET GAP",command=lambda:(self.pair_gap_mm.set(0),self.gap_preview())).pack(fill="x",padx=3,pady=2)
        else:
            self.move_button=compact_action("ENABLE CARD MOVE","Mouse Se Card Move Karein",self.toggle_move)
            compact_action("RESET POSITION","Default Position Lagayein",self.reset_a4)
            if mode in ("a4pair5","a4back","a4pair4"):
                compact_action("ROTATE SELECTED BACK 180°","Selected Back Ko Ghumayein",self.rotate_selected_back)
                compact_action("UNDO ROTATION","Pichhla Rotation Wapas Karein",self.undo_selected_rotation)
                compact_action("RESET ROTATION","Sabhi Cards Seedhe Karein",lambda:self.rotate_all(False))
        compact_action("RESET ALL SETTINGS","Crop Light Position Gap Aur Rotation Reset Karein",self.reset_all_settings)
        side_width=max(360,min(700,round(self.window.winfo_screenwidth()*.38)));side=Frame(body,width=side_width,bg=THEME["panel"],bd=2,relief="ridge",padx=10,pady=8);side.pack(side="right",fill="y",padx=(10,0));side.pack_propagate(False)
        Label(side,text="SELECTED CARD PREVIEW — FULL 90×57 MM",font=("Segoe UI",13,"bold"),fg=THEME["cyan"],bg=THEME["panel"]).pack(pady=(0,3));self.preview_name=StringVar();Label(side,textvariable=self.preview_name,font=("Segoe UI",9,"bold"),fg=THEME["text"],bg=THEME["panel"],wraplength=side_width-25).pack(pady=(0,5))
        self.photo_confidence_text=StringVar(value="PHOTO DETECTION: CHECKING");self.photo_confidence_label=Label(side,textvariable=self.photo_confidence_text,font=("Segoe UI",11,"bold"),fg=THEME["green"],bg=THEME["panel"])
        if mode not in ("a4","a4back"):self.photo_confidence_label.pack(fill="x",pady=(0,5))
        detect_actions=Frame(side,bg=THEME["panel"])
        if mode not in ("a4","a4back"):detect_actions.pack(fill="x",pady=(0,5))
        action_control(detect_actions,"RE-DETECT FRONT","Front Border Dobara Detect Karein",lambda:self.redetect_card("front"))
        action_control(detect_actions,"RE-DETECT BACK","Back Border Dobara Detect Karein",lambda:self.redetect_card("back"))
        action_control(detect_actions,"RE-DETECT PHOTO","Selected Photo Dobara Detect Karein",self.redetect_photo)
        action_control(detect_actions,"DETECT PHOTOS IN ALL","Sabhi Photos Auto Detect Karein",self.redetect_all_photos)
        self.preview_target="back" if mode=="a4back" else "front" if mode=="a4" else "photo";self.preview_zoom=1.0;tabs=Frame(side,bg=THEME["panel"]);tabs.pack(fill="x",pady=(0,6));self.preview_tab_buttons={}
        preview_tabs=(("BACK  [B]","back"),) if mode=="a4back" else (("FRONT  [F]","front"),) if mode=="a4" else (("FRONT  [F]","front"),("BACK  [B]","back"),("PHOTO  [P]","photo"))
        for name,key in preview_tabs:
            button=Button(tabs,text=name,command=lambda value=key:self.select_preview_tab(value));button.pack(side="left",fill="x",expand=True,padx=2);self.preview_tab_buttons[key]=button
        self.main_preview_label=Label(side,bg="#202a39",bd=3,relief="groove");self.main_preview_label.pack(fill="both",expand=True,pady=(0,5))
        compact_nav=Frame(side,bg=THEME["panel"]);compact_nav.pack(fill="x",pady=(0,5))
        Button(compact_nav,text="FIRST",command=lambda:self.step(-len(self.items))).pack(side="left",padx=2)
        Button(compact_nav,text="◀ PREVIOUS",command=lambda:self.step(-1)).pack(side="left",fill="x",expand=True,padx=2)
        self.card_counter=StringVar(value="CARD 01");Label(compact_nav,textvariable=self.card_counter,font=("Segoe UI",9,"bold"),fg=THEME["cyan"],bg=THEME["panel"]).pack(side="left",padx=7)
        Button(compact_nav,text="NEXT ▶",command=lambda:self.step(1)).pack(side="left",fill="x",expand=True,padx=2)
        Button(compact_nav,text="LAST",command=lambda:self.step(len(self.items))).pack(side="left",padx=2)
        thumbnails=Frame(side,bg=THEME["panel"]);thumbnails.pack(fill="x");self.batch_preview_labels={}
        thumbnail_types=(("back",THEME["cyan"]),) if mode=="a4back" else (("front",THEME["red"]),) if mode=="a4" else (("front",THEME["red"]),("back",THEME["cyan"]),("photo",THEME["green"]))
        for name,color in thumbnail_types:
            cell=Frame(thumbnails,bg=THEME["panel"]);cell.pack(side="left",fill="x",expand=True,padx=2);Label(cell,text=name.upper(),fg=color,font=("Segoe UI",8,"bold"),bg=THEME["panel"]).pack();label=Label(cell,bg="#20242b",bd=1,relief="groove",cursor="hand2");label.pack(fill="x");label.bind("<Button-1>",lambda _event,value=name:self.select_preview_tab(value));self.batch_preview_labels[name]=label
        zoom=Frame(side,bg=THEME["panel"]);zoom.pack(fill="x",pady=6)
        for text,value in (("Fit",1.0),("100%",1.35),("Zoom +",.15),("Zoom −",-.15)):Button(zoom,text=text,command=lambda v=value,t=text:self.set_preview_zoom(v,t)).pack(side="left",fill="x",expand=True,padx=2)
        edit_button=Button(side,text="EDIT SELECTED CARD",command=self.edit);edit_button._cinematic_size=11;edit_button.pack(fill="x",pady=(2,0));self.selection_buttons.append(edit_button)
        Button(side,text="CONFIRM PHOTO BOUNDARY",command=self.confirm_selected_photo).pack(fill="x",pady=2)
        Label(side,text="Selected Card Sudharein",font=("Segoe UI",8,"bold"),fg=THEME["muted"],bg=THEME["panel"]).pack(fill="x")
        self.batch_preview_images={};self.preview_cache={};self._draw_after=None
        preview_column=Frame(body,bg=THEME["canvas"]);preview_column.pack(side="left",fill="both",expand=True,padx=4)
        self.canvas=Canvas(preview_column,bg="#30343b",highlightthickness=0);self.canvas.pack(side="left",fill="both",expand=True);self.canvas.bind("<Configure>",lambda e:self.schedule_draw());
        zoom_panel=Frame(preview_column,bg=THEME["panel"],width=72);zoom_panel.pack(side="right",fill="y");zoom_panel.pack_propagate(False)
        Label(zoom_panel,text="ZOOM",font=("Segoe UI",8,"bold"),fg=THEME["cyan"],bg=THEME["panel"]).pack(pady=(8,2))
        self.page_zoom=DoubleVar(value=100)
        Scale(zoom_panel,from_=300,to=25,resolution=5,orient="vertical",variable=self.page_zoom,length=210,command=lambda value:self.set_page_zoom(value)).pack()
        Button(zoom_panel,text="FIT",command=lambda:self.set_page_zoom(100)).pack(fill="x",padx=4,pady=3)
        Label(zoom_panel,text="Ctrl + Mouse Wheel Se Zoom Karein",font=("Segoe UI",7,"bold"),fg=THEME["cyan"],bg=THEME["panel"],wraplength=64).pack(fill="x",padx=2,pady=5)
        self.canvas.bind("<Control-MouseWheel>",self.page_zoom_wheel);self.canvas.bind("<Button-1>",self.layout_down);self.canvas.bind("<B1-Motion>",self.layout_move);self.canvas.bind("<ButtonRelease-1>",self.layout_up)
        self.photo=None;apply_cinematic_theme(self.window);self.window.bind("<Control-p>",lambda e:self.print_current());self.window.bind("<Control-z>",lambda e:self.layout_undo());self.window.bind("<Control-y>",lambda e:self.layout_redo());self.window.bind("f",lambda e:self.select_preview_tab("front"));self.window.bind("b",lambda e:self.select_preview_tab("back"));self.window.bind("p",lambda e:self.select_preview_tab("photo"));self.window.bind("<Left>",lambda e:self.step(-1));self.window.bind("<Right>",lambda e:self.step(1));self.window.bind("<Home>",lambda e:self.step(-len(self.items)));self.window.bind("<End>",lambda e:self.step(len(self.items)));self.window.protocol("WM_DELETE_WINDOW",self.go_home);self.draw()
    def clear_selection(self):
        self.list.selection_clear(0,"end");self.has_selection=False;self.draw()
    def redetect_card(self,target):
        if not self.has_selection or self.busy:return
        item=self.items[self.index];self.busy=True
        def work():
            box=refine_card_box(item["page"],item.get("original_boxes",item["boxes"])[target])
            return box,refine_photo_box_with_confidence(item["page"],box) if target=="front" else None
        def ready(result,error):
            self.busy=False
            if error:messagebox.showerror("Detection",str(error),parent=self.window);return
            box,photo=result;item["boxes"][target]=box
            if photo:
                invalidate_photo(item);item["boxes"]["photo"]=photo[0];item["photo_confidence"]=photo[1]
            item["front"],item["back"],item["photo"]=processed_cards(item);self.edited()
        self.app.run_background(work,ready)

    def redetect_photo(self):
        if not self.has_selection or self.busy:return
        item=self.items[self.index];self.busy=True
        def ready(result,error):
            self.busy=False
            if error:messagebox.showerror("Detection",str(error),parent=self.window);return
            box,confidence=result;invalidate_photo(item);item["boxes"]["photo"]=box
            item["photo_confidence"]=confidence;item["photo_review"]=confidence<85
            item["front"],item["back"],item["photo"]=processed_cards(item);self.edited()
        self.app.run_background(lambda:refine_photo_box_with_confidence(item["page"],item["boxes"]["front"]),ready)
    def redetect_all_photos(self):
        if self.busy:return
        self.busy=True;self.status.set(f"0/{len(self.items)} • Photos Background Me Detect Ho Rahi Hain…");overlay=CenterProcessingOverlay(self.window,"DETECTING PHOTOS",len(self.items),True)
        def work():
            for number,item in enumerate(self.items,1):
                if overlay.cancelled:break
                box,confidence=refine_photo_box_with_confidence(item["page"],item["boxes"]["front"]);invalidate_photo(item);item["boxes"]["photo"]=box;item["photo"]=item["page"].crop(box);item["photo_confidence"]=confidence;item["photo_review"]=confidence<85
                self.app.post_ui(lambda n=number:(overlay.update(n,len(self.items),"DETECTING PHOTOS"),self.status.set(f"{n}/{len(self.items)} • Photos Detect Ho Rahi Hain…")))
            self.app.post_ui(finish)
        def finish():
            self.busy=False;overlay.close();self.preview_cache.clear();self.draw();self.status.set("Photo detection cancelled." if overlay.cancelled else "Photo Detection Complete.")
        threading.Thread(target=work,daemon=True).start()
    def update_photo_confidence(self):
        item=self.items[self.index]
        verified=item.get("photo_verified_geometry")==photo_geometry(item)
        text="PHOTO ✓ MANUALLY VERIFIED" if verified else "PHOTO NEEDS REVIEW" if needs_photo_review(item) else "PHOTO AUTO DETECTED" if not item.get("photo_bypass_geometry") else "PHOTO REVIEW SKIPPED BY USER"
        self.photo_confidence_text.set(text);self.photo_confidence_label.configure(fg=THEME["green"] if verified else THEME["muted"])
    def confirm_selected_photo(self):
        if not self.has_selection:return
        try:confirm_photo(self.items[self.index]);self.layout_dirty=True;self.draw()
        except ValueError as exc:messagebox.showwarning("Photo Boundary",str(exc),parent=self.window)
    def select(self,e=None):
        chosen=self.selected_indices()
        self.has_selection=bool(chosen)
        if chosen:self.index=chosen[-1]
        self.draw()
    def step(self,delta):
        self.has_selection=True;self.index=max(0,min(len(self.items)-1,self.index+delta));row=self.item_to_list_row[self.index];self.list.selection_clear(0,"end");self.list.selection_set(row);self.list.see(row);self.draw()
    def selected_indices(self):
        return tuple(self.list_row_to_item[r] for r in self.list.curselection() if r in self.list_row_to_item)
    def set_page_zoom(self,value):
        self.page_zoom.set(float(value));self.schedule_draw()
    def page_zoom_wheel(self,event):
        self.set_page_zoom(max(25,min(300,self.page_zoom.get()+(10 if event.delta>0 else -10))));return "break"

    def schedule_draw(self):
        """Debounce resize redraws so previews stay smooth on slower PCs."""
        if self._draw_after:
            try:self.window.after_cancel(self._draw_after)
            except Exception:pass
        self._draw_after=self.window.after(70,self.draw)
    def view(self):
        per=1 if self.mode=="4x6" else 5 if self.mode=="a4pair5" else 4 if self.mode=="a4pair4" else 10
        start=self.index//per*per
        key=(start,self.pair_gap_mm.get(),self.app.x_offset_mm,self.app.y_offset_mm)
        if not isinstance(self._a4_pages,dict):self._a4_pages={}
        if key not in self._a4_pages:
            items=self.items[start:start+per];positions=self.a4_positions[start:start+per]
            if self.mode=="4x6":
                item=items[0];page=make_4x6(item["front"],item["back"],item.get("rotate_back_4x6",True),self.app.x_offset_mm,self.app.y_offset_mm,self.pair_gap_mm.get())
            elif self.mode=="a4pair5":page=make_a4_five_pairs(items,self.vgap_mm.get(),positions)[0]
            elif self.mode=="a4pair4":page=make_a4_pairs(items,self.hgap_mm.get(),self.vgap_mm.get(),positions)[0]
            else:page=make_a4([item["back"].rotate(180) if item.get("rotate_back",False) else item["back"] for item in items] if self.mode=="a4back" else [item["front"] for item in items],positions)[0]
            if len(self._a4_pages)>3:self._a4_pages.clear()
            self._a4_pages[key]=page
        return self._a4_pages[key]
    def draw(self):
        if not self.items or self.canvas.winfo_width()<20:return
        for button in self.selection_buttons:button.configure(state="normal" if self.has_selection else "disabled")
        if not self.has_selection:
            self.canvas.delete("all");self.canvas.create_text(self.canvas.winfo_width()//2,self.canvas.winfo_height()//2,text="Select a page/card in the list",fill=THEME["muted"])
            self.main_preview_label.configure(image="");self.preview_name.set("Nothing selected");self.photo_confidence_text.set("");self.card_counter.set("");return
        self.update_photo_confidence()
        full=self.view();self.app.last_print_image=full;image=full.copy();zoom=max(.25,min(3.0,self.page_zoom.get()/100));image.thumbnail((max(40,round((self.canvas.winfo_width()-22)*zoom)),max(40,round((self.canvas.winfo_height()-22)*zoom))),Image.Resampling.LANCZOS);self.view_scale=image.width/full.width;self.view_origin=((self.canvas.winfo_width()-image.width)//2,(self.canvas.winfo_height()-image.height)//2);self.photo=ImageTk.PhotoImage(image);self.canvas.delete("all");self.canvas.create_image(self.canvas.winfo_width()//2,self.canvas.winfo_height()//2,image=self.photo);per_page=5 if self.mode=="a4pair5" else 4 if self.mode=="a4pair4" else 10
        if self.mode!="4x6":
            px,py=self.a4_positions[self.index];pair_w=2*CARD_SIZE[0] if self.mode=="a4pair5" else CARD_SIZE[0];pair_h=2*CARD_SIZE[1] if self.mode=="a4pair4" else CARD_SIZE[1];ox,oy=self.view_origin
            x1=ox+px*self.view_scale;y1=oy+py*self.view_scale;x2=x1+pair_w*self.view_scale;y2=y1+pair_h*self.view_scale
            self.canvas.create_rectangle(x1,y1,x2,y2,outline=THEME["cyan"],width=4,tags="selected");self.canvas.create_text(x1+7,y1+12,text=f"SELECTED {self.index%per_page+1}",anchor="w",fill=THEME["cyan"],font=("Segoe UI",9,"bold"),tags="selected")
        detail=(f"4×6 • 90×57 mm LOCKED • Gap {self.pair_gap_mm.get():.1f} mm • X {self.app.x_offset_mm:+.1f} / Y {self.app.y_offset_mm:+.1f} mm" if self.mode=="4x6" else f"A4 PAGE {self.index//per_page+1} • Front/Back 0 mm • Pair gap {self.vgap_mm.get():.2f} mm • Drag when MOVE is ON" if self.mode=="a4pair5" else f"A4 PAGE {self.index//per_page+1} • H {self.hgap_mm.get():.1f} / V {self.vgap_mm.get():.1f} mm • Drag when MOVE is ON");self.status.set(f"{self.index+1}/{len(self.items)} • 90×57 mm SIZE LOCKED • {detail}");self.update_side_previews()
    def update_side_previews(self):
        item=self.items[self.index];self.card_counter.set(f"CARD {self.index+1:02d} OF {len(self.items):02d}");self.preview_name.set(f"{self.index+1:02d}/{len(self.items):02d}  •  {item.get('source_label',item['path'].name)}")
        for name,label in self.batch_preview_labels.items():
            key=(name,id(item[name]));image=self.preview_cache.get(key)
            if image is None:
                image=item[name].copy().convert("RGB");image.thumbnail((145,84),Image.Resampling.BILINEAR);self.preview_cache[key]=image
            preview=ImageTk.PhotoImage(image);self.batch_preview_images[name]=preview;label.configure(image=preview)
        large=item[self.preview_target].copy().convert("RGB");available_w=max(40,self.main_preview_label.winfo_width()-12);available_h=max(40,self.main_preview_label.winfo_height()-12);large.thumbnail((round(available_w*self.preview_zoom),round(available_h*self.preview_zoom)),Image.Resampling.LANCZOS);self.batch_preview_images["large"]=ImageTk.PhotoImage(large);self.main_preview_label.configure(image=self.batch_preview_images["large"])
        for name,button in self.preview_tab_buttons.items():button._cinematic_selected=name==self.preview_target;button.configure(bg=THEME["red"] if name==self.preview_target else getattr(button,"_cinematic_bg",THEME["panel_alt"]))

    def select_preview_tab(self,target):
        if target not in ("front","back","photo") or not self.has_selection:return
        self.preview_target=target;self.update_side_previews()

    def set_preview_zoom(self,value,label):
        if not self.has_selection:return
        self.preview_zoom=value if label in ("Fit","100%") else max(.65,min(1.65,self.preview_zoom+value));self.update_side_previews()
    def toggle_move(self):
        if self.mode=="4x6":return
        self.move_cards=not self.move_cards
        self.move_button.configure(text="CARD MOVE ENABLED" if self.move_cards else "ENABLE CARD MOVE",bg=THEME["red"] if self.move_cards else THEME["blue_dark"])
        self.canvas.configure(cursor="fleur" if self.move_cards else "")
    def layout_down(self,e):
        if self.mode=="4x6" or not self.has_selection or not hasattr(self,"view_origin"):return
        ox,oy=self.view_origin;x=(e.x-ox)/self.view_scale;y=(e.y-oy)/self.view_scale;per_page=5 if self.mode=="a4pair5" else 4 if self.mode=="a4pair4" else 10;start=(self.index//per_page)*per_page
        for i in range(start,min(start+per_page,len(self.items))):
            px,py=self.a4_positions[i]
            height=2*CARD_SIZE[1] if self.mode=="a4pair4" else CARD_SIZE[1];width=2*CARD_SIZE[0] if self.mode=="a4pair5" else CARD_SIZE[0]
            if px<=x<=px+width and py<=y<=py+height:
                self.has_selection=True;self.index=i;row=self.item_to_list_row[i];self.list.selection_clear(0,"end");self.list.selection_set(row);self.list.see(row)
                if self.move_cards:self.push_layout_history();self.layout_drag=(i,x-px,y-py)
                self.draw();return
    def layout_move(self,e):
        if not self.layout_drag:return
        i,dx,dy=self.layout_drag;ox,oy=self.view_origin;x=(e.x-ox)/self.view_scale-dx;y=(e.y-oy)/self.view_scale-dy
        height=2*CARD_SIZE[1] if self.mode=="a4pair4" else CARD_SIZE[1];width=2*CARD_SIZE[0] if self.mode=="a4pair5" else CARD_SIZE[0];self.a4_positions[i]=(max(0,min(A4_SIZE[0]-width,round(x))),max(0,min(A4_SIZE[1]-height,round(y))));self.items[i][self.a4_key]=self.a4_positions[i];self._a4_pages=None;self.layout_dirty=True;self.schedule_draw()
    def layout_up(self,e):self.layout_drag=None
    def reset_a4(self):
        if self.mode=="4x6":return
        self.push_layout_history();self.a4_positions=a4_five_pair_positions(len(self.items),self.vgap_mm.get()) if self.mode=="a4pair5" else a4_pair_positions(len(self.items),self.hgap_mm.get(),self.vgap_mm.get()) if self.mode=="a4pair4" else a4_grid_positions(len(self.items),self.hgap_mm.get(),self.vgap_mm.get())
        for i,item in enumerate(self.items):item[self.a4_key]=self.a4_positions[i]
        self._a4_pages=None;self.layout_dirty=True;self.draw()
    def push_layout_history(self):
        self.layout_undo_stack.append((list(self.a4_positions),self.hgap_mm.get(),self.vgap_mm.get()));self.layout_undo_stack=self.layout_undo_stack[-30:];self.layout_redo_stack.clear()
    def restore_layout(self,state):
        positions,hgap,vgap=state;self.a4_positions=list(positions);self.hgap_mm.set(hgap);self.vgap_mm.set(vgap)
        for i,item in enumerate(self.items):item[self.a4_key]=self.a4_positions[i]
        self._a4_pages=None;self.draw()
    def layout_undo(self):
        if not self.layout_undo_stack:return
        self.layout_redo_stack.append((list(self.a4_positions),self.hgap_mm.get(),self.vgap_mm.get()));self.restore_layout(self.layout_undo_stack.pop())
    def layout_redo(self):
        if not self.layout_redo_stack:return
        self.layout_undo_stack.append((list(self.a4_positions),self.hgap_mm.get(),self.vgap_mm.get()));self.restore_layout(self.layout_redo_stack.pop())
    def gap_preview(self):
        if self.mode!="4x6":
            self.a4_positions=a4_five_pair_positions(len(self.items),self.vgap_mm.get()) if self.mode=="a4pair5" else a4_pair_positions(len(self.items),self.hgap_mm.get(),self.vgap_mm.get()) if self.mode=="a4pair4" else a4_grid_positions(len(self.items),self.hgap_mm.get(),self.vgap_mm.get())
            for i,item in enumerate(self.items):item[self.a4_key]=self.a4_positions[i]
        self._a4_pages=None;self.layout_dirty=True;self.schedule_draw()
    def auto_fit(self):
        if self.mode=="4x6":return
        self.push_layout_history();self.hgap_mm.set(0.0 if self.mode=="a4pair5" else 2.0 if self.mode=="a4pair4" else 10.0);self.vgap_mm.set(1.2 if self.mode=="a4pair5" else 8.0 if self.mode=="a4pair4" else 1.5);self.gap_preview()
    def save_layout_preset(self):
        data=self.app.read_settings();data.setdefault("layout_presets",{})[self.mode]={"hgap_mm":self.hgap_mm.get(),"vgap_mm":self.vgap_mm.get(),"pair_gap_mm":self.pair_gap_mm.get()}
        if self.app.write_settings(data):messagebox.showinfo("Layout Saved","Is layout ki spacing agli baar ke liye save ho gayi.",parent=self.window)
    def load_layout_preset(self):
        preset=self.app.read_settings().get("layout_presets",{}).get(self.mode)
        if not preset:messagebox.showinfo("No Saved Layout","Is mode ka saved layout abhi available nahi hai.",parent=self.window);return
        self.push_layout_history();self.hgap_mm.set(preset.get("hgap_mm",self.hgap_mm.get()));self.vgap_mm.set(preset.get("vgap_mm",self.vgap_mm.get()));self.pair_gap_mm.set(preset.get("pair_gap_mm",self.pair_gap_mm.get()));self.gap_preview()

    def choose_export_quality(self):
        choice=themed_message(self.window,"EXPORT QUALITY","Quality Select Karein. 600 DPI Professional Print Ke Liye Best Hai; 1200 DPI Archive File Bahut Badi Hogi.","info",("600 DPI PROFESSIONAL","1200 DPI ARCHIVE","CANCEL"))
        if choice=="600 DPI PROFESSIONAL":self.app.export_dpi=600
        elif choice=="1200 DPI ARCHIVE":self.app.export_dpi=1200
        if choice!="CANCEL":themed_message(self.window,"QUALITY SELECTED",f"Final JPG Aur PDF: {self.app.export_dpi} DPI","success",("CLOSE",))

    def reset_all_settings(self):
        choice=themed_message(self.window,"RESET ALL SETTINGS","Reset Ka Scope Select Karein. Complete Batch Sirf Aapke Clear Selection Par Reset Hoga.","warning",("RESET CURRENT CARD","RESET CURRENT PAGE","RESET COMPLETE BATCH","CANCEL"))
        if choice=="CANCEL" or not choice:return
        if choice=="RESET CURRENT CARD":indices=[self.index]
        elif choice=="RESET CURRENT PAGE":
            per_page=5 if self.mode=="a4pair5" else 4 if self.mode=="a4pair4" else 10 if self.mode!="4x6" else 1;start=(self.index//per_page)*per_page;indices=range(start,min(start+per_page,len(self.items)))
        else:indices=range(len(self.items))
        for index in indices:
            item=self.items[index];original=item.get("original_boxes")
            if original:item["boxes"]={key:tuple(value) for key,value in original.items()}
            item["adjustments"]={target:default_adjustments() for target in ("front","back","photo")};item["rotate_back"]=False;item["rotate_back_4x6"]=True
            invalidate_photo(item);item["front"],item["back"],item["photo"]=processed_cards(item)
        self.layout_dirty=True;self.pair_gap_mm.set(0);self.preview_cache.clear();self._a4_pages=None
        if self.mode!="4x6":self.reset_a4()
        else:self.draw()
        themed_message(self.window,"RESET COMPLETE",f"{len(list(indices))} Card Setting Reset Ho Gayi.","success",("CLOSE",))

    def auto_light_selected(self):
        chosen=self.selected_indices()
        for index in chosen:
            item=self.items[index];photo=item["page"].crop(item["boxes"]["photo"]);item.setdefault("adjustments",{})["photo"]=smart_light_adjustments(photo);item["front"],item["back"],item["photo"]=processed_cards(item)
        self.preview_cache.clear();self._a4_pages=None;self.layout_dirty=True;self.draw();messagebox.showinfo("Auto Light Complete",f"{len(chosen)} selected photo(s) naturally bright + clear ho gaye. Manual Edit abhi bhi available hai.",parent=self.window)
    def edit(self):
        if not self.has_selection:return
        FastCropWindow(self.app,self.items[self.index],self.edited,[self.items[i] for i in self.selected_indices()],parent=self.window)
    def rotate_all(self,value):
        for item in self.items:item["rotate_back"]=value
        self._a4_pages=None;self.layout_dirty=True;self.draw()
    def rotate_selected_back(self):
        """Toggle only the selected card's back and keep a dedicated undo."""
        chosen=self.selected_indices();before=[(i,self.items[i].get("rotate_back",False)) for i in chosen];self.rotation_undo_stack.append(before);self.rotation_undo_stack=self.rotation_undo_stack[-30:]
        for i,old in before:self.items[i]["rotate_back"]=not old
        self._a4_pages=None;self.layout_dirty=True;self.preview_cache.clear();self.draw()
    def undo_selected_rotation(self):
        if not self.rotation_undo_stack:
            messagebox.showinfo("Nothing to Undo","Abhi koi selected-card rotation undo karne ke liye nahi hai.",parent=self.window);return
        for i,value in self.rotation_undo_stack.pop():self.items[i]["rotate_back"]=value
        self._a4_pages=None;self.preview_cache.clear();self.draw()
    def review_blocked(self,indices=None):
        indices=tuple(indices if indices is not None else range(len(self.items)))
        bad=[i for i in indices if needs_photo_review(self.items[i])]
        if not bad:return False
        answer=photo_review_dialog(self.window,self.items,bad);choice=answer["value"]
        if choice=="CONTINUE WITHOUT FIXING":
            for i in bad:self.items[i]["photo_bypass_geometry"]=photo_geometry(self.items[i])
            return False
        if choice=="CONFIRM PHOTO BOUNDARY":
            try:confirm_photo(self.items[answer["index"]])
            except ValueError as exc:messagebox.showwarning("Photo Boundary",str(exc),parent=self.window);return True
            return self.review_blocked(indices)
        if choice in ("FIX SELECTED PHOTO","REVIEW ALL"):
            queue_items=bad if choice=="REVIEW ALL" else [answer["index"]]
            self.review_queue=list(queue_items)
            self.edit_next_review()
        return True
    def edit_next_review(self):
        if not self.review_queue:return
        self.index=self.review_queue.pop(0);self.step(0)
        FastCropWindow(self.app,self.items[self.index],lambda:(self.edited(),self.edit_next_review()),parent=self.window)
    def edited(self):
        self.layout_dirty=True;self._a4_pages=None;self.preview_cache.clear();self.draw()
    def confirm_print(self,label,count):
        paper="4×6" if self.mode=="4x6" else "A4";return messagebox.askyesno("PRINT SAFETY CHECK",f"{label}\n\nPaper: {paper}\nSelected cards/pages: {count}\nCard size: 90×57 mm LOCKED\n\nPrinter ON hai, {paper} paper loaded hai aur preview sahi hai?",parent=self.window)
    def print_current(self):
        if not self.has_selection:return
        per_page=1 if self.mode=="4x6" else 5 if self.mode=="a4pair5" else 4 if self.mode=="a4pair4" else 10
        start=self.index//per_page*per_page
        if self.review_blocked(range(start,min(start+per_page,len(self.items)))):return
        self.prepare_print(self.page_builder(range(start,min(start+per_page,len(self.items)))))
    def pages_for(self,chosen):
        return self.page_builder(chosen)()
    def page_builder(self,chosen):
        chosen=tuple(chosen);mode=self.mode
        items=[dict(item) for item in self.items];positions=list(self.a4_positions)
        hgap,vgap,gap=self.hgap_mm.get(),self.vgap_mm.get(),self.pair_gap_mm.get()
        dx,dy=self.app.x_offset_mm,self.app.y_offset_mm
        per=1 if mode=="4x6" else 5 if mode=="a4pair5" else 4 if mode=="a4pair4" else 10
        def build():
            pages=[]
            for group in sorted({i//per for i in chosen}):
                indexes=[i for i in chosen if i//per==group]
                subset=[items[i] for i in indexes];pos=[positions[i] for i in indexes]
                if mode=="4x6":
                    item=subset[0];pages.append(make_4x6(item["front"],item["back"],item.get("rotate_back_4x6",True),dx,dy,gap))
                elif mode=="a4pair5":pages.extend(make_a4_five_pairs(subset,vgap,pos))
                elif mode=="a4pair4":pages.extend(make_a4_pairs(subset,hgap,vgap,pos))
                else:pages.extend(make_a4([item["back"].rotate(180) if item.get("rotate_back",False) else item["back"] for item in subset] if mode=="a4back" else [item["front"] for item in subset],pos))
            label={"4x6":"4×6 Front + Back","a4":"10 Front Cards","a4back":"10 Back Cards","a4pair4":"4 Complete Cards","a4pair5":"5 Complete Cards"}[mode]
            for page in pages:page.info['layout_name']=label
            return pages
        return build
    def print_selected(self):
        chosen=self.selected_indices()
        if not chosen:return
        if self.review_blocked(chosen):return
        self.prepare_print(self.page_builder(chosen))
    def print_all(self):
        if self.review_blocked():return
        self.prepare_print(self.page_builder(range(len(self.items))))
    def prepare_print(self,build):
        if self.busy:return
        self.busy=True;self.status.set("Preparing print preview…")
        def ready(pages,error):
            self.busy=False
            if error:messagebox.showwarning("Print Preview",str(error),parent=self.window);return
            paper="4×6 layout" if self.mode=="4x6" else "A4 layout"
            if final_print_preview(self.window,pages,paper):self.app.print_batch_async(pages,self.window)
        self.app.run_background(build,ready)
    def save_pdf(self,all_files=False):
        chosen=tuple(range(len(self.items))) if all_files else self.selected_indices()
        if not chosen:return
        if self.review_blocked(chosen):return
        kind="4x6" if self.mode=="4x6" else "A4_5_CARD_FRONT_BACK" if self.mode=="a4pair5" else "A4_4_CARD_FRONT_BACK" if self.mode=="a4pair4" else "A4_BACK" if self.mode=="a4back" else "A4_FRONT"
        default=f"Seema_Digital_Maha_ID_{kind}_{'ALL' if all_files else 'SELECTED'}.pdf"
        value=filedialog.asksaveasfilename(title="Save PDF As",defaultextension=".pdf",filetypes=[("PDF File","*.pdf")],initialfile=default,parent=self.window)
        if value:self.app.save_pdf_async(self.pages_for(chosen),Path(value),self.window,self.status)
    def go_home(self):
        if self.busy or self.app.saving or self.app.printing:return
        if self.layout_dirty:
            choice=unsaved_changes_dialog(self.window)
            if choice=="cancel":return
            if choice=="save":self.save();return
        if self._draw_after:self.window.after_cancel(self._draw_after);self._draw_after=None
        self.window.destroy();self.app.status.set(f"{PRODUCT_NAME} {APP_VERSION} • Select A Layout To Start.");show_maximized(self.app.root)
    def save(self):
        if self.review_blocked():return
        default=f"Seema_Digital_Maha_ID_{self.mode.upper()}"
        selection=final_output_dialog(self.window,default,self.app.export_dpi)
        if not selection.get("path"):return
        target=selection["path"];self.app.export_dpi=selection["dpi"]
        for item in self.items:item["pair_gap_mm"]=self.pair_gap_mm.get();item["hgap_mm"]=self.hgap_mm.get();item["vgap_mm"]=self.vgap_mm.get()
        valid_items=[item for index,item in enumerate(self.items) if index not in getattr(self,"_excluded_low_confidence",set())]
        if not valid_items:
            themed_message(self.window,"NO VALID CARDS","Review Ke Bina Save Karne Layak Koi Card Nahi Hai.","warning",("REVIEW CARDS",));return
        if target.suffix.lower()==".pdf":self.app.save_pdf_async(self.pages_for(range(len(self.items))),target,self.window,self.status)
        else:self.app.export_async(valid_items,self.mode,target,self.window,self.status)

class MahaIDApp:
    def __init__(self,root):
        self._ui_events=queue.Queue();self.root=root;root.after(30,self._poll_ui_events);self.last_print_image=None;self.loading=False;self.printing=False;self.saving=False
        self.export_dpi=600;self._detection_cache={};self.config_path=self.get_config_path()
        self.x_offset_mm,self.y_offset_mm=self.load_print_position()
        root.title(f"{PRODUCT_NAME} {APP_VERSION}");root.withdraw();full_screen(root);apply_window_icon(root)
        root.protocol("WM_DELETE_WINDOW",root.destroy)
        self.status=StringVar(value=f"{PRODUCT_NAME} {APP_VERSION} • Select A Layout To Start.")
        self._install_premium_home();root.after_idle(self.show_splash)

    def _install_premium_home(self):
        self.home_canvas=Canvas(self.root,bg=THEME["bg"],highlightthickness=0,cursor="hand2");self.home_canvas.place(x=0,y=0,relwidth=1,relheight=1);self._premium_resize_after=None;self._premium_active=None
        self._premium_modes=(("SINGLE 4×6","Ek Maha ID Ka Front Aur Back",self.single),("MULTIPLE 4×6","Ek Se Zyada Front-Back Cards Alag 4×6 Pages Par",lambda:self.batch("4x6")),("A4 ME 4 COMPLETE CARDS","4 Complete Front-Back Cards Ek A4 Page Par",lambda:self.batch("a4pair4")),("A4 ME 5 COMPLETE CARDS","5 Complete Front-Back Cards Ek A4 Page Par",lambda:self.batch("a4pair5")),("A4 ME 10 CARD — ONLY FRONT","10 Front Cards Ek A4 Page Par",lambda:self.batch("a4")),("A4 ME 10 CARD — ONLY BACK","10 Back Cards Ek A4 Page Par",lambda:self.batch("a4back")))
        self._premium_boxes=((24,218,560,516),(575,218,1094,516),(1105,218,1649,516),(24,527,560,838),(575,527,1094,838),(1105,527,1649,838));self.home_canvas.bind("<Configure>",self._schedule_premium_home);self.home_canvas.bind("<Motion>",self._premium_motion);self.home_canvas.bind("<Leave>",lambda _e:self._set_premium_active(None));self.home_canvas.bind("<Button-1>",self._premium_click);self.root.after(30,self._render_premium_home)
    def _premium_base(self):
        if not hasattr(self,"_home_art_cache"):
            from .home_art import compose_home
            self._home_art_cache=compose_home(ASSET_DIR,self._premium_modes)
        return self._home_art_cache
    def _schedule_premium_home(self,_event=None):
        if self._premium_resize_after:
            try:self.root.after_cancel(self._premium_resize_after)
            except Exception:pass
        self._premium_resize_after=self.root.after(90,self._render_premium_home)
    def _render_premium_home(self):
        self._premium_resize_after=None
        if not self.home_canvas.winfo_exists():return
        width=max(640,self.home_canvas.winfo_width());height=max(360,self.home_canvas.winfo_height());base=self._premium_base();self._premium_source_size=base.size
        # Background fills the usable client area, while the approved Home artwork
        # lives in a centered aspect-safe container.  This prevents the SEEMA
        # DIGITAL header or bottom tiles being cropped at 125-200% Windows DPI.
        safe_x=max(18,round(width*.025));safe_y=max(18,round(height*.025))
        usable_w=max(320,width-2*safe_x);usable_h=max(240,height-2*safe_y)
        self._premium_scale=min(usable_w/base.width,usable_h/base.height)
        scaled=(max(1,round(base.width*self._premium_scale)),max(1,round(base.height*self._premium_scale)))
        image=base.resize(scaled,Image.Resampling.LANCZOS);self._premium_offset=((width-scaled[0])//2,(height-scaled[1])//2)
        background=home_background((width,height));self.home_premium_photo=ImageTk.PhotoImage(background);self.home_premium_art=ImageTk.PhotoImage(image)
        self.home_canvas.delete("all");self.home_canvas.create_image(0,0,anchor="nw",image=self.home_premium_photo,tags="home_bg");self.home_canvas.create_image(self._premium_offset[0],self._premium_offset[1],anchor="nw",image=self.home_premium_art,tags="home");self._draw_premium_outline()
    def _premium_hit(self,x,y):
        ox,oy=self._premium_offset;scale=self._premium_scale;sx,sy=(x-ox)/scale,(y-oy)/scale
        for index,(x1,y1,x2,y2) in enumerate(self._premium_boxes):
            if x1<=sx<=x2 and y1<=sy<=y2:return index
        return None
    def _premium_motion(self,event):self._set_premium_active(self._premium_hit(event.x,event.y))
    def _set_premium_active(self,index):
        if index==self._premium_active:return
        self._premium_active=index;self._draw_premium_outline()
    def _draw_premium_outline(self):
        self.home_canvas.delete("tile_outline")
        if self._premium_active is None:return
        x1,y1,x2,y2=self._premium_boxes[self._premium_active];s=self._premium_scale;ox,oy=self._premium_offset;self.home_canvas.create_rectangle(ox+x1*s,oy+y1*s,ox+x2*s,oy+y2*s,outline=THEME["cyan"],width=max(3,round(4*s)),tags="tile_outline")
    def _premium_click(self,event):
        index=self._premium_hit(event.x,event.y)
        if index is not None:self._premium_modes[index][2]()



    def get_config_path(self):
        base=Path(os.environ.get("APPDATA",APP_DIR))/"Seema Digital";return base/"Maha id settings 10.35.json"
    def load_print_position(self):
        try:
            data=self.read_settings();return float(data.get("x_offset_mm",0)),float(data.get("y_offset_mm",0))
        except Exception:return 0.0,0.0
    def read_settings(self):
        for candidate in (self.config_path,self.config_path.with_suffix(".bak")):
            try:
                data=json.loads(candidate.read_text(encoding="utf-8"))
                if isinstance(data,dict):return data
            except Exception:pass
        return {}
    def write_settings(self,data):
        try:
            self.config_path.parent.mkdir(parents=True,exist_ok=True);temporary=self.config_path.with_suffix(".tmp");backup=self.config_path.with_suffix(".bak")
            temporary.write_text(json.dumps(data,indent=2),encoding="utf-8")
            if self.config_path.exists():backup.write_bytes(self.config_path.read_bytes())
            os.replace(temporary,self.config_path);return True
        except Exception as exc:friendly_problem(self.root,"Settings Not Saved",str(exc),"Writable Windows user profile use karein aur dobara Save dabayein.");return False
    def set_print_position(self,x_mm,y_mm,save=False):
        dx,dy=safe_4x6_offset(x_mm,y_mm);self.x_offset_mm=round(dx/PX_PER_MM,2);self.y_offset_mm=round(dy/PX_PER_MM,2)
        if save:
            data=self.read_settings();data.update({"profile":"Windows 4x6","x_offset_mm":self.x_offset_mm,"y_offset_mm":self.y_offset_mm});self.write_settings(data)

    def show_splash(self):
        splash=Toplevel(self.root);splash.withdraw();splash.title("Seema Digital Maha id");splash.configure(bg="#020916")
        apply_window_icon(splash);full_screen(splash)
        splash.update_idletasks()
        # Client size (not monitor size) keeps the panel above the Windows
        # taskbar. This fixes the cut-off panel visible in the screenshot.
        width=max(800,splash.winfo_width());height=max(600,splash.winfo_height())
        canvas=Canvas(splash,bg="#020916",highlightthickness=0,width=width,height=height);canvas.pack(fill="both",expand=True)
        try:
            source=Image.open(resource_path("Seema_Digital_Splash_Embedded.jpg")).convert("RGB")
            scene=cinematic_splash(source,(width,height),132)
            self.splash_background=ImageTk.PhotoImage(scene);canvas.create_image(0,0,anchor="nw",image=self.splash_background)
        except Exception:
            canvas.create_text(width//2,height//2,text="SEEMA DIGITAL\nMAHA ID FAST PRINT STUDIO",fill="white",font=("Arial Black",32,"bold"))
        panel_w=min(980,round(width*.78));panel_h=128;panel_y=height-panel_h-12
        self.splash_progress_photo=ImageTk.PhotoImage(cinematic_progress_panel(panel_w,panel_h,0))
        progress_item=canvas.create_image(width//2,panel_y,anchor="n",image=self.splash_progress_photo)
        status_item=canvas.create_text(width//2,panel_y-22,text="STARTING",fill=THEME["cyan"],font=("Segoe UI",12,"bold"))
        splash.deiconify();splash.lift();splash.attributes("-topmost",True)
        def finish():
            if splash.winfo_exists():splash.destroy()
            show_maximized(self.root)
        def tick(step=0):
            if not splash.winfo_exists():return
            percent=min(100,round(step*100/60));label="STARTING" if percent<25 else "LOADING PRESETS" if percent<65 else "PREPARING HOME" if percent<95 else "READY"
            self.splash_progress_photo=ImageTk.PhotoImage(cinematic_progress_panel(panel_w,panel_h,percent,percent*3))
            canvas.itemconfigure(progress_item,image=self.splash_progress_photo);canvas.itemconfigure(status_item,text=label)
            if step<60:splash.after(35,lambda:tick(step+1))
            else:splash.after(120,finish)
        tick()
    def create_items(self,paths):
        items,errors=[],[]
        for value in paths:
            try:
                path=Path(value)
                for page_number,page in enumerate(render_source_pages(path),1):
                    front_seed,back_seed=maha_seed(page);front=refine_card_box(page,front_seed);back=refine_card_box(page,back_seed);photo,photo_confidence=refine_photo_box_with_confidence(page,front);items.append({"path":path,"source_label":f"{path.name} • Page {page_number}","source_page":page_number,"page":page,"boxes":{"front":front,"back":back,"photo":photo},"original_boxes":{"front":front,"back":back,"photo":photo},"front":page.crop(front),"back":page.crop(back),"photo":page.crop(photo),"photo_confidence":photo_confidence,"photo_review":photo_confidence<85,"adjustments":{target:default_adjustments() for target in ("front","back","photo")},"rotate_back":False,"rotate_back_4x6":True})
            except Exception as exc:errors.append(f"{Path(value).name}: {exc}")
        return items,errors
    def _process_source_path(self,path,password,cancel_event=None):
        stat=path.stat();key=(str(path.resolve()),stat.st_size,stat.st_mtime_ns);detected=self._detection_cache.get(key)
        if detected is None:
            detected=[]
            for page_number,page in enumerate(render_source_pages(path,password),1):
                if cancel_event and cancel_event.is_set():break
                front_seed,back_seed=maha_seed(page);front=refine_card_box(page,front_seed);back=refine_card_box(page,back_seed)
                photo,confidence=refine_photo_box_with_confidence(page,front)
                back_photo,back_confidence=refine_photo_box_with_confidence(page,back)
                if back_confidence>=85 and confidence<65:front,back=back,front;photo,confidence=back_photo,back_confidence
                detected.append((page_number,page,front,back,photo,confidence))
            if not (cancel_event and cancel_event.is_set()):
                if len(self._detection_cache)>=3:self._detection_cache.clear()
                self._detection_cache[key]=detected
        items=[]
        for page_number,page,front,back,photo,photo_confidence in detected:
            if cancel_event and cancel_event.is_set():break
            items.append({"path":path,"source_label":f"{path.name} • Page {page_number}","source_page":page_number,"page":page,"boxes":{"front":front,"back":back,"photo":photo},"original_boxes":{"front":front,"back":back,"photo":photo},"front":page.crop(front),"back":page.crop(back),"photo":page.crop(photo),"photo_confidence":photo_confidence,"photo_review":photo_confidence<85,"adjustments":{target:default_adjustments() for target in ("front","back","photo")},"rotate_back":False,"rotate_back_4x6":True})
        return items
    def load_paths_async(self,paths,mode):
        """Render PDFs/images outside Tk so large batches never freeze the window."""
        if self.loading:
            messagebox.showinfo("Please Wait","Pichli files abhi process ho rahi hain. Complete hone ke baad dobara select karein.",parent=self.root);return
        passwords={};preflight_errors=[]
        for value in paths:
            path=Path(value)
            try:
                password=preflight_pdf_password(path,self.root)
                if path.suffix.lower()==".pdf":
                    probe=open_pdf(path,password=password,allow_prompt=False);probe.close()
                passwords[path]=password
            except Exception as exc:preflight_errors.append(f"{path.name}: {exc}")
        valid_paths=[Path(value) for value in paths if Path(value) in passwords]
        if not valid_paths:
            self.status.set("Koi valid file select nahi hui.")
            if preflight_errors:friendly_problem(self.root,"Files Not Opened","\n".join(preflight_errors[:5]),"PDF password/file check karke dobara select karein.")
            return
        self.loading=True;self.status.set(f"0/{len(valid_paths)} • Maha ID files background me auto-crop ho rahi hain…");overlay=CenterProcessingOverlay(self.root,"PROCESSING FILES",len(valid_paths),True);events=queue.Queue()
        def work():
            items,errors=[],list(preflight_errors)
            workers=1
            with ThreadPoolExecutor(max_workers=workers,thread_name_prefix="maha-detect") as pool:
                futures={pool.submit(self._process_source_path,path,passwords[path],overlay.cancel_event):path for path in valid_paths}
                for number,future in enumerate(as_completed(futures),1):
                    path=futures[future]
                    if overlay.cancelled:break
                    try:items.extend(future.result())
                    except Exception as exc:errors.append(f"{path.name}: {exc}")
                    events.put(("progress",number))
            events.put(("done",items,errors))
        def poll():
            try:
                while True:
                    event=events.get_nowait()
                    if event[0]=="progress":
                        number=event[1];stage="CREATING PREVIEW" if number==len(valid_paths) else "DETECTING PHOTOS" if number>len(valid_paths)//2 else "DETECTING CARDS";overlay.update(number,len(valid_paths),stage);self.status.set(f"{number}/{len(valid_paths)} • Files process ho rahi hain… window active hai")
                    elif event[0]=="done":overlay.close();self.finish_loading(event[1],event[2],mode,cancelled=overlay.cancelled);return
            except queue.Empty:pass
            self.root.after(45,poll)
        threading.Thread(target=work,daemon=True).start()
        poll()
    def finish_loading(self,items,errors,mode,cancelled=False):
        self.loading=False
        if items:BatchReview(self,items,mode);self.status.set(f"{len(items)} Maha ID file(s) preview ke liye ready.")
        if errors:friendly_problem(self.root,"Some Files Not Opened","\n".join(errors[:5]),"Problem wali PDF/image check karke dobara select karein; baaki files safe hain.")
        if cancelled and not items:self.status.set("Processing safely cancel hui.")
        elif not items and not errors:self.status.set("Koi file select nahi hui.")
    def single(self):
        selected=filedialog.askopenfilename(title="Select Maha ID File",filetypes=SUPPORTED)
        if selected:self.load_paths_async([selected],"4x6")
    def batch(self,mode):
        paths=filedialog.askopenfilenames(title="Select Multiple Maha ID Files",filetypes=SUPPORTED)
        if paths:self.load_paths_async(tuple(paths),mode)
    def post_ui(self,callback):
        self._ui_events.put(callback)
    def _poll_ui_events(self):
        try:
            for _ in range(40):self._ui_events.get_nowait()()
        except queue.Empty:pass
        self.root.after(30,self._poll_ui_events)
    def run_background(self,work,done):
        events=queue.Queue()
        def worker():
            try:events.put((work(),None))
            except Exception as exc:events.put((None,exc))
        def poll():
            try:result,error=events.get_nowait()
            except queue.Empty:self.root.after(30,poll);return
            done(result,error)
        threading.Thread(target=worker,daemon=True).start();self.root.after(30,poll)

    def print_last(self):
        messagebox.showinfo("Choose Print Scope","Open a layout preview and explicitly choose Current Page, Selected Cards or All Pages.",parent=self.root)
    def print_async(self,image,parent):
        self.print_batch_async([image],parent)

    def print_batch_async(self,pages,parent):
        if self.printing:return
        if not pages:
            messagebox.showwarning("Nothing Selected","Select cards or a page first.",parent=parent);return
        from .printing import print_dialog
        print_dialog(self,parent,list(pages))

    def save_pdf_async(self,pages,path,parent,status):
        """Atomically stream an exact-size PDF without keeping duplicate page copies."""
        source_pages=list(pages);dpi=getattr(self,"export_dpi",EXPORT_DPI)
        if not source_pages:
            messagebox.showwarning("Nothing Selected","PDF save karne ke liye kam se kam ek file select karein.",parent=parent);return
        if self.saving:
            messagebox.showinfo("Save Already Running","Pichla Save complete hone tak wait karein.",parent=parent);return
        self.saving=True;status.set(f"Saving 0/{len(source_pages)} PDF page(s)…");overlay=CenterProcessingOverlay(parent,"PREPARING OUTPUT",len(source_pages),True)
        def work():
            temporary=path.with_name(f".{path.stem}.partial{path.suffix}")
            try:
                path.parent.mkdir(parents=True,exist_ok=True)
                ensure_output_capacity(path.parent,sum(page.width*page.height for page in source_pages)*0.55)
                document=pymupdf.open()
                for number,image in enumerate(source_pages,1):
                    if overlay.cancelled:raise InterruptedError("Save user ne cancel kiya")
                    rgb=high_quality_page(image,dpi);stream=io.BytesIO();rgb.save(stream,"JPEG",quality=100,subsampling=0,dpi=(dpi,dpi),optimize=False)
                    # Physical PDF geometry is authoritative, never inferred from preview DPI.
                    # A4 is exactly 210 x 297 mm; 4x6 is exactly 4 x 6 inch.
                    if image.size==A4_SIZE:
                        width_pt,height_pt=210.0*72/25.4,297.0*72/25.4
                    elif image.size==SHEET_SIZE:
                        width_pt,height_pt=4.0*72,6.0*72
                    else:
                        width_pt,height_pt=rgb.width*72/dpi,rgb.height*72/dpi
                    page=document.new_page(width=width_pt,height=height_pt);page.insert_image(page.rect,stream=stream.getvalue())
                    self.post_ui(lambda n=number:(overlay.update(n,len(source_pages),"PREPARING OUTPUT","PDF pages safely ban rahe hain"),status.set(f"Saving {n}/{len(source_pages)} PDF page(s)…")))
                document.save(temporary,garbage=4,deflate=True);document.close()
                with pymupdf.open(temporary) as check:
                    if check.page_count!=len(source_pages):raise ValueError("PDF verification page count mismatch")
                os.replace(temporary,path)
                self.post_ui(lambda:(overlay.close(),setattr(self,"saving",False),status.set(f"PDF saved: {path.name}"),messagebox.showinfo("PDF Saved",f"{len(source_pages)} page PDF safely saved:\n{path}",parent=parent)))
            except Exception as exc:
                try:
                    if temporary.exists():temporary.unlink()
                except Exception:pass
                error=str(exc);cancelled=isinstance(exc,InterruptedError);self.post_ui(lambda e=error,c=cancelled:(overlay.close(),setattr(self,"saving",False),status.set("PDF save cancelled." if c else "PDF save failed."),friendly_problem(parent,"PDF Save Error",e,"Writable folder select karein, same PDF kisi viewer me open ho to close karein, phir Save PDF dobara dabayein.")))
        threading.Thread(target=work,daemon=True).start()

    def export_async(self,items,mode,out,parent,status):
        """Encode the user-selected raster format off the Tk event loop."""
        out=Path(out);named_output=bool(out.suffix);folder=out.parent if named_output else out;base_name=re.sub(r"[^A-Za-z0-9_-]+","_",out.stem) if named_output else "";extension=out.suffix.lower() if named_output else ".jpg"
        if self.saving:
            messagebox.showinfo("Save Already Running","Pichla Save complete hone tak wait karein.",parent=parent);return
        self.saving=True;status.set(f"Saving high-quality {extension.upper()} files in background…");overlay=CenterProcessingOverlay(parent,"PREPARING OUTPUT",max(1,len(items)),True)
        snapshot=[]
        front_positions=[];back_positions=[]
        for index,item in enumerate(items):
            front,back=item["front"],item["back"]
            snapshot.append((item["path"].stem,front,back,item.get("rotate_back_4x6",True) if mode=="4x6" else item.get("rotate_back",False)))
            front_positions.append(tuple(item.get("a4_pos_front",default_a4_position(index))));back_positions.append(tuple(item.get("a4_pos_back",default_a4_position(index))))
        def work():
            try:
                folder.mkdir(parents=True,exist_ok=True)
                ensure_output_capacity(folder,sum(front.width*front.height+back.width*back.height for _,front,back,_ in snapshot)*1.2)
                used_paths=set()
                if mode=="4x6":
                    for number,(stem,front,back,rotate_back) in enumerate(snapshot,1):
                        if overlay.cancelled:raise InterruptedError("Save user ne cancel kiya")
                        name=base_name if named_output else re.sub(r"[^A-Za-z0-9_-]+","_",stem)
                        filename=f"{name}_{number:03d}{extension}" if named_output and len(snapshot)>1 else f"{name}{extension}" if named_output else f"Seema_Digital_Maha_ID_{name}_4x6{extension}"
                        target=unique_output_path(folder,filename,used_paths)
                        save_image_max(make_4x6(front,back,rotate_back,self.x_offset_mm,self.y_offset_mm,items[0].get("pair_gap_mm",0)),target,self.export_dpi)
                        self.post_ui(lambda n=number:overlay.update(n,len(snapshot),"PREPARING OUTPUT","High-quality output ban raha hai"))
                    result=f"{len(snapshot)} approved 4×6 JPG file(s) saved."
                elif mode in ("a4pair4","a4pair5"):
                    pair_items=[{"front":front,"back":back,"rotate_back":rotate} for _,front,back,rotate in snapshot]
                    if mode=="a4pair5":
                        pair_positions=[tuple(item.get("a4_pos_pair5",a4_five_pair_positions(len(items))[index])) for index,item in enumerate(items)];pages=make_a4_five_pairs(pair_items,items[0].get("vgap_mm",1.2),pair_positions);stem="5_CARD"
                    else:
                        pair_positions=[tuple(item.get("a4_pos_pair",a4_pair_positions(len(items))[index])) for index,item in enumerate(items)];pages=make_a4_pairs(pair_items,items[0].get("hgap_mm",2),items[0].get("vgap_mm",8),pair_positions);stem="4_CARD"
                    for n,page in enumerate(pages,1):save_image_max(page,unique_output_path(folder,f"Seema_Digital_Maha_ID_{stem}_A4_{n:03d}{extension}",used_paths),self.export_dpi)
                    result=f"{len(pages)} A4 page(s) saved; har front/back card 90×57 mm locked hai."
                elif mode=="a4":
                    fronts=make_a4([front for _,front,_,_ in snapshot],front_positions)
                    for n,page in enumerate(fronts,1):save_image_max(page,unique_output_path(folder,f"Seema_Digital_Maha_ID_A4_FRONT_{n:03d}{extension}",used_paths),self.export_dpi)
                    result=f"{len(fronts)} Front-only A4 {extension.upper()} page(s) saved."
                else:
                    backs=make_a4([back.rotate(180,expand=True) if rotate else back for _,_,back,rotate in snapshot],back_positions)
                    for n,page in enumerate(backs,1):save_image_max(page,unique_output_path(folder,f"Seema_Digital_Maha_ID_A4_BACK_{n:03d}{extension}",used_paths),self.export_dpi)
                    result=f"{len(backs)} Back A4 JPG page(s) saved."
                self.post_ui(lambda:(overlay.close(),setattr(self,"saving",False),status.set("Save complete."),messagebox.showinfo("Saved",result,parent=parent)))
            except Exception as exc:
                error=str(exc);cancelled=isinstance(exc,InterruptedError);self.post_ui(lambda e=error,c=cancelled:(overlay.close(),setattr(self,"saving",False),status.set("Save cancelled." if c else "Save failed."),friendly_problem(parent,"Save Error",e,"Output folder writable rakhein, same file open ho to close karein aur Save Final Output dobara dabayein.")))
        threading.Thread(target=work,daemon=True).start()

def run():
    """Start the desktop application from source or a packaged Windows EXE."""
    set_windows_app_identity();root=Tk();application=MahaIDApp(root)
    if "--smoke-test" in sys.argv:
        report=Path(sys.argv[sys.argv.index("--smoke-test")+1]);errors=[]
        root.report_callback_exception=lambda typ,error,tb:errors.append(str(error))
        def check():
            try:
                assert application.home_canvas.winfo_ismapped(),"Home window is not visible"
                assert application._premium_scale>0,"Home did not render"
                assert not errors,errors
                report.write_text(json.dumps({"version":APP_VERSION,"ready":True,"home_size":[root.winfo_width(),root.winfo_height()]}),encoding="utf-8")
            finally:root.destroy()
        root.after(6500,check)
    root.mainloop()

if __name__=="__main__":run()
