from pathlib import Path
from datetime import date

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_ALIGN_VERTICAL, WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "server-frontend.docx"

FONT_BODY = "Microsoft JhengHei"
FONT_MONO = "Cascadia Mono"
NAVY = "17365D"
BLUE = "2F75B5"
LIGHT_BLUE = "DCE6F1"
PALE_BLUE = "EEF4FA"
LIGHT_GRAY = "F2F2F2"
MID_GRAY = "D9E2F3"
DARK = "20252B"
WHITE = "FFFFFF"
RED = "C00000"
GREEN = "2E7D32"


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_border(cell, color="C8D1DC", size="6"):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_borders = tc_pr.first_child_found_in("w:tcBorders")
    if tc_borders is None:
        tc_borders = OxmlElement("w:tcBorders")
        tc_pr.append(tc_borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        element = tc_borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            tc_borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def remove_cell_borders(cell):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_borders = tc_pr.first_child_found_in("w:tcBorders")
    if tc_borders is None:
        tc_borders = OxmlElement("w:tcBorders")
        tc_pr.append(tc_borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement("w:" + edge)
        element.set(qn("w:val"), "nil")
        tc_borders.append(element)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def prevent_row_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    cant_split.set(qn("w:val"), "true")
    tr_pr.append(cant_split)


def set_repeat_heading(paragraph):
    paragraph.paragraph_format.keep_with_next = True
    paragraph.paragraph_format.keep_together = True


def set_run_font(run, name=FONT_BODY, size=None, bold=None, color=None):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)


def add_page_field(paragraph):
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char1)
    run._r.append(instr_text)
    run._r.append(fld_char2)
    set_run_font(run, size=9, color="667085")


def add_hyperlink(paragraph, text, url):
    part = paragraph.part
    relation_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relation_id)
    new_run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), BLUE)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    r_fonts = OxmlElement("w:rFonts")
    r_fonts.set(qn("w:ascii"), FONT_BODY)
    r_fonts.set(qn("w:hAnsi"), FONT_BODY)
    r_fonts.set(qn("w:eastAsia"), FONT_BODY)
    r_pr.extend([r_fonts, color, underline])
    new_run.append(r_pr)
    text_node = OxmlElement("w:t")
    text_node.text = text
    new_run.append(text_node)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


def add_paragraph(doc, text="", style=None, bold_lead=None):
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.line_spacing = 1.15
    if bold_lead and text.startswith(bold_lead):
        lead = p.add_run(bold_lead)
        set_run_font(lead, bold=True)
        body = p.add_run(text[len(bold_lead):])
        set_run_font(body)
    else:
        run = p.add_run(text)
        set_run_font(run)
    return p


def add_bullet(doc, text, level=0):
    style = "List Bullet" if level == 0 else "List Bullet 2"
    p = add_paragraph(doc, text, style=style)
    p.paragraph_format.left_indent = Inches(0.23 + level * 0.2)
    p.paragraph_format.first_line_indent = Inches(-0.16)
    return p


def add_numbered(doc, text):
    return add_paragraph(doc, text, style="List Number")


def add_code(doc, text):
    p = doc.add_paragraph(style="Code Block")
    p.paragraph_format.keep_together = True
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    set_run_font(run, FONT_MONO, 9, color=DARK)
    p_pr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), LIGHT_GRAY)
    p_pr.append(shd)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    set_repeat_heading(p)
    for run in p.runs:
        set_run_font(run, bold=True, color=DARK)
    return p


def add_caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    set_run_font(run, size=9, bold=True, color="5B6573")
    return p


def add_table(doc, headers, rows, widths=None, font_size=9.3):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.style = "Table Grid"
    header_row = table.rows[0]
    set_repeat_table_header(header_row)
    prevent_row_split(header_row)
    for idx, header in enumerate(headers):
        cell = header_row.cells[idx]
        set_cell_shading(cell, NAVY)
        set_cell_border(cell, color="B8C5D3")
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(str(header))
        set_run_font(run, size=font_size, bold=True, color=WHITE)
        if widths:
            cell.width = Inches(widths[idx])
    for row_idx, row_data in enumerate(rows):
        row = table.add_row()
        prevent_row_split(row)
        for idx, value in enumerate(row_data):
            cell = row.cells[idx]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_border(cell, color="C8D1DC")
            if row_idx % 2:
                set_cell_shading(cell, PALE_BLUE)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.05
            run = p.add_run(str(value))
            set_run_font(run, size=font_size, color=DARK)
            if widths:
                cell.width = Inches(widths[idx])
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def add_flow_table(doc, items):
    col_count = len(items) * 2 - 1
    table = doc.add_table(rows=1, cols=col_count)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    row = table.rows[0]
    prevent_row_split(row)
    for idx, item in enumerate(items):
        cell = row.cells[idx * 2]
        set_cell_shading(cell, NAVY if idx in (1, 2) else BLUE)
        set_cell_border(cell, color=NAVY, size="8")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.keep_together = True
        run = p.add_run(item)
        set_run_font(run, size=8.5, bold=True, color=WHITE)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        if idx < len(items) - 1:
            arrow = row.cells[idx * 2 + 1]
            remove_cell_borders(arrow)
            p2 = arrow.paragraphs[0]
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p2.paragraph_format.space_after = Pt(0)
            r2 = p2.add_run("→")
            set_run_font(r2, size=13, bold=True, color=BLUE)
    return table


def configure_document(doc):
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.68)
    section.left_margin = Inches(0.78)
    section.right_margin = Inches(0.72)
    section.header_distance = Inches(0.28)
    section.footer_distance = Inches(0.3)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = FONT_BODY
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_BODY)
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor.from_string(DARK)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.15

    for style_name, size, color, before, after in (
        ("Title", 25, NAVY, 0, 10),
        ("Subtitle", 12.5, "536273", 0, 10),
        ("Heading 1", 16, NAVY, 14, 6),
        ("Heading 2", 12.5, BLUE, 9, 4),
        ("Heading 3", 11, DARK, 7, 3),
    ):
        style = styles[style_name]
        style.font.name = FONT_BODY
        style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_BODY)
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.keep_together = True

    if "Code Block" not in styles:
        code_style = styles.add_style("Code Block", WD_STYLE_TYPE.PARAGRAPH)
    else:
        code_style = styles["Code Block"]
    code_style.font.name = FONT_MONO
    code_style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_BODY)
    code_style.font.size = Pt(9)
    code_style.paragraph_format.left_indent = Inches(0.12)
    code_style.paragraph_format.right_indent = Inches(0.12)
    code_style.paragraph_format.space_before = Pt(4)
    code_style.paragraph_format.space_after = Pt(6)

    for style_name in ("List Bullet", "List Bullet 2", "List Number"):
        style = styles[style_name]
        style.font.name = FONT_BODY
        style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_BODY)
        style.font.size = Pt(10.5)

    settings = doc.settings.element
    theme_lang = settings.find(qn("w:themeFontLang"))
    if theme_lang is None:
        theme_lang = OxmlElement("w:themeFontLang")
        settings.append(theme_lang)
    theme_lang.set(qn("w:val"), "zh-TW")
    theme_lang.set(qn("w:eastAsia"), "zh-TW")

    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = hp.add_run("BlindAssistDevice　Server Frontend 系統技術報告")
    set_run_font(hr, size=8.5, color="667085")

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = fp.add_run("第 ")
    set_run_font(fr, size=9, color="667085")
    add_page_field(fp)
    fr2 = fp.add_run(" 頁")
    set_run_font(fr2, size=9, color="667085")


