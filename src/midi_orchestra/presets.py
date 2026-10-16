"""Convert user-installed Surge factory FXP chunks to standard VST3 presets."""
import hashlib
from pathlib import Path
import struct

FACTORY_PRESETS = {
    "surge_pad": "Pads/MKS-70 Warm Pad.fxp",
    "surge_bass": "Basses/Mellow.fxp",
    "surge_pluck": "Plucks/Clean.fxp",
    "surge_texture": "FX/Space Adventure 1.fxp",
}
# Windows class ID from the official Surge XT 1.3.4 plugin factory.
WINDOWS_CLASS_ID = b"ABCDEF019182FAEB566D624153675854"


def convert_fxp(source, destination):
    source, destination = Path(source), Path(destination)
    data = source.read_bytes()
    if len(data) < 92 or data[:4] != b"CcnK" or data[8:12] != b"FPCh" or data[60:64] != b"sub3":
        raise ValueError("Expected a Surge XT chunk-format FXP preset")
    raw = data[60:]
    header = b"VST3" + struct.pack("<I", 1) + WINDOWS_CLASS_ID + struct.pack("<Q", 48 + len(raw))
    payload = header + raw + b"List" + struct.pack("<I", 1) + b"Comp" + struct.pack("<QQ", 48, len(raw))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()
