"""Build the magazine-style hackathon report (Report.docx).

    python make_figures.py   # graphics (needs results/results.json)
    python make_report.py    # -> Report.docx   (needs: pip install python-docx)

Layout: A4 landscape, one designed page per topic, full-bleed cover, big condensed
headings, tag banners, multi-column text, dark sidebars and icon-tile grids.
All numbers are read from results/results.json.
"""
import copy
import json

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT as VA
from docx.enum.text import WD_ALIGN_PARAGRAPH as AL, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls
from docx.shared import Cm, Pt, RGBColor, Emu

from loadshed import theme as T

R = json.load(open("results/results.json", encoding="utf-8"))
INST, BASE = R["instance"], R["baselines"]
CV, ST, ANS, BIG = R["qaoa_cvar"], R["qaoa_standard"], R["qaoa_answer"], R["scaling_15q"]
BEST = max(CV, key=lambda r: r["p_opt"])
RAND = 1 / INST["search_space"]
FIRST_MODE = min(r["p"] for r in CV if r["most_frequent_is_opt"])
HOURS = ["18:00", "19:00", "20:00"]
REPO = "github.com/usmansaeedkhosa2006/qiskit-load-shedding-qaoa"
A = "report_assets"

PAGE_W, PAGE_H = Cm(29.7), Cm(21.0)
MX, MT, MB = Cm(1.8), Cm(1.4), Cm(1.5)
CONTENT_W = 29.7 - 2 * 1.8  # cm


def rgb(h):
    return RGBColor.from_string(h.lstrip("#"))


def pct(x, d=2):
    return f"{100 * x:.{d}f}%"


doc = Document()
st = doc.styles["Normal"]
st.font.name = T.BODY_FONT
st.font.size = Pt(10)
st.font.color.rgb = rgb(T.TEXT)
st.element.rPr.rFonts.set(qn("w:eastAsia"), T.BODY_FONT)
st.paragraph_format.space_after = Pt(5)
st.paragraph_format.line_spacing = 1.08
lb = doc.styles["List Bullet"]
lb.font.name = T.BODY_FONT
lb.font.size = Pt(10)
lb.paragraph_format.space_after = Pt(3)


# =================================================================== low-level helpers
def setup_section(sec, cols=1, space_cm=0.9):
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = PAGE_W, PAGE_H
    sec.left_margin = sec.right_margin = MX
    sec.top_margin, sec.bottom_margin = MT, MB
    sec.footer_distance = Cm(0.7)
    sectPr = sec._sectPr
    c = sectPr.find(qn("w:cols"))
    if c is None:
        c = OxmlElement("w:cols")
        sectPr.append(c)
    c.attrib.clear()
    c.set(qn("w:num"), str(cols))
    c.set(qn("w:space"), str(int(space_cm * 567)))


_first = [True]


def new_page(cols=1):
    if _first[0]:
        _first[0] = False
        sec = doc.sections[0]
    else:
        sec = doc.add_section(WD_SECTION.NEW_PAGE)
    setup_section(sec, cols)
    return sec


def continuous(cols):
    sec = doc.add_section(WD_SECTION.CONTINUOUS)
    setup_section(sec, cols)
    return sec


def run_shade(run, fill):
    rPr = run._r.get_or_add_rPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill.lstrip("#"))
    rPr.append(shd)


def para(text="", size=10, color=T.TEXT, bold=False, font=None, align=None, after=5, before=0,
         italic=False, line=None, container=None):
    p = (container or doc).add_paragraph()
    pf = p.paragraph_format
    pf.space_after, pf.space_before = Pt(after), Pt(before)
    if line:
        pf.line_spacing = line
    if align is not None:
        p.alignment = align
    if text:
        add(p, text, size, color, bold, font, italic)
    return p


def add(p, text, size=10, color=T.TEXT, bold=False, font=None, italic=False):
    r = p.add_run(text)
    r.font.size = Pt(size); r.font.color.rgb = rgb(color); r.bold = bold; r.italic = italic
    if font:
        r.font.name = font
        r._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), font)
    return r


def head(text, size=50, color=T.INK, align=None, after=4, container=None, line=0.88):
    return para(text.upper(), size, color, font=T.HEAD_FONT, align=align, after=after, line=line,
                container=container)


def tag(text, bg=T.AMBER, color=T.INK, size=20, after=2, container=None, align=None):
    p = para(after=after, container=container, align=align)
    r = add(p, f" {text.upper()} ", size, color, font=T.HEAD_FONT)
    run_shade(r, bg)
    return p


def sub(text, size=17, color=T.INK, before=6, container=None):
    return para(text.upper(), size, color, font=T.HEAD_FONT, before=before, after=2, container=container)


