---
name: Sahara — Editorial Precision
colors:
  surface: '#fef9f2'
  surface-dim: '#ded9d3'
  surface-bright: '#fef9f2'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f8f3ec'
  surface-container: '#f2ede6'
  surface-container-high: '#ece7e1'
  surface-container-highest: '#e6e2db'
  on-surface: '#1d1c18'
  on-surface-variant: '#554339'
  inverse-surface: '#32302c'
  inverse-on-surface: '#f5f0e9'
  outline: '#887368'
  outline-variant: '#dbc1b5'
  surface-tint: '#99460a'
  primary: '#964407'
  on-primary: '#ffffff'
  primary-container: '#b65c21'
  on-primary-container: '#fffbff'
  inverse-primary: '#ffb68e'
  secondary: '#974544'
  on-secondary: '#ffffff'
  secondary-container: '#fe9794'
  on-secondary-container: '#782c2d'
  tertiary: '#006480'
  on-tertiary: '#ffffff'
  tertiary-container: '#007ea1'
  on-tertiary-container: '#fbfdff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdbca'
  primary-fixed-dim: '#ffb68e'
  on-primary-fixed: '#331200'
  on-primary-fixed-variant: '#773300'
  secondary-fixed: '#ffdad8'
  secondary-fixed-dim: '#ffb3b0'
  on-secondary-fixed: '#3f0308'
  on-secondary-fixed-variant: '#792e2f'
  tertiary-fixed: '#bce9ff'
  tertiary-fixed-dim: '#70d2fa'
  on-tertiary-fixed: '#001f2a'
  on-tertiary-fixed-variant: '#004d63'
  background: '#fef9f2'
  on-background: '#1d1c18'
  surface-variant: '#e6e2db'
  accent-mint: '#15BE74'
  accent-coral: '#FF6158'
  warm-border: '#d8d0c8'
  deep-obsidian: '#000000'
typography:
  display-lg:
    fontFamily: EB Garamond
    fontSize: 64px
    fontWeight: '500'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: EB Garamond
    fontSize: 48px
    fontWeight: '400'
    lineHeight: '1.2'
  headline-md:
    fontFamily: EB Garamond
    fontSize: 32px
    fontWeight: '400'
    lineHeight: '1.3'
  headline-sm:
    fontFamily: EB Garamond
    fontSize: 24px
    fontWeight: '400'
    lineHeight: '1.4'
  body-lg:
    fontFamily: DM Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: DM Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-caps:
    fontFamily: Space Mono
    fontSize: 12px
    fontWeight: '700'
    lineHeight: '1.0'
    letterSpacing: 0.1em
  headline-lg-mobile:
    fontFamily: EB Garamond
    fontSize: 36px
    fontWeight: '400'
    lineHeight: '1.2'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 8px
  container-max: 1280px
  gutter: 32px
  margin-mobile: 20px
  section-padding: 120px
  stack-sm: 16px
  stack-md: 32px
  stack-lg: 64px
---

## Brand & Style
The design system evolves into a high-end, editorial framework that marries "Sun-Baked Simplicity" with the rigorous structural discipline of a modern fintech platform. The brand personality is authoritative yet welcoming, using generous whitespace and a rhythmic padding system to convey a sense of calm control.

The aesthetic follows a **Modern Editorial** movement: it utilizes the warmth of the Sahara palette but applies it to the precise, data-rich layout patterns found in enterprise-grade software. The result is a UI that feels curated and intellectual, shifting away from "soft lifestyle" toward "high-performance luxury."

## Colors
The palette is anchored by a warm linen background, ensuring the UI never feels sterile. 

- **Primary:** Burnt Sienna is used for critical action paths and brand moments.
- **Secondary:** Dusty Rose serves as a sophisticated accent for secondary highlights.
- **Functional Accents:** Inspired by the reference, a vibrant mint and coral are introduced sparingly for semantic status indicators (success/error), but are slightly desaturated to maintain the warm aesthetic.
- **Neutrality:** Grays are strictly warm-toned to prevent visual jarring against the linen base.

## Typography
The typography scale is the primary engine of the editorial feel. 

- **Display & Headlines:** EB Garamond provides a literary, established tone. Use tight leading for larger sizes to create a "locked" visual block.
- **Body:** DM Sans offers a neutral, geometric clarity that balances the expressive serif.
- **Metadata:** Space Mono is used for labels, captions, and technical data points, nodding to the precision of the reference's structural principles.

## Layout & Spacing
This design system utilizes a **Fixed Grid** with an emphasis on vertical rhythm and "air." 

- **The 8px Grid:** All internal component padding and spacing must be multiples of 8px. 
- **Editorial Margins:** Content containers should never exceed 1280px to maintain line-length readability.
- **Rhythmic Padding:** Sections are separated by generous vertical stacks (up to 120px) to force a slow, intentional scroll. 
- **Reflow:** On mobile, margins tighten to 20px, and section padding reduces to 64px, but the "breathability" of the layout is maintained by increasing the space between text blocks.

## Elevation & Depth
Depth is achieved through **Tonal Layers** and subtle outlines rather than heavy shadows.

- **Surface Levels:** Use the primary background (#faf5ee) for the base, and a pure white (#FFFFFF) for cards or elevated containers to create a "lifted" appearance without shadow.
- **Outlines:** Use 1px borders in `warm-border` at low opacity to define boundaries.
- **Shadows:** When necessary for floating elements (modals, dropdowns), use a wide, diffused "Ambient Shadow" with a warm tint: `0 12px 40px rgba(58, 48, 42, 0.08)`.

## Shapes
Shapes are disciplined and "Soft." 

A uniform 4px corner radius (`roundedness: 1`) is applied to buttons, input fields, and small UI components. Larger containers like cards should not exceed 8px. This creates a crisp, architectural silhouette that feels more precise than round, "friendly" UI styles.

## Components
- **Buttons:** Primary buttons use a solid Burnt Sienna fill with 4px radius and `label-caps` typography in white. Secondary buttons use a `warm-border` outline with text in Deep Obsidian.
- **Chips:** Small, pill-shaped tags using Space Mono at 10px. Use very light tints of Primary or Secondary colors for background fills.
- **Lists:** Data lists utilize generous vertical padding (24px per row) with a single-pixel bottom border. No icons unless they serve a functional semantic purpose.
- **Input Fields:** Minimalist design with a 1px `warm-border` on all sides. On focus, the border transitions to Burnt Sienna. Labels use `label-caps` and sit outside the field.
- **Cards:** White background with 32px internal padding. No shadows; use a subtle 1px border for definition against the linen background.
- **Navigational Elements:** Simple text links using DM Sans. Underline decoration appears only on hover, using a 2px offset Burnt Sienna line.