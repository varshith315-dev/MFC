# ============================================================
# AI INTEGRATED MFC BATTERY SYSTEM
# Flask Backend
#
# ESP32 → Serial → Flask → Random Forest → Website
# ============================================================

import os
import time
import threading

import joblib
import pandas as pd
import serial

from flask import Flask, jsonify, request
from flask_cors import CORS


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)

CORS(app)


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# backend/
#     app.py
#
# MFC_Website/
#     backend/
#
# AI_MFC_Option_A_Demo/
#     battery_prediction_model.joblib
#
# Therefore:
#
# backend → MFC_Website → Downloads → AI_MFC_Option_A_Demo

MODEL_PATH = os.path.join(

    BASE_DIR,

    "..",
    "..",

    "AI_MFC_Option_A_Demo",

    "battery_prediction_model.joblib"

)

MODEL_PATH = os.path.abspath(
    MODEL_PATH
)


# ============================================================
# SERIAL CONFIGURATION
# ============================================================

SERIAL_PORT = "COM3"

BAUD_RATE = 115200


# ============================================================
# INITIAL SENSOR VALUES
# ============================================================

temperature = 30.60

battery = 4.03

mfc = 4.01


# ============================================================
# SYSTEM STATUS
# ============================================================

serial_connected = False

last_update = time.time()


# ============================================================
# AI MODEL FEATURES
# ============================================================

features = [

    "Temperature_C",

    "Battery_Voltage",

    "MFC_Voltage"

]


# ============================================================
# LOAD RANDOM FOREST MODEL
# ============================================================

model = None


try:

    print()
    print("=" * 65)
    print("LOADING AI MODEL")
    print("=" * 65)

    print()

    print(
        "Model path:"
    )

    print(
        MODEL_PATH
    )

    print()


    if not os.path.exists(MODEL_PATH):

        raise FileNotFoundError(

            "Model file not found:\n"
            + MODEL_PATH

        )


    model_package = joblib.load(
        MODEL_PATH
    )


    # --------------------------------------------------------
    # IMPORTANT MODEL COMPATIBILITY FIX
    # --------------------------------------------------------
    #
    # Older version:
    #
    # {
    #     "model": RandomForestRegressor,
    #     ...
    # }
    #
    # New version:
    #
    # RandomForestRegressor
    #
    # This code supports BOTH formats.
    # --------------------------------------------------------

    if (

        isinstance(
            model_package,
            dict
        )

        and

        "model" in model_package

    ):

        model = model_package["model"]

        print(
            "Loaded packaged Random Forest model."
        )


    else:

        model = model_package

        print(
            "Loaded direct Random Forest model."
        )


    print()

    print(
        "AI model loaded successfully."
    )

    print(
        "Model type:",
        type(model).__name__
    )

    print()

except Exception as error:

    print()

    print(
        "ERROR LOADING AI MODEL:"
    )

    print(
        error
    )

    print()

    model = None


# ============================================================
# SERIAL DATA PARSER
# ============================================================

def parse_serial_data(line):

    """
    Parse ESP32 serial output.

    Supported example:

    Temperature: 29.06, Battery: 4.03, Simulated MFC: 4.01

    Also supports:

    Temperature: 29.06
    Battery: 4.03
    MFC: 4.01
    """

    global temperature
    global battery
    global mfc
    global last_update


    try:

        line = line.strip()


        if not line:

            return


        print(
            "ESP32:",
            line
        )


        # ----------------------------------------------------
        # Temperature
        # ----------------------------------------------------

        if "Temperature:" in line:

            temp_part = line.split(
                "Temperature:",
                1
            )[1]


            if "," in temp_part:

                temp_part = temp_part.split(
                    ",",
                    1
                )[0]


            temperature = float(
                temp_part.strip()
            )


        # ----------------------------------------------------
        # Battery
        # ----------------------------------------------------

        if "Battery:" in line:

            battery_part = line.split(
                "Battery:",
                1
            )[1]


            if "," in battery_part:

                battery_part = battery_part.split(
                    ",",
                    1
                )[0]


            battery = float(
                battery_part.strip()
            )


        # ----------------------------------------------------
        # Simulated MFC
        # ----------------------------------------------------

        if "Simulated MFC:" in line:

            mfc_part = line.split(
                "Simulated MFC:",
                1
            )[1]


            mfc = float(
                mfc_part.strip()
            )


        elif "MFC:" in line:

            mfc_part = line.split(
                "MFC:",
                1
            )[1]


            mfc = float(
                mfc_part.strip()
            )


        # ----------------------------------------------------
        # Update timestamp
        # ----------------------------------------------------

        last_update = time.time()


    except Exception as error:

        print(
            "Serial parsing error:",
            error
        )


# ============================================================
# SERIAL MONITORING THREAD
# ============================================================

