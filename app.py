import streamlit as st
from steam import get_game_library, get_game_details

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Steam Library Analyzer",
    page_icon="🎮",
    layout="wide",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&family=Inter:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0e0e12;
    color: #d4d4d8;
}

h1, h2, h3 { font-family: 'Rajdhani', sans-serif; }

/* Metric cards */
div[data-testid="metric-container"] {
    background: #1a1a22;
    border: 1px solid #2a2a38;
    border-radius: 10px;
    padding: 16px 20px;
}
div[data-testid="metric-container"] label { color: #666680 !important; font-size: 0.78rem; }

/* Tabs */
button[data-baseweb="tab"] {
    font-family: 'Rajdhani', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    color: #888 !important;
}
button[data-baseweb="tab"][aria-selected="true"] { color: #64b4ff !important; }

/* Inputs */
input[type="text"], input[type="password"] {
    background: #1a1a22 !important;
    border: 1px solid #2a2a38 !important;
    border-radius: 6px !important;
    color: #d4d4d8 !important;
}

/* Buttons */
.stButton > button {
    background: #2864b4;
    color: white;
    border: none;
    border-radius: 6px;
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.05rem;
    font-weight: 700;
    padding: 0.5rem 1.5rem;
    transition: background 0.2s;
}
.stButton > button:hover { background: #3c82dc; }

/* Game cards */
.game-card {
    background: #1a1a22;
    border: 1px solid #2a2a38;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
}
.game-name  { font-family: 'Rajdhani', sans-serif; font-size: 1.1rem; font-weight: 700; color: #e6e6ea; }
.game-hours { color: #64b4ff; font-size: 0.9rem; }
.game-score-green { color: #64dc82; font-size: 0.9rem; }
.game-score-yellow{ color: #c8c864; font-size: 0.9rem; }
.game-dim   { color: #666680; font-size: 0.85rem; }
.tag        { display: inline-block; background: #23233a; border-radius: 4px;
              padding: 2px 8px; font-size: 0.75rem; color: #9090b8; margin: 2px 2px 0 0; }

/* Bar */
.bar-wrap { background: #1e1e2a; border-radius: 4px; height: 8px; margin: 6px 0 10px; }
.bar-fill { background: #64b4ff; border-radius: 4px; height: 8px; }

/* Rec card */
.rec-card {
    background: #1a1a22;
    border: 1px solid #2a2a38;
    border-left: 3px solid #64b4ff;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 12px;
}
.rec-reason { color: #c8b464; font-size: 0.85rem; margin-top: 6px; }

/* Untouched */
.ut-item { color: #e6e6ea; padding: 6px 0; border-bottom: 1px solid #1e1e2a; font-size: 0.95rem; }

/* Section header */
.section-label { color: #444460; font-size: 0.78rem; text-transform: uppercase;
                 letter-spacing: 0.1em; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def compute_stats(game_data):
    total   = round(sum(g["hours"] for g in game_data), 1)
    played  = [g for g in game_data if g["hours"] > 0]
    never   = [g for g in game_data if g["hours"] == 0]
    return total, played, never

def compute_top(game_data):
    return sorted(game_data, key=lambda g: g["hours"], reverse=True)[:5]

def compute_gems(game_data):
    gems = [g for g in game_data if g["review_score"] >= 85 and g["hours"] < 2]
    return sorted(gems, key=lambda g: g["review_score"], reverse=True)[:5]

def compute_untouched(game_data):
    return [g for g in game_data if g["hours"] == 0][:10]

def compute_recs(game_data):
    top5       = sorted(game_data, key=lambda g: g["hours"], reverse=True)[:5]
    fav_genres = set(genre for g in top5 for genre in g["genres"])
    candidates = []
    for g in game_data:
        if g["hours"] <= 2:
            match = fav_genres.intersection(set(g["genres"]))
            if match:
                candidates.append((len(match)*10 + g["review_score"], g, match))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[:3]


# ── Session state init ─────────────────────────────────────────────────────────
if "game_data" not in st.session_state:
    st.session_state.game_data = None
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.logged_in:
    col_l, col_c, col_r = st.columns([1, 1.4, 1])
    with col_c:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("## 🎮 Steam Library Analyzer")
        st.markdown("<p style='color:#666680'>Enter your credentials to get started.</p>", unsafe_allow_html=True)
        st.markdown("---")

        user_id = st.text_input("Steam ID (64-bit)", placeholder="76561198xxxxxxxxx")
        api_key = st.text_input("Steam Web API Key", placeholder="Paste your API key here", type="password")
        st.markdown("<p style='color:#444460; font-size:0.8rem'>Get yours free at steamcommunity.com/dev/apikey</p>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Analyze my library", use_container_width=True):
            if not api_key or not user_id:
                st.error("Both fields are required.")
            else:
                with st.spinner("Fetching your library..."):
                    library = get_game_library(api_key, user_id)

                if not library:
                    st.error("Failed — check your Steam ID or API key.")
                else:
                    st.info(f"Found {len(library)} games. Fetching details (may take a while)...")
                    with st.spinner("Fetching game details..."):
                        game_data = get_game_details(library)

                    if not game_data:
                        st.error("No game data returned.")
                    else:
                        st.session_state.game_data  = game_data
                        st.session_state.logged_in  = True
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
else:
    game_data = st.session_state.game_data
    total, played, never = compute_stats(game_data)

    # ── Top bar ──────────────────────────────────────────────────────────────
    hdr_l, hdr_r = st.columns([6, 1])
    with hdr_l:
        st.markdown("## 🎮 Steam Library Analyzer")
    with hdr_r:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Sign out"):
            st.session_state.logged_in = False
            st.session_state.game_data = None
            st.rerun()

    st.markdown("---")

    # ── Stat cards ───────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Games Owned",   len(game_data))
    c2.metric("Games Played",  len(played))
    c3.metric("Never Played",  len(never))
    c4.metric("Total Hours",   f"{total}h")

    # ── Progress bar ─────────────────────────────────────────────────────────
    pct = int(len(played) / len(game_data) * 100) if game_data else 0
    st.markdown(f"""
    <div style="margin:12px 0 4px">
      <span style="color:#666680;font-size:0.82rem">Library progress</span>
      <span style="color:#9090b8;font-size:0.82rem;float:right">{pct}% played</span>
    </div>
    <div class="bar-wrap"><div class="bar-fill" style="width:{pct}%"></div></div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    t1, t2, t3, t4 = st.tabs(["🏆 Top Played", "💎 Hidden Gems", "📦 Untouched", "🔮 Recommendations"])

    # ── Tab 1: Top Played ────────────────────────────────────────────────────
    with t1:
        st.markdown("<p class='section-label'>Your 5 most-played games</p>", unsafe_allow_html=True)
        top = compute_top(game_data)
        max_h = top[0]["hours"] if top else 1

        for i, g in enumerate(top, 1):
            bar_pct = int(g["hours"] / max_h * 100)
            genres_html = "".join(f"<span class='tag'>{x}</span>" for x in g["genres"])
            st.markdown(f"""
            <div class="game-card">
              <span style="color:#444460;font-size:0.9rem">#{i}</span>
              <span class="game-name"> {g['name']}</span>
              <span class="game-hours"> — {g['hours']}h</span><br>
              {genres_html}
              <div class="bar-wrap"><div class="bar-fill" style="width:{bar_pct}%"></div></div>
            </div>
            """, unsafe_allow_html=True)

    # ── Tab 2: Hidden Gems ───────────────────────────────────────────────────
    with t2:
        st.markdown("<p class='section-label'>High-rated games (score ≥ 85) you've barely touched</p>", unsafe_allow_html=True)
        gems = compute_gems(game_data)

        if gems:
            for g in gems:
                score_cls = "game-score-green" if g["review_score"] >= 90 else "game-score-yellow"
                genres_html = "".join(f"<span class='tag'>{x}</span>" for x in g["genres"])
                st.markdown(f"""
                <div class="game-card">
                  <span class="game-name">{g['name']}</span>
                  <span class="{score_cls}"> ★ {g['review_score']}</span>
                  <span class="game-dim"> · {g['hours']}h played</span><br>
                  {genres_html}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("<p style='color:#666680'>No hidden gems found.</p>", unsafe_allow_html=True)

    # ── Tab 3: Untouched ─────────────────────────────────────────────────────
    with t3:
        st.markdown("<p class='section-label'>Games you own but have never launched</p>", unsafe_allow_html=True)
        untouched = compute_untouched(game_data)

        for g in untouched:
            st.markdown(f"<div class='ut-item'>🔴 &nbsp;{g['name']}</div>", unsafe_allow_html=True)

    # ── Tab 4: Recommendations ───────────────────────────────────────────────
    with t4:
        st.markdown("<p class='section-label'>What to play next — based on your top genres</p>", unsafe_allow_html=True)
        recs = compute_recs(game_data)

        if recs:
            for rank, (_, g, matching) in enumerate(recs, 1):
                score_cls = "game-score-green" if g["review_score"] >= 90 else "game-score-yellow"
                genres_html = "".join(f"<span class='tag'>{x}</span>" for x in g["genres"])
                st.markdown(f"""
                <div class="rec-card">
                  <span style="color:#64b4ff;font-family:'Rajdhani',sans-serif;font-size:1rem">#{rank}</span>
                  <span class="game-name"> {g['name']}</span>
                  <span class="{score_cls}"> ★ {g['review_score']}</span>
                  <span class="game-dim"> · {g['hours']}h played</span><br>
                  {genres_html}
                  <p class="rec-reason">🎯 Matches your taste in: {', '.join(matching)}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("<p style='color:#666680'>No recommendations found.</p>", unsafe_allow_html=True)