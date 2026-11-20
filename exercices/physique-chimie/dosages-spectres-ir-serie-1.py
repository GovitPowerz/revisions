# Builds the PDF of the same name next to this file:
#   uv run --with reportlab --with matplotlib --with rdkit python exercices/physique-chimie/dosages-spectres-ir-serie-1.py
import io
import re
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import AutoMinorLocator, FuncFormatter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
                                Paragraph, Table, TableStyle, XPreformatted)
from reportlab.platypus.flowables import HRFlowable
from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D

OUT = os.path.splitext(os.path.abspath(__file__))[0] + ".pdf"
TITLE = "Dosages par étalonnage et spectres IR"
LEVEL = "Terminale, spécialité physique-chimie"

NAVY_HEX, PINK_HEX, GREY_HEX, BLUE_HEX = "#1b2540", "#c2185b", "#5b6b8c", "#3b6ea5"
NAVY = colors.HexColor(NAVY_HEX)
PINK = colors.HexColor(PINK_HEX)
GREY = colors.HexColor(GREY_HEX)
BOX = colors.HexColor("#eef1f6")
LINE = colors.HexColor("#c9d1e0")

ttf = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
for name, file in [("DV", "DejaVuSans.ttf"), ("DV-B", "DejaVuSans-Bold.ttf"), ("DV-I", "DejaVuSans-Oblique.ttf"),
                   ("DV-BI", "DejaVuSans-BoldOblique.ttf"), ("DVM", "DejaVuSansMono.ttf")]:
    pdfmetrics.registerFont(TTFont(name, os.path.join(ttf, file)))
addMapping("DV", 0, 0, "DV")
addMapping("DV", 1, 0, "DV-B")
addMapping("DV", 0, 1, "DV-I")
addMapping("DV", 1, 1, "DV-BI")

plt.rcParams.update({"mathtext.fontset": "dejavusans", "mathtext.default": "regular", "font.size": 9,
                     "axes.edgecolor": GREY_HEX, "axes.labelcolor": NAVY_HEX, "xtick.color": NAVY_HEX,
                     "ytick.color": NAVY_HEX})

S = {
    "title": ParagraphStyle("title", fontName="DV-B", fontSize=24, leading=29, textColor=NAVY, spaceAfter=4),
    "sub": ParagraphStyle("sub", fontName="DV", fontSize=11.5, leading=15, textColor=GREY, spaceAfter=10),
    "intro": ParagraphStyle("intro", fontName="DV", fontSize=9.5, leading=13, textColor=NAVY, spaceAfter=14),
    "h1": ParagraphStyle("h1", fontName="DV-B", fontSize=15, leading=19, textColor=NAVY, spaceAfter=3),
    "h2": ParagraphStyle("h2", fontName="DV", fontSize=9, leading=12, textColor=PINK, spaceBefore=3, spaceAfter=10),
    "part": ParagraphStyle("part", fontName="DV-B", fontSize=10.5, leading=14, textColor=NAVY, spaceBefore=6,
                           spaceAfter=4),
    "body": ParagraphStyle("body", fontName="DV", fontSize=10, leading=14.5, textColor=NAVY, spaceAfter=6),
    "q": ParagraphStyle("q", fontName="DV", fontSize=10, leading=14.5, textColor=NAVY, leftIndent=18,
                        bulletIndent=0, bulletFontName="DV-B", spaceAfter=5),
    "qcont": ParagraphStyle("qcont", fontName="DV", fontSize=10, leading=14.5, textColor=NAVY, leftIndent=18,
                            spaceAfter=5),
    "bul": ParagraphStyle("bul", fontName="DV", fontSize=9.5, leading=13.5, textColor=NAVY, leftIndent=10,
                          bulletIndent=0, spaceAfter=2),
    "boxh": ParagraphStyle("boxh", fontName="DV-B", fontSize=9.5, leading=13, textColor=NAVY, spaceAfter=3),
    "cap": ParagraphStyle("cap", fontName="DV-I", fontSize=8.5, leading=11, textColor=GREY, alignment=TA_CENTER,
                          spaceBefore=2, spaceAfter=10),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=9, leading=11.5, textColor=NAVY, alignment=TA_CENTER),
    "code": ParagraphStyle("code", fontName="DVM", fontSize=8.8, leading=12, textColor=NAVY),
}

def bar(x):
    """Overlined letter: a combining overline would sit on the glyph, ReportLab does no mark positioning."""
    return f'<u offset="0.84*F" width="0.05*F">{x}</u>'


NBSP = [(" ?", "\u00a0?"), (" :", "\u00a0:"), (" ;", "\u00a0;"), (" !", "\u00a0!"), ("« ", "«\u00a0"),
        (" »", "\u00a0»"), (" €", "\u00a0€"), (" %", "\u00a0%")]


def fr(text):
    text = re.sub(r"(ℬ\([^;()]+|\]0) ; ([^()\[]+[)\[])", "\\1\u00a0;\u00a0\\2", text)
    # spaces inside P(...), E(...), V(...), except those inside a markup tag
    text = re.sub(r"\b[PEV]\([^()]*\)", lambda m: re.sub(r" (?![^<>]*>)", "\u00a0", m.group(0)), text)
    for a, b in NBSP:
        text = text.replace(a, b)
    return text


def keep(style, text):
    if text.rstrip().endswith(":"):
        return ParagraphStyle(style.name + "-k", parent=style, keepWithNext=1)
    return style


def P(text, style="body"):
    return Paragraph(fr(text), keep(S[style], text))


def Q(num, text):
    return Paragraph(fr(text), keep(S["q"], text), bulletText=f"{num}.")


def QC(text):
    return Paragraph(fr(text), keep(S["qcont"], text))


def png(fig, dpi=220):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


def img(buf, width=None, dpi=None):
    """Centred image scaled to `width`, or at its true size when rendered at `dpi`."""
    w, h = ImageReader(buf).getSize()
    buf.seek(0)
    width = width or w * 72 / dpi
    im = Image(buf, width=width, height=width * h / w)
    im.hAlign = "CENTER"
    return im


def F(tex, size=11):
    """Display formula rendered with matplotlib mathtext, at true point size."""
    fig = plt.figure()
    fig.text(0, 0, f"${tex}$", fontsize=size, color=NAVY_HEX)
    im = img(png(fig, dpi=300), dpi=300)
    im.spaceBefore, im.spaceAfter = 2, 6
    return im


