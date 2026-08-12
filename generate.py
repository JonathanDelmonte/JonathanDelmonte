#!/usr/bin/env python3
"""
Gera o terminal SVG animado do README de perfil.

    python generate.py --mock     # dados de exemplo, nao precisa de token
    python generate.py            # dados reais (precisa de ACCESS_TOKEN)

Saida em assets/: terminal-dark.svg e terminal-light.svg.

Por que SVG e nao HTML: o README do GitHub sanitiza <script> e <style>, mas
carrega imagem. E um SVG carregado por <img> executa o CSS que estiver dentro
dele - inclusive @keyframes. Entao toda a animacao daqui e CSS embutido.
A mesma restricao tem um preco: <img> nao busca recurso externo, entao webfont
nao carrega. O corpo do texto assume a pilha monospace da maquina de quem olha
(avanco por caractere = 0.6em, a constante CH), e o nome nao depende de fonte
nenhuma: e desenhado ponto a ponto a partir do bitmap 5x7 aqui embaixo.
"""

import os
import sys
import json
import math
import random
import datetime
import urllib.request
from pathlib import Path

# =============================================================================
# CONFIG - o conteudo todo vive aqui.
# =============================================================================

CONFIG = {
    "username":  os.environ.get("GH_USERNAME", "JonathanDelmonte"),
    "wordmark":  "JONATHAN DELMONTE",
    "prompt":    "jonathan@delmonte:~",
    "subtitle":  "SOFTWARE ENGINEERING STUDENT  ·  JUIZ DE FORA, MG  ·  BRAZIL",
    "status":    "OPEN TO INTERNSHIP",

    "tabs": ["STATUS", "REPOS", "STACK", "BIO"],

    # --- aba STATUS: leitura de chave/valor, sem enfeite -----------------
    "status_rows": [
        ("ROLE",      "Software engineering student, full-stack web"),
        ("BASED IN",  "Juiz de Fora, MG, Brazil"),
        ("EDUCATION", "B.S. Software Engineering · UniAcademia · 2024 → 2028"),
        ("ENGLISH",   "C2 proficient · EF SET 79/100"),
        ("AVAILABLE", "internship, on-site or remote"),
    ],
    "now": [
        "SIBHub · church management system for a real client",
        "Porto Hack Santos 2026 · AI agent for port operations",
    ],

    # --- aba STACK -------------------------------------------------------
    "stack": [
        ("LANGUAGES", ["TypeScript", "JavaScript", "Python", "SQL", "HTML", "CSS"]),
        ("FRONT-END", ["React", "Next.js", "Tailwind CSS", "Three.js",
                       "React Three Fiber", "GSAP", "WebGL"]),
        ("BACK-END & DATA", ["Node.js", "Express", "REST APIs", "PostgreSQL",
                             "ER Modeling", "OOP"]),
        ("TOOLS & PRACTICE", ["Git", "GitHub", "GitLab", "Scrum / Agile",
                              "ClickUp", "Responsive Design", "Accessibility",
                              "Progressive Enhancement"]),
    ],

    # --- aba BIO ---------------------------------------------------------
    "bio": [
        "Most of what I build ends up in front of someone who is not a",
        "developer: a client, a church staff, a person ordering lunch",
        "from their phone.",
        "",
        "So it has to be interesting to look at, and it still has to work",
        "on a bad connection, on an old phone, with JavaScript half-loaded.",
    ],
    "principles": [
        "design the relational model before the first endpoint",
        "every animation needs a reduced-motion path",
        "shipping to a real client is the only real test",
    ],
}

# Paletas. A escura e a identidade (o ciano da foto de perfil sobre abissal);
# a clara e a mesma ideia em agua rasa, nao um negativo da escura.
THEMES = {
    "dark": {
        "bg0":     "#04080C",
        "bg1":     "#08202B",
        "chrome":  "#0A1A22",
        "ink":     "#E9F6F8",
        "ink_2":   "#9DBAC2",
        "ink_3":   "#5E7C86",
        "line":    "#153039",
        "accent":  "#17E0D4",
        "accent2": "#2E86FF",
        "glow":    1.0,
        "grain":   0.038,
        "scan":    0.34,    # forca das scanlines
        "pixel":   0.20,    # forca da grade vertical de pixels
        "roll":    0.05,    # forca da faixa de varredura que desce
        "off":     0.075,   # opacidade dos pontos apagados do letreiro
        "flare":   "#D9FFFB",  # clarao que atravessa o letreiro
    },
    "light": {
        "bg0":     "#EFF6F7",
        "bg1":     "#DDEEF1",
        "chrome":  "#D3E6EA",
        "ink":     "#062830",
        "ink_2":   "#37545C",
        "ink_3":   "#6E8E96",
        "line":    "#C3DBE0",
        "accent":  "#0A8E9E",
        "accent2": "#0F5E8C",
        "glow":    0.0,
        "grain":   0.026,
        "scan":    0.10,
        "pixel":   0.07,
        "roll":    0.03,
        "off":     0.055,   # no claro os pontos apagados fantasmam facil
        "flare":   "#04525C",  # no claro o clarao escurece, nao clareia
    },
}

