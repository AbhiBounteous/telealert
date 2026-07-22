import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m',  target: 100  },
    { duration: '2m',  target: 500  },
    { duration: '2m',  target: 1000 },
    { duration: '1m',  target: 500  },
    { duration: '1m',  target: 0    },
  ],
  thresholds: {
    http_req_duration: ['p(99)<3000'],
    http_req_failed:   ['rate<0.10'],
  },
};

const BASE_URL = 'http://localhost:5001';

export default function () {
  const res = http.post(
    `${BASE_URL}/event`,
    JSON.stringify({
      node_id: `STRESS-${__VU}`,
      severity: 'high',
      message: `Stress test VU ${__VU}`,
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  check(res, {
    'status 200': (r) => r.status === 200,
  });

  sleep(1);
}
