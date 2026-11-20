# Builds the PDF of the same name next to this file:
#   uv run --with reportlab --with matplotlib python exercices/maths/probabilites-loi-binomiale-serie-1.py
import io
import re
import os
from math import comb

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle, XPreformatted)
from reportlab.platypus.flowables import HRFlowable

OUT = os.path.splitext(os.path.abspath(__file__))[0] + ".pdf"
TITLE = "Probabilités, espérance, variance et loi binomiale"
LEVEL = "Terminale spécialité maths"

NAVY = colors.HexColor("#1b2540")
PINK = colors.HexColor("#c2185b")
GREY = colors.HexColor("#5b6b8c")
BOX = colors.HexColor("#eef1f6")
LINE = colors.HexColor("#c9d1e0")
BLUE_HEX, PINK_HEX = "#3b6ea5", "#c2185b"

ttf = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
for name, file in [("DV", "DejaVuSans.ttf"), ("DV-B", "DejaVuSans-Bold.ttf"), ("DV-I", "DejaVuSans-Oblique.ttf"),
                   ("DV-BI", "DejaVuSans-BoldOblique.ttf"), ("DVM", "DejaVuSansMono.ttf")]:
    pdfmetrics.registerFont(TTFont(name, os.path.join(ttf, file)))
addMapping("DV", 0, 0, "DV")
addMapping("DV", 1, 0, "DV-B")
addMapping("DV", 0, 1, "DV-I")
addMapping("DV", 1, 1, "DV-BI")

plt.rcParams.update({"mathtext.fontset": "dejavusans", "mathtext.default": "regular", "font.size": 9,
                     "axes.edgecolor": "#5b6b8c", "axes.labelcolor": "#1b2540", "xtick.color": "#1b2540",
                     "ytick.color": "#1b2540"})

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

MB, TB = "M̅", "T̅"


NBSP = [(" ?", "\u00a0?"), (" :", "\u00a0:"), (" ;", "\u00a0;"), (" !", "\u00a0!"), ("« ", "«\u00a0"),
        (" »", "\u00a0»"), (" €", "\u00a0€"), (" %", "\u00a0%")]


def fr(text):
    text = re.sub(r"(ℬ\([^;()]+|\]0) ; ([^()\[]+[)\[])", "\\1\u00a0;\u00a0\\2", text)
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


def img(buf, width):
    from reportlab.lib.utils import ImageReader
    w, h = ImageReader(buf).getSize()
    buf.seek(0)
    im = Image(buf, width=width, height=width * h / w)
    im.hAlign = "CENTER"
    return im


def F(tex, size=11):
    """Display formula rendered with matplotlib mathtext, at true point size."""
    fig = plt.figure()
    fig.text(0, 0, f"${tex}$", fontsize=size, color="#1b2540")
    dpi = 300
    buf = png(fig, dpi=dpi)
    from reportlab.lib.utils import ImageReader
    w, h = ImageReader(buf).getSize()
    buf.seek(0)
    im = Image(buf, width=w * 72 / dpi, height=h * 72 / dpi)
    im.hAlign = "CENTER"
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
    ]))
    return KeepTogether([t, Spacer(1, 10)])


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


def tree(level1, level2, leaves=None):
    fig, ax = plt.subplots(figsize=(4.6, 2.5))
    ax.set_axis_off()
    ax.set_xlim(-0.15, 3.3 if leaves else 2.2)
    ax.set_ylim(-1.9, 1.9)
    nodes1 = [(1, 1), (1, -1)]
    for (lab, pr), (x, y) in zip(level1, nodes1):
        ax.plot([0.05, x - 0.1], [0, y * 0.95], color="#3b6ea5", lw=1)
        ax.text(x, y, f"${lab}$", ha="center", va="center", fontsize=11, color="#1b2540")
        ax.text(0.5, y * 0.5 + 0.08 * (1 if y > 0 else -1), f"${pr}$", ha="right" if y > 0 else "right",
                va="bottom" if y > 0 else "top", fontsize=9, color="#c2185b")
        for j, (lab2, pr2) in enumerate(level2[0 if y > 0 else 1]):
            y2 = y + (0.5 if j == 0 else -0.5)
            ax.plot([x + 0.12, 1.9], [y, y2], color="#3b6ea5", lw=1)
            ax.text(2.0, y2, f"${lab2}$", ha="center", va="center", fontsize=11, color="#1b2540")
            ax.text(1.5, (y + y2) / 2 + (0.07 if j == 0 else -0.07), f"${pr2}$", ha="center",
                    va="bottom" if j == 0 else "top", fontsize=9, color="#c2185b")
            if leaves:
                ax.text(2.2, y2, leaves[(0 if y > 0 else 2) + j], ha="left", va="center", fontsize=8.5,
                        color="#5b6b8c")
    ax.text(-0.02, 0, "", ha="right")
    return fig


