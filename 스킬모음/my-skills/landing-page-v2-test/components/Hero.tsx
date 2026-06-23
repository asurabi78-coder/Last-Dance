"use client"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Star, Download, Users } from "lucide-react"

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Background Gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-background to-accent/5 -z-10" />

      {/* Decorative Elements */}
      <div className="absolute top-20 right-10 w-72 h-72 bg-primary/10 rounded-full blur-3xl -z-10" />
      <div className="absolute bottom-20 left-10 w-96 h-96 bg-accent/10 rounded-full blur-3xl -z-10" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 pt-32 pb-20">
        <div className="max-w-5xl mx-auto text-center">
          {/* Badge - Animated */}
          <div
            className="inline-block animate-fade-in"
            style={{ animationDelay: "0ms" }}
          >
            <Badge variant="accent" className="mb-6 px-4 py-2 text-sm">
              🎉 Now Available on iOS & Android
            </Badge>
          </div>

          {/* Main Title - Staggered Animation */}
          <h1 className="mb-6">
            <span
              className="inline-block animate-fade-in"
              style={{ animationDelay: "100ms" }}
            >
              Transform Your{" "}
            </span>
            <span
              className="inline-block animate-fade-in gradient-text"
              style={{ animationDelay: "200ms" }}
            >
              Productivity
            </span>
            <br />
            <span
              className="inline-block animate-fade-in"
              style={{ animationDelay: "300ms" }}
            >
              With the Ultimate{" "}
            </span>
            <span
              className="inline-block animate-fade-in"
              style={{ animationDelay: "400ms" }}
            >
              Mobile App
            </span>
          </h1>

          {/* Subtitle */}
          <p
            className="text-xl md:text-2xl text-muted-foreground mb-10 max-w-3xl mx-auto animate-fade-in"
            style={{ animationDelay: "500ms" }}
          >
            Experience seamless task management, real-time collaboration, and
            AI-powered insights—all in one beautiful, intuitive mobile app.
          </p>

          {/* CTA Buttons */}
          <div
            className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12 animate-fade-in"
            style={{ animationDelay: "600ms" }}
          >
            <Button variant="accent" size="xl" className="group">
              <Download className="mr-2 h-5 w-5 transition-transform group-hover:scale-110" />
              Download for Free
            </Button>
            <Button variant="outline" size="xl">
              Watch Demo
            </Button>
          </div>

          {/* Social Proof */}
          <div
            className="flex flex-col sm:flex-row items-center justify-center gap-8 text-sm animate-scale-in"
            style={{ animationDelay: "700ms" }}
          >
            {/* Rating */}
            <div className="flex items-center gap-2">
              <div className="flex">
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    className="w-5 h-5 fill-yellow-400 text-yellow-400"
                  />
                ))}
              </div>
              <span className="font-semibold">4.9/5</span>
              <span className="text-muted-foreground">(12,000+ reviews)</span>
            </div>

            {/* Divider */}
            <div className="hidden sm:block h-6 w-px bg-border" />

            {/* Downloads */}
            <div className="flex items-center gap-2">
              <Download className="w-5 h-5 text-primary" />
              <span className="font-semibold">500K+</span>
              <span className="text-muted-foreground">Downloads</span>
            </div>

            {/* Divider */}
            <div className="hidden sm:block h-6 w-px bg-border" />

            {/* Active Users */}
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-accent" />
              <span className="font-semibold">100K+</span>
              <span className="text-muted-foreground">Active Users</span>
            </div>
          </div>

          {/* App Store Badges */}
          <div
            className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-12 animate-fade-in"
            style={{ animationDelay: "800ms" }}
          >
            <a
              href="#"
              className="hover:opacity-80 transition-opacity"
              aria-label="Download on App Store"
            >
              <div className="h-14 px-6 bg-black text-white rounded-xl flex items-center gap-3">
                <svg className="w-8 h-8" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.71 19.5C17.88 20.74 17 21.95 15.66 21.97C14.32 22 13.89 21.18 12.37 21.18C10.84 21.18 10.37 21.95 9.09997 22C7.78997 22.05 6.79997 20.68 5.95997 19.47C4.24997 17 2.93997 12.45 4.69997 9.39C5.56997 7.87 7.12997 6.91 8.81997 6.88C10.1 6.86 11.32 7.75 12.11 7.75C12.89 7.75 14.37 6.68 15.92 6.84C16.57 6.87 18.39 7.1 19.56 8.82C19.47 8.88 17.39 10.1 17.41 12.63C17.44 15.65 20.06 16.66 20.09 16.67C20.06 16.74 19.67 18.11 18.71 19.5ZM13 3.5C13.73 2.67 14.94 2.04 15.94 2C16.07 3.17 15.6 4.35 14.9 5.19C14.21 6.04 13.07 6.7 11.95 6.61C11.8 5.46 12.36 4.26 13 3.5Z"/>
                </svg>
                <div className="text-left">
                  <div className="text-xs">Download on the</div>
                  <div className="text-xl font-semibold">App Store</div>
                </div>
              </div>
            </a>
            <a
              href="#"
              className="hover:opacity-80 transition-opacity"
              aria-label="Get it on Google Play"
            >
              <div className="h-14 px-6 bg-black text-white rounded-xl flex items-center gap-3">
                <svg className="w-8 h-8" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M3,20.5V3.5C3,2.91 3.34,2.39 3.84,2.15L13.69,12L3.84,21.85C3.34,21.6 3,21.09 3,20.5M16.81,15.12L6.05,21.34L14.54,12.85L16.81,15.12M20.16,10.81C20.5,11.08 20.75,11.5 20.75,12C20.75,12.5 20.53,12.9 20.18,13.18L17.89,14.5L15.39,12L17.89,9.5L20.16,10.81M6.05,2.66L16.81,8.88L14.54,11.15L6.05,2.66Z"/>
                </svg>
                <div className="text-left">
                  <div className="text-xs">GET IT ON</div>
                  <div className="text-xl font-semibold">Google Play</div>
                </div>
              </div>
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