MONO = ("ui-monospace, 'SF Mono', SFMono-Regular, Menlo, Consolas, "
        "'DejaVu Sans Mono', 'Liberation Mono', monospace")
CH = 0.6
W, H = 900, 640
M = 44
CYCLE = 28.0                  # segundos para as quatro abas
MONTHS = "JFMAMJJASOND"


# =============================================================================
# LETREIRO - bitmap 5x7. O nome nao usa fonte: e desenhado ponto a ponto,
# entao fica identico em qualquer maquina e pode acender em onda.
# =============================================================================

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000",) * 7,
}

GW, GH = 5, 7                 # colunas e linhas de um glifo


def wordmark(text, x0, y0, pitch, t, buckets=20):
    """
    Desenha o texto como matriz de LED.

    A matriz inteira e desenhada, inclusive os pontos apagados e o espaco
    entre as palavras: e isso que faz o olho ler "painel de LED" em vez de
    "um monte de bolinha". O aceso e maior que o apagado, como led que
    sangra luz. Os acesos entram numa onda da esquerda para a direita,
    agrupados em `buckets` faixas para nao virar um style por ponto - e a
    mesma faixa carrega o clarao periodico que atravessa o letreiro depois.
    """
    adv = GW * pitch + pitch + 2          # avanco por caractere
    span = max(len(text) * adv - (pitch + 2), 1)
    lit = [[] for _ in range(buckets)]
    off = []

    for ci, chpar in enumerate(text.upper()):
        glyph = FONT.get(chpar, FONT[" "])
        for row in range(GH):
            for col in range(GW):
                cx = x0 + ci * adv + col * pitch
                cy = y0 + row * pitch
                if glyph[row][col] == "1":
                    b = min(int((cx - x0) / span * buckets), buckets - 1)
                    lit[b].append((cx, cy))
                else:
                    off.append((cx, cy))

    r_on, r_off = pitch * 0.38, pitch * 0.29
    o = ['<g class="wm">']
    o.append(f'<g fill="{t["ink_2"]}" opacity="{t["off"]}">')
    o += [f'<circle cx="{x}" cy="{y}" r="{r_off:.2f}"/>' for x, y in off]
    o.append('</g>')

    # Uns poucos pontos "queimados", piscando fora de ritmo. Detalhe de tubo
    # velho: sem isso a matriz fica limpa demais para ser um painel usado.
    rnd = random.Random(3)
    flat = [p for grp in lit for p in grp]
    dead = set(rnd.sample(flat, min(3, len(flat)))) if flat else set()

    for b, pts in enumerate(lit):
        if not pts:
            continue
        o.append(f'<g class="lit" style="animation-delay:{b*0.05:.2f}s,'
                 f'{2.5 + b*0.055:.2f}s">')
        for x, y in pts:
            cls = ' class="dead"' if (x, y) in dead else ''
            o.append(f'<circle cx="{x}" cy="{y}" r="{r_on:.2f}"{cls}/>')
        o.append('</g>')
    o.append('</g>')
    return "\n".join(o), span


# =============================================================================
# API DO GITHUB
# =============================================================================

API = "https://api.github.com/graphql"

