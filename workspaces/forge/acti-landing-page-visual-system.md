# ACT-I Landing Page Visual Design System ⚔️

## 1. Color Palette & Theme

### Primary Colors
```css
--acti-navy: #1B365D;           /* Primary brand navy */
--acti-gold: #D4AF37;           /* Premium gold accent */
--acti-platinum: #F8F9FA;       /* Clean platinum */
--acti-charcoal: #2C2F36;       /* Rich charcoal */
```

### Dark Theme Gradient System
```css
--gradient-primary: linear-gradient(135deg, #1B365D 0%, #2C2F36 100%);
--gradient-accent: linear-gradient(135deg, #D4AF37 0%, #F4D03F 100%);
--gradient-subtle: linear-gradient(135deg, #2C2F36 0%, #34495E 100%);
--gradient-hero: linear-gradient(135deg, #1B365D 0%, #2C2F36 50%, #34495E 100%);
```

### Semantic Colors
```css
--success: #27AE60;
--warning: #F39C12;
--error: #E74C3C;
--info: #3498DB;
--text-primary: #F8F9FA;
--text-secondary: #BDC3C7;
--text-muted: #95A5A6;
```

## 2. Typography Hierarchy

### Font Stack
```css
--font-primary: 'Montserrat', sans-serif;    /* Headings & Authority */
--font-secondary: 'Inter', sans-serif;        /* Body & UI Elements */
--font-accent: 'Playfair Display', serif;     /* Elegant accents */
```

### Type Scale
```css
--text-xs: 12px;     /* Caption text */
--text-sm: 14px;     /* Small body */
--text-base: 16px;   /* Base body */
--text-lg: 18px;     /* Large body */
--text-xl: 20px;     /* Subheadings */
--text-2xl: 24px;    /* Section titles */
--text-3xl: 30px;    /* Page titles */
--text-4xl: 36px;    /* Hero subtitle */
--text-5xl: 48px;    /* Hero title */
--text-6xl: 60px;    /* Hero main (desktop) */
```

### Typography Classes
```css
.hero-title {
  font-family: var(--font-primary);
  font-size: var(--text-6xl);
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -0.025em;
  background: var(--gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.section-title {
  font-family: var(--font-primary);
  font-size: var(--text-3xl);
  font-weight: 700;
  color: var(--acti-platinum);
  margin-bottom: 1.5rem;
}

.body-text {
  font-family: var(--font-secondary);
  font-size: var(--text-base);
  line-height: 1.6;
  color: var(--text-secondary);
}
```

## 3. Spacing & Grid System

### Spacing Scale
```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;
--space-20: 80px;
--space-24: 96px;
```

### Responsive Grid
```css
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-6);
}

.grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-8); }
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-6); }
.grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-6); }

@media (max-width: 768px) {
  .grid-2, .grid-3, .grid-4 { 
    grid-template-columns: 1fr; 
    gap: var(--space-4);
  }
}
```

## 4. Component Designs

### Hero Section
```css
.hero {
  background: var(--gradient-hero);
  padding: var(--space-24) 0 var(--space-20);
  text-align: center;
  position: relative;
  overflow: hidden;
}

.hero::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: 
    radial-gradient(circle at 20% 80%, rgba(212, 175, 55, 0.1) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(212, 175, 55, 0.05) 0%, transparent 50%);
  pointer-events: none;
}

.hero-content {
  position: relative;
  z-index: 2;
  max-width: 800px;
  margin: 0 auto;
}

.hero-subtitle {
  font-family: var(--font-accent);
  font-size: var(--text-xl);
  color: var(--acti-gold);
  margin-bottom: var(--space-4);
  font-style: italic;
}

.hero-description {
  font-size: var(--text-lg);
  color: var(--text-secondary);
  margin: var(--space-6) 0 var(--space-8);
  line-height: 1.7;
}
```

### AI Being Cards
```css
.being-card {
  background: linear-gradient(135deg, #2C2F36 0%, #34495E 100%);
  border: 1px solid rgba(212, 175, 55, 0.2);
  border-radius: 16px;
  padding: var(--space-8);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.being-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--gradient-accent);
}

.being-card:hover {
  transform: translateY(-4px);
  border-color: var(--acti-gold);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.being-icon {
  width: 48px;
  height: 48px;
  background: var(--gradient-accent);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  margin-bottom: var(--space-4);
}

.being-title {
  font-family: var(--font-primary);
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--acti-platinum);
  margin-bottom: var(--space-3);
}

.being-description {
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-4);
}

.being-specialties {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.specialty-tag {
  background: rgba(212, 175, 55, 0.1);
  color: var(--acti-gold);
  padding: var(--space-1) var(--space-3);
  border-radius: 20px;
  font-size: var(--text-sm);
  font-weight: 500;
}
```

