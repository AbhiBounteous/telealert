import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 5,
  duration: '30s',
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = 'http://localhost:5001';

export default function () {
  // Test 1: Health check
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health status 200': (r) => r.status === 200,
    'health response time < 100ms': (r) => r.timings.duration < 100,
  });

  // Test 2: Send event
  const payload = JSON.stringify({
    node_id: `NODE-K6-${__VU}-${__ITER}`,
    severity: 'critical',
    message: `Load test event VU=${__VU} iter=${__ITER}`,
  });

  const eventRes = http.post(
    `${BASE_URL}/event`,
    payload,
    { headers: { 'Content-Type': 'application/json' } }
  );

  check(eventRes, {
    'event status 200': (r) => r.status === 200,
    'event received': (r) => r.json('status') === 'received',
    'event response time < 500ms': (r) => r.timings.duration < 500,
  });

  // Test 3: Get alerts
  const alertsRes = http.get(`${BASE_URL}/alerts`);
  check(alertsRes, {
    'alerts status 200': (r) => r.status === 200,
  });

  sleep(1);
}
