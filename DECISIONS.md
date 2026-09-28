# Decisions

## 1. Which lender requirements were prioritized

The assignment names FICO, PayNet, time in business, minimum and maximum amount,
equipment type, geography, and industry exclusions. Every one of those is a hard
criterion in the seed files. When a hard criterion fails, the application is ineligible
for that program. Reading the five documents added a few more requirements that decide
eligibility on their own. The full set of hard criteria across the five lenders:

| requirement | field | example |
|---|---|---|
| FICO floor | `guarantor.min_fico` | Stearns Tier 1, 725 |
| PayNet floor, or no PayNet | `business_credit.paynet` | Stearns "If no PayNet" programs use `is_null` |
| time in business | `business.years_in_business` | Stearns Tier 3, 2 years |
| amount range | `loan.amount` | per program |
| term | `loan.term_months` | per program |
| state | `business.state` | Apex does not lend in CA, NV, ND, VT |
| industry | `business.industry` | Stearns' excluded list |
| equipment type | `equipment.type` | Citizens' eligible list |
| equipment age | `equipment.age_years` | Falcon Trucking, 10 years or newer |
| private party sale | `equipment.is_private_party_sale` | lenders that decline them |
| bankruptcy lookback | `guarantor.years_since_bankruptcy` | Stearns, 7 years |
| credit history flags | `guarantor.has_judgments`, `has_foreclosures`, `has_repossessions` | Advantage+ declines these |
| comparable credit ratio | `business_credit.comparable_credit_ratio` | Apex Corp Only, 75% of the request |
| personal guarantor present | `guarantor.has_personal_guarantor` | Stearns corp-only programs use `is_false` |
| essential use, aesthetic use, fad medical | judgment fields | Stearns, Apex Medical |

Soft criteria are rare. All four in the seed files belong to Advantage+. Each of its two
programs has one on comparable credit ratio and one on years in business. Rates are
informational. They appear in results as an estimate and break ties between programs.
They never affect eligibility.

Rules kept as policy notes rather than criteria, with the reason:

| rule | why it is a note |
|---|---|
| Revolving utilization, physical location, foreign domicile, license status, CDL, years at residence, GPS, insurance | The form does not collect the fact. A criterion needs a field. |
| Citizens' term tables by mileage and model year | A term limit that depends on two other fields. A criterion is one field and one comparison. |
| Falcon's per-industry application-only limits, the amount above which financial statements are required | They decide which documents are required, not eligibility. |
| Rate adjustments, such as Falcon's aged equipment surcharge | Rates are informational. |
| Document requirements, commission caps, funding process | Not eligibility. |
| Stearns' comparable-debt alternatives, Apex's amount-conditional comparable borrowing | Several numbers and several alternatives in one rule. See `count_at_least` in section 2. |

A policy note is never scored. It is shown on the lender's page so the gap is visible.
Promoting a note later means adding an application field and a criterion.

## 2. Design decisions and why

**Deterministic matching.** Every criterion the assignment names is a numeric or
categorical comparison. Deterministic rules are reproducible and unit-testable. They run
in under a second and cost nothing per run. Models are used in two places only. One is
turning a lender PDF into a policy when it is ingested. The other is answering judgment
questions about an application.

**Criteria as rows over typed application fields.** Three options were weighed. Typed
columns, one per kind of criterion, make every new kind a migration and a form change.
One class per kind of criterion is type-safe but closed. I have worked on a rules system
built that way. Its closed set of rule kinds meant every new rule needed an engineer.
Generic rows are open but weakly typed on their own. The application fields fix the
typing. Every row is checked against the field's type and allowed operators on save.
The derive step computes derived fields before matching. It fixes expressiveness: "no
bankruptcy in 7 years" becomes `years_since_bankruptcy gte 7`. Rows work here because
every criterion has the same output: pass or fail, plus a weight. Only the condition
side needs to be expressive.

**Application fields as the line between the ops team and engineering.** The line is
where a field's value comes from. Any criterion over an existing application field is an
edit the ops team can make. A new judgment question is too. A new form field needs an
engineer. It is also a product change, because it is a new question the applicant must
answer. A new derived field needs an engineer until formula fields exist. A formula
field would let the ops team define a derived field as arithmetic over form fields.

