# Builds the PDF of the same name next to this file:
#   uv run --with reportlab --with matplotlib --with rdkit python exercices/physique-chimie/dosages-spectres-ir-serie-2.py
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
TITLE = "Dosages par étalonnage et spectres IR (série 2)"
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


def dye_spectra():
    lam = np.linspace(380, 750, 800)
    e102 = 0.55 * gauss(lam, 427, 35)
    e131 = 0.62 * gauss(lam, 638, 24) + 0.16 * gauss(lam, 595, 20) + 0.06 * gauss(lam, 410, 25)
    fig, ax = plt.subplots(figsize=(3.8, 2.2))
    ax.plot(lam, e102, color="#c79a00", lw=1.3)
    ax.plot(lam, e131, color="#1f4fa3", lw=1.3)
    ax.text(452, 0.56, "Tartrazine\nE102", va="top", fontsize=7.5, color="#9a7600")
    ax.text(662, 0.62, "Bleu\npatenté V\nE131", fontsize=7.5, color="#1f4fa3", va="top")
    ax.set_xlim(380, 750)
    ax.set_ylim(0, 0.7)
    ax.set_xlabel("λ (nm)", fontsize=8)
    ax.set_ylabel("Absorbance A", fontsize=8)
    graph_style(ax)
    return fig


def caffeine_uv():
    lam = np.linspace(230, 400, 600)
    fig, ax = plt.subplots(figsize=(4.4, 2.6))
    ax.plot(lam, 0.502 * gauss(lam, 273, 13) + 0.95 * gauss(lam, 205, 14), color=PINK_HEX, lw=1.3)
    ax.set_xlim(230, 400)
    ax.set_ylim(0, 0.6)
    ax.set_xlabel("λ (nm)", fontsize=8)
    ax.set_ylabel("Absorbance A", fontsize=8)
    graph_style(ax)
    return fig


def skeletal(smiles):
    d = rdMolDraw2D.MolDraw2DCairo(560, 360)
    o = d.drawOptions()
    o.useBWAtomPalette()
    o.bondLineWidth = 2
    o.minFontSize = 30
    o.padding = 0.12
    d.DrawMolecule(Chem.MolFromSmiles(smiles))
    d.FinishDrawing()
    return io.BytesIO(d.GetDrawingText())


BUTANONE = [(2982, .38, 10), (2940, .25, 9), (2885, .15, 8), (1716, .93, 9), (1460, .35, 8), (1415, .42, 7),
            (1365, .55, 7), (1172, .62, 9), (1088, .25, 7), (945, .22, 7), (760, .2, 7)]
BUTENOL = [(3340, .78, 110), (3080, .35, 10), (2940, .45, 15), (2880, .3, 10), (1642, .45, 8), (1430, .35, 9),
           (1050, .75, 12), (992, .55, 7), (915, .7, 7)]
CAFFEINE = [(3105, .3, 12), (2955, .2, 12), (1700, .9, 9), (1658, .92, 10), (1600, .35, 8), (1550, .6, 8),
            (1485, .4, 7), (1455, .35, 7), (1360, .4, 7), (1240, .5, 8), (1025, .3, 7), (975, .25, 7), (745, .45, 7)]

IR_TABLE = [
    ["<b>Liaison</b>", "<b>Nombre d'onde (cm<super>−1</super>)</b>", "<b>Allure de la bande</b>"],
    ["O–H d'un alcool (liaisons hydrogène)", "3200 – 3400", "forte, large"],
    ["O–H d'un acide carboxylique", "2500 – 3200", "forte, très large"],
    ["N–H d'une amine ou d'un amide", "3100 – 3500", "moyenne"],
    ["C–H d'un carbone engagé dans une double liaison", "3000 – 3100", "moyenne"],
    ["C–H d'un carbone tétraédrique", "2800 – 3000", "moyenne à forte"],
    ["C–H du groupe –CHO d'un aldéhyde", "2700 – 2850", "moyenne, souvent deux bandes"],
    ["C=O d'un ester", "1735 – 1750", "forte, fine"],
    ["C=O d'un aldéhyde", "1720 – 1740", "forte, fine"],
    ["C=O d'une cétone", "1705 – 1725", "forte, fine"],
    ["C=O d'un acide carboxylique", "1700 – 1725", "forte, fine"],
    ["C=O d'un amide", "1650 – 1700", "forte"],
    ["C=C", "1620 – 1680", "moyenne"],
    ["C–O", "1050 – 1300", "forte"],
]

MGL = "mg·L<super>−1</super>"
GL = "g·L<super>−1</super>"
CM1 = "cm<super>−1</super>"


