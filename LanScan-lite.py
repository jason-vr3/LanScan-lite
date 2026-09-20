import sys
import os
import time

# =====================================================================
# [沙盒核心装甲 1] 禁用缓存与修正幽灵目录 (PRODUCTION READY)
# =====================================================================
# 绝对禁止 Python 在只读的 WindowsApps 目录下生成 __pycache__，防止权限拒绝闪退
sys.dont_write_bytecode = True

# 修正工作目录：确保程序能找到自身身边的资源
try:
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(os.path.abspath(sys.executable)))
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
except Exception:
    pass

# =====================================================================
# [沙盒核心装甲 2] 黑洞拦截器：彻底屏蔽无控制台环境下的 IO 异常
# =====================================================================
class NullWriter:
    def write(self, text): pass
    def flush(self): pass
    def isatty(self): return False
    def fileno(self): return -1

if sys.stdout is None: sys.stdout = NullWriter()
if sys.stderr is None: sys.stderr = NullWriter()
if sys.stdin is None: sys.stdin = NullWriter()

# ====== 导入核心框架 ======
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import platform
import threading
import queue
import socket
import ipaddress
import uuid
import re

# =====================================================================
# [模块 1] 网络基础工具箱 (优化了底层的超时与句柄释放)
# =====================================================================
class NetworkUtils:
    @staticmethod
    def get_local_ip():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "127.0.0.1"

    @staticmethod
    def get_local_mac():
        try:
            mac_num = hex(uuid.getnode()).replace('0x', '').upper()
            return '-'.join(mac_num.zfill(12)[i:i+2] for i in range(0, 12, 2))
        except Exception:
            return "00-00-00-00-00-00"

    @staticmethod
    def get_mac_address(ip_str, local_ip):
        if platform.system().lower() != 'windows': return "-"
        if ip_str == local_ip: return NetworkUtils.get_local_mac()

        for _ in range(2):
            try:
                output = subprocess.run(['arp', '-a', ip_str], capture_output=True, creationflags=0x08000000, timeout=1, stdin=subprocess.DEVNULL)
                out_str = output.stdout.decode('oem', errors='ignore')
                for line in out_str.splitlines():
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] == ip_str:
                        mac = parts[1].upper()
                        if '-' in mac or ':' in mac: return mac
            except Exception: pass
            time.sleep(0.05)
        return "-"

    @staticmethod
    def get_default_subnet():
        local_ip = NetworkUtils.get_local_ip()
        if not local_ip or local_ip.startswith("127."):
            return "192.168.1.0/24"

        default_mask = "255.255.255.0"
        if platform.system().lower() == 'windows':
            try:
                out = subprocess.check_output(["ipconfig"], shell=False, creationflags=0x08000000, timeout=2, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL).decode('oem', errors='ignore')
                lines = out.splitlines()
                for i, line in enumerate(lines):
                    if local_ip in line:
                        for j in range(1, 4):
                            if i + j < len(lines):
                                if "Mask" in lines[i+j] or "掩码" in lines[i+j]:
                                    m = re.search(r'(\d+\.\d+\.\d+\.\d+)', lines[i+j])
                                    if m:
                                        default_mask = m.group(1)
                                        break
                        break
            except Exception:
                pass
        try:
            net = ipaddress.IPv4Interface(f"{local_ip}/{default_mask}").network
            return str(net)
        except Exception:
            return "192.168.1.0/24"

    @staticmethod
    def get_all_network_adapters_info():
        local_ip = NetworkUtils.get_local_ip()
        local_mac = NetworkUtils.get_local_mac()
        
        if platform.system().lower() != 'windows':
            return f"[ 全局默认通信网卡简述 ]\n  首选 IP  : {local_ip:<17} 物理 MAC : {local_mac}\n\n(当前系统非 Windows，详细解析功能暂不可用)"
            
        adapters = []
        try:
            out = subprocess.check_output(["ipconfig", "/all"], shell=False, creationflags=0x08000000, timeout=3, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL).decode('oem', errors='ignore')
            curr = {}
            for line in out.splitlines():
                line = line.rstrip()
                if not line: continue
                if re.match(r'^[^\s].*:$', line) and "Windows IP" not in line:
                    if curr and ('ip' in curr or 'mac' in curr): adapters.append(curr)
                    curr = {'name': line[:-1].strip(), 'status': '已连接 (Up)'}
                elif curr:
                    lower_line = line.lower()
                    if 'media disconnected' in lower_line or '媒体已断开' in lower_line:
                        curr['status'] = '已断开 (Down)'
                    elif 'description' in lower_line or '描述' in lower_line:
                        curr['desc'] = line.split(':', 1)[1].strip()
                    elif 'physical address' in lower_line or '物理地址' in lower_line:
                        curr['mac'] = line.split(':', 1)[1].strip()
                    elif 'ipv4' in lower_line:
                        ip = line.split(':', 1)[1].strip().replace('(Preferred)', '').replace('(首选)', '').strip()
                        if not curr.get('ip'): curr['ip'] = ip
                    elif 'subnet mask' in lower_line or '子网掩码' in lower_line:
                        curr['mask'] = line.split(':', 1)[1].strip()
                    elif 'default gateway' in lower_line or '默认网关' in lower_line:
                        gw = line.split(':', 1)[1].strip()
                        if gw and gw != '::' and not curr.get('gw'): curr['gw'] = gw
                    elif 'dns servers' in lower_line or 'dns 服务器' in lower_line:
                        dns = line.split(':', 1)[1].strip()
                        if dns and dns != '::' and not curr.get('dns'): curr['dns'] = dns
            if curr and ('ip' in curr or 'mac' in curr): adapters.append(curr)
        except Exception:
            pass
        
        default_ad = None
        for ad in adapters:
            if ad.get('ip') == local_ip:
                default_ad = ad
                break

        info_lines = ["[ 全局默认通信网卡简述 ]"]
        if default_ad:
            ip_str = default_ad.get('ip', local_ip)
            mask_str = default_ad.get('mask', '-')
            gw_str = default_ad.get('gw', '-')
            dns_str = default_ad.get('dns', '-')
            info_lines.append(f"  网卡描述 : {default_ad.get('desc', '-')}")
            info_lines.append(f"  网卡状态 : {default_ad.get('status', '未知')}   |   物理 MAC : {default_ad.get('mac', local_mac)}")
            info_lines.append(f"  " + "-" * 58)
            info_lines.append(f"  首选 IP  : {ip_str:<17} 子网掩码 : {mask_str}")
            info_lines.append(f"  默认网关 : {gw_str:<17} DNS 解析 : {dns_str}\n")
        else:
            info_lines.append(f"  首选 IP  : {local_ip:<17} 物理 MAC : {local_mac}")
            info_lines.append(f"  (未成功匹配到详细路由信息)\n")

        info_lines.append("[ 本机所有网卡详细状态侦测 ]")
        if adapters:
            for ad in adapters:
                info_lines.append(f"■ {ad.get('name', '未知网卡')}")
                info_lines.append(f"  ├─ 状态: {ad.get('status', '未知')}")
                info_lines.append(f"  ├─ 描述: {ad.get('desc', '-')}")
                info_lines.append(f"  ├─ IP / 掩码: {ad.get('ip', '-')} / {ad.get('mask', '-')}")
                info_lines.append(f"  ├─ MAC 地址: {ad.get('mac', '-')}")
                info_lines.append(f"  ├─ 默认网关: {ad.get('gw', '-')}")
                info_lines.append(f"  └─ DNS 服务器: {ad.get('dns', '-')}")
                info_lines.append("")
        else:
            info_lines.append("  未检测到有效网卡信息。")
            
        return "\n".join(info_lines)

