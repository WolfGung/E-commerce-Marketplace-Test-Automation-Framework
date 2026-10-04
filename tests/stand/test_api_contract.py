"""The REST API of the stand answers exactly the way the suite's API client expects.

Every answer is HTTP 200 with the real status in `responseCode`, bodies are
form-encoded, and the messages are the ones the public API gives — the API
client and the API tests were written against that shape, and the stand's job
is to keep them unchanged.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.stand


def test_the_catalogue_has_the_shape_the_product_model_expects(client) -> None:
    body = client.get("/api/productsList").json()
    assert body["responseCode"] == 200
    product = body["products"][0]
    assert product["id"] == 1 and product["name"] and product["price"].startswith("Rs. ")
    assert product["brand"] and product["category"]["usertype"]["usertype"] and product["category"]["category"]


@pytest.mark.parametrize(
    ("method", "path"),
    [("POST", "/api/productsList"), ("PUT", "/api/brandsList"), ("DELETE", "/api/verifyLogin")],
)
def test_unsupported_methods_answer_405_inside_a_200(client, method, path) -> None:
    response = client.request(method, path)
    assert response.status_code == 200
    assert response.json() == {"responseCode": 405, "message": "This request method is not supported."}


def test_brands_are_listed(client) -> None:
    body = client.get("/api/brandsList").json()
    assert body["responseCode"] == 200 and body["brands"] and body["brands"][0]["brand"]


@pytest.mark.parametrize("query", ["top", "tshirt", "jean", "Dress"])
def test_search_matches_case_insensitively_on_the_name(client, query) -> None:
    body = client.post("/api/searchProduct", data={"search_product": query}).json()
    assert body["responseCode"] == 200 and body["products"]
    assert all(query.lower() in product["name"].lower() for product in body["products"])


def test_search_without_the_parameter_is_a_400(client) -> None:
    body = client.post("/api/searchProduct").json()
    assert body == {"responseCode": 400, "message": "Bad request, search_product parameter is missing in POST request."}


def test_an_account_lives_from_creation_to_deletion(client, account_form) -> None:
    assert client.post("/api/createAccount", data=account_form).json()["responseCode"] == 201
    details = client.get("/api/getUserDetailByEmail", params={"email": account_form["email"]}).json()
    assert details["responseCode"] == 200 and details["user"]["email"] == account_form["email"]
    assert "password" not in details["user"]
    credentials = {"email": account_form["email"], "password": account_form["password"]}
    verified = client.post("/api/verifyLogin", data=credentials)
    assert verified.json() == {"responseCode": 200, "message": "User exists!"}
    account_form["company"] = "Updated QA Company"
    assert client.put("/api/updateAccount", data=account_form).json()["responseCode"] == 200
    updated = client.get("/api/getUserDetailByEmail", params={"email": account_form["email"]}).json()
    assert updated["user"]["company"] == "Updated QA Company"
    deleted = client.request("DELETE", "/api/deleteAccount", data=credentials)
    assert deleted.json()["responseCode"] == 200
    assert client.get("/api/getUserDetailByEmail", params={"email": account_form["email"]}).json() == {
        "responseCode": 404,
        "message": "Account not found with this email, try another email!",
    }


def test_creating_the_same_email_twice_is_refused(client, account_form) -> None:
    client.post("/api/createAccount", data=account_form)
    repeated = client.post("/api/createAccount", data=account_form)
    assert repeated.json() == {"responseCode": 400, "message": "Email already exists!"}


def test_login_verification_names_what_is_missing_or_wrong(client) -> None:
    assert client.post("/api/verifyLogin", data={"password": "secret"}).json() == {
        "responseCode": 400,
        "message": "Bad request, email or password parameter is missing in POST request.",
    }
    assert client.post("/api/verifyLogin", data={"email": "missing.user@example.com", "password": "wrong"}).json() == {
        "responseCode": 404,
        "message": "User not found!",
    }


def test_calling_the_api_creates_no_sessions(app, client, account_form) -> None:
    """The API door is stateless, and the session store shows it.

    Every call carries what it needs in its own body, so there is no visitor to
    remember -- but the page middleware used to run for these requests too,
    minting a session per call and setting a cookie on JSON nobody was going to
    send back. A process serving the API for a day filled up with one session
    per request. Twenty calls, a cookie jar that stays empty, and a store that
    holds nothing.
    """
    for _ in range(20):
        assert client.get("/api/productsList").status_code == 200
    assert client.post("/api/createAccount", data=account_form).json()["responseCode"] == 201

    assert app.state.sessions.count() == 0
    assert not client.cookies
