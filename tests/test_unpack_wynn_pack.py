"""Tests for scripts/unpack_wynn_pack.py — reading Wynncraft's pack zips whose
local file headers have blank names."""
import io
import os
import struct
import sys
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))

from unpack_wynn_pack import WynnPack, repair_png


def png_chunk(ctype, body):
    return struct.pack(">I", len(body)) + ctype + body + struct.pack(">I", zlib.crc32(ctype + body) & 0xFFFFFFFF)


def make_png(scanlines=b"\x00" * 3 * 2):
    """A valid 2x1 RGB PNG (each row: filter byte + 3 bytes per pixel)."""
    ihdr = struct.pack(">IIBBBBB", 2, 1, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr)
            + png_chunk(b"IDAT", zlib.compress(scanlines)) + png_chunk(b"IEND", b""))


def mangle_png(png):
    """Wrong CRC on every chunk and a wrong adler32 trailer on IDAT."""
    out = bytearray(png[:8])
    pos = 8
    while pos + 8 <= len(png):
        length, ctype = struct.unpack(">I4s", png[pos:pos + 8])
        body = png[pos + 8:pos + 8 + length]
        if ctype == b"IDAT":
            body = body[:-4] + b"\xde\xad\xbe\xef"
        out += struct.pack(">I4s", length, ctype) + body + b"\x00\x00\x00\x00"
        pos += 12 + length
    return bytes(out)


VALID_PNG = make_png(b"\x00\x10\x20\x30\x40\x50\x60")

FILES = {
    "pack.mcmeta": b'{"pack": {}}',
    "assets/minecraft/textures/wynn/tool/bronze_axe.png": mangle_png(VALID_PNG),
    "assets/minecraft/textures/wynn/tool/void_rod.png": b"PNG-void-rod",
    "assets/minecraft/models/item/wynn/tool/bronze_axe.json": b'{"parent": "item/handheld"}',
}


def obfuscated_pack(path: Path):
    """Write a zip like Wynncraft's: valid central directory, blank local names."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("pack.mcmeta", FILES["pack.mcmeta"], compress_type=zipfile.ZIP_STORED)
        for name, data in FILES.items():
            if name != "pack.mcmeta":
                z.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)
    raw = bytearray(buf.getvalue())
    # Blank each local header's file name in place (keep lengths consistent by
    # rewriting the name length to 0 and shifting the data left).
    with zipfile.ZipFile(io.BytesIO(bytes(raw))) as z:
        infos = sorted(z.infolist(), key=lambda i: i.header_offset, reverse=True)
    out = raw
    for info in infos:
        off = info.header_offset
        name_len = struct.unpack_from("<H", out, off + 26)[0]
        struct.pack_into("<H", out, off + 26, 0)
        del out[off + 30: off + 30 + name_len]
        # fix central-directory offsets of every entry that followed this one
        for other in infos:
            if other.header_offset > off:
                other.header_offset -= name_len
    # rewrite the central directory with the corrected offsets
    end = out.rfind(b"PK\x05\x06")
    cd_size, cd_off = struct.unpack_from("<II", out, end + 12)
    cd_off -= sum(len(i.orig_filename.encode()) for i in infos)
    struct.pack_into("<I", out, end + 16, cd_off)
    # patch every central-directory entry's local header offset, and lie about
    # its CRC and uncompressed size the way the real pack does
    pos = cd_off
    while pos < end:
        assert out[pos:pos + 4] == b"PK\x01\x02"
        n, m, k = struct.unpack_from("<HHH", out, pos + 28)
        name = bytes(out[pos + 46: pos + 46 + n]).decode()
        info = next(i for i in infos if i.filename == name)
        struct.pack_into("<I", out, pos + 42, info.header_offset)
        struct.pack_into("<I", out, pos + 16, 0)             # crc32
        struct.pack_into("<I", out, pos + 24, 0xFFFFFF7F)    # uncompressed size
        pos += 46 + n + m + k
    path.write_bytes(bytes(out))


def png_chunks(png):
    pos, out = 8, []
    while pos + 8 <= len(png):
        length, ctype = struct.unpack(">I4s", png[pos:pos + 8])
        body = png[pos + 8:pos + 8 + length]
        crc = struct.unpack(">I", png[pos + 8 + length:pos + 12 + length])[0]
        out.append((ctype, body, crc == zlib.crc32(ctype + body) & 0xFFFFFFFF))
        pos += 12 + length
    return out


class TestRepairPng(unittest.TestCase):
    def test_fixture_is_mangled(self):
        mangled = mangle_png(VALID_PNG)
        self.assertFalse(any(ok for _, _, ok in png_chunks(mangled)))
        with self.assertRaises(zlib.error):
            zlib.decompress(next(b for t, b, _ in png_chunks(mangled) if t == b"IDAT"))

    def test_repair_restores_crcs_and_a_valid_idat_stream(self):
        repaired = repair_png(mangle_png(VALID_PNG))
        chunks = png_chunks(repaired)
        self.assertEqual([t for t, _, _ in chunks], [b"IHDR", b"IDAT", b"IEND"])
        self.assertTrue(all(ok for _, _, ok in chunks))
        original = dict((t, b) for t, b, _ in png_chunks(VALID_PNG))
        repaired_by_type = dict((t, b) for t, b, _ in chunks)
        self.assertEqual(repaired_by_type[b"IHDR"], original[b"IHDR"])
        self.assertEqual(zlib.decompress(repaired_by_type[b"IDAT"]), zlib.decompress(original[b"IDAT"]))

    def test_non_png_data_is_returned_untouched(self):
        self.assertEqual(repair_png(b"PNG-void-rod"), b"PNG-void-rod")
        self.assertEqual(repair_png(b'{"parent": "x"}'), b'{"parent": "x"}')


class TestWynnPack(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pack = Path(self.tmp.name) / "PRODUCTION_abc"
        obfuscated_pack(self.pack)

    def tearDown(self):
        self.tmp.cleanup()

    def test_fixture_reproduces_the_obfuscation(self):
        with zipfile.ZipFile(self.pack) as z:
            self.assertEqual(sorted(z.namelist()), sorted(FILES))
            with self.assertRaises(zipfile.BadZipFile):
                z.read("pack.mcmeta")

    def test_reads_stored_and_deflated_entries_by_offset(self):
        with WynnPack(self.pack) as pack:
            for name, data in FILES.items():
                self.assertEqual(pack.read(name), data, name)

    def test_extract_all_honours_the_prefix_filter(self):
        out = Path(self.tmp.name) / "out"
        with WynnPack(self.pack) as pack:
            count = pack.extract_all(out, only="assets/minecraft/textures/wynn/tool/")
        self.assertEqual(count, 2)
        self.assertEqual(sorted(p.name for p in (out / "assets/minecraft/textures/wynn/tool").iterdir()),
                         ["bronze_axe.png", "void_rod.png"])
        self.assertFalse((out / "pack.mcmeta").exists())

    def test_extract_all_repairs_pngs_on_the_way_out(self):
        out = Path(self.tmp.name) / "out"
        with WynnPack(self.pack) as pack:
            pack.extract_all(out, only="assets/minecraft/textures/wynn/tool/")
        written = (out / "assets/minecraft/textures/wynn/tool/bronze_axe.png").read_bytes()
        self.assertTrue(all(ok for _, _, ok in png_chunks(written)))
        # a file that merely ends in .png but is not a PNG is left alone
        self.assertEqual((out / "assets/minecraft/textures/wynn/tool/void_rod.png").read_bytes(), b"PNG-void-rod")


if __name__ == "__main__":
    unittest.main()
