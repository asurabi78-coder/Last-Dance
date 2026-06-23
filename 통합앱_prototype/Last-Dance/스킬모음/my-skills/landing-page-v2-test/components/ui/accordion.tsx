"use client"

import * as React from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

type AccordionContextType = {
  openItem: string | null
  setOpenItem: (item: string | null) => void
}

const AccordionContext = React.createContext<AccordionContextType | undefined>(undefined)

const Accordion = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, children, ...props }, ref) => {
  const [openItem, setOpenItem] = React.useState<string | null>(null)

  return (
    <AccordionContext.Provider value={{ openItem, setOpenItem }}>
      <div ref={ref} className={cn("space-y-4", className)} {...props}>
        {children}
      </div>
    </AccordionContext.Provider>
  )
})
Accordion.displayName = "Accordion"

const AccordionItem = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { value: string }
>(({ className, value, children, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn(
        "border rounded-lg overflow-hidden transition-all",
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
})
AccordionItem.displayName = "AccordionItem"

const AccordionTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & { value: string }
>(({ className, children, value, ...props }, ref) => {
  const context = React.useContext(AccordionContext)
  if (!context) throw new Error("AccordionTrigger must be used within Accordion")

  const isOpen = context.openItem === value

  return (
    <button
      ref={ref}
      className={cn(
        "flex w-full items-center justify-between p-6 text-left font-medium transition-all hover:bg-accent/5",
        className
      )}
      onClick={() => context.setOpenItem(isOpen ? null : value)}
      {...props}
    >
      {children}
      <ChevronDown
        className={cn(
          "h-5 w-5 shrink-0 transition-transform duration-300",
          isOpen && "rotate-180"
        )}
      />
    </button>
  )
})
AccordionTrigger.displayName = "AccordionTrigger"

const AccordionContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { value: string }
>(({ className, children, value, ...props }, ref) => {
  const context = React.useContext(AccordionContext)
  if (!context) throw new Error("AccordionContent must be used within Accordion")

  const isOpen = context.openItem === value

  return (
    <div
      ref={ref}
      className={cn(
        "overflow-hidden transition-all duration-300 ease-in-out",
        isOpen ? "max-h-96" : "max-h-0"
      )}
      {...props}
    >
      <div className={cn("px-6 pb-6 pt-0 text-muted-foreground", className)}>
        {children}
      </div>
    </div>
  )
})
AccordionContent.displayName = "AccordionContent"

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent }
