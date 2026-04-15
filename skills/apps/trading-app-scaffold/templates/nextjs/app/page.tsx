import Link from "next/link";

export default function Home() {
  return (
    <main className="max-w-4xl mx-auto p-8">
      <h1 className="text-4xl font-bold mb-4">Trading Dashboard</h1>
      <p className="text-neutral-400 mb-8">
        Personal dashboard scaffold. Extend pages under <code>app/</code>.
      </p>
      <ul className="space-y-2">
        <li>
          <Link className="text-blue-400 hover:underline" href="/dashboard">
            /dashboard
          </Link>
          — watchlist, positions, live chart
        </li>
      </ul>
    </main>
  );
}
