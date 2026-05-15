import Database from "better-sqlite3";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export function createDb(dbPath?: string): Database.Database {
  const resolvedPath = dbPath ?? path.join(__dirname, "..", "eventiq.db");
  const db = new Database(resolvedPath);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  migrate(db);
  return db;
}

function migrate(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS events (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      name       TEXT    NOT NULL,
      date       TEXT    NOT NULL,
      status     TEXT    NOT NULL DEFAULT 'upcoming',
      created_at TEXT    NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS bets (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      event_id   INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
      description TEXT   NOT NULL,
      odds       REAL    NOT NULL,
      stake      REAL    NOT NULL,
      result     TEXT    DEFAULT 'pending',
      payout     REAL,
      created_at TEXT    NOT NULL DEFAULT (datetime('now'))
    );
  `);
}

let _db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (!_db) {
    _db = createDb();
  }
  return _db;
}
