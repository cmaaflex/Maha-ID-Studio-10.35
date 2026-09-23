"""Version-scoped cleanup: exact app targets only, no recursive deletion."""
from dataclasses import dataclass
from pathlib import Path
import ctypes, datetime, json, os, re, subprocess

UNINSTALL=r'Software\Microsoft\Windows\CurrentVersion\Uninstall'
IDS=('{80B01F80-14D9-4D3A-B9CF-5E5366E1F411}_is1','{281D2A77-F8D9-45F3-A579-10350000C0DE}_is1')

@dataclass(frozen=True)
class Installation:
    version:str
    folder:Path
    executable:Path
    hive:str=''
    key:str=''
    view:int=0
    uninstaller:str=''

@dataclass(frozen=True)
class Candidate:
    kind:str
    path:str
    size:int=0
    modified:str=''
    hive:str=''
    key:str=''
    value:str=''
    view:int=0
    signature:str=''

def registry():
    import winreg
    return winreg

def safe_child(folder,path):
    folder=Path(os.path.abspath(folder));path=Path(os.path.abspath(path))
    if not folder.is_absolute() or folder.parent==folder:return False
    try:
        if folder.is_symlink() or getattr(folder,'is_junction',lambda:False)():return False
        if not path.is_relative_to(folder) or path==folder:return False
        part=path
        while part!=folder:
            if part.is_symlink() or getattr(part,'is_junction',lambda:False)():return False
            part=part.parent
        return path.resolve().is_relative_to(folder.resolve())
    except (OSError,ValueError):return False

def discover():
    w=registry();found=[]
    for hive in ('HKEY_CURRENT_USER','HKEY_LOCAL_MACHINE'):
        for view in (w.KEY_WOW64_64KEY,w.KEY_WOW64_32KEY):
            for identifier in IDS:
                key_name=UNINSTALL+'\\'+identifier
                try:
                    with w.OpenKey(getattr(w,hive),key_name,0,w.KEY_READ|view) as key:
                        def get(name):
                            try:return str(w.QueryValueEx(key,name)[0])
                            except OSError:return ''
                        v=get('DisplayVersion');loc=get('InstallLocation')
                        if get('Publisher').casefold()!='seema digital' or not re.fullmatch(r'10\.\d+(?:\.\d+)*',v) or not loc:continue
                        folder=Path(loc);exe=folder/f'MAHA ID SOFTWARE {v}.exe'
                        if not safe_child(folder,exe):continue
                        item=Installation(v,folder,exe,hive,key_name,view,get('UninstallString'))
                        if not any(x.folder==folder and x.version==v for x in found):found.append(item)
                except FileNotFoundError:pass
    return found

def portable(executable):
    exe=Path(executable).absolute();match=re.fullmatch(r'MAHA ID SOFTWARE (10\.\d+)\.exe',exe.name,re.I)
    if not match or not exe.is_file() or not safe_child(exe.parent,exe):raise ValueError('Choose the original MAHA ID SOFTWARE <version>.exe in its portable folder.')
    return Installation(match[1],exe.parent,exe)

def allowed_files(app):
    names=[f'MAHA ID SOFTWARE {app.version}.exe',f'MAHA ID SOFTWARE {app.version} Remover.exe']
    if app.key:names+=['unins000.exe','unins000.dat','unins000.msg','HOW TO USE.txt','PRINT SETTINGS.txt','VERSION AND CHECKSUM.txt','Brand/Seema Digital Logo.png','Brand/Seema Digital Splash.jpg']
    return [app.folder/n for n in names]

def settings_files(app):
    if app.version!='10.36':return []  # Legacy settings are shared by older versions.
    base=Path(os.environ.get('APPDATA',Path.home()/'AppData/Roaming'))/'Seema Digital'
    return [base/f'Maha id settings 10.36.{ext}' for ext in ('json','bak','tmp')]

def shortcut_files(app):
    if app.version!='10.36':return []
    roaming=Path(os.environ.get('APPDATA',Path.home()/'AppData/Roaming'))
    return [Path.home()/'Desktop/Maha ID Studio 10.36.lnk',roaming/'Microsoft/Windows/Start Menu/Programs/SEEMA DIGITAL 10.36/Maha ID Studio.lnk',roaming/'Microsoft/Windows/Start Menu/Programs/SEEMA DIGITAL 10.36/Maha ID Studio Remover.lnk']

def registry_candidates(app,advanced=False):
    w=registry();result=[]
    if app.key:
        try:
            with w.OpenKey(getattr(w,app.hive),app.key,0,w.KEY_READ|app.view):pass
            result.append(Candidate('Registry key',app.hive+'\\'+app.key,hive=app.hive,key=app.key,view=app.view))
        except FileNotFoundError:pass
    if advanced:
        key=r'Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache'
        try:
            with w.OpenKey(w.HKEY_CURRENT_USER,key) as handle:
                for i in range(w.QueryInfoKey(handle)[1]):
                    name,_,_=w.EnumValue(handle,i)
                    if name.casefold() in {str(app.executable).casefold()+s for s in ('.friendlyappname','.applicationcompany')}:
                        result.append(Candidate('Registry value','HKCU\\'+key+' :: '+name,hive='HKEY_CURRENT_USER',key=key,value=name))
        except FileNotFoundError:pass
    return result

