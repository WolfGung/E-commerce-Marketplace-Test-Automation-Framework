"""The stand's pages carry the selectors and the texts the page objects use.

Parsed with selectolax, not driven by a browser: these are the same CSS
selectors `src/ecom_taf/ui/pages` uses, checked on the served HTML, so a
change to the stand's markup fails here — in milliseconds — before it fails a
browser test with a timeout.
"""
from __future__ import annotations

import pytest
from selectolax.lexbor import LexborHTMLParser

from stand.app.catalog import PRODUCTS

pytestmark = pytest.mark.stand


def _dom(response) -> LexborHTMLParser:
    assert response.status_code == 200, response.text[:200]
    return LexborHTMLParser(response.text)


def test_the_home_page_carries_the_logo_and_the_login_link(client) -> None:
    dom = _dom(client.get("/"))
    assert dom.css_first("img[alt='Website for automation practice']") is not None
    assert dom.css_first("a[href='/login']") is not None


def test_the_login_page_has_both_forms_and_the_error_lands_in_the_login_form(client) -> None:
    dom = _dom(client.get("/login"))
    for hook in ("login-email", "login-password", "login-button", "signup-name", "signup-email", "signup-button"):
        assert dom.css_first(f"[data-qa='{hook}']") is not None, hook
    forms = dom.css("form")
    assert len(forms) == 2
    login_form = next(form for form in forms if "Login" in form.text())
    assert "Signup" not in login_form.text()
    failed = client.post("/login", data={"email": "unknown.user@example.com", "password": "invalid"})
    dom = _dom(failed)
    login_form = next(form for form in dom.css("form") if "Login" in form.text())
    assert login_form.css_first("p").text(strip=True) == "Your email or password is incorrect!"


def test_an_account_created_through_the_api_can_log_in_through_the_form(client, account_form) -> None:
    assert client.post("/api/createAccount", data=account_form).json()["responseCode"] == 201
    response = client.post(
        "/login",
        data={"email": account_form["email"], "password": account_form["password"]},
        follow_redirects=False,
    )
    assert response.status_code == 303 and response.headers["location"] == "/"
    dom = _dom(client.get("/"))
    link = next(a for a in dom.css("a") if "Logged in as" in a.text())
    assert account_form["firstname"] in link.text()
    # The header greets the account by its name, which is what the site this
    # reproduces shows there. The first name is the fallback, for an account
    # created through the API with no name in it at all.
    assert account_form["name"] in link.text()


def test_the_products_grid_names_every_product_in_a_p_inside_productinfo(client) -> None:
    dom = _dom(client.get("/products"))
    names = [node.text(strip=True) for node in dom.css(".productinfo p")]
    assert names == [product["name"] for product in PRODUCTS]
    assert len(dom.css(".productinfo a.add-to-cart")) == len(PRODUCTS)
    assert dom.css_first("#search_product") is not None and dom.css_first("#submit_search") is not None
    assert dom.css_first(".features_items h2.title").text(strip=True) == "All Products"


@pytest.mark.parametrize("query", ["Dress", "Tshirt"])
def test_a_search_renders_the_searched_products_heading(client, query) -> None:
    dom = _dom(client.get("/products", params={"search": query}))
    assert dom.css_first(".features_items h2.title").text(strip=True) == "Searched Products"
    names = [node.text(strip=True) for node in dom.css(".productinfo p")]
    assert names and all(query.lower() in name.lower() for name in names)


def test_product_details_state_the_name_and_the_price_the_api_states(client) -> None:
    dom = _dom(client.get("/product_details/1"))
    assert dom.css_first(".product-information h2").text(strip=True) == PRODUCTS[0]["name"]
    assert dom.css_first(".product-information span span").text(strip=True) == PRODUCTS[0]["price"]
    assert dom.css_first("#quantity") is not None and dom.css_first("button.cart") is not None


def test_adding_to_the_cart_shows_the_modal_and_the_cart_lists_the_line(client) -> None:
    dom = _dom(client.get("/add_to_cart/1", follow_redirects=True))
    modal = dom.css_first(".modal-content")
    assert modal is not None and modal.css_first("a[href='/view_cart']") is not None
    assert dom.css_first(".modal-footer .btn-success") is not None
    client.post("/add_to_cart", data={"product_id": "2", "quantity": "3"}, follow_redirects=True)
    dom = _dom(client.get("/view_cart"))
    assert [a.text(strip=True) for a in dom.css(".cart_description h4 a")] == ["Blue Top", "Men Tshirt"]
    assert [b.text(strip=True) for b in dom.css(".cart_quantity button")] == ["1", "3"]
    assert dom.css_first("a.check_out") is not None


def test_an_empty_cart_says_so_and_renders_no_rows(client) -> None:
    dom = _dom(client.get("/view_cart"))
    assert dom.css_first("#empty_cart") is not None
    assert dom.css("#cart_info tr") == []


def test_checkout_needs_a_login_and_then_shows_the_address_of_the_account(client, account_form) -> None:
    client.get("/add_to_cart/1")
    assert client.get("/checkout", follow_redirects=False).status_code == 303
    client.post("/api/createAccount", data=account_form)
    client.post("/login", data={"email": account_form["email"], "password": account_form["password"]})
    dom = _dom(client.get("/checkout"))
    assert account_form["firstname"] in dom.css_first("#address_delivery").text()
    assert dom.css_first("a[href='/payment']") is not None


