import React, { useState } from "react";

interface Props {
  onAdd: (name: string, date: string) => void;
}

export default function EventForm({ onAdd }: Props) {
  const [name, setName] = useState("");
  const [date, setDate] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !date) return;
    onAdd(name.trim(), date);
    setName("");
    setDate("");
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      <input
        placeholder="Event name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        style={{ flex: 1, minWidth: 160 }}
      />
      <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      <button
        type="submit"
        style={{ background: "#6366f1", color: "#fff" }}
      >
        Add Event
      </button>
    </form>
  );
}
