# -*- coding: utf-8 -*-
"""生成《防汛监测预警智能体平台 — 项目说明与团队分工》Word 文档（降难度版）。"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

CN_BODY = "宋体"
CN_HEAD = "微软雅黑"
EN_BODY = "Times New Roman"
EN_HEAD = "Microsoft YaHei"

NAVY = "1F3864"
BLUE = "2E5C8A"
GRAY = "595959"
LIGHT = "D9E2F3"
HEADER_BG = "1F3864"


# ---------- 基础工具 ----------

def set_font(run, cn=CN_BODY, en=EN_BODY, size=10.5, bold=False, color=None):
    run.font.name = en
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), cn)
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def shade_cell(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def set_cell_margins(cell, top=60, bottom=60, left=100, right=100):
    tcPr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for tag, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        el = OxmlElement(f"w:{tag}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tcPr.append(mar)


def para(doc, text="", size=10.5, bold=False, color=None, align=None,
         indent=True, space_before=0, space_after=4, line=1.5, cn=CN_BODY):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = line
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    if indent:
        pf.first_line_indent = Pt(size * 2)
    if align is not None:
        p.alignment = align
    if text:
        r = p.add_run(text)
        set_font(r, cn=cn, size=size, bold=bold, color=color)
    return p


def rich(doc, chunks, size=10.5, indent=True, space_before=0, space_after=4, line=1.5):
    """chunks: [(text, bold, color)]"""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = line
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    if indent:
        pf.first_line_indent = Pt(size * 2)
    for text, bold, color in chunks:
        r = p.add_run(text)
        set_font(r, size=size, bold=bold, color=color)
    return p


def bullet(doc, text, size=10.5, level=0):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = 1.45
    pf.space_after = Pt(2)
    pf.left_indent = Cm(0.75 + 0.6 * level)
    pf.first_line_indent = Cm(-0.35)
    mark = "· " if level == 0 else "– "
    r = p.add_run(mark)
    set_font(r, size=size, color=BLUE, bold=True)
    r2 = p.add_run(text)
    set_font(r2, size=size)
    return p


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_font(r, cn=CN_HEAD, size=9, bold=True, color=GRAY)


def table(doc, headers, rows, widths, font_size=9, header_size=9, zebra=True):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, w in enumerate(widths):
        t.columns[i].width = Cm(w)

    hdr = t.rows[0]
    trPr = hdr._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    trPr.append(th)

    for i, h in enumerate(headers):
        c = hdr.cells[i]
        c.width = Cm(widths[i])
        shade_cell(c, HEADER_BG)
        set_cell_margins(c)
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.15
        r = p.add_run(h)
        set_font(r, cn=CN_HEAD, en=EN_HEAD, size=header_size, bold=True, color="FFFFFF")

    for idx, row in enumerate(rows):
        new_row = t.add_row()
        trPr2 = new_row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        trPr2.append(cs)
        cells = new_row.cells
        for i, val in enumerate(row):
            c = cells[i]
            c.width = Cm(widths[i])
            set_cell_margins(c)
            if zebra and idx % 2 == 1:
                shade_cell(c, "F2F5FA")
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in (0,) or len(str(val)) <= 6 else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.2
            r = p.add_run(str(val))
            set_font(r, size=font_size)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def h1(doc, text):
    p = doc.add_paragraph(style="Heading 1")
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_font(r, cn=CN_HEAD, en=EN_HEAD, size=16, bold=True, color=NAVY)


def h2(doc, text):
    p = doc.add_paragraph(style="Heading 2")
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_font(r, cn=CN_HEAD, en=EN_HEAD, size=12.5, bold=True, color=BLUE)


def add_page_number(paragraph):
    run = paragraph.add_run()
    f1 = OxmlElement("w:fldChar")
    f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = " PAGE "
    f2 = OxmlElement("w:fldChar")
    f2.set(qn("w:fldCharType"), "end")
    run._r.append(f1)
    run._r.append(it)
    run._r.append(f2)
    set_font(run, size=9, color=GRAY)


# ---------- 文档 ----------
doc = Document()

# 页面：A4
sec = doc.sections[0]
sec.page_width = Cm(21.0)
sec.page_height = Cm(29.7)
sec.top_margin = Cm(2.4)
sec.bottom_margin = Cm(2.2)
sec.left_margin = Cm(2.8)
sec.right_margin = Cm(2.8)

# Normal 样式
normal = doc.styles["Normal"]
normal.font.name = EN_BODY
normal.font.size = Pt(10.5)
normal.element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), CN_BODY)
normal.paragraph_format.line_spacing = 1.5
normal.paragraph_format.space_after = Pt(4)

# 页眉
hp = sec.header.paragraphs[0]
hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
hr = hp.add_run("防汛监测预警智能体平台 · 项目说明与团队分工")
set_font(hr, cn=CN_HEAD, size=8.5, color="8C8C8C")

# 页脚留空（封面与目录不编页码）
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER

# ===== 封面 =====
for _ in range(3):
    doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("软件工程项目")
set_font(r, cn=CN_HEAD, en=EN_HEAD, size=13, bold=False, color=BLUE)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(6)
r = p.add_run("防汛监测预警智能体平台")
set_font(r, cn=CN_HEAD, en=EN_HEAD, size=30, bold=True, color=NAVY)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("项 目 说 明 与 团 队 分 工")
set_font(r, cn=CN_HEAD, en=EN_HEAD, size=15, bold=False, color=GRAY)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(4)
r = p.add_run("FloodSentinel · 城市内涝与中小流域防汛值班辅助系统")
set_font(r, size=10, color="8C8C8C")

for _ in range(4):
    doc.add_paragraph()

# 封面信息表
info = doc.add_table(rows=4, cols=2)
info.alignment = WD_TABLE_ALIGNMENT.CENTER
info.autofit = False
info_data = [
    ("项目成员", "王明杰（队长）　黄锰猛　李宇露　胡子妍"),
    ("项目类型", "软件工程课程设计 · 4 人团队 · 12 周"),
    ("文档版本", "V1.0（降难度版）"),
    ("编写日期", "2026 年 11 月"),
]
for i, (k, v) in enumerate(info_data):
    c0, c1 = info.rows[i].cells
    c0.width = Cm(3.2)
    c1.width = Cm(9.0)
    for c in (c0, c1):
        set_cell_margins(c, 90, 90, 120, 120)
    p0 = c0.paragraphs[0]
    p0.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r0 = p0.add_run(k)
    set_font(r0, cn=CN_HEAD, size=10, bold=True, color=GRAY)
    p1 = c1.paragraphs[0]
    r1 = p1.add_run(v)
    set_font(r1, size=10, color="262626")

doc.add_page_break()

# ===== 目录 =====
h1(doc, "目　录")
toc_items = [
    ("一、项目概述", "1"),
    ("二、系统功能", "2"),
    ("三、技术方案（降难度版）", "3"),
    ("四、团队分工", "6"),
    ("五、进度计划（12 周）", "8"),
    ("六、协作规范", "9"),
    ("七、风险与应对", "9"),
    ("八、交付物清单", "10"),
    ("附录：接口清单", "10"),
]
for name, page in toc_items:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.left_indent = Cm(0.4)
    # 制表位 + 点线
    pPr = p._p.get_or_add_pPr()
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "right")
    tab.set(qn("w:leader"), "dot")
    tab.set(qn("w:pos"), "8700")
    tabs.append(tab)
    pPr.append(tabs)
    r = p.add_run(name)
    set_font(r, size=11)
    r2 = p.add_run("\t" + page)
    set_font(r2, size=10, color=GRAY)

# 正文另起一节，页码从 1 开始
body_sec = doc.add_section(WD_SECTION.NEW_PAGE)
body_sec.footer.is_linked_to_previous = False
bfp = body_sec.footer.paragraphs[0]
bfp.alignment = WD_ALIGN_PARAGRAPH.CENTER
add_page_number(bfp)
_sectPr = body_sec._sectPr
_pgNum = OxmlElement("w:pgNumType")
_pgNum.set(qn("w:start"), "1")
_sectPr.insert_element_before(
    _pgNum,
    "w:cols", "w:formProt", "w:vAlign", "w:noEndnote", "w:titlePg",
    "w:textDirection", "w:bidi", "w:rtlGutter", "w:docGrid",
    "w:printerSettings", "w:sectPrChange",
)

# ===== 一、项目概述 =====
h1(doc, "一、项目概述")

h2(doc, "1.1 项目定位")
para(doc, "项目名称：汛哨（FloodSentinel）—— 城市内涝与中小流域防汛监测预警智能体平台。")
rich(doc, [("一句话说明：", True, NAVY),
           ("把「雨量、水位数据 → 风险研判 → 分级预警 → 值班简报 → 消息推送 → 大屏展示」做成一条能跑通、"
            "能演示、能复盘的完整链路。", False, None)])
para(doc, "服务对象是区县、街道一级的防汛值班室。它不是水文预报系统，也不是生产级应急指挥平台，"
          "而是一个帮值班员「看得全、判得快、写得省、说得清」的辅助工具。")

h2(doc, "1.2 要解决的问题")
problems = [
    ("数据散", "雨量站、水位站、积水点的数据分散在不同系统，值班员要开好几个页面来回看。"),
    ("研判靠经验", "什么时候该发预警、发到几级，基本依赖老同志的经验判断，新人接不上手。"),
    ("报告靠手写", "每场降雨都要手写值班简报，格式不统一，一次要花半小时以上。"),
    ("复盘说不清", "事后追责时说不清「当时为什么没预警、发了没有、几点发的」。"),
]
for k, v in problems:
    rich(doc, [(f"· {k}：", True, BLUE), (v, False, None)], indent=False, space_after=2)

h2(doc, "1.3 目标用户")
para(doc, "主要用户：区县防汛值班员（会用电脑、不懂 AI 的普通工作人员），系统必须做到「打开就能用、"
          "按钮不超过三下」；次要用户：街道与乡镇应急联系人，只接收预警推送；管理用户：防汛办负责人，"
          "关注统计数据和事后复盘。")

h2(doc, "1.4 项目边界")
rich(doc, [("本项目要做的事（4 条）：", True, NAVY)], indent=False)
for t in ["生成并接入雨量、水位、积水三类观测数据；",
          "按阈值规则自动研判并生成蓝、黄、橙、红四级预警；",
          "调用大模型生成结构化值班简报（结论、依据、建议）；",
          "提供防汛大屏、告警处置台、场景回放三个界面。"]:
    bullet(doc, t)

rich(doc, [("本项目明确不做的事（5 条）：", True, "C00000")], indent=False)
for t in ["不做 7 天洪水预报，不做水文模型率定；",
          "不对接真实气象、水文生产系统（统一使用模拟数据）；",
          "不做泵站、闸门的远程控制，只输出处置建议；",
          "不做多租户、不做移动端 App、不做小程序；",
          "不做摄像头视频的 AI 识别。"]:
    bullet(doc, t)
para(doc, "把「不做什么」写清楚，既是为了控制 12 周的工作量，也是答辩时的重要加分项——"
          "评委更认可边界清晰的项目。", size=9.5, color=GRAY)

# ===== 二、系统功能 =====
h1(doc, "二、系统功能")

h2(doc, "2.1 核心业务链路")
para(doc, "整个系统只有一条主线，所有功能都为这条线服务：")
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(4)
p.paragraph_format.space_after = Pt(8)
r = p.add_run("模拟数据　→　数据入库　→　规则研判　→　分级告警　→　人工确认　→　生成简报　→　推送与大屏")
set_font(r, cn=CN_HEAD, size=10, bold=True, color=NAVY)

h2(doc, "2.2 功能清单")
caption(doc, "表 1　功能清单与责任分工")
table(doc,
      ["编号", "功能", "说明", "优先级", "负责人"],
      [
          ["F1", "数据模拟器", "按降雨—产流—水位关系生成可复现的观测数据，支持注入异常", "P0", "黄锰猛"],
          ["F2", "站点与观测查询", "站点列表、最新值、历史时序数据查询", "P0", "王明杰"],
          ["F3", "阈值规则研判", "按配置的阈值表判断是否触发预警及等级", "P0", "王明杰"],
          ["F4", "分级告警与流转", "生成告警、人工确认、关闭、超时自动过期", "P0", "王明杰"],
          ["F5", "值班简报生成", "调用大模型输出结论、依据、建议三段式简报", "P0", "李宇露"],
          ["F6", "防汛大屏", "站点分布、实时指标、告警滚动、雨量水位曲线", "P0", "胡子妍"],
          ["F7", "告警处置台", "告警列表、详情、一键确认与关闭", "P0", "胡子妍"],
          ["F8", "场景回放", "按时间轴重演一次降雨过程，输出预警时点", "P0", "黄锰猛 / 胡子妍"],
          ["F9", "消息推送", "把告警卡片推送到飞书或钉钉群", "P1", "李宇露"],
          ["F10", "预案知识检索", "关键词检索防汛预案，为简报提供依据并附页码", "P1", "李宇露"],
          ["F11", "值班问答", "单轮自然语言提问，如「现在哪个站最危险」", "P1", "李宇露"],
          ["F12", "统计与复盘", "告警数量、等级分布、平均响应时长", "P2", "黄锰猛"],
      ],
      widths=[1.3, 3.2, 6.4, 1.5, 2.6], font_size=8.5, header_size=9)
para(doc, "优先级说明：P0 为必须完成，P1 为有余力再做，P2 为可选加分项。若进度落后，"
          "按 P2 → P1 的顺序砍功能，P0 一项都不能少。", size=9.5, color=GRAY)

h2(doc, "2.3 三个演示场景")
para(doc, "验收和答辩只演示这三个场景，所有功能都为它们服务。")
scenes = [
    ("场景一：日常值班（约 30 秒）",
     "值班员问「现在全区雨情怎么样」，系统汇总各站 1 小时、3 小时、24 小时雨量，列出超警站点，"
     "输出一段 200 字以内的值班简报。"),
    ("场景二：暴雨升级（约 90 秒，核心场景）",
     "回放一段强降雨，某站 1 小时雨量达到 52 毫米，规则引擎判定为橙色预警并生成告警；"
     "系统调用大模型生成研判简报，等待值班员点击「确认」后，推送到工作群，大屏对应站点变为橙色。"),
    ("场景三：事后复盘（约 60 秒）",
     "选择一个历史场景回放，系统在时间轴上标出「第 47 分钟发出橙色预警」，"
     "与实际积水发生时间对比，给出预警提前量。"),
]
for title, body in scenes:
    rich(doc, [(title, True, BLUE)], indent=False, space_after=2)
    para(doc, body, size=10)

# ===== 三、技术方案 =====
h1(doc, "三、技术方案（降难度版）")

para(doc, "本章的技术选型以「四个人、十二周、无 GPU、能离线演示」为前提，"
          "刻意避开了分布式、中间件、向量数据库等重型方案。凡是能用一百行代码解决的，就不引入一个框架。")

h2(doc, "3.1 总体架构")
para(doc, "系统分为四层，层与层之间只通过接口通信：")
for name, desc in [
    ("数据层", "SQLite 数据库（开发期单文件，部署时可换 PostgreSQL），存放站点、观测、告警、简报、场景五类数据。"),
    ("服务层", "FastAPI 提供 REST 接口，负责查询、研判、告警流转与操作日志。"),
    ("智能层", "固定三段流水线：取数 → 规则研判 → 大模型生成简报。不引入复杂的多智能体编排框架。"),
    ("展示层", "Vue3 单页应用，包含防汛大屏、告警处置台、场景回放三个页面，轮询刷新。"),
]:
    rich(doc, [(f"{name}：", True, NAVY), (desc, False, None)], indent=False, space_after=3)

h2(doc, "3.2 技术选型与降难度对照")
caption(doc, "表 2　技术选型对照表（右两列为相对完整方案所做的简化）")
table(doc,
      ["模块", "本项目采用", "完整方案", "简化的理由"],
      [
          ["后端框架", "FastAPI", "FastAPI", "轻量、自带接口文档，改动最少"],
          ["数据库", "SQLite（可换 PostgreSQL）", "PostgreSQL + TimescaleDB", "免安装、单文件，百万级数据完全够用"],
          ["前端", "Vue3 + Element Plus + ECharts", "React + Ant Design", "模板多、上手快，队员更熟悉"],
          ["实时刷新", "轮询（每 5 秒）", "WebSocket 长连接", "省掉连接管理与重连逻辑，代码量减半"],
          ["后台任务", "Python 线程 + 定时器", "Redis + Celery", "不引入消息中间件，少一个部署组件"],
          ["规则引擎", "配置表 + 判断函数", "YAML DSL + 语法树求值", "规则不超过 10 条，不值得做 DSL"],
          ["告警状态", "状态字段 + 校验函数", "表驱动状态机", "只有 4 个状态，够用即可"],
          ["智能体", "固定三段流水线", "多步编排 + 检查点续跑", "单轮流程已能完整演示，稳定性更高"],
          ["知识检索", "关键词匹配 + 片段拼接", "向量库 RAG + 重排", "免去 embedding 服务，效果够用"],
          ["地图", "自绘 SVG 示意图", "Leaflet 在线地图", "断网可用、零依赖，演示不会白屏"],
          ["权限", "固定演示账号", "JWT + 角色权限", "课堂演示场景不需要完整权限体系"],
          ["部署", "本机一键启动脚本", "Docker Compose", "少一层环境问题，答辩现场更可靠"],
      ],
      widths=[2.2, 4.2, 3.9, 5.7], font_size=8.5, header_size=9)

h2(doc, "3.3 数据模型")
caption(doc, "表 3　核心数据表")
table(doc,
      ["表名", "作用", "主要字段"],
      [
          ["station", "站点档案", "编号、名称、类型、经纬度、警戒水位、保证水位"],
          ["observation", "观测数据", "站点、时间、指标名、数值、单位、数据质量标记"],
          ["alert", "告警记录", "站点、等级、状态、触发依据、去重键、确认人、确认时间"],
          ["report", "值班简报", "关联告警、正文、引用来源、生成模型、耗时、是否降级"],
          ["scenario", "回放场景", "名称、时长、注入脚本、期望结果"],
      ],
      widths=[3.2, 4.0, 8.8], font_size=9)

h2(doc, "3.4 关键设计")
rich(doc, [("（1）预警等级与判据", True, NAVY)], indent=False, space_after=2)
para(doc, "下表数值为示例值，代码中必须写成可配置项，并在文档中标注「需按当地防汛预案校准」。", size=9.5, color=GRAY)
caption(doc, "表 4　预警等级判据（示例值）")
table(doc,
      ["等级", "雨量判据", "水位判据", "积水判据"],
      [
          ["蓝色（Ⅳ级）", "24 小时 ≥ 50 mm", "达到警戒水位", "积水深度 ≥ 15 cm"],
          ["黄色（Ⅲ级）", "3 小时 ≥ 50 mm 或 1 小时 ≥ 25 mm", "超警戒 0.2 m 且 1 小时涨速 ≥ 0.1 m", "积水深度 ≥ 30 cm"],
          ["橙色（Ⅱ级）", "1 小时 ≥ 50 mm 或 3 小时 ≥ 80 mm", "达到保证水位", "积水深度 ≥ 50 cm"],
          ["红色（Ⅰ级）", "1 小时 ≥ 80 mm 或 3 小时 ≥ 120 mm", "超过历史最高水位", "积水深度 ≥ 80 cm 且持续上涨"],
      ],
      widths=[2.6, 4.6, 4.4, 4.4], font_size=8.5)
para(doc, "同一站点命中多条规则时，取最高等级合并为一条告警，但保留全部触发依据——"
          "这是「可追责」的落点，也是答辩时最能体现设计思考的地方。")

rich(doc, [("（2）告警状态流转", True, NAVY)], indent=False, space_before=6, space_after=2)
para(doc, "告警只有四个状态：待确认 → 已确认 → 已关闭，以及超时未处理的已过期。"
          "人工确认是强制环节，大模型无权自动确认、更无权自动推送——这一条既是安全设计，也是答辩亮点。")

rich(doc, [("（3）防止大模型胡说的三条措施", True, NAVY)], indent=False, space_before=6, space_after=2)
for t in ["简报中的数值、站点名、阈值只能来自数据库查询结果，提示词中明确禁止编造；",
          "要求模型输出严格的 JSON 结构（结论、依据、建议、引用），解析失败则重试，两次失败改用固定模板；",
          "简报末尾必须列出数据来源与预案页码，没有来源的内容一律不写。"]:
    bullet(doc, t)

# ===== 四、团队分工 =====
doc.add_page_break()
h1(doc, "四、团队分工")

para(doc, "四人按「层」分工而不是按「功能」分工。按功能分，两个人会同时改数据库、同时改页面，"
          "一周要吵三次；按层分，每个人只改自己的目录，靠接口约定协作，才能真正并行。")

h2(doc, "4.1 分工总览")
caption(doc, "表 5　团队分工总览")
table(doc,
      ["姓名", "角色", "负责模块", "主要交付物", "工作量"],
      [
          ["王明杰", "队长 / 后端", "接口、数据库、规则引擎、告警流转、部署", "后端源码、数据库脚本、接口文档、部署说明", "约 30%"],
          ["黄锰猛", "数据与算法", "数据模拟器、数据质检、回放场景、评测", "模拟器、场景库、评测报告、数据集说明", "约 24%"],
          ["李宇露", "智能体与知识", "大模型接入、简报生成、知识检索、消息推送", "简报服务、提示词库、知识库、简报样例", "约 23%"],
          ["胡子妍", "前端与可视化", "防汛大屏、告警处置台、场景回放、演示材料", "前端应用、演示视频、使用手册", "约 23%"],
      ],
      widths=[1.9, 2.6, 4.6, 5.2, 1.7], font_size=8.5)

h2(doc, "4.2 王明杰（队长 · 后端与集成）")
rich(doc, [("职责一句话：", True, NAVY), ("把四个人做的东西接成一条能跑的线，并对最终交付负责。", False, None)],
     indent=False, space_after=3)
rich(doc, [("具体任务：", True, NAVY)], indent=False, space_after=2)
for t in ["第 1 周：确定 8 个接口的清单与字段，建仓库、建数据库表；",
          "第 2—3 周：完成站点、观测查询接口，打通数据导入；",
          "第 4—5 周：实现阈值规则研判与告警生成；",
          "第 6 周：完成告警确认、关闭接口与操作日志；",
          "第 7—8 周：全链路联调、异常处理、性能检查；",
          "第 9—10 周：编写一键启动脚本与部署说明；",
          "全程：每周五组织集成验收、跟踪进度、主讲答辩技术部分。"]:
    bullet(doc, t)
rich(doc, [("交付物：", True, NAVY), ("backend/ 全部源码、数据库初始化脚本、接口文档、部署说明。", False, None)],
     indent=False, space_before=4)
rich(doc, [("协作关系：", True, NAVY),
           ("向黄锰猛确认数据格式；向李宇露确认简报返回字段；向胡子妍提供稳定可用的接口。", False, None)],
     indent=False)

h2(doc, "4.3 黄锰猛（数据与算法）")
rich(doc, [("职责一句话：", True, NAVY), ("造出「像真的」的数据，并用评测证明系统判得准。", False, None)],
     indent=False, space_after=3)
rich(doc, [("具体任务：", True, NAVY)], indent=False, space_after=2)
for t in ["第 1—2 周：数据模拟器 v1，按「降雨—产流—水位」三层关系生成数据；",
          "第 3 周：加入异常数据注入（传感器卡死、数值跳变、数据缺失）；",
          "第 4 周：实现数据质检，标记可疑数据；",
          "第 5—6 周：编写 20 个回放场景（正常、暴雨、故障、阈值边界）；",
          "第 7—8 周：编写评测脚本，统计命中率、误报率、预警提前量；",
          "第 9—10 周：提供统计接口数据与复盘报表。"]:
    bullet(doc, t)
rich(doc, [("交付物：", True, NAVY),
           ("simulator.py、scenarios/ 场景库、评测报告、数据集说明文档。", False, None)],
     indent=False, space_before=4)
rich(doc, [("注意事项：", True, "C00000"),
           ("必须保证同一个随机种子生成完全相同的数据，否则回放和评测都无法复现。", False, None)],
     indent=False)

h2(doc, "4.4 李宇露（智能体与知识）")
rich(doc, [("职责一句话：", True, NAVY), ("让系统「会说人话」，但绝不说假话。", False, None)],
     indent=False, space_after=3)
rich(doc, [("具体任务：", True, NAVY)], indent=False, space_after=2)
for t in ["第 1—2 周：封装大模型调用（超时、重试、无网络时降级）；",
          "第 3—4 周：编写简报提示词第一版，输出结论、依据、建议三段；",
          "第 5 周：实现固定模板降级方案，断网也能出简报；",
          "第 6—7 周：建立预案知识库，实现关键词检索并附页码引用；",
          "第 8 周：对接飞书或钉钉群机器人，推送告警卡片；",
          "第 9 周：实现单轮值班问答；第 10 周：人工抽查 20 条简报质量。"]:
    bullet(doc, t)
rich(doc, [("交付物：", True, NAVY),
           ("agent/ 源码、提示词库、知识库文件、20 条简报样例及抽查记录。", False, None)],
     indent=False, space_before=4)
rich(doc, [("注意事项：", True, "C00000"),
           ("每条简报必须能指出数据来源；抽查中发现编造数值的，一律重写提示词。", False, None)],
     indent=False)

h2(doc, "4.5 胡子妍（前端与可视化）")
rich(doc, [("职责一句话：", True, NAVY), ("让评委在三秒内看懂系统在做什么。", False, None)],
     indent=False, space_after=3)
rich(doc, [("具体任务：", True, NAVY)], indent=False, space_after=2)
for t in ["第 1—2 周：搭建前端工程，完成大屏静态页与自绘 SVG 流域示意图；",
          "第 3—4 周：站点列表、雨量水位曲线（ECharts）；",
          "第 5—6 周：告警处置台，列表、详情、确认按钮；",
          "第 7 周：场景回放页，时间轴播放；",
          "第 8 周：轮询刷新、空数据与错误提示；",
          "第 9 周：演示模式（一键播放完整剧情）；第 10—11 周：演示视频与使用手册。"]:
    bullet(doc, t)
rich(doc, [("交付物：", True, NAVY),
           ("frontend/ 源码、演示视频、界面截图、使用手册。", False, None)],
     indent=False, space_before=4)
rich(doc, [("注意事项：", True, "C00000"),
           ("任何页面都必须有「加载中、无数据、出错」三种状态；演示必须能在断网情况下完成。", False, None)],
     indent=False)

# ===== 五、进度 =====
h1(doc, "五、进度计划（12 周）")
para(doc, "按 12 周编排，第 6 周设中期检查，第 12 周答辩。每周五晚固定集成，失败当周补齐。")
caption(doc, "表 6　12 周任务分解")
table(doc,
      ["周次", "阶段目标", "王明杰", "黄锰猛", "李宇露", "胡子妍"],
      [
          ["第 1 周", "立项", "接口清单、建库", "模拟器 v0", "大模型接入", "工程搭建、线框"],
          ["第 2 周", "骨架", "站点观测接口", "数据入库", "提示词 v1", "大屏静态页、SVG"],
          ["第 3 周", "打通", "规则引擎", "多站点、故障注入", "简报生成", "站点页、曲线图"],
          ["第 4 周", "闭环", "告警流转、确认", "数据质检", "结构校验、重试", "告警处置台"],
          ["第 5 周", "稳定", "联调、修缺陷", "20 个场景", "模板降级", "联调、演示页"],
          ["第 6 周", "中期检查", "全链路演示", "场景跑批", "简报样例", "演示脚本"],
          ["第 7 周", "增强", "操作日志", "评测脚本", "知识检索", "回放页"],
          ["第 8 周", "增强", "启动脚本、部署", "指标统计", "消息推送", "轮询、三态"],
          ["第 9 周", "完善", "性能与异常", "统计接口", "单轮问答", "演示模式"],
          ["第 10 周", "联调", "全量走查", "评测报告", "质量抽查", "端到端走查"],
          ["第 11 周", "文档", "部署文档", "数据说明", "技术文档", "使用手册、视频"],
          ["第 12 周", "答辩", "技术主讲", "数据答疑", "演示配合", "现场操作"],
      ],
      widths=[1.5, 2.2, 3.0, 3.0, 2.8, 2.7], font_size=8.5, header_size=8.5)
rich(doc, [("关键节点：", True, NAVY)], indent=False, space_after=2)
for t in ["第 4 周末：全链路必须能跑通一次（数据→告警→简报→大屏），这是项目的生死线；",
          "第 6 周末：中期检查，必须能完整演示场景二；",
          "第 10 周末：功能冻结，之后只修缺陷不加功能；",
          "第 12 周：答辩，8 分钟讲解加 3 分钟现场演示。"]:
    bullet(doc, t)

# ===== 六、协作规范 =====
h1(doc, "六、协作规范")
rules = [
    ("接口先行", "任何人在写代码前，先确认接口字段。接口清单由王明杰维护，改动必须在群里说明并同步所有人。"),
    ("分支管理", "主分支 main 只接受合并请求，不允许直接推送；每人使用 feat/姓名-功能 形式的分支。"),
    ("每周集成", "每周五 20:00 全员到齐，把各自分支合并、跑一遍完整流程，谁弄坏谁当场修，不许过夜。"),
    ("任务看板", "所有任务登记在看板上，分为待办、进行中、待验收、已完成四列，每人每周至少移动三次。"),
    ("文档同步", "接口、数据库字段、提示词发生变更时，当天更新文档，不允许「先做后补」。"),
    ("使用 AI 的纪律", "可以用 AI 写代码，但必须自己跑通、能讲清每一行；涉及数据库修改和公式计算的代码必须人工核对。"),
]
for k, v in rules:
    rich(doc, [(f"· {k}：", True, BLUE), (v, False, None)], indent=False, space_after=3)

# ===== 七、风险 =====
h1(doc, "七、风险与应对")
caption(doc, "表 7　主要风险及应对措施")
table(doc,
      ["风险", "影响", "应对措施", "负责人"],
      [
          ["模拟数据被质疑不真实", "高", "在文档中说明生成方法，附数据分布校验图，坦承是合成数据", "黄锰猛"],
          ["大模型接口限流或断网", "高", "准备固定模板降级方案，另存一份演示录屏", "李宇露"],
          ["进度落后两周以上", "高", "按 P2、P1 顺序砍功能，优先保住场景二主线", "王明杰"],
          ["接口频繁变动导致返工", "中", "接口第 1 周冻结，变更必须全员知会", "王明杰"],
          ["演示现场网络或环境故障", "中", "全流程本地运行，准备离线快照与预录视频", "胡子妍"],
      ],
      widths=[4.6, 1.6, 7.4, 1.9], font_size=9)

# ===== 八、交付物 =====
h1(doc, "八、交付物清单")
caption(doc, "表 8　最终交付物")
table(doc,
      ["序号", "交付物", "说明"],
      [
          ["1", "源代码", "后端、前端、智能体、数据模拟器四部分，含注释"],
          ["2", "数据库脚本", "建表脚本与初始化数据"],
          ["3", "接口文档", "自动生成的接口说明，可直接在线调试"],
          ["4", "数据集与场景库", "模拟数据文件、20 个回放场景"],
          ["5", "评测报告", "命中率、误报率、预警提前量的统计结果"],
          ["6", "部署与使用说明", "一键启动步骤、常见问题"],
          ["7", "演示视频", "三个场景的完整演示，5 分钟以内"],
          ["8", "答辩材料", "演示文稿与讲稿"],
      ],
      widths=[1.4, 4.4, 9.6], font_size=9)

# ===== 附录 =====
h1(doc, "附录：接口清单")
para(doc, "共 8 个接口，第 1 周冻结，后续只增不改。", size=9.5, color=GRAY)
caption(doc, "表 9　接口清单")
table(doc,
      ["序号", "方法", "路径", "说明"],
      [
          ["1", "GET", "/api/stations", "站点列表，支持按流域、类型筛选"],
          ["2", "GET", "/api/stations/{id}/observations", "站点历史时序数据"],
          ["3", "GET", "/api/observations/latest", "多站点最新观测值"],
          ["4", "GET", "/api/alerts", "告警列表，支持按状态、等级筛选"],
          ["5", "POST", "/api/alerts/{id}/confirm", "人工确认告警"],
          ["6", "POST", "/api/alerts/{id}/close", "关闭告警"],
          ["7", "POST", "/api/reports/generate", "生成值班简报"],
          ["8", "POST", "/api/scenarios/{id}/replay", "回放指定场景"],
      ],
      widths=[1.4, 1.8, 6.6, 5.6], font_size=9)

doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = p.add_run("—— 全文完 ——")
set_font(r, size=9, color="8C8C8C")

out = r"docs\防汛监测预警智能体平台-项目说明与分工.docx"
doc.save(out)
print("saved:", out)
