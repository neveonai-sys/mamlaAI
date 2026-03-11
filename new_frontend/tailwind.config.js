/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./src/**/*.{js,jsx,ts,tsx}', './public/index.html'],
  theme: {
    extend: {
      colors: {
        primary: '#b45e08',
        'primary-dark': '#8f4a06',
        'background-light': '#f8f7f5',
        'background-dark': '#221910',
        ink: '#1c140d',
        ivory: '#fcfaf8',
        'ivory-dark': '#f0ede8',
      },
      fontFamily: {
        display: ['Inter', 'sans-serif'],
        serif: ['Lora', 'serif'],
      },
      borderRadius: {
        DEFAULT: '0.25rem',
        lg: '0.5rem',
        xl: '0.75rem',
        '2xl': '1rem',
        full: '9999px',
      },
      boxShadow: {
        subtle: '0 1px 3px 0 rgba(28,20,13,0.05), 0 1px 2px -1px rgba(28,20,13,0.05)',
        card: '0 4px 6px -1px rgba(28,20,13,0.07), 0 2px 4px -2px rgba(28,20,13,0.07)',
        elevated: '0 10px 15px -3px rgba(28,20,13,0.1), 0 4px 6px -4px rgba(28,20,13,0.1)',
      },
      animation: {
        'ping-slow': 'ping 2s cubic-bezier(0,0,0.2,1) infinite',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms')({ strategy: 'class' }),
    require('@tailwindcss/container-queries'),
  ],
};
