# -*- coding: utf-8 -*-
"""
bili-cookies-extractor
哔哩Cookie提取工具
禁止倒卖，禁止插入恶意代码并二次分发

Ver_0.2
- 支持Edge
- 支持窗口置顶
- 添加弹窗提示

Ver_0.1
- 第一版，用于配合爬取姬使用
"""

import os
import json
import time
import base64
import shutil
import platform
import tempfile
import threading
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

from DrissionPage import ChromiumPage, ChromiumOptions


APP_NAME = "bili-cookies-extractor"
APP_VERSION = "v0.2"


def _resolve_executable(candidate):
    if not candidate:
        return None
    if os.path.isabs(candidate):
        return candidate if os.path.exists(candidate) else None
    return shutil.which(candidate)


def find_browser():
    system = platform.system()
    groups = []

    if system == "Windows":
        groups = [
            ("Chrome", [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
            ]),
            ("Edge", [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
            ]),
        ]
    elif system == "Linux":
        groups = [
            ("Chrome", ["google-chrome", "google-chrome-stable"]),
            ("Chromium", ["chromium", "chromium-browser"]),
            ("Edge", ["microsoft-edge", "microsoft-edge-stable"]),
        ]
    elif system == "Darwin":
        groups = [
            ("Chrome", [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            ]),
            ("Chromium", [
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
            ]),
            ("Edge", [
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            ]),
        ]

    for name, candidates in groups:
        for candidate in candidates:
            path = _resolve_executable(candidate)
            if path:
                return name, path

    return None, None