def figure(fig, width, caption):
    return KeepTogether([img(png(fig), width), P(caption, "cap")])


def table(rows, first_col=3.2 * cm, col=1.6 * cm):
    data = [[Paragraph(str(c), S["cell"]) for c in r] for r in rows]
    t = Table(data, colWidths=[first_col] + [col] * (len(rows[0]) - 1), hAlign="CENTER")
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("BACKGROUND", (0, 0), (-1, 0), BOX),
        ("BACKGROUND", (0, 0), (0, -1), BOX),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("NOSPLIT", (0, 0), (-1, -1)),
    ]))
    t.spaceAfter = 10
    return t


def code(lines):
    numbered = "\n".join(f"{i + 1:>2}  {l}" for i, l in enumerate(lines))
    t = Table([[XPreformatted(numbered, S["code"])]], colWidths=[A4[0] - 4.4 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BOX), ("LEFTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    t.spaceAfter = 10
    return t


def heading(title, subtitle):
    return [P(title, "h1"), HRFlowable(width="100%", thickness=1.3, color=PINK, spaceBefore=1, spaceAfter=0),
            P(subtitle, "h2")]


def comma(x, _=None):
    s = f"{x:g}"
    return s.replace(".", ",").replace("-", "−")


def donnees(items, width=A4[0] - 4.4 * cm):
    inner = [P("Données", "boxh")] + [Paragraph(fr(t), S["bul"], bulletText="•") for t in items]
    t = Table([[inner]], colWidths=[width])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BOX), ("LEFTPADDING", (0, 0), (-1, -1), 10),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    t.spaceBefore, t.spaceAfter = 2, 10
    return t


def side_by_side(*cells, widths=None):
    """Blocks next to each other; a figure cell is [image, caption] as bare flowables (no KeepTogether in a cell)."""
    widths = widths or [(A4[0] - 4.4 * cm) / len(cells)] * len(cells)
    t = Table([list(cells)], colWidths=widths)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    t.spaceAfter = 4
    return t


def gauss(x, c, w):
    return np.exp(-0.5 * ((x - c) / w) ** 2)


def graph_style(ax):
    ax.grid(True, which="major", color="#c9d1e0", lw=0.6)
    ax.grid(True, which="minor", color="#e6eaf0", lw=0.4)
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    ax.xaxis.set_major_formatter(FuncFormatter(comma))
    ax.yaxis.set_major_formatter(FuncFormatter(comma))
    ax.tick_params(labelsize=7.5)


def ir(ax, bands, title, ylabel=True):
    """Simulated IR spectrum: Gaussian dips at (wavenumber, depth, width). Bands must match the band table."""
    s = np.linspace(4000, 500, 7001)
    t = np.full_like(s, 96.0)
    for c, depth, w in bands:
        t *= 1 - depth * gauss(s, c, w)
    ax.plot(s, t, color=NAVY_HEX, lw=1.0)
    ax.set_xlim(4000, 500)
    ax.set_ylim(0, 100)
    ax.set_xticks(range(4000, 499, -500))
    graph_style(ax)
    ax.set_xlabel("Nombre d'onde σ (cm$^{-1}$)", fontsize=8)
    if ylabel:
        ax.set_ylabel("Transmittance (%)", fontsize=8)
    ax.set_title(title, loc="left", fontsize=8.5, fontweight="bold", color=NAVY_HEX)


def calibration(x, y, slope, read_y, label, xlabel, ylabel, xmax, ylim, intercept=0.0):
    """Calibration points, fitted line and the reading of the unknown sample."""
    fig, ax = plt.subplots(figsize=(3.3, 2.25))
    ax.set_xlim(0, xmax)
    ax.set_ylim(*ylim)
    xs = np.linspace(0, xmax, 50)
    ax.plot(xs, intercept + slope * xs, color=BLUE_HEX, lw=1.1)
    ax.plot(x, y, "o", color=NAVY_HEX, ms=3.5)
    read_x = (read_y - intercept) / slope
    ax.plot([0, read_x], [read_y, read_y], "--", color=PINK_HEX, lw=0.9)
    ax.plot([read_x, read_x], [ylim[0], read_y], "--", color=PINK_HEX, lw=0.9)
    ax.plot([read_x], [read_y], "o", color=PINK_HEX, ms=5)
    ax.annotate(label, (read_x, read_y), xytext=(6, -12), textcoords="offset points", fontsize=7.5, color=PINK_HEX)
    ax.set_xlabel(xlabel, fontsize=8)
    ax.set_ylabel(ylabel, fontsize=8)
    graph_style(ax)
    return fig


def skeletal(smiles):
    """Same bond length and font size for every molecule: place the image with img(buf, dpi=SKELETAL_DPI)."""
    d = rdMolDraw2D.MolDraw2DCairo(-1, -1)
    o = d.drawOptions()
    o.useBWAtomPalette()
    o.bondLineWidth = 2
    o.fixedBondLength = 60
    o.fixedFontSize = 20
    o.padding = 0.1
    d.DrawMolecule(Chem.MolFromSmiles(smiles))
    d.FinishDrawing()
    return io.BytesIO(d.GetDrawingText())


def permanganate_spectrum():
    lam = np.linspace(400, 700, 600)
    fig, ax = plt.subplots(figsize=(3.6, 2.2))
    ax.plot(lam, 0.220 * gauss(lam, 530, 28), color=PINK_HEX, lw=1.3)
    ax.set_xlim(400, 700)
    ax.set_ylim(0, 0.25)
    ax.set_xlabel("λ (nm)", fontsize=8)
    ax.set_ylabel("Absorbance A", fontsize=8)
    graph_style(ax)
    return fig


def serum_points():
    fig, ax = plt.subplots(figsize=(3.6, 2.3))
    ax.plot([2, 4, 6, 8, 10], [25.3, 50.4, 75.9, 101.2, 126.3], "o", color=NAVY_HEX, ms=3.5)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 140)
    ax.set_xlabel("c (mmol·L$^{-1}$)", fontsize=8)
    ax.set_ylabel("σ (mS·m$^{-1}$)", fontsize=8)
    graph_style(ax)
    return fig


PROPANOL = [(3340, .82, 110), (2960, .62, 12), (2935, .45, 10), (2878, .5, 9), (1460, .35, 9), (1380, .28, 8),
            (1240, .15, 10), (1060, .78, 12), (970, .4, 9), (660, .3, 40)]
