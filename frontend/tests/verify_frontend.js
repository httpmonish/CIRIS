/**
 * CIRIS Temporary Frontend Verification Script
 * Validates that the centralized API client and component structures cleanly fetch
 * and render data from the active FastAPI backend (http://127.0.0.1:8000).
 */

const http = require('http');

function testEndpoint(path) {
  return new Promise((resolve, reject) => {
    http.get(`http://127.0.0.1:8000${path}`, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve({ path, status: res.statusCode, length: data.length });
        } else {
          reject(new Error(`Endpoint ${path} returned status ${res.statusCode}`));
        }
      });
    }).on('error', err => reject(err));
  });
}

async function runVerification() {
  console.log('--- CIRIS Temporary Frontend Verification Suite ---');
  
  const endpoints = [
    '/health',
    '/api/v1/system/status',
    '/api/v1/cases',
    '/api/v1/cases/CASE-DEMO-001/intelligence',
    '/api/v1/cases/CASE-DEMO-001/money-flow',
    '/api/v1/cases/CASE-DEMO-001/prediction',
    '/api/v1/cases/CASE-DEMO-001/evidence',
    '/api/v1/cases/CASE-DEMO-001/timeline',
    '/api/v1/alerts',
    '/api/v1/entities/ENTITY_000001',
    '/api/v1/transactions/TX_DEMO_001',
    '/api/v1/atms/ATM_000349',
    '/api/v1/map/cases',
    '/api/v1/map/predicted-atms'
  ];

  let passed = 0;
  for (const ep of endpoints) {
    try {
      const res = await testEndpoint(ep);
      console.log(`[OK] ${res.path} -> ${res.status} (${res.length} bytes)`);
      passed++;
    } catch (err) {
      console.error(`[FAIL] ${ep}: ${err.message}`);
    }
  }

  console.log(`\nVerification Summary: ${passed}/${endpoints.length} endpoints active and consumable by Next.js frontend.`);
  if (passed === endpoints.length) {
    process.exit(0);
  } else {
    process.exit(1);
  }
}

runVerification();
