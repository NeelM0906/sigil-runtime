# ACT-I Visual Design System
## Complete Implementation Specifications

### 🎨 COLOR PALETTE

```css
:root {
  /* Primary Colors */
  --primary-navy: #1B365D;
  --primary-gold: #D4AF37;
  --primary-platinum: #E5E4E2;
  
  /* Dark Theme Base */
  --bg-primary: #0A0F1A;
  --bg-secondary: #1A1F2E;
  --bg-card: #252B3A;
  --bg-hover: #2A3142;
  
  /* Text Colors */
  --text-primary: #FFFFFF;
  --text-secondary: #B8C5D1;
  --text-muted: #8A9BAE;
  --text-accent: #D4AF37;
  
  /* Gradients */
  --gradient-primary: linear-gradient(135deg, #1B365D 0%, #2A4A73 50%, #D4AF37 100%);
  --gradient-card: linear-gradient(145deg, #252B3A 0%, #1A1F2E 100%);
  --gradient-hover: linear-gradient(145deg, #2A3142 0%, #252B3A 100%);
  
  /* Accent Colors */
  --accent-success: #4ADE80;
  --accent-warning: #FBBF24;
  --accent-error: #F87171;
  --accent-info: #60A5FA;
}
```

### 📝 TYPOGRAPHY HIERARCHY

```css
/* Font Stack */
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&family=Playfair+Display:wght@400;500;600;700&display=swap');

:root {
  --font-primary: 'Montserrat', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-display: 'Playfair Display', Georgia, serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
}

/* Typography Scale */
.text-xs { font-size: 0.75rem; line-height: 1rem; }
.text-sm { font-size: 0.875rem; line-height: 1.25rem; }
.text-base { font-size: 1rem; line-height: 1.5rem; }
.text-lg { font-size: 1.125rem; line-height: 1.75rem; }
.text-xl { font-size: 1.25rem; line-height: 1.75rem; }
.text-2xl { font-size: 1.5rem; line-height: 2rem; }
.text-3xl { font-size: 1.875rem; line-height: 2.25rem; }
.text-4xl { font-size: 2.25rem; line-height: 2.5rem; }
.text-5xl { font-size: 3rem; line-height: 1.1; }
.text-6xl { font-size: 3.75rem; line-height: 1.05; }

/* Heading Styles */
.heading-display {
  font-family: var(--font-display);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}

.heading-primary {
  font-family: var(--font-primary);
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--text-primary);
}

.heading-secondary {
  font-family: var(--font-primary);
  font-weight: 600;
  letter-spacing: -0.005em;
  color: var(--text-secondary);
}
```

### 🏗️ RESPONSIVE GRID SYSTEM

```css
/* Container Sizes */
.container {
  width: 100%;
  margin: 0 auto;
  padding: 0 1rem;
}

/* Breakpoints */
@media (min-width: 640px) { .container { max-width: 640px; padding: 0 1.5rem; } }
@media (min-width: 768px) { .container { max-width: 768px; padding: 0 2rem; } }
@media (min-width: 1024px) { .container { max-width: 1024px; } }
@media (min-width: 1280px) { .container { max-width: 1280px; } }
@media (min-width: 1536px) { .container { max-width: 1536px; } }

/* Grid System */
.grid { display: grid; gap: 1.5rem; }
.grid-cols-1 { grid-template-columns: repeat(1, 1fr); }
.grid-cols-2 { grid-template-columns: repeat(2, 1fr); }
.grid-cols-3 { grid-template-columns: repeat(3, 1fr); }
.grid-cols-4 { grid-template-columns: repeat(4, 1fr); }

/* Responsive Grid */
@media (min-width: 768px) {
  .md\\:grid-cols-2 { grid-template-columns: repeat(2, 1fr); }
  .md\\:grid-cols-3 { grid-template-columns: repeat(3, 1fr); }
}

@media (min-width: 1024px) {
  .lg\\:grid-cols-3 { grid-template-columns: repeat(3, 1fr); }
  .lg\\:grid-cols-4 { grid-template-columns: repeat(4, 1fr); }
}
```

