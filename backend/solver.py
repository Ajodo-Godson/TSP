import math
import cvxpy as cp
import numpy as np
import googlemaps
import time
import os
import dotenv
import networkx as nx
from bs4 import BeautifulSoup  # For parsing HTML instructions
from functools import lru_cache
import logging

# ----------------- Initialization -----------------


def initialize_api():
    dotenv.load_dotenv()
    API_KEY = os.getenv("GOOGLE_API_KEY")

    if not API_KEY:
        raise ValueError(
            "Google API Key not found. Please set the 'GOOGLE_API_KEY' environment variable."
        )

    logging.info("Google API Key successfully retrieved.")
    logging.info("Installed CVXPy Solvers:", cp.installed_solvers())
    gmaps = googlemaps.Client(key=API_KEY)

    return gmaps


# ----------------- Data Definition -----------------


def define_locations():
    locations = [
        "Berlin Residence, Berlin, Germany",  # 0: Berlin Residence (Start/End)
        # San Francisco (1-6)
        "Pier 39, San Francisco, CA",  # 1: Pier 39
        "Salesforce Park, San Francisco, CA",  # 2: Salesforce Park
        "Bob's Doughnuts, San Francisco, CA",  # 3: Bob's Doughnuts
        "851 California St, San Francisco, CA",  # 4: Intersection near 851 California St
        "Union Square, San Francisco, CA",  # 5: Union Square
        "San Francisco International Airport (SFO)",  # 6: San Francisco International Airport (SFO)
        # Berlin (7-12)
        "Berlin TV Tower, Berlin, Germany",  # 7: Berlin TV Tower
        "Berlin Zoological Garden, Berlin, Germany",  # 8: Berlin Zoological Garden
        "Tempelhofer Feld, Berlin, Germany",  # 9: Tempelhofer Feld
        "East Side Gallery, Berlin, Germany",  # 10: East Side Gallery
        "Berlin Brandenburg Airport (BER)",  # 11: Berlin Brandenburg Airport (BER)
    ]
    return locations


def define_parameters(locations):
    N = len(locations)
    BER_residence = 0  # Berlin residence index
    SFO_airport = 6  # San Francisco International Airport (SFO)
    BER_airport = 11  # Berlin Brandenburg Airport (BER)
    flight_time = 660  # Approx. 11 hours in minutes
    flight_time_return = 660  # Approx. 11 hours in minutes (assuming same duration)

    return N, BER_residence, SFO_airport, BER_airport, flight_time, flight_time_return


# ----------------- Utility Functions -----------------


def get_directions(gmaps, origin, destination, mode="driving"):
    try:
        result = gmaps.directions(origin, destination, mode=mode, units="metric")
        if result:
            return result[0]["legs"][0]["steps"]
        else:
            print(f"Directions API returned no results for {origin} to {destination}")
            return None
    except Exception as e:
        print(f"Exception during Directions API call: {e}")
        return None


def get_driving_time(gmaps, origin, destination):
    try:
        result = gmaps.distance_matrix(
            origins=[origin], destinations=[destination], mode="driving", units="metric"
        )
        element = result["rows"][0]["elements"][0]
        if element["status"] == "OK":
            duration = element["duration"]["value"]  # in seconds
            return duration / 60  # Convert to minutes
        else:
            print(
                f"Distance matrix API error between {origin} and {destination}: {element['status']}"
            )
            return 1e6  # Assign high cost if API fails
    except Exception as e:
        print(f"Exception during API call: {e}")
        return 1e6  # Assign high cost if exception occurs


def get_location_coordinates(gmaps, location):
    """
    Fetches the geographical coordinates (latitude and longitude) for a given location using Google Maps Geocoding API.

    Args:
        gmaps (googlemaps.Client): The Google Maps client initialized with an API key.
        location (str): The address or place name to geocode.

    Returns:
        dict: A dictionary containing 'lat' and 'lng' keys with their respective float values.
    """
    try:
        geocode_result = gmaps.geocode(location)
        if not geocode_result:
            print(f"No geocode results found for location: {location}")
            return {"lat": 0.0, "lng": 0.0}

        # Taking the first result from the geocoding response
        geometry = geocode_result[0].get("geometry", {})
        location_dict = geometry.get("location", {})
        lat = location_dict.get("lat", 0.0)
        lng = location_dict.get("lng", 0.0)

        return {"lat": lat, "lng": lng}

    except Exception as e:
        print(f"Error fetching coordinates for '{location}': {e}")
        return {"lat": 0.0, "lng": 0.0}


@lru_cache(maxsize=None)
def get_location_coordinates_cached(gmaps, location):
    return get_location_coordinates(gmaps, location)


