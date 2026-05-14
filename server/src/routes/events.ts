import { Router, type Request, type Response } from "express";
import type Database from "better-sqlite3";

export function eventsRouter(db: Database.Database): Router {
  const router = Router();

  router.get("/", (_req: Request, res: Response) => {
    const rows = db.prepare("SELECT * FROM events ORDER BY date DESC").all();
    res.json(rows);
  });

  router.get("/:id", (req: Request, res: Response) => {
    const row = db.prepare("SELECT * FROM events WHERE id = ?").get(req.params.id);
    if (!row) {
      res.status(404).json({ error: "Event not found" });
      return;
    }
    res.json(row);
  });

  router.post("/", (req: Request, res: Response) => {
    const { name, date, status } = req.body;
    if (!name || !date) {
      res.status(400).json({ error: "name and date are required" });
      return;
    }
    const result = db.prepare(
      "INSERT INTO events (name, date, status) VALUES (?, ?, ?)"
    ).run(name, date, status ?? "upcoming");
    const event = db.prepare("SELECT * FROM events WHERE id = ?").get(result.lastInsertRowid);
    res.status(201).json(event);
  });

  router.delete("/:id", (req: Request, res: Response) => {
    const changes = db.prepare("DELETE FROM events WHERE id = ?").run(req.params.id).changes;
    if (changes === 0) {
      res.status(404).json({ error: "Event not found" });
      return;
    }
    res.status(204).send();
  });

  return router;
}
