# Marketplace Test Automation Framework

A test automation framework built from scratch for an online shop: API and browser tests run in CI against a stand shipped in this repository.

[![CI](https://github.com/WolfGung/Marketplace-Test-Automation-Framework/actions/workflows/ci.yml/badge.svg)](https://github.com/WolfGung/Marketplace-Test-Automation-Framework/actions/workflows/ci.yml)
[![live report](https://img.shields.io/badge/live%20report-Allure-brightgreen)](https://wolfgung.github.io/Marketplace-Test-Automation-Framework/report/)
[![python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![license: MIT](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

## Coverage

| What is checked | Checks | Where |
| --- | --- | --- |
| The REST API | 14 | `tests/api` |
| The browser | 8 | `tests/ui` |
| End to end, across both doors | 2 | `tests/e2e` |
| The application under test | 24 | the three rows above |
| Of those, the smoke set | 5 | `-m smoke` |
| The stand's own contract, without a browser | 31 | `tests/stand` |

Counted by `pytest --collect-only`, and pinned by `tests/unit/test_showcase_figures.py` so a number here cannot drift away from the suite it describes. The stand's row is the contract of the shop the suite runs against — the selectors and the messages the page objects and the API client depend on — checked with an HTTP client and a parser, in milliseconds, before any browser test could fail on them.

The rows above the stand's are the checks of the marketplace, and they are the only ones counted — here, on the published page, and in the figures. The stand's contract is not one of them, and neither are the checks this project carries over its own tooling in [`tests/unit/`](tests/unit): its settings, the diagnostics captured when a browser test fails, the report's failure grouping, the build of the published page, and the pins that keep every number above honest. Both are deliberately left out of the arithmetic, because neither proves anything about the application under test.

## What this shows

- **An API test suite and end-to-end tests for a checkout.** The API suite checks the catalogue, search and accounts; the purchase is driven through the browser and checked through the API.
- **A suite that does not depend on someone else's website.** CI runs against a stand in the repository; a nightly job only reports drift of the public site.
- **Failures a developer can act on.** Every browser test keeps a video and a trace, and every run publishes an Allure report with a trend.

## How the checks are layered

The suite covers three layers of the same shop: an API test suite for the rules behind the data — the catalogue, search, accounts and the answer each gives to input it should reject; browser tests for what only a customer can see; and end-to-end tests that follow a checkout flow from an empty cart to a placed order. Every run publishes an Allure report holding each case, its steps and the trend across runs, so what the suite did can be read without cloning it.

A check sits at the lowest layer that can still prove the thing that matters. Product listings, search results, account creation and deletion and the answers each gives to input it should reject are data rules, so they are asserted against the REST API, where a failure names its own cause. Only behaviour a person can see is driven through a browser. The end-to-end pair exists because the purchase is the one flow whose whole value is that the separate parts hold together.

## Evidence

Start with the evidence: **[the live Allure report](https://wolfgung.github.io/Marketplace-Test-Automation-Framework/report/)** holds every case, its steps and the trend across runs, and **[the project page](https://wolfgung.github.io/Marketplace-Test-Automation-Framework/)** — generated from the run that produced the numbers on it — carries a recording of the purchase running front to back and **[the Playwright trace of that same purchase](https://trace.playwright.dev/?trace=https://wolfgung.github.io/Marketplace-Test-Automation-Framework/media/checkout-trace.zip)**, which can be stepped through action by action with the page's DOM at each step.

[![The overview of the published Allure report: 24 test cases, 100% passing, split by suite into 14 in tests.api, 8 in tests.ui and 2 in tests.e2e, beside a trend that is green across every publication before it. Categories reads "0 items total" and Executors says there is no information about test executors.](allure-report-screenshot.png)](https://wolfgung.github.io/Marketplace-Test-Automation-Framework/report/)

That is the published report, photographed from the live site, and the two empty panels are part of what it says. Categories holds nothing because publication waits for all three test jobs, so the run that publishes is a passing one and has no failures to group; Executors is empty because the pipeline writes no executor file. The trend beside them is real: it carries over from the previous publication on every run.

[![The pipeline's run page on github.com, read logged out: a run of the CI workflow on main under a green check, Status reading Success beside the commit that started it, and its jobs both listed down the side and drawn as a graph — the API suite, the framework and stand checks and the browser suite, all against the stand and all green; the publish step that waited for them; and, skipped on a push as designed, the cross-browser matrix, the probe of the public site and the drift check that only that probe can start.](showcase/images/ci-run.png)](https://github.com/WolfGung/Marketplace-Test-Automation-Framework/actions/runs/35795572036)

That is the run the CI badge at the top of this page points at, photographed from the public run page by `PYTHONPATH=. python scripts/make-assets.py --only ci-run --ci-run <run url>`, which reads the status off the page and refuses to photograph a run that is not green.

[![Three bands. At the top the three test directories. Below them the code every test reuses: the HTTP client and the API resources, the page objects, the typed models, the per-run data factory and the settings. At the bottom the shop under test, which ships with this repository: the stand, a small FastAPI shop, and under it the two doors it answers on — the REST API at /api and the pages a browser drives. Below those, drawn with a dashed edge because it is somebody else's system, the public demo site the stand reproduces and one nightly job reads. The API tests reach the API through the client, the browser tests reach the pages through Playwright driving Chromium, and the end-to-end path runs down the middle through both doors at once. The figure states a case count for each directory; open it to read them.](showcase/assets/architecture.svg)](showcase/assets/architecture.svg)

Tests hold the assertions; everything reusable sits below them, so a change in the application lands in one file. The end-to-end path is the one route that crosses both doors. [Open the diagram at full size.](showcase/assets/architecture.svg)

## Two targets

The suite runs, by default, against **the stand**: a small shop in [`stand/`](stand) with the same pages and the same REST API as the public demo site [Automation Exercise](https://www.automationexercise.com/) — registration and login, a catalogue with search, a cart, checkout and payment, and the API's `responseCode`-inside-HTTP-200 convention, form-encoded bodies and messages. It is a FastAPI application with one in-memory account store shared by the API and the browser session, and it is started by the suite itself when nothing answers on its port, so a clean clone runs green with no second terminal and no network.

The public site is still there, one setting away (`TEST_ENV=prod`), and one CI job uses it: the nightly **drift check** runs the read-only smoke set — `-m "smoke and not destructive"`, which creates no account and places no order on somebody else's site — and never blocks the pipeline. That job keeps the page objects honest against the real markup; the stand keeps the pipeline honest against the code.

## Tech Stack

- **Python 3.11+**
- **Pytest**
- **Playwright**
- **REST API** (`httpx`)
- **FastAPI** (the stand in `stand/`)
- **Allure Report**
- **Docker**
- **CI/CD** (GitHub Actions)

## Four decisions that keep it maintainable

**API responses are parsed into typed models, not read as dictionaries.** The catalogue and the search results go through `ProductsResponse` and `Product` in [`src/ecom_taf/models/`](src/ecom_taf/models) before a test asserts anything about them, and a registration travels the same way in the other direction through `UserAccount`. A field that is renamed, dropped or returned with the wrong type fails there, naming the field, instead of surfacing three assertions later as a `KeyError` — or as a comparison against `None` that happens to pass.

**One fact is checked through two doors.** [`tests/e2e/test_api_ui_product_consistency.py`](tests/e2e/test_api_ui_product_consistency.py) reads a product from the REST API, opens the same product in the browser and compares the name and the price. Both layers can be green while the two disagree; that disagreement is what a customer sees, and neither suite on its own can catch it.

**The suite is a polite guest on a site it does not own.** The `registered_user` fixture in [`tests/conftest.py`](tests/conftest.py) creates a disposable account through the API, hands it to the test and deletes it afterwards, so a run leaves the application as it found it. That is also why the hook that captures a failure screenshot is written never to raise: a crashed session skips teardown, and skipped teardown means an account left behind on somebody else's site. Against the stand the same fixture runs unchanged, and the account it creates lives in the stand's memory for exactly one test.

**Per-run data comes from a factory, not from constants.** [`src/ecom_taf/data/user_factory.py`](src/ecom_taf/data/user_factory.py) builds a fresh account for every test that needs one, address and all. A suite pinned to a constant email passes once and then fails on "already registered", and the usual repair — deleting the record by hand between runs — is a step that cannot exist inside a pipeline.

## Architecture

```
src/ecom_taf/          # reusable framework (not tests)
  api/                 # HTTP client + resource APIs
  config/              # environment-based settings
  data/                # factories / test data builders
  models/              # typed payloads
  ui/pages/            # Page Object Model
tests/
  api/                 # contract / resource tests
  ui/                  # browser tests
  e2e/                 # business flows + API/UI checks
  stand/               # the contract of the shop below, over HTTP, no browser
  unit/                # checks of this framework, not of the marketplace
stand/                 # the shop the suite runs against (FastAPI)
```

That split is the four decisions above in directory form: a test module holds assertions and nothing else, everything a test reuses sits under `src/ecom_taf/` where a change in the application lands once, and `tests/unit/` checks that framework rather than the marketplace.

Business status codes for this AUT often live in JSON `responseCode` even when HTTP status is 200. The API client normalizes that so tests assert on the real result, not only the transport layer.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,stand]"
playwright install chromium
cp .env.example .env
```

## Run tests

```bash
# all tests
pytest

# layers
pytest -m api
pytest -m ui
pytest -m e2e
pytest -m smoke

# the drift check against the public site
TEST_ENV=prod pytest -m "smoke and not destructive"

# the shop on its own, http://127.0.0.1:8092
make stand

# Allure results
pytest --alluredir=allure-results

# record the end-to-end run: a WebM video and a Playwright trace, one of each
# per e2e case, under videos/ and traces/
RECORD_VIDEO=true pytest -m e2e
playwright show-trace traces/checkout-test_logged_in_user_can_place_an_order.zip

# Allure CLI is not installed via pip. You need Java + Allure 2, then:
allure serve allure-results
```

Useful Make targets: `make install`, `make test`, `make test-api`, `make test-ui`, `make test-e2e`, `make test-smoke`, `make test-stand`, `make test-public`, `make stand`, `make report`, `make lint`.

## Docker

One command, and it needs nothing on the machine but Docker — no Python, no Playwright, no browser:

```bash
docker compose run --rm tests
```

The first run builds the images (Python 3.12, this framework, Chromium and the system libraries it needs: a few minutes, roughly 3 GB on disk). The command then starts the stand as a service, waits for its healthcheck, and runs the API layer against it, writing Allure results to `./allure-results` through the bind mount declared in `docker-compose.yml`. The API layer is the default because it is the one layer that needs no browser and no display to be worth running. Pass `--build` to rebuild after changing the code, and `docker compose down` when you are finished: the stand keeps running between `run` commands, and that is what stops it.

Any other selection is one argument away, and the browser layers run in the same container because Chromium is already in the image:

```bash
docker compose run --rm tests pytest -m ui --alluredir=allure-results
docker compose run --rm tests pytest tests/unit          # the framework's own checks
```

The drift check runs from the same container, but the compose file pins the stand's addresses for the `tests` service, so the target is moved on the command line rather than by `TEST_ENV` alone:

```bash
docker compose run --rm \
  -e TEST_ENV=prod \
  -e BASE_URL=https://www.automationexercise.com \
  -e API_BASE_URL=https://www.automationexercise.com/api \
  tests pytest -m "smoke and not destructive"
```

Two things worth knowing, both found by running it rather than by reading it. The container runs as root, so `allure-results/` and everything in it belongs to root on the host — `sudo chown -R "$USER" allure-results` if a local run has to write into the same directory afterwards. And the image copies five more directories in as well as `tests/`: `allure/` (the failure grouping the suite copies into every results directory), `showcase/` and `scripts/` (imported and read by the framework's own checks, which also run the showcase's build script with the bash, curl and git the image already has), `stand/` (the shop itself — the fixture starts it, and `tests/stand` imports it) and `.github/` (the pipeline's shape, which one of those checks reads straight off disk), plus `.env.example`, the `Makefile` and the report screenshot, which three more of those checks read as the documentation and the evidence they pin. pytest imports the whole `tests/` tree before `-m` selects anything from it, so while any of them were missing, even `-m api` stopped at collection on an import that has nothing to do with the API.

## Configuration

Every setting in the project is here: `src/ecom_taf/config/settings.py` reads
these names and nothing else, `.env.example` lists the same set, and each is
read from the environment or from a `.env` beside it. A value set in either
one is honoured, including over the target `TEST_ENV` selects.

`TEST_ENV` names a pair of addresses — `local` is the stand, `prod` the public
site — and `BASE_URL` and `API_BASE_URL` override whichever pair it named. That
is why those two are the only lines commented out in `.env.example`: copy the
file as it is and a run follows `TEST_ENV`; uncomment one to point the suite at
a stand on another port without inventing a target for it.

| Variable | Default | Description |
| --- | --- | --- |
| `TEST_ENV` | `local` | `local` (the stand) or `prod` (the public site) |
| `BASE_URL` | `http://127.0.0.1:8092` | The shop's pages |
| `API_BASE_URL` | `http://127.0.0.1:8092/api` | REST API |
| `HEADLESS` | `true` | Playwright headless mode |
| `BROWSER` | `chromium` | `chromium`, `firefox` or `webkit` |
| `SLOW_MO_MS` | `0` | Pause between Playwright actions, for watching a run |
| `DEFAULT_TIMEOUT_MS` | `15000` | Playwright's per-action timeout |
| `HTTP_TIMEOUT_S` | `20` | `httpx` timeout for the API layer |
| `RECORD_VIDEO` | `false` | Record the end-to-end cases: a WebM and a Playwright trace each |
| `VIDEO_DIR` | `videos` | Where those recordings are written |
| `TRACE_DIR` | `traces` | Where those traces are written |

## Markers

`api`, `ui`, `e2e`, `smoke`, `negative`, `integration`, `destructive`, `stand`

`destructive` marks the cases that create accounts or place orders — they never run against the public site; `stand` marks the contract of the shop in `stand/`.

## What the report shows

Every case carries an `epic` and a `feature`, so the report's **Behaviors** view is the suite read by what it covers — API, UI and E2E, and under each of them Account, Login, Products, Brands, Search, Cart, Checkout — rather than by the directory the file happens to live in.

Every case also carries a **severity**, and it means one thing: how much the defect that case would catch costs. The purchase is `blocker`. An account that cannot be created, a catalogue that does not answer, a sign-in that does not work and a wrong password that is accepted are `critical`. Input validation and unsupported methods are `minor`. A case does not get a high severity for having been difficult to write.

And every case links the page or the documented endpoint it drives, so a failure in the report is one click from the thing that failed.

## Cross-browser

The engine is a setting (`BROWSER`, read into `Settings.browser`), so the whole browser suite runs on Firefox or WebKit without a code change:

```bash
BROWSER=firefox pytest -m "ui or e2e"
```

CI has a `browsers` job that does exactly that on all three engines, and it runs **only on manual dispatch** — not on a push, not on the schedule. No assertion here is about how a page renders in one engine versus another, so the second and third leg answer the question the first already answered, at three times the runner minutes. Whether the suite still runs on Firefox and WebKit is a question worth asking deliberately — after a Playwright upgrade, when a locator changes — which is when the button gets pressed.

## Related work

Six more repositories from the same portfolio:

- **[Toolshop-Test-Automation-Framework](https://github.com/WolfGung/Toolshop-Test-Automation-Framework)** — a test automation framework built from scratch for an online shop: API, browser and end-to-end cases against a public demo shop or a local Docker stand, with test design documents.
- **[Web-Scraping-Automation-Framework](https://github.com/WolfGung/Web-Scraping-Automation-Framework)** — a scraper that collects two practice sites and a demo store of its own, over HTTP and through a browser, detects changes between nightly runs and publishes the data, the change report and the test report.
- **[Test-Suite-Rescue](https://github.com/WolfGung/Test-Suite-Rescue)** — a deliberately sick test suite, its cured version on Playwright and Selenium, and the measured difference between them — twenty runs of each, reproducible with one command.
- **[API-Test-Generator](https://github.com/WolfGung/API-Test-Generator)** — a command-line tool that turns an OpenAPI document or a Postman collection into a runnable pytest suite, with four generated suites committed and proven against a sample API in CI.
- **[Accessibility-Test-Automation-Framework](https://github.com/WolfGung/Accessibility-Test-Automation-Framework)** — an axe-core scan and keyboard-only checks against a shop served in an accessible and a deliberately broken mode, every finding mapped to a WCAG 2.1 AA criterion, with a manual checklist for what automation cannot see.
- **[LLM-Evaluation-Framework](https://github.com/WolfGung/LLM-Evaluation-Framework)** — layered checks for two LLM features, a RAG support assistant and ticket triage: rules, reference checks, safety cases against prompt injection and data leaks, repeat-run stability, an LLM judge measured against human labels and for position bias, and a regression gate in CI, all replayed from real recorded calls.

## Hire me

I take short, well-defined jobs: a test automation framework from scratch, an API test suite for an existing backend, end-to-end tests for a critical flow, fixing flaky tests and reducing run time, setting up CI for existing tests, scrapers and data pipelines. Profile on Guru: [https://www.guru.com/freelancers/pavel-zhukov-atum](https://www.guru.com/freelancers/pavel-zhukov-atum). Time zone: Central European Time (CET/CEST), so my working hours overlap with Central European business hours. I work in writing.
