import { NextResponse } from "next/server";

/**
 * Waitlist endpoint. Swap the storage call for whichever provider you use:
 * - Resend audiences
 * - Loops
 * - ConvertKit
 * - Postgres + your own sender
 */
export async function POST(req: Request) {
  const { email } = (await req.json()) as { email?: string };
  if (!email || !email.includes("@")) {
    return NextResponse.json({ error: "invalid email" }, { status: 400 });
  }

  const apiKey = process.env.RESEND_API_KEY;
  const audienceId = process.env.RESEND_AUDIENCE_ID;
  if (!apiKey || !audienceId) {
    console.log("[waitlist] (dev) would add:", email);
    return NextResponse.json({ ok: true, dev: true });
  }

  const r = await fetch(`https://api.resend.com/audiences/${audienceId}/contacts`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, unsubscribed: false }),
  });
  if (!r.ok) {
    return NextResponse.json({ error: await r.text() }, { status: 500 });
  }
  return NextResponse.json({ ok: true });
}
