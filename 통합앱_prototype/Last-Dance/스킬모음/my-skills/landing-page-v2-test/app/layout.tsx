import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AppName - Your Mobile App for Productivity | Download Now",
  description: "Transform your daily workflow with AppName. The most intuitive mobile app for productivity, task management, and team collaboration. Available on iOS and Android.",
  keywords: ["mobile app", "productivity", "task management", "collaboration", "iOS app", "Android app"],
  authors: [{ name: "AppName Team" }],
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://yourapp.com",
    siteName: "AppName",
    title: "AppName - Your Mobile App for Productivity",
    description: "Transform your daily workflow with AppName. Download now on iOS and Android.",
    images: [
      {
        url: "/og-image.jpg",
        width: 1200,
        height: 630,
        alt: "AppName Preview",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "AppName - Your Mobile App for Productivity",
    description: "Transform your daily workflow with AppName. Download now on iOS and Android.",
    images: ["/og-image.jpg"],
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
