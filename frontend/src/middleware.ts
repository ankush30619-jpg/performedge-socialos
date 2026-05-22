import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Auth is temporarily disabled.
 * All routes are publicly accessible.
 * Just redirect bare "/" → "/dashboard".
 */
export function middleware(req: NextRequest) {
  if (req.nextUrl.pathname === "/") {
    return NextResponse.redirect(new URL("/dashboard", req.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
