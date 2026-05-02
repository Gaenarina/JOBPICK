/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
<<<<<<< HEAD
    './src/app/**/*.{js,ts,jsx,tsx}',
    './src/components/**/*.{js,ts,jsx,tsx}',
=======
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
>>>>>>> origin/frontend
  ],
  theme: {
    extend: {
      colors: {
<<<<<<< HEAD
        primary: '#2563eb',
        'primary-dark': '#1d4ed8',
=======
        primary: {
          DEFAULT: '#2563eb',
          light: '#3b82f6',
          dark: '#1d4ed8',
        },
      },
      fontFamily: {
        sans: ['Noto Sans KR', 'sans-serif'],
>>>>>>> origin/frontend
      },
    },
  },
  plugins: [],
<<<<<<< HEAD
}
=======
}
>>>>>>> origin/frontend
