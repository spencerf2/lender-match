# Demo policies

Two lender policies to paste into the add-lender page of the UI, or to send to
`POST /lenders/check` and `POST /lenders`.

| file | what happens |
|---|---|
| `new-lender-with-a-bad-criterion.json` | The check rejects it. One criterion uses the operator `in` on an integer field. The message names the program, the field, and the problem. |
| `new-lender.json` | The check passes and the lender is saved as active. Same policy with the mistake fixed. |

Paste the bad one first. Lender names are unique, so the good one has to come second.

The shape is a `LenderDraft`. Any file in `backend/seeds/lenders/` is another example.
