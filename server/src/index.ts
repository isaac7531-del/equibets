import express from "express";
import cors from "cors";
import { getDb } from "./db.js";
import { eventsRouter } from "./routes/events.js";
import { betsRouter } from "./routes/bets.js";

const app = express();
const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3001;

app.use(cors());
app.use(express.json());

const db = getDb();

app.use("/api/events", eventsRouter(db));
app.use("/api/bets", betsRouter(db));

app.get("/api/health", (_req, res) => {
  res.json({ status: "ok" });
});

app.listen(PORT, () => {
  console.log(`EventIQ API running on http://localhost:${PORT}`);
});

export default app;