# =====================================================================
# [模块 2] 任务调度引擎 (高效并发控制)
# =====================================================================
class TaskEngine:
    def __init__(self, ui_update_callback):
        self.task_queue = queue.Queue()
        self.stop_flag = threading.Event()
        self.pause_flag = threading.Event()
        self.pause_flag.set()
        
        self.workers = []
        self.ui_update_callback = ui_update_callback
        
        self.cpu_throttle_map = {"100%": 0.0, "80%": 0.01, "50%": 0.05, "30%": 0.1}

    def _worker_loop(self, worker_func, cpu_throttle):
        sleep_time = self.cpu_throttle_map.get(cpu_throttle, 0.05)
        while not self.stop_flag.is_set():
            self.pause_flag.wait() 
            if self.stop_flag.is_set(): break
            
            try: task_args = self.task_queue.get(timeout=0.3)
            except queue.Empty: break
                
            if self.stop_flag.is_set(): break
            if sleep_time > 0: time.sleep(sleep_time)
                
            result = worker_func(*task_args)
            if result and not self.stop_flag.is_set():
                self.ui_update_callback(result)
            self.task_queue.task_done()

    def start(self, tasks, worker_func, thread_count, cpu_throttle):
        self.stop_flag.clear()
        self.pause_flag.set()
        self.workers = []
        
        while not self.task_queue.empty():
            try: self.task_queue.get_nowait()
            except: break
            
        for t in tasks: self.task_queue.put(t)
            
        for _ in range(min(thread_count, len(tasks))):
            t = threading.Thread(target=self._worker_loop, args=(worker_func, cpu_throttle), daemon=True)
            t.start()
            self.workers.append(t)

    def stop(self):
        self.stop_flag.set()
        self.pause_flag.set()
        while not self.task_queue.empty():
            try: self.task_queue.get_nowait()
            except: break
    def is_alive(self): return any(t.is_alive() for t in self.workers)