PROPANONE = [(3000, .18, 9), (2965, .3, 9), (2925, .2, 8), (1715, .93, 9), (1420, .4, 9), (1365, .7, 8),
             (1220, .73, 10), (1090, .26, 8), (530, .45, 9)]
PROPANOIC = [(2950, .7, 260), (2985, .3, 10), (2945, .25, 9), (1710, .93, 10), (1465, .3, 8), (1420, .45, 9),
             (1240, .7, 12), (1080, .32, 9), (935, .45, 14)]
METHYL_ETHANOATE = [(3000, .18, 9), (2960, .33, 9), (1745, .93, 9), (1440, .4, 9), (1370, .5, 8), (1240, .9, 12),
                    (1050, .63, 11), (845, .26, 9)]
ISOAMYL_ETHANOATE = [(2960, .52, 12), (2875, .33, 10), (1740, .93, 9), (1460, .32, 9), (1370, .45, 8),
                     (1240, .9, 12), (1060, .55, 9), (1035, .38, 8)]
ISOAMYL_ALCOHOL = [(3330, .8, 110), (2955, .79, 13), (2875, .58, 10), (1470, .4, 9), (1385, .33, 8),
                   (1055, .77, 12), (1010, .33, 8)]


def four_spectra():
    fig, axs = plt.subplots(2, 2, figsize=(7.6, 5.0), sharex=True, sharey=True)
    for ax, bands, title in zip(axs.flat, [PROPANOL, PROPANONE, PROPANOIC, METHYL_ETHANOATE],
                                ["Spectre 1", "Spectre 2", "Spectre 3", "Spectre 4"]):
        ir(ax, bands, title)
    for ax in axs[0]:
        ax.set_xlabel("")
    for ax in axs[:, 1]:
        ax.set_ylabel("")
    fig.tight_layout()
    return fig


def banana_spectra():
    fig, axs = plt.subplots(1, 2, figsize=(7.6, 2.6), sharey=True)
    ir(axs[0], ISOAMYL_ETHANOATE, "Spectre X")
    ir(axs[1], ISOAMYL_ALCOHOL, "Spectre Y", ylabel=False)
    fig.tight_layout()
    return fig


IR_TABLE = [
    ["<b>Liaison</b>", "<b>Nombre d'onde (cm<super>−1</super>)</b>", "<b>Allure de la bande</b>"],
    ["O–H d'un alcool (liaisons hydrogène)", "3200 – 3400", "forte, large"],
    ["O–H d'un acide carboxylique", "2500 – 3200", "forte, très large"],
    ["N–H d'une amine ou d'un amide", "3100 – 3500", "moyenne"],
    ["C–H", "2800 – 3000", "moyenne à forte"],
    ["C=O d'un ester", "1735 – 1750", "forte, fine"],
    ["C=O d'un aldéhyde", "1720 – 1740", "forte, fine"],
    ["C=O d'une cétone", "1705 – 1725", "forte, fine"],
    ["C=O d'un acide carboxylique", "1700 – 1725", "forte, fine"],
    ["C=O d'un amide", "1650 – 1700", "forte"],
    ["C–O", "1050 – 1300", "forte"],
]

SKELETAL_DPI = 110
CM1 = "cm<super>−1</super>"
ML = "mol·L<super>−1</super>"
MMOL = "mmol·L<super>−1</super>"


