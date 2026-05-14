import React, { useEffect, useState } from "react";
import type { Event, Bet } from "../api";
import { api } from "../api";
import BetForm from "./BetForm";

interface Props {
  event: Event;
  onDelete: (id: number) => void;
}

export default function EventCard({ event, onDelete }: Props) {
  const [bets, setBets] = useState<Bet[]>([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (expanded) {
      api.getBets(event.id).then(setBets).catch(console.error);
    }
  }, [expanded, event.id]);

  const handleAddBet = async (data: {
    event_id: number;
    description: string;
    odds: number;
    stake: number;
  }) => {
    const bet = await api.createBet(data);
    setBets((prev) => [bet, ...prev]);
  };

  const handleSettle = async (betId: number, result: "won" | "lost") => {
    const updated = await api.settleBet(betId, result);
    setBets((prev) => prev.map((b) => (b.id === updated.id ? updated : b)));
  };

  const handleDeleteBet = async (betId: number) => {
    await api.deleteBet(betId);
    setBets((prev) => prev.filter((b) => b.id !== betId));
  };

  const totalStake = bets.reduce((s, b) => s + b.stake, 0);
  const totalPayout = bets.reduce((s, b) => s + (b.payout ?? 0), 0);

  return (
    <div
      style={{
        background: "#1e293b",
        borderRadius: 10,
        padding: 16,
        marginBottom: 12,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h3 style={{ fontSize: "1.1rem" }}>{event.name}</h3>
          <span style={{ color: "#94a3b8", fontSize: "0.85rem" }}>{event.date}</span>
          <span
            style={{
              marginLeft: 8,
              padding: "2px 8px",
              borderRadius: 4,
              fontSize: "0.75rem",
              background: event.status === "upcoming" ? "#312e81" : "#064e3b",
              color: event.status === "upcoming" ? "#a5b4fc" : "#6ee7b7",
            }}
          >
            {event.status}
          </span>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button
            onClick={() => setExpanded(!expanded)}
            style={{ background: "#334155", color: "#e2e8f0", fontSize: "0.8rem" }}
          >
            {expanded ? "Collapse" : "Bets"}
          </button>
          <button
            onClick={() => onDelete(event.id)}
            style={{ background: "#991b1b", color: "#fecaca", fontSize: "0.8rem" }}
          >
            Delete
          </button>
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: 12 }}>
          <BetForm eventId={event.id} onAdd={handleAddBet} />

          {bets.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.8rem",
                  color: "#94a3b8",
                  marginBottom: 4,
                }}
              >
                <span>Total staked: ${totalStake.toFixed(2)}</span>
                <span>Total payout: ${totalPayout.toFixed(2)}</span>
                <span
                  style={{ color: totalPayout - totalStake >= 0 ? "#6ee7b7" : "#fca5a5" }}
                >
                  P/L: ${(totalPayout - totalStake).toFixed(2)}
                </span>
              </div>

              {bets.map((bet) => (
                <div
                  key={bet.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "6px 0",
                    borderTop: "1px solid #334155",
                    fontSize: "0.85rem",
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <span>{bet.description}</span>
                    <span style={{ color: "#94a3b8", marginLeft: 8 }}>
                      @{bet.odds} · ${bet.stake}
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: 4 }}>
                    {bet.result === "pending" ? (
                      <>
                        <button
                          onClick={() => handleSettle(bet.id, "won")}
                          style={{ background: "#065f46", color: "#6ee7b7", fontSize: "0.75rem", padding: "4px 8px" }}
                        >
                          Won
                        </button>
                        <button
                          onClick={() => handleSettle(bet.id, "lost")}
                          style={{ background: "#7f1d1d", color: "#fca5a5", fontSize: "0.75rem", padding: "4px 8px" }}
                        >
                          Lost
                        </button>
                      </>
                    ) : (
                      <span
                        style={{
                          color: bet.result === "won" ? "#6ee7b7" : "#fca5a5",
                          fontWeight: 600,
                          fontSize: "0.8rem",
                        }}
                      >
                        {bet.result === "won" ? `Won $${bet.payout?.toFixed(2)}` : "Lost"}
                      </span>
                    )}
                    <button
                      onClick={() => handleDeleteBet(bet.id)}
                      style={{ background: "transparent", color: "#94a3b8", fontSize: "0.75rem", padding: "4px 6px" }}
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
