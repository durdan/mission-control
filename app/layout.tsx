import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Mission Control",
  description: "AI Agent Team Dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-gray-900 text-white">
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}

function Sidebar() {
  const navItems = [
    { href: "/", label: "📊 Overview", icon: "📊" },
    { href: "/agents", label: "👥 Agents", icon: "👥" },
    { href: "/projects", label: "📋 Projects", icon: "📋" },
    { href: "/tasks", label: "📝 Tasks", icon: "📝" },
    { href: "/monitoring", label: "📈 Monitoring", icon: "📈" },
    { href: "/activity", label: "⚡ Activity", icon: "⚡" },
  ];

  return (
    <aside className="w-64 bg-gray-800 border-r border-gray-700 p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Mission Control 🤙</h1>
        <p className="text-sm text-gray-400 mt-1">AI Agent Dashboard</p>
      </div>
      
      <nav className="space-y-2">
        {navItems.map(item => (
          <Link
            key={item.href}
            href={item.href}
            className="block px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
