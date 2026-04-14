"""
Survivor Network — Disaster Scenario Load Test

Simulates N concurrent survivors hitting the chatbot service during a mass
crisis event. Each simulated survivor starts a session, sends 3-5 messages,
and submits their case.

Usage:
    python disaster_sim.py --users 100 --ramp-up 60
    python disaster_sim.py --users 5 --ramp-up 5
"""

import argparse
import asyncio
import json
import random
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import aiohttp

PERSONAS: list[dict[str, Any]] = [
    {"urgency": "critical", "messages": [
        "I'm bleeding badly, someone stabbed me outside the taxi rank",
        "I'm in Diepkloof, near the shopping centre",
        "Yes I'm in danger, the person is still nearby",
        "I'm injured, bleeding from my side",
        "Please send help, I can barely stand. You can call me",
    ], "location": {"latitude": -26.2425, "longitude": 27.8960}},
    {"urgency": "critical", "messages": [
        "My husband is beating me right now, I locked myself in the bathroom",
        "I'm in Tembisa, Extension 2",
        "He has a knife, I'm terrified",
        "I'm not injured yet but he's trying to break the door",
        "WhatsApp is safest, he checks my calls",
    ], "location": {"latitude": -26.0010, "longitude": 28.2268}},
    {"urgency": "critical", "messages": [
        "There was a building collapse, people are trapped",
        "We're in Alexandra, near the bridge on London Road",
        "Multiple people injured, I can see blood",
        "I need emergency medical help, someone is unconscious",
        "Call is fine, please hurry",
    ], "location": {"latitude": -26.1076, "longitude": 28.0893}},
    {"urgency": "critical", "messages": [
        "I took too many pills, I don't want to be here anymore",
        "I'm at home in Soweto, Orlando West",
        "I'm alone and scared",
        "I feel dizzy and nauseous",
        "Text me please, I can barely talk",
    ], "location": {"latitude": -26.2285, "longitude": 27.9050}},
    {"urgency": "high", "messages": [
        "I was raped last night, I don't know what to do",
        "I'm in Hillbrow, I managed to get to a friend's place",
        "I'm not in danger right now but I'm terrified to go outside",
        "I'm injured, I need to see a doctor",
        "WhatsApp only, I don't want anyone to hear",
    ], "location": {"latitude": -26.1920, "longitude": 28.0480}},
    {"urgency": "high", "messages": [
        "My ex threatened to kill me, he knows where I live",
        "I'm in Mamelodi East, Pretoria",
        "I need a protection order and somewhere safe to stay",
        "I'm not injured but I'm very afraid",
        "You can text me on WhatsApp",
    ], "location": {"latitude": -25.7200, "longitude": 28.3960}},
    {"urgency": "high", "messages": [
        "My child was beaten at school and has a head injury",
        "We're in Katlehong, near the clinic",
        "He's conscious but confused and has a bump",
        "I need medical help for him urgently",
        "Call me, I have airtime",
    ], "location": {"latitude": -26.3450, "longitude": 28.1510}},
    {"urgency": "high", "messages": [
        "Someone is holding my sister against her will",
        "She's in Sunnyside, Pretoria, in a flat on Esselen Street",
        "The man won't let her leave, she called me crying",
        "I don't know if she's injured",
        "Call me anytime",
    ], "location": {"latitude": -25.7560, "longitude": 28.2090}},
    {"urgency": "urgent", "messages": [
        "I need shelter tonight, my partner kicked me out",
        "I'm in Germiston with my two kids, we have nowhere to go",
        "We're not in immediate danger but it's getting dark",
        "We're not injured",
        "Text is best, my phone battery is low",
    ], "location": {"latitude": -26.2200, "longitude": 28.1700}},
    {"urgency": "urgent", "messages": [
        "I ran out of my HIV medication three days ago",
        "I'm in Vosloorus, I can't get to the clinic because I have no transport",
        "I'm not in danger but I'm feeling very sick",
        "Not injured, just weak and dizzy from missing meds",
        "WhatsApp me please",
    ], "location": {"latitude": -26.3500, "longitude": 28.2000}},
    {"urgency": "urgent", "messages": [
        "I'm having a panic attack, I was assaulted last week and I can't cope",
        "I'm at home in Benoni",
        "I'm safe right now but I feel like I'm losing my mind",
        "Not physically injured but mentally I'm falling apart",
        "Email is safest for me",
    ], "location": {"latitude": -26.1880, "longitude": 28.3210}},
    {"urgency": "urgent", "messages": [
        "I need a protection order against my neighbour who keeps threatening me",
        "I'm in Boksburg, I went to SAPS but they said come back tomorrow",
        "I'm not in immediate danger but he said he'll come tonight",
        "I'm not injured",
        "Call me, I need to talk to someone",
    ], "location": {"latitude": -26.2120, "longitude": 28.2560}},
    {"urgency": "standard", "messages": [
        "I need help finding a counsellor, I've been struggling since my assault",
        "I'm in Randburg, I can travel if needed",
        "I'm safe, this happened months ago",
        "Not injured, just need mental health support",
        "Email works best for me",
    ], "location": {"latitude": -26.0940, "longitude": 28.0060}},
    {"urgency": "standard", "messages": [
        "I want to know about getting a protection order",
        "I'm in Centurion, Pretoria",
        "I'm not in danger right now, my ex lives far away",
        "I'm not injured",
        "You can call or text me",
    ], "location": {"latitude": -25.8600, "longitude": 28.1900}},
    {"urgency": "standard", "messages": [
        "I need transport to get to the Thuthuzela Care Centre",
        "I'm in Daveyton, the centre is in Benoni",
        "I'm safe but I have no money for a taxi",
        "I'm not injured, I need to go for a follow-up",
        "WhatsApp is fine",
    ], "location": {"latitude": -26.1540, "longitude": 28.4120}},
]


