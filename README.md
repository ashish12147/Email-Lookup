# IntelBase Lookup Web App

This repository contains a simple Flask-based web application that performs email lookups using the [IntelBase](https://intelbase.is) API.

## Features

- 🔍 **Email lookup** – Query IntelBase for information associated with an email address.
- 🔐 **Consent gate** – Users must affirm that they have permission to check the email.
- 🧠 **Breach summary** – Shows a concise list of breaches if available.
- 🔗 **Modules/Accounts** – Identifies associated modules such as GitHub, Google, or domain and displays key facts for each.
- 💻 **Responsive UI** – Built with vanilla HTML/CSS/JS and styled for a modern dark theme.
- ⚙️ **Easy configuration** – Set your IntelBase API key via the environment variable `INTELBASE_API_KEY`.

## Getting Started

1. **Clone this repo**

   ```bash
   git clone https://github.com/yourusername/intelbase-lookup-webapp.git
   cd intelbase-lookup-webapp
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Export your API key** (replace with your own key)

   ```bash
   export INTELBASE_API_KEY="in_YOURKEYHERE"
   ```

4. **Run the app**

   ```bash
   python app.py
   ```

5. **Browse** to `http://127.0.0.1:5000` and test your lookup.

## Project Structure

- `app.py` – Backend server using Flask. Handles API requests and formats results for the UI.
- `requirements.txt` – Python dependencies.
- `templates/index.html` – HTML template for the front-end.
- `static/style.css` – Global styles and component CSS.
- `static/app.js` – Front-end logic using vanilla JavaScript to call the backend and render results.
- `README.md` – This file.

## Note

This project is intended for educational purposes and demonstrates how to integrate the IntelBase API into a small web application. The breach summary is truncated for privacy; always use this data responsibly and ensure you have consent to search any email address.