**Guarantor combining rules.** Some application fields come from several guarantor rows.
The rule is in the field name. `guarantor.min_fico` is the minimum across guarantors.
The credit history flags are true if any guarantor has one. Homeowner and citizen are
true only if every guarantor is. None of the five documents states a combining rule.
Confidence is high for the flags and medium for homeowner and citizen. It is low that
minimum FICO is what these lenders do. When a document says "primary guarantor FICO," a
second derived field is added next to the first. No per-lender setting is needed.

**Conditional rule sets as programs.** Falcon's "All Trucking: 700 FICO" becomes a
Falcon Trucking program whose first criterion is `industry in [trucking]`. Stearns'
"If no PayNet" and "If Corp only" tables work the same way. Criteria stay flat. There is
no nesting.

**Rank as a last-resort tiebreak.** The best program is chosen by fit score, then the
lowest rate band covering the amount, then rank, then name. Rank is nullable. It is set
only where the document states an order. Falcon and Advantage+ split their programs by
situation rather than quality, so those programs have no rank. Citizens' two Tier 2
programs share a rank.

**Policy notes never scored.** A policy note is verbatim text that did not become a
criterion. Scoring it would hide a rule inside free text.

**Fit score as the share of criterion weight that passed.** Out of 100. Hard criteria
weigh 1.0. Soft criteria weigh their own weight. This gives ineligible lenders a
meaningful order too: the program that failed the fewest criteria scores highest.
Scoring by how far above a threshold the applicant is was considered. It was deferred as
more arbitrary.

**Validation in three places.** The form, for immediate feedback. FastAPI on every POST,
because curl bypasses the form. The run's first step, against the `required` flags on
the application fields. That last check exists because an application can be saved with
blanks and run later. The assignment also lists completeness as a workflow step.

**`count_at_least` for rules with several numbers.** A derived field is a parameter-free
fact about the application. A lender's numbers belong in the criterion value. When a
rule needs more than one number, the operator gets a structured value instead of a
field per lender. `count_at_least` is the first such operator. It counts trade lines,
the accounts on a credit report.

**Seed files hand-extracted and reviewed.** The five policies were written by hand from
the PDFs and reviewed line by line. They load without an API key or a model call. Tests
pin against them. When the ingest pipeline exists, it runs on the same five PDFs. Its
output is compared against the seed files. That is the accuracy test.

**No auth.** The assignment does not ask for it. `submitted_by` is a free-text broker
name until a users table exists.

**PDFs not committed, contacts fictional.** The documents are partner-distributed with
named contacts. Lender names and criteria in the seed files are real. Contact names,
emails, and phone numbers are placeholders.

**SQLAlchemy plus Pydantic rather than one fused class.** The domain classes are
Pydantic and know nothing about the database. The table classes are SQLAlchemy. A fused
class would tie validation rules to column definitions. That would make the domain
untestable without a database.

**Repositories return domain objects only.** No SQLAlchemy row leaves a repository. The
matcher is tested with in-memory objects.

**Runs start and are polled.** `POST /applications/{id}/runs` returns 202 with a run id.
The client polls `GET /runs/{id}` for the status. The status names the current step.
Then the client reads the results. Today the run executes in a FastAPI background task.
The run is one function that calls the domain's pure functions in order. Hatchet would
split that function into tasks. The domain functions would not change.

**Judgment questions behind one interface.** `DecisionProvider` has one method and three
adapters: fake, Claude on OpenRouter, and Jev on OpenRouter's `systemone` endpoint. One
environment variable, `DECISION_PROVIDER`, switches between them. Every answer is
recorded in `judgment_results` with the request, response, and latency. The same
question answered by two models is the swap the interface exists for. That swap is what
this submission demonstrates.

## 3. Simplifications and why

| simplification | why |
|---|---|
| Hatchet not wired. The run executes in a FastAPI background task behind the same start-and-poll endpoints. | The matching logic is already pure functions in the domain layer. Hatchet would change how the run's steps are scheduled, not those functions. |
| No PDF ingest pipeline. | It was the first piece of scope to drop. The seed files are the reference it will be measured against. |
| Judgment questions are asked one at a time. The OpenRouter client is not closed explicitly. | Three questions today. Parallel calls come with Hatchet. |
| `count_at_least` is defined but not evaluated. | The operator, its value shape, and the check on save exist. A criterion using it reports "not evaluated." No seed file uses it. |
| Industry and equipment lists hardcoded. | Chosen by dropdown on the form. The lists came from reading the five documents. |
| `updated_at` maintained by SQLAlchemy, not a trigger. | Covers every write path in this codebase. Writes from outside it, such as `psql`, would miss it. |
| Enum values as varchar with check constraints. | Adding a value is a Python edit plus a small migration, with no Postgres enum type to alter. |
| Corp-only programs, meaning programs for a corporation with no personal guarantor, detected by absence of guarantors. | `guarantor.has_personal_guarantor` is derived from whether any guarantor row exists. |
| Replacing or deleting a lender is blocked once runs reference it. | The database's foreign keys reject deleting or replacing a lender once match results reference its programs. The API turns that into a 409 that says to archive the lender instead. |
| Only the lender-level rate is stored per result. | Taken from the best program's rate band. Per-program rates can be recomputed from the policy. |
| Decimals inside jsonb come back as strings. | `field_values` and criterion values are jsonb. Decimal is serialized as a string to avoid float rounding. |
| Completeness is a fixed required set. | Requiring every field any active criterion references would make nearly everything required. The set would also shift with every policy edit. |
| Derived fields live on the run, not on a table. | `field_values` is the copy the run used. Old results stay explainable. |