def test_payment_places_the_order_and_empties_the_cart(client, account_form) -> None:
    client.post("/api/createAccount", data=account_form)
    client.post("/login", data={"email": account_form["email"], "password": account_form["password"]})
    client.get("/add_to_cart/1")
    dom = _dom(client.get("/payment"))
    for hook in ("name-on-card", "card-number", "cvc", "expiry-month", "expiry-year", "pay-button"):
        assert dom.css_first(f"[data-qa='{hook}']") is not None, hook
    payment_data = {
        "name_on_card": "Ada Lovelace",
        "card_number": "4111111111111111",
        "cvc": "123",
        "expiry_month": "12",
        "expiry_year": "2030",
    }
    dom = _dom(client.post("/payment", data=payment_data, follow_redirects=True))
    assert dom.css_first("[data-qa='order-placed']").text(strip=True) == "ORDER PLACED!"
    assert _dom(client.get("/view_cart")).css_first("#empty_cart") is not None


def test_signup_through_the_form_creates_an_account_the_api_can_see(client, account_form) -> None:
    started = client.post(
        "/signup",
        data={"name": account_form["name"], "email": account_form["email"]},
        follow_redirects=False,
    )
    assert started.status_code == 303 and started.headers["location"] == "/signup"
    dom = _dom(client.get("/signup"))
    for hook in (
        "password", "days", "months", "years", "first_name", "last_name", "company", "address",
        "address2", "country", "state", "city", "zipcode", "mobile_number", "create-account",
    ):
        assert dom.css_first(f"[data-qa='{hook}']") is not None, hook
    assert dom.css_first("input[value='Mr']") is not None and dom.css_first("input[value='Mrs']") is not None
    assert dom.css_first("[data-qa='country'] option[value='United States']") is not None
    created = client.post(
        "/signup/create",
        data={**account_form, "address": account_form["address1"]},
        follow_redirects=True,
    )
    dom = _dom(created)
    assert dom.css_first("[data-qa='account-created']").text(strip=True) == "ACCOUNT CREATED!"
    assert dom.css_first("[data-qa='continue-button']") is not None
    response = client.get("/api/getUserDetailByEmail", params={"email": account_form["email"]})
    assert response.json()["responseCode"] == 200


def test_signup_with_a_taken_email_says_so_in_the_signup_form(client, account_form) -> None:
    client.post("/api/createAccount", data=account_form)
    dom = _dom(client.post("/signup", data={"name": "Someone", "email": account_form["email"]}))
    signup_form = next(form for form in dom.css("form") if "Signup" in form.text())
    assert signup_form.css_first("p").text(strip=True) == "Email Address already exist!"


def test_logout_forgets_the_account(client, account_form) -> None:
    client.post("/api/createAccount", data=account_form)
    client.post("/login", data={"email": account_form["email"], "password": account_form["password"]})
    assert client.get("/logout", follow_redirects=False).headers["location"] == "/login"
    assert "Logged in as" not in client.get("/").text


@pytest.mark.parametrize(
    ("data", "what"),
    [
        ({"product_id": "two", "quantity": "1"}, "the product"),
        ({"product_id": "1", "quantity": "a lot"}, "the quantity"),
    ],
    ids=["product_id", "quantity"],
)
def test_a_cart_form_that_is_not_numbers_is_a_bad_request(client, data, what) -> None:
    """A word typed into a number field is the visitor's mistake, not a crash.

    Both values are read off the form and were handed straight to `int()`, so
    anything that is not a number left the page route raising ValueError --
    which a page has no answer for: HTTP 500 and a traceback in the log for
    typing a word into the quantity box. It is a bad request, and it says so.
    """
    response = client.post("/add_to_cart", data=data, follow_redirects=False)

    assert response.status_code == 400, what
    assert response.text == "bad request"
    assert _dom(client.get("/view_cart")).css_first("#empty_cart") is not None


def test_a_signup_finished_for_a_taken_email_is_refused_rather_than_claimed(client, account_form) -> None:
    """The page cannot announce an account the store refused to create.

    `/signup` turns a taken email away, but `/signup/create` is a route of its
    own -- reachable directly, and reachable honestly when the email is taken
    between the two steps. It ignored what the store answered: ACCOUNT CREATED!
    over a store that had created nothing, and the visitor logged in as the
    holder of somebody else's account.
    """
    assert client.post("/api/createAccount", data=account_form).json()["responseCode"] == 201

    response = client.post(
        "/signup/create",
        data={**account_form, "address": account_form["address1"]},
        follow_redirects=True,
    )

    assert response.status_code == 400
    dom = LexborHTMLParser(response.text)
    assert dom.css_first("[data-qa='account-created']") is None
    signup_form = next(form for form in dom.css("form") if "Signup" in form.text())
    assert signup_form.css_first("p").text(strip=True) == "Email Address already exist!"
    assert "Logged in as" not in client.get("/").text
