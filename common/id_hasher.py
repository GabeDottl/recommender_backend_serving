import struct
import pyhash
import base64


class IdHasher:

  def __init__(self):
    # This is a very fast hasher (not cryptographically safe) that's implemented natively.
    self.hasher = pyhash.fnv1_64(seed=0xDEADBEEF)

  # Takes ~60us.
  def hash(self, s):
    h = self.hasher(str(s))
    h = struct.pack("<Q", h)
    # -1 to drop '=' at the end.
    return base64.urlsafe_b64encode(h)[:-1].decode()
