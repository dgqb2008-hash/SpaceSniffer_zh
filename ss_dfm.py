# -*- coding: utf-8 -*-
"""
SpaceSniffer 汉化工具（二进制 DFM 解析 / 回写）

命令:
  dump   <dfm.bin> [out.txt]          把二进制 DFM 导出成可编辑的文本(路径=值)
  apply  <src.dfm.bin> <map.json> <out.dfm.bin>
         map.json 格式: { "路径": "中文", ... } 导出时同名的 *_map.json 可直接编辑
  check  <dfm.bin>                    解析并回写，验证字节完全一致
"""
import json
import sys

VA_NULL, VA_LIST, VA_INT8, VA_INT16, VA_INT32, VA_EXTENDED, VA_STRING, VA_IDENT = 0, 1, 2, 3, 4, 5, 6, 7
VA_FALSE, VA_TRUE, VA_BINARY, VA_SET, VA_LSTRING, VA_NIL, VA_COLLECTION = 8, 9, 10, 11, 12, 13, 14
VA_SINGLE, VA_CURRENCY, VA_DATE, VA_WSTRING, VA_INT64, VA_UTF8STRING, VA_DOUBLE = 15, 16, 17, 18, 19, 20, 21


class R:
    def __init__(self, buf):
        self.b, self.i = buf, 0

    def byte(self):
        v = self.b[self.i]
        self.i += 1
        return v

    def peek(self):
        return self.b[self.i]

    def raw(self, n):
        v = self.b[self.i:self.i + n]
        self.i += n
        return v

    def shortstr(self):
        n = self.byte()
        return self.raw(n)

    def int32(self):
        return int.from_bytes(self.raw(4), "little", signed=True)

    def eof(self):
        return self.i >= len(self.b)


class W:
    def __init__(self):
        self.parts = []

    def byte(self, v):
        self.parts.append(bytes([v & 0xFF]))

    def raw(self, v):
        self.parts.append(v)

    def shortstr(self, s):
        if isinstance(s, str):
            s = s.encode("gbk")
        assert len(s) < 256, "shortstring too long"
        self.byte(len(s))
        self.raw(s)

    def int32(self, v):
        self.raw(int(v).to_bytes(4, "little", signed=True))

    def out(self):
        return b"".join(self.parts)


def read_value(r):
    t = r.byte()
    if t == VA_NULL:
        return ("null", None)
    if t == VA_LIST:
        items = []
        while r.peek() != 0:
            items.append(read_value(r))
        r.byte()
        return ("list", items)
    if t == VA_INT8:
        return ("int", int.from_bytes(r.raw(1), "little", signed=True))
    if t == VA_INT16:
        return ("int", int.from_bytes(r.raw(2), "little", signed=True))
    if t == VA_INT32:
        return ("int", r.int32())
    if t == VA_INT64:
        return ("int", int.from_bytes(r.raw(8), "little", signed=True))
    if t == VA_EXTENDED:
        return ("raw", r.raw(10))
    if t == VA_SINGLE:
        return ("raw", r.raw(4))
    if t == VA_DOUBLE:
        return ("raw", r.raw(8))
    if t == VA_CURRENCY:
        return ("raw", r.raw(8))
    if t == VA_DATE:
        return ("raw", r.raw(8))
    if t == VA_STRING:
        return ("str", r.shortstr())
    if t == VA_LSTRING:
        return ("str", r.raw(r.int32()))
    if t == VA_UTF8STRING:
        return ("utf8", r.raw(r.int32()))
    if t == VA_WSTRING:
        n = r.int32()
        return ("wstr", r.raw(n * 2))
    if t == VA_IDENT:
        return ("ident", r.shortstr())
    if t == VA_FALSE:
        return ("bool", False)
    if t == VA_TRUE:
        return ("bool", True)
    if t == VA_NIL:
        return ("nil", None)
    if t == VA_BINARY:
        return ("bin", r.raw(r.int32()))
    if t == VA_SET:
        items = []
        while True:
            s = r.shortstr()
            if s == b"":
                break
            items.append(s)
        return ("set", items)
    if t == VA_COLLECTION:
        # 结构: vaCollection [ vaList 属性... 0 ]... 0
        items = []
        while r.peek() != 0:
            b = r.byte()
            if b != VA_LIST:
                raise ValueError("bad collection item start %d at %d" % (b, r.i - 1))
            props = []
            while r.peek() != 0:
                pn = r.shortstr()
                props.append((pn, read_value(r)))
            r.byte()
            items.append({"props": props})
        r.byte()
        return ("collection", items)
    raise ValueError("unknown value type %d at %d" % (t, r.i - 1))


