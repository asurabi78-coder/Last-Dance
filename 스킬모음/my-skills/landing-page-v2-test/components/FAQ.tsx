"use client"

import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion"

export default function FAQ() {
  const faqs = [
    {
      question: "Is AppName free to use?",
      answer:
        "Yes! AppName offers a generous free tier with all core features. You can upgrade to our Premium plan for advanced features like unlimited team members, priority support, and advanced analytics.",
    },
    {
      question: "Which platforms does AppName support?",
      answer:
        "AppName is available on iOS (iPhone and iPad), Android, and web browsers. All your data syncs seamlessly across all devices in real-time, so you can start on your phone and continue on your tablet or computer.",
    },
    {
      question: "How secure is my data?",
      answer:
        "We take security very seriously. All data is encrypted end-to-end using bank-level AES-256 encryption. We're SOC 2 compliant and undergo regular third-party security audits. Your data is stored on secure servers with multiple redundancy backups.",
    },
    {
      question: "Can I use AppName with my team?",
      answer:
        "Absolutely! AppName is designed for both individual use and team collaboration. You can create workspaces, invite team members, assign tasks, and collaborate in real-time. The free plan supports up to 5 team members.",
    },
    {
      question: "What's included in the Premium plan?",
      answer:
        "Premium includes unlimited team members, advanced analytics and reporting, priority customer support, custom integrations, increased storage (100GB vs 5GB), offline mode, and early access to new features. You also get advanced AI capabilities for task prioritization.",
    },
    {
      question: "Can I cancel my subscription anytime?",
      answer:
        "Yes, you can cancel your Premium subscription at any time with no cancellation fees. If you cancel, you'll continue to have Premium access until the end of your billing period, then automatically switch to the free plan.",
    },
    {
      question: "Does AppName work offline?",
      answer:
        "Yes! Premium users have full offline access. All your tasks and data are available offline, and changes automatically sync when you're back online. Free users have limited offline access to recently viewed content.",
    },
    {
      question: "How do I migrate my data from other apps?",
      answer:
        "We offer easy import tools for popular productivity apps like Trello, Asana, Notion, and Todoist. Simply go to Settings > Import Data and follow the step-by-step wizard. Most imports complete in under 5 minutes!",
    },
  ]

  return (
    <section id="faq" className="py-20 bg-background">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="mb-4">
              Frequently Asked{" "}
              <span className="gradient-text">Questions</span>
            </h2>
            <p className="text-xl text-muted-foreground">
              Everything you need to know about AppName. Can't find the answer
              you're looking for? Feel free to{" "}
              <a href="#" className="text-primary hover:underline">
                contact our support team
              </a>
              .
            </p>
          </div>

          <Accordion>
            {faqs.map((faq, index) => (
              <AccordionItem
                key={index}
                value={`item-${index}`}
                className="mb-4 border-2 border-border/50 hover:border-primary/30 transition-colors"
              >
                <AccordionTrigger
                  value={`item-${index}`}
                  className="text-left text-lg font-semibold hover:text-primary"
                >
                  {faq.question}
                </AccordionTrigger>
                <AccordionContent value={`item-${index}`} className="text-base">
                  {faq.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>

          {/* Additional Help Section */}
          <div className="mt-12 p-8 bg-gradient-to-br from-primary/10 to-accent/10 rounded-2xl border-2 border-primary/20">
            <div className="text-center">
              <h3 className="text-2xl font-bold mb-3">Still have questions?</h3>
              <p className="text-muted-foreground mb-6">
                Our support team is here to help 24/7
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <a
                  href="#"
                  className="inline-flex items-center justify-center px-6 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-colors"
                >
                  Contact Support
                </a>
                <a
                  href="#"
                  className="inline-flex items-center justify-center px-6 py-3 border-2 border-primary text-primary rounded-lg font-semibold hover:bg-primary/5 transition-colors"
                >
                  View Documentation
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