def body(text, lead=None, size=11, color=T.TEXT, container=None, after=5, align=None):
    p = para(after=after, container=container, align=align)
    if lead:
        add(p, lead, size, color, bold=True)
    add(p, text, size, color)
    return p


def bullet(text, lead=None, size=10.5, color=T.TEXT, container=None):
    p = (container or doc).add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    if lead:
        add(p, lead, size, color, bold=True)
    add(p, text, size, color)
    return p


def column_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.COLUMN)


def picture(path, width_cm, align=AL.CENTER, after=2, container=None):
    p = para(after=after, align=align, container=container)
    p.add_run().add_picture(path, width=Cm(width_cm))
    return p


def caption(text, container=None, align=AL.CENTER):
    return para(text, 8.5, T.MUTED, italic=True, align=align, after=4, container=container)


def full_bleed(path):
    """Anchored picture behind text, covering the whole page."""
    p = para(after=0)
    inline = p.add_run().add_picture(path, width=PAGE_W, height=PAGE_H)._inline
    anchor = parse_xml(
        f'<wp:anchor {nsdecls("wp", "a", "pic", "r")} distT="0" distB="0" distL="0" distR="0" '
        f'simplePos="0" relativeHeight="0" behindDoc="1" locked="1" layoutInCell="1" allowOverlap="1">'
        f'<wp:simplePos x="0" y="0"/>'
        f'<wp:positionH relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionH>'
        f'<wp:positionV relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionV>'
        f'<wp:extent cx="{int(PAGE_W)}" cy="{int(PAGE_H)}"/>'
        f'<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/>'
        f'<wp:docPr id="{inline.docPr.id}" name="Page art {inline.docPr.id}" descr="decorative page background"/>'
        f'<wp:cNvGraphicFramePr/></wp:anchor>')
    anchor.append(copy.deepcopy(inline.graphic))
    inline.getparent().replace(inline, anchor)
    return p


# ---------- tables
def _tbl_props(tbl, borders=False):
    tblPr = tbl._tbl.tblPr
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    if not borders:
        b = OxmlElement("w:tblBorders")
        for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
            x = OxmlElement(f"w:{e}"); x.set(qn("w:val"), "nil"); b.append(x)
        tblPr.append(b)
    mar = OxmlElement("w:tblCellMar")
    for e, v in (("top", 70), ("left", 140), ("bottom", 70), ("right", 140)):
        x = OxmlElement(f"w:{e}"); x.set(qn("w:w"), str(v)); x.set(qn("w:type"), "dxa"); mar.append(x)
    tblPr.append(mar)


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill.lstrip("#"))
    tcPr.append(shd)


def row_height(row, cm, rule="exact"):
    trPr = row._tr.get_or_add_trPr()
    h = OxmlElement("w:trHeight"); h.set(qn("w:val"), str(int(cm * 567))); h.set(qn("w:hRule"), rule)
    trPr.append(h)


def cell_border(cell, side, color, sz=8):
    tcPr = cell._tc.get_or_add_tcPr()
    b = tcPr.find(qn("w:tcBorders"))
    if b is None:
        b = OxmlElement("w:tcBorders"); tcPr.append(b)
    e = OxmlElement(f"w:{side}"); e.set(qn("w:val"), "single"); e.set(qn("w:sz"), str(sz))
    e.set(qn("w:color"), color.lstrip("#")); b.append(e)


def make_table(rows, cols, widths_cm, borders=False, container=None):
    t = (container or doc).add_table(rows=rows, cols=cols)
    t.autofit = False
    _tbl_props(t, borders)
    for row in t.rows:
        for i, w in enumerate(widths_cm):
            row.cells[i].width = Cm(w)
    grid = t._tbl.tblGrid
    for i, gc in enumerate(grid.findall(qn("w:gridCol"))):
        gc.set(qn("w:w"), str(int(widths_cm[i] * 567)))
    return t


def cell_text(cell, text, size=9, color=T.TEXT, bold=False, font=None, align=None):
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    if align is not None:
        p.alignment = align
    add(p, str(text), size, color, bold, font)
    return p


def data_table(header, rows, widths, size=8.5, container=None, dark=False):
    t = make_table(1 + len(rows), len(header), widths, container=container)
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        shade(c, T.AMBER if dark else T.INK)
        cell_text(c, h.upper(), size + 0.5, T.INK if dark else "FFFFFF", font=T.HEAD_FONT)
    for r, row in enumerate(rows, start=1):
        for i, v in enumerate(row):
            c = t.rows[r].cells[i]
            if dark:
                cell_text(c, v, size, "FFFFFF")
                cell_border(c, "bottom", T.INK2, 6)
            else:
                if r % 2 == 0:
                    shade(c, T.SOFT)
                cell_text(c, v, size, T.TEXT)
    return t


