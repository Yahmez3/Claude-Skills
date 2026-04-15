import "./globals.css";
import type { Metadata } from "next";

const SITE = {
  name: "AppName",
  tagline: "One-sentence value prop goes here.",
  url: "https://example.com",
};

export const metadata: Metadata = {
  title: `${SITE.name} — ${SITE.tagline}`,
  description: SITE.tagline,
  openGraph: {
    title: SITE.name,
    description: SITE.tagline,
    url: SITE.url,
    images: [{ url: "/og.png", width: 1200, height: 630 }],
  },
  twitter: { card: "summary_large_image", title: SITE.name, description: SITE.tagline },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-white text-neutral-900 antialiased">{children}</body>
    </html>
  );
}
