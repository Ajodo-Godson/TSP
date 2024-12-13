let map;
let routeData;
let animationMarker;
let animationPath = [];
let currentPathIndex = 0;
let animationInterval;
let currentBounds;
let segmentBounds = [];

function initMap() {
    map = new google.maps.Map(document.getElementById("map"), {
        zoom: 5,
        center: { lat: 37.7749, lng: -122.4194 } // Default center (San Francisco)
    });

    const backendUrl = "/get_tsp_result";

    fetch(backendUrl)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                document.getElementById("route-names-panel").innerHTML = `<h2>Error: ${data.error}</h2>`;
                return;
            }
            routeData = data;
            displayRouteOnMap(data);
            showRouteNames(data);
            document.getElementById("result").style.display = "block";

            // Add animation controls
            addAnimationControls();
        })
        .catch(error => {
            console.error("Error fetching route data:", error);
            document.getElementById("route-names-panel").innerHTML = `<h2>Error fetching route data.</h2>`;
        });
}

function addAnimationControls() {
    const controlDiv = document.createElement('div');
    controlDiv.className = 'animation-controls';
    controlDiv.innerHTML = `
        <button onclick="startAnimation()" id="startBtn">Start Animation</button>
        <button onclick="stopAnimation()" id="stopBtn" disabled>Stop</button>
        <button onclick="resetAnimation()" id="resetBtn">Reset</button>
    `;
    document.getElementById('map').appendChild(controlDiv);
}

function startAnimation() {
    if (animationInterval) return;

    document.getElementById('startBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;

    if (!animationMarker) {
        animationMarker = new google.maps.Marker({
            map: map,
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 8,
                fillColor: "#FF0000",
                fillOpacity: 1,
                strokeWeight: 2,
                strokeColor: "#FFFFFF"
            }
        });
    }

    // Create animation path if not exists
    if (animationPath.length === 0) {
        const locations = routeData.locations;
        const indices = routeData.route_indices;

        for (let i = 0; i < indices.length - 1; i++) {
            const fromIdx = indices[i];
            const toIdx = indices[i + 1];
            const from = locations[fromIdx];
            const to = locations[toIdx];

            // For flights, use direct path
            const isFlight = (
                (fromIdx === routeData.SFO_airport_idx && toIdx === routeData.BER_airport_idx) ||
                (fromIdx === routeData.BER_airport_idx && toIdx === routeData.SFO_airport_idx)
            );

            if (isFlight) {
                animationPath.push([from, to]);
            } else {
                // For driving segments, interpolate points along the path
                const steps = 50; // Number of interpolation points
                for (let j = 0; j < steps; j++) {
                    const fraction = j / steps;
                    const lat = from.lat + (to.lat - from.lat) * fraction;
                    const lng = from.lng + (to.lng - from.lng) * fraction;
                    animationPath.push([{ lat, lng }, { lat, lng }]);
                }
            }
        }
    }

    currentPathIndex = 0;
    animateMarker();
}

function animateMarker() {
    if (currentPathIndex >= animationPath.length) {
        stopAnimation();
        return;
    }

    const currentPos = animationPath[currentPathIndex][0];
    animationMarker.setPosition(currentPos);
    updateRouteHighlight(currentPathIndex);

    // Calculate current segment
    const segmentIndex = Math.floor(currentPathIndex / 50);

    if (segmentBounds[segmentIndex]) {
        const segment = segmentBounds[segmentIndex];

        // Only update zoom when changing segments
        if (!currentBounds || currentBounds.segmentIndex !== segmentIndex) {
            const padding = segment.isFlight ? 100 : 50;

            map.fitBounds(segment.bounds, {
                padding: {
                    top: padding,
                    right: padding,
                    bottom: padding,
                    left: padding
                },
                duration: 1000
            });

            currentBounds = { segmentIndex };
        }
    }

    currentPathIndex++;
    animationInterval = setTimeout(animateMarker, 100);
}

function updateRouteHighlight(index) {
    const steps = document.querySelectorAll('.route-step');
    steps.forEach(step => step.classList.remove('active'));
    if (steps[Math.floor(index / 50)]) { // Adjust based on interpolation steps
        steps[Math.floor(index / 50)].classList.add('active');
    }
}

function stopAnimation() {
    clearTimeout(animationInterval);
    animationInterval = null;
    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
}

function resetAnimation() {
    stopAnimation();
    currentPathIndex = 0;
    if (animationMarker) {
        const startPos = routeData.locations[routeData.route_indices[0]];
        animationMarker.setPosition(startPos);
    }
}

function calculateDistance(from, to) {
    if (google.maps.geometry && google.maps.geometry.spherical) {
        return google.maps.geometry.spherical.computeDistanceBetween(
            new google.maps.LatLng(from.lat, from.lng),
            new google.maps.LatLng(to.lat, to.lng)
        );
    }
    // Fallback: simple bounding box if geometry library isn't available
    return Math.sqrt(
        Math.pow(from.lat - to.lat, 2) +
        Math.pow(from.lng - to.lng, 2)
    ) * 111000; // Rough conversion to meters
}

