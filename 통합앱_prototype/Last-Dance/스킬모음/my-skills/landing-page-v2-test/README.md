# AppName - Mobile App Landing Page

A beautiful, high-converting landing page for a mobile productivity app, built with Next.js 15, TypeScript, Tailwind CSS, and ShadCN UI.

## 🎨 Design Approach

**Aesthetic Direction: Modern & Sleek**

- Clean, contemporary design with bold visual elements
- 3D device mockups with depth effects
- Smooth animations and gradient accents
- Purple-Blue gradient primary colors with Cyan accents

**Typography:**
- Display Font: **Space Grotesk** (modern, geometric, tech-forward)
- Body Font: **DM Sans** (clean, highly readable)

## ✨ Features

This landing page includes all **11 Essential Elements** for high conversion:

1. ✅ **SEO-Optimized URL** - Keywords in metadata and URL structure
2. ✅ **Company Logo** - Animated logo in sticky header
3. ✅ **Hero Title & Subtitle** - Large typography with staggered animations
4. ✅ **Primary CTA** - Prominent download buttons with hover effects
5. ✅ **Social Proof** - Star ratings, download stats, user counts
6. ✅ **Media Section** - 3 phone mockups showcasing app features
7. ✅ **Benefits/Features** - 6 feature cards with custom icons and gradients
8. ✅ **Customer Testimonials** - 6 authentic testimonials with avatars
9. ✅ **FAQ Section** - 8 questions with smooth accordion UI
10. ✅ **Final CTA** - Dramatic full-width conversion section
11. ✅ **Footer** - Multi-column footer with newsletter signup

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ or pnpm 8+

### Installation

```bash
# Install dependencies
pnpm install

# Run development server
pnpm dev

# Build for production
pnpm build

# Start production server
pnpm start
```

Open [http://localhost:3000](http://localhost:3000) to view the landing page.

## 📁 Project Structure

```
landing-page-v2-test/
├── app/
│   ├── layout.tsx          # Root layout with SEO metadata
│   ├── page.tsx            # Main landing page
│   └── globals.css         # Global styles & design system
├── components/
│   ├── ui/                 # ShadCN UI components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── accordion.tsx
│   │   ├── badge.tsx
│   │   └── avatar.tsx
│   ├── Header.tsx          # Sticky navigation header
│   ├── Hero.tsx            # Hero section with CTA
│   ├── MediaSection.tsx    # Phone mockups showcase
│   ├── Benefits.tsx        # Features grid
│   ├── Testimonials.tsx    # Customer reviews
│   ├── FAQ.tsx             # FAQ accordion
│   ├── FinalCTA.tsx        # Bottom conversion section
│   └── Footer.tsx          # Footer with links
├── lib/
│   └── utils.ts            # Utility functions
└── public/
    └── images/             # Static images
```

## 🎯 Key Components

### Header
- Sticky navigation with blur effect on scroll
- Mobile-responsive menu
- Animated logo and gradient text

### Hero Section
- Staggered text animations
- App Store badges
- Social proof metrics (ratings, downloads, users)
- Primary CTA buttons

### Media Section
- 3 phone mockups with CSS-only UI
- Hover effects (scale, rotate)
- Responsive grid layout

### Benefits
- 6 feature cards with gradient icons
- Custom hover animations
- Asymmetric layout for visual interest

### Testimonials
- 6 customer reviews
- Avatar with gradient backgrounds
- Star ratings
- Trust badges

### FAQ
- 8 common questions
- Smooth accordion animations
- Additional help section

### Final CTA
- Dramatic gradient background
- Benefits checklist
- Dual CTA buttons
- App Store badges

### Footer
- Multi-column layout
- Social media links
- Newsletter signup
- Legal links

## 🎨 Customization

### Colors

Edit `app/globals.css` to change the color palette:

```css
:root {
  --primary: 243 75% 59%;  /* Purple-Blue */
  --accent: 188 94% 43%;   /* Cyan */
  /* ... other colors */
}
```

### Typography

Change fonts by updating Google Fonts import in `app/globals.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=Your+Font&display=swap');

:root {
  --font-display: 'Your Font', sans-serif;
}
```

### Content

Update text content in each component file:
- Hero titles, CTAs, and stats
- Feature descriptions
- Testimonials
- FAQ questions and answers

## 🔧 Technologies Used

- **Next.js 15** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first CSS
- **ShadCN UI** - Customizable component library
- **Lucide React** - Icon library
- **Framer Motion** - Animation library (optional)

## 📱 Responsive Design

The landing page is fully responsive across:
- Mobile (320px+)
- Tablet (768px+)
- Desktop (1024px+)
- Large screens (1280px+)

## ♿ Accessibility

- Semantic HTML5 elements
- ARIA labels for icon-only buttons
- Keyboard navigation support
- Color contrast meets WCAG AA standards
- Reduced motion support

## 🎭 Design Philosophy

This landing page follows the **Landing Page Guide V2** principles:

1. **Conversion + Memorability** - Converts visitors AND makes them remember your brand
2. **Intentional Design** - Every choice is deliberate, not default
3. **No Generic AI Aesthetics** - Avoids template-looking designs
4. **Design System First** - Fonts, colors, motion defined before coding
5. **Customized Components** - ShadCN is a starting point, not the final design

## 📝 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Feel free to customize this template for your own mobile app landing page!

---

Built with ❤️ using the Landing Page Guide V2 skill
