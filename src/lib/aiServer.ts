/**
 * Server-side Flask AI URL. Never expose this value through NEXT_PUBLIC_*.
 * Local development may use http://localhost:8000 explicitly in .env.local.
 */
export function getAiServerBaseUrl(): string | null {
  const configured = process.env.AI_SERVER_URL?.trim();
  if (!configured) return null;

  try {
    const parsed = new URL(configured);
    const hostname = parsed.hostname.replace(/^\[|\]$/g, "").toLowerCase();
    const isLoopback = ["localhost", "127.0.0.1", "0.0.0.0", "::1"].includes(
      hostname
    );

    if (
      !["http:", "https:"].includes(parsed.protocol) ||
      parsed.username ||
      parsed.password ||
      parsed.pathname !== "/" ||
      parsed.search ||
      parsed.hash ||
      (process.env.VERCEL && isLoopback)
    ) {
      console.error("Invalid AI_SERVER_URL configuration.");
      return null;
    }

    return parsed.origin;
  } catch {
    console.error("Invalid AI_SERVER_URL configuration.");
    return null;
  }
}