def serial_reader():

    global serial_connected


    while True:

        try:

            print()
            print(
                "=" * 65
            )

            print(
                f"Connecting to ESP32 on {SERIAL_PORT}..."
            )

            print(
                "=" * 65
            )

            print()


            ser = serial.Serial(

                SERIAL_PORT,

                BAUD_RATE,

                timeout=1

            )


            serial_connected = True


            print(
                f"ESP32 connected successfully on {SERIAL_PORT}"
            )

            print()


            # Give ESP32 time to reset after serial connection.

            time.sleep(2)


            while True:

                try:

                    if ser.in_waiting:

                        line = (

                            ser.readline()

                            .decode(
                                "utf-8",
                                errors="ignore"
                            )

                            .strip()

                        )


                        if line:

                            parse_serial_data(
                                line
                            )


                    else:

                        time.sleep(
                            0.05
                        )


                except Exception as error:

                    print(
                        "Serial read error:",
                        error
                    )

                    break


        except Exception as error:

            serial_connected = False


            print()
            print(
                "ESP32 connection failed:"
            )

            print(
                error
            )

            print()

            print(
                f"Retrying {SERIAL_PORT} in 3 seconds..."
            )

            print()


            time.sleep(3)


        finally:

            serial_connected = False


            try:

                ser.close()

            except:

                pass


# ============================================================
# START SERIAL THREAD
# ============================================================

serial_thread = threading.Thread(

    target=serial_reader,

    daemon=True

)

serial_thread.start()


# ============================================================
# AI PREDICTION FUNCTION
# ============================================================

def predict_battery(

    temperature_value,

    battery_value,

    mfc_value

):

    """
    Predict next battery voltage using
    the trained Random Forest model.
    """


    if model is None:

        raise RuntimeError(
            "AI model is not loaded."
        )


    values = {

        "Temperature_C":
            temperature_value,

        "Battery_Voltage":
            battery_value,

        "MFC_Voltage":
            mfc_value

    }


    # --------------------------------------------------------
    # Use a DataFrame with the exact feature names used during
    # training. This prevents scikit-learn feature-name warnings.
    # --------------------------------------------------------

    input_data = pd.DataFrame(

        [

            [

                values[feature]

                for feature in features

            ]

        ],

        columns=features

    )


    prediction = model.predict(
        input_data
    )[0]


    return float(
        prediction
    )


# ============================================================
# HOME / HEALTH CHECK
# ============================================================

@app.route("/")
def home():

    return jsonify({

        "status":
            "MFC AI Backend Running",

        "esp32_connected":
            serial_connected,

        "model_loaded":
            model is not None,

        "port":
            SERIAL_PORT

    })


# ============================================================
# LIVE SENSOR DATA API
# ============================================================

@app.route(
    "/api/data",
    methods=["GET"]
)
def get_data():

    try:

        # ----------------------------------------------------
        # Generate AI prediction
        # ----------------------------------------------------

        prediction = predict_battery(

            temperature,

            battery,

            mfc

        )


    except Exception as error:

        print(
            "Prediction error:",
            error
        )


        # If AI prediction fails, use current battery
        # value as a safe fallback for the dashboard.

        prediction = battery


    return jsonify({

        "battery":
            round(
                float(battery),
                2
            ),

        "mfc":
            round(
                float(mfc),
                2
            ),

        "temperature":
            round(
                float(temperature),
                2
            ),

        "prediction":
            round(
                float(prediction),
                4
            ),

        "mfc_mode":
            "SIMULATED",

        "esp32_connected":
            serial_connected,

        "last_update":
            last_update

    })


# ============================================================
# MANUAL / LIVE AI PREDICTION API
# ============================================================

@app.route(
    "/api/predict",
    methods=["POST"]
)
def predict():

    try:

        data = request.get_json() or {}


        # ----------------------------------------------------
        # Temperature
        # ----------------------------------------------------

        temp_value = float(

            data.get(

                "temperature",

                temperature

            )

        )


        # ----------------------------------------------------
        # Battery
        # ----------------------------------------------------

        battery_value = float(

            data.get(

                "battery",

                battery

            )

        )


        # ----------------------------------------------------
        # MFC
        # ----------------------------------------------------

        mfc_value = float(

            data.get(

                "mfc",

                mfc

            )

        )


        # ----------------------------------------------------
        # AI prediction
        # ----------------------------------------------------

        prediction = predict_battery(

            temp_value,

            battery_value,

            mfc_value

        )


        return jsonify({

            "predicted_battery":

                round(

                    prediction,

                    4

                )

        })


    except Exception as error:

        print()

        print(
            "Prediction API error:"
        )

        print(
            error
        )

        print()


        return jsonify({

            "error":
                str(error)

        }), 500


# ============================================================
# RUN FLASK SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 65)
    print("AI INTEGRATED MFC BATTERY SYSTEM")
    print("FLASK BACKEND")
    print("=" * 65)

    print()

    print(
        "Website API:"
    )

    print(
        "http://127.0.0.1:5000"
    )

    print()

    print(
        "ESP32 Port:",
        SERIAL_PORT
    )

    print(
        "Baud Rate:",
        BAUD_RATE
    )

    print()

    print(
        "AI Model Loaded:",
        model is not None
    )

    print()

    print(
        "Starting Flask server..."
    )

    print()


    app.run(

        host="127.0.0.1",

        port=5000,

        debug=False,

        use_reloader=False

    )