class BiliCookieExtractor:
    LOGIN_PROFILE_DIR = Path.home() / ".bili_cookie_extractor" / "login_profile"

    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("1100x760")
        self.root.minsize(900, 600)

        self.browser_name, self.browser_path = find_browser()
        self._guest_tmp_dir = None
        self._last_cookies = []
        self._busy = False
        self.var_topmost = tk.BooleanVar(value=True)

        self._build_ui()

        self._apply_topmost()

        if not self.browser_path:
            self.log("[!] 未找到 Chrome / Chromium / Edge")
        else:
            self.log(f"[+] 浏览器: {self.browser_name} -> {self.browser_path}")
        self.log(f"[+] 登录模式 profile: {self.LOGIN_PROFILE_DIR}")
        self.log("[i] 需配合 Chrome / Chromium / Edge 使用。不兼容无显示输出的设备。")

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.grid(row=0, column=0, sticky="ew")

        self.btn_guest = ttk.Button(
            top, text="获取一组游客cookies", width=22,
            command=lambda: self._confirm_and_run(self.get_guest_cookies),
        )
        self.btn_guest.pack(side=tk.LEFT, padx=4)

        self.btn_login = ttk.Button(
            top, text="登录以获取cookies", width=22,
            command=lambda: self._confirm_and_run(self.get_login_cookies),
        )
        self.btn_login.pack(side=tk.LEFT, padx=4)

        self.btn_clear = ttk.Button(
            top, text="清除登录态", width=14,
            command=self.clear_login_profile,
        )
        self.btn_clear.pack(side=tk.LEFT, padx=4)

        self.chk_topmost = ttk.Checkbutton(
            top, text="窗口置顶", variable=self.var_topmost,
            command=self._apply_topmost,
        )
        self.chk_topmost.pack(side=tk.RIGHT, padx=4)

        mid = ttk.Frame(self.root, padding=(10, 0))
        mid.grid(row=1, column=0, sticky="nsew")
        mid.columnconfigure(0, weight=1)
        mid.columnconfigure(1, weight=1)
        mid.rowconfigure(0, weight=1)

        frame_str = ttk.LabelFrame(mid, text="Cookies(字符串格式)", padding=6)
        frame_str.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        frame_str.columnconfigure(0, weight=1)
        frame_str.rowconfigure(1, weight=1)

        str_bar = ttk.Frame(frame_str)
        str_bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(str_bar, text="导出", width=10,
                   command=self.export_string).pack(side=tk.RIGHT)

        self.text_str = scrolledtext.ScrolledText(
            frame_str, wrap=tk.NONE, font=("Consolas", 9))
        self.text_str.grid(row=1, column=0, sticky="nsew")

        frame_ns = ttk.LabelFrame(mid, text="Cookies(Netscape格式)", padding=6)
        frame_ns.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        frame_ns.columnconfigure(0, weight=1)
        frame_ns.rowconfigure(1, weight=1)

        ns_bar = ttk.Frame(frame_ns)
        ns_bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(ns_bar, text="导出", width=10,
                   command=self.export_netscape).pack(side=tk.RIGHT)

        self.text_ns = scrolledtext.ScrolledText(
            frame_ns, wrap=tk.NONE, font=("Consolas", 9))
        self.text_ns.grid(row=1, column=0, sticky="nsew")

        bot = ttk.LabelFrame(self.root, text="日志", padding=6)
        bot.grid(row=2, column=0, sticky="nsew", padx=10, pady=(6, 10))
        bot.columnconfigure(0, weight=1)
        bot.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            bot, height=8, font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=3)
        self.root.rowconfigure(2, weight=1)

    def _apply_topmost(self):
        try:
            self.root.attributes("-topmost", bool(self.var_topmost.get()))
        except Exception:
            pass

    def _raise_self(self):
        try:
            self.root.deiconify()
        except Exception:
            pass
        try:
            self.root.lift()
        except Exception:
            pass
        try:
            self.root.focus_force()
        except Exception:
            pass

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def _confirm_and_run(self, func):
        if self._busy:
            messagebox.showinfo("提示", "当前已有任务在执行")
            return

        self._apply_topmost()
        self._raise_self()

        messagebox.showinfo(
            "注意",
            "即将进行自动化作业，请不要关闭弹出的浏览器窗口",
            parent=self.root,
        )

        self._run_async(func)

    def _run_async(self, func):
        if self._busy:
            messagebox.showinfo("提示", "当前已有任务在执行")
            return
        self._busy = True
        self._set_buttons_state(tk.DISABLED)

        def wrapper():
            try:
                func()
            finally:
                self._busy = False
                self._set_buttons_state(tk.NORMAL)

        threading.Thread(target=wrapper, daemon=True).start()

    def _set_buttons_state(self, state):
        for b in (self.btn_guest, self.btn_login, self.btn_clear):
            try:
                b.config(state=state)
            except Exception:
                pass

    def _create_browser(self, mode):
        if not self.browser_path:
            messagebox.showerror("错误", "未找到 Chrome / Chromium / Edge")
            return None

        co = ChromiumOptions()
        co.set_browser_path(self.browser_path)
        co.set_argument("--disable-blink-features=AutomationControlled")
        co.set_argument("--no-first-run")
        co.set_argument("--no-default-browser-check")

        if mode == "guest":
            self._guest_tmp_dir = tempfile.mkdtemp(prefix="bili_guest_")
            co.set_user_data_path(self._guest_tmp_dir)
            self.log(f"[i] 游客模式 profile: {self._guest_tmp_dir}")
        else:
            self.LOGIN_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            co.set_user_data_path(str(self.LOGIN_PROFILE_DIR))
            self.log(f"[i] 登录模式 profile: {self.LOGIN_PROFILE_DIR}")

        try:
            page = ChromiumPage(addr_or_opts=co)
            self.log(f"[i] 已启动: {self.browser_name}")
            return page
        except Exception as e:
            self.log(f"[!] 启动浏览器失败: {e}")
            self._cleanup_guest_dir()
            return None

    def _cleanup_guest_dir(self):
        if self._guest_tmp_dir:
            try:
                shutil.rmtree(self._guest_tmp_dir, ignore_errors=True)
                self.log("[i] 已清理临时 profile")
            except Exception:
                pass
            self._guest_tmp_dir = None

    def _close_browser(self, page):
        if page is not None:
            try:
                page.quit()
            except Exception:
                pass
        self._cleanup_guest_dir()

    def get_guest_cookies(self):
        self.log("===== 游客模式：开始 =====")
        page = self._create_browser(mode="guest")
        if not page:
            return

        try:
            self.log("产生正常Cookies...")
            page.get("https://www.bilibili.com/")
            time.sleep(3)

            self.log("访问 nav 接口...")
            page.get("https://api.bilibili.com/x/web-interface/nav")
            time.sleep(2)

            cookies = self._collect_cookies(page)

            if any(c["name"] == "SESSDATA" and c["value"] for c in cookies):
                self.log("[!] 警告：游客模式检测到 SESSDATA，可能有污染")
                cookies = [c for c in cookies if c["name"] != "SESSDATA"]
                self.log("[i] 已强制剔除 SESSDATA")

            self._show_cookies(cookies)
            self.log(f"[+] 游客 Cookie 提取完成，共 {len(cookies)} 项")
            self._show_time_dialog(cookies)
        except Exception as e:
            self.log(f"[!] 出错: {e}")
        finally:
            self._close_browser(page)

    def get_login_cookies(self):
        self.log("===== 登录模式：开始 =====")
        page = self._create_browser(mode="login")
        if not page:
            return

        try:
            self.log("打开登录页...")
            page.get("https://passport.bilibili.com/login")
            time.sleep(2)

            cookies = self._collect_cookies(page)
            if any(c["name"] == "SESSDATA" and c["value"] for c in cookies):
                self.log("[+] 检测到已有登录态，跳过登录")
            else:
                self.log("[*] 请在浏览器窗口中登录")
                self.log("[*] 最多等待 180 秒...")

                ok = False
                for i in range(180):
                    try:
                        cookies = self._collect_cookies(page)
                        if any(c["name"] == "SESSDATA" and c["value"] for c in cookies):
                            ok = True
                            break
                    except Exception:
                        pass
                    if i % 10 == 0 and i > 0:
                        self.log(f"[*] 已等待 {i}s ...")
                    time.sleep(1)

                if not ok:
                    self.log("[!] 登录超时")
                    return

            self.log("[+] 登录成功，刷新 Cookie ...")
            page.get("https://www.bilibili.com/")
            time.sleep(3)
            page.get("https://api.bilibili.com/x/web-interface/nav")
            time.sleep(2)

            cookies = self._collect_cookies(page)
            self._show_cookies(cookies)

            has_sess = any(c["name"] == "SESSDATA" and c["value"] for c in cookies)
            self.log(f"[+] 登录 Cookie 提取完成，共 {len(cookies)} 项，"
                     f"SESSDATA={'有' if has_sess else '无'}")
            self._show_time_dialog(cookies)
        except Exception as e:
            self.log(f"[!] 出错: {e}")
        finally:
            self._close_browser(page)

    def clear_login_profile(self):
        if not self.LOGIN_PROFILE_DIR.exists():
            self.log("[i] 登录 profile 不存在，无需清除")
            messagebox.showinfo("提示", "当前没有保存的登录态")
            return
        if not messagebox.askyesno("确认", "确定要清除已保存的登录态吗？\n下次需重新登录。"):
            return
        try:
            shutil.rmtree(self.LOGIN_PROFILE_DIR, ignore_errors=True)
            self.log(f"[+] 已清除: {self.LOGIN_PROFILE_DIR}")
            messagebox.showinfo("提示", "登录态已清除")
        except Exception as e:
            self.log(f"[!] 清除失败: {e}")
            messagebox.showerror("错误", str(e))

    def _collect_cookies(self, page):
        raw = page.cookies(all_domains=True)
        result = []
        for c in raw:
            domain = c.get("domain", "") or ""
            if "bilibili.com" not in domain:
                continue
            result.append({
                "name": c.get("name", ""),
                "value": c.get("value", ""),
                "domain": domain,
                "path": c.get("path", "/"),
                "expires": c.get("expires", -1),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", False),
            })
        return result

    def _show_cookies(self, cookies):
        self._last_cookies = cookies

        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        self.text_str.delete("1.0", tk.END)
        self.text_str.insert(tk.END, cookie_str)

        ns = self._to_netscape(cookies)
        self.text_ns.delete("1.0", tk.END)
        self.text_ns.insert(tk.END, ns)

    def _to_netscape(self, cookies):
        lines = [
            "# Netscape HTTP Cookie File",
            "# https://curl.se/docs/http-cookies.html",
            f"# Generated by {APP_NAME} {APP_VERSION} at "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
        for c in cookies:
            domain = c["domain"]
            include_sub = "TRUE" if domain.startswith(".") else "FALSE"
            path = c["path"] or "/"
            secure = "TRUE" if c.get("secure") else "FALSE"
            expires = c.get("expires", -1)
            try:
                expires = int(expires)
            except Exception:
                expires = 0
            if expires < 0:
                expires = 0
            name = c["name"]
            value = c["value"]
            lines.append(
                "\t".join([domain, include_sub, path, secure,
                           str(expires), name, value])
            )
        return "\n".join(lines) + "\n"

    def _show_time_dialog(self, cookies):
        cookie_dict = {c["name"]: c["value"] for c in cookies}

        device_ts = None
        if "b_nut" in cookie_dict:
            try:
                device_ts = int(cookie_dict["b_nut"])
            except Exception:
                pass

        issue_ts = None
        jwt_exp_ts = None
        if "bili_ticket" in cookie_dict:
            payload = self._decode_jwt_payload(cookie_dict["bili_ticket"])
            if payload:
                issue_ts = payload.get("iat")
                jwt_exp_ts = payload.get("exp")

        ticket_exp_ts = None
        if "bili_ticket_expires" in cookie_dict:
            try:
                ticket_exp_ts = int(cookie_dict["bili_ticket_expires"])
            except Exception:
                pass

        lines = []
        if device_ts:
            lines.append(f"设备ID生成时间(b_nut)：\n    {self._fmt_ts(device_ts)}")
        if issue_ts:
            lines.append(f"Cookies下发时间(bili_ticket.iat)：\n    {self._fmt_ts(issue_ts)}")
        if ticket_exp_ts:
            lines.append(f"Cookies理论过期时间(bili_ticket_expires)：\n    {self._fmt_ts(ticket_exp_ts)}")
        elif jwt_exp_ts:
            lines.append(f"Cookies理论过期时间(bili_ticket.exp)：\n    {self._fmt_ts(jwt_exp_ts)}")

        for line in lines:
            self.log("[time] " + line.replace("\n    ", " "))

        tips = ["作业已完成，单击“确认”来关闭多余窗口"]
        tips.extend(lines)
        messagebox.showinfo("提示", "\n\n".join(tips))

    def _fmt_ts(self, ts):
        try:
            return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(ts)

    def _decode_jwt_payload(self, token):
        try:
            parts = token.split(".")
            if len(parts) < 2:
                return None
            payload_b64 = parts[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            return json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            return None

    def export_string(self):
        data = self.text_str.get("1.0", tk.END).strip()
        if not data:
            messagebox.showwarning("提示", "还没有 Cookie 可导出")
            return
        path = filedialog.asksaveasfilename(
            title="导出 Cookies(字符串格式)",
            defaultextension=".txt",
            initialfile="cookies.txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
            self.log(f"[+] 字符串格式已导出: {path}")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def export_netscape(self):
        data = self.text_ns.get("1.0", tk.END).strip()
        if not data:
            messagebox.showwarning("提示", "还没有 Cookie 可导出")
            return
        path = filedialog.asksaveasfilename(
            title="导出 Cookies(Netscape格式)",
            defaultextension=".txt",
            initialfile="cookies.txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(data + "\n")
            self.log(f"[+] Netscape 格式已导出: {path}")
        except Exception as e:
            messagebox.showerror("错误", str(e))


def main():
    root = tk.Tk()
    try:
        if platform.system() == "Windows":
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    BiliCookieExtractor(root)
    root.mainloop()


if __name__ == "__main__":
    main()