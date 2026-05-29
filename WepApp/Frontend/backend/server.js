import express from "express";
import cors from "cors";
import fs from "fs";

const app = express();

app.use(cors());

app.use(express.json());

// SAVE JSON
app.post(
  "/save-house",
  (req, res) => {
    fs.writeFileSync(
      "./backend/house.json",
      JSON.stringify(
        req.body,
        null,
        2
      )
    );

    res.json({
      success: true,
    });
  }
);

// LOAD JSON
app.get(
  "/load-house",
  (req, res) => {
    const data =
      fs.readFileSync(
        "./backend/house.json",
        "utf-8"
      );

    res.send(data);
  }
);

app.listen(3000, () => {
  console.log("Backend running on port 3000");
});