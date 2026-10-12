# Learn4All — Web frontend

A standalone, build-free web client for the Learn4All REST API. It contains **no backend code**:
every piece of data comes from HTTP calls in [`js/api.js`](js/api.js). You can replace this folder
with any other frontend (React, Vue, Flutter, mobile…) without touching the backend.

## Run

```bash
python3 -m http.server 5500      # from this folder
# open http://127.0.0.1:5500
```

The API is expected at `http://127.0.0.1:8000`. To point at another server:

* open `http://127.0.0.1:5500/?api=http://my-host:9000` (remembered in localStorage), or
* use **Settings → API connection**, or
* change `DEFAULT_API_BASE_URL` in [`js/config.js`](js/config.js).

## Structure

| File | Purpose |
|------|---------|
| `index.html` | App shell (sidebar, top bar) |
| `css/styles.css` | Design tokens (light/dark), layout and components |
| `js/config.js` | API base URL resolution |
| `js/api.js` | One function per API endpoint; throws `ApiError {status, code, details}` |
| `js/store.js` | Cache of reference data (meta, settings, subjects, learners) |
| `js/ui.js` | Safe HTML templating, formatting, modal, toast, form helpers |
| `js/charts.js` | Dependency-free SVG line / bar / donut / sparkline charts |
| `js/forms.js` | Learner, assessment and resource dialogs |
| `js/views/*.js` | One module per page: `render(root, params) → title` |
| `js/app.js` | Hash router (`#/student/3`), theme toggle, API health pill |

## Pages

Class dashboard · Learners · Learner report (`#/student/{id}`) · Assessments (with bulk CSV import) ·
Resources · Subjects & topics · Data quality · Rules explained · Settings · API reference.

Accessibility: semantic HTML, a skip link, visible focus, ARIA labels, keyboard-operable rows and dialogs
(Esc closes them), reduced-motion support, high-contrast status colours and a dark mode.