def build_report():
    doc = Document()
    configure_document(doc)

    # Cover
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(54)

    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = title.add_run("Server Frontend 系統技術報告")
    set_run_font(tr, size=25, bold=True, color=NAVY)

    subtitle = doc.add_paragraph(style="Subtitle")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sr = subtitle.add_run("BlindAssistDevice 統一伺服器 前端儀表板 與人工智慧語音流程")
    set_run_font(sr, size=12.5, color="536273")

    meta = doc.add_table(rows=4, cols=2)
    meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta.autofit = False
    meta_rows = [
        ("文件名稱", "server-frontend"),
        ("報告日期", "2026 年 11 月 12 日"),
        ("程式基準", "Git f1eba51 與目前工作目錄"),
        ("部署環境", "Windows 11 Build 26100　Asia Taipei"),
    ]
    for i, (label, value) in enumerate(meta_rows):
        for j, text in enumerate((label, value)):
            cell = meta.rows[i].cells[j]
            set_cell_border(cell, color="C8D1DC")
            set_cell_shading(cell, LIGHT_BLUE if j == 0 else WHITE)
            cell.width = Inches(1.55 if j == 0 else 4.7)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            r = p.add_run(text)
            set_run_font(r, size=10, bold=(j == 0), color=DARK)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)
    summary_title = doc.add_paragraph()
    summary_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    strun = summary_title.add_run("摘要")
    set_run_font(strun, size=13, bold=True, color=NAVY)
    summary = doc.add_paragraph()
    summary.paragraph_format.left_indent = Inches(0.55)
    summary.paragraph_format.right_indent = Inches(0.55)
    summary.paragraph_format.line_spacing = 1.25
    summary.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    srun = summary.add_run(
        "本系統以單一 Python HTTP 服務整合裝置遙測 影像接收 地點資料 語音辨識 Gemma 3 推論與語音合成，"
        "並由 React 儀表板呈現即時狀態 地圖與攝影機畫面。現行低延遲流程會在模型輸出遇到句號或逗號等標點時立即合成 WAV，"
        "透過分塊 NDJSON 傳至模擬器播放。核心架構已可運作，但正式展示前仍應完成臺灣本地 TTS 切換、真實 Gemma 端到端壓力測試、"
        "存取控制與 OpenStreetMap 公共服務使用政策確認。"
    )
    set_run_font(srun, size=10.5, color=DARK)

    doc.add_page_break()

    add_heading(doc, "目錄", 1)
    for item in (
        "1 系統範圍與主要結論",
        "2 整體架構",
        "3 統一伺服器設計",
        "4 人工智慧與串流語音流程",
        "5 前端儀表板",
        "6 ESP 模擬器與裝置介面",
        "7 API 介面摘要",
        "8 資料與狀態管理",
        "9 技術版本與執行環境",
        "10 測試與驗證結果",
        "11 安全性 隱私與可靠度",
        "12 部署與操作",
        "13 競賽合規與臺灣本地 TTS",
        "14 優先改善建議",
        "15 結論",
        "附錄 主要程式與參考資料",
    ):
        add_paragraph(doc, item)

    add_heading(doc, "1 系統範圍與主要結論", 1)
    add_paragraph(
        doc,
        "本報告涵蓋 BlindAssistDevice 工作目錄中的統一伺服器 人工智慧服務 前端儀表板 ESP 模擬器 共用通訊協定與本機部署環境。"
        "分析結果以目前程式碼與已驗證的執行版本為準。",
    )
    add_bullet(doc, "後端實際使用 Python 標準函式庫 ThreadingHTTPServer 與 HTTP 1.1，FastAPI 與 Uvicorn 雖已安裝但不在目前執行路徑中。")
    add_bullet(doc, "Gemma 3 27B 在伺服器啟動階段預先載入 Ollama，並以 keep alive 保持常駐；正常關閉時才要求卸載。")
    add_bullet(doc, "語音回覆已支援標點級低延遲串流，在句號 逗號 問號 驚嘆號及中英文等價標點處切分。")
    add_bullet(doc, "OpenStreetMap 圖磚與 Nominatim 反向地理編碼由瀏覽器前端直接呼叫，後端目前不代理這兩項服務。")
    add_bullet(doc, "目前 Piper 使用 zh_CN huayan medium；若競賽禁止中國來源或中國資料模型，正式版應改用臺灣本地語音並留下來源證明。")
    add_bullet(doc, "自動化測試已通過 29 項，JavaScript 語法與 Piper 實機合成也已驗證；最新版本尚需補做真實 Gemma 27B 完整串流壓力測試。")

    add_heading(doc, "2 整體架構", 1)
    add_caption(doc, "圖 1 主要請求與回覆流程")
    add_flow_table(doc, ["ESP 裝置或模擬器", "統一伺服器 8787", "Whisper Gemma Piper", "分段音訊播放端"])
    add_paragraph(
        doc,
        "裝置持續上傳 JPEG 影像與遙測資料；使用者按下辨識鍵後，錄音會送至統一伺服器。伺服器完成語音轉文字，"
        "把問題與最新影像交給 Gemma 3，接著逐段合成語音並回傳。另一條前端路徑由瀏覽器每秒取得儀表板狀態，"
        "同時直接連線 OpenStreetMap 與 Nominatim。",
    )
    add_caption(doc, "表 1 子系統責任")
    add_table(
        doc,
        ["子系統", "主要責任", "核心技術"],
        [
            ("Unified Server", "統一 API 生命週期 併發控制 資料與人工智慧協調", "Python 3.14　ThreadingHTTPServer"),
            ("AI Server", "影像接收 Whisper STT Gemma 推論 Piper TTS", "Ollama　faster whisper　Piper"),
            ("Frontend1", "狀態 地圖 地點 攝影機與導航資訊", "React　Vite　Tailwind　Leaflet"),
            ("ESP Simulator", "模擬裝置影像 定位 遙測 錄音與串流播放", "Node.js　Electron 型桌面頁面"),
            ("Backend", "SQLite 資料層與地點 導航 狀態 API", "Python　SQLite"),
            ("SharedProtocol", "裝置 伺服器與前端共用 API 契約", "Markdown　JSON　NDJSON　WAV"),
        ],
        widths=[1.25, 3.5, 1.65],
    )

    add_heading(doc, "3 統一伺服器設計", 1)
    add_heading(doc, "3 1 啟動與關閉生命週期", 2)
    add_numbered(doc, "讀取根目錄環境變數並初始化 SQLite。")
    add_numbered(doc, "建立只允許單一執行個體綁定連接埠的 ExclusiveThreadingHTTPServer。")
    add_numbered(doc, "在正式人工智慧模式下預載 gemma3 27b Whisper 與 Piper；任何必要服務載入失敗時不啟動 HTTP 服務。")
    add_numbered(doc, "進入 serve forever 並接受儀表板 裝置與辨識請求。")
    add_numbered(doc, "收到關閉要求後停止 HTTP 服務，並通知 Ollama 卸載模型。")
    add_code(doc, "python unified_server.py\n# 測試模式\npython unified_server.py --mock-ai")

    add_heading(doc, "3 2 併發與資源保護", 2)
    add_paragraph(
        doc,
        "HTTP 伺服器可為一般狀態 地點與影像請求建立執行緒，但辨識流程使用非阻塞鎖限制同時只處理一個 recognize 請求。"
        "若人工智慧工作正在執行，下一個辨識請求會收到 HTTP 429，以避免 8 GB 顯示記憶體上同時載入或推論造成資源失控。",
    )
    add_heading(doc, "3 3 請求限制與相容性", 2)
    add_paragraph(
        doc,
        "伺服器以 Content Length 執行有上限的請求本文讀取，影像只接受 JPEG。辨識端依 Accept 標頭決定回覆格式。"
        "舊版客戶端仍可取得單一 audio wav；新版客戶端要求 application x ndjson 後即可取得逐段音訊。",
    )

    add_heading(doc, "4 人工智慧與串流語音流程", 1)
    add_caption(doc, "圖 2 語音辨識與回覆管線")
    add_flow_table(doc, ["錄音 WAV", "Whisper 轉文字", "Gemma 3 Token 串流", "標點切分", "Piper WAV 串流"])
    add_heading(doc, "4 1 模型常駐", 2)
    add_paragraph(
        doc,
        "啟動程式呼叫 Ollama 預載 gemma3 27b，並使用 keep alive 為負值維持常駐。這可把首次請求的模型載入時間移到伺服器啟動階段，"
        "避免使用者每次按下辨識鍵才載入模型。Whisper 與 Piper 也以程序內單例方式保留，降低後續請求延遲。",
    )
    add_heading(doc, "4 2 標點級語音串流", 2)
    add_paragraph(
        doc,
        "Gemma 的輸出不等待完整答案，而是持續累積 token。遇到以下任一標點便形成可播放片段：半形句號 逗號 問號 驚嘆號，"
        "以及全形句號 逗號 問號 驚嘆號。每個片段立即交給持續載入的 Piper 產生 WAV。",
    )
    add_code(doc, "Accept: application/x-ndjson, audio/wav\n\n{\"type\":\"audio\",\"index\":1,\"text\":\"前方有人，\",\"contentType\":\"audio/wav\",\"audio\":\"UklGR...\"}\n{\"type\":\"done\",\"sentenceCount\":1}")
    add_paragraph(
        doc,
        "每個 JSON 事件以 HTTP chunked transfer 立即 flush，並設定 no store no transform 與 X Accel Buffering no，"
        "減少代理伺服器或瀏覽器緩衝造成的等待。由於逗號也會切分，實際傳輸單位應稱為語句片段，而非完整句子。",
    )
    add_heading(doc, "4 3 目前 TTS 狀態", 2)
    add_paragraph(
        doc,
        "目前實作為 Piper TTS 1.4.2 與 zh_CN-huayan-medium，模型在啟動時載入並重複使用。此配置完全本機執行，"
        "但語系標記為中國大陸簡體中文，競賽來源規範與語料授權仍需另外確認。臺灣本地語音的建議遷移方案見第 13 節。",
    )

    add_heading(doc, "5 前端儀表板", 1)
    add_heading(doc, "5 1 元件與更新方式", 2)
    add_paragraph(
        doc,
        "Frontend1 是 React 單頁應用程式。Dashboard 每秒呼叫 api status，呈現後端連線 裝置上線 定位 朝向 導航與偵測資訊；"
        "SavedPlaces 管理已儲存地點；CameraPanel 讀取最新影像；MapPanel 顯示 Leaflet 地圖與標記。",
    )
    add_table(
        doc,
        ["前端模組", "功能", "資料來源"],
        [
            ("Dashboard", "集中狀態與錯誤重試", "GET api status　每 1 秒"),
            ("MapPanel", "地圖 定位 標記與導航摘要", "Leaflet　OSM 圖磚　Nominatim"),
            ("CameraPanel", "最新攝影機畫面與偵測結果", "GET api image　status detections"),
            ("SavedPlaces", "顯示與刪除地點", "GET DELETE api places"),
            ("api service", "統一後端請求與反向地理編碼快取", "Fetch API"),
        ],
        widths=[1.35, 2.65, 2.4],
    )
    add_heading(doc, "5 2 OpenStreetMap 呼叫位置", 2)
    add_paragraph(
        doc,
        "OpenStreetMap 相關請求由 frontend 執行。MapPanel 直接下載 OpenStreetMap 圖磚；services api js 直接呼叫 Nominatim reverse，"
        "指定 jsonv2 zoom 18 addressdetails 與 zh TW zh Hant 語言偏好，並以五位小數座標做記憶體快取。後端目前不呼叫 OpenStreetMap。",
    )
    add_paragraph(
        doc,
        "此設計開發簡單且地圖互動直接，但正式部署時瀏覽器 IP 會直接接觸公共服務，快取與速率限制也分散在各客戶端。"
        "若展示人數增加，建議把反向地理編碼改由後端代理並建立共用快取；圖磚仍可由前端載入，但必須保留正確 attribution 並遵守使用政策。",
    )

    add_heading(doc, "6 ESP 模擬器與裝置介面", 1)
    add_paragraph(
        doc,
        "ESP 模擬器用於在沒有實體硬體時重現攝影機 位置 遙測 按鍵錄音與語音播放。它會定期上傳畫面和狀態，"
        "錄音後送至 api recognize，並明確要求 NDJSON 串流。收到 audio 事件後先解碼 Base64 WAV，再放入播放佇列，"
        "前一段播放完立即接續下一段；done 事件只表示伺服器已完成傳輸，不會中斷已排隊音訊。",
    )
    add_bullet(doc, "相容舊版單一 WAV 回覆，便於逐步更新實體 ESP 客戶端。")
    add_bullet(doc, "播放佇列避免多段音訊同時播放與互相覆蓋。")
    add_bullet(doc, "逗號切分可更早開始說話，但片段過短時可能增加 WAV 封裝 Base64 與網路事件的固定成本。")
    add_bullet(doc, "正式 ESP 韌體應採相同事件解析與排隊策略，並處理斷線 重送 與記憶體上限。")

    add_heading(doc, "7 API 介面摘要", 1)
    add_table(
        doc,
        ["方法與路徑", "用途", "主要回覆或行為"],
        [
            ("GET /api/health", "伺服器健康檢查", "服務狀態 AI 模式 攝影機 FPS"),
            ("GET /api/status", "儀表板綜合狀態", "裝置 定位 導航 偵測 地點摘要"),
            ("POST /api/telemetry", "上傳裝置遙測", "儲存最新狀態"),
            ("POST /api/location", "更新目前 GPS", "接受座標與更新時間"),
            ("DELETE /api/location", "清除測試定位", "重設目前位置"),
            ("GET /api/places", "取得已儲存地點", "JSON 陣列"),
            ("POST /api/places", "新增地點", "名稱 地址 緯度 經度"),
            ("DELETE /api/places/{id}", "刪除地點", "刪除結果"),
            ("POST /api/navigation/resolve", "解析目的地與導航狀態", "目的地 距離 ETA 下一指示"),
            ("POST /api/videoframe", "接收最新 JPEG 畫面", "接受結果並更新影像儲存"),
            ("GET /api/image", "提供最新 JPEG 給前端", "image jpeg 且禁止快取"),
            ("POST /api/recognize", "語音辨識與 AI 回覆", "完整 audio wav 或分塊 NDJSON"),
        ],
        widths=[2.05, 1.9, 2.45],
        font_size=8.7,
    )
    add_paragraph(
        doc,
        "介面文件位於 SharedProtocol API md。正式對接前應把事件格式 錯誤碼 最大本文大小與版本欄位固定成可機器驗證的契約，"
        "例如 OpenAPI JSON Schema 或共用型別。",
    )

    add_heading(doc, "8 資料與狀態管理", 1)
    add_table(
        doc,
        ["資料", "位置與生命週期", "用途"],
        [
            ("應用資料", "Backend app.db　SQLite 持久化", "地點與後端狀態"),
            ("最新攝影機畫面", "程序內最新影像儲存　新畫面覆蓋舊畫面", "AI 視覺上下文與前端預覽"),
            ("最新定位與遙測", "後端目前狀態與資料庫資料", "儀表板與導航"),
            ("反向地理編碼快取", "瀏覽器記憶體　依五位小數座標", "減少同一工作階段重複 Nominatim 請求"),
            ("人工智慧模型", "程序記憶體與 GPU 記憶體常駐", "降低每次辨識延遲"),
            ("語音片段", "記憶體中逐段產生與傳送", "低延遲播放"),
        ],
        widths=[1.35, 2.55, 2.5],
    )
    add_paragraph(
        doc,
        "系統偏向保存最新狀態而非完整時間序列，符合即時輔助裝置的低複雜度需求。若未來需要事故追溯或效能分析，"
        "應另外設計具有保存期限與匿名化規則的事件紀錄，不宜直接長期保留原始聲音與影像。",
    )

    add_heading(doc, "9 技術版本與執行環境", 1)
    add_caption(doc, "表 2 伺服器與人工智慧版本")
    add_table(
        doc,
        ["類別", "元件", "版本或模型", "使用狀態"],
        [
            ("作業系統", "Windows 11", "Build 26100", "目前主機"),
            ("執行環境", "Python", "3.14.0", "實際使用"),
            ("HTTP", "ThreadingHTTPServer", "Python 標準函式庫", "實際使用 HTTP 1.1"),
            ("Web 框架", "FastAPI", "0.127.0", "已安裝 未使用"),
            ("ASGI", "Uvicorn", "0.40.0", "已安裝 未使用"),
            ("資料庫", "SQLite", "3.50.4", "實際使用"),
            ("LLM Runtime", "Ollama", "0.17.1", "實際使用"),
            ("LLM", "Gemma 3", "27B", "啟動時預載"),
            ("STT", "faster whisper", "1.2.1", "medium　zh"),
            ("推論引擎", "CTranslate2", "4.6.3", "Whisper 後端"),
            ("TTS", "piper tts", "1.4.2", "zh_CN-huayan-medium"),
            ("音訊推論", "ONNX Runtime", "1.26.0", "Piper 後端"),
            ("深度學習", "PyTorch", "2.9.1+cu128", "CUDA 12.8"),
            ("視覺", "Ultralytics", "8.4.67", "物件偵測"),
            ("影像", "OpenCV Python", "4.13.0.92", "影像處理"),
            ("數值", "NumPy", "2.3.5", "實際使用"),
            ("影像工具", "Pillow", "12.0.0", "實際使用"),
        ],
        widths=[1.0, 1.55, 1.75, 2.1],
        font_size=8.3,
    )
    add_caption(doc, "表 3 前端與地圖版本")
    add_table(
        doc,
        ["元件", "版本", "備註"],
        [
            ("Node.js", "24.11.0", "前端工具鏈"),
            ("npm", "11.6.1", "套件管理"),
            ("React", "19.2.7", "儀表板 UI"),
            ("React DOM", "19.2.7", "瀏覽器渲染"),
            ("Vite", "8.1.0", "開發與建置"),
            ("Tailwind CSS", "4.3.1", "樣式系統"),
            ("Leaflet", "1.9.4", "地圖核心"),
            ("React Leaflet", "5.0.0", "React 地圖整合"),
            ("React Icons", "5.6.0", "圖示"),
            ("OpenStreetMap 圖磚", "公共端點未釘選版本", "frontend 直接呼叫"),
            ("Nominatim", "reverse jsonv2　伺服器版本未釘選", "frontend 直接呼叫"),
        ],
        widths=[1.75, 2.0, 2.65],
        font_size=8.8,
    )
    add_caption(doc, "表 4 硬體與加速")
    add_table(
        doc,
        ["項目", "目前環境"],
        [
            ("GPU", "NVIDIA GeForce RTX 5060 Laptop GPU"),
            ("顯示記憶體", "8,151 MiB"),
            ("NVIDIA Driver", "582.05"),
            ("CUDA Runtime", "PyTorch cu128"),
        ],
        widths=[2.0, 4.4],
    )

    add_heading(doc, "10 測試與驗證結果", 1)
    add_table(
        doc,
        ["驗證項目", "結果", "說明"],
        [
            ("後端完整單元測試", "通過", "29 項測試全部通過"),
            ("NDJSON 串流契約", "通過", "分段 audio 事件與 done 事件由自動化測試覆蓋"),
            ("舊版 WAV 相容性", "通過", "未要求串流時回傳完整 audio wav"),
            ("ESP 模擬器 JavaScript", "通過", "node check 無語法錯誤"),
            ("Piper 實際合成", "通過", "模型暖機後單片段約 0.05 至 0.09 秒"),
            ("Gemma 3 27B 真實端到端", "待補", "最新改版尚未執行完整長答案串流壓力測試"),
            ("實體 ESP 長時間播放", "待補", "需驗證斷線 記憶體與播放佇列"),
        ],
        widths=[1.75, 0.75, 3.9],
        font_size=8.8,
    )
    add_paragraph(
        doc,
        "目前測試足以確認路由 協定與向後相容性，但不能取代真實 GPU 模型 網路狀況與實體裝置的整合測試。"
        "正式展示前應記錄首段音訊延遲 每段合成時間 全答案完成時間 GPU 記憶體峰值與連續 30 分鐘穩定性。",
    )

    add_heading(doc, "11 安全性 隱私與可靠度", 1)
    add_table(
        doc,
        ["風險", "目前狀態", "建議控制"],
        [
            ("未授權存取", "服務預設綁定 0.0.0.0 且未見身份驗證", "限制可信 LAN　加入 API Token　防火牆白名單"),
            ("聲音與影像隱私", "原始錄音與最新畫面進入本機服務", "預設不落盤　明確保存期限　展示前取得同意"),
            ("公共地圖服務", "瀏覽器直接使用 OSM 與 Nominatim", "遵守 attribution 速率與 User Agent 政策　加入後端快取"),
            ("單點故障", "AI 預載失敗則服務不啟動", "健康檢查　啟動記錄　可選降級模式"),
            ("GPU 壓力", "辨識請求一次只允許一個", "保留 429 與客戶端退避　監控 VRAM"),
            ("片段過短", "逗號可產生大量小音訊", "設定最短字數或最大等待時間　量測後調整"),
            ("錯誤恢復", "串流可送 error 事件", "客戶端顯示狀態並清理佇列　支援可控重試"),
        ],
        widths=[1.3, 2.35, 2.75],
        font_size=8.6,
    )

    add_heading(doc, "12 部署與操作", 1)
    add_heading(doc, "12 1 伺服器", 2)
    add_code(doc, "cd F:\\BlindAssistDevice\npython unified_server.py")
    add_paragraph(
        doc,
        "預設監聽 0.0.0.0 8787。正式模式會在開始接受請求前載入 Gemma Whisper 與 Piper，因此啟動時間較長但第一次互動較快。"
        "若只需驗證 UI 或 API，可使用 mock ai 避免載入大型模型。",
    )
    add_heading(doc, "12 2 前端", 2)
    add_code(doc, "cd F:\\BlindAssistDevice\\Frontend1\nnpm install\nnpm run dev\n# 正式建置\nnpm run build")
    add_paragraph(
        doc,
        "VITE_API_URL 可覆寫統一伺服器網址，VITE_GEOCODING_URL 可覆寫 Nominatim reverse 端點。若頁面與後端不在同一主機，"
        "應確認防火牆 CORS 與 HTTPS 混合內容限制。",
    )
    add_heading(doc, "12 3 啟動檢查", 2)
    add_bullet(doc, "Ollama 服務可用且本機已安裝 gemma3 27b。")
    add_bullet(doc, "Whisper medium 與 Piper voice 檔案可讀，GPU 驅動與 CUDA 相容。")
    add_bullet(doc, "8787 連接埠未被其他程序占用，Windows 防火牆僅允許需要的網路範圍。")
    add_bullet(doc, "api health 與 api status 回覆正常，模擬器能上傳一張 JPEG。")
    add_bullet(doc, "串流辨識能在第一個逗號或句號後開始播放，不必等待完整答案。")

    add_heading(doc, "13 競賽合規與臺灣本地 TTS", 1)
    add_paragraph(
        doc,
        "若競賽規定禁止中國開發的人工智慧或中國來源模型，不能只依語言名稱判斷合規，應同時確認開發者 模型來源 訓練資料 授權與是否使用雲端。"
        "目前 Gemma 由 Google 提供，Whisper 由 OpenAI 提供；Piper 引擎為開源本機 TTS，但現用 voice 名稱為 zh_CN-huayan-medium，"
        "其語系與語音資料來源需要主辦單位書面確認。",
    )
    add_heading(doc, "13 1 建議目標語音", 2)
    add_paragraph(
        doc,
        "建議優先評估 Windows 本地語音 Microsoft Hanhan Desktop Chinese Traditional Taiwan。完成 Windows 繁體中文臺灣語言與語音套件下載後，"
        "該語音可透過本機 SAPI 使用，不需要每次連線雲端。它與 Azure zh-TW-HsiaoChenNeural 不同；HsiaoChenNeural 是雲端自然語音名稱，"
        "不是目前 Windows 下載畫面中的本機 Basic voice 模型。",
    )
    add_table(
        doc,
        ["方案", "本機或雲端", "競賽風險", "目前狀態"],
        [
            ("Piper zh_CN huayan medium", "本機", "中國大陸語系與資料來源需確認", "程式正在使用"),
            ("Microsoft Hanhan Desktop zh TW", "本機", "需確認競賽接受 Microsoft 與 Windows 語音授權", "建議遷移 尚未接入程式"),
            ("Azure zh-TW-HsiaoChenNeural", "雲端", "需網路與 Azure 服務　非完全本機", "未使用"),
        ],
        widths=[2.0, 1.0, 2.3, 1.1],
        font_size=8.7,
    )
    add_heading(doc, "13 2 遷移驗收", 2)
    add_numbered(doc, "在 Windows 設定完成繁體中文臺灣語音下載，並於本機語音清單確認 Hanhan token。")
    add_numbered(doc, "在 AiServer speech 建立可替換 TTS adapter，維持輸出 PCM WAV 與既有串流事件不變。")
    add_numbered(doc, "以臺灣地名 數字 方位與道路指示建立發音測試集。")
    add_numbered(doc, "量測第一片段延遲 片段間空隙 音量與實體 ESP 解碼相容性。")
    add_numbered(doc, "保存官方來源 授權條款與主辦單位確認紀錄，避免只以口頭判斷合規。")

    add_heading(doc, "14 優先改善建議", 1)
    add_table(
        doc,
        ["優先級", "工作", "預期成果"],
        [
            ("P0", "切換並驗證臺灣本地 TTS 或取得現行 voice 合規確認", "降低競賽資格風險"),
            ("P0", "執行真實 Gemma 27B 長答案端到端測試", "確認首音延遲 VRAM 與穩定性"),
            ("P0", "限制 8787 存取範圍並加入最小身份驗證", "避免 LAN 未授權呼叫與影像外洩"),
            ("P1", "將 Nominatim 反向地理編碼改為後端代理與共用快取", "集中速率限制 隱私與服務替換"),
            ("P1", "為逗號切分加入最短字數與最大等待時間", "平衡首音速度與片段數量"),
            ("P1", "建立結構化延遲與錯誤監控", "可量化展示品質並快速定位故障"),
            ("P2", "把 API 契約轉為 OpenAPI 或 JSON Schema", "減少 ESP 前端與後端格式漂移"),
            ("P2", "將開發工具與未使用 WebSocket 程式整理隔離", "降低維護與誤解成本"),
        ],
        widths=[0.75, 3.55, 2.1],
        font_size=8.7,
    )

    add_heading(doc, "15 結論", 1)
    add_paragraph(
        doc,
        "BlindAssistDevice 已形成清楚的裝置 統一伺服器 人工智慧與前端分層。這次改版的關鍵成果是將 Gemma 3 27B 的載入移至伺服器啟動階段，"
        "並把模型 token 依句號與逗號等標點轉成可立即播放的語音片段，使使用者不必等待完整答案。ESP 模擬器已跟進新的 NDJSON 播放佇列，"
        "舊版完整 WAV 仍可相容。",
    )
    add_paragraph(
        doc,
        "目前最重要的收尾工作不是增加更多功能，而是完成臺灣本地 TTS 的實際接入與來源證明，補做真實 Gemma 長時間端到端測試，"
        "並把網路存取與公共地圖服務使用方式收斂到可展示 可維護且可稽核的狀態。完成這三項後，整體系統即可更穩定地用於競賽展示。",
    )

    add_heading(doc, "附錄 主要程式與參考資料", 1)
    add_heading(doc, "主要程式位置", 2)
    add_table(
        doc,
        ["檔案", "內容"],
        [
            ("unified_server.py", "統一 HTTP 服務 啟動預載 串流回覆與關閉流程"),
            ("AiServer/Recognize/process.py", "Whisper Gemma 與標點切分管線"),
            ("AiServer/speech/tts.py", "Piper 模型載入與 WAV 產生"),
            ("Frontend1/src/services/api.js", "後端 API 與 Nominatim 反向地理編碼"),
            ("Frontend1/src/components/MapPanel.jsx", "Leaflet 與 OpenStreetMap 圖磚"),
            ("Frontend1/src/pages/Dashboard.jsx", "儀表板輪詢與狀態整合"),
            ("espsimulator/app.js", "錄音 上傳 NDJSON 解碼與播放佇列"),
            ("SharedProtocol/API.md", "裝置與伺服器 API 契約"),
            ("Frontend1/package.json", "前端依賴與建置命令"),
        ],
        widths=[2.65, 3.75],
        font_size=8.8,
    )
    add_heading(doc, "官方參考", 2)
    refs = [
        ("OpenStreetMap 圖磚使用政策", "https://operations.osmfoundation.org/policies/tiles/"),
        ("Nominatim 使用政策", "https://operations.osmfoundation.org/policies/nominatim/"),
        ("Nominatim Reverse API", "https://nominatim.org/release-docs/latest/api/Reverse/"),
        ("Ollama API 文件", "https://docs.ollama.com/api"),
        ("Microsoft Windows 語音設定", "https://support.microsoft.com/windows/use-voice-access-to-control-your-pc-author-text-with-your-voice-4dcd23ee-f1b9-4fd1-bacc-862ab611f55d"),
    ]
    for label, url in refs:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(3)
        add_hyperlink(p, label, url)

    add_paragraph(
        doc,
        "版本與測試結果為 2026 年 11 月 12 日在目前開發主機上取得。公共服務與套件版本會隨時間更新，正式交付時應重新執行版本清單與測試。",
    )

    core = doc.core_properties
    core.title = "Server Frontend 系統技術報告"
    core.subject = "BlindAssistDevice 統一伺服器 前端儀表板 人工智慧語音流程"
    core.author = "OpenAI Codex"
    core.keywords = "BlindAssistDevice, server, frontend, Gemma, Whisper, TTS, OpenStreetMap"
    core.comments = "依目前程式碼與本機驗證結果建立"

    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build_report()
