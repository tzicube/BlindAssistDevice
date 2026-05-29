const express = require("express");
const fs = require("fs");
const cors = require("cors");

const app = express();

app.use(cors());

// Cho frontend đọc file public
app.use(express.static("public"));

function generateFakeDetection() {
  return {
    x: Math.floor(Math.random() * 400),
    y: Math.floor(Math.random() * 250),
    width: 50,
    height: 120,
    label: "Bottle",
  };
}

// Update data.json liên tục
setInterval(() => {
  const fakeData = generateFakeDetection();

  fs.writeFileSync(
    "./public/data.json",
    JSON.stringify(fakeData, null, 2)
  );

  console.log("Updated data.json");
}, 1000);

app.listen(5000, () => {
  console.log("Server running on port 5000");
});