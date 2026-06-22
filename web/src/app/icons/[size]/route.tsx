import { ImageResponse } from "next/og";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ size: string }> }
) {
  const { size: sizeParam } = await params;
  const size = sizeParam === "192" ? 192 : 512;
  const fontSize = Math.round(size * 0.38);
  const subSize = Math.round(size * 0.14);
  const gap = Math.round(size * 0.02);
  const radius = Math.round(size * 0.18);

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
          borderRadius: radius,
        }}
      >
        <span
          style={{
            color: "white",
            fontSize,
            fontWeight: 800,
            fontFamily: "sans-serif",
            letterSpacing: Math.round(-fontSize * 0.06),
            lineHeight: 1,
          }}
        >
          SE
        </span>
        <span
          style={{
            color: "rgba(255,255,255,0.65)",
            fontSize: subSize,
            fontFamily: "sans-serif",
            marginTop: gap,
          }}
        >
          ⚾
        </span>
      </div>
    ),
    { width: size, height: size }
  );
}
