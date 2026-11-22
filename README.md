<h1 align="center">💧 SensiCup</h1>
<p align="center"><i>a smart cup that tells you what's actually in your water</i></p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/Flask-SocketIO-000000?logo=flask">
  <img src="https://img.shields.io/badge/ESP32-Arduino-00979D?logo=arduino&logoColor=white">
  <img src="https://img.shields.io/badge/ML-XGBoost-ff6f00">
</p>

---

## What is this?

The whole idea started with our school water fountain. Honestly, we had no idea if the water we were drinking every day was clean or not, and there wasn't really an easy way to check. That's basically why we built SensiCup.

SensiCup is a cup with pH, TDS (total dissolved solids), salinity, and temperature sensors built in. The sensors connect to an ESP32, which then sends the readings to a website in real time. On top of that, a machine learning model looks at all four readings together and gives the water a cleanliness score from 0 to 100, so you don't have to be a chemist to understand the results.

## What it can do

- **Live sensor readings.** As soon as the cup takes a reading, it shows up on the site without refreshing, thanks to Flask-SocketIO.
- **A cleanliness score.** An XGBoost model weighs pH the most, then TDS, then temperature, and finally salinity, and turns all of that into one easy number.
- **A camera feed.** There's a live camera view through OpenCV, so you can actually see the water you're testing.
- **Saved databases.** You can save readings and photos into your own little database, and then download them later as a zip.
- **Pop-up explainers.** If you don't know what TDS or salinity means (which, fair), you can click on it and get a quick explanation with a diagram.
- **A working contact form** that emails our team directly.

## Built with

| Part | What we used |
|---|---|
| Hardware | ESP32, Arduino, pH sensor, TDS sensor, salinity sensor, temperature sensor |
| Backend | Python, Flask, Flask-SocketIO, SQLite |
| Machine learning | XGBoost, scikit-learn, pandas, NumPy |
| Camera | OpenCV |
| Frontend | HTML, CSS, JavaScript |

## Running it yourself

First, clone the repo and hop into the folder:

```bash
git clone https://github.com/KUlusoy/SensiCup.git
cd SensiCup
```

Next, set up a virtual environment and install everything:

```bash
python -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

After that, the contact form needs an email login to send messages, so set these environment variables with your own Gmail and an app password:

```bash
export EMAIL_ADDRESS="your-email@gmail.com"
export EMAIL_PASSWORD="your-app-password"
export SECRET_KEY="anything-random"
```

(On Windows PowerShell, it's `$env:EMAIL_ADDRESS="your-email@gmail.com"` and so on.)

Finally, start the app:

```bash
python sensicup_app.py
```

Then open the link it prints in your browser, and you're good to go. If you don't have the physical cup, you can still visit `/test-data/<cup_id>` to send in fake readings and see how everything works.

## How it's organized

```
SensiCup/
├── sensicup_app.py           # the main Flask app and all the routes
├── water_quality_model.py    # trains and runs the cleanliness model
├── continuous_monitoring.py  # keeps checking new readings in the background
├── test_system.py            # quick tests for the whole pipeline
├── templates/                # the website pages
└── static/                   # images, diagrams, and the logo
```

## What I learned

Honestly, getting the hardware and the website to talk to each other was the hardest part. At first, the TDS sensor was the only one updating live, and then getting all four sensors running through the ESP32 at the same time took a lot of trial and error. Also, deploying to Heroku with SocketIO was its own adventure. Still, seeing the numbers pop up on the site in real time for the first time made all of it worth it.

## The team

Built with [@stephanieyangg](https://github.com/stephanieyangg) and the rest of the SensiCup team.

