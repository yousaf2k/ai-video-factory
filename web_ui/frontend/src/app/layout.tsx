/**
 * Root layout for the application
 */
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from '@/components/providers';
import { Toaster } from 'sonner';
import Link from 'next/link';
import { List } from 'lucide-react';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'AI Video Factory',
  description: 'Generate cinematic videos from text ideas',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <div className="min-h-screen bg-background">
            <header className="border-b bg-card">
              <div className="container mx-auto px-4 py-4 flex items-center justify-between">
                <Link href="/sessions" className="text-xl font-bold text-primary">
                  AI Video Factory
                </Link>
                <nav className="flex items-center gap-6">
                  <Link href="/sessions" className="text-sm font-medium hover:text-primary transition-colors">
                    Sessions
                  </Link>
                  <Link href="/queue" className="text-sm font-medium hover:text-primary transition-colors flex items-center gap-1">
                    <List className="w-4 h-4" />
                    Queue
                  </Link>
                  <Link href="/agents" className="text-sm font-medium hover:text-primary transition-colors">
                    Agents
                  </Link>
                  <Link href="/workflows" className="text-sm font-medium hover:text-primary transition-colors">
                    Workflows
                  </Link>
                  <Link href="/config" className="text-sm font-medium hover:text-primary transition-colors">
                    Configuration
                  </Link>
                </nav>
              </div>
            </header>
            <main>
              {children}
            </main>
          </div>
          <Toaster
            position="top-right"
            toastOptions={{
              style: {
                border: "2px solid",
                borderRadius: "0.5rem",
                boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)",
              },
              success: {
                style: {
                  borderColor: "rgb(34 197 94)", // green-500
                  backgroundColor: "rgb(240 253 244)", // green-50
                  color: "rgb(21 128 61)", // green-800
                },
              },
              error: {
                style: {
                  borderColor: "rgb(239 68 68)", // red-500
                  backgroundColor: "rgb(254 242 242)", // red-50
                  color: "rgb(185 28 28)", // red-800
                },
              },
              warning: {
                style: {
                  borderColor: "rgb(234 179 8)", // yellow-500
                  backgroundColor: "rgb(254 252 240)", // yellow-50
                  color: "rgb(161 98 7)", // yellow-800
                },
              },
              info: {
                style: {
                  borderColor: "rgb(59 130 246)", // blue-500
                  backgroundColor: "rgb(239 246 255)", // blue-50
                  color: "rgb(30 64 175)", // blue-800
                },
              },
            }}
          />
        </Providers>
      </body>
    </html>
  );
}
