import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import Link from "next/link";
import { 
  FiHome, 
  FiGitBranch, 
  FiCpu, 
  FiCode, 
  FiTrendingUp, 
  FiPackage, 
  FiShield,
  FiUsers,
  FiLayers,
  FiActivity,
  FiBarChart,
  FiFileText,
  FiZap,
  FiGlobe,
  FiTerminal,
  FiDatabase,
  FiSearch,
  FiAlertCircle,
  FiCheckCircle,
  FiEdit3,
  FiMonitor
} from "react-icons/fi";

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
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="font-sans antialiased bg-primary text-primary">
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 bg-primary">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}

function Sidebar() {
  const navSections = [
    {
      title: "Dashboard",
      items: [
        { href: "/", label: "Overview", icon: <FiHome className="w-4 h-4" /> },
        { href: "/hierarchy", label: "Hierarchy", icon: <FiGitBranch className="w-4 h-4" /> },
        { href: "/activity", label: "Activity", icon: <FiActivity className="w-4 h-4" /> },
        { href: "/monitoring", label: "Monitoring", icon: <FiBarChart className="w-4 h-4" /> },
      ]
    },
    {
      title: "Orchestrators",
      items: [
        { href: "/agents/ceo", label: "CEO Atlas", icon: <FiGlobe className="w-4 h-4" /> },
        { href: "/agents/engineering", label: "Engineering Atlas", icon: <FiCode className="w-4 h-4" /> },
        { href: "/agents/growth", label: "Growth Atlas", icon: <FiTrendingUp className="w-4 h-4" /> },
        { href: "/agents/product", label: "Product Atlas", icon: <FiPackage className="w-4 h-4" /> },
        { href: "/agents/ops", label: "Ops Atlas", icon: <FiShield className="w-4 h-4" /> },
      ]
    },
    {
      title: "Engineering Team",
      items: [
        { href: "/agents/forge", label: "Forge", icon: <FiTerminal className="w-4 h-4" /> },
        { href: "/agents/tess", label: "Tess", icon: <FiCheckCircle className="w-4 h-4" /> },
        { href: "/agents/arc", label: "Arc", icon: <FiLayers className="w-4 h-4" /> },
        { href: "/agents/guardian", label: "Guardian", icon: <FiShield className="w-4 h-4" /> },
        { href: "/agents/shield", label: "Shield", icon: <FiAlertCircle className="w-4 h-4" /> },
        { href: "/agents/docsmith", label: "Docsmith", icon: <FiFileText className="w-4 h-4" /> },
      ]
    },
    {
      title: "Growth Team",
      items: [
        { href: "/agents/orbit", label: "Orbit", icon: <FiSearch className="w-4 h-4" /> },
        { href: "/agents/beacon", label: "Beacon", icon: <FiEdit3 className="w-4 h-4" /> },
        { href: "/agents/pulse", label: "Pulse", icon: <FiUsers className="w-4 h-4" /> },
        { href: "/agents/relay", label: "Relay", icon: <FiZap className="w-4 h-4" /> },
        { href: "/agents/lumen", label: "Lumen", icon: <FiMonitor className="w-4 h-4" /> },
      ]
    },
    {
      title: "Product Team",
      items: [
        { href: "/agents/sage", label: "Sage", icon: <FiFileText className="w-4 h-4" /> },
        { href: "/agents/nova", label: "Nova", icon: <FiUsers className="w-4 h-4" /> },
        { href: "/agents/signal", label: "Signal", icon: <FiBarChart className="w-4 h-4" /> },
      ]
    },
    {
      title: "Ops Team",
      items: [
        { href: "/agents/sentinel", label: "Sentinel", icon: <FiActivity className="w-4 h-4" /> },
        { href: "/agents/auditor", label: "Auditor", icon: <FiDatabase className="w-4 h-4" /> },
        { href: "/agents/responder", label: "Responder", icon: <FiAlertCircle className="w-4 h-4" /> },
      ]
    }
  ];

  return (
    <aside className="w-64 bg-secondary border-r border-gray-700 overflow-y-auto">
      <div className="p-6">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <FiCpu className="w-6 h-6" />
            Mission Control
          </h1>
          <p className="text-sm text-secondary mt-1">AI Agent Dashboard</p>
        </div>
        
        <nav className="space-y-6">
          {navSections.map((section) => (
            <div key={section.title}>
              <h3 className="text-xs font-semibold text-tertiary uppercase tracking-wider mb-2">
                {section.title}
              </h3>
              <div className="space-y-1">
                {section.items.map(item => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-tertiary transition-colors text-secondary hover:text-primary"
                  >
                    {item.icon}
                    <span className="text-sm">{item.label}</span>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </nav>
      </div>
    </aside>
  );
}