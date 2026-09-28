# Lender Match

Lender Match takes one equipment finance application and evaluates it against every
lender's policy, in what the code calls a run. Each policy is stored as programs made of
criteria, and the Lender Match Operations team can edit them without involving the Eng
team or necessitating a deployment. A run scores every program, ranks the lenders, and
explains each criterion that passed or failed.

## Setup

Prerequisites:

1. Docker with Compose
2. Python 3.12
3. Poetry

[mise](https://mise.jdx.dev) is optional. If installed, it selects the Python version and
virtualenv, and the Makefiles use it when available and skip otherwise.

From the repo root:

```sh
make install     # Installs backend dependencies into backend/.venv and a pre-commit hook that runs the formatter
make db-start    # Starts Postgres 17 in Docker and waits until it accepts connections
```

From `backend/`:

```sh
cp .env.example .env   # Creates .env with DATABASE_URL set to the Docker Postgres
make migrate           # Runs alembic upgrade head
make seed              # Loads the five lender policies and the judgment questions
make run               # Serves the API on port 8000
```

The API serves at <http://localhost:8000>. Its OpenAPI page is at <http://localhost:8000/docs>.

The lender PDFs are not committed since they are partner-distributed documents with named
contacts. The seed files under `backend/seeds/` carry the policies extracted from them,
with fictional contacts.

### Frontend

Confirm once the frontend lands.

```sh
cd frontend && pnpm install && pnpm dev   # http://localhost:5173
```

## Architecture

The backend is Python with FastAPI, Pydantic, SQLAlchemy, and Postgres. It is split into
layers, and each layer depends only on the ones below it. The domain layer has no
infrastructure dependencies: no SQLAlchemy, no FastAPI, no other layer.

Paths in the table below are under `backend/lender_match/` unless noted.

| layer | directory | holds |
|---|---|---|
| domain | `domain/` | Application fields, policies, loan applications and their results, the matcher, and the `DecisionProvider` interface. |
| repositories | `repositories/` | Database access. Each accepts and returns domain classes only. |
| services | `services/` | The six steps of a run, and the check of a policy against the application fields before a lender is saved. |
| api | `api/` | FastAPI routes, one file per resource. |
| db and migrations | `db/`, `../alembic/` | One SQLAlchemy class per table, and the migrations. |
| seeds | `../seeds/` | One JSON file per lender, plus the questions a model answers about an application (the judgment questions). |

### Routes

Routes receive their database session through FastAPI's dependency injection. The domain
layer's classes are the request and response models, so there is no separate API schema.

### Criteria

A criterion is one rule in a lender's policy, stored as a database row rather than as
code. The row names the application field it tests, such as the minimum FICO across
guarantors. It names the operator to apply, such as at least, at most, between, in a list,
or not in a list. It holds the value to compare against, such as "725". It says whether
the rule is hard or soft: a failed hard criterion makes the application ineligible for
that program, and a failed soft criterion only lowers the program's fit score, the 0 to
100 number used for ranking. A soft criterion also carries a weight for how much it counts
toward that score. The field must come from the application fields, the list of everything
the system knows about an application, each with a type. The operations team adds a rule
by adding a row, and every row is checked on save so the operator and value fit the
field's type.

### Matcher module

The matcher module is deterministic and built from pure functions.

### Judgment questions

Judgment questions are questions a model such as Jev (or Claude Sonnet 5) answers about an
application, like whether the equipment is essential to the business. They are answered
through the `DecisionProvider` interface: one method that takes a question and the application
and returns an answer. The run calls that method and does not know what is behind it. This
submission ships a fake provider, and the Jev adapter goes behind the same interface
later.

### Runs

A run starts in a background task, the client polls its status, and results are stored per
criterion with the actual value and an explanation.

## API

The OpenAPI page at `/docs` is authoritative.

| method and path | purpose |
|---|---|
| `POST /applications`, `GET /applications` | Create and list applications. |
| `GET PUT DELETE /applications/{id}` | Read, replace, or delete one application. |
| `POST /applications/{id}/runs` | Start a run. Returns 202 and the run id. |
| `GET /applications/{id}/runs` | Run history, for re-evaluation after a policy edit. |
| `GET /runs/{id}` | Status, current step, error. |
| `GET /runs/{id}/results` | Ranked lenders with program and criterion detail. |
| `GET POST /lenders` | List lenders. Add a lender with its full policy. |
| `GET PUT DELETE /lenders/{id}` | Read, replace, or delete one lender. |
| `GET POST /judgment-questions` | List judgment questions. POST upserts by key, so it also edits. No PUT or DELETE. |
| `GET /application-fields` | Every field a criterion may test, with its type and operators. A criterion edit form reads this. |

Program and criterion edits go through `PUT /lenders/{id}` with the full policy.
`/lenders/check` validates a policy without saving it.

## Testing

From `backend/`:

```sh
make test              # the matcher and seed file tests
make validate-seeds    # every seed file parses and passes the criterion check
```

The matcher module was built test-driven development style. Its tests were written first
and observed failing non-vacuously (for the right reasons, not because of a missing import
or something simple like a typo). The implementation was then added to take them from red
to green. This increases confidence that the tests check the matching logic itself rather
than whatever the code happened to do.