# ----------------- Cost Matrix Construction -----------------


def initialize_cost_matrix(N):
    return np.full((N, N), 1e6)  # Initialize with high cost (1,000,000 minutes)


def populate_cost_matrix(
    C, locations, N, gmaps, BER_residence, SFO_airport, BER_airport, flight_time
):
    for i in range(N):
        for j in range(N):
            if i == j:
                C[i][j] = 1e6
            else:
                if (i < 6 and j < 6) or (i >= 6 and j >= 6):
                    driving_time = get_driving_time(gmaps, locations[i], locations[j])
                    C[i][j] = driving_time
                    print(
                        f"Driving time from {locations[i]} to {locations[j]}: {driving_time} minutes"
                    )
                elif (i == BER_residence and j >= 6) or (i >= 6 and j == BER_residence):
                    C[i][j] = 10000  # High cost for intercontinental travel
                    print(
                        f"Setting high cost for intercontinental travel from {locations[i]} to {locations[j]}: 10000 minutes"
                    )
                elif (i == SFO_airport and j == BER_airport) or (
                    i == BER_airport and j == SFO_airport
                ):
                    C[i][j] = flight_time
                    print(
                        f"Setting flight time between {locations[i]} and {locations[j]}: {flight_time} minutes"
                    )
                else:
                    C[i][j] = 10000  # High cost for intercontinental travel
                    print(
                        f"Setting high cost for intercontinental travel from {locations[i]} to {locations[j]}: 10000 minutes"
                    )
    return C


def verify_cost_matrix(C, BER_airport, SFO_airport):
    print("\n--- Cost Matrix Verification ---")
    print(f"C[{BER_airport}][{SFO_airport}] = {C[BER_airport][SFO_airport]}")
    print(f"C[{SFO_airport}][{BER_airport}] = {C[SFO_airport][BER_airport]}")
    print("--- End of Verification ---\n")


# ----------------- Optimization Model -----------------


def define_tsp_model(C, N, sf_nodes, berlin_nodes, locations):
    # Define TSP Variables
    X = cp.Variable((N, N), boolean=True)
    U = cp.Variable(N, integer=True)

    # Initialize penalty matrix
    penalty_matrix = np.zeros((N, N))
    penalty_weight = 1e4

    # Add penalties for undesired connections
    for i in range(N):
        for j in range(N):
            if i in sf_nodes and j in berlin_nodes:
                penalty_matrix[i, j] = penalty_weight
                print(
                    f"Adding penalty for connecting {locations[i]} to {locations[j]}: {penalty_weight}"
                )
            if i in berlin_nodes and j in sf_nodes:
                penalty_matrix[i, j] = penalty_weight
                print(
                    f"Adding penalty for connecting {locations[i]} to {locations[j]}: {penalty_weight}"
                )

    # Combined Objective
    objective = cp.Minimize(cp.sum(cp.multiply(C + penalty_matrix, X)))

    return X, U, objective


def define_constraints(X, U, N):
    constraints = []

    # Each city must be entered exactly once
    for i in range(N):
        constraints.append(cp.sum(X[:, i]) == 1)
        constraints.append(cp.sum(X[i, :]) == 1)

    # Subtour elimination constraints (MTZ formulation)
    for i in range(1, N):
        constraints.append(U[i] >= 1)
        constraints.append(U[i] <= N - 1)
        for j in range(1, N):
            if i != j:
                constraints.append(U[i] - U[j] + (N) * X[i, j] <= N - 1)

    return constraints


def solve_tsp_problem(objective, constraints):
    prob = cp.Problem(objective, constraints)
    prob.solve(solver=cp.GLPK_MI, verbose=True, max_iters=10000)
    return prob


# ----------------- Route Reconstruction -----------------


