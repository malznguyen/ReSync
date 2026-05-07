import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: {
    control_api_read_mix: {
      executor: "ramping-vus",
      stages: [
        { duration: "30s", target: 10 },
        { duration: "1m", target: 25 },
        { duration: "30s", target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500"],
  },
};

const BASE_URL = (
  __ENV.E2E_API_BASE_URL ||
  __ENV.API_BASE_URL ||
  "http://localhost:8000"
).replace(/\/$/, "");
const USERNAME = __ENV.E2E_API_USERNAME || __ENV.API_ADMIN_USERNAME || "admin";
const PASSWORD = __ENV.E2E_API_PASSWORD || __ENV.API_ADMIN_PASSWORD;

export function setup() {
  if (!PASSWORD) {
    throw new Error("Set E2E_API_PASSWORD or API_ADMIN_PASSWORD before running k6.");
  }

  const response = http.post(
    `${BASE_URL}/auth/token`,
    { username: USERNAME, password: PASSWORD },
    { headers: { "Content-Type": "application/x-www-form-urlencoded" } },
  );

  check(response, {
    "auth token issued": (res) => res.status === 200 && Boolean(res.json("access_token")),
  });

  return { token: response.json("access_token") };
}

export default function (data) {
  const authParams = {
    headers: {
      Authorization: `Bearer ${data.token}`,
    },
  };

  const responses = http.batch([
    ["GET", `${BASE_URL}/health`, null, {}],
    ["GET", `${BASE_URL}/cameras?limit=100`, null, authParams],
    ["GET", `${BASE_URL}/zones?limit=100`, null, authParams],
    ["GET", `${BASE_URL}/webhooks?limit=100`, null, authParams],
    ["GET", `${BASE_URL}/analytics/events?limit=100`, null, authParams],
    ["GET", `${BASE_URL}/analytics/visits?limit=100`, null, authParams],
  ]);

  check(responses[0], { "health ok": (res) => res.status === 200 });
  check(responses[1], { "cameras ok": (res) => res.status === 200 });
  check(responses[2], { "zones ok": (res) => res.status === 200 });
  check(responses[3], { "webhooks ok": (res) => res.status === 200 });
  check(responses[4], { "events ok": (res) => res.status === 200 });
  check(responses[5], { "visits ok": (res) => res.status === 200 });

  sleep(0.2 + Math.random() * 0.8);
}
