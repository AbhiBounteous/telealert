import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

const eventsCreated = new Counter('events_created');
const errorRate = new Rate('error_rate');
const eventDuration = new Trend('event_duration');

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m',  target: 50 },
    { duration: '1m',  target: 100 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration:    ['p(95)<1000'],
    http_req_failed:      ['rate<0.05'],
    error_rate:           ['rate<0.05'],
  },
};

const BASE_URL = 'http://localhost:5001';

const severities = ['low', 'medium', 'high', 'critical'];
const nodeIds = [
  'NODE-MUM-001', 'NODE-MUM-002', 'NODE-DEL-001',
  'NODE-BLR-001', 'NODE-HYD-001', 'NODE-CHN-001',
];

export default function () {
  const severity = severities[
    Math.floor(Math.random() * severities.length)
  ];
  const nodeId = nodeIds[
    Math.floor(Math.random() * nodeIds.length)
  ];

  const payload = JSON.stringify({
    node_id: nodeId,
    severity: severity,
    message: `Network anomaly detected on ${nodeId}`,
  });

  const start = Date.now();
  const res = http.post(
    `${BASE_URL}/event`,
    payload,
    { headers: { 'Content-Type': 'application/json' } }
  );
  const duration = Date.now() - start;

  const success = check(res, {
    'status 200': (r) => r.status === 200,
    'event received': (r) => {
      try {
        return r.json('status') === 'received';
      } catch {
        return false;
      }
    },
  });

  eventDuration.add(duration);
  errorRate.add(!success);

  if (success) {
    eventsCreated.add(1);
  }

  sleep(Math.random() * 2);
}

export function handleSummary(data) {
  return {
    'stdout': JSON.stringify({
      totalRequests: data.metrics.http_reqs.values.count,
      failedRequests: data.metrics.http_req_failed.values.passes,
      p95ResponseTime: data.metrics.http_req_duration.values['p(95)'],
      eventsCreated: data.metrics.events_created
        ? data.metrics.events_created.values.count : 0,
    }, null, 2),
  };
}
