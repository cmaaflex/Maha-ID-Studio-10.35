"""MAHA ID version-selective remover; launching or scanning never deletes files."""
import ctypes, queue, subprocess, sys, threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from maha_id_studio import removal as engine

BG='#020916';PANEL='#0b1d36';CYAN='#21d8ff';WHITE='#f4f8ff'

class Remover:
    def __init__(self,root):
        self.root=root;root.title('MAHA ID SOFTWARE 10.35 — Complete Remover');root.geometry('1040x780');root.minsize(780,590);root.configure(bg=BG)
        self.events=queue.Queue();self.busy=False;self.cancelled=threading.Event();self.installations=[];self.candidates=[];self.target=None;self.result={};self.folder=None
        self.version=tk.StringVar(master=root,value='');self.mode=tk.StringVar(master=root,value='Safe')
        self.settings=tk.BooleanVar(master=root,value=False);self.prefetch=tk.BooleanVar(master=root,value=False);self.restore=tk.BooleanVar(master=root,value=False)
        self.status=tk.StringVar(master=root,value='Choose the exact version to remove. Nothing selected automatically.')
        tk.Label(root,text='SEEMA DIGITAL  •  MAHA ID REMOVER',font=('Segoe UI',20,'bold'),fg=CYAN,bg=BG).pack(pady=12)
        tk.Label(root,text='Personal PDFs, photos, exported cards and original ZIP backups are preserved.',fg=WHITE,bg=BG).pack()
        controls=tk.Frame(root,bg=PANEL,padx=15,pady=10);controls.pack(fill='x',padx=15,pady=10)
        tk.Label(controls,text='Version / location',fg=CYAN,bg=PANEL).grid(row=0,column=0,sticky='w')
        self.combo=ttk.Combobox(controls,textvariable=self.version,state='readonly',width=65);self.combo.grid(row=0,column=1,sticky='ew',padx=8)
        self.button(controls,'Browse portable EXE',self.browse).grid(row=0,column=2);controls.columnconfigure(1,weight=1)
        modes=tk.Frame(controls,bg=PANEL);modes.grid(row=1,column=0,columnspan=3,sticky='w',pady=8)
        for name in ('Safe','Moderate','Advanced'):tk.Radiobutton(modes,text=name,variable=self.mode,value=name,bg=PANEL,fg=WHITE,selectcolor=BG,command=self.options_changed).pack(side='left',padx=10)
        tk.Label(controls,text='Safe: known files + uninstall entry | Moderate: shortcuts too | Advanced: exact app registry traces',fg=WHITE,bg=PANEL,wraplength=900).grid(row=2,column=0,columnspan=3,sticky='w')
        for row,(label,var) in enumerate((('Create Windows restore point (requires enabled System Protection)',self.restore),('Remove version-specific settings / calibration (legacy shared settings are kept)',self.settings),('Include this version’s Prefetch files (Advanced mode only)',self.prefetch)),3):
            tk.Checkbutton(controls,text=label,variable=var,bg=PANEL,fg=WHITE,selectcolor=BG,command=self.options_changed).grid(row=row,column=0,columnspan=3,sticky='w')
        tk.Label(controls,text='App registry backup is mandatory before deletion. Other versions are preserved.',fg=CYAN,bg=PANEL).grid(row=6,column=0,columnspan=3,sticky='w',pady=4)
        tk.Label(root,textvariable=self.status,fg=CYAN,bg=BG,wraplength=980,justify='left').pack(fill='x',padx=16,pady=5)
        self.progress=ttk.Progressbar(root,mode='indeterminate');self.progress.pack(fill='x',padx=16)
        actions=tk.Frame(root,bg=BG);actions.pack(side='bottom',fill='x',padx=12,pady=10)
        rows=[(('Select All',self.select_all),('Deselect All',self.deselect),('Delete Selected',self.delete),('Scan / Re-scan',self.scan),('Back',self.back),('Next / Finish',self.finish)),(('Analyse / Uninstall',self.uninstall),('Retry after restart',self.restart),('Save Report',self.report),('Restore Registry Backup',self.restore_backup),('Administrator',self.elevate),('Cancel',self.cancel))]
        for entries in rows:
            row=tk.Frame(actions,bg=BG);row.pack(fill='x',pady=3)
            for label,action in entries:self.button(row,label,action).pack(side='left',fill='x',expand=True,padx=3)
        area=tk.Frame(root,bg=PANEL);area.pack(fill='both',expand=True,padx=16,pady=8)
        self.tree=ttk.Treeview(area,columns=('kind','path','size','date'),show='headings',selectmode='extended')
        for name,width in (('kind',105),('path',565),('size',90),('date',135)):
            self.tree.heading(name,text=name.title());self.tree.column(name,width=width,minwidth=60)
        h=ttk.Scrollbar(area,orient='horizontal',command=self.tree.xview);h.pack(side='bottom',fill='x')
        v=ttk.Scrollbar(area,orient='vertical',command=self.tree.yview);v.pack(side='right',fill='y')
        self.tree.configure(xscrollcommand=h.set,yscrollcommand=v.set);self.tree.pack(fill='both',expand=True)
        self.combo.bind('<<ComboboxSelected>>',lambda _:self.options_changed());root.protocol('WM_DELETE_WINDOW',self.cancel)
        root.after(40,self.poll);self.run(engine.discover,self.loaded)

    def button(self,parent,text,action):
        return tk.Button(parent,text=text,command=action,bg='#cf1833' if 'Delete' in text else '#103458',fg=WHITE,activebackground='#0753a8',activeforeground=WHITE,relief='flat',pady=8,wraplength=135)
    def run(self,work,done):
        if self.busy:return
        self.busy=True;self.cancelled.clear();self.progress.start();self.combo.configure(state='disabled')
        def worker():
            try:self.events.put((done,work(),None))
            except Exception as e:self.events.put((done,None,e))
        threading.Thread(target=worker,daemon=True).start()
    def poll(self):
        try:
            done,result,error=self.events.get_nowait();self.busy=False;self.progress.stop();self.combo.configure(state='readonly')
            if error:self.status.set('Operation incomplete: '+str(error));messagebox.showerror('Remover',str(error),parent=self.root)
            else:done(result)
        except queue.Empty:pass
        self.root.after(40,self.poll)
    def loaded(self,items):
        self.installations=items;self.combo.configure(values=[f'{x.version} — {x.folder}' for x in items]);self.status.set('Choose a version or browse its portable EXE. No version is selected.')
    def browse(self):
        if self.busy:return
        path=filedialog.askopenfilename(parent=self.root,filetypes=[('MAHA ID portable EXE','*.exe')])
        if not path:return
        try:
            record=engine.portable(path);self.installations.append(record);self.combo.configure(values=[f'{x.version} — {x.folder}' for x in self.installations]);self.combo.current(len(self.installations)-1);self.options_changed()
        except Exception as e:messagebox.showerror('Portable version',str(e),parent=self.root)
    def options_changed(self):
        if self.busy:return
        self.candidates=[];self.tree.delete(*self.tree.get_children());self.result={};self.target=None;self.folder=None;self.status.set('Options changed. Scan again before selecting items.')
    def choose(self):
        index=self.combo.current()
        if index<0:messagebox.showinfo('Select version','Choose the exact installed or portable version first.',parent=self.root);return None
        return self.installations[index]
    def scan(self):
        if self.busy:return
        self.target=self.choose()
        if not self.target:return
        self.scan_options=(self.mode.get(),self.settings.get(),self.prefetch.get());target=self.target;options=self.scan_options
        self.status.set('Scanning selected version only…');self.run(lambda:engine.scan(target,*options,self.cancelled),self.scanned)
    def scanned(self,result):
        self.candidates,notes=result;self.tree.delete(*self.tree.get_children())
        for i,c in enumerate(self.candidates):self.tree.insert('','end',iid=str(i),values=(c.kind,c.path,f'{c.size:,}' if c.kind=='File' else '',c.modified))
        self.status.set(f'{len(self.candidates)} app items found. Select explicitly. '+' '.join(notes));self.result['scan_notes']=notes
    def select_all(self):
        if not self.busy:self.tree.selection_set(self.tree.get_children())
    def deselect(self):
        if not self.busy:self.tree.selection_remove(self.tree.selection())
    def uninstall(self):
        if self.busy:return
        target=self.choose()
        if not target:return
        if not messagebox.askyesno('Confirm version',f'Remove MAHA ID {target.version} from:\n{target.folder}\n\nSave your work and close this version first. Other versions and personal output stay safe. Continue?',parent=self.root):return
        uninstaller=engine.built_in_uninstaller(target);self.folder=engine.report_folder();restore=self.restore.get();self.target=target
        self.status.set('Backing up app registry and checking restore point…')
        def prepare():return engine.backup_registry(target,[],self.folder),engine.restore_point() if restore else (None,'Not requested')
        def prepared(result):
            backups,(ok,detail)=result;self.result={'backup_files':backups,'restore_point':{'created':ok,'detail':detail}}
            if ok is False and not messagebox.askyesno('Restore point unavailable',f'Restore point was NOT created.\n{detail}\n\nContinue with app registry backup?',parent=self.root):return
            if not uninstaller:self.status.set('Built-in uninstaller missing; scanning verified app targets.');self.scan();return
            self.status.set('Complete the built-in uninstaller prompts; leftover scan follows.')
            self.run(lambda:subprocess.run([str(uninstaller)],check=False).returncode,self.uninstalled)
        self.run(prepare,prepared)
    def uninstalled(self,code):
        self.result['uninstaller_exit_code']=code
        if code:messagebox.showwarning('Uninstaller result',f'Exit code {code}. Review remaining items; removal is not complete.',parent=self.root)
        self.scan()
    def delete(self):
        if self.busy or not self.target:return
        selected=[self.candidates[int(i)] for i in self.tree.selection()]
        if not selected:messagebox.showinfo('Select items','Select the specific leftovers to delete.',parent=self.root);return
        if not messagebox.askyesno('Delete selected leftovers',f'Permanently delete {len(selected)} selected items belonging to MAHA ID {self.target.version}?\nRegistry is backed up first.',parent=self.root):return
        self.folder=self.folder or engine.report_folder();target=self.target;options=self.scan_options
        self.status.set('Backing up registry and deleting selected items…');self.run(lambda:engine.delete_selected(target,selected,*options,self.folder),self.deleted)
    def deleted(self,result):
        self.result.update(result);self.report(quiet=True);self.status.set('Checking remaining items…');self.run(lambda:engine.scan(self.target,*self.scan_options),self.verify)
    def verify(self,result):
        self.scanned(result);self.result['remaining']=[c.path for c in self.candidates]
        complete=not self.candidates and not result[1] and not self.result.get('failed')
        self.status.set(('Cleanup complete for identified app items' if complete else 'Cleanup incomplete — review remaining items')+f'. Removed {len(self.result.get("removed",[]))}; remaining {len(self.candidates)}; failed {len(self.result.get("failed",[]))}.');self.report(quiet=True)
    def restart(self):
        if self.busy:return
        paths=[r['path'] for r in self.result.get('failed',[]) if r['kind']=='File']
        if not paths:messagebox.showinfo('Restart cleanup','No failed file deletions to schedule.',parent=self.root);return
        if not messagebox.askyesno('Schedule next restart','Schedule these failed, previously selected files for deletion at next restart?\n\n'+'\n'.join(paths),parent=self.root):return
        def done(result):
            scheduled,failed=result;self.result['pending_restart']=scheduled;self.result['restart_schedule_failed']=failed
            self.status.set(f'Pending restart: {len(scheduled)}. Scheduling failed: {len(failed)}. Restart then re-scan.');self.report(quiet=True)
        self.run(lambda:engine.schedule_restart(paths),done)
    def report(self,quiet=False):
        if self.busy:return
        self.folder=self.folder or engine.report_folder();path=engine.save_report(self.folder,{'version':self.target.version if self.target else None,'installation':str(self.target.folder) if self.target else None,**self.result})
        if not quiet:messagebox.showinfo('Removal report',str(path),parent=self.root)
    def restore_backup(self):
        if self.busy:return
        path=filedialog.askopenfilename(parent=self.root,title='Select app registry backup',filetypes=[('Registry backup JSON','registry-*.json')])
        if path and messagebox.askyesno('Restore app registry backup','Restore the registry values in this backup? Only choose a backup created by this remover.',parent=self.root):self.run(lambda:engine.restore_backup(path),lambda _:self.status.set('Registry backup restored.'))
    def back(self):
        if not self.busy:self.options_changed()
    def finish(self):
        if self.busy:return
        if self.candidates and not messagebox.askyesno('Skip leftovers?',f'{len(self.candidates)} identified items remain. Leave them and finish?',parent=self.root):return
        self.report(quiet=True);self.root.destroy()
    def cancel(self):
        if self.busy:self.cancelled.set();self.status.set('Cancel requested. Current operation finishes safely; scan stops at next item.');return
        self.root.destroy()
    def elevate(self):
        if self.busy:return
        if not messagebox.askyesno('Administrator','Restart remover as Administrator? Choose version and items again after restart.',parent=self.root):return
        args='' if getattr(sys,'frozen',False) else subprocess.list2cmdline([str(Path(__file__).resolve())])
        if ctypes.windll.shell32.ShellExecuteW(None,'runas',sys.executable,args,None,1)>32:self.root.destroy()

def main():
    root=tk.Tk();Remover(root)
    if '--smoke-test' in sys.argv:
        destination=Path(sys.argv[sys.argv.index('--smoke-test')+1])
        def ready():destination.write_text('{"ready":true,"version":"10.35","remover":true}');root.destroy()
        root.after(1200,ready)
    root.mainloop()

if __name__=='__main__':main()
