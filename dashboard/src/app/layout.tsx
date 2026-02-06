import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Lab Test Comparison Dashboard",
  description:
    "Compare diagnostic test prices and availability across Metropolis, Agilus, Apollo, Neuberg, and TRUSTlab",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-gray-50 dark:bg-gray-950`}
      >
        <nav className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-14">
              <div className="flex items-center gap-8">
                <Link
                  href="/"
                  className="text-lg font-bold text-gray-900 dark:text-white"
                >
                  LabCompare
                </Link>
                <div className="hidden sm:flex gap-6">
                  <Link
                    href="/"
                    className="text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
                  >
                    Search
                  </Link>
                  <Link
                    href="/heatmap"
                    className="text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
                  >
                    Price Heatmap
                  </Link>
                  <Link
                    href="/availability"
                    className="text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
                  >
                    Availability
                  </Link>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-400">5 Labs</span>
                <div className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-blue-600" title="Metropolis" />
                  <span className="w-2 h-2 rounded-full bg-green-600" title="Agilus" />
                  <span className="w-2 h-2 rounded-full bg-red-600" title="Apollo" />
                  <span className="w-2 h-2 rounded-full bg-purple-600" title="Neuberg" />
                  <span className="w-2 h-2 rounded-full bg-orange-600" title="TRUSTlab" />
                </div>
              </div>
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {children}
        </main>
      </body>
    </html>
  );
}