def content():
    # ---------------------------------------------------------------- numbers
    a1 = [0.044, 0.088, 0.131, 0.176, 0.220]
    assert [round(a / (c * 1e-5)) for a, c in zip(a1, [2, 4, 6, 8, 10])] == [2200, 2200, 2183, 2200, 2200]
    cd = 0.140 / 2.2e3
    assert round(cd * 1e5, 1) == 6.4 and round(6.4e-5 * 0.100 * 158 * 1e3, 1) == 1.0
    s2 = [25.3, 50.4, 75.9, 101.2, 126.3]
    assert [round(s / c, 2) for s, c in zip(s2, [2, 4, 6, 8, 10])] == [12.65, 12.6, 12.65, 12.65, 12.63]
    assert round(97.0 / 12.6, 1) == 7.7 and round(20 * 7.7e-3, 3) == 0.154 and round(0.154 * 58.5, 1) == 9.0
    assert round(0.23 * 1120 / 36.5, 1) == 7.1 and round(298 / (34.98 + 7.63), 2) == 6.99
    assert round(6.99 * 36.5) == 255 and round(255 / 1120, 3) == 0.228 and round(0.10 / 7.1 * 1e3) == 14
    assert round(1 / 1715 * 1e4, 2) == 5.83

    # ---------------------------------------------------------------- statements

    EX = []

    EX.append(heading("Exercice 1. Le permanganate dans l'eau de Dakin",
                      "Dosage par étalonnage spectrophotométrique") + [
        P("L'eau de Dakin est un antiseptique. Sa teinte rose est due aux ions permanganate "
          "MnO<sub>4</sub><super>−</super>, apportés par du permanganate de potassium KMnO<sub>4</sub>. L'étiquette "
          "indique : « permanganate de potassium : 0,0010 g pour 100 mL ». On souhaite contrôler cette indication."),
        P(f"On dispose d'une solution mère S<sub>5</sub> de permanganate de potassium de concentration "
          f"c<sub>5</sub> = 1,0 × 10<super>−4</super> {ML}. On prépare par dilution quatre solutions filles "
          "S<sub>1</sub> à S<sub>4</sub>, puis on mesure l'absorbance de chaque solution à la longueur d'onde "
          "λ = 530 nm, dans des cuves identiques. Dans les mêmes conditions, l'eau de Dakin a une absorbance "
          "A<sub>D</sub> = 0,140. À cette longueur d'onde, seul l'ion permanganate absorbe."),
        table([["Solution", "S<sub>1</sub>", "S<sub>2</sub>", "S<sub>3</sub>", "S<sub>4</sub>", "S<sub>5</sub>"],
               [f"c (× 10<super>−5</super> {ML})", "2,0", "4,0", "6,0", "8,0", "10,0"],
               ["Absorbance A", "0,044", "0,088", "0,131", "0,176", "0,220"]], 4.6 * cm, 2.2 * cm),
        side_by_side([img(png(permanganate_spectrum()), 6.6 * cm),
                      P("Figure 1. Spectre d'absorption de la solution S<sub>5</sub>.", "cap")],
                     [donnees(["M(KMnO<sub>4</sub>) = 158 g·mol<super>−1</super>.",
                               "Le vert et le magenta sont des couleurs complémentaires.",
                               "Verrerie disponible : pipettes jaugées de 5,0 mL, 10,0 mL et 20,0 mL ; fioles "
                               "jaugées de 50,0 mL et 100,0 mL."], 9.4 * cm)],
                     widths=[7.2 * cm, 9.4 * cm]),
        Q(1, "À l'aide de la figure 1, justifier le choix de la longueur d'onde de travail, puis expliquer la couleur "
             "de la solution."),
        Q(2, "Décrire la préparation de 50,0 mL de la solution S<sub>2</sub> à partir de la solution S<sub>5</sub>, "
             "en précisant la verrerie utilisée."),
        Q(3, "Montrer que les mesures sont en accord avec la loi de Beer-Lambert, puis déterminer le coefficient k "
             "tel que A = k·c."),
        Q(4, "En déduire la concentration c<sub>D</sub> en ions permanganate de l'eau de Dakin."),
        Q(5, "Calculer la masse de permanganate de potassium contenue dans 100 mL d'eau de Dakin. Comparer à "
             "l'étiquette."),
        Q(6, "Une autre solution de permanganate, mesurée dans les mêmes conditions, a une absorbance A = 0,65. "
             "Peut-on utiliser directement la droite d'étalonnage ? Proposer une solution."),
    ])

    EX.append(heading("Exercice 2. Le sérum physiologique",
                      "Dosage par étalonnage conductimétrique, loi de Kohlrausch") + [
        P("Le sérum physiologique est une solution aqueuse de chlorure de sodium (Na<super>+</super>(aq) + "
          "Cl<super>−</super>(aq)). L'étiquette indique « chlorure de sodium : 0,9 % », ce qui correspond à 9,0 g de "
          "chlorure de sodium par litre de solution. On souhaite contrôler cette indication."),
        P("On prépare cinq solutions étalons de chlorure de sodium et on mesure leur conductivité σ avec la même "
          "cellule, à la même température. On dilue ensuite 20 fois le sérum : on obtient une solution S, dont la "
          "conductivité vaut σ<sub>S</sub> = 97,0 mS·m<super>−1</super> dans les mêmes conditions."),
        table([["Solution", "E<sub>1</sub>", "E<sub>2</sub>", "E<sub>3</sub>", "E<sub>4</sub>", "E<sub>5</sub>"],
               [f"c ({MMOL})", "2,0", "4,0", "6,0", "8,0", "10,0"],
               ["σ (mS·m<super>−1</super>)", "25,3", "50,4", "75,9", "101,2", "126,3"]], 4.6 * cm, 2.2 * cm),
        figure(serum_points(), 6.6 * cm,
               "Figure 2. Conductivité des solutions étalons en fonction de leur concentration."),
        donnees(["M(NaCl) = 58,5 g·mol<super>−1</super>.",
                 "Conductivités molaires ioniques λ, en mS·m<super>2</super>·mol<super>−1</super> : "
                 "Na<super>+</super> 5,01 ; Cl<super>−</super> 7,63.",
                 f"La loi de Kohlrausch s'applique aux solutions diluées, de concentration inférieure à "
                 f"10<super>−2</super> {ML} environ. Les concentrations s'y expriment en mol·m<super>−3</super>.",
                 "Verrerie disponible : pipettes jaugées de 5,0 mL, 10,0 mL et 25,0 mL ; fioles jaugées de 50,0 mL, "
                 "100,0 mL et 250,0 mL."]),
        Q(1, "Choisir, dans la verrerie disponible, celle qui permet de diluer 20 fois le sérum. Justifier."),
        Q(2, "Expliquer pourquoi il faut diluer le sérum avant de mesurer sa conductivité."),
        Q(3, "Montrer que les mesures sont en accord avec une relation σ = k·c, puis déterminer la valeur du "
             "coefficient k."),
        Q(4, f"Écrire la loi de Kohlrausch pour une solution de chlorure de sodium de concentration c. Montrer que "
             f"1 {MMOL} = 1 mol·m<super>−3</super>, puis vérifier que la valeur de k est cohérente avec les "
             "conductivités molaires ioniques."),
        Q(5, "Déterminer la concentration c<sub>S</sub> de la solution S, puis la concentration c du sérum."),
        Q(6, "En déduire la concentration en masse du sérum en chlorure de sodium. Comparer à l'étiquette."),
        Q(7, "Aurait-on pu réaliser ce dosage par spectrophotométrie dans le visible ? Justifier."),
    ])

    EX.append(heading("Exercice 3. Un acide chlorhydrique du commerce",
                      "Titre massique, densité, dilution et mesure conductimétrique") + [
        P("Un bidon d'acide chlorhydrique vendu en magasin de bricolage porte l'étiquette : « Acide chlorhydrique à "
          "23 % en masse de chlorure d'hydrogène HCl. Densité : d = 1,12 ». On souhaite contrôler ce titre "
          "massique."),
        P("L'acide chlorhydrique est une solution aqueuse qui contient des ions oxonium "
          "H<sub>3</sub>O<super>+</super>(aq) et des ions chlorure Cl<super>−</super>(aq), tous deux à la "
          "concentration c de la solution."),
        P("On dilue 1000 fois la solution commerciale S<sub>0</sub>, en deux dilutions successives : on obtient une "
          "solution S<sub>1</sub> de concentration c<sub>1</sub>. À 25 °C, la conductivité de la solution "
          "S<sub>1</sub> vaut σ<sub>1</sub> = 298 mS·m<super>−1</super>."),
        donnees(["M(HCl) = 36,5 g·mol<super>−1</super> ; masse volumique de l'eau : ρ<sub>eau</sub> = "
                 "1,00 kg·L<super>−1</super>.",
                 "Conductivités molaires ioniques λ à 25 °C, en mS·m<super>2</super>·mol<super>−1</super> : "
                 "H<sub>3</sub>O<super>+</super> 34,98 ; Cl<super>−</super> 7,63.",
                 f"La loi de Kohlrausch s'applique aux solutions diluées, de concentration inférieure à "
                 f"10<super>−2</super> {ML} environ. Les concentrations s'y expriment en mol·m<super>−3</super>.",
                 "Verrerie disponible : pipettes jaugées de 5,0 mL, 10,0 mL et 20,0 mL ; fioles jaugées de "
                 "100,0 mL, 500,0 mL et 1000,0 mL."]),
        Q(1, f"Définir le titre massique d'une solution. À partir des indications de l'étiquette, montrer que la "
             f"concentration attendue de la solution commerciale est c<sub>0</sub> ≈ 7,1 {ML}."),
        Q(2, "Proposer deux dilutions successives permettant de diluer 1000 fois la solution commerciale avec la "
             "verrerie disponible. Quelles précautions impose la manipulation de la solution commerciale ?"),
        Q(3, "Écrire la loi de Kohlrausch pour la solution S<sub>1</sub>, en fonction de c<sub>1</sub> et des "
             "conductivités molaires ioniques."),
        Q(4, f"Calculer c<sub>1</sub> en mol·m<super>−3</super>, puis en {ML}."),
        Q(5, "En déduire la concentration c<sub>0</sub> de la solution commerciale, puis son titre massique. Comparer "
             "à l'étiquette."),
        Q(6, "Pourquoi n'a-t-on pas mesuré directement la conductivité de la solution commerciale ?"),
        Q(7, f"Quel volume de solution commerciale faut-il prélever pour préparer 1,0 L d'acide chlorhydrique de "
             f"concentration 0,10 {ML} ? On prendra c<sub>0</sub> = 7,1 {ML}."),
    ])

    EX.append(heading("Exercice 4. Six molécules, quatre spectres",
                      "Groupes caractéristiques, familles de composés et spectroscopie infrarouge") + [
        P("On considère six espèces chimiques organiques, notées A à F :"),
        table([["Espèce", "Formule semi-développée"],
               ["A", "CH<sub>3</sub>–CH<sub>2</sub>–CH<sub>2</sub>–OH"],
               ["B", "CH<sub>3</sub>–CO–CH<sub>3</sub>"],
               ["C", "CH<sub>3</sub>–CH<sub>2</sub>–COOH"],
               ["D", "CH<sub>3</sub>–COO–CH<sub>3</sub>"],
               ["E", "CH<sub>3</sub>–CH<sub>2</sub>–CO–NH<sub>2</sub>"],
               ["F", "CH<sub>3</sub>–CH<sub>2</sub>–CH<sub>2</sub>–NH<sub>2</sub>"]], 2.4 * cm, 6.4 * cm),
        P("Les spectres infrarouges de quatre d'entre elles ont été enregistrés (figure 3)."),
        figure(four_spectra(), 16.4 * cm, "Figure 3. Spectres infrarouges de quatre des six espèces."),
        KeepTogether([table(IR_TABLE, 7.4 * cm, 4.4 * cm),
                      P("Tableau. Bandes d'absorption infrarouge de quelques liaisons.", "cap")]),
        Q(1, "Pour chaque espèce, identifier le groupe caractéristique et la famille de composés correspondante."),
        Q(2, "Associer à chaque espèce son nom : propan-1-ol, propanone, acide propanoïque, éthanoate de méthyle, "
             "propanamide, propan-1-amine."),
        Q(3, "Montrer que les espèces C et D sont isomères."),
        Q(4, "Attribuer chacun des spectres 1 à 4 à l'une des six espèces, en justifiant à l'aide du tableau."),
        Q(5, "Quelles bandes caractéristiques s'attend-on à observer sur le spectre de l'espèce E ?"),
        Q(6, f"Calculer la longueur d'onde associée au nombre d'onde σ = 1715 {CM1}. Vérifier qu'elle appartient au "
             "domaine infrarouge, qui s'étend de 800 nm à 1 mm."),
        Q(7, f"On oxyde du propan-2-ol pour obtenir de la propanone. Le spectre infrarouge du produit, soigneusement "
             f"séché, présente une bande intense à 1715 {CM1} et une bande large vers 3350 {CM1}. Que peut-on en "
             "conclure ?"),
    ])

    EX.append(heading("Exercice 5. L'arôme de banane",
                      "Formules topologiques, groupes caractéristiques et spectroscopie infrarouge") + [
        P("L'éthanoate de 3-méthylbutyle est l'espèce responsable de l'odeur de banane de nombreux bonbons. On le "
          "synthétise au laboratoire en faisant réagir le 3-méthylbutan-1-ol avec l'acide éthanoïque. Il se forme "
          "aussi de l'eau."),
        KeepTogether([
            side_by_side([img(skeletal("OCCC(C)C"), dpi=SKELETAL_DPI), P("A : 3-méthylbutan-1-ol", "cap")],
                         [img(skeletal("CC(=O)O"), dpi=SKELETAL_DPI), P("B : acide éthanoïque", "cap")],
                         [img(skeletal("CC(=O)OCCC(C)C"), dpi=SKELETAL_DPI),
                          P("E : éthanoate de 3-méthylbutyle", "cap")],
                         widths=[5.2 * cm, 4.2 * cm, 7.2 * cm]),
            P("Figure 4. Formules topologiques des trois espèces organiques.", "cap")]),
        P("On enregistre le spectre infrarouge de deux de ces espèces, à l'état pur (figure 5). On utilisera le "
          "tableau des bandes d'absorption de l'exercice 4."),
        figure(banana_spectra(), 16.4 * cm, "Figure 5. Spectres infrarouges de deux des trois espèces."),
        Q(1, "Écrire la formule semi-développée et la formule brute des espèces A et E."),
        Q(2, "Pour chacune des espèces A, B et E, identifier le groupe caractéristique et la famille de composés."),
        Q(3, "Justifier le nom 3-méthylbutan-1-ol de l'espèce A."),
        Q(4, "Écrire l'équation de la réaction de synthèse en utilisant les formules brutes. Vérifier la conservation "
             "des éléments."),
        Q(5, "Attribuer les spectres X et Y à deux des espèces A, B et E, en justifiant."),
        Q(6, f"Le spectre du produit obtenu en fin de synthèse présente, en plus des bandes de l'ester, une bande très "
             f"large entre 2500 et 3200 {CM1} et un épaulement vers 1710 {CM1}. Quelle espèce le produit "
             "contient-il encore ?"),
        Q(7, "L'éthanoate de pentyle a pour formule "
             "CH<sub>3</sub>–COO–CH<sub>2</sub>–CH<sub>2</sub>–CH<sub>2</sub>–CH<sub>2</sub>–CH<sub>3</sub>. Montrer "
             "que c'est un isomère de l'espèce E. Les bandes du tableau permettent-elles de distinguer ces deux "
             "espèces ?"),
    ])

    # ---------------------------------------------------------------- corrections

    CO = []

    CO.append(heading("Corrigé de l'exercice 1", "Dosage par étalonnage spectrophotométrique") + [
        Q(1, "Le spectre présente un maximum d'absorption vers 530 nm. À cette longueur d'onde, l'absorbance est la "
             "plus grande pour une concentration donnée : la mesure est plus sensible et son incertitude relative plus "
             "faible. La solution absorbe surtout dans le vert ; elle a donc la couleur complémentaire, le magenta, "
             "d'où sa teinte rose-violet."),
        Q(2, "Lors d'une dilution, la quantité de matière de soluté se conserve : c<sub>5</sub>·V<sub>5</sub> = "
             "c<sub>2</sub>·V<sub>2</sub>, soit V<sub>5</sub> = 4,0 × 10<super>−5</super> × 50,0 / "
             "(1,0 × 10<super>−4</super>) = 20,0 mL."),
        QC("On prélève 20,0 mL de S<sub>5</sub> avec une pipette jaugée, on les verse dans une fiole jaugée de "
           "50,0 mL, on complète à l'eau distillée jusqu'au trait de jauge, puis on bouche et on homogénéise."),
        Q(3, "On calcule le quotient A / c pour chaque solution, en L·mol<super>−1</super> : 2200 ; 2200 ; 2183 ; "
             "2200 ; 2200. Il est constant à moins de 1 % près : l'absorbance est proportionnelle à la concentration, "
             "et les points s'alignent sur une droite passant par l'origine. C'est la loi de Beer-Lambert, A = k·c, "
             "avec k = 2,2 × 10<super>3</super> L·mol<super>−1</super>."),
        figure(calibration([2, 4, 6, 8, 10], a1, 0.022, 0.140, "Dakin", "c (× 10$^{-5}$ mol·L$^{-1}$)",
                           "Absorbance A", 11, (0, 0.25)),
               5.8 * cm, "Droite d'étalonnage et lecture de la concentration de l'eau de Dakin."),
        Q(4, f"c<sub>D</sub> = A<sub>D</sub> / k = 0,140 / (2,2 × 10<super>3</super>) = 6,4 × 10<super>−5</super> "
             f"{ML}. La lecture graphique sur la droite d'étalonnage donne la même valeur."),
        Q(5, "m = c<sub>D</sub> × V × M = 6,4 × 10<super>−5</super> × 0,100 × 158 = 1,0 × 10<super>−3</super> g, "
             "soit 1,0 mg pour 100 mL. C'est la valeur portée sur l'étiquette (0,0010 g) : l'écart est d'environ "
             "1 %, l'indication est vérifiée."),
        Q(6, "Non. L'absorbance 0,65 est très au-dessus de celle de la solution étalon la plus concentrée (0,220) : "
             "rien ne garantit que la proportionnalité reste valable dans ce domaine, et prolonger la droite serait "
             "hasardeux. Il faut diluer la solution, par exemple 5 fois (absorbance attendue proche de 0,13), mesurer "
             "son absorbance, lire la concentration sur la droite, puis la multiplier par le facteur de dilution."),
    ])

    CO.append(heading("Corrigé de l'exercice 2", "Dosage par étalonnage conductimétrique, loi de Kohlrausch") + [
        Q(1, "Le facteur de dilution est le rapport du volume de la fiole au volume de la pipette. Il vaut 20 pour la "
             "pipette jaugée de 5,0 mL et la fiole jaugée de 100,0 mL (100,0 / 5,0 = 20). Aucune autre association "
             "ne donne ce facteur."),
        Q(2, f"Le sérum a une concentration proche de 9,0 / 58,5 = 0,15 {ML}, bien supérieure à 10<super>−2</super> "
             f"{ML} : la loi de Kohlrausch ne s'y applique pas, et sa conductivité n'est pas proportionnelle à sa "
             f"concentration. Il faut aussi que la mesure tombe dans le domaine des solutions étalons, de 2 à 10 "
             f"{MMOL}. Dilué 20 fois, le sérum a une concentration voisine de 7,7 {MMOL}."),
        Q(3, f"Les points sont alignés sur une droite passant par l'origine : σ est proportionnelle à c. Le quotient "
             f"σ / c vaut 12,65 ; 12,60 ; 12,65 ; 12,65 ; 12,63 pour les cinq solutions, soit k = 12,6 "
             f"mS·m<super>−1</super> par {MMOL}."),
        figure(calibration([2, 4, 6, 8, 10], s2, 12.6, 97.0, "solution S", "c (mmol·L$^{-1}$)",
                           "σ (mS·m$^{-1}$)", 11, (0, 140)),
               5.8 * cm, "Droite d'étalonnage et lecture de la concentration de la solution S."),
        Q(4, "σ = λ(Na<super>+</super>)·[Na<super>+</super>] + λ(Cl<super>−</super>)·[Cl<super>−</super>]. Dans "
             "une solution de chlorure de sodium, [Na<super>+</super>] = [Cl<super>−</super>] = c, donc "
             "σ = (λ(Na<super>+</super>) + λ(Cl<super>−</super>))·c."),
        QC(f"Un mètre cube contient 1000 L : 1 {MMOL} = 10<super>−3</super> mol pour 10<super>−3</super> "
           "m<super>3</super>, soit 1 mol·m<super>−3</super>. La valeur de k s'exprime donc aussi en "
           "mS·m<super>2</super>·mol<super>−1</super> : k = 12,6 mS·m<super>2</super>·mol<super>−1</super>."),
        QC("La loi de Kohlrausch prévoit k = 5,01 + 7,63 = 12,64 mS·m<super>2</super>·mol<super>−1</super>. Les "
           "deux valeurs sont en accord."),
        Q(5, f"c<sub>S</sub> = σ<sub>S</sub> / k = 97,0 / 12,6 = 7,7 {MMOL} (lecture graphique : toute valeur entre "
             f"7,6 et 7,8 {MMOL} est acceptable). Le sérum est 20 fois plus concentré : "
             f"c = 20 × 7,7 × 10<super>−3</super> = 0,154 {ML}."),
        Q(6, "Concentration en masse : t = c × M = 0,154 × 58,5 = 9,0 g·L<super>−1</super>. C'est la valeur portée "
             "sur l'étiquette : l'indication est vérifiée."),
        Q(7, "Non. Les ions sodium et chlorure sont incolores : la solution n'absorbe pas dans le visible, et son "
             "absorbance y serait nulle quelle que soit la concentration. La spectrophotométrie visible ne convient "
             "qu'aux espèces colorées."),
    ])

    CO.append(heading("Corrigé de l'exercice 3", "Titre massique, densité, dilution et mesure conductimétrique") + [
        Q(1, "Le titre massique est le rapport de la masse de soluté à la masse de solution qui le contient."),
        QC(f"Un litre de solution commerciale a une masse m = d × ρ<sub>eau</sub> × V = 1,12 × 1,00 × 1,00 = "
           f"1,12 kg, soit 1120 g. Il contient 0,23 × 1120 = 258 g de chlorure d'hydrogène, soit "
           f"n = 258 / 36,5 = 7,1 mol. Donc c<sub>0</sub> ≈ 7,1 {ML}."),
        Q(2, "On dilue d'abord 10 fois : 10,0 mL de S<sub>0</sub> prélevés à la pipette jaugée, versés dans une fiole "
             "jaugée de 100,0 mL que l'on complète à l'eau distillée. On dilue ensuite 100 fois la solution obtenue : "
             "5,0 mL dans une fiole de 500,0 mL (ou 10,0 mL dans une fiole de 1000,0 mL). Au total, "
             "10 × 100 = 1000."),
        QC("La solution commerciale est corrosive et dégage des vapeurs irritantes : blouse, gants, lunettes de "
           "protection et travail sous hotte. On verse toujours l'acide dans l'eau, jamais l'inverse."),
        Q(3, "σ<sub>1</sub> = λ(H<sub>3</sub>O<super>+</super>)·[H<sub>3</sub>O<super>+</super>] + "
             "λ(Cl<super>−</super>)·[Cl<super>−</super>], avec [H<sub>3</sub>O<super>+</super>] = "
             "[Cl<super>−</super>] = c<sub>1</sub>, donc σ<sub>1</sub> = (λ(H<sub>3</sub>O<super>+</super>) + "
             "λ(Cl<super>−</super>))·c<sub>1</sub>."),
        Q(4, f"c<sub>1</sub> = σ<sub>1</sub> / (λ(H<sub>3</sub>O<super>+</super>) + λ(Cl<super>−</super>)) = "
             f"298 / (34,98 + 7,63) = 298 / 42,61 = 6,99 mol·m<super>−3</super>. Comme 1 mol·m<super>−3</super> = "
             f"10<super>−3</super> {ML}, c<sub>1</sub> = 6,99 × 10<super>−3</super> {ML}."),
        QC(f"Cette concentration est inférieure à 10<super>−2</super> {ML} : la loi de Kohlrausch s'applique bien."),
        Q(5, f"c<sub>0</sub> = 1000 × c<sub>1</sub> = 6,99 {ML}. Un litre de solution commerciale contient donc "
             "6,99 × 36,5 = 255 g de chlorure d'hydrogène pour une masse totale de 1120 g. Le titre massique vaut "
             "255 / 1120 = 0,228, soit 22,8 %."),
        QC("L'écart relatif avec l'étiquette vaut (23 − 22,8) / 23, soit environ 1 % : l'indication est vérifiée."),
        Q(6, "La solution commerciale est beaucoup trop concentrée pour que la loi de Kohlrausch s'applique : sa "
             "conductivité n'est pas proportionnelle à sa concentration, et la mesure ne permettrait pas de remonter "
             "à c<sub>0</sub>. La dilution évite aussi de plonger la cellule dans une solution corrosive."),
        Q(7, "Il faut n = 0,10 × 1,0 = 0,10 mol de soluté. Le volume à prélever est V<sub>0</sub> = n / c<sub>0</sub> "
             "= 0,10 / 7,1 = 0,014 L, soit 14 mL."),
    ])

    CO.append(heading("Corrigé de l'exercice 4",
                      "Groupes caractéristiques, familles de composés et spectroscopie infrarouge") + [
        Q(1, "Les groupes caractéristiques et les familles sont donnés dans le tableau ci-dessous."),
        Q(2, "Les noms sont donnés dans le même tableau."),
        table([["<b>Espèce</b>", "<b>Nom</b>", "<b>Groupe caractéristique</b>", "<b>Famille</b>"],
               ["A", "propan-1-ol", "hydroxyle –OH", "alcool"],
               ["B", "propanone", "carbonyle C=O, porté par un carbone lié à deux carbones", "cétone"],
               ["C", "acide propanoïque", "carboxyle –COOH", "acide carboxylique"],
               ["D", "éthanoate de méthyle", "ester –COO–C", "ester"],
               ["E", "propanamide", "amide –CO–N", "amide"],
               ["F", "propan-1-amine", "amine –NH<sub>2</sub>", "amine"]], 2.0 * cm, 4.6 * cm),
        Q(3, "C et D ont la même formule brute, C<sub>3</sub>H<sub>6</sub>O<sub>2</sub>, mais des enchaînements "
             "d'atomes différents : ce sont des isomères de constitution."),
        Q(4, f"Spectre 1 : espèce A. Bande forte et large vers 3340 {CM1}, caractéristique de la liaison O–H d'un "
             f"alcool, et aucune bande C=O vers 1700 {CM1}. La bande forte vers 1060 {CM1} correspond à la liaison "
             "C–O."),
        QC(f"Spectre 2 : espèce B. Bande fine et intense à 1715 {CM1}, dans le domaine du C=O d'une cétone, et "
           f"aucune bande au-dessus de 3100 {CM1} : ni O–H, ni N–H."),
        QC(f"Spectre 3 : espèce C. Bande très large entre 2500 et 3200 {CM1} (O–H d'un acide carboxylique) et bande "
           f"intense vers 1710 {CM1} (C=O)."),
        QC(f"Spectre 4 : espèce D. Bande intense à 1745 {CM1}, dans le domaine du C=O d'un ester, bande forte vers "
           f"1240 {CM1} (C–O) et aucune bande O–H."),
        Q(5, f"Pour le propanamide, on attend une absorption N–H entre 3100 et 3500 {CM1} et une bande C=O d'amide "
             f"entre 1650 et 1700 {CM1}, en plus des bandes C–H entre 2800 et 3000 {CM1}."),
        Q(6, "λ = 1 / σ = 1 / 1715 = 5,83 × 10<super>−4</super> cm, soit 5,83 × 10<super>−6</super> m ou 5,83 µm. "
             "Cette valeur est comprise entre 800 nm (0,8 µm) et 1 mm (1000 µm) : elle appartient bien au domaine "
             "infrarouge."),
        Q(7, f"La bande à 1715 {CM1} révèle une liaison C=O de cétone : de la propanone s'est formée. La bande large "
             f"vers 3350 {CM1} révèle une liaison O–H : le produit contient encore du propan-2-ol, puisque "
             "l'échantillon a été séché et ne contient pas d'eau. La transformation n'est donc pas terminée, ou le "
             "produit n'a pas été correctement purifié."),
    ])

    CO.append(heading("Corrigé de l'exercice 5",
                      "Formules topologiques, groupes caractéristiques et spectroscopie infrarouge") + [
        Q(1, "Dans une formule topologique, chaque extrémité et chaque sommet de la ligne brisée représente un atome "
             "de carbone, et les atomes d'hydrogène liés aux carbones ne sont pas dessinés."),
        QC("A : CH<sub>3</sub>–CH(CH<sub>3</sub>)–CH<sub>2</sub>–CH<sub>2</sub>–OH, de formule brute "
           "C<sub>5</sub>H<sub>12</sub>O."),
        QC("E : CH<sub>3</sub>–COO–CH<sub>2</sub>–CH<sub>2</sub>–CH(CH<sub>3</sub>)–CH<sub>3</sub>, de formule brute "
           "C<sub>7</sub>H<sub>14</sub>O<sub>2</sub>."),
        Q(2, "A porte le groupe hydroxyle –OH : c'est un alcool. B porte le groupe carboxyle –COOH : c'est un acide "
             "carboxylique. E porte le groupe ester –COO–C : c'est un ester."),
        Q(3, "La chaîne carbonée la plus longue qui contient le carbone porteur du groupe hydroxyle compte 4 atomes "
             "de carbone : butan. On la numérote à partir de l'extrémité la plus proche du groupe hydroxyle, qui est "
             "donc porté par le carbone 1 : butan-1-ol. Un groupe méthyle est fixé sur le carbone 3 : "
             "3-méthylbutan-1-ol."),
        Q(4, "L'acide éthanoïque a pour formule brute C<sub>2</sub>H<sub>4</sub>O<sub>2</sub>. L'équation s'écrit "
             "C<sub>5</sub>H<sub>12</sub>O + C<sub>2</sub>H<sub>4</sub>O<sub>2</sub> → "
             "C<sub>7</sub>H<sub>14</sub>O<sub>2</sub> + H<sub>2</sub>O."),
        QC("De chaque côté, on compte 7 atomes de carbone, 16 atomes d'hydrogène et 3 atomes d'oxygène."),
        Q(5, f"Spectre X : espèce E. Bande fine et intense vers 1740 {CM1}, dans le domaine du C=O d'un ester, bande "
             f"forte vers 1240 {CM1} (C–O), et aucune bande au-dessus de 3000 {CM1} : pas de liaison O–H."),
        QC(f"Spectre Y : espèce A. Bande forte et large vers 3330 {CM1}, caractéristique de la liaison O–H d'un "
           f"alcool, et aucune bande C=O vers 1700 {CM1}."),
        Q(6, f"La bande très large entre 2500 et 3200 {CM1} est celle de la liaison O–H d'un acide carboxylique, et "
             f"l'épaulement vers 1710 {CM1} celle de son C=O. Le produit contient encore de l'acide éthanoïque : il "
             "doit être purifié."),
        Q(7, "L'éthanoate de pentyle a pour formule brute C<sub>7</sub>H<sub>14</sub>O<sub>2</sub>, comme E, mais sa "
             "chaîne carbonée est linéaire et non ramifiée : les deux espèces sont des isomères de constitution."),
        QC(f"Elles portent le même groupe ester et les mêmes types de liaisons : leurs spectres présentent les mêmes "
           f"bandes caractéristiques, et le tableau ne permet pas de les distinguer. Seule la zone située en dessous "
           f"de 1500 {CM1}, propre à chaque molécule, diffère : il faut comparer le spectre à un spectre de "
           "référence."),
    ])
    return EX, CO


