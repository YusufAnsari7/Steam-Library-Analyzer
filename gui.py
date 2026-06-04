import threading
from queue import Queue

from dearpygui import dearpygui as dpg

from steam import get_game_details, get_game_library

# Globals
game_data = []
ui_queue = Queue()


# Compute helpers
def compute_stats():
    total = round(sum(g["hours"] for g in game_data), 1)
    played = [g for g in game_data if g["hours"] > 0]
    never = [g for g in game_data if g["hours"] == 0]
    return total, played, never


def compute_top_games():
    return sorted(game_data, key=lambda g: g["hours"], reverse=True)[:5]


def compute_hidden_gems():
    gems = [g for g in game_data if g["review_score"] >= 85 and g["hours"] < 2]
    return sorted(gems, key=lambda g: g["review_score"], reverse=True)[:5]


def compute_untouched():
    return [g for g in game_data if g["hours"] == 0][:10]


def compute_recommendations():
    top5 = sorted(game_data, key=lambda g: g["hours"], reverse=True)[:5]
    fav_genres = set(genre for g in top5 for genre in g["genres"])
    candidates = []

    for g in game_data:
        if g["hours"] <= 2:
            match = fav_genres.intersection(set(g["genres"]))
            if match:
                candidates.append((len(match) * 10 + g["review_score"], g, match))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[:3]


# Safe UI helper (called only from main thread)
def set_status(msg, color=(180, 180, 180)):
    if dpg.does_item_exist("status_text"):
        dpg.set_value("status_text", msg)
        dpg.configure_item("status_text", color=color)


def clear_group(tag):
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag, children_only=True)


# Populate dashboard on the main thread via the render loop.
def populate_dashboard():
    total, played, never = compute_stats()

    # stat cards
    dpg.set_value("stat_owned", str(len(game_data)))
    dpg.set_value("stat_played", str(len(played)))
    dpg.set_value("stat_never", str(len(never)))
    dpg.set_value("stat_hours", f"{total}h")

    # played percent bar
    pct = int(len(played) / len(game_data) * 100) if game_data else 0
    dpg.set_value("played_bar", pct / 100)
    dpg.set_value("played_bar_lbl", f"{pct}% of library played")

    # Top Played
    clear_group("top_group")
    top_games = compute_top_games()
    max_hours = top_games[0]["hours"] if top_games else 0

    for i, g in enumerate(top_games, 1):
        bar_w = int((g["hours"] / max_hours) * 340) if max_hours else 0

        with dpg.group(horizontal=False, parent="top_group"):
            with dpg.group(horizontal=True):
                dpg.add_text(f"{i}.", color=(120, 120, 120))
                dpg.add_text(f" {g['name']}", color=(220, 220, 220))
                dpg.add_text(f" {g['hours']}h", color=(100, 180, 255))

            dpg.add_drawlist(width=bar_w + 2, height=8)
            with dpg.draw_node(parent=dpg.last_item()):
                dpg.draw_rectangle(
                    [0, 1],
                    [bar_w, 7],
                    color=(100, 180, 255, 0),
                    fill=(100, 180, 255, 180),
                    rounding=2,
                )

            dpg.add_spacer(height=6)

    # Hidden Gems
    clear_group("gems_group")
    gems = compute_hidden_gems()

    if gems:
        for g in gems:
            score_color = (100, 220, 130) if g["review_score"] >= 90 else (200, 200, 100)

            with dpg.group(horizontal=True, parent="gems_group"):
                dpg.add_text(f" {g['name']}", color=(220, 220, 220))
                dpg.add_text(f" Score: {g['review_score']}", color=score_color)
                dpg.add_text(f" ({g['hours']}h played)", color=(120, 120, 120))

            dpg.add_spacer(height=4, parent="gems_group")
    else:
        dpg.add_text("No hidden gems found.", color=(160, 160, 160), parent="gems_group")

    # Untouched
    clear_group("untouched_group")

    for g in compute_untouched():
        with dpg.group(horizontal=True, parent="untouched_group"):
            dpg.add_text(" -", color=(200, 80, 80))
            dpg.add_text(f" {g['name']}", color=(220, 220, 220))

        dpg.add_spacer(height=4, parent="untouched_group")

    # Recommendations
    clear_group("rec_group")
    recs = compute_recommendations()

    if recs:
        for rank, (_, g, matching) in enumerate(recs, 1):
            with dpg.child_window(height=110, border=True, parent="rec_group"):
                with dpg.group(horizontal=True):
                    dpg.add_text(f"#{rank}", color=(100, 180, 255))
                    dpg.add_text(f" {g['name']}", color=(230, 230, 230))

                dpg.add_separator()
                dpg.add_text(f"Genres: {', '.join(g['genres'])}", color=(160, 160, 160))
                dpg.add_text(f"Score: {g['review_score']}", color=(100, 220, 130))
                dpg.add_text(f"Hours: {g['hours']}h played", color=(160, 160, 160))
                dpg.add_text(
                    f"Why: Matches your taste in {', '.join(matching)}",
                    color=(200, 180, 100),
                )

            dpg.add_spacer(height=6, parent="rec_group")
    else:
        dpg.add_text("No recommendations found.", color=(160, 160, 160), parent="rec_group")

    # Show dashboard, hide login.
    dpg.configure_item("login_window", show=False)
    dpg.configure_item("dashboard_window", show=True)