Seed modeling notes, where a document's rule did not map cleanly:

| document says | modeled as |
|---|---|
| Stearns restricts "OTR" | The industry list has one trucking value, so the criterion excludes all trucking, not only over-the-road. Noted. |
| Stearns' comparable-debt alternatives | A policy note. Several alternatives with several numbers each. |
| Apex's comparable borrowing that varies by amount | A policy note. The ratio depends on the requested amount. |
| Falcon's per-industry application-only limits, and refrigerated trailers under 7 years | Policy notes. The age criterion holds the 10-year Class 8 limit. |
| A blank equipment year | Fails every age criterion with "not provided." |
| "over 5 years" discharged | Modeled as at least 5. |

## 4. What I would add with more time

The deferred slices come first: Hatchet for the run and for ingest, and the ingest
pipeline. After those, in order of value:

1. Formula fields, so the ops team can define derived fields without an engineer.
2. Evaluate `count_at_least`. Then promote the Stearns and Apex comparable-credit notes
   to criteria.
3. PayNet and trade lines from a credit pull instead of typed in.
4. Auth and a users table for staff.
5. Per-lender guarantor combining rules, after a needs analysis with customers or an
   industry expert. Until then, a second derived field such as `guarantor.primary_fico`.
6. Lender-defined scoring rules, such as extra points for clearing a FICO floor by 80.
   Scoring by distance above a threshold belongs here.
7. Previewing a judgment question against recent applications. Probabilities that
   cluster near 0.5 mean the question is badly posed.
8. OpenTelemetry and LangFuse for model-call traces and cost. The `trace_id` columns
   already exist.
9. Fields carry a source: stated by the applicant, or verified from a record such as a
   Secretary of State filing. Criteria evaluate the verified value when one exists.
10. A form builder, so the ops team can add application questions.
11. Modeling rate adjustments instead of noting them.
12. Training a model on human corrections, such as reclassified industries.
13. Letting a user pick the model that answers judgment questions for their run.
14. A progress bar with a time estimate from past run durations.
15. Lender-side re-review of applications passed over earlier.
16. Semantic search across lenders and applications.
17. CRM integrations.
18. A voice interface.
19. Scanned-PDF handling beyond what reading each page as an image already covers.
20. A `BEFORE UPDATE` trigger for `updated_at`, to cover writes from outside this
    codebase.

Per-lender judgment thresholds are already possible through the probability field.

## 5. Known limits and risks

- **OCR misreads pass the quote check.** In the planned pipeline, extraction runs over
  the OCR markdown. Each quote is then checked against that same markdown. If OCR read
  725 as 726, both agree and the check passes. The per-page confidence flags in the OCR
  report are the cover for that.
- **Jev availability.** Jev is integrated through OpenRouter's `systemone` endpoint.
  Direct TypeSafe signups were paused when this was built. Availability therefore
  depends on OpenRouter continuing to carry it. The OpenRouter Claude adapter is the
  fallback behind the same interface.
- **The probability behind a judgment answer is not in the explanation text.** It is
  stored in `judgment_results` and in the run's `field_values`. The criterion's
  explanation does not print it yet.
- **Citizens' term tables have gaps.** Class 8 mileage from 600,001 to 601,000 falls in
  no row. Light duty says "over 175,001" against a row that ends at 175,000. These are
  policy notes, not criteria, so nothing evaluates them yet. They need a lender question
  before they become criteria.
- **Guarantor combining rules are inferred.** None of the five documents says how to
  combine several guarantors. Minimum FICO is a conservative reading, not a stated rule.
