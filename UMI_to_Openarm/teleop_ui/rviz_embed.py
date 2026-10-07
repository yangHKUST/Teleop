"""Session-owned RViz discovery and verified native X11 reparenting."""
import ctypes as C
from contextlib import contextmanager
from pathlib import Path
import time


def descendants(root):
    parents = {}
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().rsplit(')', 1)[1].split()
            parents[int(path.parent.name)] = int(fields[1])
        except (OSError, ValueError, IndexError):
            pass
    owned = {root}
    while True:
        new = {pid for pid, parent in parents.items() if parent in owned} - owned
        if not new:
            return owned
        owned |= new


class XErrorEvent(C.Structure):
    _fields_=[("type",C.c_int),("display",C.c_void_p),("resource",C.c_ulong),("serial",C.c_ulong),("error",C.c_ubyte),("request",C.c_ubyte),("minor",C.c_ubyte)]


class WindowAttributes(C.Structure):
    _fields_ = [(name, C.c_int) for name in ("x", "y", "width", "height", "border_width", "depth")] + [
        ("visual", C.c_void_p), ("root", C.c_ulong), ("window_class", C.c_int),
        ("bit_gravity", C.c_int), ("win_gravity", C.c_int), ("backing_store", C.c_int),
        ("backing_planes", C.c_ulong), ("backing_pixel", C.c_ulong), ("save_under", C.c_int),
        ("colormap", C.c_ulong), ("map_installed", C.c_int), ("map_state", C.c_int),
        ("all_event_masks", C.c_long), ("your_event_mask", C.c_long),
        ("do_not_propagate_mask", C.c_long), ("override_redirect", C.c_int), ("screen", C.c_void_p)]


class X11:
    def __init__(self):
        self.x = x = C.CDLL('libX11.so.6')
        def api(name, arguments, result=C.c_int):
            fn=getattr(x,name); fn.argtypes=arguments; fn.restype=result
        d=C.c_void_p; w=C.c_ulong; ptr=C.POINTER
        api('XOpenDisplay',[C.c_char_p],d)
        api('XCloseDisplay',[d]); api('XDefaultRootWindow',[d],w)
        api('XDefaultScreen',[d]); api('XSync',[d,C.c_int])
        api('XQueryTree',[d,w,ptr(w),ptr(w),ptr(ptr(w)),ptr(C.c_uint)])
        api('XFetchName',[d,w,ptr(C.c_char_p)])
        api('XGetWindowAttributes',[d,w,ptr(WindowAttributes)])
        api('XInternAtom',[d,C.c_char_p,C.c_int],w)
        api('XGetWindowProperty',[d,w,w,C.c_long,C.c_long,C.c_int,w,ptr(w),ptr(C.c_int),ptr(w),ptr(w),ptr(ptr(C.c_ubyte))])
        api('XFree',[d]); api('XSetErrorHandler',[d],d)
        api('XWithdrawWindow',[d,w,C.c_int]); api('XUnmapWindow',[d,w])
        api('XReparentWindow',[d,w,w,C.c_int,C.c_int])
        api('XResizeWindow',[d,w,C.c_uint,C.c_uint]); api('XMapWindow',[d,w])
        api('XSetWindowBorderWidth',[d,w,C.c_uint])
        api('XSetWindowBackgroundPixmap',[d,w,w])
        api('XSetWindowBorder',[d,w,w])
        self.display=x.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError('无法连接 X11 显示服务器')
        self.root=x.XDefaultRootWindow(self.display)
        self.last_errors=[]
        self.handler_type=C.CFUNCTYPE(C.c_int,d,d)
        self.handler=self.handler_type(self.on_error)

    def on_error(self,display,error):
        event=C.cast(error,C.POINTER(XErrorEvent)).contents
        self.last_errors.append((event.error,event.request,event.resource))
        return 0

    @contextmanager
    def guarded(self):
        self.last_errors=[]
        previous=self.x.XSetErrorHandler(C.cast(self.handler,C.c_void_p))
        try:
            yield
        finally:
            self.x.XSync(self.display,False)
            self.x.XSetErrorHandler(previous)

    def property(self,window,name):
        atom=self.x.XInternAtom(self.display,name.encode(),False)
        actual=C.c_ulong(); fmt=C.c_int(); count=C.c_ulong(); remain=C.c_ulong(); data=C.POINTER(C.c_ubyte)()
        status=self.x.XGetWindowProperty(self.display,window,atom,0,4096,False,0,C.byref(actual),C.byref(fmt),C.byref(count),C.byref(remain),C.byref(data))
        try:
            if status or not data: return None
            if fmt.value==32:
                return list(C.cast(data,C.POINTER(C.c_ulong))[:count.value])
            if fmt.value==8:
                return C.string_at(data,count.value)
            return None
        finally:
            if data:self.x.XFree(data)

    def tree(self,window):
        root=C.c_ulong(); parent=C.c_ulong(); children=C.POINTER(C.c_ulong)(); count=C.c_uint()
        success=self.x.XQueryTree(self.display,window,C.byref(root),C.byref(parent),C.byref(children),C.byref(count))
        try:
            return (parent.value,list(children[:count.value])) if success else (None,[])
        finally:
            if children:self.x.XFree(children)

    def attributes(self,window):
        attributes=WindowAttributes()
        return attributes if self.x.XGetWindowAttributes(self.display,window,C.byref(attributes)) else None

    def title(self,window):
        modern=self.property(window,'_NET_WM_NAME')
        if isinstance(modern,bytes):return modern.decode(errors='replace')
        name=C.c_char_p();self.x.XFetchName(self.display,window,C.byref(name))
        try:return name.value.decode(errors='replace') if name.value else ''
        finally:
            if name:self.x.XFree(name)

    def close(self):
        if self.display:
            with self.guarded():self.x.XSync(self.display,False)
            self.x.XCloseDisplay(self.display);self.display=None


