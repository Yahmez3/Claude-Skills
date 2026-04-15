import WaitlistForm from "./WaitlistForm";

const features = [
  { title: "Feature one", body: "What it does for the user in one sentence." },
  { title: "Feature two", body: "Benefit-led copy. No jargon." },
  { title: "Feature three", body: "Point at the gap vs the alternative." },
];

export default function Home() {
  return (
    <main className="max-w-5xl mx-auto px-6 py-16">
      {/* Hero */}
      <section className="text-center space-y-6 py-16">
        <h1 className="text-5xl sm:text-6xl font-bold tracking-tight">
          One-sentence headline.
          <br />
          <span className="text-neutral-500">Second line sharpens who it's for.</span>
        </h1>
        <p className="text-xl text-neutral-600 max-w-2xl mx-auto">
          Subhead: expand the value prop. Keep under 20 words.
        </p>
        <WaitlistForm />
        <p className="text-sm text-neutral-400">
          iOS, Android, web. Launching Q{`{quarter}`}. No spam, one email on launch day.
        </p>
      </section>

      {/* Social proof */}
      <section className="py-12 border-t border-neutral-200">
        <p className="text-center text-sm uppercase tracking-widest text-neutral-500 mb-6">
          As seen in
        </p>
        <div className="flex flex-wrap justify-center gap-10 opacity-60">
          <span>Outlet 1</span>
          <span>Outlet 2</span>
          <span>Outlet 3</span>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 grid gap-12 sm:grid-cols-3">
        {features.map((f) => (
          <div key={f.title} className="space-y-2">
            <h3 className="text-xl font-semibold">{f.title}</h3>
            <p className="text-neutral-600">{f.body}</p>
          </div>
        ))}
      </section>

      {/* Final CTA */}
      <section className="text-center py-16 border-t border-neutral-200">
        <h2 className="text-3xl font-bold">Ready when you are.</h2>
        <p className="text-neutral-600 mt-2 mb-6">
          Join the waitlist — first 500 get {`{incentive}`}.
        </p>
        <WaitlistForm />
      </section>

      <footer className="text-sm text-neutral-500 text-center py-8">
        © {new Date().getFullYear()} AppName. <a href="/privacy">Privacy</a> ·{" "}
        <a href="/terms">Terms</a> · <a href="/press">Press</a>
      </footer>
    </main>
  );
}