### Service Cards
```css
.service-card {
  background: var(--gradient-subtle);
  border: 1px solid rgba(248, 249, 250, 0.1);
  border-radius: 20px;
  padding: var(--space-10);
  text-align: center;
  transition: all 0.3s ease;
  position: relative;
}

.service-card.featured {
  border-color: var(--acti-gold);
  background: linear-gradient(135deg, #1B365D 0%, #2C2F36 100%);
  transform: scale(1.05);
}

.service-card.featured::before {
  content: 'MOST POPULAR';
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--gradient-accent);
  color: var(--acti-navy);
  padding: var(--space-2) var(--space-4);
  border-radius: 20px;
  font-size: var(--text-xs);
  font-weight: 700;
  letter-spacing: 0.05em;
}

.service-price {
  font-family: var(--font-primary);
  font-size: var(--text-4xl);
  font-weight: 800;
  color: var(--acti-gold);
  margin-bottom: var(--space-2);
}

.service-title {
  font-family: var(--font-primary);
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--acti-platinum);
  margin-bottom: var(--space-4);
}

.service-features {
  list-style: none;
  padding: 0;
  margin: var(--space-6) 0;
}

.service-features li {
  color: var(--text-secondary);
  margin-bottom: var(--space-3);
  position: relative;
  padding-left: var(--space-6);
}

.service-features li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: var(--acti-gold);
  font-weight: bold;
}
```

### Contact Form
```css
.contact-form {
  background: var(--gradient-subtle);
  border: 1px solid rgba(212, 175, 55, 0.2);
  border-radius: 20px;
  padding: var(--space-10);
  max-width: 600px;
  margin: 0 auto;
}

.form-group {
  margin-bottom: var(--space-6);
}

.form-label {
  display: block;
  color: var(--acti-platinum);
  font-weight: 600;
  margin-bottom: var(--space-2);
}

.form-input, .form-textarea, .form-select {
  width: 100%;
  background: rgba(248, 249, 250, 0.05);
  border: 1px solid rgba(248, 249, 250, 0.2);
  border-radius: 12px;
  padding: var(--space-4);
  color: var(--acti-platinum);
  font-family: var(--font-secondary);
  transition: all 0.3s ease;
}

.form-input:focus, .form-textarea:focus, .form-select:focus {
  outline: none;
  border-color: var(--acti-gold);
  box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.1);
}

.form-textarea {
  height: 120px;
  resize: vertical;
}
```

### Buttons & CTAs
```css
.btn-primary {
  background: var(--gradient-accent);
  color: var(--acti-navy);
  border: none;
  padding: var(--space-4) var(--space-8);
  border-radius: 12px;
  font-family: var(--font-primary);
  font-weight: 700;
  font-size: var(--text-base);
  cursor: pointer;
  transition: all 0.3s ease;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(212, 175, 55, 0.3);
}

.btn-secondary {
  background: transparent;
  color: var(--acti-platinum);
  border: 2px solid var(--acti-gold);
  padding: var(--space-3) var(--space-6);
  border-radius: 12px;
  font-family: var(--font-primary);
  font-weight: 600;
  transition: all 0.3s ease;
}

.btn-secondary:hover {
  background: var(--acti-gold);
  color: var(--acti-navy);
}

.btn-large {
  padding: var(--space-5) var(--space-10);
  font-size: var(--text-lg);
  border-radius: 16px;
}
```

## 5. Visual Hierarchy Flow

### Page Structure
1. **Hero Section** - Maximum visual impact with gradient background
2. **Trust Indicators** - Subtle gold accents, clean spacing
3. **AI Beings Grid** - Card-based layout with hover animations
4. **Service Tiers** - Progressive disclosure with featured highlighting
5. **Contact Form** - Focused, single-column layout
6. **Footer** - Minimal, professional closure

### Hierarchy Principles
- **Primary Focus**: Hero title with gradient text treatment
- **Secondary Focus**: AI being cards with interactive states
- **Tertiary Focus**: Service cards with price emphasis
- **Support Elements**: Form fields, navigation, footer

### Animation & Interaction
```css
/* Scroll-triggered animations */
.fade-in-up {
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.6s ease;
}

.fade-in-up.visible {
  opacity: 1;
  transform: translateY(0);
}

/* Staggered animation delays */
.being-card:nth-child(1) { transition-delay: 0.1s; }
.being-card:nth-child(2) { transition-delay: 0.2s; }
.being-card:nth-child(3) { transition-delay: 0.3s; }
.being-card:nth-child(4) { transition-delay: 0.4s; }
.being-card:nth-child(5) { transition-delay: 0.5s; }
.being-card:nth-child(6) { transition-delay: 0.6s; }
```

## 6. Responsive Specifications

### Breakpoints
```css
--mobile: 480px;
--tablet: 768px;
--desktop: 1024px;
--large: 1200px;
```

### Mobile Adaptations
```css
@media (max-width: 768px) {
  .hero-title { font-size: var(--text-4xl); }
  .hero { padding: var(--space-16) 0; }
  .being-card, .service-card { padding: var(--space-6); }
  .container { padding: 0 var(--space-4); }
}

@media (max-width: 480px) {
  .hero-title { font-size: var(--text-3xl); }
  .service-card.featured { transform: none; }
  .btn-large { 
    width: 100%; 
    padding: var(--space-4) var(--space-6);
  }
}
```

## 7. Accessibility & Performance

### Accessibility Features
- **Color Contrast**: 4.5:1 minimum ratio maintained
- **Focus States**: Clear visual indicators for keyboard navigation
- **Screen Reader**: Semantic HTML structure with proper ARIA labels
- **Motion**: Respect prefers-reduced-motion user preference

### Performance Optimizations
- **Critical CSS**: Inline hero section styles
- **Font Loading**: Use font-display: swap for web fonts
- **Images**: WebP format with fallbacks
- **Animations**: Use transform and opacity for GPU acceleration

This visual system creates a premium, professional aesthetic that conveys innovation and trust while maintaining excellent usability across all devices.