def _jitter_coords(lat: float, lon: float, radius_km: float = 2.0) -> dict:
    deg_per_km = 0.009
    jitter_lat = random.uniform(-radius_km, radius_km) * deg_per_km
    jitter_lon = random.uniform(-radius_km, radius_km) * deg_per_km
    return {
        "latitude": round(lat + jitter_lat, 6),
        "longitude": round(lon + jitter_lon, 6),
        "accuracy": random.uniform(10, 500),
        "source": "browser",
    }


@dataclass
class RequestMetric:
    user_id: int
    step: str
    status_code: int
    latency_ms: float
    error: str | None = None
    urgency: str | None = None


@dataclass
class SimulationResults:
    total_users: int = 0
    completed_users: int = 0
    failed_users: int = 0
    metrics: list[RequestMetric] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def duration_s(self) -> float:
        return self.end_time - self.start_time

    def summary(self) -> dict:
        successful = [m for m in self.metrics if m.status_code == 200]
        failed = [m for m in self.metrics if m.status_code != 200]
        latencies = [m.latency_ms for m in successful]

        by_step: dict[str, list[float]] = {}
        for m in successful:
            by_step.setdefault(m.step, []).append(m.latency_ms)

        step_stats = {}
        for step, lats in sorted(by_step.items()):
            step_stats[step] = {
                "count": len(lats),
                "avg_ms": round(sum(lats) / len(lats), 1),
                "p50_ms": round(sorted(lats)[len(lats) // 2], 1),
                "p95_ms": round(sorted(lats)[int(len(lats) * 0.95)], 1),
                "max_ms": round(max(lats), 1),
            }

        urgency_counts: dict[str, int] = {}
        for m in self.metrics:
            if m.urgency:
                urgency_counts[m.urgency] = urgency_counts.get(m.urgency, 0) + 1

        return {
            "total_users": self.total_users,
            "completed": self.completed_users,
            "failed": self.failed_users,
            "duration_seconds": round(self.duration_s, 1),
            "total_requests": len(self.metrics),
            "successful_requests": len(successful),
            "failed_requests": len(failed),
            "overall_latency": {
                "avg_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
                "p50_ms": round(sorted(latencies)[len(latencies) // 2], 1) if latencies else 0,
                "p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 1) if latencies else 0,
                "max_ms": round(max(latencies), 1) if latencies else 0,
            },
            "by_step": step_stats,
            "urgency_distribution": urgency_counts,
            "requests_per_second": round(len(self.metrics) / self.duration_s, 1) if self.duration_s > 0 else 0,
        }


async def simulate_user(
    user_id: int,
    base_url: str,
    session: aiohttp.ClientSession,
    results: SimulationResults,
    message_delay: tuple[float, float] = (1.0, 3.0),
) -> None:
    persona = random.choice(PERSONAS)
    loc = persona["location"]
    location = _jitter_coords(loc["latitude"], loc["longitude"])
    num_messages = random.randint(3, min(5, len(persona["messages"])))
    messages = persona["messages"][:num_messages]

    try:
        t0 = time.monotonic()
        async with session.post(
            f"{base_url}/sessions/start",
            json={"initial_message": messages[0], "location": location},
        ) as resp:
            latency = (time.monotonic() - t0) * 1000
            body = {}
            resp_text = ""
            try:
                resp_text = await resp.text()
                body = json.loads(resp_text) if resp.status == 200 else {}
            except Exception:
                pass
            results.metrics.append(RequestMetric(
                user_id=user_id, step="start_session",
                status_code=resp.status, latency_ms=latency,
                urgency=persona["urgency"],
                error=resp_text[:200] if resp.status != 200 else None,
            ))
            if resp.status != 200:
                if results.failed_users < 3:
                    print(f"  ⚠ User {user_id} start_session failed ({resp.status}): {resp_text[:120]}", flush=True)
                results.failed_users += 1
                return

        session_id = body.get("session_id")
        if not session_id:
            results.failed_users += 1
            return

        for i, msg in enumerate(messages[1:], start=1):
            await asyncio.sleep(random.uniform(*message_delay))
            t0 = time.monotonic()
            async with session.post(
                f"{base_url}/sessions/{session_id}/message",
                json={"message": msg, "client_message_id": f"sim-{user_id}-{i}", "location": location},
            ) as resp:
                latency = (time.monotonic() - t0) * 1000
                results.metrics.append(RequestMetric(
                    user_id=user_id, step=f"message_{i}",
                    status_code=resp.status, latency_ms=latency,
                    urgency=persona["urgency"],
                ))
                if resp.status != 200:
                    error_text = await resp.text()
                    results.metrics[-1].error = error_text[:200]

        await asyncio.sleep(random.uniform(0.5, 2.0))
        t0 = time.monotonic()
        async with session.post(f"{base_url}/sessions/{session_id}/submit") as resp:
            latency = (time.monotonic() - t0) * 1000
            results.metrics.append(RequestMetric(
                user_id=user_id, step="submit",
                status_code=resp.status, latency_ms=latency,
                urgency=persona["urgency"],
            ))

        results.completed_users += 1

    except Exception as exc:
        results.failed_users += 1
        results.metrics.append(RequestMetric(
            user_id=user_id, step="connection_error",
            status_code=0, latency_ms=0, error=str(exc)[:200],
        ))
        if results.failed_users <= 3:
            print(f"  ⚠ User {user_id} failed: {str(exc)[:120]}", flush=True)


async def run_simulation(
    num_users: int, base_url: str,
    ramp_up_seconds: float, message_delay: tuple[float, float],
) -> SimulationResults:
    results = SimulationResults(total_users=num_users)

    print(f"  Checking connectivity to {base_url}/health ...", flush=True)
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as check:
            async with check.get(f"{base_url}/health") as resp:
                body = await resp.text()
                print(f"  ✅ Health check: {resp.status} — {body[:80]}", flush=True)
    except Exception as exc:
        print(f"  ❌ Cannot reach {base_url}: {exc}", flush=True)
        print(f"  Aborting simulation.", flush=True)
        results.start_time = results.end_time = time.monotonic()
        return results

    connector = aiohttp.TCPConnector(limit=200, limit_per_host=100)
    timeout = aiohttp.ClientTimeout(total=120)
    session = aiohttp.ClientSession(
        connector=connector, timeout=timeout,
        headers={"Content-Type": "application/json"},
    )

    try:
        tasks: list[asyncio.Task] = []
        delay_per_user = ramp_up_seconds / num_users if num_users > 1 and ramp_up_seconds > 0 else 0
        results.start_time = time.monotonic()

        for i in range(num_users):
            task = asyncio.create_task(
                simulate_user(i, base_url, session, results, message_delay)
            )
            tasks.append(task)
            if delay_per_user > 0:
                await asyncio.sleep(delay_per_user)
            if (i + 1) % 10 == 0 or i == num_users - 1:
                print(f"  Launched {i + 1}/{num_users} users...", flush=True)

        print(f"\n  All {num_users} users launched. Waiting for completion...\n", flush=True)
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, tr in enumerate(task_results):
            if isinstance(tr, Exception):
                print(f"  ⚠ Task {i} raised: {tr}", flush=True)

        results.end_time = time.monotonic()
    finally:
        await session.close()

    return results


def print_results(results: SimulationResults) -> None:
    summary = results.summary()
    print("=" * 64)
    print("  DISASTER SIMULATION RESULTS")
    print("=" * 64)
    print(f"  Users:      {summary['total_users']} total, "
          f"{summary['completed']} completed, {summary['failed']} failed")
    print(f"  Duration:   {summary['duration_seconds']}s")
    print(f"  Throughput: {summary['requests_per_second']} req/s")
    print(f"  Requests:   {summary['total_requests']} total, "
          f"{summary['successful_requests']} ok, {summary['failed_requests']} failed")
    print()
    print("  Overall Latency:")
    ol = summary["overall_latency"]
    print(f"    avg={ol['avg_ms']}ms  p50={ol['p50_ms']}ms  "
          f"p95={ol['p95_ms']}ms  max={ol['max_ms']}ms")
    print()
    print("  By Step:")
    for step, stats in summary["by_step"].items():
        print(f"    {step:20s}  n={stats['count']:4d}  avg={stats['avg_ms']:8.1f}ms  "
              f"p50={stats['p50_ms']:8.1f}ms  p95={stats['p95_ms']:8.1f}ms  "
              f"max={stats['max_ms']:8.1f}ms")
    print()
    print("  Urgency Distribution:")
    for urg, count in sorted(summary["urgency_distribution"].items()):
        print(f"    {urg:12s}: {count}")
    print()
    errors = [m for m in results.metrics if m.error]
    if errors:
        print(f"  Errors ({len(errors)}):")
        seen: set[str] = set()
        for m in errors[:10]:
            err_key = (m.error or "")[:80]
            if err_key not in seen:
                seen.add(err_key)
                print(f"    user={m.user_id} step={m.step}: {m.error}")
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more")
    print()
    output_file = f"disaster_sim_results_{int(time.time())}.json"
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Full results written to: {output_file}")
    print("=" * 64)


def main():
    parser = argparse.ArgumentParser(description="Survivor Network Disaster Load Test")
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--ramp-up", type=float, default=60)
    parser.add_argument("--base-url", type=str, default="http://chatbot-service.127.0.0.1.nip.io")
    parser.add_argument("--min-delay", type=float, default=1.0)
    parser.add_argument("--max-delay", type=float, default=3.0)
    args = parser.parse_args()

    print()
    print("=" * 64)
    print("  SURVIVOR NETWORK — DISASTER SCENARIO SIMULATION")
    print("=" * 64)
    print(f"  Target:     {args.base_url}")
    print(f"  Users:      {args.users}")
    print(f"  Ramp-up:    {args.ramp_up}s")
    print(f"  Msg delay:  {args.min_delay}-{args.max_delay}s between messages")
    print(f"  Personas:   {len(PERSONAS)} crisis scenarios")
    print("=" * 64)
    print()

    results = asyncio.run(
        run_simulation(
            num_users=args.users, base_url=args.base_url,
            ramp_up_seconds=args.ramp_up,
            message_delay=(args.min_delay, args.max_delay),
        )
    )
    print_results(results)


if __name__ == "__main__":
    main()
