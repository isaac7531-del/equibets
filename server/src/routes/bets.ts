import { Router, type Request, type Response } from "express";
import type Database from "better-sqlite3";

export function betsRouter(db: Database.Database): Router {
  const router = Router();

  router.get("/", (req: Request, res: Response) => {
    const eventId = req.query.event_id;
    if (eventId) {
      const rows = db
        .prepare("SELECT * FROM bets WHERE event_id = ? ORDER BY created_at DESC")
        .all(eventId);
      res.json(rows);
    } else {
      const rows = db.prepare("SELECT * FROM bets ORDER BY created_at DESC").all();
      res.json(rows);
    }
  });

  router.post("/", (req: Request, res: Response) => {
    const { event_id, description, odds, stake } = req.body;
    if (!event_id || !description || odds == null || stake == null) {
      res.status(400).json({ error: "event_id, description, odds, and stake are required" });
      return;
    }
    const event = db.prepare("SELECT id FROM events WHERE id = ?").get(event_id);
    if (!event) {
      res.status(404).json({ error: "Event not found" });
      return;
    }
    const result = db.prepare(
      "INSERT INTO bets (event_id, description, odds, stake) VALUES (?, ?, ?, ?)"
    ).run(event_id, description, odds, stake);
    const bet = db.prepare("SELECT * FROM bets WHERE id = ?").get(result.lastInsertRowid);
    res.status(201).json(bet);
  });

  router.patch("/:id/settle", (req: Request, res: Response) => {
    const { result } = req.body;
    if (!result || !["won", "lost"].includes(result)) {
      res.status(400).json({ error: "result must be 'won' or 'lost'" });
      return;
    }
    const bet = db.prepare("SELECT * FROM bets WHERE id = ?").get(req.params.id) as
      | { id: number; odds: number; stake: number }
      | undefined;
    if (!bet) {
      res.status(404).json({ error: "Bet not found" });
      return;
    }
    const payout = result === "won" ? bet.odds * bet.stake : 0;
    db.prepare("UPDATE bets SET result = ?, payout = ? WHERE id = ?").run(result, payout, bet.id);
    const updated = db.prepare("SELECT * FROM bets WHERE id = ?").get(bet.id);
    res.json(updated);
  });

  router.delete("/:id", (req: Request, res: Response) => {
    const changes = db.prepare("DELETE FROM bets WHERE id = ?").run(req.params.id).changes;
    if (changes === 0) {
      res.status(404).json({ error: "Bet not found" });
      return;
    }
    res.status(204).send();
  });

  return router;
}