# Render-loop callback: drains pending work.
def drain_pending():
    while not ui_queue.empty():
        fn = ui_queue.get()
        fn()


# Background fetch thread
def fetch_worker(api_key, user_id):
    global game_data

    def ui(fn):
        ui_queue.put(fn)

    ui(lambda: set_status("Fetching library...", (100, 180, 255)))

    library = get_game_library(api_key, user_id)
    if not library:
        ui(lambda: set_status("Failed - check Steam ID or API key.", (255, 80, 80)))
        ui(lambda: dpg.configure_item("analyze_btn", enabled=True))
        return

    msg = f"Found {len(library)} games - fetching details (may take a while)..."
    ui(lambda: set_status(msg, (100, 180, 255)))

    game_data = get_game_details(library)
    if not game_data:
        ui(lambda: set_status("No game data returned.", (255, 80, 80)))
        ui(lambda: dpg.configure_item("analyze_btn", enabled=True))
        return

    ui(populate_dashboard)


# Callbacks
def on_analyze():
    api_key = dpg.get_value("input_api_key").strip()
    user_id = dpg.get_value("input_user_id").strip()

    if not api_key or not user_id:
        set_status("Both fields are required.", (255, 80, 80))
        return

    dpg.configure_item("analyze_btn", enabled=False)
    threading.Thread(target=fetch_worker, args=(api_key, user_id), daemon=True).start()


def on_signout():
    dpg.configure_item("dashboard_window", show=False)
    dpg.configure_item("login_window", show=True)
    dpg.set_value("input_api_key", "")
    dpg.set_value("input_user_id", "")
    dpg.configure_item("analyze_btn", enabled=True)
    set_status("")


