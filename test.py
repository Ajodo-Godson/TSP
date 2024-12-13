import os
import requests
import numpy as np
import cvxpy as cp


# Google Maps API Configuration
class GoogleMapsDistanceCalculator:
    def __init__(self, api_key):
        """
        Initialize Google Maps Distance Calculator

        Args:
        - api_key: Google Maps API key
        """
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"

    def calculate_distance_matrix(self, locations, location_names):
        """
        Calculate distance matrix using Google Maps Distance Matrix API

        Args:
        - locations: List of (lat, lon) tuples
        - location_names: Corresponding location names

        Returns:
        - Distance matrix (travel times in minutes)
        - Travel mode matrix
        """
        N = len(locations)
        distance_matrix = np.full((N, N), 1e6)
        mode_matrix = np.full((N, N), "unknown")

        # Break into smaller batches to avoid API limits
        for i in range(N):
            for j in range(N):
                if i == j:
                    distance_matrix[i][j] = 1e6  # No self-loops
                    continue

                # Prepare API request
                params = {
                    "origins": f"{locations[i][0]},{locations[i][1]}",
                    "destinations": f"{locations[j][0]},{locations[j][1]}",
                    "key": self.api_key,
                    # Prefer driving, but allow alternatives
                    "mode": "driving",  # Options: driving, walking, transit, bicycling
                }

                try:
                    response = requests.get(self.base_url, params=params).json()

                    # Check API response
                    if (
                        response.get("rows")
                        and response["rows"][0].get("elements")
                        and response["rows"][0]["elements"][0].get("duration")
                    ):

                        # Extract duration in minutes
                        duration = (
                            response["rows"][0]["elements"][0]["duration"]["value"] / 60
                        )
                        distance_matrix[i][j] = duration

                        # Determine travel mode
                        if (i in range(5) and j in range(5)) or (
                            i in range(6, 11) and j in range(6, 11)
                        ):
                            mode_matrix[i][j] = "local"
                        elif (i == 5 and j == 11) or (i == 11 and j == 5):
                            mode_matrix[i][j] = "flight"
                        else:
                            mode_matrix[i][j] = "inter_city"

                except Exception as e:
                    print(
                        f"API error for route {location_names[i]} to {location_names[j]}: {e}"
                    )
                    # Fallback to a default high cost
                    distance_matrix[i][j] = 1e6

        return distance_matrix, mode_matrix


# Locations (same as previous example)
locations = [
    # San Francisco (0-4)
    (37.8108768154404, -122.41130158223476),  # 0: Pier 39
    (37.789781803374005, -122.39614415790999),  # 1: Salesforce Park
    (37.791910785363335, -122.42112580112462),  # 2: Bob's Doughnuts
    (37.79205309076259, -122.4091846423365),  # 3: Intersection near 851 California St
    (37.78809178222717, -122.40754012934133),  # 4: Union Square
    (37.6213, -122.3790),  # 5: San Francisco International Airport (SFO)
    # Berlin (6-10)
    (52.535762026660855, 13.417079485888127),  # 6: Berlin TV Tower
    (52.50793475414388, 13.339576629881693),  # 7: Berlin Zoological Garden
    (52.47900985886714, 13.3999477871695),  # 8: Tempelhofer Feld
    (52.50517912120416, 13.439738005163983),  # 9: East Side Gallery
    (52.509289197179555, 13.424068847090055),  # 10: Berlin Residence
    (52.3667, 13.5033),  # 11: Berlin Brandenburg Airport (BER)
]

# Location Names
location_names = [
    "Pier 39 (SF)",
    "Salesforce Park (SF)",
    "Bob's Doughnuts (SF)",
    "851 California St Intersection (SF)",
    "Union Square (SF)",
    "San Francisco International Airport (SFO)",
    "Berlin TV Tower (Berlin)",
    "Berlin Zoological Garden (Berlin)",
    "Tempelhofer Feld (Berlin)",
    "East Side Gallery (Berlin)",
    "Berlin Residence (Berlin)",
    "Berlin Brandenburg Airport (BER)",
]