def bars(ks, ps, highlight=None, xlabel="k", ylabel="P(X = k)", size=(5.2, 2.3)):
    fig, ax = plt.subplots(figsize=size)
    cols = [PINK_HEX if highlight and highlight(k) else BLUE_HEX for k in ks]
    ax.bar(ks, ps, width=0.6, color=cols)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.yaxis.set_major_formatter(FuncFormatter(comma))
    ax.grid(axis="y", color="#dfe4ee", lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return fig


pmf = lambda n, p, k: comb(n, k) * p ** k * (1 - p) ** (n - k)
cdf = lambda n, p, k: sum(pmf(n, p, i) for i in range(k + 1))
f4 = lambda x: f"{x:.4f}".replace(".", ",")

def content():
    # ---------------------------------------------------------------- statements

    EX = []

    EX.append(heading("Exercice 1. Un test de dépistage",
                      "Probabilités conditionnelles, arbre pondéré, formule des probabilités totales") + [
        P("Une maladie touche 2 % de la population d'un pays. Un laboratoire a mis au point un test de dépistage de "
          "cette maladie. Des études ont montré que :"),
        Paragraph("si une personne est malade, le test est positif dans 95 % des cas ;", S["bul"], bulletText="•"),
        Paragraph("si une personne n'est pas malade, le test est négatif dans 96 % des cas.", S["bul"],
                  bulletText="•"),
        Spacer(1, 6),
        P("On choisit une personne au hasard dans la population. On note M l'événement « la personne est malade » et "
          "T l'événement « le test de la personne est positif ». Pour tout événement A, on note A̅ son événement "
          "contraire. Les probabilités seront arrondies à 10<super>−3</super> si nécessaire."),
        P("Partie A. Dans la population générale", "part"),
        Q(1, "Représenter la situation par un arbre pondéré."),
        Q(2, "Calculer P(M ∩ T). Traduire ce résultat par une phrase."),
        Q(3, "Montrer que P(T) = 0,0582."),
        Q(4, "Le test d'une personne est positif. Quelle est la probabilité qu'elle soit malade ? Commenter ce "
             "résultat."),
        Q(5, "Les événements M et T sont-ils indépendants ? Pourquoi est-ce une bonne nouvelle pour le laboratoire ?"),
        P("Partie B. Dans une population à risque", "part"),
        P("Le test est maintenant utilisé dans une population où la proportion de malades est p, avec 0 &lt; p &lt; 1. "
          "Les caractéristiques du test sont inchangées."),
        Q(6, "Montrer que la probabilité qu'une personne dont le test est positif soit malade est :"),
        F(r"f(p) = \dfrac{95p}{91p + 4}"),
        Q(7, "Étudier le sens de variation de la fonction f sur ]0 ; 1[. Interpréter ce résultat."),
        Q(8, "Quelle doit être la proportion de malades dans la population testée pour que la probabilité qu'une "
             "personne positive soit malade atteigne au moins 0,9 ?"),
    ])

    EX.append(heading("Exercice 2. Le jeu de la fête foraine",
                      "Loi d'une variable aléatoire, espérance, variance, jeu équitable") + [
        P("Sur un stand de fête foraine, une urne contient 10 boules indiscernables au toucher : 2 rouges et "
          "8 blanches. Le joueur paie une mise de m euros, tire au hasard une boule, la garde, puis tire au hasard une "
          "seconde boule parmi les 9 restantes."),
        P("Il reçoit 40 € s'il obtient deux boules rouges, 5 € s'il obtient exactement une boule rouge, et rien "
          "sinon. On note G le montant reçu par le joueur et N = G − m son gain net, en euros."),
        Q(1, "Représenter l'expérience par un arbre pondéré. Les deux tirages sont-ils indépendants ?"),
        Q(2, "Montrer que P(G = 5) = 16/45, puis donner la loi de G."),
        Q(3, "Calculer l'espérance de G."),
        Q(4, "Exprimer E(N) en fonction de m. Pour quelle mise le jeu est-il équitable ?"),
        Q(5, "Le forain fixe la mise à 3 €. Calculer E(N) et interpréter ce résultat. Sur une soirée de 300 parties, "
             "quel bénéfice le forain peut-il espérer ?"),
        Q(6, "Calculer la variance et l'écart type de G. En déduire, sans nouveau calcul, la variance et l'écart type "
             "de N."),
        Q(7, "Avec une mise de 3 €, calculer la probabilité que le joueur gagne de l'argent lors d'une partie. Ce "
             "résultat contredit-il celui de la question 5 ?"),
        Q(8, "Un employé propose de remettre la première boule dans l'urne avant le second tirage. On note R le "
             "nombre de boules rouges obtenues. Quelle est alors la loi de R ? Avec une mise de 3 €, le jeu "
             "reste-t-il favorable au forain ?"),
    ])

    EX.append(heading("Exercice 3. La sandwicherie",
                      "Linéarité de l'espérance, variance, somme de variables aléatoires indépendantes") + [
        P("Dans une sandwicherie, on note X le nombre de sandwichs achetés par un client pris au hasard. Une étude a "
          "permis d'établir la loi de X :"),
        table([["x<sub>i</sub>", "1", "2", "3"], ["P(X = x<sub>i</sub>)", "0,5", "0,3", "0,2"]]),
        P("Chaque sandwich coûte 6 €. Chaque client achète aussi une boisson, à 2 €. On note D la dépense d'un "
          "client, en euros."),
        P("Partie A. Un client", "part"),
        Q(1, "Calculer E(X), puis montrer que V(X) = 0,61. Donner σ(X) arrondi à 10<super>−2</super>."),
        Q(2, "Exprimer D en fonction de X. En déduire E(D), V(D) et σ(D)."),
        P("Partie B. Une journée de 100 clients", "part"),
        P("Un jour donné, 100 clients passent à la sandwicherie. On admet que leurs achats sont indépendants et "
          "suivent tous la loi de X. On note X<sub>1</sub>, …, X<sub>100</sub> les nombres de sandwichs qu'ils "
          "achètent, S = X<sub>1</sub> + … + X<sub>100</sub> le nombre total de sandwichs vendus, et M = S / 100 le "
          "nombre moyen de sandwichs par client."),
        Q(3, "Calculer E(S), V(S) et σ(S)."),
        Q(4, "Un stagiaire écrit : « S = 100X, donc V(S) = 100<super>2</super> × V(X) = 6100 et σ(S) ≈ 78,1. » "
             "Expliquer son erreur."),
        Q(5, "Calculer E(M) et σ(M). Comparer σ(M) à σ(X) et interpréter."),
        Q(6, "On note R la recette de la journée, en euros. Calculer E(R) et σ(R) de deux façons : à partir de S, "
             "puis à partir des dépenses D<sub>1</sub>, …, D<sub>100</sub> des 100 clients."),
        P("Partie C. Une boutique concurrente", "part"),
        P("Dans une autre sandwicherie, le nombre Y de sandwichs achetés par un client suit la loi suivante :"),
        table([["y<sub>i</sub>", "1", "2"], ["P(Y = y<sub>i</sub>)", "0,3", "0,7"]]),
        Q(7, "Calculer E(Y) et V(Y). Les deux boutiques vendent-elles autant de sandwichs par client en moyenne ? "
             "Laquelle a les ventes les plus régulières ? Justifier."),
    ])

    ks4 = list(range(9))
    EX.append(heading("Exercice 4. Contrôle de qualité",
                      "Schéma de Bernoulli, loi binomiale, calculs de probabilités et seuils") + [
        P("Une usine fabrique des ampoules LED. On admet que 3 % des ampoules produites sont défectueuses. Pour "
          "contrôler la production, on prélève au hasard un lot de 50 ampoules. La production est assez importante "
          "pour que l'on puisse assimiler ce prélèvement à 50 tirages successifs avec remise. On note X le nombre "
          "d'ampoules défectueuses du lot."),
        figure(bars(ks4, [pmf(50, 0.03, k) for k in ks4]), 11.5 * cm, "Figure 1. Loi de probabilité de X."),
        P("Le tableau ci-dessous donne des valeurs de P(X ≤ k), arrondies à 10<super>−4</super>."),
        table([["k"] + [str(k) for k in range(7)], ["P(X ≤ k)"] + [f4(cdf(50, 0.03, k)) for k in range(7)]],
              first_col=2.2 * cm, col=1.75 * cm),
        Q(1, "Justifier que X suit une loi binomiale dont on précisera les paramètres."),
        Q(2, "Calculer P(X = 0) et P(X = 2), arrondies à 10<super>−4</super>."),
        Q(3, "Calculer la probabilité qu'un lot contienne au moins une ampoule défectueuse."),
        Q(4, "À l'aide du tableau, calculer P(X ≥ 3) et P(2 ≤ X ≤ 4)."),
        Q(5, "Calculer l'espérance et l'écart type de X. Interpréter l'espérance."),
        Q(6, "Le service qualité refuse un lot s'il contient strictement plus de k ampoules défectueuses. Déterminer "
             "le plus petit entier k tel que la probabilité de refuser un lot, P(X &gt; k), soit inférieure ou égale "
             "à 0,05."),
        Q(7, "Combien d'ampoules faut-il prélever au minimum pour que la probabilité d'obtenir au moins une ampoule "
             "défectueuse soit supérieure ou égale à 0,99 ?"),
    ])

    ks5 = list(range(132, 161))
    EX.append(heading("Exercice 5. La surréservation", "Loi binomiale, problème de seuil, algorithme en Python") + [
        P("Une compagnie aérienne exploite un avion de 150 places. Chaque passager qui a acheté un billet se présente "
          "à l'embarquement avec une probabilité de 0,92, indépendamment des autres passagers. Pour éviter de voler "
          "avec des places vides, la compagnie vend n billets, avec n ≥ 150 : c'est la surréservation. On note "
          "X<sub>n</sub> le nombre de passagers qui se présentent à l'embarquement."),
        P("Chaque billet est vendu 200 € et n'est pas remboursé si le passager ne se présente pas. Chaque passager "
          "qui se présente mais ne peut pas embarquer, faute de place, reçoit une indemnité de 600 €."),
        figure(bars(ks5, [pmf(160, 0.92, k) for k in ks5], highlight=lambda k: k > 150, ylabel="P(X₁₆₀ = k)"),
               12 * cm, "Figure 2. Loi de X<sub>160</sub>. En rose, les cas où des passagers ne peuvent pas "
                        "embarquer."),
        P("Le tableau ci-dessous donne des valeurs de P(X<sub>n</sub> ≤ 150), arrondies à 10<super>−4</super>."),
        table([["n"] + [str(n) for n in range(155, 163)],
               ["P(X<sub>n</sub> ≤ 150)"] + [f4(cdf(n, 0.92, 150)) for n in range(155, 163)]],
              first_col=2.9 * cm, col=1.6 * cm),
        P("Partie A. Sans surréservation", "part"),
        Q(1, "On suppose que n = 150. Quelle est la loi de X<sub>150</sub> ? Calculer son espérance, puis la "
             "probabilité que l'avion parte plein. Commenter."),
        P("Partie B. Avec 160 billets vendus", "part"),
        Q(2, "On suppose que n = 160. Calculer l'espérance et l'écart type de X<sub>160</sub>."),
        Q(3, "Calculer la probabilité qu'au moins un passager ne puisse pas embarquer."),
        Q(4, "On note Y le nombre de passagers qui ne peuvent pas embarquer, et on admet que E(Y) ≈ 0,36. Montrer "
             "que l'espérance de la recette de la compagnie, indemnités déduites, vaut environ 31 784 €. Comparer "
             "avec la recette sans surréservation."),
        P("Partie C. Combien de billets vendre ?", "part"),
        Q(5, "La compagnie veut que la probabilité qu'au moins un passager ne puisse pas embarquer reste inférieure "
             "ou égale à 5 %. À l'aide du tableau, déterminer le nombre maximal de billets qu'elle peut vendre."),
        Q(6, "On considère le programme Python ci-dessous, où comb(n, i) renvoie le coefficient binomial "
             "« i parmi n » :"),
        code(["from math import comb", "", "def proba(n, p, k):", "    s = 0", "    for i in range(k + 1):",
              "        s = s + comb(n, i) * p**i * (1 - p)**(n - i)", "    return s", "",
              "def seuil(n, p, alpha):", "    k = 0", "    while ..............................:",
              "        k = k + 1", "    return k"]),
        QC("a. X suit la loi ℬ(n ; p). Que renvoie proba(n, p, k) ?"),
        QC("b. Compléter la ligne 11 pour que seuil(n, p, alpha) renvoie le plus petit entier k tel que "
           "P(X &gt; k) ≤ alpha."),
        QC("c. L'appel seuil(160, 0.92, 0.05) renvoie 153. Interpréter ce résultat dans le contexte."),
    ])

    # ---------------------------------------------------------------- corrections

    CO = []

    CO.append(heading("Corrigé de l'exercice 1", "Probabilités conditionnelles, arbre pondéré, formule des "
                                                 "probabilités totales") + [
        Q(1, "Les probabilités de la seconde série de branches sont des probabilités conditionnelles : "
             f"P<sub>M</sub>(T) = 0,95 et P<sub>{MB}</sub>(T) = 1 − 0,96 = 0,04."),
        figure(tree([("M", "0{,}02"), (r"\overline{M}", "0{,}98")],
                    [[("T", "0{,}95"), (r"\overline{T}", "0{,}05")], [("T", "0{,}04"), (r"\overline{T}", "0{,}96")]]),
               9.5 * cm, "Arbre pondéré de la situation."),
        Q(2, "P(M ∩ T) = P(M) × P<sub>M</sub>(T) = 0,02 × 0,95 = 0,019. Dans la population, 1,9 % des personnes "
             "sont malades et ont un test positif."),
        Q(3, f"M et M̅ forment une partition de l'univers. D'après la formule des probabilités totales : "
             f"P(T) = P(M ∩ T) + P({MB} ∩ T) = 0,019 + 0,98 × 0,04 = 0,019 + 0,0392 = 0,0582."),
        Q(4, "On cherche P<sub>T</sub>(M) = P(M ∩ T) / P(T) = 0,019 / 0,0582 ≈ 0,326."),
        QC("Seulement un tiers environ des personnes positives sont malades. Le test n'est pas mauvais pour autant : "
           "la maladie est rare, et les faux positifs (4 % des 98 % de personnes saines, soit 0,0392) sont deux fois "
           "plus nombreux que les vrais positifs (0,019). Un test positif doit être confirmé par un autre examen."),
        Q(5, "P(M) × P(T) = 0,02 × 0,0582 = 0,001164, alors que P(M ∩ T) = 0,019 : les deux nombres sont "
             "différents, donc M et T ne sont pas indépendants."),
        QC("C'est heureux : si le résultat du test était indépendant de la maladie, il n'apprendrait rien sur l'état "
           "de santé de la personne. Ici, P<sub>T</sub>(M) ≈ 0,326 est environ 16 fois plus grand que P(M) = 0,02."),
        Q(6, "P(M ∩ T) = 0,95p et, par la formule des probabilités totales, "
             "P(T) = 0,95p + 0,04(1 − p) = 0,91p + 0,04. Donc :"),
        F(r"P_T(M) = \dfrac{P(M \cap T)}{P(T)} = \dfrac{0{,}95p}{0{,}91p + 0{,}04} = \dfrac{95p}{91p + 4}"),
        QC("en multipliant le numérateur et le dénominateur par 100. On retrouve f(0,02) ≈ 0,326, comme dans la "
           "partie A."),
        Q(7, "f est un quotient de fonctions dérivables, et 91p + 4 &gt; 0 sur ]0 ; 1[. Pour tout p de ]0 ; 1[ :"),
        F(r"f'(p) = \dfrac{95(91p + 4) - 95p \times 91}{(91p + 4)^2} = \dfrac{380}{(91p + 4)^2} > 0"),
        QC("f est strictement croissante sur ]0 ; 1[ : plus la maladie est fréquente dans la population testée, plus "
           "un test positif est fiable."),
        Q(8, "Comme 91p + 4 &gt; 0, f(p) ≥ 0,9 ⟺ 95p ≥ 0,9 × (91p + 4) ⟺ 95p − 81,9p ≥ 3,6 ⟺ 13,1p ≥ 3,6 "
             "⟺ p ≥ 36/131 ≈ 0,275."),
        QC("Il faut qu'au moins 27,5 % environ de la population testée soit malade. C'est pourquoi ce type de test "
           "est réservé aux populations à risque, ou confirmé par un second test."),
    ])

    CO.append(heading("Corrigé de l'exercice 2", "Loi d'une variable aléatoire, espérance, variance, "
                                                 "jeu équitable") + [
        Q(1, "On note R une boule rouge et B une boule blanche. Au premier tirage, l'urne contient 2 rouges sur "
             "10 boules ; au second, il reste 9 boules, dont la composition dépend du premier tirage."),
        figure(tree([("R", "2/10"), ("B", "8/10")],
                    [[("R", "1/9"), ("B", "8/9")], [("R", "2/9"), ("B", "7/9")]],
                    leaves=["G = 40", "G = 5", "G = 5", "G = 0"]),
               9.5 * cm, "Arbre pondéré des deux tirages sans remise."),
        QC("Les deux tirages ne sont pas indépendants : la probabilité de tirer une rouge au second tirage vaut 1/9 "
           "si la première boule était rouge, et 2/9 si elle était blanche."),
        Q(2, "L'événement {G = 5} correspond aux deux chemins (R ; B) et (B ; R) :"),
        F(r"P(G = 5) = \dfrac{2}{10} \times \dfrac{8}{9} + \dfrac{8}{10} \times \dfrac{2}{9} = \dfrac{32}{90} "
          r"= \dfrac{16}{45}"),
        QC("De même, P(G = 40) = 2/10 × 1/9 = 2/90 = 1/45 et P(G = 0) = 8/10 × 7/9 = 56/90 = 28/45. "
           "On vérifie que 28/45 + 16/45 + 1/45 = 1."),
        table([["g<sub>i</sub>", "0", "5", "40"], ["P(G = g<sub>i</sub>)", "28/45", "16/45", "1/45"]]),
        Q(3, "E(G) = 0 × 28/45 + 5 × 16/45 + 40 × 1/45 = 120/45 = 8/3 ≈ 2,67 €."),
        Q(4, "Par linéarité de l'espérance, E(N) = E(G) − m = 8/3 − m. Le jeu est équitable si E(N) = 0, "
             "c'est-à-dire pour une mise m = 8/3 ≈ 2,67 €."),
        Q(5, "E(N) = 8/3 − 3 = −1/3 ≈ −0,33 €. Sur un grand nombre de parties, le joueur perd en moyenne environ "
             "33 centimes par partie : le jeu lui est défavorable. Ce que le joueur perd, le forain le gagne : sur "
             "300 parties, il peut espérer un bénéfice d'environ 300 × 1/3 = 100 €."),
        Q(6, "E(G<super>2</super>) = 0<super>2</super> × 28/45 + 5<super>2</super> × 16/45 + 40<super>2</super> × "
             "1/45 = 2000/45 = 400/9. Donc V(G) = E(G<super>2</super>) − E(G)<super>2</super> = 400/9 − 64/9 = "
             "112/3 ≈ 37,33 et σ(G) = √(112/3) ≈ 6,11 €."),
        QC("N = G − m : retrancher une constante décale toutes les valeurs sans changer leur dispersion. Donc "
           "V(N) = V(G) ≈ 37,33 et σ(N) = σ(G) ≈ 6,11 €."),
        Q(7, "Le joueur gagne de l'argent si N &gt; 0, c'est-à-dire si G &gt; 3, soit G = 5 ou G = 40 : "
             "P(N &gt; 0) = 16/45 + 1/45 = 17/45 ≈ 0,378."),
        QC("Ce n'est pas contradictoire : l'espérance est une moyenne. Le joueur gagne un peu plus d'une partie sur "
           "trois, mais le plus souvent seulement 2 € nets, alors qu'il perd 3 € dans près de deux parties sur "
           "trois. En moyenne, il perd."),
        Q(8, "Avec remise, les deux tirages sont identiques et indépendants, et ont deux issues (rouge, de probabilité "
             "0,2, ou blanche) : R suit la loi binomiale ℬ(2 ; 0,2). P(R = 0) = 0,8<super>2</super> = 0,64, "
             "P(R = 1) = 2 × 0,2 × 0,8 = 0,32 et P(R = 2) = 0,2<super>2</super> = 0,04."),
        QC("Alors E(G) = 5 × 0,32 + 40 × 0,04 = 3,2 € et E(N) = 3,2 − 3 = 0,2 € &gt; 0 : le jeu devient favorable au "
           "joueur, et le forain perdrait en moyenne 20 centimes par partie. La proposition est à refuser."),
    ])


    def xy_bars():
        fig, ax = plt.subplots(figsize=(4.8, 2.1))
        ax.bar([0.82, 1.82, 2.82], [0.5, 0.3, 0.2], width=0.34, color=BLUE_HEX, label="X (première boutique)")
        ax.bar([1.18, 2.18], [0.3, 0.7], width=0.34, color=PINK_HEX, label="Y (boutique concurrente)")
        ax.set_xticks([1, 2, 3])
        ax.set_xlabel("Nombre de sandwichs")
        ax.set_ylabel("Probabilité")
        ax.yaxis.set_major_formatter(FuncFormatter(comma))
        ax.grid(axis="y", color="#dfe4ee", lw=0.6)
        ax.set_axisbelow(True)
        ax.legend(frameon=False, fontsize=8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        return fig


    CO.append(heading("Corrigé de l'exercice 3", "Linéarité de l'espérance, variance, somme de variables "
                                                 "aléatoires indépendantes") + [
        Q(1, "E(X) = 1 × 0,5 + 2 × 0,3 + 3 × 0,2 = 1,7. E(X<super>2</super>) = 1 × 0,5 + 4 × 0,3 + 9 × 0,2 = 3,5, "
             "donc V(X) = E(X<super>2</super>) − E(X)<super>2</super> = 3,5 − 2,89 = 0,61, et σ(X) = √0,61 ≈ 0,78."),
        QC("On peut aussi utiliser la définition : V(X) = 0,5 × (−0,7)<super>2</super> + 0,3 × 0,3<super>2</super> + "
           "0,2 × 1,3<super>2</super> = 0,245 + 0,027 + 0,338 = 0,61."),
        Q(2, "D = 6X + 2. Par linéarité, E(D) = 6E(X) + 2 = 12,2 €. V(D) = 6<super>2</super> × V(X) = 36 × 0,61 = "
             "21,96 et σ(D) = 6σ(X) = √21,96 ≈ 4,69 €. La boisson, la même pour tous, augmente la dépense moyenne de "
             "2 € mais ne change pas la dispersion."),
        Q(3, "Par linéarité, E(S) = 100 × E(X) = 170. Les X<sub>i</sub> sont indépendantes, donc leurs variances "
             "s'ajoutent : V(S) = 100 × V(X) = 61, et σ(S) = √61 ≈ 7,81."),
        Q(4, "100X représente 100 fois les achats d'un seul client, comme si les 100 clients achetaient tous le même "
             "nombre de sandwichs. En réalité, les X<sub>i</sub> sont indépendantes : un client qui achète beaucoup "
             "est souvent compensé par un client qui achète peu. Les variances s'ajoutent, V(S) = 100V(X) = 61, "
             "alors que V(100X) = 10 000V(X). Les deux espérances sont égales (170), ce qui rend l'erreur difficile "
             "à repérer."),
        Q(5, "E(M) = E(S) / 100 = 1,7. V(M) = V(S) / 100<super>2</super> = 0,0061, donc σ(M) = σ(X) / √100 ≈ "
             "0,078."),
        QC("Le nombre de sandwichs acheté par un client varie beaucoup (écart type 0,78), mais la moyenne sur "
           "100 clients varie dix fois moins et reste très proche de 1,7 : pour la moyenne d'un échantillon de "
           "taille n, l'écart type est divisé par √n."),
        Q(6, "Avec S : chaque client paie aussi 2 € de boisson, donc R = 6S + 200. E(R) = 6 × 170 + 200 = 1220 €, "
             "V(R) = 36 × 61 = 2196 et σ(R) = 6√61 ≈ 46,9 €."),
        QC("Avec les dépenses : R = D<sub>1</sub> + … + D<sub>100</sub>, où les D<sub>i</sub> sont indépendantes et "
           "suivent la loi de D. E(R) = 100 × 12,2 = 1220 €, V(R) = 100 × 21,96 = 2196 et σ(R) ≈ 46,9 €. On "
           "retrouve les mêmes résultats."),
        Q(7, "E(Y) = 1 × 0,3 + 2 × 0,7 = 1,7. E(Y<super>2</super>) = 0,3 + 4 × 0,7 = 3,1, donc V(Y) = 3,1 − 2,89 = "
             "0,21 et σ(Y) ≈ 0,46."),
        figure(xy_bars(), 10 * cm, "Lois de X et de Y : même espérance, dispersions différentes."),
        QC("Les deux boutiques vendent en moyenne 1,7 sandwich par client. Mais V(Y) &lt; V(X) : les achats sont "
           "moins dispersés dans la boutique concurrente, dont les ventes sont plus régulières et donc plus faciles "
           "à prévoir."),
    ])

    CO.append(heading("Corrigé de l'exercice 4", "Schéma de Bernoulli, loi binomiale, calculs de probabilités et "
                                                 "seuils") + [
        Q(1, "Chaque prélèvement est une épreuve de Bernoulli, dont le succès « l'ampoule est défectueuse » a pour "
             "probabilité p = 0,03. Le mot « succès » désigne seulement l'issue que l'on compte. Les 50 prélèvements "
             "sont identiques et indépendants, puisqu'on les assimile à des tirages avec remise : c'est un schéma de "
             "Bernoulli. X compte les succès, donc X suit la loi binomiale ℬ(50 ; 0,03)."),
        Q(2, "Pour tout entier k entre 0 et 50 :"),
        F(r"P(X = k) = \genfrac{(}{)}{0}{0}{50}{k} \times 0{,}03^k \times 0{,}97^{50 - k}"),
        QC("P(X = 0) = 0,97<super>50</super> ≈ 0,2181. Pour k = 2, le coefficient binomial vaut 50 × 49 / 2 = 1225 : "
           "c'est le nombre de façons de placer les 2 ampoules défectueuses parmi les 50."),
        F(r"P(X = 2) = \genfrac{(}{)}{0}{0}{50}{2} \times 0{,}03^2 \times 0{,}97^{48} = 1225 \times 0{,}0009 \times 0{,}97^{48} "
          r"\approx 0{,}2555"),
        Q(3, "P(X ≥ 1) = 1 − P(X = 0) = 1 − 0,97<super>50</super> ≈ 0,7819. Près de 4 lots sur 5 contiennent au "
             "moins une ampoule défectueuse."),
        Q(4, "P(X ≥ 3) = 1 − P(X ≤ 2) ≈ 1 − 0,8108 = 0,1892. L'événement contraire de {X ≥ 3} est {X ≤ 2}, et non "
             "{X ≤ 3}."),
        QC("P(2 ≤ X ≤ 4) = P(X ≤ 4) − P(X ≤ 1) ≈ 0,9832 − 0,5553 = 0,4279. On retire P(X ≤ 1), et non P(X ≤ 2), "
           "pour garder la valeur 2."),
        Q(5, "E(X) = np = 50 × 0,03 = 1,5. V(X) = np(1 − p) = 50 × 0,03 × 0,97 = 1,455, donc σ(X) = √1,455 ≈ 1,21. "
             "Sur un grand nombre de lots de 50 ampoules, on trouve en moyenne 1,5 ampoule défectueuse par lot."),
        Q(6, "P(X &gt; k) = 1 − P(X ≤ k). P(X &gt; 3) ≈ 1 − 0,9372 = 0,0628 &gt; 0,05, et "
             "P(X &gt; 4) ≈ 1 − 0,9832 = 0,0168 ≤ 0,05."),
        QC("Comme P(X &gt; k) diminue quand k augmente, le plus petit entier qui convient est k = 4 : on refuse un lot "
           "s'il contient au moins 5 ampoules défectueuses. Un lot issu d'une production normale n'est alors refusé "
           "que dans 1,7 % des cas environ."),
        Q(7, "Avec n ampoules, le nombre d'ampoules défectueuses suit ℬ(n ; 0,03), et la probabilité d'en obtenir au "
             "moins une vaut 1 − 0,97<super>n</super>. On résout :"),
        QC("1 − 0,97<super>n</super> ≥ 0,99 ⟺ 0,97<super>n</super> ≤ 0,01 ⟺ n × ln(0,97) ≤ ln(0,01) ⟺ "
           "n ≥ ln(0,01) / ln(0,97), car ln(0,97) &lt; 0 change le sens de l'inégalité quand on divise."),
        QC("ln(0,01) / ln(0,97) ≈ 151,2 : il faut prélever au moins 152 ampoules. Vérification : "
           "1 − 0,97<super>151</super> ≈ 0,9899 et 1 − 0,97<super>152</super> ≈ 0,9902."),
    ])

    CO.append(heading("Corrigé de l'exercice 5", "Loi binomiale, problème de seuil, algorithme en Python") + [
        Q(1, "Les 150 passagers se présentent indépendamment, chacun avec la probabilité 0,92 : X<sub>150</sub> suit "
             "la loi ℬ(150 ; 0,92). E(X<sub>150</sub>) = 150 × 0,92 = 138 : en moyenne, 12 places restent vides."),
        QC("L'avion part plein si les 150 passagers se présentent : P(X<sub>150</sub> = 150) = 0,92<super>150</super> "
           "≈ 3,7\u00a0×\u00a010<super>−6</super>. Cela n'arrive pratiquement jamais, ce qui pousse la compagnie à vendre plus "
           "de billets que de places."),
        Q(2, "X<sub>160</sub> suit la loi ℬ(160 ; 0,92). E(X<sub>160</sub>) = 160 × 0,92 = 147,2, "
             "V(X<sub>160</sub>) = 160 × 0,92 × 0,08 = 11,776 et σ(X<sub>160</sub>) ≈ 3,43."),
        Q(3, "Des passagers restent au sol dès que plus de 150 se présentent : P(X<sub>160</sub> &gt; 150) = "
             "1 − P(X<sub>160</sub> ≤ 150) ≈ 1 − 0,8316 = 0,1684. Dans un vol sur six environ, au moins un passager "
             "ne peut pas embarquer."),
        Q(4, "La recette vaut 200 × 160 − 600 × Y = 32 000 − 600Y. Par linéarité de l'espérance, son espérance vaut "
             "32 000 − 600 × E(Y) ≈ 32 000 − 600 × 0,36 = 31 784 €."),
        QC("Sans surréservation, la recette est de 150 × 200 = 30 000 €, sans aucune indemnité. Vendre 160 billets "
           "rapporte en moyenne environ 1 784 € de plus par vol, au prix d'un passager refusé dans un vol sur six "
           "environ."),
        Q(5, "P(X<sub>n</sub> &gt; 150) = 1 − P(X<sub>n</sub> ≤ 150). Pour n = 157 : 1 − 0,9715 = 0,0285 ≤ 0,05. "
             "Pour n = 158 : 1 − 0,9425 = 0,0575 &gt; 0,05."),
        QC("Cette probabilité augmente avec n : plus on vend de billets, plus le risque est grand. La compagnie peut "
           "donc vendre au plus 157 billets."),
        Q(6, "a. proba(n, p, k) additionne les probabilités P(X = i) pour i allant de 0 à k : elle renvoie "
             "P(X ≤ k)."),
        QC("b. Ligne 11 : <font name='DVM'>while 1 - proba(n, p, k) &gt; alpha:</font>. La boucle augmente k tant "
           "que P(X &gt; k) = 1 − P(X ≤ k) est strictement supérieure à alpha, et s'arrête au premier k tel que "
           "P(X &gt; k) ≤ alpha."),
        QC("c. Avec 160 billets vendus, la probabilité que plus de 153 passagers se présentent est inférieure ou égale "
           "à 5 %, et 153 est le plus petit entier qui a cette propriété (P(X<sub>160</sub> &gt; 152) ≈ 0,053 et "
           "P(X<sub>160</sub> &gt; 153) ≈ 0,025). Il faudrait donc un avion d'au moins 153 places pour que le risque "
           "de refuser des passagers ne dépasse pas 5 %."),
    ])
    return EX, CO


# ---------------------------------------------------------------- document

class Doc(BaseDocTemplate):
    def __init__(self, path, **kw):
        super().__init__(path, pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=1.8 * cm,
                         bottomMargin=2 * cm, title=f"{TITLE} : exercices corrigés", subject=LEVEL, **kw)
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
    out = [P(TITLE, "title"), P("Terminale, spécialité maths. Cinq exercices type bac et leurs corrigés.", "sub"),
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