def reconstruct_route(
    prob, X, locations, gmaps, N, BER_residence, BER_airport, SFO_airport, C
):
    print("Status:", prob.status)
    if prob.status == cp.OPTIMAL:
        print("Solution found:")
        print("Route:")
        X_val = X.value
        if X_val is None:
            print("No solution found.")
        else:
            route = [BER_residence]
            current_node = BER_residence
            visited = set(route)

            while len(route) < N:
                next_nodes = np.where(X_val[current_node] > 0.5)[0]
                if len(next_nodes) == 0:
                    print(f"Error: No outgoing edge from node {current_node}.")
                    break
                next_node = next_nodes[0]
                if next_node in visited:
                    print(f"Error: Detected a loop at node {next_node}.")
                    break
                route.append(next_node)
                visited.add(next_node)
                current_node = next_node

            # Ensure the route returns to Berlin Residence
            if X_val[current_node][BER_residence] > 0.5:
                route.append(BER_residence)
            else:
                print("Error: Route does not return to the starting point.")

            print("\n--- Reconstructed Route ---")
            for idx, node in enumerate(route):
                print(f"Step {idx}: {locations[node]} (Index {node})")
            print("--- End of Route ---\n")

        optimal_travel_time = prob.value  # Get the optimal travel time from the solver
        print(
            "Optimal Value (Total Travel Time in minutes from Solver):",
            optimal_travel_time,
        )

        print("\n--------------------------------------------------")
        print("Detailed Route and Directions:")
        print("--------------------------------------------------\n")

        directions_list = []
        total_travel_time = 0
        local_travel_time = 0
        flight_time_total = 0

        for i in range(len(route) - 1):
            current_idx = route[i]
            next_idx = route[i + 1]

            # Check if this is a flight segment
            is_flight = (current_idx == SFO_airport and next_idx == BER_airport) or (
                current_idx == BER_airport and next_idx == SFO_airport
            )

            if is_flight:
                # Handle flight segment
                flight_duration = C[current_idx][next_idx]
                flight_time_total += flight_duration
                total_travel_time += flight_duration

                directions_list.append(
                    {
                        "type": "flight",
                        "duration_minutes": flight_duration,
                        "from_location": locations[current_idx],
                        "to_location": locations[next_idx],
                    }
                )
            else:
                # Handle driving segment
                directions = get_directions(
                    gmaps, locations[current_idx], locations[next_idx]
                )

                if directions:
                    segment_duration = 0
                    steps = []

                    for step in directions:
                        soup = BeautifulSoup(step["html_instructions"], "html.parser")
                        instruction = soup.get_text()

                        step_info = {"instruction": instruction}

                        if "distance" in step:
                            step_info["distance"] = step["distance"]["text"]
                        if "duration" in step:
                            duration_value = (
                                step["duration"]["value"] / 60
                            )  # Convert to minutes
                            step_info["duration"] = step["duration"]["text"]
                            segment_duration += duration_value

                        steps.append(step_info)

                    directions_list.append(
                        {
                            "type": "driving",
                            "steps": steps,
                            "duration_minutes": segment_duration,
                        }
                    )

                    local_travel_time += segment_duration
                    total_travel_time += segment_duration
                else:
                    # Use estimated time if directions not available
                    estimated_time = 30
                    directions_list.append(
                        {
                            "type": "driving",
                            "steps": [
                                {
                                    "instruction": "Navigate to destination",
                                    "duration": "~11 hours",
                                }
                            ],
                            "duration_minutes": estimated_time,
                        }
                    )
                    local_travel_time += estimated_time
                    total_travel_time += estimated_time

        tsp_result = {
            "route_names": [locations[idx] for idx in route],
            "route_indices": route,
            "total_travel_time_minutes": total_travel_time,
            "local_travel_time_minutes": local_travel_time,
            "flight_time_total_minutes": flight_time_total,
            "locations": [
                get_location_coordinates(gmaps, locations[idx]) for idx in route
            ],
            "SFO_airport_idx": SFO_airport,
            "BER_airport_idx": BER_airport,
            "directions": directions_list,  # Add directions to the response
        }
    else:
        tsp_result = {"error": "No solution found."}

    return tsp_result


# ----------------- Solve TSP Function -----------------


def solve_tsp():
    try:
        # Initialization
        gmaps = initialize_api()

        # Data Definition
        locations = define_locations()
        N, BER_residence, SFO_airport, BER_airport, flight_time, flight_time_return = (
            define_parameters(locations)
        )

        # Cost Matrix Construction
        C = initialize_cost_matrix(N)
        C = populate_cost_matrix(
            C, locations, N, gmaps, BER_residence, SFO_airport, BER_airport, flight_time
        )
        verify_cost_matrix(C, BER_airport, SFO_airport)

        # Define city groups
        sf_nodes = list(range(1, 6))  # SF locations excluding airport
        berlin_nodes = list(range(7, 11))  # Berlin locations excluding airport

        # Optimization Model
        X, U, objective = define_tsp_model(C, N, sf_nodes, berlin_nodes, locations)
        constraints = define_constraints(X, U, N)
        prob = solve_tsp_problem(objective, constraints)

        # Route Reconstruction
        tsp_result = reconstruct_route(
            prob, X, locations, gmaps, N, BER_residence, BER_airport, SFO_airport, C
        )

        return tsp_result

    except Exception as e:
        logging.error(f"Error in solve_tsp: {e}")
        return {"error": "TSP solver failed due to an exception."}
