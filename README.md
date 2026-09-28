# SpaceSniffer 汉化工程（v2.2.0.27）

> 用纯 Python 直接改写 PE 资源与代码段字符串，把 **SpaceSniffer 2.2.0.27** 的界面汉化为简体中文。
> 无需 Delphi、无需源码、无需资源编辑器（ResHacker / Resource Hacker），全程脚本化、可复现。

![图片描述](OK.png)

![Python](https://img.shields.io/badge/Python-3.6%2B-blue)
![platform](https://img.shields.io/badge/platform-windows-lightgrey)
![deps](https://img.shields.io/badge/dependencies-none-green)
![license](https://img.shields.io/badge/scripts-MIT-orange)

---

## 目录

- [一、项目简介](#一项目简介)
- [二、汉化覆盖范围](#二汉化覆盖范围)
- [三、目录结构](#三目录结构)
- [四、工作原理](#四工作原理)
- [五、环境要求](#五环境要求)
- [六、完整复现流程](#六完整复现流程)
- [七、脚本与命令参考](#七脚本与命令参考)
- [八、数据文件格式说明](#八数据文件格式说明)
- [九、翻译表编辑规范（重要）](#九翻译表编辑规范重要)
- [十、旧版译文复用机制](#十旧版译文复用机制)
- [十一、常见问题与注意事项](#十一常见问题与注意事项)
- [十二、待办与后续计划](#十二待办与后续计划)
- [十三、版权与免责声明](#十三版权与免责声明)

---

## 一、项目简介

[SpaceSniffer](http://www.uderzo.it/main_products/space_sniffer/) 是一款用 Delphi 编写的磁盘空间可视化分析工具，官方长期只提供英文界面。

本工程提供一套**二进制级汉化工具链**：

1. 直接从 `SpaceSniffer.exe` 的 PE 资源目录（ `RCDATA` ）中抽取窗体资源；
2. 解析 Delphi **二进制 DFM**（`TPF0`）结构，把所有可翻译字符串导出为 JSON；
3. 复用旧版汉化（1.3.0.2）的译文 + 人工补译，生成汉化表；
4. 把译文回写进二进制 DFM，再原地写回 exe 的 PE 资源；
5. 最后修补代码段中的硬编码字符串（官网域名、主窗口标题）。

产物 `SpaceSniffer2.2.0.27_zh.exe` 与原始 exe **文件大小完全相同**（8,691,097 字节），仅仅是资源内容被替换，不新增节、不改动入口点、不破坏数字签名以外的任何结构。

主要特点：

- **零依赖**：只用 Python 标准库（`struct` / `json` / `re`），pip 都不用装。
- **无损回写**：DFM 解析器保证「解析 → 序列化」字节级一致（`ss_dfm.py check`），不会破坏窗体结构。
- **原地替换**：中文（GBK）通常比英文短，资源只会变小不会变大，因此无需重建资源表。
- **可追溯**：所有翻译以「控件路径 → 中文」的 JSON 保存，改一个词只需编辑文本再重跑一次。

---

## 二、汉化覆盖范围

汉化对象为 exe 中 8 个 `RCDATA` 窗体资源：

| 资源名 | 对应界面 | 可译条目 | 已译 | 说明 |
|---|---|---:|---:|---|
| `TFRMABOUT` | 关于窗口 | 12 | 8 | 版本、作者、致谢 |
| `TFRMCONFIG` | 设置 / 选项 | 123 | 108 | 最大的一个窗体 |
| `TFRMCONSOLE` | 控制台 / 脚本 | 10 | 5 | |
| `TFRMEXPORT` | 导出向导 | 77 | 48 | 含大量模板示例文本 |
| `TFRMHELP` | 帮助 | 3 | 1 | |
| `TFRMMAIN` | 主窗口 | 69 | 53 | 菜单、工具栏、状态栏 |
| `TFRMSTART` | 启动 / 快速开始 | 12 | 11 | 含较长说明文本 |
| `TFRMVIEW` | 视图 / 筛选器 | 20 | 17 | 筛选栏、进度提示 |
| **合计** | | **326** | **251** | 约 **77%** |

> 说明：
> - `all_new.json` 共导出 904 条字符串，其中大量是颜色常量（`#clBtnFace`）、字体名、枚举标识等**不需要翻译**的条目；上表统计的是「含字母、非 `#` 常量、非 `<%...%>` 模板」的**真正可译条目**。
> - 剩余未译部分主要是：工具栏/Action 的内部名称（`ToolBar1`、`actRefresh`…）、脚本宏占位符（`{script}`、`{if{value1}=={value2}?...}`）、以及由 `code_patch.py` 单独处理的官网域名。详见 [remain.txt](remain.txt) 与 [todo.txt](todo.txt)。

代码段（非资源）的额外处理：

| 原字符串 | 汉化后 |
|---|---|
| `www.uderzo.it`（各处 URL） | `www.caoleme.cn` |
| 主窗口标题后缀 ` - www.uderzo.it` | ` - www.caoleme.cn by 历尽沧桑还得装 汉化` |

---

## 三、目录结构

```
.
├── pe_res.py          # PE 资源目录解析器：列出 / 抽取 / 原地改写 RCDATA
├── ss_dfm.py          # Delphi 二进制 DFM(TPF0) 解析与序列化 + 字符串导出/回写
├── dump_all.py        # 批量导出新旧两个版本的窗体字符串 -> all_new.json / all_old.json
├── make_map.py        # 生成汉化表 zh_all.json（复用旧版 + 人工补充），并输出 remain.txt
├── apply_all.py       # 把 zh_all.json 应用到 res_new/*.bin，输出到 res_out/
├── code_patch.py      # 代码段字符串原地改写 + 变长标题的引用重定向
├── todo.py            # 统计仍未翻译的「唯一英文原文」 -> todo.txt，便于批量补译
│
├── res_new/           # 从新版(2.2.0.27) exe 抽取的原始窗体资源（9 个 .bin）
├── res_old/           # 旧版(1.3.0.2)汉化版抽取的窗体资源，用于复用译文（9 个 .bin）
├── res_out/           # 构建产物：应用汉化表后的窗体资源（脚本生成，可随时重跑）
│
├── all_new.json       # 新版全部字符串 {窗体: {路径: 英文}}
├── all_old.json       # 旧版全部字符串（含中文译文）{窗体: {路径: 文本}}
├── zh_all.json        # ★ 汉化表 {窗体: {路径: 中文}} —— 主要维护对象
├── manual_en.json     # 人工补译：按「英文原文」匹配（全局生效）
├── manual_path.json   # 人工补译：按「控件路径」匹配（优先级最高）
├── remain.txt         # 各窗体仍未翻译的条目清单
├── todo.txt           # 去重后的待译文本清单（含出现次数）
│
├── SpaceSniffer2.2.0.27.exe      # 原版程序（构建输入）
├── SpaceSniffer2.2.0.27_zh.exe   # 汉化产物（构建输出）
└── spacesniffer汉化.zip          # 打包分发用压缩包
```

> `res_new/TFRMVIEW_zh.bin` 是某次手工修改后的 `TFRMVIEW` 备份，与 `res_out/TFRMVIEW.bin` 内容相同，**不参与构建**；`res_old/TFRMVIEW_0.bin` 同理。真正的资源清单以 exe 为准（8 个 `TFRM*`）。

---

## 四、工作原理

### 1. PE 资源层（`pe_res.py`）

不调用 Win32 资源 API，直接按 PE 结构手工走三层资源目录：

```
IMAGE_DATA_DIRECTORY[2] (Resource)
  └─ 类型目录 (RT_RCDATA = 10)
       └─ 名称目录 (TFRMABOUT / TFRMCONFIG / ...)
            └─ 语言目录 (lang)
                 └─ IMAGE_RESOURCE_DATA_ENTRY -> RVA + Size
```

`patch()` 只在**原资源长度范围内**覆盖数据，尾部补 `\0`，并把数据目录项里的 `Size` 改成新长度——因此文件体积永远不增加，节表、偏移全部保持不变。

### 2. DFM 层（`ss_dfm.py`）

Delphi 二进制窗体文件以 `TPF0` 开头，是一棵树：

```
object: [0xF0|flags] 类名(shortstr) 对象名(shortstr) 属性列表 0 子对象列表 0
value : 类型字节(vaInt8/vaString/vaLString/vaIdent/vaCollection/...) + 载荷
```

`ss_dfm.py` 完整实现了 `read_value` / `write_value` 的 20 余种 `TValueType`，并支持 `vaCollection`（工具栏按钮、列表列等）。`parse → serialize` 的 round-trip 必须字节一致，否则解析器有 bug（`check` 命令就是干这个的）。

字符串以**控件路径**为键导出，形如：

```
TfrmView.frmView/TPanel.pnlFilter/TButton.btnFilter/Caption
TfrmView.frmView/TActionList.actions/TAction.actStartSniffing/Caption
TfrmMain.frmView/ToolBar.ToolBar1/item[0]/Caption
```

### 3. 代码段层（`code_patch.py`）

标题后缀 `" - www.uderzo.it"` 变成中文后**变长**，无法原地替换，采用的办法是：

1. 资源被汉化缩小后，尾部会留下一段 `\0` 空隙 → `find_free_tail()` 找到最大的那段；
2. 把新标题串（GBK）写进空隙；
3. 扫描全文，把所有指向旧串的**绝对地址（8 字节 VA）**和 **`lea reg,[rip+disp32]` 的 RIP 相对位移**改成指向新串；
4. 旧串失去引用后就地清掉，避免出现半截残留。

其余 `www.uderzo.it` 都是独立 C 字符串且替换后变短，直接原地改写即可。

---

## 五、环境要求

- **Python 3.6+**（实测 Python 3.9.9）
- 无第三方依赖
- 目标文件为 Windows PE，但脚本本身跨平台（Linux / macOS 也能跑，只是没法直接运行产物）

---

## 六、完整复现流程

假设手上有原版 `SpaceSniffer2.2.0.27.exe`。以下所有命令都在项目根目录执行。

### 步骤 0：准备待汉化的副本

```powershell
copy SpaceSniffer2.2.0.27.exe SpaceSniffer_zh.exe
```

> 后续步骤 5 会**原地**改写这个副本。

### 步骤 1：从 exe 抽取窗体资源

```powershell
python pe_res.py extract SpaceSniffer2.2.0.27.exe res_new
```

输出示例：

```
TFRMABOUT     11818 -> res_new\TFRMABOUT.bin
TFRMCONFIG    28700 -> res_new\TFRMCONFIG.bin
...
```

### 步骤 2：导出两个版本的字符串

```powershell
python dump_all.py
```

生成 `all_new.json`（新版，待译）与 `all_old.json`（旧版汉化版，含译文），并打印可复用情况：

```
TFRMABOUT     新=42   可直接沿用旧版=2
TFRMCONFIG    新=289  可直接沿用旧版=106
...
合计 904 条，其中 221 条可从旧版汉化直接复用
```

> 若没有旧版汉化 exe，`res_old/` 留空即可，脚本会正常产出空的 `all_old.json`，只是复用阶段无译文可用。
> 若新版新增了窗体，记得把新窗体名加进 `dump_all.py` 顶部的 `FORMS` 列表。

### 步骤 3：生成汉化表

```powershell
python make_map.py
```

产出：

- `zh_all.json` —— 汉化表（**改这个文件就是改翻译**）
- `remain.txt` —— 按窗体分组的未译清单

```
已翻译 281 / 904
  TFRMABOUT      10 / 42
  ...
```

### 步骤 4：（人工）补译

1. 打开 `remain.txt` 或 `todo.txt`（`todo.txt` 是去重版，带出现次数，更高效）；
2. 通用词（同一个英文到处出现）写进 `manual_en.json`；
3. 只针对某个控件的写法写进 `manual_path.json`；
4. 也可以直接改 `zh_all.json`；
5. **重复执行步骤 3**（`make_map.py` 可反复运行，人工补充优先级最高，不会丢失）。

### 步骤 5：生成汉化后的资源

```powershell
python apply_all.py
```

```
TFRMABOUT    应用  10 条   11818 ->  11792  OK
TFRMCONFIG   应用 122 条   28700 ->  27754  OK
...
```

> 每行末尾必须是 `OK`。若出现 **「增大」**，说明中文比英文长，原资源放不下，需要缩短译文或用 `code_patch.py` 的重定向思路单独处理（见 [常见问题](#十一常见问题与注意事项)）。

### 步骤 6：回写进 exe

```powershell
$forms = 'TFRMABOUT','TFRMCONFIG','TFRMCONSOLE','TFRMEXPORT','TFRMHELP','TFRMMAIN','TFRMSTART','TFRMVIEW'
foreach ($f in $forms) { python pe_res.py patch SpaceSniffer_zh.exe $f "res_out/$f.bin" }
```

（CMD 版本）

```bat
for %f in (TFRMABOUT TFRMCONFIG TFRMCONSOLE TFRMEXPORT TFRMHELP TFRMMAIN TFRMSTART TFRMVIEW) do python pe_res.py patch SpaceSniffer_zh.exe %f res_out\%f.bin
```

不加第 4 个参数时，`pe_res.py` 默认就地写入第 2 个参数指定的 exe。

### 步骤 7：修补代码段字符串

```powershell
python code_patch.py SpaceSniffer_zh.exe
```

```
  改写 0x004A1234: http://www.uderzo.it/main_products/space_sniffer/ -> http://www.caoleme.cn
  旧标题串 0x00B1xxxx (RVA 0x...)，新串放入 0x00B2xxxx (RVA 0x...), 空隙 1024 字节
  绝对指针引用 @0x...
  RIP相对引用(lea) @0x...
saved -> SpaceSniffer_zh.exe (字符串改写 N 处, 引用重定向 M 处)
```

> **顺序不能反**：必须先做步骤 6（资源缩小腾出空隙），再做步骤 7。

### 步骤 8：验证

```powershell
python -c "import pe_res,os;p=pe_res.PE('SpaceSniffer_zh.exe');print(len(p.d))"   # 应与原版一致
python pe_res.py list SpaceSniffer_zh.exe
```

然后直接双击运行 `SpaceSniffer_zh.exe`，检查各窗口文字与中文显示是否正常（无乱码说明 `Font.Charset` 已生效）。

---

## 七、脚本与命令参考

### `pe_res.py` —— PE 资源工具

| 命令 | 说明 |
|---|---|
| `python pe_res.py list <exe>` | 列出所有 `RCDATA` 资源（类型/名称/语言/大小/偏移） |
| `python pe_res.py extract <exe> <outdir>` | 抽取所有 `TFRM*` 资源为 `*.bin` |
| `python pe_res.py patch <exe> <资源名> <新数据> [输出exe]` | 原地替换指定资源，省略输出则就地写回 |

### `ss_dfm.py` —— DFM 工具（单窗体粒度）

| 命令 | 说明 |
|---|---|
| `python ss_dfm.py dump <dfm.bin> [out.txt]` | 导出为 `路径<TAB>值` 文本，并生成同名 `*_map.json` |
| `python ss_dfm.py apply <src.bin> <map.json> <out.bin>` | 把 map 应用回二进制 DFM |
| `python ss_dfm.py check <dfm.bin>` | 解析后重新序列化，验证字节一致（`OK` / `FAIL`） |

### 其他脚本

| 脚本 | 作用 | 输入 → 输出 |
|---|---|---|
| `dump_all.py` | 批量导出字符串 | `res_new/`+`res_old/` → `all_new.json`、`all_old.json` |
| `make_map.py` | 生成汉化表 | `all_*.json` + `manual_*.json` → `zh_all.json`、`remain.txt` |
| `apply_all.py` | 应用汉化表 | `res_new/` + `zh_all.json` → `res_out/` |
| `code_patch.py` | 代码段字符串改写/重定向 | exe → exe |
| `todo.py` | 统计去重后的待译文本 | `all_new.json` + `zh_all.json` → `todo.txt` |

---

## 八、数据文件格式说明

### `all_new.json` / `all_old.json`（自动生成，不要手改）

```json
{
  "TFRMMAIN": {
    "TfrmMain.frmMain/Caption": "SpaceSniffer",
    "TfrmMain.frmMain/Color": "#clBtnFace",
    "TfrmMain.frmMain/Font.Charset": "#DEFAULT_CHARSET"
  }
}
```

以 `#` 开头的值表示 DFM 标识符（`vaIdent`），如颜色、枚举、字符集。

### `zh_all.json`（★ 汉化表，主要维护对象）

```json
{
  "TFRMVIEW": {
    "TfrmView.frmView/TPanel.pnlFilter/TButton.btnFilter/Caption": "过滤器(&F)",
    "TfrmView.frmView/TActionList.actions/TAction.actStartSniffing/Caption": "开始嗅探",
    "TfrmView.frmView/TPanel.pnlClosing/Caption": "关闭..."
  }
}
```

- 键为**控件路径**，值为中文；值为空串表示「不翻译」，会被跳过。
- 值以 `#` 开头会按**标识符**写入（ASCII），例如 `#GB2312_CHARSET`。

### `manual_en.json`（按英文原文补译，全局生效）

```json
{
  "Window": "窗口",
  "Go parent": "转到上级目录",
  "Special chars": "特殊字符"
}
```

### `manual_path.json`（按控件路径补译，优先级最高）

```json
{
  "TFRMABOUT": {
    "TfrmAbout.frmAbout/Caption": "历尽沧桑还得装 汉化",
    "TfrmAbout.frmAbout/TLabel.lblURL/Caption": "www.caoleme.cn"
  }
}
```

### `remain.txt` / `todo.txt`

- `remain.txt`：按 `===== 窗体名 (已译/总数) =====` 分组，每行 `路径<TAB>英文原文`。
- `todo.txt`：去重版，每行 `出现次数<TAB>英文原文`，按出现频率排序，适合一次性批量补译。

---

## 九、翻译表编辑规范（重要）

1. **编码是 GBK，不是 UTF-8**
   二进制 DFM 里 Delphi 的 `string` 是 ANSI 字节串，写入时统一 `encode("gbk")`。生僻字（如 emoji、部分汉字扩展区）无法编码，请避免使用。

2. **译文不能比原文长**
   `pe_res.py patch` 要求 `len(new) <= size`。中文通常更短（约省 30%~40%），一般没问题；`apply_all.py` 会打印每窗体前后大小，出现「增大」就必须缩短译文。

3. **保留 `&` 加速键**
   原文 `&Filter` 应译为 `过滤器(&F)`，不要丢掉 `&`，也不要与同一窗体内其他控件的加速键冲突。

4. **保留首尾空格**
   部分控件（如标签）靠空格做缩进对齐，导出时空格会保留，翻译时不要随手删掉（例如 `"   过滤器 "`）。

5. **不要翻译这些**
   - `#` 开头的常量/枚举（`#clBtnFace`、`#DEFAULT_CHARSET`）
   - `Font.Name`（字体名）
   - `<%...%>` 模板占位符、`{script}` 这类脚本宏
   - 控件内部名称（`ToolBar1`、`actRefresh`）——改了不影响显示，但会破坏程序内部查找

6. **中文字体字符集**
   旧版汉化把 `Font.Charset` 从 `#DEFAULT_CHARSET` 改成了 `#GB2312_CHARSET`，`make_map.py` 会自动沿用（第一轮 b）。若某个窗体中文显示为方框，检查对应窗体的 `Font.Charset` 是否为 `#GB2312_CHARSET`。

7. **改完只需重跑**
   ```
   python make_map.py && python apply_all.py
   ```
   然后从[流程步骤 6](#步骤-6回写进-exe)重新打 exe（**务必从原版 exe 重新复制一份**，不要在上一次产物上叠加）。

---

## 十、旧版译文复用机制

`make_map.py` 按四轮优先级填充 `zh_all.json`：

| 轮次 | 策略 | 标记 |
|---|---|---|
| 1 | **同路径复用**：新版某路径在旧版存在且旧版值含中文 → 直接沿用 | `path` |
| 1b | **字符集沿用**：`Font.Charset` 为 `#DEFAULT_CHARSET` 而旧版是 `#GB2312_CHARSET` → 沿用 | `charset` |
| 2 | **同原文复用**：第 1 轮建立的「英文→中文」词典，遇到相同英文文本自动填充 | `value` |
| 3 | **人工按路径**：`manual_path.json` | `manual` |
| 4 | **人工按原文**：`manual_en.json` | `manual-en` |

因此**已经翻译过的内容不会丢失**：只要改 `manual_*.json`，重跑即可增量覆盖。

---

## 十一、常见问题与注意事项

**Q：为什么不用 Resource Hacker / 通用汉化工具？**
A：这类工具大多只处理 `RT_DIALOG` 标准资源，对 Delphi 的 `RCDATA` + 二进制 DFM 无能为力；而且可视化改写容易出现长度溢出、结构错位。本工程直接解析 DFM 结构，可精确控制到每一个属性。

**Q：译文太长放不下怎么办？**
A：三种办法，按推荐顺序：
   1. 缩短译文（首选，中文通常远短于英文）；
   2. 缩短同一窗体里其他译文，腾出空间（资源是整块替换的，看的是总量）；
   3. 仿照 `code_patch.py` 的做法：把长串放到其他资源缩小后的空隙里，再重定向引用。

**Q：中文显示为方框/乱码？**
A：把该窗体的 `Font.Charset` 设为 `#GB2312_CHARSET`（写进 `manual_path.json` 后重跑即可）。

**Q：改了一个词，需要重跑全部流程吗？**
A：不用。改 `zh_all.json` / `manual_*.json` → `make_map.py` → `apply_all.py` → 步骤 6、7。

**Q：能用在别的 Delphi 程序上吗？**
A：可以。`ss_dfm.py` 是通用的二进制 DFM 解析/回写库，`pe_res.py` 是通用的 PE `RCDATA` 补丁器，把 `dump_all.py` 里的 `FORMS` 换成目标程序的资源名即可。

**Q：汉化后的程序会被杀毒软件报毒吗？**
A：修改 exe 会破坏原有数字签名，个别杀软可能误报。本工程只替换资源区与个别字符串的字节，不含任何代码注入/壳，可自行用 `pe_res.py list`、文件哈希、节表对比等方式核验。建议从官方渠道下载原版 exe 后自行构建。

**Q：仓库要不要提交 exe？**
A：建议不要。原版 exe 属于第三方二进制，且体积巨大。推荐 `.gitignore`：

```gitignore
__pycache__/
*.pyc
res_out/
*.exe
*.zip
```

汉化产物请在 GitHub **Releases** 中发布。

---

## 十二、待办与后续计划

- [ ] 补译 `todo.txt` 中剩余的约 62 条唯一文本（配置向导、导出模板说明部分内容较多）
- [ ] 校验 `TFRMEXPORT` 里长段模板示例文本的排版（换行符在 DFM 中以 `#13#10` 形式存在，导出时用 `\n` 转义）
- [ ] 把步骤 5~7 合并成一键 `build.py`
- [ ] 适配 SpaceSniffer 后续版本（只需重跑步骤 1~7）
- [ ] 附带界面截图与 Release 说明

---

## 十三、版权与免责声明

- **SpaceSniffer 的著作权归原作者 Uderzo Umberto 及 www.uderzo.it 所有**，本仓库不包含也不分发其源码，仅提供对二进制文件的**本地修改脚本**与方法说明。请遵守原软件的许可条款，原版程序请从官方站点获取。
- 本仓库中的 Python 脚本（`pe_res.py`、`ss_dfm.py`、`dump_all.py`、`make_map.py`、`apply_all.py`、`code_patch.py`、`todo.py`）以 **MIT** 许可发布，可自由使用、修改与分发。
- 汉化产物仅供学习交流，**请勿用于任何商业用途**；因使用本工程造成的任何问题，作者不承担责任。
- 代码段替换把官网链接改为了 `www.caoleme.cn`，如需还原，修改 `code_patch.py` 顶部的 `TITLE_NEW` 与 `rewrite_strings()` 中的替换目标即可。

---

### 致谢

- [SpaceSniffer](http://www.uderzo.it/main_products/space_sniffer/) —— Uderzo Umberto 的优秀作品
- 旧版（1.3.0.2）汉化作者 —— 提供了大量可复用的初始译文
- 汉化/整理：**历尽沧桑还得装**
