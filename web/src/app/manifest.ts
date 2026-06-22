import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "SharpEdge",
    short_name: "SharpEdge",
    description:
      "Calibrated MLB & soccer probability picks graded against the closing line. Every call, every grade, published.",
    start_url: "/",
    display: "standalone",
    background_color: "#07111f",
    theme_color: "#ff5c6c",
    icons: [
      { src: "/icons/192", sizes: "192x192", type: "image/png" },
      { src: "/icons/512", sizes: "512x512", type: "image/png" },
    ],
  };
}
