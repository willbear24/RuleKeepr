class TestReadGames:
    """Tests for GET /games and GET /games/{id}"""

    def test_list_games_empty(self, client, auth_headers):
        response = client.get("/games/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_games_with_catalog_game(self, client, sample_game, auth_headers):
        response = client.get("/games/", headers=auth_headers)

        assert response.status_code == 200
        assert response.json() == [
            {
                "id": sample_game["id"],
                "title": sample_game["title"],
                "min_player": sample_game["min_player"],
                "max_player": sample_game["max_player"],
                "play_time_minutes": sample_game["play_time_minutes"],
            }
        ]

    def test_list_games_requires_authentication(self, client):
        response = client.get("/games/")
        assert response.status_code == 401

    def test_get_game_by_id(self, client, sample_game, auth_headers):
        response = client.get(f"/games/{sample_game['id']}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Monopoly"
        assert response.json()["id"] == sample_game["id"]

    def test_get_game_not_found(self, client, auth_headers):
        response = client.get("/games/9999", headers=auth_headers)
        assert response.status_code == 404


class TestGameShelf:
    def test_add_list_update_and_remove_game(
        self, client, sample_game, auth_headers
    ):
        game_id = sample_game["id"]
        shelf_url = f"/games/{game_id}/shelf"

        add_response = client.post(
            shelf_url,
            headers=auth_headers,
            json={"notes": "Family favorite", "rating": 4.5},
        )
        assert add_response.status_code == 201
        assert add_response.json()["game"]["id"] == game_id
        assert add_response.json()["notes"] == "Family favorite"
        assert add_response.json()["rating"] == 4.5

        list_response = client.get("/games/mine", headers=auth_headers)
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1
        assert list_response.json()[0]["game"]["id"] == game_id

        update_response = client.patch(
            shelf_url,
            headers=auth_headers,
            json={"notes": "Great for game night", "rating": 5},
        )
        assert update_response.status_code == 200
        assert update_response.json()["notes"] == "Great for game night"
        assert update_response.json()["rating"] == 5

        remove_response = client.delete(shelf_url, headers=auth_headers)
        assert remove_response.status_code == 204
        assert client.get("/games/mine", headers=auth_headers).json() == []
