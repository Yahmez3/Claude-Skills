"use client";

import { useState } from "react";

export default function WaitlistForm() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "ok" | "err">("idle");
  const [msg, setMsg] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.includes("@")) return;
    setStatus("loading");
    try {
      const r = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!r.ok) throw new Error(await r.text());
      setStatus("ok");
      setMsg("You're in. Check your email for a confirmation.");
      setEmail("");
    } catch (err: any) {
      setStatus("err");
      setMsg(err?.message || "Something went wrong.");
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col sm:flex-row gap-2 max-w-md mx-auto">
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@example.com"
        className="flex-1 px-4 py-3 rounded border border-neutral-300 focus:outline-none focus:border-neutral-900"
        required
      />
      <button
        type="submit"
        disabled={status === "loading"}
        className="px-6 py-3 rounded bg-neutral-900 text-white font-medium disabled:opacity-50"
      >
        {status === "loading" ? "..." : "Join waitlist"}
      </button>
      {msg && (
        <p className={status === "ok" ? "text-green-600 text-sm" : "text-red-600 text-sm"}>
          {msg}
        </p>
      )}
    </form>
  );
}