# Build UI
def build_ui():
    dpg.create_context()
    window_width = 860
    window_height = 640

    # Theme
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (18, 18, 22))
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (26, 26, 32))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (36, 36, 46))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (46, 46, 60))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (40, 100, 180))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (60, 130, 220))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (30, 80, 150))
            dpg.add_theme_color(dpg.mvThemeCol_Tab, (30, 30, 40))
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (50, 100, 180))
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, (40, 100, 200))
            dpg.add_theme_color(dpg.mvThemeCol_Header, (40, 80, 140))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (50, 100, 170))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (20, 20, 28))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (30, 60, 110))
            dpg.add_theme_color(dpg.mvThemeCol_Separator, (50, 50, 65))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (210, 210, 215))
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 14, 12)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 6)

    dpg.bind_theme(global_theme)

    # Login
    with dpg.window(
        tag="login_window",
        label="Steam Library Analyzer",
        width=400,
        height=310,
        no_resize=True,
        no_collapse=True,
        no_move=True,
        pos=[(window_width - 400) // 2, (window_height - 310) // 2],
    ):
        dpg.add_spacer(height=4)
        dpg.add_text("Steam Library Analyzer", color=(100, 180, 255))
        dpg.add_text("Enter your credentials to get started.", color=(130, 130, 130))
        dpg.add_separator()
        dpg.add_spacer(height=8)

        dpg.add_text("Steam ID (64-bit or vanity URL)")
        dpg.add_input_text(tag="input_user_id", hint="e.g. 76561198xxxxxxxxx", width=365)
        dpg.add_spacer(height=8)

        dpg.add_text("Steam Web API Key")
        dpg.add_input_text(
            tag="input_api_key",
            hint="Paste your API key here",
            password=True,
            width=365,
        )
        dpg.add_text(" Get yours free at steamcommunity.com/dev/apikey", color=(90, 90, 90))
        dpg.add_spacer(height=12)

        dpg.add_button(
            tag="analyze_btn",
            label="Analyze my library",
            width=365,
            height=38,
            callback=on_analyze,
        )
        dpg.add_spacer(height=6)
        dpg.add_text("", tag="status_text")

    # Dashboard
    with dpg.window(
        tag="dashboard_window",
        label="Steam Library Analyzer - Dashboard",
        width=window_width,
        height=window_height,
        no_collapse=True,
        no_close=True,
        pos=[0, 0],
        show=False,
    ):
        # top bar
        with dpg.group(horizontal=True):
            dpg.add_text("Steam Library Analyzer", color=(100, 180, 255))
            dpg.add_spacer(width=16)
            dpg.add_button(label="Sign out", callback=on_signout, small=True)

        dpg.add_separator()
        dpg.add_spacer(height=8)

        # Stat cards row
        with dpg.group(horizontal=True):
            for tag, label, accent in [
                ("stat_owned", "Games Owned", (100, 180, 255)),
                ("stat_played", "Games Played", (100, 220, 130)),
                ("stat_never", "Never Played", (255, 130, 80)),
                ("stat_hours", "Total Hours", (200, 160, 255)),
            ]:
                with dpg.child_window(width=192, height=72, border=True):
                    dpg.add_text(label, color=(120, 120, 130))
                    dpg.add_text("-", tag=tag, color=accent)

        dpg.add_spacer(height=4)

        # played progress bar
        with dpg.group(horizontal=True):
            dpg.add_text("Library progress:", color=(120, 120, 130))
            dpg.add_spacer(width=6)
            dpg.add_progress_bar(tag="played_bar", default_value=0.0, width=340, overlay="")
            dpg.add_spacer(width=8)
            dpg.add_text("", tag="played_bar_lbl", color=(160, 160, 160))

        dpg.add_spacer(height=10)
        dpg.add_separator()
        dpg.add_spacer(height=6)

        # Tabs
        with dpg.tab_bar():
            with dpg.tab(label=" Top Played "):
                dpg.add_spacer(height=8)
                dpg.add_text("Your 5 most played games", color=(120, 120, 130))
                dpg.add_spacer(height=10)
                with dpg.child_window(height=380, border=False):
                    dpg.add_group(tag="top_group")

            with dpg.tab(label=" Hidden Gems "):
                dpg.add_spacer(height=8)
                dpg.add_text(
                    "High-rated games (score >= 85) you've barely touched",
                    color=(120, 120, 130),
                )
                dpg.add_spacer(height=10)
                with dpg.child_window(height=380, border=False):
                    dpg.add_group(tag="gems_group")

            with dpg.tab(label=" Untouched "):
                dpg.add_spacer(height=8)
                dpg.add_text("Games you own but have never launched", color=(120, 120, 130))
                dpg.add_spacer(height=10)
                with dpg.child_window(height=380, border=False):
                    dpg.add_group(tag="untouched_group")

            with dpg.tab(label=" Recommendations "):
                dpg.add_spacer(height=8)
                dpg.add_text(
                    "What to play next - based on your top genres",
                    color=(120, 120, 130),
                )
                dpg.add_spacer(height=10)
                with dpg.child_window(height=380, border=False):
                    dpg.add_group(tag="rec_group")

    # Viewport and render loop
    dpg.create_viewport(
        title="Steam Library Analyzer",
        width=window_width,
        height=window_height,
        min_width=window_width,
        min_height=window_height,
    )
    dpg.setup_dearpygui()
    dpg.show_viewport()

    while dpg.is_dearpygui_running():
        drain_pending()
        dpg.render_dearpygui_frame()

    dpg.destroy_context()


if __name__ == "__main__":
    build_ui()
