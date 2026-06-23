import Header from "@/components/Header"
import Hero from "@/components/Hero"
import MediaSection from "@/components/MediaSection"
import Benefits from "@/components/Benefits"
import Testimonials from "@/components/Testimonials"
import FAQ from "@/components/FAQ"
import FinalCTA from "@/components/FinalCTA"
import Footer from "@/components/Footer"

export default function Home() {
  return (
    <>
      <Header />
      <main>
        <Hero />
        <MediaSection />
        <Benefits />
        <Testimonials />
        <FAQ />
        <FinalCTA />
      </main>
      <Footer />
    </>
  )
}