def find_rviz(root, owned_pids=None):
    """Identify by PID + executable/class/title, not only legacy WM_NAME."""
    connection=X11()
    try:
        owned=descendants(root) | set(owned_pids or ())
        with connection.guarded():
            clients=connection.property(connection.root,'_NET_CLIENT_LIST') or []
            tree=[connection.root]; seen=set(); candidates=[]
            for window in [*clients,*tree]:
                # First collect top-level managed windows; recursive pass follows.
                if window not in seen:candidates.append(window);seen.add(window)
            for window in tree:
                _,children=connection.tree(window)
                for child in children:
                    if child not in seen:candidates.append(child);seen.add(child)
                    tree.append(child)
            for window in candidates:
                pids=connection.property(window,'_NET_WM_PID') or []
                if not pids or pids[0] not in owned:continue
                attributes=connection.attributes(window)
                if not attributes or attributes.map_state!=2 or attributes.override_redirect or attributes.width<200 or attributes.height<150:continue
                title=connection.title(window)
                types=connection.property(window,'_NET_WM_WINDOW_TYPE') or []
                splash=connection.x.XInternAtom(connection.display,b'_NET_WM_WINDOW_TYPE_SPLASH',False)
                if splash in types:continue
                wmclass=connection.property(window,'WM_CLASS') or b''
                try:executable=Path(f'/proc/{pids[0]}/exe').resolve().name
                except OSError:executable=''
                if executable=='rviz2' or any(part in (b'rviz',b'rviz2') for part in wmclass.lower().split(b'\x00')):
                    return window
    finally:
        connection.close()
    return None


class NativeEmbedding:
    """Qt5 RViz -> Qt6 native host. Verify actual X parent before reporting success."""
    def __init__(self,window,host,width,height):
        self.connection=X11();self.window=window;self.host=host
        try:
            x=self.connection.x;d=self.connection.display
            with self.connection.guarded():
                x.XWithdrawWindow(d,window,x.XDefaultScreen(d))
                x.XUnmapWindow(d,window)
            # The window manager withdraws asynchronously. Reparenting before it
            # has removed its frame lets it put RViz back in a standalone frame.
            deadline=time.monotonic()+1.5
            while True:
                with self.connection.guarded():
                    parent,_=self.connection.tree(window)
                    attrs=self.connection.attributes(window)
                if parent==self.connection.root and attrs and attrs.map_state==0:
                    break
                if time.monotonic()>=deadline:
                    raise RuntimeError('窗口管理器尚未释放 RViz 窗口，稍后重试')
                time.sleep(.02)
            with self.connection.guarded():
                # ParentRelative backgrounds cannot cross a Qt5/Qt6 visual-depth
                # boundary (BadMatch). Use a concrete background before reparent.
                x.XSetWindowBackgroundPixmap(d,window,0)
                x.XSetWindowBorder(d,window,0)
                x.XReparentWindow(d,window,host,0,0)
                x.XSetWindowBorderWidth(d,window,0)
                x.XResizeWindow(d,window,max(1,width),max(1,height))
                x.XMapWindow(d,window)
            errors=list(self.connection.last_errors)
            if not self.is_attached():
                wa=self.connection.attributes(window); ha=self.connection.attributes(host)
                info=lambda a: (a.root,a.depth,a.window_class) if a else None
                raise RuntimeError(f'RViz 窗口没有进入界面容器：目标={host}，实际父窗口={self.connection.tree(window)[0]}，X11错误={errors}，RViz属性={info(wa)}，容器属性={info(ha)}')
        except Exception:
            with self.connection.guarded():
                parent,_=self.connection.tree(window)
                if parent is not None:
                    x.XReparentWindow(d,window,self.connection.root,0,0)
                    x.XMapWindow(d,window)
            self.close();raise

    def is_attached(self):
        with self.connection.guarded():
            parent,_=self.connection.tree(self.window)
        return parent==self.host

    def resize(self,width,height):
        with self.connection.guarded():
            self.connection.x.XResizeWindow(self.connection.display,self.window,max(1,width),max(1,height))

    def close(self):
        if self.connection.display:
            # Do not destroy an externally-owned RViz window with the Qt container.
            with self.connection.guarded():
                parent,_=self.connection.tree(self.window)
                if parent==self.host:
                    self.connection.x.XReparentWindow(self.connection.display,self.window,self.connection.root,0,0)
                    self.connection.x.XMapWindow(self.connection.display,self.window)
            self.connection.close()


def hide_window(window):
    """Hide the original session RViz; our isolated view replaces only its display."""
    connection=X11()
    try:
        with connection.guarded():
            connection.x.XWithdrawWindow(connection.display,window,connection.x.XDefaultScreen(connection.display))
            connection.x.XUnmapWindow(connection.display,window)
    finally:connection.close()