Q_REPOS = """
query($login:String!, $after:String) {
  user(login:$login) {
    createdAt
    followers { totalCount }
    repositories(first:100, after:$after, ownerAffiliations:OWNER,
                 isFork:false, privacy:PUBLIC) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        stargazerCount
        languages(first:12, orderBy:{field:SIZE, direction:DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""

Q_CONTRIB = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def graphql(query, variables, token):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "profile-readme-generator",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise RuntimeError(json.dumps(payload["errors"], indent=2))
    return payload["data"]


def fetch(username, token):
    repos, stars, langs, cursor = 0, 0, {}, None
    created_at, followers = None, 0
    while True:
        d = graphql(Q_REPOS, {"login": username, "after": cursor}, token)["user"]
        created_at = d["createdAt"]
        followers = d["followers"]["totalCount"]
        rr = d["repositories"]
        repos = rr["totalCount"]
        for node in rr["nodes"]:
            stars += node["stargazerCount"]
            for edge in node["languages"]["edges"]:
                nm = edge["node"]["name"]
                langs[nm] = langs.get(nm, 0) + edge["size"]
        if not rr["pageInfo"]["hasNextPage"]:
            break
        cursor = rr["pageInfo"]["endCursor"]

    now = datetime.datetime.now(datetime.timezone.utc)

    # Commits somando ano a ano desde a criacao da conta: a API so devolve
    # contribuicoes dentro de uma janela, entao nao da para pedir tudo de uma vez.
    commits = 0
    year = datetime.datetime.fromisoformat(created_at.replace("Z", "+00:00")).year
    while year <= now.year:
        frm = datetime.datetime(year, 1, 1, tzinfo=datetime.timezone.utc)
        to = min(datetime.datetime(year, 12, 31, 23, 59,
                                   tzinfo=datetime.timezone.utc), now)
        c = graphql(Q_CONTRIB, {"login": username, "from": frm.isoformat(),
                                "to": to.isoformat()}, token)["user"]["contributionsCollection"]
        commits += c["totalCommitContributions"] + c["restrictedContributionsCount"]
        year += 1

    frm = now - datetime.timedelta(days=364)
    cal = graphql(Q_CONTRIB, {"login": username, "from": frm.isoformat(),
                              "to": now.isoformat()},
                  token)["user"]["contributionsCollection"]["contributionCalendar"]
    buckets = {}
    for week in cal["weeks"]:
        for day in week["contributionDays"]:
            key = day["date"][:7]
            buckets[key] = buckets.get(key, 0) + day["contributionCount"]

    keys, cur = [], datetime.date(now.year, now.month, 1)
    for _ in range(12):
        keys.append(f"{cur.year:04d}-{cur.month:02d}")
        cur = (cur.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
    keys.reverse()

    return {
        "repos": repos,
        "stars": stars,
        "commits": commits,
        "followers": followers,
        "bytes": sum(langs.values()),
        "languages": sorted(langs.items(), key=lambda kv: -kv[1]),
        "monthly": [{"month": int(k[5:7]), "value": buckets.get(k, 0)} for k in keys],
        "built": now.strftime("%d %b %Y").upper(),
    }


def mock():
    """Valores reais e publicos do perfil, para conferir o desenho sem token."""
    vals = [0, 0, 0, 0, 6, 21, 34, 58, 72, 61, 94, 69]
    today = datetime.date.today()
    months, cur = [], datetime.date(today.year, today.month, 1)
    for _ in range(12):
        months.append(cur.month)
        cur = (cur.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
    months.reverse()
    return {
        "repos": 7, "stars": 3, "commits": 415, "followers": 2,
        "bytes": 925852,
        "languages": [("TypeScript", 447178), ("CSS", 332543), ("Python", 92051),
                      ("HTML", 31556), ("JavaScript", 22524)],
        "monthly": [{"month": m, "value": v} for m, v in zip(months, vals)],
        "built": today.strftime("%d %b %Y").upper(),
    }


# =============================================================================
# PRIMITIVAS
# =============================================================================

def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt(n):
    return f"{n:,}".replace(",", " ")


def wide(s, size, spacing=0.0):
    s = str(s)
    return len(s) * CH * size + max(len(s) - 1, 0) * spacing


def txt(x, y, s, size, fill, *, weight=400, spacing=0.0, anchor="start",
        opacity=1.0, cls=None, extra=""):
    a = [f'x="{x:.1f}"', f'y="{y:.1f}"', f'font-size="{size}"', f'fill="{fill}"']
    if weight != 400:
        a.append(f'font-weight="{weight}"')
    if spacing:
        a.append(f'letter-spacing="{spacing}"')
    if anchor != "start":
        a.append(f'text-anchor="{anchor}"')
    if opacity != 1.0:
        a.append(f'opacity="{opacity:.3f}"')
    if cls:
        a.append(f'class="{cls}"')
    if extra:
        a.append(extra)
    return f'<text {" ".join(a)}>{esc(s)}</text>'


def smooth(points, tension=0.34):
    if len(points) < 2:
        return ""
    d = [f"M{points[0][0]:.2f},{points[0][1]:.2f}"]
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1, p2 = points[i], points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) * tension / 2,
              p1[1] + (p2[1] - p0[1]) * tension / 2)
        c2 = (p2[0] - (p3[0] - p1[0]) * tension / 2,
              p2[1] - (p3[1] - p1[1]) * tension / 2)
        d.append(f"C{c1[0]:.2f},{c1[1]:.2f} {c2[0]:.2f},{c2[1]:.2f} "
                 f"{p2[0]:.2f},{p2[1]:.2f}")
    return " ".join(d)


def _window(i, n, fade=1.6):
    """Janela [entrada, saida] da aba i dentro do ciclo, em porcentagem."""
    share = 100.0 / n
    return share * i, share * (i + 1), fade


def tab_keyframes(i, n):
    """Conteudo da aba: visivel so na sua janela, entrando de baixo."""
    a, b, fade = _window(i, n)
    ON = "opacity:1; transform:translateY(0);"
    OFF = "opacity:0; transform:translateY(6px);"
    if i == 0:
        return f"0%,{b-fade:.2f}% {{ {ON} }} {b:.2f}%,100% {{ {OFF} }}"
    tail = "100%" if i == n - 1 else f"{b:.2f}%,100%"
    return (f"0%,{a-fade:.2f}% {{ {OFF} }} "
            f"{a:.2f}%,{b-fade:.2f}% {{ {ON} }} "
            f"{tail} {{ {OFF} }}")


def win_keyframes(i, n, frm, to, start=1.0, dur=3.0):
    """
    Animacao que acontece UMA vez, dentro da janela da aba i, e fica parada
    o resto do ciclo. Usar animation-delay aqui nao serviria: o delay
    deslocaria o ciclo de 28s inteiro e desalinharia a aba.
    """
    a, _, _ = _window(i, n)
    s, e = a + start, a + start + dur
    return f"0%,{s:.2f}% {{ {frm} }} {e:.2f}%,100% {{ {to} }}"


def tab_label_keyframes(i, n, on, off):
    """Rotulo da aba: acende na cor de destaque enquanto a aba esta no ar."""
    a, b, fade = _window(i, n)
    ON = f"fill:{on}; opacity:1;"
    OFF = f"fill:{off}; opacity:0.42;"
    if i == 0:
        return f"0%,{b-fade:.2f}% {{ {ON} }} {b:.2f}%,100% {{ {OFF} }}"
    tail = "100%" if i == n - 1 else f"{b:.2f}%,100%"
    return (f"0%,{a-fade:.2f}% {{ {OFF} }} "
            f"{a:.2f}%,{b-fade:.2f}% {{ {ON} }} "
            f"{tail} {{ {OFF} }}")


# =============================================================================
# O TERMINAL
# =============================================================================

def render(d, theme_name):
    t = THEMES[theme_name]
    accent, ink, ink2, ink3 = t["accent"], t["ink"], t["ink_2"], t["ink_3"]
    glow = ' filter="url(#glow)"' if t["glow"] else ""
    tabs = CONFIG["tabs"]

    alt = (f'{CONFIG["wordmark"]}. {CONFIG["subtitle"]}. '
           f'{d["repos"]} repositories, {d["stars"]} stars, {d["commits"]} commits. '
           f'Stack: ' + ", ".join(i for _, g in CONFIG["stack"] for i in g) + '.')

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'width="{W}" height="{H}" role="img" aria-label="{esc(alt)}">']

    # ------------------------------------------------------------------ defs
    o.append(f'''<defs>
  <radialGradient id="bg" cx="0.72" cy="0.16" r="1.0">
    <stop offset="0%"   stop-color="{t['bg1']}"/>
    <stop offset="100%" stop-color="{t['bg0']}"/>
  </radialGradient>
  <linearGradient id="fade" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%"   stop-color="{t['line']}" stop-opacity="0"/>
    <stop offset="12%"  stop-color="{t['line']}" stop-opacity="1"/>
    <stop offset="88%"  stop-color="{t['line']}" stop-opacity="1"/>
    <stop offset="100%" stop-color="{t['line']}" stop-opacity="0"/>
  </linearGradient>
  <radialGradient id="vig" cx="0.5" cy="0.5" r="0.75">
    <stop offset="52%"  stop-color="{t['bg0']}" stop-opacity="0"/>
    <stop offset="100%" stop-color="{t['bg0']}" stop-opacity="0.9"/>
  </radialGradient>
  <linearGradient id="rollg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"   stop-color="{t['accent']}" stop-opacity="0"/>
    <stop offset="50%"  stop-color="{t['accent']}" stop-opacity="1"/>
    <stop offset="100%" stop-color="{t['accent']}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="areag" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"   stop-color="{t['accent']}" stop-opacity="0.38"/>
    <stop offset="100%" stop-color="{t['accent']}" stop-opacity="0.02"/>
  </linearGradient>
  <!-- CRT: scanline horizontal e grade vertical de pixels.
       scan  = camada de baixo, forte;  scan2 = camada de cima, discreta. -->
  <pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse">
    <rect width="4" height="1.2" fill="#000" fill-opacity="{t['scan']}"/>
  </pattern>
  <pattern id="scan2" width="4" height="3" patternUnits="userSpaceOnUse">
    <rect width="4" height="1" fill="#000" fill-opacity="{t['scan']*0.34:.3f}"/>
  </pattern>
  <pattern id="pix" width="3" height="3" patternUnits="userSpaceOnUse">
    <rect width="1" height="3" fill="#000" fill-opacity="{t['pixel']}"/>
  </pattern>
  <filter id="grain" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" seed="9"/>
    <feColorMatrix type="saturate" values="0"/>
  </filter>
  <filter id="glow" x="-70%" y="-70%" width="240%" height="240%">
    <feGaussianBlur stdDeviation="2.6" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <clipPath id="screen">
    <rect x="0" y="0" width="{W}" height="{H}" rx="12"/>
  </clipPath>
</defs>''')

    o.append('<g clip-path="url(#screen)">')
    o.append(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')

    # CRT, camada de baixo. A textura pesada fica AQUI, sob o conteudo.
    # Por cima do texto ela destroi glifo: a grade vertical de 3px cai em cima
    # da haste do M em corpo 13 e sobra a forma de um A. Embaixo, o efeito
    # aparece igual e a letra continua inteira.
    o.append(f'<rect width="{W}" height="{H}" fill="url(#scan)"/>')
    o.append(f'<rect width="{W}" height="{H}" fill="url(#pix)"/>')

    # ----------------------------------------------------- moldura da janela
    o.append(f'<rect width="{W}" height="38" fill="{t["chrome"]}"/>')
    for i, col in enumerate((ink3, t["accent2"], accent)):
        o.append(f'<circle cx="{24 + i*19}" cy="19" r="4.6" fill="{col}" '
                 f'opacity="{0.55 + i*0.18:.2f}"/>')
    o.append(txt(W / 2, 23, CONFIG["prompt"], 11, ink3, spacing=1.6,
                 anchor="middle"))
    pw = wide(CONFIG["prompt"], 11, 1.6)
    o.append(f'<rect x="{W/2 + pw/2 + 4:.1f}" y="14" width="6.6" height="11" '
             f'fill="{accent}" class="cur"/>')
    o.append(f'<line x1="0" y1="38" x2="{W}" y2="38" stroke="{t["line"]}" '
             f'stroke-width="1"/>')

    # Tudo daqui para baixo treme junto no glitch raro. A moldura da janela
    # fica de fora de proposito: e a tela que falha, nao o monitor.
    o.append('<g class="glitch">')

    # ---------------------------------------------------------- o letreiro
    wm, span = wordmark(CONFIG["wordmark"], M, 66, 7, t)
    o.append(f'<g fill="{accent}"{glow}>{wm}</g>')
    o.append(txt(M, 142, CONFIG["subtitle"], 11, ink3, spacing=2.6,
                 cls="fade1"))

    # -------------------------------------------------------------- as abas
    TABX, TABW, TABS = M, 120, 11.5
    tab_w = [wide(name, TABS, 2.8) for name in tabs]
    for i, name in enumerate(tabs):
        o.append(txt(TABX + i * TABW, 186, name, TABS, ink3, spacing=2.8,
                     weight=700, cls=f"tl tl{i}"))
    o.append(f'<line x1="{M}" y1="199" x2="{W-M}" y2="199" '
             f'stroke="{t["line"]}" stroke-width="1"/>')
    # O sublinhado desliza e encolhe para caber exatamente no rotulo ativo:
    # largura base 100, escalada por tab_w[i]/100 em cada parada.
    o.append(f'<g transform="translate({TABX},199)">'
             f'<rect x="0" y="-1.5" width="100" height="2.5" fill="{accent}" '
             f'class="slide"{glow}/></g>')

    # ===================================================== conteudo das abas
    # Cada linha entra escalonada dentro da janela da sua aba. Como delay de
    # CSS deslocaria o ciclo inteiro de 28s, o escalonamento vai na propria
    # porcentagem do keyframe - por isso um keyframe por (aba, linha).
    rows_used = []

    def row(i, j):
        if (i, j) not in rows_used:
            rows_used.append((i, j))
        return f"r{i}_{j}"

    def open_tab(i):
        return f'<g class="tab tab{i}">'

    # --- 0 STATUS ---------------------------------------------------------
    o.append(open_tab(0))
    for j, (k, v) in enumerate(CONFIG["status_rows"]):
        y = 244 + j * 34
        o.append(f'<g class="{row(0, j)}">')
        o.append(txt(M, y, k, 11, ink3, spacing=2.2))
        o.append(txt(M + 130, y, v, 13, ink2))
        o.append('</g>')
    nj = len(CONFIG["status_rows"])
    o.append(f'<g class="{row(0, nj)}">')
    o.append(f'<line x1="{M}" y1="436" x2="{W-M}" y2="436" '
             f'stroke="url(#fade)" stroke-width="1"/>')
    o.append(txt(M, 464, "NOW", 11, accent, spacing=3.4))
    o.append('</g>')
    for j, line in enumerate(CONFIG["now"]):
        y = 498 + j * 30
        o.append(f'<g class="{row(0, nj + 1 + j)}">')
        o.append(f'<rect x="{M}" y="{y-9}" width="2" height="12" fill="{accent}" '
                 f'opacity="0.5"/>')
        o.append(txt(M + 14, y, line, 13, ink))
        o.append('</g>')
    o.append('</g>')

    # --- 1 REPOS ----------------------------------------------------------
    o.append(open_tab(1))
    cells = [("REPOSITORIES", f'{d["repos"]:02d}'),
             ("STARS",        f'{d["stars"]:02d}'),
             ("COMMITS",      fmt(d["commits"])),
             ("CODE",         f'{d["bytes"]/1024:.0f} KB')]
    cw = (W - 2 * M) / 4
    for j, (label, value) in enumerate(cells):
        x = M + j * cw
        o.append(f'<g class="{row(1, j)}">')
        if j:
            o.append(f'<line x1="{x-22:.0f}" y1="252" x2="{x-22:.0f}" y2="318" '
                     f'stroke="{t["line"]}" stroke-width="1"/>')
        o.append(txt(x, 264, label, 11, ink3, spacing=2.2))
        o.append(txt(x, 308, value, 34, ink, weight=700, spacing=1))
        o.append('</g>')

    langs = d["languages"][:5]
    grand = sum(v for _, v in d["languages"]) or 1
    shown = sum(v for _, v in langs)
    slices = [(nm, v / grand) for nm, v in langs]
    if grand - shown > 0:
        slices.append(("Other", (grand - shown) / grand))

    o.append(f'<g class="{row(1, 4)}">')
    o.append(txt(M, 362, "LANGUAGES", 11, ink3, spacing=2.2))
    bw, by, bh, gap = W - 2 * M, 374, 9, 3
    # A barra inteira se estica a partir da esquerda quando a aba entra.
    o.append(f'<g transform="translate({M},{by})"><g class="bargrow">')
    x = 0
    for j, (nm, frac) in enumerate(slices):
        seg = max(frac * (bw - gap * (len(slices) - 1)), 6)
        op = max(0.95 - j * 0.14, 0.32)
        o.append(f'<rect x="{x:.1f}" width="{seg:.1f}" height="{bh}" '
                 f'fill="{accent}" opacity="{op:.2f}"/>')
        x += seg + gap
    o.append('</g></g>')
    o.append('</g>')

    o.append(f'<g class="{row(1, 5)}">')
    lx = M
    for j, (nm, frac) in enumerate(slices):
        op = max(0.95 - j * 0.14, 0.32)
        o.append(f'<rect x="{lx:.1f}" y="{by+26}" width="7" height="7" '
                 f'fill="{accent}" opacity="{op:.2f}"/>')
        label = f"{nm} {frac*100:.1f}%"
        o.append(txt(lx + 14, by + 33, label, 11.5, ink2))
        lx += 14 + wide(label, 11.5) + 24
    o.append('</g>')

    # sparkline dos 12 meses
    o.append(f'<g class="{row(1, 6)}">')
    o.append(txt(M, 466, "ACTIVITY · LAST 12 MONTHS", 11, ink3, spacing=2.2))
    o.append(txt(W - M, 466, f'{fmt(sum(m["value"] for m in d["monthly"]))} '
                             f'CONTRIBUTIONS', 11, accent, spacing=2.2,
                 anchor="end"))
    CX0, CX1, CY0, CY1 = M, W - M, 484, 552
    vals = [m["value"] for m in d["monthly"]] or [0]
    peak = max(vals) or 1
    n = len(vals)
    pts = [(CX0 + (CX1 - CX0) * (i / (n - 1)),
            CY1 - (CY1 - CY0) * (0.05 + 0.95 * (v / peak)))
           for i, v in enumerate(vals)]
    line_d = smooth(pts)
    o.append(f'<path d="{line_d} L{CX1},{CY1} L{CX0},{CY1} Z" fill="url(#areag)"/>')
    # a linha se desenha sozinha toda vez que a aba REPOS entra
    o.append(f'<path d="{line_d}" fill="none" stroke="{accent}" stroke-width="2" '
             f'stroke-linecap="round" pathLength="1" class="trace"{glow}/>')
    o.append(f'<line x1="{CX0}" y1="{CY1}" x2="{CX1}" y2="{CY1}" '
             f'stroke="{t["line"]}" stroke-width="1"/>')
    for j, m in enumerate(d["monthly"]):
        mx = CX0 + (CX1 - CX0) * (j / (n - 1))
        o.append(txt(mx, CY1 + 19, MONTHS[m["month"] - 1], 10, ink3,
                     anchor="middle", opacity=0.75))
    o.append('</g>')
    o.append('</g>')

    # --- 2 STACK ----------------------------------------------------------
    o.append(open_tab(2))
    groups = CONFIG["stack"]
    gw = (W - 2 * M) / len(groups)
    for gi, (title, items) in enumerate(groups):
        x = M + gi * gw
        o.append(f'<g class="{row(2, gi)}">')
        o.append(txt(x + 13, 252, title, 11, accent, spacing=2.8, opacity=0.9))
        top = 268
        bot = top + (len(items) - 1) * 30 + 16
        o.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{bot}" '
                 f'stroke="{t["line"]}" stroke-width="1.5"/>')
        o.append(f'<g transform="translate({x},{top})">'
                 f'<line x1="0" y1="0" x2="0" y2="34" stroke="{accent}" '
                 f'stroke-width="1.5" class="trav" '
                 f'style="animation-delay:{gi*0.5:.2f}s;'
                 f'--span:{bot-top-34}px"/></g>')
        for ii, item in enumerate(items):
            y = 290 + ii * 30
            o.append(f'<rect x="{x+12}" y="{y-4.5}" width="4.5" height="4.5" '
                     f'fill="{accent}" opacity="0.6"/>')
            o.append(txt(x + 26, y, item, 13, ink2))
        o.append('</g>')
    o.append('</g>')

    # --- 3 BIO ------------------------------------------------------------
    o.append(open_tab(3))
    y, para = 250, 0
    o.append(f'<g class="{row(3, 0)}">')
    for line in CONFIG["bio"]:
        if line:
            o.append(txt(M, y, line, 14, ink))
            y += 26
        else:
            # linha em branco separa paragrafo: fecha o grupo e abre o proximo
            para += 1
            o.append(f'</g><g class="{row(3, para)}">')
            y += 14
    o.append('</g>')
    para += 1
    o.append(f'<g class="{row(3, para)}">')
    o.append(f'<line x1="{M}" y1="{y+18}" x2="{W-M}" y2="{y+18}" '
             f'stroke="url(#fade)" stroke-width="1"/>')
    o.append(txt(M, y + 52, "PRINCIPLES", 11, accent, spacing=3.4))
    o.append('</g>')
    for j, p in enumerate(CONFIG["principles"]):
        py = y + 82 + j * 27
        o.append(f'<g class="{row(3, para + 1 + j)}">')
        o.append(f'<rect x="{M}" y="{py-5}" width="4.5" height="4.5" '
                 f'fill="{accent}" opacity="0.6"/>')
        o.append(txt(M + 16, py, p, 13, ink2))
        o.append('</g>')
    o.append('</g>')
    o.append('</g>')   # fecha .glitch

    # ------------------------------------------------------- barra de baixo
    o.append(f'<line x1="{M}" y1="596" x2="{W-M}" y2="596" '
             f'stroke="url(#fade)" stroke-width="1"/>')
    o.append(f'<circle cx="{M+4}" cy="617" r="3.4" fill="{accent}" '
             f'class="dot"{glow}/>')
    o.append(txt(M + 17, 621, CONFIG["status"], 11, ink2, spacing=2.2))
    o.append(txt(W - M, 621, f'UPDATED {d["built"]}', 11, ink3, spacing=2.2,
                 anchor="end"))

    # ------------------------------------------------------------- CRT/grao
    o.append(f'<rect width="{W}" height="{H}" fill="url(#vig)"/>')
    o.append(f'<rect width="{W}" height="{H}" filter="url(#grain)" '
             f'opacity="{t["grain"]}"/>')
    # CRT, camada de cima: so a scanline horizontal, fraca. Ela amarra o
    # conteudo a textura sem comer haste vertical. A grade de pixels nao
    # entra aqui de proposito.
    o.append(f'<rect width="{W}" height="{H}" fill="url(#scan2)"/>')
    # a faixa que desce devagar, como o refresh de um tubo antigo
    o.append(f'<rect x="0" y="0" width="{W}" height="140" fill="url(#rollg)" '
             f'opacity="{t["roll"]}" class="roll"/>')
    o.append('</g>')

    # --------------------------------------------------------------- borda
    o.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" '
             f'fill="none" stroke="{t["line"]}" stroke-width="1"/>')

    # ----------------------------------------------------------------- CSS
    css = [f'''
    text {{ font-family: {MONO}; white-space: pre;
            text-rendering: geometricPrecision; }}

    /* letreiro: acende em onda, e depois um clarao atravessa de tempo em
       tempo. Os dois atrasos por faixa vem no style de cada grupo. */
    .lit {{ opacity: 0;
            animation: ignite .5s ease-out forwards,
                       flare 11s ease-in-out infinite; }}
    @keyframes ignite {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    @keyframes flare {{ 0%,88%,100% {{ fill: {accent}; }}
                        93% {{ fill: {t["flare"]}; }} }}
    /* pontos queimados, piscando fora de ritmo */
    .dead {{ animation: dead 7.3s steps(1) infinite; }}
    @keyframes dead {{ 0%,38% {{ opacity: 1; }} 39%,41% {{ opacity: .12; }}
                       42%,73% {{ opacity: 1; }} 74%,75% {{ opacity: .3; }}
                       76%,100% {{ opacity: 1; }} }}
    .wm {{ animation: wmglow 9s ease-in-out infinite 2s; }}
    @keyframes wmglow {{ 0%,88%,100% {{ opacity: 1; }} 94% {{ opacity: .82; }} }}

    .fade1 {{ opacity: 0; animation: fadein .8s ease-out 1.1s forwards; }}
    @keyframes fadein {{ to {{ opacity: 1; }} }}

    .cur {{ animation: blink 1.1s steps(1) infinite; }}
    @keyframes blink {{ 0%,55% {{ opacity: 1; }} 55.01%,100% {{ opacity: 0; }} }}

    /* falha rara de tela: so o conteudo treme, a moldura fica parada */
    .glitch {{ animation: glitch 17s steps(1) infinite; }}
    @keyframes glitch {{ 0%,97.4%,100% {{ transform: translateX(0); }}
                         97.7% {{ transform: translateX(-2px); }}
                         98.1% {{ transform: translateX(3px); }}
                         98.5% {{ transform: translateX(-1px); }} }}

    .roll {{ animation: roll 9s linear infinite; }}
    @keyframes roll {{ from {{ transform: translateY(-160px); }}
                       to   {{ transform: translateY({H + 20}px); }} }}

    .dot {{ animation: pulse 2.4s ease-in-out infinite; }}
    @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: .25; }} }}

    .trav {{ animation: trav 4.6s cubic-bezier(.5,0,.5,1) infinite; }}
    @keyframes trav {{ 0% {{ transform: translateY(0); opacity: 0; }}
                       12% {{ opacity: .9; }}
                       70%,100% {{ opacity: 0;
                                   transform: translateY(var(--span)); }} }}

    .tab {{ opacity: 0; }}
    .slide {{ animation: slide {CYCLE}s cubic-bezier(.6,0,.3,1) infinite; }}
    @keyframes slide {{
      0%,23.5%   {{ transform: translateX(0px) scaleX({tab_w[0]/100:.3f}); }}
      25%,48.5%  {{ transform: translateX({TABW}px) scaleX({tab_w[1]/100:.3f}); }}
      50%,73.5%  {{ transform: translateX({TABW*2}px) scaleX({tab_w[2]/100:.3f}); }}
      75%,96%    {{ transform: translateX({TABW*3}px) scaleX({tab_w[3]/100:.3f}); }}
      100%       {{ transform: translateX(0px) scaleX({tab_w[0]/100:.3f}); }} }}''']

    nt = len(tabs)
    for i in range(nt):
        css.append(f'''
    .tab{i} {{ animation: tabv{i} {CYCLE}s linear infinite; }}
    @keyframes tabv{i} {{ {tab_keyframes(i, nt)} }}
    .tl{i} {{ animation: tll{i} {CYCLE}s linear infinite; }}
    @keyframes tll{i} {{ {tab_label_keyframes(i, nt, accent, ink3)} }}''')

    # Entrada escalonada linha a linha, dentro da janela de cada aba.
    for i, j in rows_used:
        kf = win_keyframes(
            i, nt,
            "opacity:0; transform:translateX(-7px);",
            "opacity:1; transform:translateX(0);",
            start=0.35 + j * 0.26, dur=1.0)
        css.append(f'''
    .r{i}_{j} {{ animation: kr{i}_{j} {CYCLE}s cubic-bezier(.2,.7,.3,1) infinite; }}
    @keyframes kr{i}_{j} {{ {kf} }}''')

    # A barra de linguagens estica e a linha do grafico se desenha toda vez
    # que a aba REPOS volta.
    css.append(f'''
    .bargrow {{ animation: bargrow {CYCLE}s cubic-bezier(.2,.7,.3,1) infinite; }}
    @keyframes bargrow {{ {win_keyframes(1, nt, "transform:scaleX(0);",
                                         "transform:scaleX(1);",
                                         start=1.8, dur=3.4)} }}
    .trace {{ stroke-dasharray: 1;
              animation: trace {CYCLE}s cubic-bezier(.4,0,.2,1) infinite; }}
    @keyframes trace {{ {win_keyframes(1, nt, "stroke-dashoffset:1;",
                                       "stroke-dashoffset:0;",
                                       start=2.0, dur=6.0)} }}''')

    rowsel = ", ".join(f".r{i}_{j}" for i, j in rows_used) or ".none"
    css.append(f'''
    @media (prefers-reduced-motion: reduce) {{
      .roll, .dot, .trav, .slide, .wm, .cur, .dead, .glitch
        {{ animation: none !important; }}
      {rowsel} {{ animation: none !important; opacity: 1;
                  transform: translateX(0); }}
      .bargrow {{ animation: none !important; transform: scaleX(1); }}
      .trace {{ animation: none !important; stroke-dashoffset: 0; }}
      .lit {{ animation: none !important; opacity: 1; }}
      .fade1 {{ animation: none !important; opacity: 1; }}
      .tab, .tl0, .tl1, .tl2, .tl3 {{ animation: none !important; }}
      .tab0 {{ opacity: 1; }}
      .tl0 {{ opacity: 1; fill: {accent}; }}
    }}''')

    o.append(f'<style>{"".join(css)}\n    </style>')
    o.append('</svg>')
    return "\n".join(o)


# =============================================================================

def main():
    out = Path(__file__).resolve().parent
    assets = out / "assets"
    assets.mkdir(exist_ok=True)
    cache = out / "cache" / "data.json"
    cache.parent.mkdir(parents=True, exist_ok=True)

    if "--mock" in sys.argv:
        data = mock()
    else:
        token = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("Faltou o token. Defina ACCESS_TOKEN ou rode com --mock.")
        try:
            data = fetch(CONFIG["username"], token)
            cache.write_text(json.dumps(data, indent=2))
        except Exception as e:
            # Se a API cair, reusa o ultimo resultado bom em vez de quebrar o build.
            print(f"API falhou ({e}); usando cache.", file=sys.stderr)
            if not cache.exists():
                raise
            data = json.loads(cache.read_text())

    for theme in ("dark", "light"):
        path = assets / f"terminal-{theme}.svg"
        path.write_text(render(data, theme), encoding="utf-8")
        print(f"  {path.relative_to(out)}  ({path.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
