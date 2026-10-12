#!/usr/bin/env python3
"""Build the macOS-desktop profile: desktop.svg + a clickable Dock (dock/*.svg).

The README places desktop.svg full width, then the Dock as one row of separate
images (each icon wrapped in its own link) whose widths add up to 100%, so the
row lines up exactly under the desktop.

Runs daily in a GitHub Action: the menu bar date and the notification (latest
public push) are refreshed. Without GITHUB_TOKEN it falls back to static text.
"""
from __future__ import annotations

import base64
import datetime as dt
import io
import json
import os
import random
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

USER = "NoahSmo"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"   # clawdio's real icon and sprite sheet (from NoahSmo/clawdio/docs)


def data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def clawdio_icon() -> str:
    return data_uri(Image.open(ASSETS / "clawdio-icon.png").convert("RGBA"))


def clawdio_frames() -> list[str]:
    """The 8 real Clawdio avatar frames: 128x128 cells every 152px in docs/avatar.png."""
    sheet = Image.open(ASSETS / "clawdio-avatar.png").convert("RGBA")
    frames = []
    for i in range(8):
        cell = sheet.crop((152 * i, 0, 152 * i + 128, 128))
        frames.append(data_uri(cell.resize((16, 16), Image.NEAREST)))  # back to the native 16x16 pixels
    return frames

W, H = 1000, 540          # desktop canvas
DOCK_H = 100              # dock row height, same scale as the desktop
GROUND = "#150f2e"        # skyline colour, continues into the dock row
SANS = '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif'
MONO = '"SF Mono", ui-monospace, Menlo, Consolas, "DejaVu Sans Mono", "Liberation Mono", monospace'

DAYS = ["Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam.", "Dim."]
MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def fr_date(d: dt.date, weekday: bool = True) -> str:
    s = f"{d.day} {MONTHS[d.month - 1]}"
    return f"{DAYS[d.weekday()]} {s}" if weekday else s


# ------------------------------------------------------------------- data ---