def content():
    # ---------------------------------------------------------------- numbers
    k1 = 0.183                                   # L/mg, exercise 1
    assert abs(0.302 / k1 - 1.65) < 0.005
    a2 = 11.90 + 2 * 7.63                        # mS m2/mol, CaCl2
    g2 = a2 * 1.0e-2 * 1000                      # µS per mmol/L for s/L = 1.0e-2 m
    c1 = 451 / 272
    assert round(a2, 2) == 27.16 and round(g2) == 272 and round(c1, 2) == 1.66
    assert round(c1 * 10e-3 * 111, 2) == 1.84 and round(1.84 / 2.00, 2) == 0.92
    cm3 = np.array([0, 25, 50, 75, 100, 125.0])
    rho3 = np.array([49.91, 50.40, 50.87, 51.35, 51.84, 52.31]) / 0.0500
    b3, rho0 = np.polyfit(cm3, rho3, 1)
    assert round(rho0, 1) == 998.3 and round(b3, 3) == 0.384 and round((1028.0 - rho0) / b3) == 77
    k5 = 0.0502                                  # L/mg, exercise 5
    assert round(0.322 / k5, 2) == 6.41 and round(50 * 0.322 / k5) == 321 and round(k5 * 194e3) == 9739
    e4 = 6.63e-34 * 3.00e8 * 1715e2
    assert round(e4 * 1e20, 2) == 3.41 and round(e4 / 1.60e-19, 3) == 0.213

    # ---------------------------------------------------------------- statements

    EX = []

    EX.append(heading("Exercice 1. Le bleu patenté d'un sirop de menthe",
                      "Spectrophotométrie, mélange de colorants et dose journalière admissible") + [
        P("Un sirop de menthe doit sa couleur verte à deux colorants : la tartrazine E102 et le bleu patenté V E131. "
          "On veut doser le bleu patenté et comparer sa teneur à la dose journalière admissible (DJA)."),
        P("On prépare cinq solutions étalons de bleu patenté et on mesure leur absorbance à 640 nm, dans des cuves "
          "identiques. On dilue ensuite 10 fois le sirop : la solution S obtenue a une absorbance "
          "A<sub>S</sub> = 0,302 dans les mêmes conditions."),
        table([["Solution", "E<sub>1</sub>", "E<sub>2</sub>", "E<sub>3</sub>", "E<sub>4</sub>", "E<sub>5</sub>"],
               [f"C<sub>m</sub> ({MGL})", "0,50", "1,00", "1,50", "2,00", "2,50"],
               ["Absorbance A à 640 nm", "0,092", "0,183", "0,275", "0,366", "0,458"]], 4.6 * cm, 2.2 * cm),
        side_by_side([img(png(dye_spectra()), 6.6 * cm),
                      P("Figure 1. Spectres d'absorption de la tartrazine et du bleu patenté.", "cap")],
                     [donnees(["Couleurs complémentaires : violet-bleu et jaune ; orange-rouge et bleu.",
                               "DJA du bleu patenté V : 5 mg par kilogramme de masse corporelle et par jour.",
                               "Verrerie disponible : pipettes jaugées de 5,0 mL, 10,0 mL et 20,0 mL ; fioles "
                               "jaugées de 50,0 mL, 100,0 mL et 200,0 mL."], 9.4 * cm)],
                     widths=[7.2 * cm, 9.4 * cm]),
        Q(1, "À l'aide de la figure 1, expliquer la couleur de chaque colorant, puis celle du sirop."),
        Q(2, "Pourquoi mesure-t-on l'absorbance à 640 nm plutôt qu'à 430 nm ?"),
        Q(3, "Montrer que les mesures sont en accord avec la loi de Beer-Lambert, puis déterminer le coefficient k "
             "tel que A = k·C<sub>m</sub>."),
        Q(4, "Pourquoi faut-il diluer le sirop avant la mesure ? Choisir la verrerie pour le diluer 10 fois."),
        Q(5, "Déterminer la concentration en masse de bleu patenté dans S, puis dans le sirop."),
        Q(6, "Un verre de menthe à l'eau contient 20 mL de sirop. Combien de verres une personne de 60 kg "
             "devrait-elle boire en une journée pour atteindre la DJA du bleu patenté ? Conclure."),
        Q(7, "Pourquoi ne peut-on pas doser la tartrazine en reportant l'absorbance à 430 nm du sirop dilué sur une "
             "droite d'étalonnage de la tartrazine seule ? Proposer une démarche."),
    ])

    EX.append(heading("Exercice 2. Les pastilles d'un absorbeur d'humidité",
                      "Conductance, loi de Kohlrausch et pureté d'un solide ionique") + [
        P("Les absorbeurs d'humidité contiennent des pastilles de chlorure de calcium anhydre CaCl<sub>2</sub>(s), un "
          "solide ionique qui capte la vapeur d'eau de l'air. L'emballage indique « chlorure de calcium : 96 % "
          "minimum ». On veut contrôler la composition d'une pastille prélevée dans un absorbeur qui fonctionne "
          "depuis plusieurs jours."),
        P("On broie la pastille, on en pèse m = 2,00 g et on dissout cet échantillon dans de l'eau distillée, dans une "
          "fiole jaugée de 1000,0 mL : on obtient la solution S<sub>0</sub>. On dilue ensuite 10 fois S<sub>0</sub> : "
          "on obtient la solution S<sub>1</sub>."),
        P("On mesure la conductance G de solutions étalons de chlorure de calcium, puis celle de S<sub>1</sub>, avec "
          "la même cellule et à la même température, 25 °C. Pour S<sub>1</sub>, on mesure G<sub>1</sub> = 451 µS."),
        table([["Solution", "E<sub>1</sub>", "E<sub>2</sub>", "E<sub>3</sub>", "E<sub>4</sub>", "E<sub>5</sub>"],
               ["c (mmol·L<super>−1</super>)", "0,50", "1,00", "1,50", "2,00", "2,50"],
               ["G (µS)", "136", "271", "408", "542", "680"]], 4.6 * cm, 2.2 * cm),
        donnees(["M(CaCl<sub>2</sub>) = 111 g·mol<super>−1</super>.",
                 "Conductivités molaires ioniques λ à 25 °C, en mS·m<super>2</super>·mol<super>−1</super> : "
                 "Ca<super>2+</super> 11,90 ; Cl<super>−</super> 7,63.",
                 "La loi de Kohlrausch s'applique aux solutions diluées, de concentration inférieure à "
                 "10<super>−2</super> mol·L<super>−1</super> environ. Les concentrations s'y expriment en "
                 "mol·m<super>−3</super> ; 1 mmol·L<super>−1</super> = 1 mol·m<super>−3</super>.",
                 "La conductance d'une solution placée entre deux plaques parallèles d'aire s, séparées d'une distance "
                 "L, vaut G = σ·s / L. Pour la cellule utilisée : s = 1,0 cm<super>2</super> et L = 1,0 cm.",
                 "Verrerie disponible : pipettes jaugées de 5,0 mL, 10,0 mL et 20,0 mL ; fioles jaugées de 50,0 mL, "
                 "100,0 mL et 250,0 mL."]),
        Q(1, "Écrire l'équation de la dissolution du chlorure de calcium dans l'eau. Exprimer les concentrations "
             "[Ca<super>2+</super>] et [Cl<super>−</super>] en fonction de la concentration c en soluté apporté."),
        Q(2, "Écrire la loi de Kohlrausch pour une solution de chlorure de calcium, puis montrer que σ = a·c, où a est "
             "un coefficient que l'on calculera."),
        Q(3, "Montrer que, pour la cellule utilisée, la conductance est proportionnelle à c. Calculer la valeur "
             "attendue du coefficient de proportionnalité, en µS par mmol·L<super>−1</super>, et la comparer aux "
             "mesures."),
        Q(4, "Calculer la concentration qu'aurait S<sub>0</sub> si la pastille était du chlorure de calcium pur. "
             "Expliquer pourquoi on mesure la conductance de S<sub>1</sub> plutôt que celle de S<sub>0</sub>, et "
             "décrire la préparation de S<sub>1</sub>."),
        Q(5, "Déterminer la concentration de S<sub>1</sub>, puis celle de S<sub>0</sub>. En déduire la masse de "
             "chlorure de calcium contenue dans l'échantillon, puis son pourcentage en masse dans la pastille."),
        Q(6, "Le résultat est inférieur à l'indication de l'emballage. Proposer une explication."),
        Q(7, "Pourquoi faut-il préparer les solutions et rincer la cellule avec de l'eau distillée, et non avec l'eau "
             "du robinet ?"),
    ])

    EX.append(heading("Exercice 3. Le sucre d'une limonade",
                      "Masse volumique, densité, titre massique et étalonnage") + [
        P("La masse volumique d'une boisson augmente avec la quantité de sucre dissous : sa mesure permet donc un "
          "dosage par étalonnage. L'étiquette d'une limonade indique « sucres : 7,8 g pour 100 mL ». On assimile les "
          "sucres de la limonade à du saccharose et on admet que sa masse volumique ne dépend que de sa teneur en "
          "sucres."),
        P("On prépare six solutions étalons de saccharose. Pour chacune, on prélève 50,0 mL à la pipette jaugée et on "
          "pèse ce prélèvement sur une balance au centième de gramme. Toutes les mesures sont faites à 20 °C. On "
          "procède de même avec la limonade, préalablement dégazée : 50,0 mL de limonade ont une masse de 51,40 g."),
        table([["Solution", "E<sub>0</sub>", "E<sub>1</sub>", "E<sub>2</sub>", "E<sub>3</sub>", "E<sub>4</sub>",
                "E<sub>5</sub>"],
               [f"C<sub>m</sub> ({GL})", "0", "25,0", "50,0", "75,0", "100,0", "125,0"],
               ["Masse de 50,0 mL (g)", "49,91", "50,40", "50,87", "51,35", "51,84", "52,31"]], 4.4 * cm, 1.9 * cm),
        donnees([f"La densité d'une solution est d = ρ / ρ<sub>réf</sub>, avec ρ<sub>réf</sub> = 1000 {GL}.",
                 "M(saccharose) = 342 g·mol<super>−1</super>.",
                 "Une canette contient 33 cL de boisson ; un morceau de sucre a une masse d'environ 6 g."]),
        Q(1, f"Calculer la masse volumique ρ de chaque solution étalon, en {GL}. Pourquoi prélève-t-on les 50,0 mL "
             "avec une pipette jaugée ?"),
        Q(2, "Montrer que la masse volumique est une fonction affine de la concentration en masse : "
             "ρ = ρ<sub>0</sub> + b·C<sub>m</sub>. Déterminer ρ<sub>0</sub> et b. Que représente ρ<sub>0</sub> ? "
             "Pourquoi ρ n'est-elle pas proportionnelle à C<sub>m</sub> ?"),
        Q(3, "Pourquoi faut-il dégazer la limonade avant la mesure ?"),
        Q(4, "Déterminer la concentration en masse de sucres de la limonade, puis sa concentration en quantité de "
             "matière. Comparer à l'étiquette."),
        Q(5, "Calculer la densité de la limonade, puis son titre massique en sucres."),
        Q(6, "À combien de morceaux de sucre correspond le sucre contenu dans une canette ?"),
        Q(7, f"Une limonade « zéro sucre » contient 0,20 {GL} d'édulcorant. On admet que sa masse volumique varie "
             "avec la concentration en édulcorant comme avec celle du saccharose. Peut-on doser l'édulcorant par "
             "cette méthode ? Justifier."),
    ])

    EX.append(heading("Exercice 4. Deux flacons sans étiquette",
                      "Isomères, groupes caractéristiques et spectroscopie infrarouge") + [
        P("Deux flacons X et Y ont perdu leur étiquette. On sait seulement que chacun contient l'une des quatre "
          "espèces A à D ci-dessous, à l'état pur. On enregistre le spectre infrarouge du contenu de chaque flacon "
          "(figure 2)."),
        table([["Espèce", "Formule semi-développée"],
               ["A", "CH<sub>3</sub>–CH<sub>2</sub>–CH<sub>2</sub>–CHO"],
               ["B", "CH<sub>3</sub>–CO–CH<sub>2</sub>–CH<sub>3</sub>"],
               ["C", "CH<sub>2</sub>=CH–CH<sub>2</sub>–CH<sub>2</sub>–OH"],
               ["D", "CH<sub>3</sub>–CH(CH<sub>3</sub>)–CHO"]], 2.4 * cm, 6.4 * cm),
        figure(flasks(), 16.4 * cm, "Figure 2. Spectres infrarouges du contenu des flacons X et Y."),
        KeepTogether([table(IR_TABLE, 7.4 * cm, 4.4 * cm),
                      P("Tableau. Bandes d'absorption infrarouge de quelques liaisons.", "cap")]),
        donnees(["h = 6,63 × 10<super>−34</super> J·s ; c = 3,00 × 10<super>8</super> m·s<super>−1</super> ; "
                 "1 eV = 1,60 × 10<super>−19</super> J."]),
        Q(1, "Vérifier que les quatre espèces ont la même formule brute. Comment qualifie-t-on de telles espèces ?"),
        Q(2, "Pour chaque espèce, identifier le ou les groupes caractéristiques et la famille de composés."),
        Q(3, "Associer les noms butanal, butanone et but-3-én-1-ol à trois des espèces. Justifier le nom "
             "2-méthylpropanal de la quatrième."),
        Q(4, "Identifier l'espèce contenue dans le flacon Y, en justifiant à l'aide du tableau."),
        Q(5, "Montrer que le flacon X contient une espèce possédant une liaison C=O. Expliquer pourquoi il ne peut "
             "s'agir ni de A ni de D, et conclure."),
        Q(6, "Quelles bandes caractéristiques s'attend-on à observer sur le spectre de l'espèce D ?"),
        Q(7, f"Calculer l'énergie, en joules puis en électronvolts, d'un photon de nombre d'onde σ = 1715 {CM1}, "
             "absorbé par la liaison C=O. La comparer à celle d'un photon de lumière visible de longueur d'onde "
             "500 nm."),
    ])

    EX.append(heading("Exercice 5. La caféine d'une boisson énergisante",
                      "Spectroscopie UV-visible, dosage par étalonnage et spectre infrarouge") + [
        P("Une canette de 250 mL de boisson énergisante porte l'indication « caféine : 32 mg pour 100 mL ». La "
          "caféine (figure 3) absorbe dans l'ultraviolet ; son spectre d'absorption est donné figure 4."),
        P("On prépare cinq solutions étalons de caféine et on mesure leur absorbance à 273 nm, dans des cuves en "
          "quartz de largeur ℓ = 1,00 cm. On dilue 50 fois la boisson dégazée : la solution obtenue, notée S, a une "
          "absorbance A<sub>S</sub> = 0,322 dans les mêmes conditions. On admet qu'à 273 nm, seule la caféine "
          "absorbe dans la solution S."),
        table([["Solution", "E<sub>1</sub>", "E<sub>2</sub>", "E<sub>3</sub>", "E<sub>4</sub>", "E<sub>5</sub>"],
               [f"C<sub>m</sub> ({MGL})", "2,0", "4,0", "6,0", "8,0", "10,0"],
               ["Absorbance A à 273 nm", "0,101", "0,200", "0,302", "0,401", "0,502"]], 4.6 * cm, 2.2 * cm),
        side_by_side([img(skeletal("Cn1cnc2c1c(=O)n(C)c(=O)n2C"), 5.2 * cm),
                      P("Figure 3. Formule topologique de la caféine.", "cap")],
                     [img(png(caffeine_uv()), 7.6 * cm),
                      P(f"Figure 4. Spectre d'absorption d'une solution de caféine à 10 {MGL}.", "cap")]),
        donnees(["Masses molaires atomiques, en g·mol<super>−1</super> : H 1,0 ; C 12,0 ; N 14,0 ; O 16,0.",
                 "Le domaine visible s'étend de 400 nm à 800 nm environ. Le verre et le polystyrène absorbent les "
                 "rayonnements de longueur d'onde inférieure à 340 nm environ ; le quartz est transparent au-delà de "
                 "190 nm.",
                 "Apport maximal de caféine recommandé pour un adolescent : 3 mg par kilogramme de masse corporelle "
                 "et par jour.",
                 "Verrerie disponible : pipettes jaugées de 2,0 mL, 5,0 mL et 10,0 mL ; fioles jaugées de 100,0 mL, "
                 "250,0 mL et 500,0 mL.",
                 "Pour la question 8, on utilisera le tableau des bandes d'absorption de l'exercice 4."]),
        Q(1, "La caféine est-elle colorée ? Justifier à l'aide de la figure 4. Pourquoi mesure-t-on l'absorbance à "
             "273 nm, et pourquoi dans une cuve en quartz ?"),
        Q(2, "Montrer que les mesures sont en accord avec la loi de Beer-Lambert, puis déterminer le coefficient k tel "
             "que A = k·C<sub>m</sub>, en L·mg<super>−1</super>."),
        Q(3, "Déterminer la formule brute de la caféine à partir de sa formule topologique, puis calculer sa masse "
             "molaire."),
        Q(4, "En déduire le coefficient d'absorption molaire ε de la caféine à 273 nm."),
        Q(5, "Proposer deux façons de diluer 50 fois la boisson avec la verrerie disponible. Laquelle est la plus "
             "précise ?"),
        Q(6, "Déterminer la concentration en masse de caféine dans la boisson. Comparer à l'étiquette."),
        Q(7, "Un adolescent de 55 kg peut-il boire deux canettes dans la journée sans dépasser l'apport maximal "
             "recommandé ?"),
        Q(8, "Repérer les groupes caractéristiques de la caféine. Le spectre infrarouge de la caféine est donné "
             "ci-dessous : justifier les bandes présentes et les bandes absentes."),
        figure(caffeine_ir(), 9.5 * cm, "Figure 5. Spectre infrarouge de la caféine."),
    ])

    # ---------------------------------------------------------------- corrections

    CO = []

    CO.append(heading("Corrigé de l'exercice 1",
                      "Spectrophotométrie, mélange de colorants et dose journalière admissible") + [
        Q(1, "La tartrazine absorbe surtout vers 430 nm, dans le violet-bleu : elle a la couleur complémentaire, le "
             "jaune. Le bleu patenté absorbe surtout vers 640 nm, dans l'orange-rouge : il apparaît bleu. Le sirop "
             "absorbe à la fois le violet-bleu et l'orange-rouge ; entre 500 et 560 nm environ, les deux colorants "
             "absorbent peu : le sirop transmet surtout le vert, d'où sa couleur."),
        Q(2, "À 640 nm, seul le bleu patenté absorbe (la tartrazine n'absorbe plus au-delà de 520 nm environ), et "
             "c'est son maximum d'absorption, où la mesure est la plus sensible. À 430 nm, les deux colorants "
             "absorbent et leurs absorbances s'ajoutent."),
        Q(3, "Les quotients A / C<sub>m</sub> valent 0,184 ; 0,183 ; 0,183 ; 0,183 ; 0,183 L·mg<super>−1</super> : "
             "constants à 1 % près, les points s'alignent sur une droite passant par l'origine. C'est la loi de "
             "Beer-Lambert, avec k = 0,183 L·mg<super>−1</super>."),
        figure(calibration([0.5, 1.0, 1.5, 2.0, 2.5], [0.092, 0.183, 0.275, 0.366, 0.458], k1, 0.302, "Solution S",
                           "C$_m$ (mg·L$^{-1}$)", "Absorbance A", 3.0, (0, 0.55)),
               5.8 * cm, "Droite d'étalonnage et lecture de la concentration de la solution S."),
        Q(4, "Sans dilution, l'absorbance du sirop serait voisine de 10 × 0,302 ≈ 3,0, très au-dessus de celle de "
             "l'étalon le plus concentré (0,458) : hors du domaine où la proportionnalité a été vérifiée, et la loi "
             "de Beer-Lambert ne s'applique qu'aux solutions diluées."),
        QC("Le facteur de dilution est le rapport du volume de la fiole au volume de la pipette : prélever 10,0 mL de "
           "sirop à la pipette jaugée, les verser dans une fiole jaugée de 100,0 mL, compléter à l'eau distillée "
           "jusqu'au trait de jauge et homogénéiser (5,0 mL / 50,0 mL ou 20,0 mL / 200,0 mL conviennent aussi)."),
        Q(5, f"C<sub>S</sub> = A<sub>S</sub> / k = 0,302 / 0,183 = 1,65 {MGL} (lecture graphique : entre 1,6 et 1,7 "
             f"{MGL}). Le sirop est 10 fois plus concentré : C<sub>sirop</sub> = 16,5 {MGL}."),
        Q(6, "DJA pour 60 kg : 5 × 60 = 300 mg par jour ; un verre apporte 16,5 × 0,020 = 0,33 mg de bleu patenté. "
             "Il faudrait 300 / 0,33 ≈ 9 × 10<super>2</super> verres par jour (environ 18 L de sirop) : une "
             "consommation normale reste très loin de la DJA."),
        Q(7, "À 430 nm, les deux colorants absorbent et A = A<sub>tartrazine</sub> + A<sub>bleu</sub> : la droite de "
             "la tartrazine seule surestimerait sa concentration. Démarche : avec la concentration de bleu patenté "
             "trouvée à 640 nm et sa droite d'étalonnage à 430 nm, calculer sa contribution à 430 nm, la soustraire "
             "de l'absorbance mesurée, puis lire la concentration de tartrazine sur sa propre droite à 430 nm."),
    ])

    CO.append(heading("Corrigé de l'exercice 2", "Conductance, loi de Kohlrausch et pureté d'un solide ionique") + [
        Q(1, "CaCl<sub>2</sub>(s) → Ca<super>2+</super>(aq) + 2 Cl<super>−</super>(aq). Chaque unité "
             "CaCl<sub>2</sub> libère un ion calcium et deux ions chlorure : [Ca<super>2+</super>] = c et "
             "[Cl<super>−</super>] = 2c."),
        Q(2, "σ = λ(Ca<super>2+</super>)·[Ca<super>2+</super>] + λ(Cl<super>−</super>)·[Cl<super>−</super>] = "
             "(λ(Ca<super>2+</super>) + 2 λ(Cl<super>−</super>))·c. Donc σ = a·c avec a = 11,90 + 2 × 7,63 = "
             "27,16 mS·m<super>2</super>·mol<super>−1</super>. Le facteur 2 porte sur l'ion chlorure, présent deux "
             "fois : l'oublier donne a = 19,53."),
        Q(3, "G = σ·s / L = a·(s / L)·c : pour une cellule donnée, s / L est constant, donc G est proportionnelle à "
             "c. Ici s / L = 1,0 × 10<super>−4</super> m<super>2</super> / 1,0 × 10<super>−2</super> m = "
             "1,0 × 10<super>−2</super> m."),
        QC("Pour c = 1 mmol·L<super>−1</super> = 1 mol·m<super>−3</super> : G = 27,16 × 1,0 × 10<super>−2</super> × 1 "
           "= 0,2716 mS, soit 272 µS. Le coefficient attendu vaut donc 272 µS par mmol·L<super>−1</super>."),
        QC("Les quotients G / c mesurés valent 272 ; 271 ; 272 ; 271 ; 272 µS par mmol·L<super>−1</super> : ils "
           "sont en accord avec la loi de Kohlrausch."),
        figure(calibration([0.5, 1.0, 1.5, 2.0, 2.5], [136, 271, 408, 542, 680], g2, 451, "Solution S$_1$",
                           "c (mmol·L$^{-1}$)", "G (µS)", 3.0, (0, 800)),
               5.8 * cm, "Droite d'étalonnage et lecture de la concentration de la solution S<sub>1</sub>."),
        Q(4, "Pastille pure : n = m / M = 2,00 / 111 = 1,80 × 10<super>−2</super> mol dans 1,000 L, soit "
             "c<sub>0</sub> = 18,0 mmol·L<super>−1</super>."),
        QC("Cette concentration dépasse 10<super>−2</super> mol·L<super>−1</super> : la loi de Kohlrausch ne "
           "s'applique plus et G ne serait plus proportionnelle à c. Elle est aussi très au-dessus du domaine des "
           "étalons (0,50 à 2,50 mmol·L<super>−1</super>). Diluée 10 fois, la solution tombe dans ce domaine."),
        QC("Préparation de S<sub>1</sub> : prélever 10,0 mL de S<sub>0</sub> avec une pipette jaugée, les verser "
           "dans une fiole jaugée de 100,0 mL, compléter à l'eau distillée jusqu'au trait de jauge, boucher et "
           "homogénéiser (ou 5,0 mL dans une fiole de 50,0 mL)."),
        Q(5, "c<sub>1</sub> = G<sub>1</sub> / 272 = 451 / 272 = 1,66 mmol·L<super>−1</super> (lecture graphique : "
             "entre 1,6 et 1,7 mmol·L<super>−1</super>). Donc c<sub>0</sub> = 10 × c<sub>1</sub> = "
             "16,6 mmol·L<super>−1</super> = 1,66 × 10<super>−2</super> mol·L<super>−1</super>."),
        QC("Masse de chlorure de calcium dans l'échantillon : m<sub>CaCl2</sub> = c<sub>0</sub> × V × M = "
           "1,66 × 10<super>−2</super> × 1,000 × 111 = 1,84 g."),
        QC("Pourcentage en masse : 1,84 / 2,00 = 0,92, soit 92 %."),
        Q(6, "Le chlorure de calcium a capté de la vapeur d'eau pendant le fonctionnement de l'absorbeur : c'est son "
             "rôle. L'échantillon de 2,00 g contient donc de l'eau en plus du chlorure de calcium, ce qui abaisse la "
             "part en masse de CaCl<sub>2</sub>. Le pourcentage de l'emballage concerne les pastilles neuves."),
        Q(7, "L'eau du robinet contient des ions (calcium, magnésium, hydrogénocarbonate, etc.) : sa conductivité, "
             "quelques dizaines de mS·m<super>−1</super>, est du même ordre que celle des solutions étudiées et "
             "fausserait toutes les mesures. L'eau distillée ne contient presque pas d'ions."),
    ])

    CO.append(heading("Corrigé de l'exercice 3", "Masse volumique, densité, titre massique et étalonnage") + [
        Q(1, f"ρ = m / V avec V = 50,0 mL = 0,0500 L. Pour E<sub>0</sub> : ρ = 49,91 / 0,0500 = 998,2 {GL}. "
             f"De même : 1008,0 ; 1017,4 ; 1027,0 ; 1036,8 ; 1046,2 {GL}."),
        QC("La pipette jaugée délivre un volume connu avec précision : l'incertitude sur ρ vient alors surtout de la "
           "pesée."),
        Q(2, f"Chaque ajout de 25,0 {GL} de saccharose augmente ρ d'environ 9,6 {GL} : les points sont alignés sur "
             f"une droite qui ne passe pas par l'origine. Par régression linéaire : ρ<sub>0</sub> = 998 {GL} et "
             "b = 0,384."),
        QC("ρ<sub>0</sub> est la masse volumique de la solution sans sucre, c'est-à-dire de l'eau à 20 °C. Même sans "
           "soluté, un litre de solution a une masse : ρ ne peut donc pas être proportionnelle à C<sub>m</sub>, "
           "contrairement à l'absorbance ou à la conductivité, qui sont nulles en l'absence de l'espèce dosée."),
        QC("Remarque : b = 0,384 signifie que dissoudre 1 g de saccharose par litre n'augmente la masse d'un litre de "
           "solution que de 0,384 g. Le sucre dissous occupe un volume et prend la place d'une partie de l'eau."),
        figure(calibration(list(cm3), list(rho3), b3, 1028.0, "Limonade", "C$_m$ (g·L$^{-1}$)", "ρ (g·L$^{-1}$)",
                           140, (995, 1050), intercept=rho0),
               5.8 * cm, "Droite d'étalonnage et lecture de la concentration en sucres de la limonade."),
        Q(3, "La limonade contient du dioxyde de carbone dissous qui forme des bulles. Dans la pipette, les bulles "
             "occupent une partie des 50,0 mL : la masse de liquide prélevée serait trop faible, et la masse "
             "volumique sous-estimée."),
        Q(4, f"ρ<sub>limonade</sub> = 51,40 / 0,0500 = 1028,0 {GL}, donc C<sub>m</sub> = (1028,0 − 998,3) / 0,384 = "
             f"77 {GL} (lecture graphique : entre 76 et 79 {GL})."),
        QC("En quantité de matière : c = C<sub>m</sub> / M = 77 / 342 = 0,225 mol·L<super>−1</super>."),
        QC(f"L'étiquette indique 7,8 g pour 100 mL, soit 78 {GL} : l'écart est d'environ 1 %, l'indication est "
           "vérifiée."),
        Q(5, "d = ρ / ρ<sub>réf</sub> = 1028,0 / 1000 = 1,028. Titre massique : w = C<sub>m</sub> / ρ = 77 / 1028 = "
             "0,075, soit 7,5 %. Diviser par 1000 au lieu de ρ donnerait 7,7 % : le titre massique rapporte la masse "
             "de soluté à la masse de la solution, pas à son volume."),
        Q(6, "Masse de sucres dans 33 cL : 77 × 0,330 = 25 g, soit 25 / 6 ≈ 4 morceaux de sucre."),
        Q(7, f"D'après la relation obtenue, 0,20 {GL} d'édulcorant augmenterait ρ de 0,384 × 0,20 ≈ 0,077 {GL}. "
             "Sur 50,0 mL, la masse augmenterait de 0,077 × 0,0500 ≈ 0,004 g, ce qui est inférieur au centième de "
             "gramme que la balance peut détecter. La méthode n'est pas assez sensible : on ne peut pas doser "
             "l'édulcorant ainsi."),
    ])

    CO.append(heading("Corrigé de l'exercice 4", "Isomères, groupes caractéristiques et spectroscopie infrarouge") + [
        Q(1, "Chaque espèce compte 4 atomes de carbone, 8 atomes d'hydrogène et 1 atome d'oxygène : formule brute "
             "C<sub>4</sub>H<sub>8</sub>O. Ces espèces ont la même formule brute mais des enchaînements d'atomes "
             "différents : ce sont des isomères de constitution."),
        Q(2, "Les réponses aux questions 2 et 3 sont regroupées dans le tableau ci-dessous."),
        table([["<b>Espèce</b>", "<b>Nom</b>", "<b>Groupe caractéristique</b>", "<b>Famille</b>"],
               ["A", "butanal", "carbonyle, en bout de chaîne (–CHO)", "aldéhyde"],
               ["B", "butanone", "carbonyle, sur un carbone lié à deux carbones", "cétone"],
               ["C", "but-3-én-1-ol", "hydroxyle –OH (et C=C)", "alcool"],
               ["D", "2-méthylpropanal", "carbonyle, en bout de chaîne (–CHO)", "aldéhyde"]], 2.0 * cm, 4.6 * cm),
        Q(3, "Pour D, la chaîne carbonée la plus longue qui contient le carbone du groupe –CHO compte 3 atomes de "
             "carbone : propanal. Le carbone du groupe –CHO porte le numéro 1 ; un groupe méthyle est fixé sur le "
             "carbone 2 : 2-méthylpropanal."),
        Q(4, f"Flacon Y : espèce C. Bande forte et large vers 3340 {CM1} (O–H d'un alcool), bande moyenne vers "
             f"3080 {CM1} (C–H d'un carbone engagé dans une double liaison), bande moyenne vers 1640 {CM1} (C=C), "
             f"bande forte vers 1050 {CM1} (C–O), et aucune bande C=O vers 1700 {CM1}."),
        Q(5, f"Le spectre de X présente une bande fine et intense à 1715 {CM1} : c'est une liaison C=O. Il ne présente "
             "aucune bande O–H : ce n'est pas C."),
        QC(f"Un aldéhyde présenterait une ou deux bandes entre 2700 et 2850 {CM1} (C–H du groupe –CHO) ; le spectre "
           f"de X n'en présente aucune : ses bandes C–H se situent entre 2880 et 2990 {CM1}. De plus, 1715 {CM1} est "
           "dans le domaine du C=O d'une cétone et en dehors de celui d'un aldéhyde. Ce n'est donc ni A ni D : le "
           "flacon X contient la butanone, B."),
        Q(6, f"Pour le 2-méthylpropanal, on attend une bande fine et intense entre 1720 et 1740 {CM1} (C=O d'un "
             f"aldéhyde), une ou deux bandes moyennes entre 2700 et 2850 {CM1} (C–H du groupe –CHO), les bandes C–H "
             f"entre 2800 et 3000 {CM1}, et aucune bande O–H."),
        Q(7, f"σ = 1715 {CM1} = 1,715 × 10<super>5</super> m<super>−1</super>. E = h·c / λ = h·c·σ = "
             "6,63 × 10<super>−34</super> × 3,00 × 10<super>8</super> × 1,715 × 10<super>5</super> = "
             "3,41 × 10<super>−20</super> J, soit 3,41 × 10<super>−20</super> / 1,60 × 10<super>−19</super> = "
             "0,213 eV. Garder σ en cm<super>−1</super> donnerait une énergie 100 fois trop petite."),
        QC("Photon visible à 500 nm : E = h·c / λ = 6,63 × 10<super>−34</super> × 3,00 × 10<super>8</super> / "
           "5,00 × 10<super>−7</super> = 3,98 × 10<super>−19</super> J, soit 2,49 eV. Le photon infrarouge est "
           "environ 12 fois moins énergétique : il suffit à faire vibrer une liaison, pas à modifier l'état "
           "électronique de la molécule."),
    ])

    CO.append(heading("Corrigé de l'exercice 5",
                      "Spectroscopie UV-visible, dosage par étalonnage et spectre infrarouge") + [
        Q(1, "La caféine n'absorbe qu'en dessous de 310 nm environ, dans l'ultraviolet : elle n'absorbe aucune "
             "radiation visible, donc elle est incolore."),
        QC("On mesure au maximum d'absorption, 273 nm, où la mesure est la plus sensible. Le verre et le polystyrène "
           "absorbent à cette longueur d'onde : ils fausseraient la mesure. Le quartz est transparent à 273 nm."),
        Q(2, "Les quotients A / C<sub>m</sub> valent 0,0505 ; 0,0500 ; 0,0503 ; 0,0501 ; 0,0502 "
             "L·mg<super>−1</super> : ils sont constants à 1 % près. L'absorbance est proportionnelle à la "
             "concentration : c'est la loi de Beer-Lambert, avec k = 5,02 × 10<super>−2</super> L·mg<super>−1</super>."),
        figure(calibration([2, 4, 6, 8, 10], [0.101, 0.200, 0.302, 0.401, 0.502], k5, 0.322, "Solution S",
                           "C$_m$ (mg·L$^{-1}$)", "Absorbance A", 12, (0, 0.6)),
               5.8 * cm, "Droite d'étalonnage et lecture de la concentration de la solution S."),
        Q(3, "Dans une formule topologique, chaque sommet ou extrémité non légendé représente un atome de carbone, et "
             "les atomes d'hydrogène liés aux carbones ne sont pas dessinés. La caféine compte 5 carbones dans les "
             "cycles et 3 carbones de groupes méthyle, 3 × 3 + 1 = 10 atomes d'hydrogène, 4 atomes d'azote et "
             "2 atomes d'oxygène : C<sub>8</sub>H<sub>10</sub>N<sub>4</sub>O<sub>2</sub>. "
             "M = 8 × 12,0 + 10 × 1,0 + 4 × 14,0 + 2 × 16,0 = 194 g·mol<super>−1</super>."),
        Q(4, "A = ε·ℓ·c avec c = C<sub>m</sub> / M, donc ε = k·M / ℓ. Avec k = 5,02 × 10<super>−2</super> "
             "L·mg<super>−1</super> = 50,2 L·g<super>−1</super> : ε = 50,2 × 194 / 1,00 = "
             "9,74 × 10<super>3</super> L·mol<super>−1</super>·cm<super>−1</super>. Oublier de convertir les "
             "milligrammes en grammes donne une valeur 1000 fois trop petite."),
        Q(5, "Le rapport du volume de la fiole à celui de la pipette doit valoir 50 : 2,0 mL dans une fiole de "
             "100,0 mL, 5,0 mL dans une fiole de 250,0 mL, ou 10,0 mL dans une fiole de 500,0 mL. La dernière est la "
             "plus précise : plus le volume mesuré est grand, plus l'incertitude relative de la verrerie jaugée est "
             "faible."),
        Q(6, f"C<sub>S</sub> = A<sub>S</sub> / k = 0,322 / 5,02 × 10<super>−2</super> = 6,41 {MGL} (lecture "
             f"graphique : entre 6,3 et 6,5 {MGL}). Boisson : C<sub>m</sub> = 50 × 6,41 = 321 {MGL}, soit 32,1 mg "
             "pour 100 mL. L'indication de l'étiquette est vérifiée."),
        Q(7, "Apport maximal : 3 × 55 = 165 mg par jour. Une canette contient 321 × 0,250 = 80 mg de caféine, deux "
             "canettes 160 mg. C'est juste en dessous de la limite : la moindre autre source de caféine dans la "
             "journée (café, thé, soda au cola) la ferait dépasser."),
        Q(8, "La caféine possède deux groupes carbonyle C=O, liés chacun à un atome d'azote : ce sont des groupes "
             f"amide. Bandes présentes : deux bandes fortes vers 1700 et 1660 {CM1} (C=O d'amide), et des bandes C–H "
             f"faibles vers 2950 {CM1} (groupes méthyle) et 3100 {CM1} (C–H du cycle, porté par un carbone engagé "
             "dans une double liaison). Bandes absentes : aucune bande O–H ni N–H, car aucun atome d'azote ne porte "
             "d'hydrogène et la molécule n'a pas de groupe hydroxyle."),
    ])
    return EX, CO


def flasks():
    fig, axs = plt.subplots(1, 2, figsize=(7.6, 2.6), sharey=True)
    ir(axs[0], BUTANONE, "Flacon X")
    ir(axs[1], BUTENOL, "Flacon Y", ylabel=False)
    fig.tight_layout()
    return fig


def caffeine_ir():
    fig, ax = plt.subplots(figsize=(4.6, 2.6))
    ir(ax, CAFFEINE, "Caféine")
    return fig


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
