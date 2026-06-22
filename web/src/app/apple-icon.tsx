import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "#ff5c6c",
        }}
      >
        <span
          style={{
            color: "white",
            fontSize: 80,
            fontWeight: 800,
            fontFamily: "sans-serif",
            letterSpacing: "-4px",
            lineHeight: 1,
          }}
        >
          SE
        </span>
        <span
          style={{
            color: "rgba(255,255,255,0.65)",
            fontSize: 26,
            fontFamily: "sans-serif",
            marginTop: 4,
          }}
        >
          ⚾
        </span>
      </div>
    ),
    size
  );
}
