"use client"

import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Zap, Shield, Users, Sparkles, Clock, TrendingUp } from "lucide-react"

export default function Benefits() {
  const features = [
    {
      icon: Zap,
      title: "Lightning Fast",
      description: "Experience blazing-fast performance with our optimized mobile app. No lag, no waiting—just seamless productivity.",
      gradient: "from-yellow-400 to-orange-500",
    },
    {
      icon: Shield,
      title: "Bank-Level Security",
      description: "Your data is protected with end-to-end encryption and industry-leading security protocols. Privacy guaranteed.",
      gradient: "from-blue-400 to-indigo-500",
    },
    {
      icon: Users,
      title: "Real-Time Collaboration",
      description: "Work together with your team in real-time. Share tasks, communicate instantly, and stay synced across all devices.",
      gradient: "from-purple-400 to-pink-500",
    },
    {
      icon: Sparkles,
      title: "AI-Powered Insights",
      description: "Get intelligent suggestions and automated task prioritization powered by advanced machine learning algorithms.",
      gradient: "from-cyan-400 to-blue-500",
    },
    {
      icon: Clock,
      title: "Smart Scheduling",
      description: "Automatically organize your day with intelligent scheduling that adapts to your workflow and priorities.",
      gradient: "from-green-400 to-teal-500",
    },
    {
      icon: TrendingUp,
      title: "Progress Analytics",
      description: "Visualize your productivity trends with beautiful charts and actionable insights to optimize your performance.",
      gradient: "from-red-400 to-rose-500",
    },
  ]

  return (
    <section id="features" className="py-20 bg-background">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="mb-4">
              Powerful Features for{" "}
              <span className="gradient-text">Maximum Productivity</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Everything you need to supercharge your workflow and achieve more
              in less time. Built for modern teams and individuals.
            </p>
          </div>

          {/* Features Grid */}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => {
              const Icon = feature.icon
              return (
                <Card
                  key={index}
                  className="group border-2 border-border/50 hover:border-primary/50 transition-all duration-300 hover:shadow-2xl hover:-translate-y-2 bg-gradient-to-br from-background to-primary/5"
                  style={{
                    animationDelay: `${index * 100}ms`,
                  }}
                >
                  <CardHeader>
                    <div
                      className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-4 transform transition-transform group-hover:scale-110 group-hover:rotate-3`}
                    >
                      <Icon className="w-7 h-7 text-white" />
                    </div>
                    <CardTitle className="text-2xl mb-2">
                      {feature.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-base leading-relaxed">
                      {feature.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {/* Additional CTA */}
          <div className="text-center mt-12">
            <p className="text-muted-foreground mb-4">
              And many more features to discover...
            </p>
            <a
              href="#"
              className="text-primary font-semibold hover:underline inline-flex items-center gap-2"
            >
              See all features
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M17 8l4 4m0 0l-4 4m4-4H3"
                />
              </svg>
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
