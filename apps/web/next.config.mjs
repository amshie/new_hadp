/** @type {import('next').NextConfig} */
const nextConfig = {
  // The API client is a workspace TS package; transpile it for the app.
  transpilePackages: ["@hadp/api-client"],
  reactStrictMode: true,
};

export default nextConfig;
