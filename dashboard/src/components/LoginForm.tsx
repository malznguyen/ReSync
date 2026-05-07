"use client";

import { KeyRound, LockKeyhole, LogIn, UserRound } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiClientError, getDevCredentials, login } from "@/lib/api";

export function LoginForm(): JSX.Element {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | undefined>();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isFilling, setIsFilling] = useState(false);

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    event.preventDefault();
    setError(undefined);
    setIsSubmitting(true);

    try {
      await login({ username, password });
      const next = searchParams.get("next") ?? "/dashboard";
      router.push(next);
      router.refresh();
    } catch (caughtError) {
      const message =
        caughtError instanceof ApiClientError
          ? caughtError.message
          : "Unable to sign in";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFillDevCredentials = async (): Promise<void> => {
    setError(undefined);
    setIsFilling(true);

    try {
      const credentials = await getDevCredentials();
      setUsername(credentials.username);
      setPassword(credentials.password);
    } catch (caughtError) {
      const message =
        caughtError instanceof ApiClientError
          ? caughtError.message
          : "Local admin credentials are unavailable";
      setError(message);
    } finally {
      setIsFilling(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="space-y-4">
        <div className="relative">
          <UserRound
            className="pointer-events-none absolute bottom-3.5 left-3 h-4 w-4 text-ink-500"
            aria-hidden="true"
          />
          <Input
            label="Username"
            name="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="pl-10"
            autoComplete="username"
            required
          />
        </div>
        <div className="relative">
          <LockKeyhole
            className="pointer-events-none absolute bottom-3.5 left-3 h-4 w-4 text-ink-500"
            aria-hidden="true"
          />
          <Input
            label="Password"
            name="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="pl-10"
            autoComplete="current-password"
            required
          />
        </div>
      </div>

      {error ? (
        <div className="rounded-lg border border-copper-600/20 bg-copper-100/45 px-3 py-2 text-sm font-semibold text-copper-600">
          {error}
        </div>
      ) : null}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        <LogIn className="h-4 w-4" aria-hidden="true" />
        {isSubmitting ? "Signing in" : "Sign in"}
      </Button>
      <Button
        type="button"
        variant="secondary"
        className="w-full"
        onClick={handleFillDevCredentials}
        disabled={isFilling || isSubmitting}
      >
        <KeyRound className="h-4 w-4" aria-hidden="true" />
        {isFilling ? "Filling credentials" : "Use local admin"}
      </Button>
    </form>
  );
}
