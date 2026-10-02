/**
 * JWT Token Utilities for Supabase Session Handling
 * Extracts custom claims (like tenant_id) from JWT access tokens
 */

interface JWTClaims {
  sub?: string; // user ID
  email?: string;
  role?: string;
  tenant_id?: string; // Custom claim added by backend hook
  app_metadata?: { tenant_id?: string; [key: string]: any };
  user_metadata?: { tenant_id?: string; [key: string]: any };
  exp?: number;
  iat?: number;
  [key: string]: any;
}

const UUID_TENANT = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const SLUG_TENANT = /^[a-z0-9][a-z0-9_-]{0,63}$/i;

export function isSupportedTenantId(tenantId: string): boolean {
  return typeof tenantId === 'string' && (UUID_TENANT.test(tenantId) || SLUG_TENANT.test(tenantId));
}

export function tenantIdFromClaims(claims: JWTClaims | null): string | null {
  if (!claims) return null;
  const candidates = [
    claims.tenant_id,
    claims.app_metadata?.tenant_id,
    claims.user_metadata?.tenant_id,
  ];
  for (const value of candidates) {
    if (typeof value === 'string' && isSupportedTenantId(value)) {
      return value;
    }
  }
  return null;
}

/**
 * Decode JWT token payload without verification (client-side only)
 * WARNING: This is for reading claims only, never for security validation
 */
export function decodeJWTPayload(token: string): JWTClaims | null {
  try {
    // JWT has 3 parts separated by dots: header.payload.signature
    const parts = token.split('.');
    if (parts.length !== 3) {
      console.warn('[JWT] Invalid token format');
      return null;
    }

    // Get the payload (middle part)
    const payload = parts[1];
    
    // Add padding if needed for base64 decoding. JWTs use base64url.
    const paddedPayload = payload + '=='.substring(0, (4 - (payload.length % 4)) % 4);
    const base64Payload = paddedPayload.replace(/-/g, '+').replace(/_/g, '/');
    
    // Decode base64 and parse JSON
    const decodedBytes = atob(base64Payload);
    const claims = JSON.parse(decodedBytes) as JWTClaims;
    
    return claims;
  } catch (error) {
    console.error('[JWT] Failed to decode token payload:', error);
    return null;
  }
}

/**
 * Extract tenant_id from Supabase session JWT claims
 */
export function extractTenantFromSession(session: any): string | null {
  if (!session?.access_token) {
    return null;
  }

  try {
    const claims = decodeJWTPayload(session.access_token);
    const tenantId = tenantIdFromClaims(claims);
    
    if (tenantId) {
      if (import.meta.env.DEV) {
        console.log('[JWT] Extracted tenant_id from claims:', tenantId);
      }
      return tenantId;
    }
    
    return null;
  } catch (error) {
    console.error('[JWT] Error extracting tenant from session:', error);
    return null;
  }
}

/**
 * Get all custom claims from JWT token
 */
export function getCustomClaims(token: string): Record<string, any> {
  const claims = decodeJWTPayload(token);
  if (!claims) return {};
  
  // Filter out standard JWT claims to get custom ones
  const standardClaims = ['sub', 'exp', 'iat', 'iss', 'aud', 'email', 'role', 'email_confirmed_at'];
  const customClaims: Record<string, any> = {};
  
  Object.entries(claims).forEach(([key, value]) => {
    if (!standardClaims.includes(key)) {
      customClaims[key] = value;
    }
  });
  
  return customClaims;
}