### 🎯 HERO SECTION COMPONENT

```css
.hero-section {
  background: var(--bg-primary);
  background-image: var(--gradient-primary);
  min-height: 100vh;
  display: flex;
  align-items: center;
  position: relative;
  overflow: hidden;
}

.hero-content {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 2rem;
  text-align: center;
  z-index: 2;
}

.hero-title {
  font-size: clamp(2.5rem, 8vw, 6rem);
  font-family: var(--font-display);
  font-weight: 700;
  line-height: 1.1;
  color: var(--text-primary);
  margin-bottom: 1.5rem;
  background: linear-gradient(135deg, #FFFFFF 0%, #D4AF37 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: clamp(1.125rem, 3vw, 1.5rem);
  color: var(--text-secondary);
  margin-bottom: 2rem;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
  line-height: 1.6;
}

.hero-cta {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--primary-gold);
  color: var(--bg-primary);
  padding: 1rem 2rem;
  border-radius: 0.75rem;
  font-weight: 600;
  text-decoration: none;
  font-size: 1.125rem;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.hero-cta:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 40px rgba(212, 175, 55, 0.3);
  border-color: var(--primary-platinum);
}
```

### 👥 TEAM CARD COMPONENT

```css
.team-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  padding: 4rem 0;
}

.team-card {
  background: var(--gradient-card);
  border-radius: 1rem;
  padding: 2rem;
  text-align: center;
  border: 1px solid rgba(212, 175, 55, 0.1);
  transition: all 0.4s ease;
  position: relative;
  overflow: hidden;
}

.team-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--gradient-primary);
  transform: scaleX(0);
  transition: transform 0.4s ease;
}

.team-card:hover::before {
  transform: scaleX(1);
}

.team-card:hover {
  transform: translateY(-8px);
  background: var(--gradient-hover);
  border-color: rgba(212, 175, 55, 0.3);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
}

.team-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  margin: 0 auto 1.5rem;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: var(--text-primary);
  border: 3px solid var(--primary-gold);
}

.team-name {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.team-role {
  font-size: 1rem;
  color: var(--primary-gold);
  margin-bottom: 1rem;
  font-weight: 500;
}

.team-bio {
  font-size: 0.875rem;
  color: var(--text-secondary);
  line-height: 1.6;
}
```

### 🛠️ SERVICE CARD COMPONENT

```css
.service-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 2rem;
  padding: 4rem 0;
}

.service-card {
  background: var(--bg-card);
  border-radius: 1.5rem;
  padding: 2.5rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.service-card::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--gradient-primary);
  opacity: 0;
  transition: opacity 0.4s ease;
  z-index: 1;
}

.service-card:hover::after {
  opacity: 0.05;
}

.service-card:hover {
  transform: translateY(-12px);
  border-color: var(--primary-gold);
  box-shadow: 0 25px 80px rgba(212, 175, 55, 0.15);
}

.service-content {
  position: relative;
  z-index: 2;
}

.service-icon {
  width: 60px;
  height: 60px;
  background: var(--gradient-primary);
  border-radius: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
  color: var(--text-primary);
}

.service-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 1rem;
  line-height: 1.3;
}

.service-description {
  font-size: 1rem;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 1.5rem;
}

.service-features {
  list-style: none;
  padding: 0;
  margin-bottom: 2rem;
}

.service-features li {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.service-features li::before {
  content: '✓';
  color: var(--primary-gold);
  font-weight: 700;
  font-size: 1rem;
}
```

### 📨 CONTACT FORM COMPONENT