# =====================================================================
# [模块 3] 存活主机扫描模块
# =====================================================================
class PingScannerModule:
    def __init__(self, app_root, parent_frame, local_ip):
        self.app = app_root
        self.parent = parent_frame
        self.local_ip = local_ip
        self.engine = TaskEngine(self.on_task_result)
        self.is_scanning = False
        self.ip_labels = {}
        self.setup_ui()
        self.app.root.after(100, self.monitor_scan)

    def setup_ui(self):
        ctrl = tk.Frame(self.parent)
        ctrl.pack(fill=tk.X, pady=(0, 10))

        tk.Label(ctrl, text="目标网络:").grid(row=0, column=0, padx=2)
        self.target_var = tk.StringVar(value=NetworkUtils.get_default_subnet())
        tk.Entry(ctrl, textvariable=self.target_var, width=15).grid(row=0, column=1, padx=2)

        tk.Label(ctrl, text="超时(ms):").grid(row=0, column=2, padx=2)
        self.timeout_var = tk.StringVar(value="300")
        tk.Entry(ctrl, textvariable=self.timeout_var, width=4).grid(row=0, column=3, padx=2)

        tk.Label(ctrl, text="线程:").grid(row=0, column=4, padx=2)
        self.threads_var = tk.StringVar(value="100")
        tk.Entry(ctrl, textvariable=self.threads_var, width=4).grid(row=0, column=5, padx=2)

        tk.Label(ctrl, text="CPU控制:").grid(row=0, column=6, padx=2)
        self.cpu_var = tk.StringVar(value="50%")
        ttk.Combobox(ctrl, textvariable=self.cpu_var, values=["30%", "50%", "80%", "100%"], width=5, state="readonly").grid(row=0, column=7, padx=2)

        tk.Label(ctrl, text="Ping次数:").grid(row=0, column=8, padx=2)
        self.count_var = tk.StringVar(value="2")
        tk.Spinbox(ctrl, from_=1, to=10, textvariable=self.count_var, width=3).grid(row=0, column=9, padx=2)

        self.start_btn = tk.Button(ctrl, text="🚀 开始", command=self.start_scan, relief=tk.RAISED, bg="#e0f7fa")
        self.start_btn.grid(row=0, column=10, padx=(10, 5))

        self.stop_btn = tk.Button(ctrl, text="🛑 停止", command=self.stop_scan, relief=tk.RAISED, state=tk.DISABLED, bg="#ffebee")
        self.stop_btn.grid(row=0, column=11, padx=5)

        nav = tk.Frame(self.parent)
        nav.pack(fill=tk.X, pady=(5, 0))
        self.btn_grid = tk.Button(nav, text=" 🟩 网格视图 ", font=("Microsoft YaHei", 9, "bold"), fg="darkgreen", command=lambda: self.switch_tab(0))
        self.btn_grid.pack(side=tk.LEFT, padx=2)
        self.btn_list = tk.Button(nav, text=" 📜 列表视图 ", font=("Microsoft YaHei", 9, "bold"), fg="indigo", command=lambda: self.switch_tab(1))
        self.btn_list.pack(side=tk.LEFT, padx=2)

        content = tk.Frame(self.parent, bd=2, relief=tk.GROOVE)
        content.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.grid_tab_frame = tk.Frame(content, bg="white")
        self.grid_canvas_widget = tk.Canvas(self.grid_tab_frame, bg="white", highlightthickness=0)
        self.grid_scrollbar = ttk.Scrollbar(self.grid_tab_frame, orient=tk.VERTICAL, command=self.grid_canvas_widget.yview)
        self.grid_canvas_widget.configure(yscrollcommand=self.grid_scrollbar.set)
        self.grid_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.grid_canvas_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.grid_canvas = tk.Frame(self.grid_canvas_widget, bg="white")
        self.grid_window_id = self.grid_canvas_widget.create_window((0, 0), window=self.grid_canvas, anchor=tk.N)

        self.grid_canvas.bind("<Configure>", lambda e: self.grid_canvas_widget.configure(scrollregion=self.grid_canvas_widget.bbox("all")))
        self.grid_canvas_widget.bind("<Configure>", lambda e: self.grid_canvas_widget.coords(self.grid_window_id, e.width // 2, 0))

        def _on_mousewheel(event):
            self.grid_canvas_widget.yview_scroll(int(-1*(event.delta/120)), "units")
        self.grid_canvas_widget.bind("<MouseWheel>", _on_mousewheel)
        self.grid_canvas.bind("<MouseWheel>", _on_mousewheel)
        self._on_mousewheel_func = _on_mousewheel 

        self.list_frame = tk.Frame(content)
        cols = ("ip", "mac", "hostname", "delay", "status")
        self.tree = ttk.Treeview(self.list_frame, columns=cols, show="headings")
        for c, t, w in zip(cols, ["在线 IP 地址", "MAC 物理地址", "解析主机名", "响应时延", "状态"], [120, 160, 180, 80, 60]):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor=tk.CENTER if c != "hostname" else tk.W)
        self.app.setup_tree_copy(self.tree)
        
        scr = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scr.set)
        scr.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="就绪 - (列表模式支持右键静默复制)")
        tk.Label(self.parent, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)
        self.switch_tab(0)

    def switch_tab(self, idx):
        if idx == 0 and self.btn_grid.cget('state') == tk.DISABLED: return
        if idx == 0:
            self.list_frame.pack_forget()
            self.grid_tab_frame.pack(fill=tk.BOTH, expand=True)
            self.btn_grid.config(relief=tk.SUNKEN, bg="#e0e0e0")
            self.btn_list.config(relief=tk.RAISED, bg="#f0f0f0")
        else:
            self.grid_tab_frame.pack_forget()
            self.list_frame.pack(fill=tk.BOTH, expand=True)
            self.btn_list.config(relief=tk.SUNKEN, bg="#e0e0e0")
            self.btn_grid.config(relief=tk.RAISED, bg="#f0f0f0")

    def _ping_core(self, ip_str, timeout, count):
        is_windows = platform.system().lower() == 'windows'
        cmd = ['ping', '-n' if is_windows else '-c', str(count), '-w' if is_windows else '-W', str(timeout if is_windows else max(1, timeout//1000)), ip_str]
        kwargs = {'creationflags': 0x08000000} if is_windows else {}
        hard_timeout = (timeout * count) / 1000.0 + 2.0
        
        is_on, mac, host, delay = False, "-", "-", "-"
        try:
            out = subprocess.run(cmd, capture_output=True, timeout=hard_timeout, stdin=subprocess.DEVNULL, **kwargs)
            out_txt = out.stdout.decode('oem' if is_windows else 'utf-8', errors='ignore')
            if "TTL=" in out_txt.upper():
                is_on = True
                m = re.search(r'(?:time|时间|ms)[=<]\s*([0-9.]+)\s*ms', out_txt, re.IGNORECASE)
                delay = f"{m.group(1)} ms" if m else "<1 ms"
                mac = NetworkUtils.get_mac_address(ip_str, self.local_ip)
                try: host = socket.gethostbyaddr(ip_str)[0]
                except: pass
        except Exception: pass
        return (ip_str, mac, host, is_on, delay)

    def start_scan(self):
        if self.is_scanning: return
        try:
            net = ipaddress.ip_network(self.target_var.get().strip(), strict=False)
            ips = list(net.hosts()) or [ipaddress.ip_address(self.target_var.get().strip().split('/')[0])]
            timeout, threads = int(self.timeout_var.get()), int(self.threads_var.get())
            count = int(self.count_var.get())
            cpu_opt = self.cpu_var.get()
        except Exception:
            messagebox.showerror("错误", "参数有误！"); return

        self.is_scanning = True
        self.start_btn.config(state=tk.DISABLED, text="⏳ 扫描中")
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set(f"正在扫描 {net} ... (共 {len(ips)} 个 IP，限制 {cpu_opt} CPU)")
        
        for item in self.tree.get_children(): self.tree.delete(item)
        
        if len(ips) <= 256:
            self.btn_grid.config(state=tk.NORMAL)
            self.switch_tab(0)
            for w in self.grid_canvas.winfo_children(): w.destroy()
            self.ip_labels.clear()
            for i, ip in enumerate(ips):
                r, c, ip_s = i // 16, i % 16, str(ip)
                lbl = tk.Label(self.grid_canvas, text=ip_s.split('.')[-1], width=4, bg="#e0e0e0")
                lbl.grid(row=r, column=c, padx=1, pady=1)
                lbl.bind("<MouseWheel>", self._on_mousewheel_func)
                self.ip_labels[ip_s] = lbl
        else:
            self.btn_grid.config(state=tk.DISABLED)
            self.switch_tab(1)
            self.ip_labels.clear()

        tasks = [(str(ip), timeout, count) for ip in ips]
        self.engine.start(tasks, self._ping_core, threads, cpu_opt)

    def stop_scan(self):
        self.engine.stop()
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("🛑 正在瞬间中断任务...")

    def on_task_result(self, result):
        self.app.root.after(0, lambda: self._update_ui(result))
        
    def _update_ui(self, result):
        ip_str, mac, host, is_on, delay = result
        if ip_str in self.ip_labels:
            lbl = self.ip_labels[ip_str]
            lbl.config(bg="lime green" if is_on else "red")
            if is_on: lbl.bind("<Enter>", lambda e: self.status_var.set(f"IP: {ip_str} | MAC: {mac} | {host}"))
        if is_on:
            self.tree.insert("", tk.END, values=(ip_str, mac, host, delay, "🟢 在线"))
            self.tree.yview_moveto(1)

    def monitor_scan(self):
        if self.is_scanning and not self.engine.is_alive():
            self.is_scanning = False
            self.start_btn.config(state=tk.NORMAL, text="🚀 开始")
            self.stop_btn.config(state=tk.DISABLED)
            msg = "⏹ 扫描强行终止" if self.engine.stop_flag.is_set() else "✅ 扫描完美完成"
            self.status_var.set(f"{msg}！共发现 {len(self.tree.get_children())} 台设备。")
        self.app.root.after(200, self.monitor_scan)

# =====================================================================
# [模块 5 & 6] IPv4 / IPv6 计算器
# =====================================================================
class IPv4CalcModule:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.syncing = False
        self.setup_ui()

    def setup_ui(self):
        tk.Label(self.parent, text="IPv4 网络地址计算器", font=("Microsoft YaHei", 12, "bold"), fg="darkblue").grid(row=0, column=0, columnspan=12, sticky="w", pady=(0, 20))
        tk.Label(self.parent, text="输入 IP:", font=("Microsoft YaHei", 10, "bold")).grid(row=1, column=0, sticky="e")
        self.ips = [tk.StringVar(value=v) for v in ["192", "168", "0", "1"]]
        for i, var in enumerate(self.ips):
            tk.Entry(self.parent, textvariable=var, width=5, justify="center").grid(row=1, column=1+i, padx=3)
            var.trace_add("write", self.calc)

        tk.Label(self.parent, text="掩码位:", font=("Microsoft YaHei", 10)).grid(row=1, column=5, padx=10, sticky="e")
        self.mlen = tk.StringVar(value="24")
        tk.Spinbox(self.parent, from_=0, to=32, textvariable=self.mlen, width=4).grid(row=1, column=6)
        self.mlen.trace_add("write", self.on_len_change)

        tk.Label(self.parent, text="点分掩码:", font=("Microsoft YaHei", 10, "bold")).grid(row=2, column=0, sticky="e", pady=10)
        self.masks = [tk.StringVar(value=v) for v in ["255", "255", "255", "0"]]
        for i, var in enumerate(self.masks):
            tk.Entry(self.parent, textvariable=var, width=5, justify="center").grid(row=2, column=1+i, padx=3)
            var.trace_add("write", self.on_mask_change)

        ttk.Separator(self.parent, orient='horizontal').grid(row=3, column=0, columnspan=10, sticky="ew", pady=10)
        
        self.out = {k: [tk.StringVar() for _ in range(4 if k != "us" else 1)] for k in ["us", "net", "fst", "lst", "bc"]}
        for r, (k, lbl) in enumerate(zip(self.out.keys(), ["可用IP总数", "网络地址", "第一可用 IP", "最后可用 IP", "广播地址"]), 4):
            tk.Label(self.parent, text=lbl, font=("Microsoft YaHei", 10)).grid(row=r, column=0, sticky="e", pady=5)
            if k == "us": tk.Entry(self.parent, textvariable=self.out[k][0], state="readonly", width=12).grid(row=r, column=1, columnspan=2, sticky="w")
            else:
                for i, var in enumerate(self.out[k]): tk.Entry(self.parent, textvariable=var, state="readonly", width=8).grid(row=r, column=1+i)
        self.calc()

    def on_len_change(self, *a):
        if self.syncing: return
        self.syncing = True
        try:
            v = self.mlen.get()
            if v.isdigit() and 0<=int(v)<=32:
                ms = str(ipaddress.IPv4Network(f"0.0.0.0/{v}").netmask).split('.')
                for i, m in enumerate(ms): self.masks[i].set(m)
        except: pass
        self.syncing = False; self.calc()

    def on_mask_change(self, *a):
        if self.syncing: return
        self.syncing = True
        try:
            ms = [v.get() for v in self.masks]
            if all(ms): self.mlen.set(str(ipaddress.IPv4Network(f"0.0.0.0/{'.'.join(ms)}", strict=False).prefixlen))
        except: pass
        self.syncing = False; self.calc()

    def calc(self, *a):
        if self.syncing: return
        try:
            ip = ".".join([v.get() or "0" for v in self.ips])
            net = ipaddress.IPv4Network(f"{ip}/{self.mlen.get() or '24'}", strict=False)
            self.out["us"][0].set(str(1 if net.prefixlen==32 else (2 if net.prefixlen==31 else net.num_addresses-2)))
            for i in range(4):
                self.out["net"][i].set(str(net.network_address).split('.')[i])
                self.out["bc"][i].set(str(net.broadcast_address).split('.')[i])
                fst = lst = str(net.network_address).split('.')
                if net.prefixlen < 31: fst = str(net.network_address+1).split('.'); lst = str(net.broadcast_address-1).split('.')
                elif net.prefixlen == 31: lst = str(net.broadcast_address).split('.')
                self.out["fst"][i].set(fst[i]); self.out["lst"][i].set(lst[i])
        except: pass

class IPv6CalcModule:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.setup_ui()

    def setup_ui(self):
        tk.Label(self.parent, text="IPv6 网络地址计算器", font=("Microsoft YaHei", 12, "bold"), fg="darkgreen").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 20))
        tk.Label(self.parent, text="IPv6 地址").grid(row=1, column=0, sticky="e")
        self.ip_var = tk.StringVar(value="fe80::1a2b")
        tk.Entry(self.parent, textvariable=self.ip_var, width=35).grid(row=1, column=1, padx=5)
        self.ip_var.trace_add("write", self.calc)
        tk.Label(self.parent, text="前缀(/)").grid(row=1, column=2, sticky="e")
        self.pref = tk.StringVar(value="64")
        tk.Spinbox(self.parent, from_=0, to=128, textvariable=self.pref, width=4).grid(row=1, column=3)
        self.pref.trace_add("write", self.calc)
        ttk.Separator(self.parent, orient='horizontal').grid(row=2, column=0, columnspan=4, sticky="ew", pady=10)
        
        self.outs = [tk.StringVar() for _ in range(5)]
        for r, (var, lbl) in enumerate(zip(self.outs, ["展开形式", "网络地址", "IP 范围", "总数量", "类型"]), 3):
            tk.Label(self.parent, text=lbl).grid(row=r, column=0, sticky="e", pady=5)
            tk.Entry(self.parent, textvariable=var, state="readonly", width=55).grid(row=r, column=1, columnspan=3, sticky="w")
        self.calc()

    def calc(self, *a):
        try:
            ip, pref = self.ip_var.get(), self.pref.get() or "64"
            net = ipaddress.IPv6Network(f"{ip}/{pref}", strict=False)
            obj = ipaddress.IPv6Address(ip)
            self.outs[0].set(obj.exploded)
            self.outs[1].set(str(net.network_address))
            self.outs[2].set(str(net.network_address) if net.prefixlen==128 else f"{net.network_address} - {net.broadcast_address}")
            self.outs[3].set(f"{net.num_addresses} (约 2^{128-net.prefixlen} 个)" if net.num_addresses>1000000 else str(net.num_addresses))
            typs = []
            if obj.is_loopback: typs.append("环回")
            if obj.is_link_local: typs.append("链路本地")
            if obj.is_private: typs.append("私有")
            if obj.is_global: typs.append("全球单播")
            self.outs[4].set(" | ".join(typs) if typs else "常规")
        except:
            for v in self.outs: v.set("解析中...")

# =====================================================================
# [模块 7] 软件主架构与全局 UI
# =====================================================================
class QuickPingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lan Scan lite 网络排障专家 (Free 基础版)")
        self.root.geometry("1200x640") 
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_ui()
        
    def on_closing(self):
        try:
            import os
            os._exit(0)
        except Exception:
            self.root.destroy()

    def copy_to_clipboard(self, text, show_msg=False):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        if show_msg: messagebox.showinfo("复制成功", "已成功复制到剪贴板！")

    def setup_tree_copy(self, tree):
        def show_menu(event):
            row = tree.identify_row(event.y)
            col = tree.identify_column(event.x)
            if not row: return
            if row not in tree.selection(): tree.selection_set(row)
            
            menu = tk.Menu(self.root, tearoff=0)
            sel = tree.selection()
            if len(sel) > 1:
                menu.add_command(label=f"📋 复制选中的 {len(sel)} 行", 
                                 command=lambda: self.copy_to_clipboard("\n".join("\t".join(str(v) for v in tree.item(i, 'values')) for i in sel)))
            else:
                if col:
                    idx = int(col.replace('#', '')) - 1
                    val = str(tree.item(row, 'values')[idx])
                    menu.add_command(label=f"📋 复制: {val[:15]}...", command=lambda: self.copy_to_clipboard(val))
                menu.add_command(label="📋 复制整行", command=lambda: self.copy_to_clipboard("\t".join(str(v) for v in tree.item(row, 'values'))))
            menu.tk_popup(event.x_root, event.y_root)
        tree.bind("<Button-3>", show_menu)
        tree.bind("<Button-2>", show_menu)

    def setup_text_copy(self, text_widget):
        def copy_selection():
            try: self.copy_to_clipboard(text_widget.selection_get())
            except tk.TclError: pass
                
        def copy_all():
            self.copy_to_clipboard(text_widget.get(1.0, tk.END).strip())

        def show_menu(event):
            menu = tk.Menu(self.root, tearoff=0)
            try:
                text_widget.selection_get()
                menu.add_command(label="📋 复制选中文字", command=copy_selection)
            except tk.TclError:
                menu.add_command(label="📋 复制选中文字", state=tk.DISABLED)
                
            menu.add_separator()
            menu.add_command(label="📄 复制全部网络信息", command=copy_all)
            menu.tk_popup(event.x_root, event.y_root)
        text_widget.bind("<Button-3>", show_menu)
        text_widget.bind("<Button-2>", show_menu)

    def setup_ui(self):
        nav_f = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        nav_f.pack(fill=tk.X, side=tk.TOP)
        
        self.main_pane = tk.PanedWindow(self.root, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=6)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))

        content_f = tk.Frame(self.main_pane)
        self.main_pane.add(content_f, stretch="always")

        self.frames = {}
        self.btns = []

        tabs = [
            ("📍 存活主机扫描", "black", lambda f: PingScannerModule(self, f, NetworkUtils.get_local_ip())),
            ("🧮 IPv4 计算器", "darkblue", lambda f: IPv4CalcModule(f)),
            ("🌐 IPv6 计算器", "darkgreen", lambda f: IPv6CalcModule(f)),
            ("👨‍💻 软件说明", "dimgray", self.setup_author)
        ]

        for i, (txt, color, func) in enumerate(tabs):
            frm = tk.Frame(content_f)
            self.frames[i] = frm
            func(frm)
            b = tk.Button(nav_f, text=txt, font=("Microsoft YaHei", 10, "bold"), fg=color, relief=tk.RAISED, command=lambda idx=i: self.switch_tab(idx))
            b.pack(side=tk.LEFT, padx=2, pady=2)
            self.btns.append(b)
        self.switch_tab(0)

        bottom_f = tk.LabelFrame(self.main_pane, text="📡 本机全网卡环境状态分析 (可鼠标划选，支持右键提取，支持上下拖拽调节高度)", font=("Microsoft YaHei", 9, "bold"), fg="#17a2b8")
        self.main_pane.add(bottom_f, stretch="never")
        
        self.net_txt = tk.Text(bottom_f, height=5, bg="#f8f9fa", font=("Consolas", 10), relief=tk.FLAT)
        scr_net = ttk.Scrollbar(bottom_f, orient=tk.VERTICAL, command=self.net_txt.yview)
        self.net_txt.configure(yscroll=scr_net.set)
        
        scr_net.pack(side=tk.RIGHT, fill=tk.Y)
        self.net_txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=2)
        
        self.setup_text_copy(self.net_txt)
        
        self.net_txt.insert(tk.END, "正在深度探测本机所有网卡网络环境，请稍候...")
        self.net_txt.config(state=tk.DISABLED)
        threading.Thread(target=self.load_net_info, daemon=True).start()

    def load_net_info(self):
        info = NetworkUtils.get_all_network_adapters_info()
        self.root.after(0, lambda: self._set_net_info(info))
        
    def _set_net_info(self, info):
        self.net_txt.config(state=tk.NORMAL)
        self.net_txt.delete(1.0, tk.END)
        self.net_txt.insert(tk.END, info)
        self.net_txt.config(state=tk.DISABLED)

    def switch_tab(self, idx):
        for i, f in self.frames.items():
            if i == idx: f.pack(fill=tk.BOTH, expand=True); self.btns[i].config(relief=tk.SUNKEN, bg="#e0e0e0")
            else: f.pack_forget(); self.btns[i].config(relief=tk.RAISED, bg="#f0f0f0")

    def setup_author(self, parent):
        tk.Label(parent, text="Lan Scan lite (Free 基础版)", font=("Microsoft YaHei", 18, "bold"), fg="dimgray").pack(pady=(20, 5))
        tk.Label(parent, text="Version 14.0.0 Free", font=("Arial", 10)).pack()
        f = tk.Frame(parent); f.pack(pady=20)
        
        infos = [
            ("开发作者 :", "Jason / vr3"),
            ("联系邮箱 :", "jason_vr3@hotmail.com"),
            ("免费版功能 :", "极速多线程存活主机扫描、IPv4/v6 子网计算器、全息网卡侦测仪"),
            ("商业授权 :", "如需解锁『高并发多IP端口扫描』等进阶排障功能，请获取 Pro 商业版。")
        ]
        for i, (k, v) in enumerate(infos):
            tk.Label(f, text=k, font=("Microsoft YaHei", 10, "bold")).grid(row=i, column=0, sticky="e", pady=8, padx=10)
            tk.Label(f, text=v, font=("Microsoft YaHei", 10), justify=tk.LEFT).grid(row=i, column=1, sticky="w", pady=8)

# =====================================================================
# 程序入口
# =====================================================================
if __name__ == "__main__":
    # -----------------------------------------------------------------
    # [GUI 增强] 开启高 DPI 适配，解决高分屏下 Tkinter 界面模糊问题
    # -----------------------------------------------------------------
    try:
        import ctypes
        # 首选方案：调用 Windows 8.1+ 的高级 DPI 感知 API
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            # 备用方案：兼容 Windows 7/8 的基础 DPI 感知 API
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass  # 如果系统实在不支持，就静默放弃，绝对不能让程序崩溃
    # -----------------------------------------------------------------

    try:
        root = tk.Tk()
        
        # (如果您觉得开启高 DPI 后界面变得太小，可以在这里稍微把窗口放大一点)
        # 比如把原来的 800x480 改成 1000x600：
        app = QuickPingApp(root)
        
        root.mainloop()
    except Exception:
        import os
        os._exit(1)