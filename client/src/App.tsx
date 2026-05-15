import { useEffect, useState } from "react";
import type { Event } from "./api";
import { api } from "./api";
import EventForm from "./components/EventForm";
import EventCard from "./components/EventCard";

export default function App() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchEvents = async () => {
    try {
      const data = await api.getEvents();
      setEvents(data);
    } catch (err) {
      console.error("Failed to load events", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  const handleAddEvent = async (name: string, date: string) => {
    const event = await api.createEvent({ name, date });
    setEvents((prev) => [event, ...prev]);
  };

  const handleDeleteEvent = async (id: number) => {
    await api.deleteEvent(id);
    setEvents((prev) => prev.filter((e) => e.id !== id));
  };

  return (
    <div style={{ maxWidth: 700, margin: "0 auto", padding: "32px 16px" }}>
      <h1
        style={{
          fontSize: "1.75rem",
          fontWeight: 700,
          marginBottom: 4,
          background: "linear-gradient(135deg, #6366f1, #a78bfa)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
        }}
      >
        EventIQ
      </h1>
      <p style={{ color: "#94a3b8", marginBottom: 24, fontSize: "0.9rem" }}>
        Track your event bets and results
      </p>

      <EventForm onAdd={handleAddEvent} />

      <div style={{ marginTop: 24 }}>
        {loading ? (
          <p style={{ color: "#64748b" }}>Loading…</p>
        ) : events.length === 0 ? (
          <p style={{ color: "#64748b" }}>No events yet. Add one above!</p>
        ) : (
          events.map((event) => (
            <EventCard key={event.id} event={event} onDelete={handleDeleteEvent} />
          ))
        )}
      </div>
    </div>
  );
}
