import React, { useState } from "react";

interface Props {
  eventId: number;
  onAdd: (data: { event_id: number; description: string; odds: number; stake: number }) => void;
}

export default function BetForm({ eventId, onAdd }: Props) {
  const [description, setDescription] = useState("");
  const [odds, setOdds] = useState("");
  const [stake, setStake] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim() || !odds || !stake) return;
    onAdd({
      event_id: eventId,
      description: description.trim(),
      odds: parseFloat(odds),
      stake: parseFloat(stake),
    });
    setDescription("");
    setOdds("");
    setStake("");
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      <input
        placeholder="Bet description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        style={{ flex: 1, minWidth: 140 }}
      />
      <input
        type="number"
        step="0.01"
        placeholder="Odds"
        value={odds}
        onChange={(e) => setOdds(e.target.value)}
        style={{ width: 80 }}
      />
      <input
        type="number"
        step="0.01"
        placeholder="Stake"
        value={stake}
        onChange={(e) => setStake(e.target.value)}
        style={{ width: 80 }}
      />
      <button type="submit" style={{ background: "#10b981", color: "#fff" }}>
        Place Bet
      </button>
    </form>
  );
}
