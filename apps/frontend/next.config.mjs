/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // The browser talks to /api/*; Next proxies to the backend. Keeps the frontend
    // origin single (no CORS) and mirrors the BFF pattern the architecture specifies.
    return [
      {
        source: "/backend/:path*",
        destination: `${process.env.TAXOS_API_URL ?? "http://localhost:8000"}/:path*`,
      },
    ];
  },
};

export default nextConfig;
