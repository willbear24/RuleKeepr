import os
import requests

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


class ApiError(Exception):
    """A readable error the UI can show with st.error()."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _request(method, path, token=None, timeout=15, **kwargs):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        response = requests.request(
            method, f"{BASE_URL}{path}", headers=headers, timeout=timeout, **kwargs
        )
    except requests.exceptions.RequestException:
        raise ApiError("Can't reach the RuleKeepr server.")

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", "Something went wrong")
        except ValueError:  # non-JSON error body, e.g. a proxy error page
            detail = f"Server error ({response.status_code})"
        raise ApiError(str(detail), response.status_code)  # 422 detail is a list, hence str()
    return response.json() if response.content else None  # DELETE gives 204, no body


def register(name, email, password):
    data = _request(
        "POST",
        "/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    return data["access_token"]


def get_me(token):
    return _request("GET", "/users/me", token)


def login(email, password):
    data = _request("POST", "/auth/login", json={"email": email, "password": password})
    return data["access_token"]


def list_games(token):
    return _request("GET", "/games/", token)


def my_games(token):
    return _request("GET", "/games/mine", token)


def add_to_shelf(token, game_id):
    return _request("POST", f"/games/{game_id}/shelf", token, json={})


def remove_from_shelf(token, game_id):
    return _request("DELETE", f"/games/{game_id}/shelf", token)


def create_session(token, game_id, notes=None):
    return _request(
        "POST", "/sessions/", token, json={"game_id": game_id, "notes": notes}
    )


def list_sessions(token, game_id=None):
    params = {"game_id": game_id} if game_id is not None else None
    return _request("GET", "/sessions/", token, params=params)


def end_session(token, session_id):
    return _request("POST", f"/sessions/{session_id}/end", token)


def update_notes(token, session_id, notes):
    return _request("PATCH", f"/sessions/{session_id}", token, json={"notes": notes})


def delete_session(token, session_id):
    return _request("DELETE", f"/sessions/{session_id}", token)


def list_questions(token, session_id):
    return _request("GET", f"/sessions/{session_id}/questions/", token)


def ask_question(token, session_id, text):
    # Generating an answer can take a while, especially on the model's first load.
    return _request(
        "POST",
        f"/sessions/{session_id}/questions/",
        token,
        timeout=90,
        json={"question_text": text},
    )
