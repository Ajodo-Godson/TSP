# Traveling Salesman Problem (TSP) Solver

## Overview

This project implements a Traveling Salesman Problem (TSP) solver optimized for a specific route between Berlin, Germany, and San Francisco, CA. The solver uses mathematical optimization to find the most efficient route visiting each location exactly once, with special handling for intercontinental flights between airports.

## Mathematical Formulation

The problem is formulated as an Integer Linear Program (ILP) where:
- Each location is a vertex in a graph V = {v₁, ..., vₙ}
- Travel times between locations form the cost matrix d(i,j)
- Binary variables xᵢⱼ indicate if edge (i,j) is used in the solution
- Additional constraints ensure:
  - Each location is visited exactly once
  - Only valid airport connections are used for intercontinental travel
  - Subtours are eliminated using Miller-Tucker-Zemlin constraints

## Features

- Optimized route calculation between multiple locations in Berlin and San Francisco
- Google Maps API integration for accurate travel distances
- Special handling of airport connections (SFO ↔ BER)
- Penalty system for specific route constraints
- Interactive visualization of the optimal route
- Styled output in Jupyter Notebook format

## Prerequisites

- Python 3.9+
- Virtual Environment (recommended)
- Google Maps API key (for cost matrix generation)

## Installation

1. **Clone the repository**

2. **Set up the backend**   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   pip install -r requirements.txt   ```

3. **Configure Google Maps API**
   - Get a Google Maps API key from the Google Cloud Console
   - Replace the API key in `frontend/index.html` where it says:     
   ```
     <script src="https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY"></script>    
    ```

## Running Locally

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
The backend will start on `http://localhost:5001` (note: port 5001 is specified in app.py)

### Frontend
The frontend is served directly by Flask, so no separate server is needed. Simply:
1. Open your browser
2. Navigate to `http://localhost:5001`

### Features Available
- Interactive map visualization
- Route animation controls (Start, Stop, Reset)
- Turn-by-turn directions
- Special handling of flight segments between airports
- Total journey time calculation

### Notes on the Penalty function
Mandatorily enforcing SFO <-> BER might not be posible as it violates subtour elimination constraints. 
So we added a penalty function to the objective function to discourage the solver from using the SFO <-> BER connection at the very worst case. If there's a solution such that SFO <-> BER is used, it will be used, else the penalty function discourages the use of that. 

### Troubleshooting

Common issues:
- If you see a blank map, verify your Google Maps API key is correctly set
- Make sure all required Python packages are installed (check requirements.txt)
- For CORS issues, ensure Flask-CORS is properly installed
- The application requires Python 3.9 or higher

## Jupyter Notebook
The jupyter notebook uses the already generated cost matrix from google maps api, so there is no need to run it with an API key. 
