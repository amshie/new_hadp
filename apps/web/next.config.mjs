/** @type {import('next').NextConfig} */

// In dev, Next's HMR needs eval + a websocket; production drops both for a tighter policy.
const isDev = process.env.NODE_ENV !== "production";

// Baseline CSP. The app makes no cross-origin browser requests (the API is reached server-side),
// so connect/img/etc. stay 'self'. `'unsafe-inline'` for scripts/styles is the known Next App Router
// limitation without a nonce middleware (a nonce-based CSP is a documented follow-up); the
// frame-ancestors/object-src/base-uri directives still close clickjacking and base-tag/object
// injection regardless.
const contentSecurityPolicy = [
  "default-src 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "frame-src 'none'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  "style-src 'self' 'unsafe-inline'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  `connect-src 'self'${isDev ? " ws:" : ""}`,
  "form-action 'self'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: contentSecurityPolicy },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), browsing-topics=()",
  },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
];

const nextConfig = {
  // The API client is a workspace TS package; transpile it for the app.
  transpilePackages: ["@hadp/api-client"],
  reactStrictMode: true,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
