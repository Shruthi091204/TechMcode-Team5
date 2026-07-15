import { NextResponse } from "next/server";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ scenario: string }> }
) {
  const { scenario } = await params;
  try {
    const res = await fetch(`http://127.0.0.1:8000/replay/${scenario}`, {
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
  } catch (err) {
    return NextResponse.json(
      { error: "Scenario not available yet (backend offline)" },
      { status: 503 }
    );
  }
}

