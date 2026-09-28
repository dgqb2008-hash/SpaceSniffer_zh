# -*- coding: utf-8 -*-
"""直接解析/改写 PE 资源目录中的 RCDATA 条目（不依赖 Win32 资源 API）。

用法:
  python pe_res.py list  <exe>
  python pe_res.py patch <exe> <资源名> <新数据文件>
"""
import struct
import sys

RT_RCDATA = 10


class PE:
    def __init__(self, path):
        self.d = bytearray(open(path, "rb").read())
        e_lfanew = struct.unpack_from("<I", self.d, 0x3C)[0]
        assert self.d[e_lfanew:e_lfanew + 4] == b"PE\0\0"
        self.pe = e_lfanew + 4
        nsec, = struct.unpack_from("<H", self.d, self.pe + 2)
        size_opt, = struct.unpack_from("<H", self.d, self.pe + 16)
        self.opt = self.pe + 20
        magic, = struct.unpack_from("<H", self.d, self.opt)
        self.plus = magic == 0x20B
        dd_off = self.opt + (112 if self.plus else 96)
        self.res_rva, self.res_size = struct.unpack_from("<II", self.d, dd_off + 8 * 2)
        self.sections = []
        so = self.opt + size_opt
        for i in range(nsec):
            b = so + i * 40
            name = bytes(self.d[b:b + 8]).rstrip(b"\0").decode("ascii", "replace")
            vs, va, rs, pr = struct.unpack_from("<IIII", self.d, b + 8)
            self.sections.append((va, vs, pr, rs, name))
        self.res_off = self.rva2off(self.res_rva)

    def rva2off(self, rva):
        for va, vs, pr, rs, _ in self.sections:
            if va <= rva < va + max(vs, rs):
                return pr + (rva - va)
        raise ValueError("RVA 0x%X 不在任何节内" % rva)

    @staticmethod
    def _name(off, base):
        return off

    def read_name(self, off):
        n, = struct.unpack_from("<H", self.d, off)
        return self.d[off + 2:off + 2 + n * 2].decode("utf-16-le")

    def entries(self, dir_off):
        named, ided = struct.unpack_from("<HH", self.d, dir_off + 12)
        out = []
        for i in range(named + ided):
            b = dir_off + 16 + i * 8
            nm, od = struct.unpack_from("<II", self.d, b)
            out.append((b, nm, od))
        return out

    def walk(self):
        """返回 [(类型, 名称, 语言, 数据文件偏移, 大小, 数据条目偏移)]"""
        res = []
        for _, t, td in self.entries(self.res_off):
            if not (t & 0x80000000):  # 只用已知类型 ID
                if t != RT_RCDATA:
                    continue
                tname = str(t)
            else:
                tname = self.read_name(self.res_off + (t & 0x7FFFFFFF))
            d2 = self.res_off + (td & 0x7FFFFFFF)
            for _, nm, nd in self.entries(d2):
                if nm & 0x80000000:
                    name = self.read_name(self.res_off + (nm & 0x7FFFFFFF))
                else:
                    name = "#%d" % nm
                d3 = self.res_off + (nd & 0x7FFFFFFF)
                for _, lang, ld in self.entries(d3):
                    de = self.res_off + (ld & 0x7FFFFFFF)
                    rva, size, cp, _ = struct.unpack_from("<IIII", self.d, de)
                    res.append((tname, name, lang, self.rva2off(rva), size, de))
        return res

    def patch(self, name, data):
        n = 0
        for tname, rname, lang, off, size, de in self.walk():
            if rname == name and len(data) <= size:
                self.d[off:off + len(data)] = data
                self.d[off + len(data):off + size] = b"\0" * (size - len(data))
                struct.pack_into("<I", self.d, de + 4, len(data))
                n += 1
        return n

    def save(self, path):
        import time
        for k in range(5):
            try:
                open(path, "wb").write(bytes(self.d))
                return
            except PermissionError:
                time.sleep(0.6)
        open(path, "wb").write(bytes(self.d))


def cmd_list(path):
    p = PE(path)
    print("资源表 RVA=0x%X 文件偏移=0x%X" % (p.res_rva, p.res_off))
    for tname, name, lang, off, size, de in p.walk():
        head = bytes(p.d[off:off + 12])
        print("type=%-4s name=%-12s lang=0x%04X size=%-7d off=0x%08X head=%s"
              % (tname, name, lang, size, off, head))


def cmd_patch(path, name, datafile, out):
    p = PE(path)
    data = open(datafile, "rb").read()
    n = p.patch(name, data)
    print("patched %d entry(ies), %d bytes" % (n, len(data)))
    if n:
        p.save(out)
        print("saved ->", out)


def cmd_extract(path, outdir):
    import os
    p = PE(path)
    os.makedirs(outdir, exist_ok=True)
    for tname, name, lang, off, size, de in p.walk():
        if not name.startswith("TFRM"):
            continue
        fn = os.path.join(outdir, name + ".bin")
        open(fn, "wb").write(bytes(p.d[off:off + size]))
        print("%-12s %6d -> %s" % (name, size, fn))


if __name__ == "__main__":
    a = sys.argv
    if a[1] == "list":
        cmd_list(a[2])
    elif a[1] == "extract":
        cmd_extract(a[2], a[3])
    else:
        cmd_patch(a[2], a[3], a[4], a[5] if len(a) > 5 else a[2])
