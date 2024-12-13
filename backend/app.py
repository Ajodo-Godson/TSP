from flask import Flask, jsonify, render_template
from flask_cors import CORS
from solver import solve_tsp
import logging
import numpy as np
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(
    __name__,
    static_folder="../frontend/static",
    template_folder="../frontend/",
)
CORS(app)

# Configure logging for Flask
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)

# Retrieve the Google Maps API key from environment variables
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_API_KEY")

# Run the TSP solver on startup and store the result
try:
    logging.info("Starting TSP solver...")
    tsp_result = solve_tsp()
    logging.info("TSP solver completed successfully.")
except Exception as e:
    logging.error(f"Error running TSP solver: {e}")
    tsp_result = {"error": "TSP solver failed."}


def convert_types(obj):
    """
    Recursively convert numpy data types to native Python types.
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_types(item) for item in obj]
    else:
        return obj


@app.route("/")
def home():
    """Serve the frontend with the Google Maps API key."""
    return render_template("index.html", google_maps_api_key=GOOGLE_MAPS_API_KEY)


@app.route("/get_tsp_result", methods=["GET"])
def get_tsp_result():
    """
    API endpoint to get the precomputed Traveling Salesman Problem result.
    """
    if not tsp_result:
        logging.error("TSP result not available.")
        return jsonify({"error": "TSP result not available."}), 500

    if "error" in tsp_result:
        logging.error(f"TSP Solver Error: {tsp_result['error']}")
        return jsonify(tsp_result), 500

    # Convert 'tsp_result' to serializable types without modifying solver.py
    serializable_result = convert_types(tsp_result)

    logging.info("TSP result successfully fetched.")
    return jsonify(serializable_result), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    logging.info(f"Flask server is running on port {port}.")
    app.run(host="0.0.0.0", port=port, debug=True)
