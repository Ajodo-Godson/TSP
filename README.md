# Traveling Salesman Problem (TSP) Solver

## Overview

This project implements a Traveling Salesman Problem (TSP) solver optimized for a specific route between Berlin, Germany, and San Francisco, CA. The solver uses mathematical optimization to find the most efficient route visiting each location exactly once, with special handling for intercontinental flights between airports.

## Mathematical Formulation

The problem is formulated as an Integer Linear Program (ILP) where:
- Each location is a vertex in a graph $V = \{v_1, \ldots, v_n\}$
- Travel times between locations form the cost matrix $d(i,j)$
- Binary variables $x_{ij}$ indicate if edge $(i,j)$ is used in the solution
- Additional constraints ensure:
  - Each location is visited exactly once
  - Only valid airport connections are used for intercontinental travel
  - Subtours are eliminated using Miller-Tucker-Zemlin constraints

### Objective Function
$$
\text{Minimize} \quad \sum_{i=1}^{n} \sum_{j=1}^{n} d(i,j) \cdot x_{ij}
$$
### Constraints
1. **Degree Constraints:**
   $$
   \sum_{j=1}^{n} x_{ij} = 1 \quad \forall i \in V \quad (\text{Outgoing})
   $$
   
   $$
   \sum_{i=1}^{n} x_{ij} = 1 \quad \forall j \in V \quad (\text{Incoming})
   $$

2. **Miller-Tucker-Zemlin (MTZ) Subtour Elimination:**
   $$
   u_i - u_j + n \cdot x_{ij} \leq n - 1 \quad \forall i, j \in V, \, i \neq j
   $$

3. **Airport Connection Constraints:**
   $$
   x_{ij} = 0 \quad \text{if} \quad i \in \text{Berlin}, \, j \in \text{SF} \quad \text{and} \quad (i,j) \notin \text{Airports}
   $$

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
    ```bash
    git clone https://github.com/yourusername/your-repo.git
    cd your-repo
    ```

2. **Set up the backend**
    ```bash
    cd backend
    python -m venv venv
    source venv/bin/activate  # On Windows use: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3. **Configure Google Maps API**
   - Get a Google Maps API key from the Google Cloud Console
   - Replace the API key in `frontend/index.html` where it says:
     ```html
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
Mandatorily enforcing SFO <-> BER might not be posible as it violates subtour elimination constraints, and the typical nature of Traveling Salesman problem in general.  
So we added a penalty function to the objective function to discourage the solver from using the SFO <-> BER connection at the very worst case. If there's a solution such that SFO <-> BER is used, it will be used, else the penalty function discourages the use of that. 

### Troubleshooting

Common issues:
- If you see a blank map, verify your Google Maps API key is correctly set
- Make sure all required Python packages are installed (check requirements.txt)
- For CORS issues, ensure Flask-CORS is properly installed
- The application requires Python 3.9 or higher

## Jupyter Notebook
The jupyter notebook uses the already generated cost matrix from google maps api, so there is no need to run it with an API key. 
