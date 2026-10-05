import { NextResponse, type NextRequest } from "next/server";
import { jwtVerify } from "jose";

/**
 * Role-based route protection (§10).
 * Verifies the JWT (HS256) from the `spa_token` cookie and enforces the
 * /student, /faculty, /admin prefixes. The backend remains the real
 * authorization boundary — this middleware is for redirect UX.
 */
const SECRET = new TextEncoder().encode(process.env.JWT_SECRET ?? "change-me-in-real-environments");

const ROLE_PREFIX: Record<string, string> = {
  STUDENT: "/student",
  FACULTY: "/faculty",
  ADMIN: "/admin",
};

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get("spa_token")?.value;

  const area = ["/student", "/faculty", "/admin"].find((p) => pathname.startsWith(p));
  const isAuthPage = pathname === "/login" || pathname === "/register";

  let role: string | null = null;
  if (token) {
    try {
      const { payload } = await jwtVerify(token, SECRET);
      role = (payload.role as string) ?? null;
    } catch {
      role = null; // invalid/expired token — treat as logged out
    }
  }

  // logged-in users on auth pages -> their dashboard
  if (isAuthPage && role && ROLE_PREFIX[role]) {
    return NextResponse.redirect(new URL(ROLE_PREFIX[role] + "/dashboard", request.url));
  }

  // protected area without a valid session -> login
  if (area && !role) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // wrong role in an area -> own dashboard
  if (area && role && ROLE_PREFIX[role] && !pathname.startsWith(ROLE_PREFIX[role])) {
    return NextResponse.redirect(new URL(ROLE_PREFIX[role] + "/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/student/:path*", "/faculty/:path*", "/admin/:path*", "/login", "/register"],
};