def scan(app,mode='Safe',settings=False,prefetch=False,cancelled=None):
    found=[];notes=[];paths=allowed_files(app)
    if mode in ('Moderate','Advanced'):paths+=shortcut_files(app)
    if settings:paths+=settings_files(app)
    if prefetch and mode=='Advanced':
        base=Path(os.environ.get('WINDIR','C:/Windows'))/'Prefetch'
        try:paths+=list(base.glob(f'MAHA ID SOFTWARE {app.version}.EXE-*.pf'))
        except OSError as e:notes.append('Prefetch: '+str(e))
    for path in paths:
        if cancelled and cancelled.is_set():notes.append('Scan cancelled; list is incomplete.');break
        try:
            if path.is_file() and safe_child(path.parent,path):
                st=path.stat();found.append(Candidate('File',str(path),st.st_size,datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M'),signature=f'{st.st_mtime_ns}:{st.st_ctime_ns}'))
        except OSError as e:notes.append(str(e))
    if not cancelled or not cancelled.is_set():
        try:found+=registry_candidates(app,mode=='Advanced')
        except OSError as e:notes.append('Registry scan incomplete: '+str(e))
    return found,notes

def backup_registry(app,candidates,destination):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    keys={(c.hive,c.key,c.view) for c in candidates if c.kind.startswith('Registry')}
    if app.key:keys.add((app.hive,app.key,app.view))
    files=[];w=registry()
    for index,(hive,key,view) in enumerate(sorted(keys)):
        try:
            with w.OpenKey(getattr(w,hive),key,0,w.KEY_READ|view) as handle:
                # Export exact typed values via a JSON backup; suitable for recovery with restore_backup.
                values=[w.EnumValue(handle,i) for i in range(w.QueryInfoKey(handle)[1])]
                if w.QueryInfoKey(handle)[0]:raise ValueError('Registry key has subkeys; manual review required before deletion.')
        except FileNotFoundError:continue
        target=destination/f'registry-{index+1}.json'
        data={'hive':hive,'key':key,'view':view,'values':[(n,list(v) if isinstance(v,bytes) else v,t) for n,v,t in values]}
        target.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8');files.append(str(target))
    return files

def restore_backup(path):
    w=registry();data=json.loads(Path(path).read_text(encoding='utf-8'))
    with w.CreateKeyEx(getattr(w,data['hive']),data['key'],0,w.KEY_SET_VALUE|data['view']) as handle:
        for name,value,kind in data['values']:w.SetValueEx(handle,name,0,kind,bytes(value) if kind==w.REG_BINARY else value)

def restore_point():
    result=subprocess.run(['powershell.exe','-NoProfile','-Command','$ErrorActionPreference="Stop"; Checkpoint-Computer -Description "Before MAHA ID removal" -RestorePointType MODIFY_SETTINGS'],capture_output=True,text=True,timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    return result.returncode==0,(result.stderr or result.stdout).strip()

def built_in_uninstaller(app):
    match=re.match(r'^"([^"\r\n]+\.exe)"|^(.+?\.exe)(?:\s|$)',app.uninstaller,re.I)
    if not match:return None
    path=Path(match.group(1) or match.group(2))
    if path.parent!=app.folder or not re.fullmatch(r'unins\d+\.exe',path.name,re.I) or not safe_child(app.folder,path):return None
    return path if path.is_file() else None

def delete_selected(app,selected,mode,settings,prefetch,report_dir):
    current,_=scan(app,mode,settings,prefetch);selected=list(selected)
    if any(c not in current for c in selected):raise ValueError('Targets changed. Re-scan before deleting.')
    backups=backup_registry(app,selected,report_dir)
    result={'removed':[],'failed':[],'pending_restart':[],'backup_files':backups}
    for c in selected:
        try:
            if c.kind=='File':
                path=Path(c.path)
                if not safe_child(path.parent,path):raise ValueError('Unsafe redirected path')
                path.unlink()
            else:
                w=registry();hive=getattr(w,c.hive)
                if c.kind=='Registry value':
                    with w.OpenKey(hive,c.key,0,w.KEY_SET_VALUE|c.view) as handle:w.DeleteValue(handle,c.value)
                else:w.DeleteKeyEx(hive,c.key,c.view,0)
            result['removed'].append(c.path)
        except FileNotFoundError:result['removed'].append(c.path)
        except Exception as e:result['failed'].append({'path':c.path,'error':str(e),'kind':c.kind})
    if app.key:
        for path in (app.folder/'Brand',app.folder):
            try:
                if path.resolve()==path.absolute():path.rmdir()
            except OSError:pass
    return result

def schedule_restart(paths):
    scheduled=[];failed=[]
    for path in paths:
        p=Path(path)
        if not safe_child(p.parent,p) or not p.is_file():failed.append(str(p));continue
        if ctypes.windll.kernel32.MoveFileExW(str(p),None,4):scheduled.append(str(p))
        else:failed.append(str(p))
    return scheduled,failed

def report_folder():
    path=Path.home()/'Documents/MAHA ID Removal Reports'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');path.mkdir(parents=True,exist_ok=True);return path

def save_report(folder,data):
    path=Path(folder)/'removal-report.json';path.write_text(json.dumps(data,indent=2,ensure_ascii=False,default=str),encoding='utf-8');return path
