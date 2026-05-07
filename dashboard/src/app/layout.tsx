import type { Metadata } from "next";
import { Instrument_Sans, Manrope } from "next/font/google";

import "./globals.css";

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
  display: "swap"
});

const instrument = Instrument_Sans({
  subsets: ["latin"],
  variable: "--font-instrument",
  display: "swap"
});

export const metadata: Metadata = {
  title: "ReSync Control",
  description: "Admin dashboard for the AI Restaurant Vision System"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>): JSX.Element {
  return (
    <html lang="en">
      <body className={`${manrope.variable} ${instrument.variable} font-sans`}>
        {children}
      </body>
    </html>
  );
}
