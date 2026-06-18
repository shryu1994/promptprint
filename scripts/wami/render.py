"""Promptprint 리포트 렌더러 — insights.json + aggregates.json → self-contained HTML.

의존성 0(표준 라이브러리만), 네트워크 0(외부 폰트·스크립트 없음), 결정적.
디자인: "V3 Parchment Max" — 양피지·잉크·황동, 교차 full-bleed 블록,
        COLOSSAL display-serif 숫자, 항해/등고선 모티프, 극적인 서지 차트.
"""
import html as _html
from typing import Dict, List, Optional

from wami.fonts_css import FONT_FACE_CSS

# ── i18n ─────────────────────────────────────────────────────────────────────

LABELS = {
    "ko": {
        "nav_chart":      "항로도",
        "nav_bearings":   "방위",
        "nav_cards":      "기념엽서",
        "section_chart":  "항로도 — 활동량",
        "section_dims":   "방위 — 여섯 차원",
        "section_chaps":  "항해일지 — 장별 여정",
        "section_cards":  "기념엽서",
        "section_next":   "다음 항로",
        "chart_eyebrow":  "활동량",
        "chart_caption":  "막대 높이 = 월별 질문 수 · 숫자 = 해당 월 count",
        "dims_eyebrow":   "성장의 6가지 차원",
        "dims_sub":       "질문이 드러내는 작업 방식의 단면들.",
        "chaps_eyebrow":  "장별 항해 일지",
        "chaps_sub":      "질문이 달라진 국면들.",
        "cards_eyebrow":  "주목할 숫자들",
        "cards_sub":      "가지고 떠날 카드",
        "cards_hint":     "각 카드의 “이미지로 저장”을 누르면 PNG로 내려받을 수 있습니다.",
        "next_eyebrow":   "다음 항로",
        "next_heading":   "나침반이\n가리키는 곳",
        "next_sub":       "지금의 패턴을 읽고 다음에 집중할 방향.",
        "save_btn":       "이미지로 저장",
        "footer_made":    "made with Promptprint · 100% local",
        "field_journal":  "field journal no. 01",
        "total_q":        "총 질문",
        "by_tool":        "도구별",
        "period_label":   "기록 기간",
        "conf_prefix":    "데이터 신뢰도",
    },
    "en": {
        "nav_chart":      "Chart",
        "nav_bearings":   "Bearings",
        "nav_cards":      "Cards",
        "section_chart":  "Chart of Passage",
        "section_dims":   "Six Bearings",
        "section_chaps":  "Log Entries",
        "section_cards":  "Postcards",
        "section_next":   "Next Bearings",
        "chart_eyebrow":  "Activity",
        "chart_caption":  "Bar height = monthly question count · number = count for that month",
        "dims_eyebrow":   "Six Dimensions of Growth",
        "dims_sub":       "Cross-sections of your working style revealed by your questions.",
        "chaps_eyebrow":  "Voyage Log",
        "chaps_sub":      "The phases where your questions shifted.",
        "cards_eyebrow":  "Numbers to Remember",
        "cards_sub":      "Cards to Take With You",
        "cards_hint":     'Click "Save as image" on each card to download it as PNG.',
        "next_eyebrow":   "Next Bearings",
        "next_heading":   "Where the\nCompass Points",
        "next_sub":       "Reading the current patterns to find the next focus.",
        "save_btn":       "Save as image",
        "footer_made":    "made with Promptprint · 100% local",
        "field_journal":  "field journal no. 01",
        "total_q":        "Total Questions",
        "by_tool":        "By Tool",
        "period_label":   "Period",
        "conf_prefix":    "Data confidence",
    },
}

DIMENSION_ORDER = [
    ("topic_evolution", {"ko": "주제의 진화",    "en": "Topic Evolution"}),
    ("depth",           {"ko": "질문의 깊이",    "en": "Question Depth"}),
    ("metaskill",       {"ko": "AI 메타스킬",    "en": "AI Meta-skill"}),
    ("craft",           {"ko": "질문의 정교함",  "en": "Question Craft"}),
    ("mastery",         {"ko": "숙달의 흔적",    "en": "Mastery Traces"}),
    ("clusters",        {"ko": "당신만의 국면",  "en": "Your Clusters"}),
]