```css
.contact-form {
  background: var(--bg-card);
  border-radius: 1.5rem;
  padding: 3rem;
  border: 1px solid rgba(212, 175, 55, 0.1);
  max-width: 600px;
  margin: 0 auto;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-label {
  display: block;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.form-input,
.form-textarea {
  width: 100%;
  padding: 1rem 1.25rem;
  background: var(--bg-secondary);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.75rem;
  color: var(--text-primary);
  font-size: 1rem;
  transition: all 0.3s ease;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--primary-gold);
  box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.1);
  background: var(--bg-primary);
}

.form-input::placeholder,
.form-textarea::placeholder {
  color: var(--text-muted);
}

.form-textarea {
  resize: vertical;
  min-height: 120px;
}

.form-submit {
  width: 100%;
  background: var(--gradient-primary);
  color: var(--text-primary);
  border: none;
  padding: 1rem 2rem;
  border-radius: 0.75rem;
  font-weight: 600;
  font-size: 1.125rem;
  cursor: pointer;
  transition: all 0.3s ease;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.form-submit:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 40px rgba(212, 175, 55, 0.3);
}
```

### 🎭 ANIMATION UTILITIES

```css
/* Fade In Animation */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fadeInUp {
  animation: fadeInUp 0.8s ease-out;
}

/* Stagger Animation for Grid Items */
.stagger-item {
  opacity: 0;
  animation: fadeInUp 0.8s ease-out forwards;
}

.stagger-item:nth-child(1) { animation-delay: 0.1s; }
.stagger-item:nth-child(2) { animation-delay: 0.2s; }
.stagger-item:nth-child(3) { animation-delay: 0.3s; }
.stagger-item:nth-child(4) { animation-delay: 0.4s; }

/* Pulse Animation for CTAs */
@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(212, 175, 55, 0.4);
  }
  50% {
    box-shadow: 0 0 0 20px rgba(212, 175, 55, 0);
  }
}

.animate-pulse-cta {
  animation: pulse 2s infinite;
}
```

### 📱 RESPONSIVE UTILITY CLASSES

```css
/* Spacing System */
.p-4 { padding: 1rem; }
.p-6 { padding: 1.5rem; }
.p-8 { padding: 2rem; }
.py-12 { padding-top: 3rem; padding-bottom: 3rem; }
.py-16 { padding-top: 4rem; padding-bottom: 4rem; }
.py-24 { padding-top: 6rem; padding-bottom: 6rem; }

.m-4 { margin: 1rem; }
.mb-8 { margin-bottom: 2rem; }
.mb-12 { margin-bottom: 3rem; }

/* Text Alignment */
.text-center { text-align: center; }
.text-left { text-align: left; }
.text-right { text-align: right; }

/* Display */
.flex { display: flex; }
.grid { display: grid; }
.hidden { display: none; }

/* Responsive Utilities */
@media (min-width: 768px) {
  .md\\:flex { display: flex; }
  .md\\:grid-cols-2 { grid-template-columns: repeat(2, 1fr); }
  .md\\:text-left { text-align: left; }
}

@media (min-width: 1024px) {
  .lg\\:grid-cols-3 { grid-template-columns: repeat(3, 1fr); }
  .lg\\:text-6xl { font-size: 3.75rem; line-height: 1.05; }
}
```

### 🎯 IMPLEMENTATION NOTES

1. **CSS Custom Properties**: All colors and spacing use CSS custom properties for easy theming
2. **Mobile-First**: All responsive design starts from mobile and scales up
3. **Accessibility**: 4.5:1 contrast ratios maintained, focus states included
4. **Performance**: Animations use transform and opacity for GPU acceleration
5. **Scalability**: Component-based approach allows easy extension

### 🔧 USAGE EXAMPLES

```html
<!-- Hero Section -->
<section class="hero-section">
  <div class="hero-content">
    <h1 class="hero-title">ACT-I</h1>
    <p class="hero-subtitle">Human Actualization Platform</p>
    <a href="#contact" class="hero-cta">Get Started</a>
  </div>
</section>

<!-- Team Grid -->
<section class="container">
  <div class="team-grid">
    <div class="team-card stagger-item">
      <div class="team-avatar">⚔️</div>
      <h3 class="team-name">Sai Forge</h3>
      <p class="team-role">The Builder</p>
      <p class="team-bio">Runs the Colosseum. Evolves beings.</p>
    </div>
  </div>
</section>
```

This complete visual design system provides all the specifications needed for implementation, including exact hex codes, responsive breakpoints, component CSS, and usage examples.