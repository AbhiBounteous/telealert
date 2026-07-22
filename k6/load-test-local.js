import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

const eventsCreated = new Counter('events_created');
const errorRate = new Rate('error_rate');

export const options = {
  stages: [
    { duration: '20s', target: 3 },
    { duration: '40s', target: 5 },
    { duration: '20s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = 'http://localhost:5001';
const severities = ['low', 'medium', 'high', 'critical'];
const nodeIds = [
  'NODE-MUM-001', 'NODE-DEL-001',
  'NODE-BLR-001', 'NODE-HYD-001',
];

export default function () {
  const severity = severities[
    Math.floor(Math.random() * severities.length)
  ];
  const nodeId = nodeIds[
    Math.floor(Math.random() * nodeIds.length)
  ];

  const res = http.post(
    `${BASE_URL}/event`,
    JSON.stringify({
      node_id: nodeId,
      severity: severity,
      message: `Network anomaly on ${nodeId}`,
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  const success = check(res, {
    'status 200': (r) => r.status === 200,
    'event received': (r) => {
      try { return r.json('status') === 'received'; }
      catch { return false; }
    },
  });

  errorRate.add(!success);
  if (success) eventsCreated.add(1);

  sleep(2);
}
