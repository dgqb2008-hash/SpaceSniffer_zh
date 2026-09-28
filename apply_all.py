# -*- coding: utf-8 -*-
"""把汉化表应用到所有窗体资源，输出到 res_out/。"""
import json
import os
import ss_dfm as D

zh = json.load(open("zh_all.json", encoding="utf-8"))
os.makedirs("res_out", exist_ok=True)

for form, mp in zh.items():
    src = os.path.join("res_new", form + ".bin")
    buf = open(src, "rb").read()
    root = D.parse(buf)
    n = 0
    for k, v in mp.items():
        if not v:
            continue
        raw = v[1:].encode("ascii") if v.startswith("#") else v.encode("gbk")
        if D.set_by_path(root, k.split("/"), raw):
            n += 1
    out = D.serialize(root)
    dst = os.path.join("res_out", form + ".bin")
    open(dst, "wb").write(out)
    flag = "OK " if len(out) <= len(buf) else "增大"
    print("%-12s 应用 %3d 条  %6d -> %6d  %s" % (form, n, len(buf), len(out), flag))
