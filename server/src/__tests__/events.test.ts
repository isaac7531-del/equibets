import { describe, it, expect, beforeEach, afterEach } from "vitest";
import Database from "better-sqlite3";
import { createDb } from "../db.js";
import { eventsRouter } from "../routes/events.js";
import express from "express";
import type { Server } from "node:http";

function buildApp(db: Database.Database) {
  const app = express();
  app.use(express.json());
  app.use("/api/events", eventsRouter(db));
  return app;
}

describe("Events API", () => {
  let db: Database.Database;
  let server: Server;
  let baseUrl: string;

  beforeEach(async () => {
    db = createDb(":memory:");
    const app = buildApp(db);
    await new Promise<void>((resolve) => {
      server = app.listen(0, () => {
        const addr = server.address();
        if (addr && typeof addr === "object") {
          baseUrl = `http://localhost:${addr.port}`;
        }
        resolve();
      });
    });
  });

  afterEach(() => {
    server?.close();
    db?.close();
  });

  it("returns empty array initially", async () => {
    const res = await fetch(`${baseUrl}/api/events`);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual([]);
  });

  it("creates and retrieves an event", async () => {
    const create = await fetch(`${baseUrl}/api/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Test Race", date: "2026-06-01" }),
    });
    expect(create.status).toBe(201);
    const event = await create.json();
    expect(event.name).toBe("Test Race");
    expect(event.date).toBe("2026-06-01");
    expect(event.status).toBe("upcoming");

    const get = await fetch(`${baseUrl}/api/events/${event.id}`);
    expect(get.status).toBe(200);
    const fetched = await get.json();
    expect(fetched.id).toBe(event.id);
  });

  it("deletes an event", async () => {
    const create = await fetch(`${baseUrl}/api/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "To Delete", date: "2026-07-01" }),
    });
    const event = await create.json();

    const del = await fetch(`${baseUrl}/api/events/${event.id}`, { method: "DELETE" });
    expect(del.status).toBe(204);

    const get = await fetch(`${baseUrl}/api/events/${event.id}`);
    expect(get.status).toBe(404);
  });

  it("rejects event without name", async () => {
    const res = await fetch(`${baseUrl}/api/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: "2026-06-01" }),
    });
    expect(res.status).toBe(400);
  });
});
