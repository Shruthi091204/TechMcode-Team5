import { NextResponse } from "next/server";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ scenario: string }> }
) {
  const { scenario } = await params;
  const backend = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  try {
    const res = await fetch(`${backend}/replay/${scenario}`, {
      method: "POST",
    });
    if (!res.ok) {
      return NextResponse.json(
        { error: `Backend returned status ${res.status}` },
        { status: res.status }
      );
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { error: "Scenario not available yet (backend offline)" },
      { status: 503 }
    );
  }
}

