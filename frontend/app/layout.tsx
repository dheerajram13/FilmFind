import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FilmFind - AI-Powered Movie Discovery",
  description: "Discover movies using natural language and AI-powered semantic search",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
