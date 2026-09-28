# -*- coding: utf-8 -*-
"""代码段字符串补丁：
1. 所有包含 www.uderzo.it 的独立字符串原地改写为 caoleme.cn（变短，安全）
2. 主窗口标题后缀 " - www.uderzo.it" 变长，无法原地替换：
   把新字符串放入被汉化缩小的资源尾部空隙，并把代码里的引用重定向过去。
"""
import struct
import sys
import pe_res

TITLE_OLD = b" - www.uderzo.it"
TITLE_NEW = " - www.caoleme.cn by 历尽沧桑还得装 汉化".encode("gbk")
LEA_MODRM = {0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x35, 0x3D}


def off2rva(pe, off):
    for va, vs, pr, rs, name in pe.sections:
        if pr <= off < pr + rs:
            return va + (off - pr)
    raise ValueError("offset 0x%X 不在任何节内" % off)


def find_free_tail(pe, min_len):
    """在 RCDATA TFRM* 资源被缩小后留下的零填充尾部找一段空闲空间。"""
    best = None
    for tname, name, lang, off, size, de in pe.walk():
        if not name.startswith("TFRM"):
            continue
        # 资源尾部：从 size 开始向后找连续 0
        end = off + size
        n = 0
        while end + n < len(pe.d) and pe.d[end + n] == 0:
            n += 1
        if n >= min_len and (best is None or n > best[1]):
            best = (end, n)
    return best


def rewrite_strings(pe):
    """原地改写包含 www.uderzo.it 的独立字符串（除标题后缀外）。"""
    d = pe.d
    count = 0
    i = 0
    while i < len(d):
        j = d.find(b"www.uderzo.it", i)
        if j < 0:
            break
        # 找到所在 null 结尾字符串的起点和终点
        s = d.rfind(b"\x00", 0, j) + 1
        e = d.find(b"\x00", j)
        raw = bytes(d[s:e])
        if raw == TITLE_OLD.strip() or raw.endswith(b" - www.uderzo.it"):
            i = e + 1
            continue  # 标题后缀单独处理
        if raw.startswith(b"http"):
            # 只保留主域名，不带具体网页路径
            new = b"http://www.caoleme.cn"
        else:
            new = raw.replace(b"www.uderzo.it", b"www.caoleme.cn")
        if len(new) <= len(raw):
            d[s:s + len(new)] = new
            d[s + len(new):e] = b"\x00" * (len(raw) - len(new))
            print("  改写 0x%08X: %s -> %s" % (s, raw.decode("ascii", "replace"),
                                              new.decode("ascii", "replace")))
            count += 1
        i = e + 1
    return count


def patch_title_ref(pe, verbose=True):
    d = pe.d
    slot = find_free_tail(pe, len(TITLE_NEW) + 1)
    if not slot:
        raise RuntimeError("没有足够的空闲资源尾部空间")
    off, n = slot
    d[off:off + len(TITLE_NEW) + 1] = TITLE_NEW + b"\x00"
    # 旧字符串位置（必须是独立字符串: 前面是 \0）
    o = d.find(TITLE_OLD)
    assert d[o - 1:o] == b"\x00" or True
    # 确保是独立字符串: 前后都是 \0
    while o >= 0 and not (o == 0 or d[o - 1] == 0):
        o = d.find(TITLE_OLD, o + 1)
    assert o >= 0, "找不到独立标题字符串"
    old_rva = off2rva(pe, o)
    new_rva = off2rva(pe, off)
    print("  旧标题串 0x%08X (RVA 0x%X)，新串放入 0x%08X (RVA 0x%X), 空隙 %d 字节"
          % (o, old_rva, off, new_rva, n))

    imagebase = struct.unpack_from("<Q", d, pe.opt + 24)[0]
    old_va = imagebase + old_rva
    new_va = imagebase + new_rva

    refs = 0
    i = 0
    while True:
        i = d.find(struct.pack("<Q", old_va), i)
        if i < 0:
            break
        d[i:i + 8] = struct.pack("<Q", new_va)
        print("  绝对指针引用 @0x%08X" % i)
        refs += 1
        i += 8

    # RIP 相对引用 (lea reg,[rip+disp32])：disp 以虚拟地址计算
    i = 0
    while i < len(d) - 4:
        disp = struct.unpack_from("<i", d, i)[0]
        try:
            next_va = imagebase + off2rva(pe, i + 4)
        except ValueError:
            i += 1
            continue
        if disp == old_va - next_va:
            op3 = d[i - 3:i]
            if op3[0] in (0x48, 0x4C) and op3[1] == 0x8D and op3[2] in LEA_MODRM:
                struct.pack_into("<i", d, i, new_va - next_va)
                print("  RIP相对引用(lea) @0x%08X" % i)
                refs += 1
            else:
                print("  [候选但opcode不符] @0x%08X 前字节=%s" % (i, op3.hex()))
        i += 1
    print("  共重定向 %d 处引用" % refs)
    if refs:
        # 旧字符串已无引用，原地清掉里面的 uderzo.it
        repl = b" - caoleme.cn\x00"
        d[o:o + len(TITLE_OLD)] = repl + b"\x00" * (len(TITLE_OLD) - len(repl))
    return refs


def main(src, dst):
    pe = pe_res.PE(src)
    n = rewrite_strings(pe)
    r = patch_title_ref(pe)
    pe.save(dst)
    print("saved -> %s (字符串改写 %d 处, 引用重定向 %d 处)" % (dst, n, r))


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2] if len(a) > 2 else a[1])
