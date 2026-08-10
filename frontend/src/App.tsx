import AppShell from "@/components/layout/app-shell";
import { useAuth } from "@/context/auth";
import DashboardPage from "@/pages/dashboard";
import LoginPage from "@/pages/login";
import ItensPage from "@/pages/itens";
import MovimentarPage from "@/pages/movimentar";
import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router";

function Protected({ children }: { children: ReactNode }) {
  const { isAuthenticated, isReady } = useAuth();
  if (!isReady) return <div className="p-6 text-muted-foreground">Carregando...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <Protected>
            <AppShell />
          </Protected>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/itens" element={<ItensPage />} />
        <Route path="/movimentar" element={<MovimentarPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
