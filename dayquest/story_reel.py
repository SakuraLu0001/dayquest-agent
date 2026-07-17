"""Self-contained animated reel for existing DayQuest scenes."""

from __future__ import annotations

import html
from typing import Sequence

from .models import Scene


MOTIF_THEMES = {
    "MIST_GATE": "mist",
    "CLOCKWORK_TRIAL": "clockwork",
    "RUNE_STORM": "rune",
    "SKY_CARAVAN": "sky",
    "MIRROR_SPIRIT": "mirror",
}


def motif_theme(motif: str | None) -> str:
    return MOTIF_THEMES.get(motif or "", "default")


def render_story_reel_html(scenes: Sequence[Scene], selected_motif: str | None = None) -> str:
    visible = list(scenes[:5])
    if not visible:
        return '<div class="dq-empty">Story reel will appear after a successful Agent run.</div>'
    esc = lambda value: html.escape(str(value), quote=True)
    panels = "".join(
        f'''<section class="dq-scene" data-scene="{i}"><div class="glow"></div>
        <div class="counter">Scene {i + 1} / {len(visible)}</div><div class="copy">
        <div class="time">{esc(scene.approximate_time)}</div><h2>{esc(scene.title)}</h2>
        <p>{esc(scene.narration)}</p></div></section>'''
        for i, scene in enumerate(visible)
    )
    dots = "".join(f'<button class="dot" data-dot="{i}" aria-label="Scene {i + 1}"></button>' for i in range(len(visible)))
    static = " static" if len(visible) < 3 else ""
    script = "" if static else '''<script>(()=>{const r=document.getElementById("dq-reel"),s=[...r.querySelectorAll("[data-scene]")],d=[...r.querySelectorAll("[data-dot]")];let n=0,t=null;function show(i){clearTimeout(t);s.forEach((x,j)=>x.classList.toggle("active",i===j));d.forEach((x,j)=>x.classList.toggle("active",i===j));n=i;if(n<s.length-1)t=setTimeout(()=>show(n+1),3800)}function replayStoryReel(){show(0)}r.querySelector("[data-replay]").addEventListener("click",replayStoryReel);show(0)})();</script>'''
    theme = motif_theme(selected_motif)
    return f'''<style>
    *{{box-sizing:border-box}}body{{margin:0;background:transparent;color:#f8f5ff;font-family:system-ui,sans-serif}}
    .reel{{--a:#bda8ff;--g:#6d5cda;--b1:#10152c;--b2:#35204f;position:relative;width:100%;aspect-ratio:16/9;min-height:360px;max-height:520px;overflow:hidden;border-radius:18px;background:linear-gradient(135deg,var(--b1),var(--b2));box-shadow:0 18px 50px #0008}}
    .theme-mist{{--a:#dcf5ff;--g:#9dd7e8;--b1:#0b1928;--b2:#385669}}.theme-clockwork{{--a:#f1c46d;--g:#c9842f;--b1:#1a1109;--b2:#4b2d13}}.theme-rune{{--a:#c9a8ff;--g:#7358ff;--b1:#110d32;--b2:#422172}}.theme-sky{{--a:#f7e9bd;--g:#91d6ff;--b1:#102544;--b2:#587ea8}}.theme-mirror{{--a:#e4f5ff;--g:#8bd8ff;--b1:#101a2a;--b2:#35506d}}
    .reel:after{{content:"";position:absolute;inset:0;z-index:5;pointer-events:none;box-shadow:inset 0 0 95px #000b}}.dq-scene{{position:absolute;inset:0;opacity:0;visibility:hidden;transition:opacity .55s}}.dq-scene.active{{opacity:1;visibility:visible}}
    .glow{{position:absolute;width:65%;height:85%;left:-12%;top:-25%;border-radius:50%;background:radial-gradient(circle,var(--g),transparent 68%);filter:blur(24px);opacity:.52;animation:drift 3.8s ease-out both}}.dq-scene:before{{content:"";position:absolute;inset:-20%;opacity:.16;background:repeating-radial-gradient(circle at 75% 35%,transparent 0 34px,var(--a) 35px 36px);animation:pan 9s linear infinite}}
    .copy{{position:absolute;left:8%;right:15%;bottom:17%;z-index:3;text-shadow:0 3px 18px #000}}.time{{color:var(--a);letter-spacing:.18em;text-transform:uppercase}}h2{{font:700 clamp(1.8rem,4vw,3.5rem)/1.05 Georgia,serif;margin:.5rem 0 .7rem}}p{{max-width:760px;font-size:clamp(.9rem,1.7vw,1.15rem);line-height:1.55;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}}.active .copy>*{{animation:copy .7s both}}.active h2{{animation-delay:.3s}}.active p{{animation-delay:.65s}}
    .counter{{position:absolute;right:5%;top:7%;z-index:6;color:var(--a);background:#080a1499;padding:.4rem .75rem;border-radius:99px}}.controls{{position:absolute;left:0;right:0;bottom:4%;z-index:7;display:flex;justify-content:center;gap:.55rem}}.dot{{width:8px;height:8px;padding:0;border:0;border-radius:50%;background:#fff5}}.dot.active{{background:var(--a);box-shadow:0 0 12px var(--g)}}.replay{{position:absolute;right:4%;bottom:3%;z-index:8;border:1px solid var(--a);border-radius:99px;background:#080a1499;color:white;padding:.45rem .8rem;cursor:pointer}}
    .static{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1px}}.static .dq-scene{{position:relative;opacity:1;visibility:visible;min-height:360px}}.static .copy>*{{animation:none;opacity:1}}.static .controls,.static .replay{{display:none}}.dq-empty{{padding:1rem;background:#17243a;border-radius:12px;color:#dce8ff}}
    @keyframes copy{{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:none}}}}@keyframes drift{{to{{transform:scale(1.14) translate(8%,5%)}}}}@keyframes pan{{to{{transform:translateX(8%) rotate(5deg)}}}}
    </style><div id="dq-reel" class="reel theme-{theme}{static}">{panels}<div class="controls">{dots}</div><button class="replay" data-replay>Replay Story Reel</button></div>{script}'''
