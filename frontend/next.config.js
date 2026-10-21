/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  generateEtags: false,
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate',
          },
        ],
      },
      {
        source: '/_next/static/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
    ];
  },
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8888';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: '/pay/:path*',
        destination: `${backendUrl}/pay/:path*`,
      },
      {
        source: '/broker',
        destination: `${backendUrl}/broker`,
      },
      {
        source: '/infrastructure',
        destination: `${backendUrl}/infrastructure`,
      },
      {
        source: '/reconciliation',
        destination: `${backendUrl}/reconciliation`,
      },
    ];
  },
};

module.exports = nextConfig;
