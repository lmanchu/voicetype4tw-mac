import threading
import time
import platform
from typing import Callable, Optional, Dict

IS_WINDOWS = platform.system() == "Windows"

def key_to_str(key) -> str:
    return str(key).lower().replace("key.", "")

def str_to_key(key_str: str):
    return key_str

# Mapping common key names to macOS virtual key codes
KEY_NAME_TO_CODE = {
    "alt": 58, "alt_r": 61,
    "cmd": 55, "cmd_r": 54,
    "ctrl": 59, "ctrl_r": 62,
    "shift": 56, "shift_r": 60,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97,
    "f7": 98, "f8": 100, "f9": 101, "f10": 109, "f11": 103, "f12": 111,
    "f13": 105, "f14": 107, "f15": 113, "f16": 106,
    "space": 49, "enter": 36, "tab": 48, "esc": 53,
}

class HotkeyListener:
    def __init__(
        self,
        hotkey_configs: Dict[str, str],
        on_start: Callable[[str], None],
        on_stop: Callable[[str], None],
    ):
        self.configs = hotkey_configs
        self.on_start = on_start
        self.on_stop = on_stop
        
        self._active_mode: Optional[str] = None
        self._loop_thread: Optional[threading.Thread] = None
        
        # macOS specific
        self._run_loop = None
        self._tap = None
        self._key_states: Dict[int, bool] = {}
        
        # Windows specific
        self._win_listener = None

        self.key_map: Dict[int, str] = {}
        if not IS_WINDOWS:
            self._refresh_key_map_macos()

    def _refresh_key_map_macos(self):
        self.key_map = {}
        for mode, name in self.configs.items():
            name = name.lower()
            if name in KEY_NAME_TO_CODE:
                self.key_map[KEY_NAME_TO_CODE[name]] = mode

    def start(self) -> None:
        if IS_WINDOWS:
            self._start_windows()
        else:
            self._start_macos()

    def stop(self) -> None:
        if IS_WINDOWS:
            if self._win_listener:
                try:
                    import keyboard
                    keyboard.unhook_all()
                except Exception:
                    pass
                self._win_listener = None
        else:
            if self._run_loop:
                from Foundation import CFRunLoopStop
                CFRunLoopStop(self._run_loop)
            if self._loop_thread:
                self._loop_thread.join(timeout=0.5)
        self._loop_thread = None

    # Map config key names to `keyboard` module key names (Windows)
    _KB_NAME_MAP = {
        "alt_r": "right alt", "alt_l": "left alt",
        "ctrl_r": "right ctrl", "ctrl_l": "left ctrl",
        "shift_r": "right shift", "shift_l": "left shift",
        "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4",
        "f5": "f5", "f6": "f6", "f7": "f7", "f8": "f8",
        "f9": "f9", "f10": "f10", "f11": "f11", "f12": "f12",
        "f13": "f13", "f14": "f14", "f15": "f15",
        "space": "space", "enter": "enter", "esc": "esc",
    }

    def _start_windows(self):
        """Use `keyboard` package on Windows. pynput's low-level hooks are
        blocked by some Windows 11 security policies, while `keyboard`
        works reliably via a different hook mechanism."""
        try:
            import keyboard

            key_to_mode = {}
            for mode, cfg_key in self.configs.items():
                kb_name = self._KB_NAME_MAP.get(cfg_key.lower(), cfg_key.lower())
                key_to_mode[kb_name] = mode

            def on_event(e):
                mode = key_to_mode.get(e.name)
                if not mode:
                    return
                if e.event_type == "down":
                    self._handle_press(mode)
                elif e.event_type == "up":
                    self._handle_release(mode)

            keyboard.hook(on_event)
            self._win_listener = True  # flag to track hook state
            print(f"[hotkey] Windows listener started. Keys: {key_to_mode}")
        except ImportError:
            print("[hotkey] Error: keyboard package not found. pip install keyboard")

    def _start_macos(self):
        if self._loop_thread and self._loop_thread.is_alive():
            return
        self._loop_thread = threading.Thread(target=self._run_macos, daemon=True)
        self._loop_thread.start()

    def _run_macos(self):
        import Quartz
        from Foundation import CFRunLoopGetCurrent, kCFRunLoopDefaultMode, CFRunLoopRunInMode
        self._run_loop = CFRunLoopGetCurrent()
        event_mask = (1 << Quartz.kCGEventKeyDown) | (1 << Quartz.kCGEventKeyUp) | (1 << Quartz.kCGEventFlagsChanged)
        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly, event_mask, self._macos_callback, None
        )
        if not self._tap:
            print("[hotkey] ERR: Failed to create macOS event tap.")
            return
        run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        Quartz.CFRunLoopAddSource(self._run_loop, run_loop_source, kCFRunLoopDefaultMode)
        Quartz.CGEventTapEnable(self._tap, True)
        CFRunLoopRunInMode(kCFRunLoopDefaultMode, 10e10, False)

    def _macos_callback(self, proxy, type, event, refcon):
        import Quartz
        keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
        mode = self.key_map.get(keycode)
        if not mode: return event

        if type == Quartz.kCGEventKeyDown:
            if not self._key_states.get(keycode, False):
                self._key_states[keycode] = True
                self._handle_press(mode)
        elif type == Quartz.kCGEventKeyUp:
            if self._key_states.get(keycode, False):
                self._key_states[keycode] = False
                self._handle_release(mode)
        elif type == Quartz.kCGEventFlagsChanged:
            flags = Quartz.CGEventGetFlags(event)
            is_pressed = False
            if keycode in [58, 61]: is_pressed = bool(flags & Quartz.kCGEventFlagMaskAlternate)
            elif keycode in [56, 60]: is_pressed = bool(flags & Quartz.kCGEventFlagMaskShift)
            elif keycode in [59, 62]: is_pressed = bool(flags & Quartz.kCGEventFlagMaskControl)
            elif keycode in [55, 54]: is_pressed = bool(flags & Quartz.kCGEventFlagMaskCommand)
            
            was_pressed = self._key_states.get(keycode, False)
            if is_pressed and not was_pressed:
                self._key_states[keycode] = True
                self._handle_press(mode)
            elif not is_pressed and was_pressed:
                self._key_states[keycode] = False
                self._handle_release(mode)
        return event

    def _handle_press(self, mode: str):
        if mode == "toggle":
            if self._active_mode is None:
                self._active_mode = "toggle"
                threading.Thread(target=self.on_start, args=("toggle",), daemon=True).start()
            elif self._active_mode == "toggle":
                self._active_mode = None
                threading.Thread(target=self.on_stop, args=("toggle",), daemon=True).start()
        elif self._active_mode is None:
            self._active_mode = mode
            threading.Thread(target=self.on_start, args=(mode,), daemon=True).start()

    def _handle_release(self, mode: str):
        if mode == "toggle": return
        if self._active_mode == mode:
            self._active_mode = None
            threading.Thread(target=self.on_stop, args=(mode,), daemon=True).start()