function createSegmentBounds(from, to, isFlight) {
    const bounds = new google.maps.LatLngBounds();
    bounds.extend({ lat: from.lat, lng: from.lng });
    bounds.extend({ lat: to.lat, lng: to.lng });

    if (!isFlight) {
        // For local segments, add padding
        const center = {
            lat: (from.lat + to.lat) / 2,
            lng: (from.lng + to.lng) / 2
        };

        // Calculate padding based on distance
        const distance = calculateDistance(from, to);
        const padding = distance * 0.2; // 20% padding

        // Extend bounds with padding
        bounds.extend({
            lat: center.lat + (padding / 111000), // Rough conversion from meters to degrees
            lng: center.lng + (padding / (111000 * Math.cos(center.lat * Math.PI / 180)))
        });
        bounds.extend({
            lat: center.lat - (padding / 111000),
            lng: center.lng - (padding / (111000 * Math.cos(center.lat * Math.PI / 180)))
        });
    }

    return bounds;
}

function displayRouteOnMap(data) {
    const bounds = new google.maps.LatLngBounds();
    const locations = data.locations;
    const routeIndices = data.route_indices;

    // Clear existing segment bounds
    segmentBounds = [];

    // Create segments
    for (let i = 0; i < routeIndices.length - 1; i++) {
        const fromIdx = routeIndices[i];
        const toIdx = routeIndices[i + 1];
        const from = locations[fromIdx];
        const to = locations[toIdx];

        const isFlight = (
            (fromIdx === data.SFO_airport_idx && toIdx === data.BER_airport_idx) ||
            (fromIdx === data.BER_airport_idx && toIdx === data.SFO_airport_idx)
        );

        // Create segment bounds
        const segmentBound = createSegmentBounds(from, to, isFlight);

        segmentBounds.push({
            bounds: segmentBound,
            isFlight: isFlight
        });

        // Create polyline
        new google.maps.Polyline({
            path: [
                { lat: from.lat, lng: from.lng },
                { lat: to.lat, lng: to.lng }
            ],
            geodesic: true,
            strokeColor: isFlight ? '#0000FF' : '#FF0000',
            strokeOpacity: 1.0,
            strokeWeight: 2,
            map: map
        });

        // Create marker
        new google.maps.Marker({
            position: { lat: from.lat, lng: from.lng },
            map: map,
            title: data.route_names[i],
            label: (i + 1).toString()
        });

        bounds.extend({ lat: from.lat, lng: from.lng });
        bounds.extend({ lat: to.lat, lng: to.lng });
    }

    // Add final marker
    const lastIdx = routeIndices[routeIndices.length - 1];
    new google.maps.Marker({
        position: {
            lat: locations[lastIdx].lat,
            lng: locations[lastIdx].lng
        },
        map: map,
        title: data.route_names[routeIndices.length - 1],
        label: routeIndices.length.toString()
    });

    // Initial fit to bounds
    map.fitBounds(bounds, {
        padding: { top: 50, right: 50, bottom: 50, left: 50 }
    });
}

function showRouteNames(data) {
    const panel = document.getElementById("route-names-panel");
    panel.innerHTML = "<h2>Route Sequence:</h2>";

    // Show route sequence
    data.route_names.forEach((name, index) => {
        panel.innerHTML += `
            <p class="route-step" data-index="${index}">
                <strong>Step ${index + 1}:</strong> ${name}
            </p>`;
    });

    // Add directions panel
    panel.innerHTML += `
        <div class="directions-panel">
            <h3>Turn-by-Turn Directions:</h3>
            <div id="directions-list"></div>
        </div>`;

    // Show directions if available
    if (data.directions) {
        const directionsList = document.getElementById("directions-list");
        data.directions.forEach((segment, segmentIndex) => {
            if (segment.steps) {
                directionsList.innerHTML += `
                    <div class="segment-directions">
                        <h4>Segment ${segmentIndex + 1}: ${data.route_names[segmentIndex]} → ${data.route_names[segmentIndex + 1]}</h4>
                        ${segment.steps.map(step => `
                            <div class="direction-step">
                                <p class="instruction">${step.instruction}</p>
                                ${step.distance ? `<p class="distance">Distance: ${step.distance}</p>` : ''}
                                ${step.duration ? `<p class="duration">Duration: ${step.duration}</p>` : ''}
                            </div>
                        `).join('')}
                        <hr class="segment-divider">
                    </div>`;
            } else if (segment.type === 'flight') {
                directionsList.innerHTML += `
                    <div class="segment-directions flight">
                        <h4>Flight Segment ${segmentIndex + 1}</h4>
                        <p>Flight from ${data.route_names[segmentIndex]} to ${data.route_names[segmentIndex + 1]}</p>
                        <p>Duration: ${formatTime(segment.duration_minutes)}</p>
                        <hr class="segment-divider">
                    </div>`;
            }
        });
    }

    const totalMinutes = data.flight_time_total_minutes + data.local_travel_time_minutes;
    panel.innerHTML += `<h3>Total Time: ${formatTime(totalMinutes)}</h3>`;
}

function formatTime(minutes) {
    const days = Math.floor(minutes / 1440);
    const remainderAfterDays = minutes % 1440;
    const hours = Math.floor(remainderAfterDays / 60);
    const mins = Math.floor(remainderAfterDays % 60);

    let timeString = "";
    if (days > 0) timeString += `${days} days, `;
    if (hours > 0) timeString += `${hours} hours, `;
    timeString += `${mins} minutes`;
    return timeString;
}

function zoomToSegment(bounds, duration) {
    map.fitBounds(bounds, {
        padding: { top: 50, right: 50, bottom: 50, left: 50 },
        duration: duration
    });
}

function zoomToFlightSegment(bounds, duration) {
    map.fitBounds(bounds, {
        padding: { top: 100, right: 100, bottom: 100, left: 100 },
        duration: duration
    });
}

window.onload = initMap;