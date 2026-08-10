import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/context/auth";

export default function DashboardPage() {
  const { profile } = useAuth();
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Bem-vindo, {profile?.full_name || profile?.email}.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Fundação pronta</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Login (Supabase) e estrutura no ar. Os módulos de peças, máquinas e relatórios entram
          nas próximas fases.
        </CardContent>
      </Card>
    </div>
  );
}