def write_value(w, v):
    t, p = v
    if t == "null":
        w.byte(VA_NULL)
    elif t == "list":
        w.byte(VA_LIST)
        for it in p:
            write_value(w, it)
        w.byte(0)
    elif t == "int":
        if -128 <= p <= 127:
            w.byte(VA_INT8)
            w.raw(int(p).to_bytes(1, "little", signed=True))
        elif -32768 <= p <= 32767:
            w.byte(VA_INT16)
            w.raw(int(p).to_bytes(2, "little", signed=True))
        else:
            w.byte(VA_INT32)
            w.int32(p)
    elif t == "raw":
        w.byte({10: VA_EXTENDED, 4: VA_SINGLE, 8: VA_DOUBLE}[len(p)])
        w.raw(p)
    elif t == "str":
        b = p if isinstance(p, bytes) else p.encode("gbk")
        if len(b) < 256:
            w.byte(VA_STRING)
            w.shortstr(b)
        else:
            w.byte(VA_LSTRING)
            w.int32(len(b))
            w.raw(b)
    elif t == "utf8":
        w.byte(VA_UTF8STRING)
        w.int32(len(p))
        w.raw(p)
    elif t == "wstr":
        w.byte(VA_WSTRING)
        w.int32(len(p) // 2)
        w.raw(p)
    elif t == "ident":
        w.byte(VA_IDENT)
        w.shortstr(p)
    elif t == "bool":
        w.byte(VA_TRUE if p else VA_FALSE)
    elif t == "nil":
        w.byte(VA_NIL)
    elif t == "bin":
        w.byte(VA_BINARY)
        w.int32(len(p))
        w.raw(p)
    elif t == "set":
        w.byte(VA_SET)
        for it in p:
            w.shortstr(it)
        w.byte(0)
    elif t == "collection":
        w.byte(VA_COLLECTION)
        for it in p:
            w.byte(VA_LIST)
            for pn, pv in it["props"]:
                w.shortstr(pn)
                write_value(w, pv)
            w.byte(0)
        w.byte(0)
    else:
        raise ValueError("bad type " + t)


def read_object(r):
    flags, childpos = 0, None
    b = r.peek()
    if (b & 0xF0) == 0xF0:
        r.byte()
        flags = b & 0x0F
        if flags & 0x02:
            childpos = read_value(r)[1]
    cls = r.shortstr()  # 二进制 DFM 中顺序为: 类名, 对象名
    name = r.shortstr()
    props = []
    while r.peek() != 0:
        pn = r.shortstr()
        props.append((pn, read_value(r)))
    r.byte()
    children = []
    while r.peek() != 0:
        children.append(read_object(r))
    r.byte()
    return {"class": cls, "name": name, "flags": flags, "childpos": childpos,
            "props": props, "children": children}


def write_object(w, o):
    if o["flags"]:
        w.byte(0xF0 | o["flags"])
        if o["childpos"] is not None:
            write_value(w, ("int", o["childpos"]))
    w.shortstr(o["class"])
    w.shortstr(o["name"])
    for pn, pv in o["props"]:
        w.shortstr(pn)
        write_value(w, pv)
    w.byte(0)
    for c in o["children"]:
        write_object(w, c)
    w.byte(0)


def parse(buf):
    assert buf[:4] == b"TPF0", "not a binary DFM"
    r = R(buf)
    r.raw(4)
    o = read_object(r)
    assert r.eof(), "trailing bytes at %d / %d" % (r.i, len(buf))
    return o


def serialize(o):
    w = W()
    w.raw(b"TPF0")
    write_object(w, o)
    return w.out()


def dec(v):
    if isinstance(v, bytes):
        return v.decode("gbk", "replace")
    return v


def walk(o, path, out):
    here = path + [dec(o["class"]) + "." + dec(o["name"])]
    for pn, pv in o["props"]:
        out.append((here + [dec(pn)], pv))
        if pv[0] == "collection":
            for i, it in enumerate(pv[1]):
                base = here + [dec(pn), "item[%d]" % i]
                for qn, qv in it["props"]:
                    out.append((base + [dec(qn)], qv))
    for c in o["children"]:
        walk(c, here, out)


def set_by_path(root, path, newbytes):
    """path: 形如 ['TfrmView.frmView','TPanel.pnlFilter','Caption']"""
    def find(o, p, i):
        want = p[i]
        cur = dec(o["class"]) + "." + dec(o["name"])
        if cur != want:
            return None
        if i == len(p) - 2:  # 最后一个元素是属性名，属于当前对象
            return ("prop", o, p[-1])
        for c in o["children"]:
            r = find(c, p, i + 1)
            if r:
                return r
        return None

    kind, node, last = find(root, path, 0)
    if kind == "prop":
        for i, (pn, pv) in enumerate(node["props"]):
            if dec(pn) == last:
                node["props"][i] = (pn, (pv[0], newbytes))
                return True
    return False


def cmd_dump(path, outp):
    buf = open(path, "rb").read()
    root = parse(buf)
    assert serialize(root) == buf, "回写不一致，解析器需修正"
    items = []
    walk(root, [], items)
    lines, mp = [], {}
    for p, v in items:
        key = "/".join(p)
        if v[0] in ("str", "utf8", "wstr"):
            val = dec(v[1]) if v[0] != "wstr" else v[1].decode("utf-16-le", "replace")
            if v[0] == "utf8":
                val = v[1].decode("utf-8", "replace")
            lines.append("%s\t%s" % (key, val.replace("\n", "\\n").replace("\r", "\\r")))
            mp[key] = val
        elif v[0] == "ident":
            lines.append("%s\t#%s" % (key, dec(v[1])))
    open(outp, "w", encoding="utf-8").write("\n".join(lines))
    json.dump(mp, open(outp.replace(".txt", "_map.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("ok: %s  (可翻译条目 %d)" % (outp, len(mp)))


def cmd_check(path):
    buf = open(path, "rb").read()
    root = parse(buf)
    out = serialize(root)
    print("round-trip %s, %d bytes" % ("OK" if out == buf else "FAIL", len(buf)))


def cmd_apply(src, mapfile, dst):
    buf = open(src, "rb").read()
    root = parse(buf)
    mp = json.load(open(mapfile, encoding="utf-8"))
    n = 0
    for k, v in mp.items():
        if not v:
            continue
        raw = v[1:].encode("ascii") if v.startswith("#") else v.encode("gbk")
        if set_by_path(root, k.split("/"), raw):
            n += 1
    open(dst, "wb").write(serialize(root))
    print("applied %d -> %s" % (n, dst))


if __name__ == "__main__":
    a = sys.argv
    if a[1] == "dump":
        cmd_dump(a[2], a[3] if len(a) > 3 else a[2] + ".txt")
    elif a[1] == "check":
        cmd_check(a[2])
    elif a[1] == "apply":
        cmd_apply(a[2], a[3], a[4])
    else:
        print(__doc__)
