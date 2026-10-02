import assert from 'node:assert/strict';
import { decodeJWTPayload, isSupportedTenantId, tenantIdFromClaims } from './jwtUtils.ts';

const payload = Buffer.from(JSON.stringify({
  email: 'sunset@propertyflow.com',
  app_metadata: { tenant_id: 'tenant-a' },
  user_metadata: { name: 'Sunset Properties Manager ???' },
})).toString('base64url');

const claims = decodeJWTPayload(`header.${payload}.signature`);

assert.equal(tenantIdFromClaims(claims), 'tenant-a');
assert.equal(isSupportedTenantId('tenant-b'), true);
assert.equal(isSupportedTenantId('11111111-1111-1111-1111-111111111111'), true);
assert.equal(tenantIdFromClaims({ tenant_id: 'not a tenant' }), null);
assert.equal(tenantIdFromClaims({ user_metadata: { tenant_id: 'tenant-b' } }), 'tenant-b');

console.log('jwt tenant claims ok');
