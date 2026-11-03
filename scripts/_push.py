"""git add/commit/push 一步走（凭据从 wincred 读，不落盘不打印）。"""
import base64
import ctypes
import ctypes.wintypes as wt
import subprocess
import sys

GIT = r"D:\hermes\git\cmd\git.exe"
REPO = r"D:\工作\chan_quant"


class CREDENTIAL_ATTRIBUTE(ctypes.Structure):
    _fields_ = [("Keyword", wt.LPWSTR), ("Flags", wt.DWORD), ("ValueSize", wt.DWORD),
                ("Value", ctypes.POINTER(ctypes.c_byte))]


class CREDENTIAL(ctypes.Structure):
    _fields_ = [("Flags", wt.DWORD), ("Type", wt.DWORD), ("TargetName", wt.LPWSTR),
                ("Comment", wt.LPWSTR), ("LastWritten", wt.FILETIME),
                ("CredentialBlobSize", wt.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
                ("Persist", wt.DWORD), ("AttributeCount", wt.DWORD),
                ("Attributes", ctypes.POINTER(CREDENTIAL_ATTRIBUTE)),
                ("TargetAlias", wt.LPWSTR), ("UserName", wt.LPWSTR)]


def github_token() -> str:
    p = ctypes.c_void_p()
    if not ctypes.windll.advapi32.CredReadW("git:https://github.com", 1, 0, ctypes.byref(p)):
        raise RuntimeError("wincred read failed")
    c = ctypes.cast(p, ctypes.POINTER(CREDENTIAL)).contents
    raw = ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize)
    ctypes.windll.advapi32.CredFree(p)
    return raw.decode("utf-16-le")


def main():
    paths = sys.argv[1:-1]
    msg = sys.argv[-1]
    token = github_token()
    hdr = "Authorization: Basic " + base64.b64encode(f"RaiderYi:{token}".encode()).decode()
    subprocess.run([GIT, "-C", REPO, "add"] + paths, check=True)
    r = subprocess.run([GIT, "-C", REPO, "commit", "-m", msg], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout.strip() or r.stderr.strip())
    r = subprocess.run([GIT, "-C", REPO, "-c", "http.proxy=http://127.0.0.1:7890",
                        "-c", f"http.extraHeader={hdr}", "push", "origin", "main"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout.strip(), r.stderr.strip())
    print("push rc =", r.returncode)


if __name__ == "__main__":
    main()
