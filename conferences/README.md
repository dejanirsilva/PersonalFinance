# Conferences

- Source data: `conferences/presentations_2026.csv`
- Dashboard output: `conferences/presentations_2026.html`

## Generate the dashboard

```bash
python3 conferences/build_dashboard.py
```

Then open `conferences/presentations_2026.html` in your browser.

## Other years

```bash
python3 conferences/build_dashboard.py --csv conferences/presentations_2025.csv --out conferences/presentations_2025.html
```