def main():
    # IMPORTANT: Replace with your actual Google Maps API key
    API_KEY = os.environ.get(
        "GOOGLE_API_KEY", "AIzaSyBuG6RzWnxhae6O8Iu_A_fuw5N3Gqite4I"
    )

    # Calculate distance matrix
    distance_calculator = GoogleMapsDistanceCalculator(API_KEY)
    C, mode_matrix = distance_calculator.calculate_distance_matrix(
        locations, location_names
    )

    N = len(locations)
    SFO_airport = 5  # San Francisco International Airport
    BER_airport = 11  # Berlin Brandenburg Airport

    # Optimization Setup
    X = cp.Variable((N, N), boolean=True)  # Edge variables
    U = cp.Variable(N, integer=True)  # MTZ variables for subtour elimination

    # Objective Function
    objective = cp.Minimize(cp.sum(cp.multiply(C, X)))

    # Constraints
    constraints = []

    # Soft constraint: Visit all San Francisco locations before SFO
    sf_indices = list(range(5))  # 0-4 are SF locations
    for sf_loc in sf_indices:
        constraints.append(cp.sum(X[sf_loc, SFO_airport]) <= 1)

    # Soft constraint: Visit all Berlin locations before BER
    berlin_indices = list(range(6, 11))  # 6-10 are Berlin locations
    for berlin_loc in berlin_indices:
        constraints.append(cp.sum(X[berlin_loc, BER_airport]) <= 1)

    # Degree Constraints
    for i in range(N):
        if i == 0:  # Start at first SF location
            constraints.append(cp.sum(X[i, :]) == 1)
            constraints.append(cp.sum(X[:, i]) == 0)
        elif i == BER_airport:  # End at BER airport
            constraints.append(cp.sum(X[i, :]) == 0)
            constraints.append(cp.sum(X[:, i]) == 1)
        else:
            constraints.append(cp.sum(X[i, :]) == 1)
            constraints.append(cp.sum(X[:, i]) == 1)

    # Flight Constraint
    constraints.append(X[SFO_airport, BER_airport] == 1)

    # No Self-Loops
    for i in range(N):
        constraints.append(X[i, i] == 0)

    # MTZ Subtour Elimination Constraints
    constraints.append(U[0] == 0)  # Start node has U = 0
    for i in range(1, N):
        constraints.append(U[i] >= 1)
        constraints.append(U[i] <= N - 1)

    for i in range(N):
        for j in range(N):
            if i != j and j != 0:
                constraints.append(U[j] >= U[i] + 1 - (N) * (1 - X[i, j]))

    # Solve the Problem
    prob = cp.Problem(objective, constraints)

    try:
        prob.solve(solver=cp.CBC, verbose=True)

        print("Status:", prob.status)
        if prob.status not in ["infeasible", "unbounded"]:
            print("Optimal Travel Time (minutes):", prob.value)

            # Retrieve Route
            X_val = X.value
            if X_val is not None:
                route = []
                current = 0  # Start at Pier 39
                route.append(current)
                visited = set([current])

                while True:
                    # Find next destination
                    next_dest = np.argmax(X_val[current, :])
                    if X_val[current, next_dest] < 0.5:
                        print("No valid route found.")
                        break

                    route.append(next_dest)
                    current = next_dest

                    if current == BER_airport:
                        break

                    if current in visited:
                        print("Cycle detected. Terminating.")
                        break

                    visited.add(current)

                # Print Route Details
                print("\nOptimal Route:")
                for i, idx in enumerate(route, 1):
                    print(f"{i}. {location_names[idx]}")

                # Print Travel Modes
                print("\nTravel Modes:")
                for i in range(len(route) - 1):
                    start = route[i]
                    end = route[i + 1]
                    print(
                        f"{location_names[start]} -> {location_names[end]}: {mode_matrix[start][end]}"
                    )
            else:
                print("No solution found.")
    except Exception as e:
        print(f"Optimization error: {e}")


if __name__ == "__main__":
    main()
