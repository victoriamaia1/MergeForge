export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["JetBrains Mono", "monospace"],
        body: ["IBM Plex Sans", "system-ui", "sans-serif"]
      },
      colors: {
        ink: "#0a0f0d",
        panel: "#101814",
        edge: "#1c2a22",
        line: "#243530",
        accent: "#a3e635",   // lime
        accent2: "#fb923c",  // orange
        muted: "#8aa19a"
      }
    }
  },
  plugins: []
}
