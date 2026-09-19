#!/usr/bin/env python
"""
Unpacks a Wynncraft server resource pack zip into a directory.

The client caches the pack under .minecraft/downloads/<uuid>/<sha> (or a
dev client's run/downloads/). The pack is deliberately mangled in ways the
game's loaders tolerate but ordinary tools do not:

- zip local file headers carry blank names and the central directory lies
  about sizes and CRCs, so entries are inflated straight from their recorded
  offsets until the deflate stream ends;
- every PNG chunk carries a wrong CRC and the IDAT zlib stream a wrong
  adler32 trailer, so PNGs are rebuilt from their (intact) raw deflate data.

Usage:
    python scripts/unpack_wynn_pack.py <pack-file> <out-dir>
    python scripts/unpack_wynn_pack.py <pack-file> <out-dir> --only assets/minecraft/textures/wynn/tool/

Then point the icon extractor at it:
    python scripts/extract_resource_pack_icons.py --src <out-dir>/assets/minecraft/textures/wynn
"""

import argparse
import struct
import sys
import zipfile
import zlib
from pathlib import Path

LOCAL_HEADER = struct.Struct("<IHHHHHIIIHH")  # signature .. name length, extra length
LOCAL_HEADER_SIGNATURE = 0x04034B50


class WynnPack:
    """Read entries of a pack zip whose local headers have blank names."""

    def __init__(self, path):
        self._zip = zipfile.ZipFile(path)
        self._fh = open(path, "rb")
        self.infos = {info.filename: info for info in self._zip.infolist()}

    def close(self):
        self._fh.close()
        self._zip.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def names(self):
        return list(self.infos)

    def read(self, name: str) -> bytes:
        """The entry's bytes. The recorded sizes are not trusted: a deflated
        entry is inflated until the stream itself ends, a stored one is read
        up to the next entry."""
        info = self.infos[name]
        self._fh.seek(info.header_offset)
        fields = LOCAL_HEADER.unpack(self._fh.read(LOCAL_HEADER.size))
        if fields[0] != LOCAL_HEADER_SIGNATURE:
            raise zipfile.BadZipFile(f"bad local header for {name}")
        name_len, extra_len = fields[9], fields[10]
        self._fh.seek(info.header_offset + LOCAL_HEADER.size + name_len + extra_len)
        if info.compress_type == zipfile.ZIP_DEFLATED:
            inflater = zlib.decompressobj(-zlib.MAX_WBITS)
            out = bytearray()
            while not inflater.eof:
                chunk = self._fh.read(65536)
                if not chunk:
                    raise zipfile.BadZipFile(f"truncated deflate stream for {name}")
                out += inflater.decompress(chunk)
            return bytes(out)
        if info.compress_type == zipfile.ZIP_STORED:
            return self._fh.read(info.compress_size)
        raise zipfile.BadZipFile(f"unsupported compression {info.compress_type} for {name}")

    def extract_all(self, out: Path, only: str = "") -> int:
        written = 0
        for name, info in self.infos.items():
            if info.is_dir() or not name.startswith(only):
                continue
            data = self.read(name)
            if name.lower().endswith(".png"):
                data = repair_png(data)
            dest = out / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            written += 1
        return written


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_chunk(ctype: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + ctype + body + struct.pack(">I", zlib.crc32(ctype + body) & 0xFFFFFFFF)


def repair_png(data: bytes) -> bytes:
    """Rebuild a PNG whose chunk CRCs and IDAT adler32 trailer are wrong.

    The raw deflate data inside IDAT is intact, so the image is re-emitted
    losslessly: chunks are copied with recomputed CRCs and the IDAT stream is
    inflated (ignoring its trailer) and deflated again as a valid zlib stream.
    Anything that is not a PNG is returned untouched.
    """
    if not data.startswith(PNG_SIGNATURE):
        return data
    chunks = []
    idat = b""
    pos = len(PNG_SIGNATURE)
    while pos + 8 <= len(data):
        length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if ctype == b"IDAT":
            idat += body
        elif ctype == b"IEND":
            break
        else:
            chunks.append((ctype, body))
        pos += 12 + length
    if not idat:
        return data
    inflater = zlib.decompressobj(-zlib.MAX_WBITS)
    scanlines = inflater.decompress(idat[2:])  # skip the 2-byte zlib header
    out = bytearray(PNG_SIGNATURE)
    for ctype, body in chunks:
        out += _png_chunk(ctype, body)
    out += _png_chunk(b"IDAT", zlib.compress(scanlines, 9))
    out += _png_chunk(b"IEND", b"")
    return bytes(out)


def main():
    parser = argparse.ArgumentParser(description="Unpack a Wynncraft resource pack zip")
    parser.add_argument("pack", type=Path, help="the cached pack file (a zip without extension)")
    parser.add_argument("out", type=Path, help="directory to unpack into")
    parser.add_argument("--only", default="", help="only entries whose path starts with this prefix")
    args = parser.parse_args()

    if not args.pack.is_file():
        print(f"Error: not a file: {args.pack}")
        sys.exit(1)

    with WynnPack(args.pack) as pack:
        count = pack.extract_all(args.out, args.only)
    print(f"Unpacked {count} files to {args.out}")


if __name__ == "__main__":
    main()
