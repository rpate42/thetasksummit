# Recorded Statement Report Converter

This workspace contains a local-only prototype for converting recorded statement transcript `.docx` files into narrative summary `.docx` files.

## Plain-English Goal

The goal is not a perfect report writer for every scenario on earth.

The goal is a strong first-draft generator that:

- works without AI or API costs
- uses only facts stated in the transcript
- writes in a smoother, more human report style
- supports a broad range of property damage and bodily injury statements
- still requires human review before the report is used

The person asking questions is treated as the adjuster/interviewer. The person answering is treated as the interviewee, even if the transcript accidentally flips speaker numbers in places. The report should identify that interviewee according to the user-selected dropdown value, not by automatically assuming they are always the insured.

## Privacy

- The workflow is designed to run locally in this workspace.
- No web search or external upload is required for the converter itself.
- The redacted sample transcripts and summaries were used only for local inspection in this session.

## Current Files

- [report_converter.py](C:/Users/ryanp/Documents/Codex/2026-04-18-ok-i-guess-we-are-starting/report_converter.py)
- [report_regression_check.py](C:/Users/ryanp/Documents/Codex/2026-04-18-ok-i-guess-we-are-starting/report_regression_check.py)
- [report_regression_cases.json](C:/Users/ryanp/Documents/Codex/2026-04-18-ok-i-guess-we-are-starting/report_regression_cases.json)
- [web_server.py](C:/Users/ryanp/Documents/Codex/2026-04-18-ok-i-guess-we-are-starting/web_server.py)
- [requirements.txt](C:/Users/ryanp/Documents/Codex/2026-04-18-ok-i-guess-we-are-starting/requirements.txt)
- [render.yaml](C:/Users/ryanp/Documents/Codex/2026-04-18-ok-i-guess-we-are-starting/render.yaml)

## Current Scope

We are building toward two broad claim families:

- Property damage
- Bodily injury

Current redacted regression cases in this workspace:

- `ni_trans_1`: property damage, condo shower pan leak
- `ni_trans_2`: property damage, condo AC leak plus kitchen sink leak
- `ni_trans_3`: bodily injury, deck fall claim handled through a personal representative

## What The Prototype Does

- Reads a transcript `.docx`
- Detects speaker turns
- Infers interviewer vs interviewee
- Converts question/answer flow into a narrative `.docx`
- Preserves uncertainty phrases such as not knowing, not being sure, or only having limited knowledge
- Exports the report as `.docx`

## What Still Needs Improvement

- The current redacted sample set is small, so we still need more regression cases before trusting broad real-world coverage
- Multi-part questions can still split awkwardly in harder transcripts
- The converter still needs stronger generic cleanup for filler-heavy spoken language
- Bodily injury handling is better than before, but it still needs more edge-case testing
- The current engine is still partly patch-based and needs more generalized narrative rules

## Run The Converter

```powershell
& "C:\Users\ryanp\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" `
  "C:\Users\ryanp\Documents\Codex\2026-04-18-ok-i-guess-we-are-starting\report_converter.py" `
  --role insured `
  "C:\path\to\input transcript.docx" `
  "C:\path\to\output summary.docx"
```

For a custom interviewee label, use `--role-label` instead of `--role`.

```powershell
& "C:\Users\ryanp\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" `
  "C:\Users\ryanp\Documents\Codex\2026-04-18-ok-i-guess-we-are-starting\report_converter.py" `
  --role-label "Personal Representative" `
  "C:\path\to\input transcript.docx" `
  "C:\path\to\output summary.docx"
```

## Run The Website

Install dependencies first:

```powershell
& "C:\Users\ryanp\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pip install -r `
  "C:\Users\ryanp\Documents\Codex\2026-04-18-ok-i-guess-we-are-starting\requirements.txt"
```

```powershell
& "C:\Users\ryanp\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" `
  "C:\Users\ryanp\Documents\Codex\2026-04-18-ok-i-guess-we-are-starting\web_server.py" `
  --host 127.0.0.1 `
  --port 8000
```

Then open:

- [http://127.0.0.1:8000](http://127.0.0.1:8000)

The website:

- accepts a transcript `.docx`
- enforces a `100 KB` maximum transcript size
- uses the selected interviewee label from the dropdown
- generates the report locally on the server
- returns the finished `.docx` as a download
- has been verified end-to-end with a redacted sample upload

## Deploy Live With GitHub

GitHub Pages is not enough for this project because it only hosts static files and this app needs a Python backend to accept uploads and generate `.docx` files.

This repo is now set up for a GitHub-connected Python host:

- `requirements.txt` installs the Python dependencies
- `.python-version` pins Python to `3.12`
- `Procfile` provides a standard web start command
- `render.yaml` provides a ready-to-use Render Blueprint

### Recommended first live deployment

1. Push this repository to GitHub.
2. Create a new web service on Render and connect the GitHub repository.
3. Let Render detect the included `render.yaml`, or manually use:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn web_server:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
4. Wait for the first deploy to finish.
5. Open the generated public URL and test a transcript upload.

### Important note before public launch

The app is now deployable, but it is still a first public MVP. If you want to sell this to the public, the next security phase should include:

- user accounts
- HTTPS-only usage
- automatic deletion of uploaded files
- rate limiting
- better error logging and monitoring
- a privacy policy / terms page

## Run The Regression Check

This runs all redacted sample cases in `report_regression_cases.json` and tells us which claim families still have obvious problems.

```powershell
& "C:\Users\ryanp\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" `
  "C:\Users\ryanp\Documents\Codex\2026-04-18-ok-i-guess-we-are-starting\report_regression_check.py" `
  --output-dir "C:\Users\ryanp\Documents\Codex\2026-04-18-ok-i-guess-we-are-starting\regression_outputs"
```

## Current Status

At the moment:

- `ni_trans_1` passes the regression check
- `ni_trans_2` passes the regression check
- `ni_trans_3` passes the regression check

That means the current redacted sample set is stable, but the engine is still not broad enough to trust across every supported claim scenario without more testing.
