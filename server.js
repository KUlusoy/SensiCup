const express = require('express');
const app = express();
const port = 5005; // Or any other port you prefer

app.get('/data', (req, res) => {
  // The TDS value is in the query parameters
  const tdsValue = req.query.tds;

  if (tdsValue) {
    console.log(`Received TDS value: ${tdsValue}`);
    // Now you can store this value, e.g., in a variable, file, or database
    // For now, let's just send a response back
    res.send(`TDS value ${tdsValue} received successfully.`);
  } else {
    res.status(400).send("No TDS value provided.");
  }
});

app.listen(port, () => {
  console.log(`Web app listening at http://localhost:${port}`);
});