DIM_ICON_LABELS = {
    "topic_evolution": {"ko": "주제 진화", "en": "Topic"},
    "depth":           {"ko": "깊이",      "en": "Depth"},
    "metaskill":       {"ko": "메타스킬",  "en": "Meta-skill"},
    "craft":           {"ko": "제작 공예", "en": "Craft"},
    "mastery":         {"ko": "숙달",      "en": "Mastery"},
    "clusters":        {"ko": "클러스터",  "en": "Clusters"},
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _esc(s) -> str:
    return _html.escape(str(s), quote=True)


def _fmt_int(n) -> str:
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return _esc(n)


def _lbl(labels: dict, key: str) -> str:
    return _esc(labels.get(key, key))


# ── surge chart ───────────────────────────────────────────────────────────────

def _surge_chart_html(by_month: Dict[str, int], avg_len: Dict[str, float]) -> str:
    """V3 스타일의 극적인 세로막대 차트 (inline SVG)."""
    months = sorted(by_month)
    if not months:
        return '<p style="color:var(--ink-muted);font-family:ui-monospace,Menlo,monospace;font-size:13px;">데이터 없음</p>'

    max_count = max(by_month.values()) or 1
    chart_height = 320  # px — this is the visual max bar height

    bars_html = []
    for m in months:
        count = by_month[m]
        bar_pct = count / max_count  # 0..1
        bar_h = max(4, int(bar_pct * chart_height))  # min 4px so it's visible
        is_max = count == max_count
        avg = avg_len.get(m, 0) if avg_len else 0

        # bar colour: max month gets dark ink, others get muted tones
        if is_max:
            bar_color = "var(--ink)"
        elif bar_pct > 0.3:
            bar_color = "var(--brass-dim)"
        else:
            bar_color = "var(--ink-muted)"

        num_cls = ' class="surge-bar-num big"' if is_max else ' class="surge-bar-num"'
        avg_str = _fmt_int(int(avg)) + "자" if avg else ""
        label_parts = _esc(m.replace("-", "."))
        if avg_str:
            label_parts += f"<br>평균 {_esc(avg_str)}"

        bars_html.append(
            f'<div class="surge-month">'
            f'<div{num_cls}>{_fmt_int(count)}</div>'
            f'<div class="surge-bar-wrap">'
            f'<div class="surge-bar" style="height:{bar_h}px;background:{bar_color};'
            f'animation:barRise 1.4s cubic-bezier(.16,1,.3,1) both;"></div>'
            f'</div>'
            f'<div class="surge-divider"></div>'
            f'<div class="surge-bar-label">{label_parts}</div>'
            f'</div>'
        )

    return (
        '<div class="surge-chart-wrap">' +
        "".join(bars_html) +
        '</div><div class="surge-baseline"></div>'
    )


# ── dimension block ────────────────────────────────────────────────────────────

def _dimension_block(key: str, label: str, icon_label: str, dim: dict) -> str:
    dim = dim or {}
    evidence_items = "".join(
        f"<li>{_esc(e)}</li>" for e in (dim.get("evidence") or [])
    )
    evidence_html = (
        f'<ul class="dim-evidence">{evidence_items}</ul>' if evidence_items else ""
    )
    return (
        f'<div class="dim-card">'
        f'<div class="dim-icon">{_esc(icon_label)}</div>'
        f'<div class="dim-title">{_esc(label)}</div>'
        f'<p class="dim-narrative">{_esc(dim.get("narrative", ""))}</p>'
        f'{evidence_html}'
        f'</div>'
    )


# ── chapter block ─────────────────────────────────────────────────────────────

def _chapter_block(c: dict, idx: int) -> str:
    num = f"{idx:02d}"
    return (
        f'<div class="chapter-item" style="position:relative;">'
        f'<div class="chapter-period">{_esc(c.get("period", ""))}<br><br>'
        f'<span style="font-family:\'PP Display\',Georgia,\'Iowan Old Style\',serif;'
        f'font-size:28px;font-weight:900;color:var(--brass-light);opacity:0.5;font-style:italic;">'
        f'{num}</span></div>'
        f'<div class="chapter-right">'
        f'<h3 class="chapter-title">{_esc(c.get("title", ""))}</h3>'
        f'<p class="chapter-narrative">{_esc(c.get("narrative", ""))}</p>'
        f'</div></div>'
    )


# ── card block ────────────────────────────────────────────────────────────────

def _card_block(c: dict, save_label: str) -> str:
    """Cards show headline/stat/caption only — no evidence, no raw question text."""
    return (
        f'<div class="share-card">'
        f'<div class="share-card-num">{_esc(c.get("headline", ""))}</div>'
        f'<div class="share-card-stat">{_esc(c.get("stat", ""))}</div>'
        f'<div class="share-card-caption">{_esc(c.get("caption", ""))}</div>'
        f'<button class="share-save-btn" type="button" onclick="saveCard(this)">{_esc(save_label)}</button>'
        f'</div>'
    )


# ── bearing block ─────────────────────────────────────────────────────────────

def _bearing_block(b: dict, idx: int) -> str:
    num = f"{idx:02d}"
    last_style = ""
    return (
        f'<div class="bearing-item">'
        f'<div class="bearing-num">{num}</div>'
        f'<div>'
        f'<div class="bearing-title">{_esc(b.get("title", ""))}</div>'
        f'<p class="bearing-why">{_esc(b.get("why", ""))}</p>'
        f'<p class="bearing-how">{_esc(b.get("how", ""))}</p>'
        f'</div></div>'
    )


# ── confidence badge ───────────────────────────────────────────────────────────

def _confidence_badge(meta: dict, conf_prefix: str) -> str:
    tier = meta.get("confidence_tier", "")
    if not tier or tier == "full":
        return ""
    note = _esc(meta.get("confidence_note", tier))
    prefix = _esc(conf_prefix)
    return (
        f'<div class="confidence-badge" role="status">'
        f'<span class="conf-prefix">{prefix}:</span> {note}'
        f'</div>'
    )


# ── month span helper ─────────────────────────────────────────────────────────

def _month_span(dr) -> str:
    if not dr or not dr[0] or not dr[1]:
        return "—"
    try:
        a = str(dr[0])[:7]
        b = str(dr[1])[:7]
        ay, am = (int(x) for x in a.split("-"))
        by_, bm = (int(x) for x in b.split("-"))
        months = (by_ - ay) * 12 + (bm - am) + 1
        return f"{months}개월"
    except (ValueError, AttributeError):
        return "—"


# ── CSS ───────────────────────────────────────────────────────────────────────

STYLE = """
/* ── CSS VARIABLES ── */
:root{
  --parchment:#F5EDD8;--parchment-light:#FAF5E8;--parchment-mid:#EAD9B4;
  --ink:#1C1207;--ink-mid:#2E1F08;--ink-soft:#4A3415;--ink-muted:#7A5C35;
  --brass:#B8873A;--brass-light:#D4A855;--brass-dim:#7A5520;
  --rust:#8B3A1F;--rust-light:#C05030;--cream:#FBF7EE;
  --deep-bg:#0F0A02;--deep-mid:#1A1005;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:Georgia,'Iowan Old Style',serif;background:var(--parchment);color:var(--ink);overflow-x:hidden;line-height:1.6;-webkit-font-smoothing:antialiased}

/* ── ANIMATIONS ── */
@keyframes fadeUp{from{opacity:0;transform:translateY(32px)}to{opacity:1;transform:translateY(0)}}
@keyframes inkDrop{0%{opacity:0;transform:scaleY(.6) scaleX(.9);filter:blur(8px)}60%{filter:blur(0)}100%{opacity:1;transform:scaleY(1) scaleX(1);filter:blur(0)}}
@keyframes lineGrow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes barRise{from{transform:scaleY(0);transform-origin:bottom}to{transform:scaleY(1);transform-origin:bottom}}
.anim-fadeup{animation:fadeUp .9s cubic-bezier(.16,1,.3,1) both}
.anim-inkdrop{animation:inkDrop 1.1s cubic-bezier(.16,1,.3,1) both}
.d1{animation-delay:.1s}.d2{animation-delay:.3s}.d3{animation-delay:.5s}
.d4{animation-delay:.7s}.d5{animation-delay:.9s}.d6{animation-delay:1.1s}

/* ── SECTION BLOCKS ── */
.section-parchment{background:var(--parchment);padding:120px 48px}
.section-dark{background:var(--deep-bg);padding:120px 48px;color:var(--parchment-light)}
.section-ink{background:var(--ink);padding:120px 48px;color:var(--parchment)}
.surge-section{background:var(--parchment-light);padding:120px 48px;position:relative;overflow:hidden}

.container{max-width:960px;margin:0 auto}

/* ── HERO ── */
.hero{background:var(--deep-bg);min-height:100vh;display:flex;flex-direction:column;
  justify-content:center;align-items:flex-start;padding:80px 48px 120px;position:relative;overflow:hidden}
.hero-contour{position:absolute;inset:0;pointer-events:none;opacity:.07}
.hero-label{font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:.22em;text-transform:uppercase;
  color:var(--brass);margin-bottom:40px;border-left:2px solid var(--brass);padding-left:16px}
.hero-number{font-family:'PP Display',Georgia,'Iowan Old Style',serif;font-size:clamp(120px,22vw,240px);
  font-weight:900;line-height:.85;color:var(--parchment);letter-spacing:-.04em;display:block;margin-bottom:40px}
.hero-number em{color:var(--brass-light);font-style:normal}
.hero-headline{font-family:'PP Display',Georgia,'Iowan Old Style',serif;font-size:clamp(28px,4.5vw,52px);
  font-weight:600;font-style:italic;color:var(--parchment);line-height:1.25;max-width:720px;margin-bottom:32px}
.hero-summary{font-family:Georgia,'Iowan Old Style',serif;font-size:18px;color:var(--parchment-mid);
  max-width:640px;line-height:1.75;opacity:.85}
.hero-divider{width:80px;height:2px;background:var(--brass);margin:48px 0;transform-origin:left}
.hero-meta{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:var(--ink-muted);
  letter-spacing:.08em;display:flex;gap:32px;flex-wrap:wrap;margin-top:48px}
.hero-meta span{color:var(--brass)}

/* ── CONFIDENCE BADGE ── */
.confidence-badge{display:inline-flex;gap:6px;align-items:center;
  font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:.08em;
  background:rgba(184,135,58,.15);border:1px solid var(--brass);
  color:var(--brass-light);padding:6px 14px;margin-bottom:32px;border-radius:2px}
.conf-prefix{font-weight:700;text-transform:uppercase;letter-spacing:.12em}

/* ── TOP NAV ── */
.top-nav{position:absolute;top:0;left:0;right:0;padding:24px 48px;
  display:flex;justify-content:space-between;align-items:center;z-index:10}
.top-nav .mark{font-family:'PP Display',Georgia,'Iowan Old Style',serif;font-size:14px;
  letter-spacing:.32em;color:var(--parchment);text-transform:uppercase}
.top-nav nav{display:flex;gap:24px}
.top-nav nav a{font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--brass);text-decoration:none}
.top-nav nav a:hover{color:var(--brass-light)}

/* ── SURGE / CHART ── */
.section-eyebrow{font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:.2em;
  text-transform:uppercase;color:var(--brass-dim);margin-bottom:24px;
  display:flex;align-items:center;gap:12px}
.section-eyebrow::after{content:'';display:block;height:1px;width:60px;background:var(--brass-dim);opacity:.5}
.section-eyebrow-light{color:var(--brass)}
.section-eyebrow-light::after{background:var(--brass)}
.surge-chart-wrap{display:flex;align-items:flex-end;gap:0;height:320px;margin:60px 0 40px;position:relative}
.surge-month{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:0;height:100%;position:relative}
.surge-bar-wrap{width:100%;display:flex;align-items:flex-end;justify-content:center;flex:1}
.surge-bar{border-radius:4px 4px 0 0;width:70%}
.surge-bar-num{font-family:'PP Display',Georgia,'Iowan Old Style',serif;font-weight:900;font-size:18px;
  color:var(--ink);margin-bottom:10px;text-align:center;white-space:nowrap}
.surge-bar-num.big{font-size:52px;color:var(--ink);line-height:1}
.surge-bar-label{font-family:ui-monospace,Menlo,monospace;font-size:12px;letter-spacing:.1em;
  color:var(--ink-muted);text-align:center;padding:10px 0 0}
.surge-divider{position:absolute;top:0;right:0;width:1px;height:100%;background:var(--parchment-mid)}
.surge-baseline{width:100%;height:1px;background:var(--ink);opacity:.25;margin:0}
.surge-annotation{font-family:Georgia,'Iowan Old Style',serif;font-style:italic;font-size:17px;
  color:var(--ink-muted);text-align:center;margin-top:32px}
.surge-annotation strong{font-family:'PP Display',Georgia,'Iowan Old Style',serif;font-weight:800;
  font-style:normal;color:var(--ink);font-size:22px}

/* ── STAT CARDS (meta-pattern only) ── */
.stat-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:2px;background:var(--ink)}
.stat-card{background:var(--parchment-light);padding:60px 48px;position:relative;overflow:hidden}
.stat-card:nth-child(odd){background:var(--cream)}
.stat-headline{font-family:'PP Display',Georgia,'Iowan Old Style',serif;font-size:clamp(56px,10vw,96px);
  font-weight:900;line-height:.9;color:var(--ink);letter-spacing:-.03em;margin-bottom:16px}
.stat-label{font-family:Georgia,'Iowan Old Style',serif;font-size:20px;font-weight:600;
  color:var(--ink-soft);margin-bottom:8px}
.stat-caption{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:var(--ink-muted);letter-spacing:.06em}
.stat-card-accent{position:absolute;top:0;right:0;width:4px;height:100%;background:var(--brass)}

/* ── CHAPTERS ── */
.chapter-item{display:grid;grid-template-columns:160px 1fr;gap:0;
  border-top:1px solid var(--parchment-mid);padding:64px 0;align-items:start}
.chapter-item:last-child{border-bottom:1px solid var(--parchment-mid)}
.chapter-period{font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:.18em;
  text-transform:uppercase;color:var(--brass-dim);padding-top:8px}
.chapter-title{font-family:'PP Display',Georgia,'Iowan Old Style',serif;font-size:clamp(28px,4vw,44px);
  font-weight:800;font-style:italic;color:var(--parchment);line-height:1.15;margin-bottom:24px}
.chapter-narrative{font-family:Georgia,'Iowan Old Style',serif;font-size:17px;
  color:var(--parchment-mid);line-height:1.75;max-width:560px}

/* ── 6 DIMENSIONS ── */
.dim-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;
  background:var(--parchment-mid);border:1px solid var(--parchment-mid)}
.dim-card{background:var(--parchment);padding:48px 36px;position:relative}
.dim-icon{font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:.2em;text-transform:uppercase;
  color:var(--brass);margin-bottom:20px;display:flex;align-items:center;gap:8px}
.dim-icon::before{content:'';display:block;width:24px;height:1px;background:var(--brass)}
.dim-title{font-family:'PP Display',Georgia,'Iowan Old Style',serif;font-size:26px;font-weight:700;
  color:var(--ink);margin-bottom:16px;line-height:1.2}
.dim-narrative{font-family:Georgia,'Iowan Old Style',serif;font-size:15px;color:var(--ink-soft);
  line-height:1.7;margin-bottom:20px}
.dim-evidence{list-style:none;border-top:1px solid var(--parchment-mid);padding-top:16px;margin-top:8px}
.dim-evidence li{font-family:ui-monospace,Menlo,monospace;font-size:11px;color:var(--ink-muted);
  line-height:1.6;padding:4px 0 4px 12px;position:relative}
.dim-evidence li::before{content:'·';position:absolute;left:0;color:var(--brass)}

/* ── SHARE CARDS ── */
.share-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:2px;background:var(--ink)}
.share-card{background:var(--deep-bg);padding:56px 48px;position:relative;overflow:hidden;
  border-top:3px solid transparent;transition:border-color .2s}
.share-card:hover{border-top-color:var(--brass)}
.share-card-num{font-family:'PP Display',Georgia,'Iowan Old Style',serif;font-size:clamp(52px,9vw,88px);
  font-weight:900;line-height:.9;color:var(--parchment-light);letter-spacing:-.03em;margin-bottom:12px}
.share-card-stat{font-family:Georgia,'Iowan Old Style',serif;font-size:18px;font-weight:600;
  color:var(--brass-light);margin-bottom:8px}
.share-card-caption{font-family:ui-monospace,Menlo,monospace;font-size:11px;color:var(--ink-muted);
  letter-spacing:.08em}
.share-save-btn{display:block;margin-top:20px;background:transparent;color:var(--brass);
  border:1px solid rgba(184,135,58,.5);font-family:ui-monospace,Menlo,monospace;font-size:11px;
  letter-spacing:.08em;padding:7px 14px;cursor:pointer;border-radius:0}
.share-save-btn:hover{background:rgba(184,135,58,.12)}

/* ── BEARINGS ── */
.bearing-item{display:grid;grid-template-columns:64px 1fr;gap:40px;padding:56px 0;
  border-top:1px solid rgba(255,255,255,.08);align-items:start}
.bearing-num{font-family:'PP Display',Georgia,'Iowan Old Style',serif;font-size:52px;font-weight:900;
  font-style:italic;color:var(--brass-light);opacity:.6;line-height:1;text-align:center}
.bearing-title{font-family:'PP Display',Georgia,'Iowan Old Style',serif;font-size:28px;font-weight:700;
  color:var(--parchment-light);line-height:1.2;margin-bottom:16px}
.bearing-why{font-family:Georgia,'Iowan Old Style',serif;font-style:italic;font-size:16px;
  color:var(--parchment-mid);line-height:1.7;margin-bottom:12px;padding-left:16px;
  border-left:2px solid var(--brass-dim)}
.bearing-how{font-family:Georgia,'Iowan Old Style',serif;font-size:15px;color:var(--ink-muted);line-height:1.7}

/* ── SECTION HEADINGS ── */
.section-h2-dark{font-family:'PP Display',Georgia,'Iowan Old Style',serif;font-size:clamp(36px,6vw,72px);
  font-weight:900;line-height:1.0;color:var(--parchment-light);letter-spacing:-.02em;margin-bottom:16px}
.section-h2-light{font-family:'PP Display',Georgia,'Iowan Old Style',serif;font-size:clamp(36px,6vw,72px);
  font-weight:900;line-height:1.0;color:var(--ink);letter-spacing:-.02em;margin-bottom:16px}
.section-sub-dark{font-family:Georgia,'Iowan Old Style',serif;font-size:18px;color:var(--parchment-mid);
  max-width:560px;line-height:1.7;margin-bottom:64px}
.section-sub-light{font-family:Georgia,'Iowan Old Style',serif;font-size:18px;color:var(--ink-soft);
  max-width:560px;line-height:1.7;margin-bottom:64px}

/* ── CONTOUR BG ── */
.contour-bg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:hidden}

/* ── FOOTER ── */
.footer{background:var(--ink);padding:60px 48px;text-align:center}
.footer-logo{font-family:'PP Display',Georgia,'Iowan Old Style',serif;font-size:32px;font-weight:900;
  font-style:italic;color:var(--parchment-light);letter-spacing:-.02em;margin-bottom:16px}
.footer-logo em{color:var(--brass-light);font-style:normal}
.footer-sub{font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:.2em;
  text-transform:uppercase;color:var(--ink-muted)}

/* ── RESPONSIVE ── */
@media(max-width:700px){
  .hero{padding:60px 24px 80px}
  .section-parchment,.section-dark,.section-ink,.surge-section{padding:80px 24px}
  .stat-grid,.share-grid{grid-template-columns:1fr}
  .dim-grid{grid-template-columns:1fr}
  .chapter-item{grid-template-columns:1fr;gap:12px}
  .bearing-item{grid-template-columns:1fr;gap:16px}
}
@media print{
  body{background:#fff}
  .share-save-btn{display:none}
  .anim-fadeup,.anim-inkdrop{animation:none}
}
"""

# ── Share JS (canvas-based card save) ─────────────────────────────────────────

SHARE_JS = """
function saveCard(btn){
  var card=btn.closest('.share-card');var W=720,H=880;
  var cv=document.createElement('canvas');cv.width=W;cv.height=H;var x=cv.getContext('2d');
  x.fillStyle='#0F0A02';x.fillRect(0,0,W,H);
  x.strokeStyle='rgba(212,168,85,0.15)';x.lineWidth=1.5;
  [80,160,260,380].forEach(function(r){x.beginPath();x.arc(W-60,80,r,0,7);x.stroke();});
  var pad=64;
  x.fillStyle='#D4A855';x.font='600 18px ui-monospace,Menlo,monospace';x.textBaseline='top';
  x.fillText('PROMPTPRINT',pad,pad);
  var num=card.querySelector('.share-card-num');
  var stat=card.querySelector('.share-card-stat');
  var cap=card.querySelector('.share-card-caption');
  x.fillStyle='#FAF5E8';x.font='900 110px Georgia,serif';x.textBaseline='alphabetic';
  x.fillText(num?num.textContent:'',pad,H/2-40);
  x.fillStyle='#D4A855';x.font='600 28px Georgia,serif';
  x.fillText(stat?stat.textContent:'',pad,H/2+40);
  x.fillStyle='rgba(234,217,180,.72)';x.font='400 16px ui-monospace,Menlo,monospace';
  x.fillText(cap?cap.textContent:'',pad,H/2+84);
  x.fillStyle='rgba(234,217,180,.5)';x.font='400 14px ui-monospace,Menlo,monospace';
  x.fillText('made with Promptprint · 100% local',pad,H-pad-16);
  cv.toBlob(function(b){var a=document.createElement('a');a.href=URL.createObjectURL(b);
    a.download='promptprint-card.png';a.click();URL.revokeObjectURL(a.href);});
}
"""

# ── hero contour SVG ───────────────────────────────────────────────────────────

HERO_CONTOUR = (
    '<svg class="hero-contour" viewBox="0 0 1200 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
    '<g stroke="#D4A855" stroke-width="0.5" fill="none" opacity="0.6">'
    '<ellipse cx="900" cy="450" rx="180" ry="90"/>'
    '<ellipse cx="900" cy="450" rx="240" ry="130"/>'
    '<ellipse cx="900" cy="450" rx="310" ry="180"/>'
    '<ellipse cx="900" cy="450" rx="390" ry="235"/>'
    '<ellipse cx="900" cy="450" rx="480" ry="295"/>'
    '<ellipse cx="900" cy="450" rx="580" ry="360"/>'
    '<ellipse cx="900" cy="450" rx="700" ry="440"/>'
    '<ellipse cx="900" cy="450" rx="840" ry="530"/>'
    '<ellipse cx="900" cy="450" rx="1000" ry="640"/>'
    '</g></svg>'
)


def _contour_dark_left():
    return (
        '<svg class="contour-bg" viewBox="0 0 1200 700" preserveAspectRatio="xMaxYMid slice" aria-hidden="true">'
        '<g stroke="#B8873A" stroke-width="0.4" fill="none" opacity="0.4">'
        '<ellipse cx="200" cy="350" rx="120" ry="60"/>'
        '<ellipse cx="200" cy="350" rx="200" ry="110"/>'
        '<ellipse cx="200" cy="350" rx="290" ry="165"/>'
        '<ellipse cx="200" cy="350" rx="390" ry="225"/>'
        '<ellipse cx="200" cy="350" rx="500" ry="290"/>'
        '</g></svg>'
    )


def _contour_compass():
    return (
        '<svg class="contour-bg" viewBox="0 0 1200 700" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
        '<g stroke="#B8873A" stroke-width="0.4" fill="none" opacity="0.35">'
        '<circle cx="600" cy="350" r="80"/><circle cx="600" cy="350" r="160"/>'
        '<circle cx="600" cy="350" r="250"/><circle cx="600" cy="350" r="360"/>'
        '<circle cx="600" cy="350" r="490"/><circle cx="600" cy="350" r="640"/>'
        '<line x1="600" y1="0" x2="600" y2="700" stroke-dasharray="4 8"/>'
        '<line x1="0" y1="350" x2="1200" y2="350" stroke-dasharray="4 8"/>'
        '<line x1="200" y1="0" x2="1000" y2="700" stroke-dasharray="4 8"/>'
        '<line x1="1000" y1="0" x2="200" y2="700" stroke-dasharray="4 8"/>'
        '</g></svg>'
    )


# ── main builder ──────────────────────────────────────────────────────────────

def build_report_html(insights: dict, aggregates: dict, title: str = "Promptprint") -> str:
    """insights + aggregates를 받아 V3 디자인의 self-contained HTML 리포트를 만든다."""
    insights = insights or {}
    aggregates = aggregates or {}
    meta = aggregates.get("meta", {})
    activity = aggregates.get("activity", {})
    shape = aggregates.get("shape", {})
    by_tool = meta.get("by_tool", {})
    dr = meta.get("date_range", [None, None])

    # ── language ──────────────────────────────────────────────────────────────
    raw_lang = insights.get("lang", "ko")
    lang = raw_lang if raw_lang in LABELS else "ko"
    L = LABELS[lang]

    # ── period string ─────────────────────────────────────────────────────────
    period_str = ""
    if dr and dr[0]:
        period_str = "{} — {}".format(
            _esc(str(dr[0])[:7]).replace("-", "·"),
            _esc(str(dr[1])[:7]).replace("-", "·"),
        )

    # ── hero colossal number: total questions ─────────────────────────────────
    total = meta.get("total_questions", 0)
    total_str = _fmt_int(total)
    # Split last digit group for em colouring (e.g. "5,602" → "5," + "602")
    if "," in total_str:
        comma_pos = total_str.index(",")
        hero_num_html = (
            _esc(total_str[: comma_pos + 1]) +
            f"<em>{_esc(total_str[comma_pos + 1:])}</em>"
        )
    else:
        hero_num_html = _esc(total_str)

    # ── hero meta line ─────────────────────────────────────────────────────────
    tool_items = " ".join(
        f'<span>{_esc(k)} <span>{_fmt_int(v)}</span></span>'
        for k, v in sorted(by_tool.items())
    )
    period_short = _esc(_month_span(dr))
    hero_meta_html = (
        f'{tool_items}'
        f'<span>{_lbl(L, "period_label")} <span>{period_short}</span></span>'
    )

    # ── confidence badge ───────────────────────────────────────────────────────
    conf_badge = _confidence_badge(meta, L.get("conf_prefix", "신뢰도"))

    # ── surge chart ────────────────────────────────────────────────────────────
    surge_html = _surge_chart_html(
        activity.get("by_month", {}),
        shape.get("avg_len_by_month", {}),
    )

    # ── dimensions ────────────────────────────────────────────────────────────
    dims = insights.get("dimensions", {})
    dim_blocks = []
    for key, label_dict in DIMENSION_ORDER:
        label = label_dict.get(lang, label_dict.get("ko", key))
        icon = DIM_ICON_LABELS.get(key, {}).get(lang, key)
        dim_blocks.append(_dimension_block(key, label, icon, dims.get(key, {})))
    dim_html = "".join(dim_blocks)

    # ── chapters ──────────────────────────────────────────────────────────────
    chap_html = "".join(
        _chapter_block(c, i + 1)
        for i, c in enumerate(insights.get("chapters", []))
    )

    # ── cards (headline/stat/caption only, no evidence) ───────────────────────
    save_label = L.get("save_btn", "이미지로 저장")
    card_html = "".join(
        _card_block(c, save_label) for c in insights.get("cards", [])
    )

    # ── bearings ──────────────────────────────────────────────────────────────
    bearing_html = "".join(
        _bearing_block(b, i + 1) for i, b in enumerate(insights.get("next_bearings", []))
    )

    # ── section heading helpers ───────────────────────────────────────────────
    def eyebrow(text, light=False):
        cls = "section-eyebrow section-eyebrow-light" if light else "section-eyebrow"
        return f'<div class="{cls}">{_esc(text)}</div>'

    next_heading_lines = _lbl(L, "next_heading").replace("&#x0a;", "<br>")
    # Build \n → <br> for multi-line heading
    next_heading_html = _esc(L.get("next_heading", "")).replace("&#10;", "<br>").replace("\n", "<br>")

    return (
        "<!DOCTYPE html>\n"
        f'<html lang="{_esc(lang)}">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{_esc(title)} — field journal</title>\n'
        f"<style>{FONT_FACE_CSS}\n{STYLE}</style>\n"
        "</head>\n"
        "<body>\n"
        # ── HERO ──────────────────────────────────────────────────────────────
        '<section class="hero">\n'
        f'{HERO_CONTOUR}\n'
        '<div class="top-nav">\n'
        f'  <div class="mark">{_esc(title)}</div>\n'
        '  <nav>\n'
        f'    <a href="#chart">{_lbl(L,"nav_chart")}</a>\n'
        f'    <a href="#dims">{_lbl(L,"nav_bearings")}</a>\n'
        f'    <a href="#cards">{_lbl(L,"nav_cards")}</a>\n'
        '  </nav>\n'
        '</div>\n'
        '<div class="container" style="position:relative;">\n'
        f'  {conf_badge}\n'
        f'  <div class="hero-label anim-fadeup d1">{_esc(title)}&nbsp;·&nbsp;{period_str}</div>\n'
        f'  <span class="hero-number anim-inkdrop d2">{hero_num_html}</span>\n'
        f'  <h1 class="hero-headline anim-fadeup d3">{_esc(insights.get("headline",""))}</h1>\n'
        '  <div class="hero-divider anim-fadeup d4" '
        'style="animation:lineGrow .8s .7s cubic-bezier(.16,1,.3,1) both;"></div>\n'
        f'  <p class="hero-summary anim-fadeup d5">{_esc(insights.get("summary",""))}</p>\n'
        f'  <div class="hero-meta anim-fadeup d6">{hero_meta_html}</div>\n'
        '</div>\n'
        '</section>\n'
        # ── SURGE CHART ───────────────────────────────────────────────────────
        f'<section class="surge-section" id="chart">\n'
        '<div class="container">\n'
        f'  {eyebrow(L.get("chart_eyebrow",""))}\n'
        f'  <h2 class="section-h2-light" style="font-style:italic;">'
        f'{_lbl(L,"section_chart")}</h2>\n'
        f'  {surge_html}\n'
        f'  <p class="surge-annotation">{_lbl(L,"chart_caption")}</p>\n'
        '</div>\n'
        '</section>\n'
        # ── CHAPTERS ──────────────────────────────────────────────────────────
        '<section class="section-dark" id="chapters" style="position:relative;overflow:hidden;">\n'
        f'{_contour_dark_left()}\n'
        '<div class="container" style="position:relative;">\n'
        f'  {eyebrow(L.get("chaps_eyebrow",""), light=True)}\n'
        f'  <h2 class="section-h2-dark">{_lbl(L,"section_chaps")}</h2>\n'
        f'  <p class="section-sub-dark">{_lbl(L,"chaps_sub")}</p>\n'
        f'  {chap_html}\n'
        '</div>\n'
        '</section>\n'
        # ── 6 DIMENSIONS ──────────────────────────────────────────────────────
        f'<section class="section-parchment" id="dims">\n'
        '<div class="container">\n'
        f'  {eyebrow(L.get("dims_eyebrow",""))}\n'
        f'  <h2 class="section-h2-light">{_lbl(L,"section_dims")}</h2>\n'
        f'  <p class="section-sub-light">{_lbl(L,"dims_sub")}</p>\n'
        f'  <div class="dim-grid">{dim_html}</div>\n'
        '</div>\n'
        '</section>\n'
        # ── CARDS ─────────────────────────────────────────────────────────────
        '<section style="background:var(--ink);padding:80px 0 0;" id="cards">\n'
        '<div class="container" style="padding:0 48px;">\n'
        f'  {eyebrow(L.get("section_cards",""), light=True)}\n'
        f'  <h2 class="section-h2-dark" style="margin-bottom:8px;">'
        f'{_lbl(L,"cards_sub")}</h2>\n'
        f'  <p style="font-family:ui-monospace,Menlo,monospace;font-size:11px;'
        f'color:var(--ink-muted);margin-bottom:48px;">{_lbl(L,"cards_hint")}</p>\n'
        '</div>\n'
        f'<div class="share-grid">{card_html}</div>\n'
        '</section>\n'
        # ── NEXT BEARINGS ─────────────────────────────────────────────────────
        '<section class="section-dark" id="bearings" style="position:relative;overflow:hidden;">\n'
        f'{_contour_compass()}\n'
        '<div class="container" style="position:relative;">\n'
        f'  {eyebrow(L.get("next_eyebrow",""), light=True)}\n'
        f'  <h2 class="section-h2-dark">{next_heading_html}</h2>\n'
        f'  <p class="section-sub-dark">{_lbl(L,"next_sub")}</p>\n'
        f'  <div>{bearing_html}</div>\n'
        '</div>\n'
        '</section>\n'
        # ── FOOTER ────────────────────────────────────────────────────────────
        '<footer class="footer">\n'
        '  <div class="footer-logo">Prompt<em>print</em></div>\n'
        f'  <div class="footer-sub">{_lbl(L,"footer_made")}</div>\n'
        '</footer>\n'
        f'<script>{SHARE_JS}</script>\n'
        '</body>\n'
        '</html>'
    )
