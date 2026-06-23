"use client"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Download, Sparkles, CheckCircle } from "lucide-react"

export default function FinalCTA() {
  const benefits = [
    "Free forever plan available",
    "No credit card required",
    "Cancel anytime, no questions asked",
    "14-day money-back guarantee",
  ]

  return (
    <section className="relative py-24 overflow-hidden">
      {/* Dramatic Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary via-primary/90 to-accent -z-10" />

      {/* Animated Background Elements */}
      <div className="absolute top-0 left-0 w-96 h-96 bg-white/10 rounded-full blur-3xl -z-10" />
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-accent/20 rounded-full blur-3xl -z-10" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          {/* Badge */}
          <Badge
            variant="secondary"
            className="mb-6 bg-white/20 text-white border-white/30 backdrop-blur"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Join 100,000+ Happy Users
          </Badge>

          {/* Headline */}
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
            Ready to Transform Your Productivity?
          </h2>

          {/* Subheadline */}
          <p className="text-xl md:text-2xl text-white/90 mb-8 max-w-2xl mx-auto">
            Start your free trial today and experience the power of AppName.
            No commitments, just results.
          </p>

          {/* Benefits List */}
          <div className="grid sm:grid-cols-2 gap-3 max-w-2xl mx-auto mb-10">
            {benefits.map((benefit, index) => (
              <div
                key={index}
                className="flex items-center gap-2 text-white/90 text-left bg-white/10 backdrop-blur rounded-lg px-4 py-3"
              >
                <CheckCircle className="w-5 h-5 text-green-300 flex-shrink-0" />
                <span>{benefit}</span>
              </div>
            ))}
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-8">
            <Button
              size="xl"
              className="bg-white text-primary hover:bg-white/90 shadow-2xl hover:shadow-white/50 hover:scale-110 transition-all font-bold"
            >
              <Download className="mr-2 h-6 w-6" />
              Get Started Free
            </Button>
            <Button
              size="xl"
              variant="outline"
              className="border-2 border-white text-white hover:bg-white/10 backdrop-blur"
            >
              Schedule a Demo
            </Button>
          </div>

          {/* Trust Signal */}
          <div className="text-white/80 text-sm">
            <p className="mb-2">Trusted by teams at</p>
            <div className="flex flex-wrap items-center justify-center gap-6 opacity-80">
              {["Google", "Microsoft", "Apple", "Amazon"].map((company) => (
                <span key={company} className="font-semibold text-lg">
                  {company}
                </span>
              ))}
            </div>
          </div>

          {/* App Store Badges */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-10">
            <a
              href="#"
              className="hover:opacity-80 transition-opacity"
              aria-label="Download on App Store"
            >
              <div className="h-14 px-6 bg-black text-white rounded-xl flex items-center gap-3 shadow-lg">
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
              <div className="h-14 px-6 bg-black text-white rounded-xl flex items-center gap-3 shadow-lg">
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
