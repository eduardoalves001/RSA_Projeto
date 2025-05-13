const canvas = document.getElementById("road");
const ctx = canvas.getContext("2d");

function drawRoad() {
    // estrada com duas faixas
    ctx.fillStyle = "#555"; // cinzento escuro
    ctx.fillRect(0, 100, canvas.width, 200);

    // linha divisória entre as faixas (tracejada)
    ctx.strokeStyle = "white";
    ctx.setLineDash([20, 15]);
    ctx.beginPath();
    ctx.moveTo(0, 200);
    ctx.lineTo(canvas.width, 200);
    ctx.stroke();
    ctx.setLineDash([]); // reset
}

let ambulanceImg = new Image();
let carImg = new Image();
let crashedImg = new Image();
ambulanceImg.src = "static/ambulance.png";
carImg.src = "static/car.png";
crashedImg.src = "static/crashed.png"

ambulanceImg.onload = function() {
    console.log("Ambulance image loaded");
};
carImg.onload = function() {
    console.log("Car image is loaded");
}
crashedImg.onload = function(){
    console.log("Crashed car image is loaded");
}

function drawVehicle(x, y, type, state) {
    if (state === "crashed") {
        if (crashedImg.complete) {
            ctx.drawImage(crashedImg, x, y, 50, 60);
        }else{
            console.log("Crashed car image is not yet loaded");
        }
    } else if (type === "ambulance") {
        // Only draw the image once it's loaded
        if (ambulanceImg.complete) {
            ctx.drawImage(ambulanceImg, x, y, 50, 60); 
        } else {
            console.log("Ambulance image is not yet loaded");
        }
    } else {
        // Only draw the image once it's loaded
        if (carImg.complete) {
            ctx.drawImage(carImg, x, y, 40, 60); 
        } else {
            console.log("Car image is not yet loaded");
        }
    }
}

function updateCanvas(vehicles) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawRoad();
    vehicles.forEach(v => drawVehicle(v.x, v.y, v.type, v.state));
}

function fetchAndDraw() {
    fetch("/state")
        .then(response => response.json())
        .then(data => updateCanvas(data))
        .catch(error => console.error('Error fetching vehicle state:', error));
}

// Update the canvas every 50ms
setInterval(fetchAndDraw, 50);
