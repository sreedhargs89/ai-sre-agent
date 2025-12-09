# 🤖 AI SRE Observer Daemon: Under the Hood

This document explains how the **Observer Daemon** works, visualized with flowcharts, and provides a guide on how to validat it using the Chaos Sandbox.

## 1. Architecture: The Monitoring Loop

The Daemon acts as an autonomous "infinite loop" that constantly watches the cluster state. It is decoupled from the interactive chat but shares the same intelligent core (`AISREContext`).

### The Flow (Step-by-Step)

The daemon operates in a continuous cycle:

1.  **Start**: The daemon initializes and connects to the MCP tools.
2.  **Wait**: It pauses for the configured interval (default: 60 seconds).
3.  **Poll**: It runs a check against the cluster (`kubectl get pods`).
4.  **Decision**:
    *   **If all Pods are Healthy**: Return to **Wait** step.
    *   **If a Pod is Unhealthy**: Proceed to **Investigate**.
5.  **Investigate**: The daemon captures the pod's logs and events.
6.  **Reason**: The AI Agent analyzes the data.
7.  **Alert**: The Agent prints a diagnosis to the console.
8.  **Repeat**: Return to **Wait** step.

### Visual Flow

```text
       +------------------+
       |   Start Daemon   |
       +--------+---------+
                |
                v
       +--------+---------+
       |  Connect to MCP  |
       +--------+---------+
                |
                v
       +--------+---------+       (Loop every 60s)
  +--> |    Wait Cycle    | <-----------------------+
  |    +--------+---------+                         |
  |             |                                   |
  |             v                                   |
  |    +--------+---------+                         |
  |    |   Poll Cluster   |                         |
  |    +--------+---------+                         |
  |             |                                   |
  |             v                                   |
  |    +--------+---------+        Healthy          |
  |    |  Check Status?   +-------------------------+
  |    +--------+---------+                         |
  |             | Unhealthy                         |
  |             v                                   |
  |    +--------+---------+                         |
  |    | Capture Details  |                         |
  |    +--------+---------+                         |
  |             |                                   |
  |             v                                   |
  |    +--------+---------+                         |
  |    | Analyze with AI  |                         |
  |    +--------+---------+                         |
  |             |                                   |
  |             v                                   |
  |    +------------------+                         |
  |    | Print Diagnosis  |                         |
  |    +--------+---------+                         |
  |             |                                   |
  +-------------+-----------------------------------+
```

### Key Components

1.  **Poller**: Effectively runs `kubectl get pods -A -o json` to get a raw snapshot of the cluster. This is faster than making individual API calls for every pod.
2.  **Filter**: Logic in `src/core/daemon.py` filters out noise. It looks specifically for:
    *   Exit Code != 0
    *   Status `OOMKilled`
    *   Status `CrashLoopBackOff`
    *   Image Pull Errors
3.  **Investigator (The Agent)**: When a bad pod is found, we don't just print the error. We construct a natural language prompt:
    > *"Diagnose why pod 'backend-x' is failing. Check logs and events."*
    
    The Agent then uses its MCP tools to inspect the specific pod deeply before returning a summary.

---

## 2. Testing Guide: The Chaos Sandbox 💥

We have provided a pre-built environment to safely test the Daemon's detection capabilities without breaking your real apps.

### Prerequisites
*   A running Kubernetes cluster (Minikube, Kind, Docker Desktop).
*   `kubectl` configured.

### Step-by-Step Test

#### Phase 1: Unleash Chaos
Deploy the sandbox applications. This includes one healthy frontend, a crashing backend, and a memory-leaking worker.

```bash
cd examples/chaos_sandbox
./manage.sh start
```

> **What just happened?**
> *   `frontend` (2 replicas) is running fine.
> *   `backend-crash` (3 replicas) starts, waits 10s, then exits with error 1.
> *   `worker-oom` (1 replica) rapidly consumes RAM until the kernel kills it.

#### Phase 2: Start the Watcher
In a new terminal window, start the AI Daemon.

```bash
# Run from the root of the project
python main.py daemon --interval 10
```
*(We use `--interval 10` for faster feedback during testing)*

#### Phase 3: Observe Discovery
Within ~10-20 seconds, you should see the Daemon "wake up" and notice the issues.

**Expected Output:**
```text
👀 AI SRE Observer Daemon starting...
🔍 Scanning cluster for issues...

⚠️  Found 2 unhealthy pods!

👉 Investigating backend-crash-xyz (default) - Running/Error
🤖 Assessing: Diagnose why the pod 'backend-crash-xyz' is failing...
🛠️  Executing: get_pod_logs
   Result size: 543 chars
🛠️  Executing: get_events
   Result size: 890 chars

[AI Diagnosis]: The pod 'backend-crash' is failing because the application process exited with code 1. 
The logs indicate a "CRITICAL: Database connection failed" error shortly after startup. 
This suggests a misconfiguration or dependency failure.
```

#### Phase 4: Cleanup
Stop the daemon (`Ctrl+C`) and remove the sandbox resources.

```bash
cd examples/chaos_sandbox
./manage.sh stop
```

---

## 3. Extending the Daemon
Currently, the daemon simply prints to the console. Future versions (Level 3+) will:
1.  **Send Notifications**: Slack/Teams webhooks integration.
2.  **Auto-Heal**: If the error is known (e.g., "Full Disk"), execute a cleanup script automatically.
