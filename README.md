# MSU Registration Helper

Desktop GUI helper for preparing and running Mahasarakham University course registration through a controlled browser session. Users log in manually in the browser; the app does not store passwords.

## Key Features

- PyQt6 desktop GUI
- Playwright-powered browser automation
- Manual login only; no password storage
- Waiting-room/session checks
- Current registration queue
- Saved Course Profiles for preparing course lists before registration day
- Per-course result history in SQLite
- CSV export/import for saved profiles
- CSV export for registration result history
- Retry settings with a default non-spam delay of 5-10 seconds

## Project Structure

```text
msureghelpper/
|-- main.py
|-- config.py
|-- requirements.txt
|-- automation/
|   |-- browser.py
|   `-- register.py
|-- database/
|   `-- db.py
|-- gui/
|   |-- app.py
|   |-- styles.py
|   `-- widgets.py
|-- models/
|   `-- course.py
`-- demo_server/
    |-- server.py
    |-- index.html
    |-- dashboard.html
    |-- register.html
    `-- result.html
```

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

For demo testing, set `MODE = "demo"` in `config.py`, then run:

```bash
python demo_server/server.py
python main.py
```

For production use, set `MODE = "production"` in `config.py`, then run:

```bash
python main.py
```

## Build For Distribution

Use this when you want to upload an installer to Google Drive or another download host.

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_release.ps1 -Version 1.0.0
```

The build creates:

- `release/MSU-Registration-Helper-Setup-1.0.0.exe` - installer for normal users
- `release/MSU-Registration-Helper-1.0.0-portable.zip` - portable folder build

The installer bundles:

- Python runtime
- PyQt6
- Playwright Python package
- Playwright Chromium browser runtime

Users do not need to install Python, PyQt6, Playwright, or Chromium separately.

Runtime user data is created per machine at:

```text
%LOCALAPPDATA%\MSU Registration Helper
```

That folder stores the local SQLite database, browser profile, logs, and screenshots. Do not distribute your local `msu_profile`, `msu_helper.db`, `logs`, or `screenshots` folders.

## Saved Course Profiles

Saved Course Profiles let you prepare course lists before registration day and load only enabled courses into the active registration queue when you are ready.

### Before registration day

1. Open the program.
2. In **Saved Course Profiles**, click **Create**.
3. Enter a profile name, for example `Term 2569/1`.
4. Enter the academic term, for example `2569/1`.
5. Click **Add Course** and enter course code, section/group, note, priority/order, and enabled/disabled status.
6. Use **Edit**, **Remove**, **Enable/Disable**, **Up**, and **Down** to maintain the profile.
7. Use **Export CSV** to back up the selected profile.
8. Use **Import CSV** to create a profile from a CSV file.

### On registration day

1. Open the program.
2. Click **Open Browser**.
3. Log in manually in the browser.
4. Select the saved profile, for example `Term 2569/1`.
5. Click **Load to Queue**.
6. Adjust **Retry count** and **Retry delay seconds** if needed.
7. Click **Register All Enabled / Queued**.
8. The program processes courses one by one, waits after each course, updates the queue status, and records each result into History.

## Database Tables

`course_profiles`

- `id`
- `name`
- `academic_term`
- `created_at`
- `updated_at`

`saved_courses`

- `id`
- `profile_id`
- `course_code`
- `section`
- `note`
- `priority`
- `enabled`
- `created_at`

The app also keeps the existing current queue in `courses` and registration results in `history`.

## Result History

Per-course history supports:

- `pending`
- `success`
- `full`
- `conflict`
- `invalid`
- `failed`
- `skipped`

Open **History** to review results or click **Export History CSV** to export the registration result history.

## CSV Profile Format

```csv
profile_name,academic_term,course_code,section,note,priority,enabled
Term 2569/1,2569/1,0041001,1,Main choice,1,1
Term 2569/1,2569/1,0041002,2,Backup section,2,0
```

## Safety Notes

- The user logs in manually through the browser.
- The app does not collect or store passwords.
- Retry delay should stay at 5 seconds or more to avoid request spam.
- Use this as a personal helper and verify final results on the official registration website.

## License

Educational/personal portfolio project. Mahasarakham University and its registration system remain the property of their respective owners.
