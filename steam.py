import requests
import json

api_key = "..."
user_id = "..."

def get_game_library(api_key, user_id):
    url = (
        f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        f"?key={api_key}&steamid={user_id}&format=json"
    )

    response = requests.get(url)
    data = response.json()

    if "response" in data and "games" in data["response"]:
        return data["response"]["games"]

    print("Failed to retrieve game library.")
    return []


def get_game_details(games):
    game_data = []

    for game in games:
        appid = game["appid"]
        hours = round(game["playtime_forever"] / 60, 1)

        url = f"https://store.steampowered.com/api/appdetails?appids={appid}"

        try:
            response = requests.get(url, timeout=10)
            data = response.json()
        except:
            continue

        if (
            data
            and str(appid) in data
            and data[str(appid)]["success"]
        ):
            info = data[str(appid)]["data"]

            name = info.get("name", "Unknown")

            genres = []
            if "genres" in info:
                genres = [
                    genre["description"]
                    for genre in info["genres"]
                ]

            review_score = 0
            if "metacritic" in info:
                review_score = info["metacritic"].get("score", 0)

            game_data.append({
                "appid": appid,
                "name": name,
                "hours": hours,
                "genres": genres,
                "review_score": review_score
            })

    return game_data


def print_top_games(game_data):
    print("\n===== TOP PLAYED GAMES =====")

    sorted_games = sorted(
        game_data,
        key=lambda g: g["hours"],
        reverse=True
    )

    for i, game in enumerate(sorted_games[:5], start=1):
        print(
            f"{i}. {game['name']} "
            f"- {game['hours']}h"
        )


def print_library_stats(game_data):
    total_hours = sum(
        game["hours"]
        for game in game_data
    )

    played = len([
        game for game in game_data
        if game["hours"] > 0
    ])

    never_played = len([
        game for game in game_data
        if game["hours"] == 0
    ])

    print("\n===== LIBRARY STATS =====")
    print(f"Games Owned: {len(game_data)}")
    print(f"Games Played: {played}")
    print(f"Games Never Played: {never_played}")
    print(f"Total Hours Played: {round(total_hours,1)}")


def hidden_gems(game_data):
    gems = [
        game for game in game_data
        if game["review_score"] >= 85
        and game["hours"] < 2
    ]

    gems.sort(
        key=lambda g: g["review_score"],
        reverse=True
    )

    print("\n===== HIDDEN GEMS =====")

    for game in gems[:5]:
        print(
            f"{game['name']} "
            f"(Score: {game['review_score']})"
        )


def untouched_games(game_data):
    untouched = [
        game for game in game_data
        if game["hours"] == 0
    ]

    print("\n===== UNTOUCHED GAMES =====")

    for game in untouched[:10]:
        print(game["name"])


def recommend_games(game_data):
    top_games = sorted(
        game_data,
        key=lambda g: g["hours"],
        reverse=True
    )[:5]

    favorite_genres = set()

    for game in top_games:
        for genre in game["genres"]:
            favorite_genres.add(genre)

    candidates = []

    for game in game_data:
        if game["hours"] <= 2:
            genre_match = len(
                favorite_genres.intersection(
                    set(game["genres"])
                )
            )

            if genre_match > 0:
                score = (
                    genre_match * 10
                    + game["review_score"]
                )

                candidates.append(
                    (score, game)
                )

    candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    print("\n===== TOP 3 RECOMMENDATIONS =====")

    if not candidates:
        print("No recommendations found.")
        return

    for rank, (_, game) in enumerate(candidates[:3], start=1):
        print(f"\n#{rank}")
        print(f"Game: {game['name']}")
        print(f"Hours Played: {game['hours']}")
        print(
            f"Genres: {', '.join(game['genres'])}"
        )
        print(
            f"Review Score: {game['review_score']}"
        )

        matching = favorite_genres.intersection(
            set(game["genres"])
        )

        print(
            "Reason: Matches your favorite genres: "
            + ", ".join(matching)
        )


def main():
    with open("config.json") as config_file:
        config = json.load(config_file)

    api_key = config["api_key"]
    user_id = config["user_id"]

    library = get_game_library(
        api_key,
        user_id
    )

    if not library:
        return

    print("Fetching game details...")
    game_data = get_game_details(library)

    print_top_games(game_data)
    print_library_stats(game_data)
    hidden_gems(game_data)
    untouched_games(game_data)
    recommend_games(game_data)


if __name__ == "__main__":
    main()