def sidebar(title, width_cm, fill=T.INK, container=None):
    """Dark call-out box; returns the cell to write into."""
    t = make_table(1, 1, [width_cm], container=container)
    c = t.rows[0].cells[0]
    shade(c, fill)
    c.paragraphs[0].paragraph_format.space_after = Pt(4)
    add(c.paragraphs[0], title.upper(), 19, T.AMBER, font=T.HEAD_FONT)
    return c


def tile_grid(items, ncols, dark_h, desc_h, icon_cm=1.5, title_size=15, desc_size=9, gap=0.45,
              number=True, tile_fill=T.INK):
    """Dark icon tiles with a description underneath (the 'enemies' / 'principles' layout)."""
    tw = (CONTENT_W - gap * (ncols - 1)) / ncols
    widths = []
    for i in range(ncols):
        widths.append(tw)
        if i < ncols - 1:
            widths.append(gap)
    nrows = (len(items) + ncols - 1) // ncols
    t = make_table(nrows * 3, len(widths), widths)
    for k, (icon, title, desc) in enumerate(items):
        r0, c0 = (k // ncols) * 3, (k % ncols) * 2
        dark, light = t.rows[r0].cells[c0], t.rows[r0 + 1].cells[c0]
        shade(dark, tile_fill)
        dark.vertical_alignment = VA.TOP
        p = dark.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        if number:
            add(p, f"{k + 1}", 13, T.AMBER, font=T.HEAD_FONT)
        p2 = dark.add_paragraph(); p2.alignment = AL.CENTER
        p2.paragraph_format.space_after = Pt(2)
        p2.add_run().add_picture(f"{A}/icon_{icon}.png", width=Cm(icon_cm))
        p3 = dark.add_paragraph(); p3.paragraph_format.space_after = Pt(0)
        p3.paragraph_format.line_spacing = 0.9
        add(p3, title.upper(), title_size, "FFFFFF", font=T.HEAD_FONT)
        light.vertical_alignment = VA.TOP
        lp = light.paragraphs[0]; lp.paragraph_format.space_after = Pt(0)
        lp.paragraph_format.line_spacing = 1.0
        add(lp, desc, desc_size, T.TEXT)
    for i in range(nrows):
        row_height(t.rows[i * 3], dark_h)
        row_height(t.rows[i * 3 + 1], desc_h)
        row_height(t.rows[i * 3 + 2], 0.25)
    return t


def footer_with_page(sec):
    f = sec.footer
    f.is_linked_to_previous = False
    p = f.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    fld = OxmlElement("w:fldSimple"); fld.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r"); rPr = OxmlElement("w:rPr")
    b = OxmlElement("w:b"); rPr.append(b)
    sz = OxmlElement("w:sz"); sz.set(qn("w:val"), "16"); rPr.append(sz)
    col = OxmlElement("w:color"); col.set(qn("w:val"), T.INK.lstrip("#")); rPr.append(col)
    r.append(rPr); t = OxmlElement("w:t"); t.text = "1"; r.append(t); fld.append(r)
    p._p.append(fld)
    add(p, "     Hackathon Report  ·  Fair Load-Shedding with QAOA", 8, T.MUTED)


def empty_footer(sec):
    sec.footer.is_linked_to_previous = False
    sec.footer.paragraphs[0].text = ""


# =================================================================== PAGE 1 · cover
sec = new_page()
sec.top_margin = Cm(0.8)
empty_footer(sec)
full_bleed(f"{A}/cover.jpg")
para("Team: [team name / members]", 12, "FFFFFF", bold=True, align=AL.RIGHT, before=468, after=0)
para(f"Code: {REPO}", 10, T.AMBER_LIGHT, align=AL.RIGHT, after=0)
para("Video: [Google Drive link]", 10, T.AMBER_LIGHT, align=AL.RIGHT, after=0)

# =================================================================== PAGE 2 · statement
new_page()
full_bleed(f"{A}/statement.jpg")
para("", after=0)

# =================================================================== PAGE 3 · contents
sec = new_page()
footer_with_page(sec)
head("Contents", 66, after=24)
TOC = [("The Challenge: Keeping the Lights On, Fairly", 4), ("Who Does This Help?", 5),
       ("From Grid to Qubits: the Formulation", 6), ("The Four Rules", 7), ("Why QAOA?", 8),
       ("How It Fits Together: Architecture", 9), ("Building It in Qiskit", 10),
       ("Results: Did It Work?", 11), ("More Layers, Better Odds", 12),
       ("What the Quantum Computer Saw", 13), ("The Limits: an Honest Assessment", 14),
       ("What's Next, Reproducing It and Credits", 15)]
for title, pg in TOC:
    p = para(after=9)
    p.paragraph_format.left_indent = Cm(8)
    p.paragraph_format.tab_stops.add_tab_stop(Cm(CONTENT_W - 2), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    add(p, title, 11.5, T.TEXT)
    add(p, f"\t{pg}", 11.5, T.INK, bold=True)

# =================================================================== PAGE 4 · challenge
new_page()
tag("The challenge:", size=22)
head("Keeping the lights on, fairly", 54, after=6)
continuous(3)
body("When generation can't meet demand, a power distribution company (DISCO) such as LESCO or "
     "K-Electric has to shed load: it switches whole feeders off for an hour at a time. "
     "Every evening a control room decides which neighbourhoods go dark, and in what order.",
     size=11.5, color=T.INK).runs[0].bold = True
sub("When supply falls short")
body("Shed too little and grid frequency drops, protection relays trip, and a local shortfall can "
     "become a wide blackout. Shed too much and paying customers lose power for nothing. Cut a "
     "hospital or a water-pumping station and the harm is no longer just inconvenience.")
body("Pakistan's DISCOs already use loss-based load management: feeders with higher losses (theft "
     "and non-payment) get longer outages. That turns a technical problem into a social one.")
column_break()
sub("Why it's hard", before=0)
body("Rotation tables are still largely built by hand from fixed categories. With hundreds of "
     "feeders, a deficit that changes every hour, protected loads, and a fairness expectation "
     "that nobody should be cut twice in a row, the number of possible schedules explodes: "
     "2 to the power (feeders × hours).")
sub("Our idea")
body("Treat each “feeder f is off in hour h” decision as a qubit. Write every goal as an energy "
     "term, so the lowest-energy state of a quantum system is the fairest valid schedule. Then use "
     "QAOA, a hybrid quantum-classical algorithm, to search for it in Qiskit, and check the answer "
     "against an exact solver.")
column_break()
c = sidebar("Our test grid", 7.9)
p = c.add_paragraph(); p.paragraph_format.space_after = Pt(4)
add(p, "Illustrative evening peak, 18:00–20:00", 9, T.AMBER_LIGHT)
fr = [[f["name"], f["kind"].replace("Mixed residential/commercial", "Mixed use"), f"{f['load_mw']:g}", f"{int(f['loss_rate'] * 100)}%" if not f["protected"] else "never cut"]
      for f in INST["feeders"]]
data_table(["Feeder", "Type", "MW", "Loss"], fr, [1.6, 3.3, 1.0, 1.5], size=8.5, container=c, dark=True)
p = c.add_paragraph(); p.paragraph_format.space_before = Pt(6); p.paragraph_format.space_after = Pt(2)
add(p, "Deficit to shed:  ", 9.5, "FFFFFF", bold=True)
add(p, "   ".join(f"{h} → {d} MW" for h, d in zip(HOURS, INST["deficits_mw"])), 9.5, "FFFFFF")
p = c.add_paragraph(); p.paragraph_format.space_after = Pt(2)
add(p, f"{INST['n_qubits']} qubits · {INST['search_space']:,} schedules · only "
       f"{INST['n_valid_schedules']} valid", 9.5, T.AMBER, bold=True)

# =================================================================== PAGE 5 · who
new_page()
head("Who does this help?", 58, T.AMBER, align=AL.CENTER, after=6)
p = para("A fair, automatic rotation table creates value for at least ", 13, align=AL.CENTER, after=10)
add(p, "four groups:", 13, T.INK, bold=True)
picture(f"{A}/bracket.png", CONTENT_W * 0.98, after=0)
WHO = [("bolt", "Grid operators", ["A valid rotation table in seconds, not hours",
                                    "Never under-shed: no frequency collapse",
                                    "Re-plan instantly when the deficit changes"]),
       ("house", "Paying customers", ["Low-loss feeders cut least",
                                      "No needless over-shedding",
                                      "Never two outages back to back"]),
       ("hospital", "Critical services", ["Hospitals and water pumping are never cut",
                                          "Enforced before optimisation, so it cannot fail"]),
       ("scale", "The regulator", ["Rules written as explicit maths",
                                   "Auditable, repeatable, and the same for everyone"])]
cw = CONTENT_W / 4
t = make_table(1, 4, [cw] * 4)
for i, (icon, title, lines) in enumerate(WHO):
    c = t.rows[0].cells[i]
    p = c.paragraphs[0]; p.alignment = AL.CENTER
    p.add_run().add_picture(f"{A}/circle_{icon}.png", width=Cm(3.4))
    p2 = c.add_paragraph(); p2.alignment = AL.CENTER; p2.paragraph_format.space_after = Pt(6)
    add(p2, title.upper(), 26, T.INK, font=T.HEAD_FONT)
    for ln in lines:
        q = c.add_paragraph(); q.alignment = AL.CENTER; q.paragraph_format.space_after = Pt(5)
        add(q, ln, 12.5, T.TEXT)
para("", after=40)
tag("Built for one real situation: the evening peak in a Pakistani distribution company",
    bg=T.INK, color="FFFFFF", size=19, align=AL.CENTER)

# =================================================================== PAGE 6 · formulation
new_page()
head("From grid to qubits", 54, after=4)
tag("How we turned load-shedding into a QUBO", bg=T.AMBER, color="FFFFFF", size=18, after=8)
continuous(3)
sub("Decision variables", before=0)
body("x[f,h] ∈ {0,1} equals 1 when sheddable feeder f is switched off in hour h. With 4 sheddable "
     "feeders × 3 hours that is 12 binary variables, and each one becomes one qubit.")
sub("Protected feeders: zero qubits")
body("The hospital and water-pumping feeder F5 is removed before the quantum step, so x is fixed to "
     "0. A hard rule enforced classically costs no qubits and can never be violated.")
sub("Units")
body("Loads and deficits are expressed in 10 MW blocks, which keeps the penalty coefficients small "
     "and the energy landscape smoother.")
column_break()
sub("The objective", before=0)
ft = make_table(1, 1, [7.9])
fc = ft.rows[0].cells[0]
shade(fc, T.SOFT)
for i, ln in enumerate(["minimise  C(x) =", "   Σ c_f · x[f,h]", " + A · Σ_h (Σ_f L_f·x[f,h] − D_h)²",
                        " + B · Σ_f Σ_h x[f,h] · x[f,h+1]"]):
    q = fc.paragraphs[0] if i == 0 else fc.add_paragraph()
    q.paragraph_format.space_after = Pt(1)
    add(q, ln, 10.5, T.INK, bold=(i == 0), font="Consolas")
para("", after=2)
bullet("c_f = L_f·(1 − loss_f), the MW of paying customers cut. High-loss feeders are cheaper to shed, "
       "which reproduces loss-based load management.", "Harm: ", 10.5)
bullet("penalises both under-shedding (grid risk) and over-shedding (needless outages). A = 3.",
       "Deficit: ", 10.5)
bullet("a pairwise penalty on the same feeder in consecutive hours, a natural ZZ interaction. B = 3.",
       "Fairness: ", 10.5)
column_break()
sub("Checking the penalties", before=0)
body("We verified A and B by brute force over all 4,096 states. The global minimum is a schedule "
     "that satisfies every rule, and the cheapest rule-breaking schedule (9.35) costs more than "
     "either valid one (7.70 and 8.00).")
sub("From QUBO to Ising")
body("Substituting x = (1 − Z)/2 gives a Hamiltonian H = Σ hᵢZᵢ + Σ JᵢⱼZᵢZⱼ, built as a Qiskit "
     "SparsePauliOp. A unit test checks that its diagonal equals C(x) for every state.")
c = sidebar("By the numbers", 7.9)
for big, small in (("12", "qubits"), ("4,096", "possible schedules"), (str(INST["n_valid_schedules"]), "valid schedules"),
                   ("12 + 26", "Z and ZZ terms")):
    q = c.add_paragraph(); q.paragraph_format.space_after = Pt(0)
    add(q, big + "  ", 20, "FFFFFF", font=T.HEAD_FONT); add(q, small, 10, T.AMBER_LIGHT)

# =================================================================== PAGE 7 · four rules
new_page()
head("The four rules", 54, after=0)
para("WHAT EVERY LOAD-SHEDDING SCHEDULE MUST GET RIGHT", 17, T.INK2, font=T.HEAD_FONT, after=6)
body("These are the goals a control room juggles every evening. Each one becomes a term in the "
     "quantum cost function, or is removed before the quantum step. Together they create the trade-off "
     "the optimiser has to resolve.", size=10.5, after=12)
tile_grid([
    ("target", "Meet the deficit", "Shed exactly the missing megawatts each hour, no more and no less. "
     "Modelled as a squared penalty A·(shed − deficit)², so both under- and over-shedding cost energy."),
    ("percent", "Loss-based priority", "Prefer feeders with high technical and commercial losses. Each "
     "feeder-hour costs L·(1 − loss rate), the paying-customer MW cut, as a linear term."),
    ("shield", "Protect critical loads", "Hospitals and water pumping are never shed. This is a hard "
     "rule handled classically: the feeder is dropped from the model and uses no qubits."),
    ("clock", "No back-to-back cuts", "Fairness: no feeder goes dark in two consecutive hours. This is a "
     "pairwise penalty B·x[f,h]·x[f,h+1], which maps to one ZZ interaction per pair."),
], ncols=4, dark_h=5.4, desc_h=4.2, icon_cm=2.4, title_size=21, desc_size=10.5)

# =================================================================== PAGE 8 · why QAOA
new_page()
head("Why QAOA?", 54, after=0)
para("THE DESIGN CHOICES BEHIND OUR QUANTUM SOLVER", 17, T.INK2, font=T.HEAD_FONT, after=10)
tile_grid([
    ("nodes", "A natural fit", "Our cost has only linear and pairwise terms: exactly what QAOA's "
     "cost layer (RZ and RZZ gates) implements, with no extra encoding."),
    ("chip", "Quantum does the work", "Every measurement is a candidate rotation table. The circuit's "
     "output is the solution itself, not a side calculation."),
    ("wave", "Near-term friendly", "Shallow parameterised circuits plus a classical optimiser suit "
     "today's noisy hardware, and run on a laptop simulator at 12 to 15 qubits."),
    ("target", "CVaR objective", "We minimise the mean cost of the best 10% of outcomes, not the "
     "average, because in optimisation only the best samples matter (Barkoutsos et al., 2020)."),
    ("layers", "INTERP warm starts", "Depth p+1 is initialised by interpolating the trained angles "
     "from depth p (Zhou et al., 2020), with 10 random restarts per depth."),
    ("fork", "Alternatives considered", "VQE (no problem structure, more parameters), Grover adaptive "
     "search (deep circuits and an oracle), quantum annealing (not in Qiskit)."),
], ncols=3, dark_h=3.6, desc_h=2.4, icon_cm=1.6, title_size=18, desc_size=10.5)

# =================================================================== PAGE 9 · architecture
new_page()
tag("Architecture", size=20)
head("How it fits together", 50, after=6)
picture("results/fig_architecture.png", 24.5, after=2)
caption("Classical pre-processing → QUBO / Ising → hybrid QAOA loop (quantum circuit ⇄ classical "
        "optimiser) → sampling → validation against exact and heuristic baselines → rotation table.")

# =================================================================== PAGE 10 · implementation
new_page()
tag("Implementation", size=20)
head("Building it in Qiskit", 50, after=8)
continuous(3)
sub("Code layout", before=0)
for lead, txt in (("instance.py: ", "feeder data and deficits"),
                  ("qubo.py: ", "QUBO builder, Ising mapping, schedule metrics"),
                  ("qaoa.py: ", "QAOA circuit, CVaR, COBYLA loop, Qiskit Sampler"),
                  ("baselines.py: ", "brute force, greedy rule, simulated annealing"),
                  ("run_experiments.py: ", "the full study, end to end"),
                  ("tests/: ", "Ising = QUBO, optimum is valid, simulator equivalence")):
    bullet(txt, lead, 9.5)
sub("Stack")
body("Qiskit 2.6.2 (QuantumCircuit, ParameterVector, SparsePauliOp, Statevector, StatevectorSampler, "
     "transpile, GenericBackendV2), SciPy COBYLA, NumPy and Matplotlib. Python 3.14.")
column_break()
sub("The quantum loop", before=0)
body(f"For each depth p = 1…{R['config']['p_max']}: build the circuit (H on all qubits, then p "
     f"rounds of an RZZ/RZ cost layer and an RX mixer). COBYLA tunes the 2p angles for up to "
     f"{R['config']['maxiter']} iterations from {R['config']['restarts']} starting points. The trained "
     f"circuit is sampled {R['config']['shots']:,} times with Qiskit's Sampler primitive.")
sub("Circuit cost on a device")
body("Compiled to a 3×4 grid of qubits with native {CZ, RZ, SX, X} gates:", size=9.5)
cs = R["circuit"]
data_table(["Depth", "RZZ", "CZ", "Depth after transpile"],
           [[k, v["logical_2q_gates"], v["transpiled_cz"], v["transpiled_depth"]] for k, v in cs.items()],
           [1.6, 1.4, 1.4, 3.5], size=9)
column_break()
c = sidebar("Honesty note", 7.9)
for txt in ("During training, the QAOA state is computed with an equivalent NumPy routine: the cost layer "
            "is a diagonal phase and the mixer is RX on every qubit. Rebuilding the Qiskit circuit on "
            "every optimiser call was too slow.",
            "A test confirms the routine matches qiskit.quantum_info.Statevector to 1e-16.",
            "Every probability, sample and figure in this report comes from the actual Qiskit circuit."):
    q = c.add_paragraph(); q.paragraph_format.space_after = Pt(5)
    add(q, txt, 9.5, "FFFFFF")
para("", after=4)
c = sidebar("Reproducible", 7.9, fill=T.AMBER)
c.paragraphs[0].runs[0].font.color.rgb = rgb(T.INK)
q = c.add_paragraph(); q.paragraph_format.space_after = Pt(2)
add(q, f"All seeds are fixed. The full run takes about {R['runtime_seconds'] / 60:.0f} minutes on a laptop.",
    9.5, T.INK)

# =================================================================== PAGE 11 · results
new_page()
tag("Results:", size=20)
head("Did it work?", 50, after=4)
picture("results/fig_schedules.png", 25.5, after=0)
rows = []
for name, key in (("Exact (brute force)", "exact_bruteforce"), ("Greedy loss-based rule", "greedy_rule"),
                  ("Simulated annealing", "simulated_annealing")):
    b = BASE[key]
    rows.append([name, "  |  ".join("+".join(v) or "none" for v in b["schedule"].values()),
                 f"{b['cost']:.2f}", b["over_shed_mw"], b["unmet_mw"], b["back_to_back_cuts"],
                 "yes" if b["feasible"] else "no"])
rows.insert(1, [f"CVaR-QAOA (p={ANS['p']})", "  |  ".join("+".join(v) for v in ANS["schedule"].values()),
                f"{BEST['best_sampled_cost']:.2f}", ANS["over_shed_mw"], ANS["unmet_mw"],
                ANS["back_to_back_cuts"], "yes" if ANS["feasible"] else "no"])
data_table(["Method", "Feeders off 18:00 | 19:00 | 20:00", "Cost", "Over-shed MW", "Unmet MW",
            "Back-to-back", "Valid"], rows, [5.0, 7.6, 2.0, 2.9, 2.6, 3.0, 3.0], size=9)
body(f"QAOA's best sample is the exact optimum: it sheds the high-loss feeder F1 at the 19:00 peak and "
     f"rotates the others around it. The greedy rule over-sheds {BASE['greedy_rule']['over_shed_mw']} MW at "
     f"19:00 and cuts {BASE['greedy_rule']['paying_mw_cut']} paying-customer MW against "
     f"{BASE['exact_bruteforce']['paying_mw_cut']} for the optimum.", size=10, after=0).paragraph_format.space_before = Pt(6)

# =================================================================== PAGE 12 · depth
new_page()
tag("QAOA performance", size=20)
head("More layers, better odds", 50, after=4)
picture("results/fig_depth.png", 20.5, after=0)
rows = [[r["p"], pct(r["p_opt"]), f"{r['p_opt'] / RAND:.0f}×", pct(r["p_feasible"]), f"{r['approx_ratio']:.3f}",
         f"{r['opt_hits_in_shots']} / {r['shots']}", "yes" if r["most_frequent_is_opt"] else "no", pct(s["p_opt"])]
        for r, s in zip(CV, ST)]
data_table(["p", "P(optimum)", "vs random", "P(valid)", "Approx. ratio", "Optimal shots",
            "Most frequent = optimum", "Standard QAOA P(opt)"], rows,
           [1.2, 2.8, 2.6, 2.6, 2.8, 3.2, 5.1, 5.8], size=8.5)
para(f"Random guessing finds the optimum {pct(RAND, 3)} of the time. From p = {FIRST_MODE}, the single most "
     f"frequently measured schedule is the optimum.", 9, T.MUTED, italic=True, before=4, after=0)

# =================================================================== PAGE 13 · what the QC saw
new_page()
head("What the quantum computer saw", 48, after=8)
lay = make_table(1, 2, [17.3, 8.4])
left, right = lay.rows[0].cells
left.vertical_alignment = right.vertical_alignment = VA.TOP
left.paragraphs[0].add_run().add_picture("results/fig_histogram.png", width=Cm(16.8))
caption(f"Most frequent schedules at p = {BEST['p']} out of {BEST['shots']:,} shots. Amber = optimal, "
        f"indigo = valid, grey = breaks a rule.", container=left, align=AL.LEFT)
body("Most measured schedules still break a rule, usually by being 10 MW short in one hour. That is the price "
     "of soft penalties. But the optimum is clearly the tallest bar, so reading off the most frequent "
     "result already gives the right answer.", container=left, size=10)
shade(right, T.INK)
add(right.paragraphs[0], "SCALING TO 15 QUBITS", 19, T.AMBER, font=T.HEAD_FONT)
q = right.add_paragraph(); q.paragraph_format.space_after = Pt(6)
add(q, f"Adding a fifth feeder gives 15 qubits, 32,768 schedules and {BIG['n_valid_schedules']} valid ones.",
    9.5, "FFFFFF")
data_table(["p", "P(opt)", "P(valid)", "Best = opt"],
           [[r["p"], pct(r["p_opt"], 3), pct(r["p_feasible"], 2), "yes" if r["best_sampled_is_opt"] else "no"]
            for r in BIG["qaoa_cvar"]], [0.9, 2.1, 2.1, 2.3], size=9, container=right, dark=True)
q = right.add_paragraph(); q.paragraph_format.space_before = Pt(6)
add(q, "The optimum appeared only once in 2,048 shots. Penalty-based QAOA degrades fast as the problem "
       "grows. This is our main limitation.", 9.5, T.AMBER_LIGHT, bold=True)

# =================================================================== PAGE 14 · limitations
new_page()
head("The limits", 54, after=0)
para("AN HONEST ASSESSMENT OF WHAT DIDN'T WORK", 17, T.INK2, font=T.HEAD_FONT, after=8)
tile_grid([
    ("hourglass", "No quantum advantage", "Brute force solves 12 qubits in milliseconds and simulated "
     "annealing finds the optimum instantly. Real DISCOs would use MILP solvers. We claim no speedup."),
    ("dice", "Low success rate", f"Even at the best depth only {pct(BEST['p_opt'])} of shots are optimal. We "
     "rely on best-of-many samples, which scales poorly."),
    ("sliders", "Penalty tuning", "A and B were hand-tuned. The cost range (7.7 to 240) makes the "
     "landscape rugged. Constraint-preserving XY mixers would be better."),
    ("blocks", "Exact-match deficits", "The squared penalty needs sheds to match deficits exactly in "
     "10 MW blocks. Real deficits need slack-variable inequalities, which cost more qubits."),
    ("wave", "Noiseless simulation", "Statevector simulation only. After routing, the p = 8 circuit "
     "needs about 730 CZ gates, and today's hardware noise would swamp it."),
    ("loop", "Training cost", "Thousands of circuit evaluations per depth: the classical optimiser loop "
     "is the bottleneck, not the quantum circuit."),
    ("database", "Illustrative data", "Feeder data are hypothetical. The model ignores network "
     "topology, voltage limits and customer counts per feeder."),
    ("warning", "What didn't work", "At 15 qubits QAOA almost never found the optimum. Standard QAOA beat "
     "CVaR only at p = 2, and at p = 1 it essentially never found a valid schedule."),
], ncols=4, dark_h=3.4, desc_h=3.2, icon_cm=1.5, title_size=16, desc_size=9.8)

# =================================================================== PAGE 15 · next steps
new_page()
head("What's next", 54, after=8)
continuous(3)
sub("Next steps", before=0)
for lead, txt in (("XY mixers: ", "keep the fairness rule satisfied by construction."),
                  ("Decomposition: ", "split by hour or grid station so each quantum sub-problem stays small."),
                  ("Warm starts: ", "seed QAOA from the greedy schedule."),
                  ("Hardware: ", "run on IBM devices with error mitigation."),
                  ("Richer model: ", "customer counts, priority classes and multi-day fairness.")):
    bullet(txt, lead, 10)
column_break()
sub("Reproduce it", before=0)
ct = make_table(1, 1, [7.9])
cc = ct.rows[0].cells[0]
shade(cc, T.SOFT)
for i, ln in enumerate(["git clone", "  https://" + REPO + ".git", "cd qiskit-load-shedding-qaoa", "python -m venv .venv",
                        "pip install -r requirements.txt", "python -m tests.test_formulation",
                        "python run_experiments.py"]):
    q = cc.paragraphs[0] if i == 0 else cc.add_paragraph()
    q.paragraph_format.space_after = Pt(1)
    add(q, ln, 8.5, T.INK, font="Consolas")
body("Results, figures and this report are regenerated by run_experiments.py, make_figures.py and "
     "make_report.py.", size=9.5).paragraph_format.space_before = Pt(6)
column_break()
sub("Credits", before=0)
body("All code was written by the team for this hackathon. Ideas we used:", size=9.5)
for txt in ("QAOA: Farhi, Goldstone & Gutmann, arXiv:1411.4028 (2014)",
            "CVaR objective: Barkoutsos et al., Quantum 4, 256 (2020)",
            "INTERP initialisation: Zhou et al., Phys. Rev. X 10, 021067 (2020)",
            "QUBO penalties: Lucas, Front. Phys. 2, 5 (2014)",
            "Software: Qiskit, SciPy, NumPy, Matplotlib"):
    bullet(txt, size=9.5)

# =================================================================== PAGE 16 · back cover
sec = new_page()
empty_footer(sec)
full_bleed(f"{A}/back.jpg")
para(f"Code:  {REPO}", 14, "FFFFFF", bold=True, before=215, after=4)
para("Video:  [Google Drive link]", 14, "FFFFFF", bold=True, after=4)
para("Team:  [team name / members]", 14, T.AMBER_LIGHT, bold=True, after=0)

doc.save("Report.docx")
print("saved Report.docx")
