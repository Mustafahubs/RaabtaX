---
name: Obsidian Flux
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#8c909f'
  outline-variant: '#424754'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e6a'
  primary-container: '#4d8eff'
  on-primary-container: '#00285d'
  inverse-primary: '#005ac2'
  secondary: '#b9c7e0'
  on-secondary: '#233144'
  secondary-container: '#3c4a5e'
  on-secondary-container: '#abb9d2'
  tertiary: '#4ae176'
  on-tertiary: '#003915'
  tertiary-container: '#00a74b'
  on-tertiary-container: '#003111'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#d5e3fd'
  secondary-fixed-dim: '#b9c7e0'
  on-secondary-fixed: '#0d1c2f'
  on-secondary-fixed-variant: '#3a485c'
  tertiary-fixed: '#6bff8f'
  tertiary-fixed-dim: '#4ae176'
  on-tertiary-fixed: '#002109'
  on-tertiary-fixed-variant: '#005321'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
  title-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-lg:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.1px
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 16px
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  margin-horizontal: 1rem
  gutter: 0.5rem
  stack-sm: 0.25rem
  stack-md: 0.75rem
  stack-lg: 1.5rem
  touch-target: 3rem
---

## Brand & Style

The design system is engineered for a premium, high-fidelity mobile chat experience. It targets a tech-savvy audience that values focus, privacy, and visual depth. The brand personality is professional yet fluid, utilizing a **Corporate Modern** foundation infused with subtle **Glassmorphism** to create a sense of layered sophistication.

The UI should evoke a sense of calm and precision. By leveraging a deep, monochromatic base with vibrant functional accents, the design system ensures that content—the user's conversations—remains the primary focus while the interface recedes into a supportive, high-end background.

## Colors

The color palette is built on a "Deep Sea" dark mode logic. 
- **Primary (#3b82f6):** Used for actionable items, active states, and outgoing message bubbles to ensure high visibility.
- **Secondary (#334155):** Reserved for inactive states, secondary surfaces, and neutral message bubbles.
- **Tertiary (#22c55e):** Specifically for "Online" status indicators and success states.
- **Neutral/Background (#0f172a):** The primary canvas color, providing a high-contrast base for slate surfaces.

The system utilizes a hierarchical layering of grays: `#0f172a` for the main background, `#1e293b` for top-level surfaces like cards and headers, and `#334155` for interactive elements or borders.

## Typography

This design system utilizes **Inter** exclusively to achieve a systematic, utilitarian aesthetic that remains highly legible at small scales typical of mobile chat. 

Headlines use tighter letter spacing and heavier weights to establish a clear hierarchy against the dark background. Body text maintains standard tracking for maximum readability. All type is rendered in high-contrast off-whites (`#f8fafc`) or muted grays (`#94a3b8`) depending on the information's importance.

## Layout & Spacing

Following Material Design 3 rhythms, the layout uses an 8dp grid system. 
- **Margins:** Standard mobile views use 16px (1rem) horizontal margins. 
- **Gutter:** Elements within a group (like avatars next to bubbles) use 8px (0.5rem) spacing.
- **Chat Flow:** Messages from the same user are clustered with 4px spacing, while different users are separated by 12px to 16px.
- **Reflow:** On tablets, the chat interface transitions into a master-detail view, with the contact list pinned to the left (320px width) and the active conversation filling the remaining fluid space.

## Elevation & Depth

Depth is established through **Tonal Layers** rather than heavy shadows. 
- **Level 0 (Background):** `#0f172a` — The base layer.
- **Level 1 (Cards/Inputs):** `#1e293b` — Raised slightly with a 1px subtle stroke of `#334155`.
- **Level 2 (Modals/Popovers):** `#334155` — Elevated with a soft, diffused shadow (`0 10px 15px -3px rgba(0, 0, 0, 0.5)`).

For specific interactive elements like the message input bar, use a 20px Backdrop Blur (15%) over the content to maintain a sense of place within the scrollable thread.

## Shapes

The design system employs a **Pill-shaped** strategy to soften the high-tech aesthetic and make the app feel more approachable. 
- **Message Bubbles:** 18px radius on corners, with "tail" corners sharpening to 4px to indicate the speaker.
- **Action Buttons & Inputs:** Use full pill-shaping (height/2) for a modern, tactile feel.
- **Avatars:** Strictly circular (50% radius) to contrast with the rectangular/pill shapes of the chat interface.

## Components

- **Message Bubbles:** Outgoing bubbles use the Primary color with white text. Incoming bubbles use the Surface Slate color with high-contrast neutral text.
- **Pill Inputs:** The message composer should be a 48px height pill with a 1px border. Use a "ghost" style when inactive and a primary border when focused.
- **Chips:** Used for "Quick Replies" or filters. These should be low-profile with `#1e293b` backgrounds and 16px roundedness.
- **Status Indicators:** A 10px Tertiary green circle, positioned at the bottom-right of avatars, with a 2px border matching the background color to create "cutout" separation.
- **Lists:** Contact lists use 72px row heights with 16px horizontal padding. Separators should be 1px lines using the `#334155` color at 50% opacity.
- **Floating Action Button (FAB):** If used, it must be the Primary color, circular, with a centered icon and Level 2 elevation shadows.