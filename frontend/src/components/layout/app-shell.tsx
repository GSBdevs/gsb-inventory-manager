import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/auth";
import { Boxes, LayoutDashboard, LogOut } from "lucide-react";
import { NavLink, Outlet } from "react-router";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/itens", label: "Itens", icon: Boxes, end: false },
];

export default function AppShell() {
  const { profile, logout } = useAuth();
  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 flex-col border-r border-border bg-card p-4 md:flex">
        <div className="mb-6 px-2 text-lg font-bold tracking-tight">
          GrupoSB <span className="text-primary">Estoque</span>
        </div>
        <nav className="flex flex-col gap-1">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm ${
                  isActive
                    ? "bg-primary/15 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto flex items-center justify-between px-2 pt-4">
          <span className="truncate text-xs text-muted-foreground">{profile?.email}</span>
          <Button variant="ghost" size="icon" onClick={() => void logout()} title="Sair">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </aside>
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  );
}
