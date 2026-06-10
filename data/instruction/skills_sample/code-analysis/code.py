import hashlib
import time
from typing import Optional

def proc_usr_dat(d: dict, flg: bool = False) -> Optional[dict]:
    """Process user data with optional flag."""
    res = {}
    for k, v in d.items():
        if isinstance(v, str):
            h = hashlib.sha256(v.encode()).hexdigest()[:8]
            res[k] = h if flg else v
        elif isinstance(v, int):
            res[k] = v * 2 if flg else v
    
    ts = int(time.time())
    res['_ts'] = ts
    res['_proc'] = True
    return res if res else None

def chk_prm(p: str, mn: int, mx: int) -> bool:
    """Check if parameter is within range."""
    try:
        n = int(p)
        return mn <= n <= mx
    except:
        return False