def latest_push() -> dict | None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return None
    req = urllib.request.Request(
        f"https://api.github.com/users/{USER}/events/public?per_page=50",
        headers={"Authorization": f"Bearer {token}", "User-Agent": USER,
                 "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            events = json.load(r)
    except Exception as e:
        print("events unavailable:", e)
        return None
    for ev in events:
        if ev.get("type") != "PushEvent":
            continue
        commits = ev.get("payload", {}).get("commits") or []
        if not commits:
            continue
        msg = commits[-1]["message"].splitlines()[0]
        when = dt.datetime.fromisoformat(ev["created_at"].replace("Z", "+00:00")).date()
        return {"repo": ev["repo"]["name"].split("/")[-1], "msg": msg, "date": when}
    return None


def clip(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


# ---------------------------------------------------------------- desktop ---

def skyline() -> str:
    rnd = random.Random(76)  # 76 = Seine-Maritime, keeps the skyline stable between runs
    parts = []
    x = 0
    while x < W:
        bw = rnd.choice([34, 42, 50, 58, 66])
        top = rnd.randint(440, 482)
        if 520 < x < 640:  # leave room around the cathedral
            top = rnd.randint(468, 490)
        parts.append(f'<rect x="{x}" y="{top}" width="{bw + 1}" height="{H - top}" fill="{GROUND}"/>')
        for wy in range(top + 10, H - 12, 14):
            for wx in range(x + 7, x + bw - 8, 12):
                if rnd.random() < 0.16:
                    parts.append(f'<rect class="lit" x="{wx}" y="{wy}" width="5" height="6" fill="#ffd27a" style="animation-delay:{rnd.uniform(0, 6):.1f}s"/>')
        x += bw
    # Rouen cathedral: two towers and the tall cast-iron spire, pixel style
    cx = 584
    cath = [
        (cx - 70, 418, 28, 122), (cx + 42, 410, 28, 130),          # towers
        (cx - 64, 404, 16, 14), (cx + 48, 396, 16, 14),            # tower tops
        (cx - 44, 438, 88, 102),                                   # nave
        (cx - 14, 400, 28, 40), (cx - 9, 370, 18, 32),             # crossing tower
        (cx - 6, 330, 12, 42), (cx - 4, 290, 8, 42), (cx - 2, 240, 4, 52),  # spire
    ]
    for (bx, by, bw, bh) in cath:
        parts.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{GROUND}"/>')
    parts.append(f'<rect x="{cx - 1}" y="226" width="2" height="16" fill="{GROUND}"/>')
    return "".join(parts)


def stars() -> str:
    rnd = random.Random(14)
    out = []
    for _ in range(70):
        x, y = rnd.uniform(0, W), rnd.uniform(34, 300)
        r = rnd.choice([0.7, 0.9, 1.1, 1.4])
        cls = ' class="tw"' if rnd.random() < 0.35 else ""
        out.append(f'<circle{cls} cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#fff" opacity="{rnd.uniform(.35, .9):.2f}" style="animation-delay:{rnd.uniform(0, 4):.1f}s"/>')
    return "".join(out)


def window(x, y, w, h, title, body, dark=True) -> str:
    bg = "#1f1d2b" if dark else "#f6f5fb"
    bar = "#2a2838" if dark else "#e7e5ef"
    tc = "#a9a6bd" if dark else "#5c5970"
    return f'''<g class="win" filter="url(#shadow)">
<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{bg}" opacity=".97"/>
<path d="M{x} {y + 12}a12 12 0 0 1 12-12h{w - 24}a12 12 0 0 1 12 12v18h-{w}z" fill="{bar}"/>
<line x1="{x}" y1="{y + 30}" x2="{x + w}" y2="{y + 30}" stroke="#000" stroke-opacity=".25"/>
<circle cx="{x + 18}" cy="{y + 15}" r="6" fill="#ff5f57"/><circle cx="{x + 38}" cy="{y + 15}" r="6" fill="#febc2e"/><circle cx="{x + 58}" cy="{y + 15}" r="6" fill="#28c840"/>
<text x="{x + w / 2}" y="{y + 19.5}" text-anchor="middle" class="sans" font-size="12.5" font-weight="600" fill="{tc}">{escape(title)}</text>
{body}
</g>'''


def about_window() -> str:
    x, y, w = 40, 70, 500
    tags = ["Python", "Next.js", "Swift", "SwiftUI", "Node.js", "C# · .NET", "PostgreSQL"]
    tx, ty, tag_svg = x + 28, y + 262, []
    for t in tags:
        tw = len(t) * 7.3 + 20
        if tx + tw > x + w - 24:
            tx, ty = x + 28, ty + 30
        tag_svg.append(f'<rect x="{tx:.0f}" y="{ty}" width="{tw:.0f}" height="22" rx="11" fill="#2f2b45" stroke="#4a4470"/>'
                       f'<text x="{tx + tw / 2:.0f}" y="{ty + 15}" text-anchor="middle" class="sans" font-size="12" fill="#cfc9ff">{escape(t)}</text>')
        tx += tw + 8
    h = ty + 22 + 22 - y
    lines = [
        ("Hi, I'm Noah", 26, 700, "#ffffff", 70),
        ("French developer based in Rouen.", 15.5, 400, "#d9d6ea", 108),
        ("Next.js & Python (AI) at Wesur.", 15.5, 400, "#d9d6ea", 134),
        ("After hours: native macOS apps in Swift —", 15.5, 400, "#d9d6ea", 166),
        ("things that live in your notch & menu bar.", 15.5, 400, "#d9d6ea", 190),
        ("Free time: making games.", 15.5, 400, "#d9d6ea", 222),
    ]
    body = "".join(
        f'<text x="{x + 28}" y="{y + ly}" class="sans" font-size="{fs}" font-weight="{fw}" fill="{c}">{escape(t)}</text>'
        for t, fs, fw, c, ly in lines)
    body += f'<rect x="{x + 28 + 158}" y="{y + 50}" width="2" height="26" fill="#9d8cff" class="cur"/>'
    body += "".join(tag_svg)
    return window(x, y, w, h, "about-me.md", body)


def terminal_window(today: dt.date) -> str:
    x, y, w, h = 612, 214, 360, 160
    rows = [
        (f"Last login: {fr_date(today)} on ttys001", "#8b87a3", 0.6),
        ("~ % brew install --cask NoahSmo/clawdio/clawdio", "#e6e3f5", 1.3),
        ("==> clawdio was successfully installed!", "#7ee787", 2.0),
        ("~ % brew install --cask noahsmo/tap/hiddenbar", "#e6e3f5", 2.7),
        ("==> hiddenbar was successfully installed!", "#7ee787", 3.4),
    ]
    body = ""
    for i, (t, col, d) in enumerate(rows):
        body += f'<text x="{x + 14}" y="{y + 54 + i * 19}" class="mono f" font-size="11" fill="{col}" style="animation-delay:{d}s">{escape(t)}</text>'
    py = y + 54 + len(rows) * 19
    body += f'<g class="f" style="animation-delay:4s"><text x="{x + 14}" y="{py}" class="mono" font-size="11" fill="#e6e3f5">~ %</text>'
    body += f'<rect class="cur" x="{x + 42}" y="{py - 10}" width="7" height="13" fill="#e6e3f5"/></g>'
    return window(x, y, w, h, "noah — zsh — 80×24", body)


def notification(push: dict | None, today: dt.date) -> str:
    x, y, w, h = 652, 42, 320, 68
    is_clawdio = not push or push["repo"].lower() == "clawdio"
    if push:
        title = f"Pushed to {push['repo']}"
        msg = clip(push["msg"], 42)
        when = "aujourd'hui" if push["date"] == today else fr_date(push["date"], weekday=False)
    else:
        title, msg, when = "clawdio", "Claude Code quota, right in your notch", "maintenant"
    if is_clawdio:
        icon = f'<image x="{x + 10}" y="{y + 13}" width="42" height="42" href="{clawdio_icon()}"/>'
    else:
        icon = (f'<rect x="{x + 12}" y="{y + 15}" width="38" height="38" rx="9" fill="#14121f"/>'
                f'<circle cx="{x + 24}" cy="{y + 25}" r="3.4" fill="none" stroke="#7ee787" stroke-width="2"/>'
                f'<circle cx="{x + 24}" cy="{y + 43}" r="3.4" fill="none" stroke="#7ee787" stroke-width="2"/>'
                f'<circle cx="{x + 39}" cy="{y + 29}" r="3.4" fill="none" stroke="#7ee787" stroke-width="2"/>'
                f'<path d="M{x + 24} {y + 28.5}v11M{x + 39} {y + 32.5}c0 6-15 3-15 7" fill="none" stroke="#7ee787" stroke-width="2"/>')
    return f'''<g class="notif" filter="url(#shadow)">
<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="#2b2840" opacity=".96" stroke="#ffffff" stroke-opacity=".08"/>
{icon}
<text x="{x + 62}" y="{y + 29}" class="sans" font-size="13" font-weight="700" fill="#fff">{escape(title)}</text>
<text x="{x + w - 14}" y="{y + 29}" text-anchor="end" class="sans" font-size="11.5" fill="#9e9ab5">{escape(when)}</text>
<text x="{x + 62}" y="{y + 49}" class="sans" font-size="12.5" fill="#d6d3e8">{escape(msg)}</text>
</g>'''


def menubar(today: dt.date) -> str:
    items = [("Noah", 700), ("File", 400), ("Edit", 400), ("Projects", 400), ("Wesur", 400), ("Help", 400)]
    out = [f'<rect width="{W}" height="28" fill="#0d0a1c" opacity=".55"/>']
    # custom pixel "N" mark instead of a brand logo
    n = ["1001", "1101", "1011", "1001"]
    for r, row in enumerate(n):
        for c, ch in enumerate(row):
            if ch == "1":
                out.append(f'<rect x="{18 + c * 3}" y="{8 + r * 3}" width="3" height="3" fill="#fff"/>')
    x = 44
    for label, fw in items:
        out.append(f'<text x="{x}" y="18.5" class="sans" font-size="13" font-weight="{fw}" fill="#fff">{label}</text>')
        x += len(label) * 7.1 + (26 if fw == 700 else 21)
    # right side: wifi, battery, date
    rx = W - 18
    date = fr_date(today)
    out.append(f'<text x="{rx}" y="18.5" text-anchor="end" class="sans" font-size="13" fill="#fff">{escape(date)}</text>')
    bx = rx - len(date) * 7.2 - 44
    out.append(f'<rect x="{bx}" y="9" width="22" height="11" rx="3" fill="none" stroke="#fff" stroke-opacity=".9"/>'
               f'<rect x="{bx + 2}" y="11" width="15" height="7" rx="1.5" fill="#fff"/>'
               f'<rect x="{bx + 23}" y="12.5" width="2" height="4" rx="1" fill="#fff" opacity=".9"/>')
    wx = bx - 22
    out.append(f'<path d="M{wx - 8} 13a11 11 0 0 1 16 0M{wx - 5} 16a6.5 6.5 0 0 1 10 0" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/>'
               f'<circle cx="{wx}" cy="19.5" r="1.6" fill="#fff"/>')
    return "".join(out)


def notch() -> str:
    """Clawdio's pill, as in the app: quota ring + reset time on the left, Clawd on the right,
    and the orange → rose → violet → blue halo running along the sides and bottom."""
    x, w, h, r = 365, 270, 40, 16
    pill = f'M{x - 10} 0h{w + 20}c-7 0-10 4-10 10v{h - 10 - r}a{r} {r} 0 0 1-{r} {r}h-{w - 2 * r}a{r} {r} 0 0 1-{r}-{r}V10c0-6-3-10-10-10z'
    edge = f'M{x} 6V{h - r}a{r} {r} 0 0 0 {r} {r}h{w - 2 * r}a{r} {r} 0 0 0 {r}-{r}V6'
    cx, cy, rr = x + 22, 20, 8.5
    circ = 2 * 3.14159 * rr
    ring = (f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="none" stroke="#fff" stroke-opacity=".16" stroke-width="3.2"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="none" stroke="#5fd47c" stroke-width="3.2" stroke-linecap="round" '
            f'stroke-dasharray="{circ * .42:.1f} {circ:.1f}" transform="rotate(-90 {cx} {cy})"/>')
    clock = f'<text x="{x + 40}" y="25" class="mono" font-size="13.5" font-weight="800" fill="#fff" letter-spacing=".5">12:41PM</text>'
    frames = "".join(
        f'<image class="fr" x="{x + w - 46}" y="3" width="32" height="32" href="{uri}" '
        f'style="image-rendering:pixelated;animation-delay:{i * 1.5}s"/>'
        for i, uri in enumerate(clawdio_frames()))
    return (f'<g filter="url(#halo)"><path d="{edge}" fill="none" stroke="url(#halograd)" stroke-width="5" stroke-linecap="round"/></g>'
            f'<path d="{edge}" fill="none" stroke="url(#halograd)" stroke-width="1.6" stroke-linecap="round"/>'
            f'<path d="{pill}" fill="#000"/>{ring}{clock}{frames}')


def desktop_svg(today: dt.date, push: dict | None) -> str:
    css = f"""
.sans {{ font-family: {SANS}; }}
.mono {{ font-family: {MONO}; white-space: pre; }}
.tw {{ animation: tw 3.2s ease-in-out infinite; }}
@keyframes tw {{ 50% {{ opacity: .1; }} }}
.lit {{ animation: lit 7s step-end infinite; }}
@keyframes lit {{ 70% {{ opacity: 1; }} 80% {{ opacity: .15; }} }}
.blink {{ opacity: 0; animation: blink 4s step-end infinite; }}
@keyframes blink {{ 0%, 92% {{ opacity: 0; }} 94% {{ opacity: 1; }} 97% {{ opacity: 0; }} }}
.bob {{ animation: bob 2.4s ease-in-out infinite; }}
@keyframes bob {{ 50% {{ transform: translateY(1px); }} }}
.st {{ opacity: 0; animation: st 12s infinite; }}
@keyframes st {{ 0% {{ opacity: 0; }} 3%, 22% {{ opacity: 1; }} 25%, 100% {{ opacity: 0; }} }}
.pulse {{ animation: pulse 2s ease-in-out infinite; }}
@keyframes pulse {{ 50% {{ opacity: .35; }} }}
.cur {{ animation: cur 1.1s step-end infinite; }}
.fr {{ opacity: 0; animation: fr 12s step-end infinite; }}
@keyframes fr {{ 0% {{ opacity: 1; }} 12.5% {{ opacity: 0; }} }}
@keyframes cur {{ 50% {{ opacity: 0; }} }}
.f {{ opacity: 0; animation: f .2s ease-out forwards; }}
@keyframes f {{ to {{ opacity: 1; }} }}
.notif {{ transform: translateX(360px); animation: notif .6s cubic-bezier(.2,.9,.3,1.2) 1.2s forwards; }}
@keyframes notif {{ to {{ transform: none; }} }}
@media (prefers-reduced-motion: reduce) {{
  .tw, .lit, .bob, .pulse, .cur {{ animation: none; }}
  .blink {{ animation: none; opacity: 0; }}
  .f {{ animation: none; opacity: 1; }}
  .notif {{ animation: none; transform: none; }}
  .fr {{ animation: none; }} .fr:first-of-type {{ opacity: 1; }}
}}"""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
<title id="t">noah@rouen — desktop</title>
<desc id="d">A macOS-style desktop for Noah (NoahSmo): an about-me window (French developer in Rouen, Next.js and Python AI at Wesur, native macOS apps in Swift, makes games), a terminal installing clawdio and HiddenBar with Homebrew, a notification with the latest GitHub push, and a pixel-art Rouen skyline at dusk.</desc>
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#140f33"/><stop offset=".38" stop-color="#3b2466"/>
<stop offset=".66" stop-color="#a8457a"/><stop offset=".82" stop-color="#ec7e5c"/><stop offset="1" stop-color="#f6b26b"/>
</linearGradient>
<radialGradient id="sun" cx=".58" cy=".86" r=".32"><stop offset="0" stop-color="#ffd9a0" stop-opacity=".85"/><stop offset="1" stop-color="#ffd9a0" stop-opacity="0"/></radialGradient>
<filter id="shadow" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="10" stdDeviation="12" flood-color="#000" flood-opacity=".45"/></filter>
<linearGradient id="halograd" gradientUnits="userSpaceOnUse" x1="365" y1="0" x2="905" y2="0" spreadMethod="reflect">
<stop offset="0" stop-color="#ff9e5c"/><stop offset=".33" stop-color="#fa73ad"/><stop offset=".66" stop-color="#a870ff"/><stop offset="1" stop-color="#739eff"/>
<animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="-540 0" dur="6s" repeatCount="indefinite"/>
</linearGradient>
<filter id="halo" x="-20%" y="-60%" width="140%" height="260%"><feGaussianBlur stdDeviation="6"/></filter>
<clipPath id="screen"><path d="M0 16a16 16 0 0 1 16-16h{W - 32}a16 16 0 0 1 16 16V{H}H0z"/></clipPath>
</defs>
<style>{css}</style>
<g clip-path="url(#screen)">
<rect width="{W}" height="{H}" fill="url(#sky)"/>
<rect width="{W}" height="{H}" fill="url(#sun)"/>
{stars()}
{skyline()}
<rect y="{H - 40}" width="{W}" height="40" fill="{GROUND}"/>
{about_window()}
{terminal_window(today)}
{notification(push, today)}
{menubar(today)}
{notch()}
</g>
</svg>
'''


# ------------------------------------------------------------------- dock ---

SHELF_Y, SHELF_H = 12, 80
SHELF = "#2e2748"
SHELF_EDGE = "#4b4370"
ICON = 64
SEG = 80


def seg_svg(width: float, inner: str, style: str = "") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:g}" height="{DOCK_H}" viewBox="0 0 {width:g} {DOCK_H}">'
            + (f"<style>{style}</style>" if style else "") + inner + "</svg>\n")


def shelf(width: float) -> str:
    return (f'<rect width="{width:g}" height="{DOCK_H}" fill="{GROUND}"/>'
            f'<rect y="{SHELF_Y}" width="{width:g}" height="{SHELF_H}" fill="{SHELF}"/>'
            f'<rect y="{SHELF_Y}" width="{width:g}" height="1" fill="{SHELF_EDGE}"/>'
            f'<rect y="{SHELF_Y + SHELF_H - 1}" width="{width:g}" height="1" fill="{SHELF_EDGE}"/>')


def icon_frame(art: str, running: bool, bounce: bool = False) -> str:
    ox, oy = (SEG - ICON) / 2, SHELF_Y + 7
    g = f'<g transform="translate({ox} {oy})"><g class="{"bounce" if bounce else ""}">{art}</g></g>'
    dot = f'<circle cx="{SEG / 2}" cy="{SHELF_Y + SHELF_H - 5}" r="2.2" fill="#d8d3ff"/>' if running else ""
    return shelf(SEG) + g + dot


def squircle(fill: str, extra: str = "") -> str:
    return f'<rect width="{ICON}" height="{ICON}" rx="15" fill="{fill}"/>{extra}'


def grad(id_: str, a: str, b: str) -> str:
    return f'<defs><linearGradient id="{id_}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs>'


ICONS = [
    # (file, title, url, art, running, bounce)
    ("repos", "Repositories", f"https://github.com/{USER}?tab=repositories",
     grad("g", "#64b5ff", "#2c6be0") + squircle("url(#g)",
        '<rect x="12" y="17" width="18" height="9" rx="2.5" fill="#cfe6ff"/>'
        '<rect x="12" y="21" width="40" height="27" rx="4" fill="#dcedff"/>'
        '<rect x="12" y="26" width="40" height="22" rx="4" fill="#fff"/>'
        '<rect x="18" y="33" width="28" height="3" rx="1.5" fill="#b9d6ff"/>'), False, False),
    ("clawdio", "clawdio — your Claude Code quota in the notch", f"https://github.com/{USER}/clawdio",
     None, True, True),  # art = the real app icon, filled in by dock_files()
    ("hiddenbar", "HiddenBar — hide menu bar icons", f"https://github.com/{USER}/HiddenBar",
     grad("g", "#f3f6fb", "#c7d1e0") + squircle("url(#g)",
        '<rect x="7" y="21" width="50" height="14" rx="4" fill="#fff" stroke="#b9c4d6"/>'
        '<circle cx="15" cy="28" r="2.6" fill="#55607a"/><circle cx="23" cy="28" r="2.6" fill="#55607a"/>'
        '<path d="M33 24l-4 4 4 4" fill="none" stroke="#2f6fe0" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
        '<circle cx="41" cy="28" r="2.6" fill="#55607a" opacity=".2"/><circle cx="49" cy="28" r="2.6" fill="#55607a" opacity=".2"/>'
        '<rect x="16" y="42" width="32" height="4" rx="2" fill="#a7b3c8"/>'), True, False),
    ("homebrew-tap", "homebrew-tap — brew install my apps", f"https://github.com/{USER}/homebrew-tap",
     grad("g", "#26252b", "#121116") + squircle("url(#g)",
        '<rect x="6" y="6" width="52" height="52" rx="10" fill="none" stroke="#3a3942"/>'
        '<path d="M15 24l8 7-8 7" fill="none" stroke="#7ee787" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>'
        '<rect x="27" y="36" width="16" height="3.2" rx="1.6" fill="#7ee787"/>'), False, False),
    ("contact", "Contact me on LinkedIn", "https://linkedin.com/in/noah-smo",
     grad("g", "#c99566", "#8a5631") + squircle("url(#g)",
        '<rect x="10" y="8" width="44" height="48" rx="6" fill="#f7efe6"/>'
        '<circle cx="32" cy="27" r="8" fill="#a77a55"/>'
        '<path d="M18 50c0-9 6-13 14-13s14 4 14 13z" fill="#a77a55"/>'
        '<rect x="6" y="16" width="5" height="6" rx="1.5" fill="#d9c5b1"/><rect x="6" y="30" width="5" height="6" rx="1.5" fill="#d9c5b1"/>'), False, False),
]
TRASH = ("trash", "Trash — archived repos", f"https://github.com/{USER}?tab=repositories&type=archived",
         '<path d="M17 22h30l-3 32a4 4 0 0 1-4 3.6H24a4 4 0 0 1-4-3.6z" fill="#d7dcf0" fill-opacity=".22" stroke="#cfd5ec" stroke-width="1.5"/>'
         '<rect x="14" y="16" width="36" height="6" rx="2" fill="#d7dcf0" fill-opacity=".35" stroke="#cfd5ec" stroke-width="1.5"/>'
         '<path d="M27 28l1 24M32 28v24M37 28l-1 24" stroke="#cfd5ec" stroke-opacity=".7" stroke-width="1.4"/>', False, False)

BOUNCE_CSS = (".bounce{animation:bounce 1.4s ease-out 1.6s 1}"
              "@keyframes bounce{0%,100%{transform:none}15%{transform:translateY(-14px)}30%{transform:none}45%{transform:translateY(-8px)}60%{transform:none}}"
              "@media (prefers-reduced-motion:reduce){.bounce{animation:none}}")

CAP = 20
SEP = 24


def dock_files() -> list[dict]:
    """Return the dock segments in order: {file, width, svg, url?, title?}."""
    segs = []
    n_icons = len(ICONS) + 1
    inner = CAP * 2 + SEP + SEG * n_icons
    filler = (W - inner) / 2

    r = 16  # bottom corners of the screen
    fw = filler + CAP
    # left: screen corner + left end of the dock shelf, in one image (fewer seams)
    left = (f'<path d="M0 0h{fw:g}v{DOCK_H}H{r}a{r} {r} 0 0 1-{r}-{r}z" fill="{GROUND}"/>'
            f'<path d="M{fw:g} {SHELF_Y}h-2a18 18 0 0 0-18 18v{SHELF_H - 36}a18 18 0 0 0 18 18h2z" fill="{SHELF}"/>'
            f'<path d="M{fw:g} {SHELF_Y + .5}h-2a17.5 17.5 0 0 0-17.5 17.5v{SHELF_H - 35}a17.5 17.5 0 0 0 17.5 17.5h2" fill="none" stroke="{SHELF_EDGE}"/>')
    segs.append(dict(file="00-left.svg", width=fw, svg=seg_svg(fw, left)))
    for i, (name, title, url, art, running, bounce) in enumerate(ICONS):
        if art is None:  # real app icon (it has its own transparent margin, like a macOS .icns)
            art = f'<image x="-9" y="-9" width="{ICON + 18}" height="{ICON + 18}" href="{clawdio_icon()}"/>'
        segs.append(dict(file=f"{i + 1:02d}-{name}.svg", width=SEG, url=url, title=title,
                         svg=seg_svg(SEG, icon_frame(art, running, bounce), BOUNCE_CSS if bounce else "")))
    # separator + trash in one image
    name, title, url, art, running, bounce = TRASH
    tw = SEP + SEG
    trash = (shelf(tw) + f'<rect x="{SEP / 2 - .5}" y="{SHELF_Y + 14}" width="1" height="{SHELF_H - 28}" fill="#6a6194"/>'
             + f'<g transform="translate({SEP} 0)">{icon_frame(art, running)[len(shelf(SEG)):]}</g>')
    segs.append(dict(file=f"{len(ICONS) + 1:02d}-{name}.svg", width=tw, url=url, title=title, svg=seg_svg(tw, trash)))
    right = (f'<path d="M0 0h{fw:g}v{DOCK_H - r}a{r} {r} 0 0 1-{r} {r}H0z" fill="{GROUND}"/>'
             f'<path d="M0 {SHELF_Y}h2a18 18 0 0 1 18 18v{SHELF_H - 36}a18 18 0 0 1-18 18h-2z" fill="{SHELF}"/>'
             f'<path d="M0 {SHELF_Y + .5}h2a17.5 17.5 0 0 1 17.5 17.5v{SHELF_H - 35}a17.5 17.5 0 0 1-17.5 17.5h-2" fill="none" stroke="{SHELF_EDGE}"/>')
    segs.append(dict(file=f"{len(ICONS) + 2:02d}-right.svg", width=fw, svg=seg_svg(fw, right)))
    return segs


def readme(segs: list[dict]) -> str:
    imgs = []
    for s in segs:
        pct = f"{s['width'] / W * 100:.4g}%"
        if "url" in s:
            imgs.append(f'<a href="{s["url"]}"><img src="dock/{s["file"]}" width="{pct}" align="top" '
                        f'alt="{escape(s["title"])}" title="{escape(s["title"])}"></a>')
        else:
            imgs.append(f'<img src="dock/{s["file"]}" width="{pct}" align="top" alt="">')
    # no whitespace between the dock images, or the browser inserts gaps
    return (f'<p align="center"><a href="https://github.com/{USER}"><img src="desktop.svg" width="100%" align="top" '
            'alt="Noah\'s desktop: French developer in Rouen, Next.js &amp; Python (AI) at Wesur, building native macOS apps in Swift and games."></a><br>'
            + "".join(imgs) + "</p>\n\n"
            "<!-- desktop.svg is refreshed daily by .github/workflows/desktop.yml (scripts/desktop.py). "
            "Dock icons are clickable. -->\n")


def main() -> None:
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=2))).date()
    push = latest_push()
    (ROOT / "desktop.svg").write_text(desktop_svg(today, push), encoding="utf-8")
    dock = ROOT / "dock"
    dock.mkdir(exist_ok=True)
    segs = dock_files()
    for s in segs:
        (dock / s["file"]).write_text(s["svg"], encoding="utf-8")
    (ROOT / "README.md").write_text(readme(segs), encoding="utf-8")
    print("desktop.svg, README.md and", len(segs), "dock segments written; push:", push)


if __name__ == "__main__":
    main()
