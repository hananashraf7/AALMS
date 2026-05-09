import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "AALMS — Smart Attendance",
  description: "AI-powered facial recognition attendance management system",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} antialiased`}>
        {/* Navigation — clean top bar */}
        <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-black/5">
          <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-7 h-7 rounded-lg bg-[#1a1a1a] flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                </svg>
              </div>
              <span className="text-sm font-bold tracking-wider text-[#1a1a1a]">AALMS</span>
            </Link>
            <div className="flex items-center gap-1">
              <Link href="/" className="text-xs font-semibold tracking-wide px-4 py-2 rounded-lg text-gray-500 hover:text-[#1a1a1a] hover:bg-black/[0.03] transition-colors">
                Kiosk
              </Link>
              <Link href="/admin" className="text-xs font-semibold tracking-wide px-4 py-2 rounded-lg text-gray-500 hover:text-[#1a1a1a] hover:bg-black/[0.03] transition-colors">
                Admin
              </Link>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto px-6 pb-12" style={{ paddingTop: '6rem' }}>
          {children}
        </main>
      </body>
    </html>
  );
}
