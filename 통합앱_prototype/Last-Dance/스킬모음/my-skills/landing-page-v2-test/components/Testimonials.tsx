"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar"
import { Star } from "lucide-react"

export default function Testimonials() {
  const testimonials = [
    {
      name: "Sarah Chen",
      role: "Product Manager at TechCorp",
      avatar: "SC",
      rating: 5,
      text: "This app has completely transformed how our team collaborates. The real-time sync and intuitive interface make it a joy to use every day. Couldn't imagine working without it!",
    },
    {
      name: "Michael Rodriguez",
      role: "Freelance Designer",
      avatar: "MR",
      rating: 5,
      text: "As a freelancer juggling multiple clients, this app keeps me organized and on track. The AI-powered insights have helped me optimize my workflow significantly.",
    },
    {
      name: "Emily Thompson",
      role: "Startup Founder",
      avatar: "ET",
      rating: 5,
      text: "The best productivity app I've ever used. Simple, beautiful, and powerful. It's helped our startup move faster and stay aligned across time zones.",
    },
    {
      name: "David Kim",
      role: "Software Engineer",
      avatar: "DK",
      rating: 5,
      text: "Clean UI, blazing fast, and packed with features. The mobile app is even better than the desktop version. 10/10 would recommend to any developer.",
    },
    {
      name: "Jessica Martinez",
      role: "Marketing Director",
      avatar: "JM",
      rating: 5,
      text: "Our marketing team's productivity has increased by 40% since switching to this app. The analytics dashboard gives us insights we never had before.",
    },
    {
      name: "Alex Johnson",
      role: "Student",
      avatar: "AJ",
      rating: 5,
      text: "Perfect for managing coursework and group projects. The free tier has everything I need, and the premium features are worth every penny!",
    },
  ]

  return (
    <section id="testimonials" className="py-20 bg-gradient-to-b from-primary/5 to-background">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="mb-4">
              Loved by{" "}
              <span className="gradient-text">Thousands of Users</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Don't just take our word for it. Here's what real users have to
              say about their experience with AppName.
            </p>
          </div>

          {/* Testimonials Grid */}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {testimonials.map((testimonial, index) => (
              <Card
                key={index}
                className="group border-2 border-border/50 hover:border-accent/50 transition-all duration-300 hover:shadow-xl hover:-translate-y-1 bg-card/50 backdrop-blur"
                style={{
                  animationDelay: `${index * 100}ms`,
                }}
              >
                <CardContent className="p-6">
                  {/* Rating */}
                  <div className="flex gap-1 mb-4">
                    {[...Array(testimonial.rating)].map((_, i) => (
                      <Star
                        key={i}
                        className="w-4 h-4 fill-yellow-400 text-yellow-400"
                      />
                    ))}
                  </div>

                  {/* Testimonial Text */}
                  <p className="text-foreground/90 mb-6 leading-relaxed">
                    "{testimonial.text}"
                  </p>

                  {/* Author */}
                  <div className="flex items-center gap-3">
                    <Avatar className="w-12 h-12 border-2 border-primary/20">
                      <AvatarFallback className="bg-gradient-to-br from-primary to-accent text-white font-semibold">
                        {testimonial.avatar}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="font-semibold text-foreground">
                        {testimonial.name}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {testimonial.role}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Trust Badges */}
          <div className="mt-16 text-center">
            <p className="text-sm text-muted-foreground mb-6">
              Trusted by teams at leading companies
            </p>
            <div className="flex flex-wrap items-center justify-center gap-8 opacity-50">
              {["Google", "Meta", "Apple", "Amazon", "Microsoft"].map((company) => (
                <div
                  key={company}
                  className="text-2xl font-bold text-foreground/60"
                >
                  {company}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