# ---------------------------------------------------------------- document

class Doc(BaseDocTemplate):
    def __init__(self, path, **kw):
        super().__init__(path, pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=1.8 * cm,
                         bottomMargin=2 * cm, title=f"{TITLE} : exercices corrigés", subject=LEVEL, invariant=1, **kw)
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=self.footer)])
        self.corr_page = None

    def footer(self, canv, doc):
        canv.saveState()
        canv.setFont("DV", 8)
        canv.setFillColor(GREY)
        canv.drawString(self.leftMargin, 1.1 * cm, f"{TITLE} · {LEVEL}")
        canv.drawRightString(A4[0] - self.rightMargin, 1.1 * cm, str(doc.page))
        canv.restoreState()

    def afterFlowable(self, f):
        if getattr(f, "_corr", False):
            self.corr_page = self.page


def story(corr_page):
    EX, CO = content()
    out = [P(TITLE, "title"), P(f"{LEVEL}. Cinq exercices type bac et leurs corrigés.", "sub"),
           P(f"Environ 20 minutes par exercice. Calculatrice autorisée. Corrigés à partir de la page {corr_page}.",
             "intro")]
    for i, ex in enumerate(EX):
        if i:
            out.append(PageBreak())
        out += ex
    out.append(PageBreak())
    h = P("Corrigés", "title")
    h._corr = True
    out += [h, P("Les résultats sont donnés avec la précision demandée par l'énoncé. Une méthode correcte qui "
                 "aboutit à un arrondi légèrement différent est juste.", "intro")]
    for i, co in enumerate(CO):
        if i:
            out.append(PageBreak())
        out += co
    return out


first = Doc(io.BytesIO())
first.build(story("?"))
Doc(OUT).build(story(first.corr_page))
print("corrigés page", first.corr_page)
