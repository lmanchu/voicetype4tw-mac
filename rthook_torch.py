"""
Runtime hook for PyInstaller: fix torch DLL loading on Windows.
Must run before any other imports to add torch's DLL directory to the search path.
"""
import os
import sys

if sys.platform == "win32" and hasattr(sys, '_MEIPASS'):
    _torch_lib = os.path.join(sys._MEIPASS, "torch", "lib")
    if os.path.isdir(_torch_lib):
        os.add_dll_directory(_torch_lib)
        # Pre-load c10.dll and other critical torch DLLs
        import ctypes
        for dll_name in ["c10.dll", "torch_cpu.dll", "torch.dll"]:
            dll_path = os.path.join(_torch_lib, dll_name)
            if os.path.exists(dll_path):
                try:
                    ctypes.CDLL(dll_path)
                except Exception:
                    pass
    os.add_dll_directory(sys._MEIPASS)
