import { AppShell } from "@/components/AppShell";

export default function ProtectedLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>): JSX.Element {
  return <AppShell>{children}</AppShell>;
}
