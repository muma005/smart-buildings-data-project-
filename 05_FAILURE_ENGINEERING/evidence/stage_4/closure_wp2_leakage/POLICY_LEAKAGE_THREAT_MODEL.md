# Level 2 Threat Model: In-Process Python Policy Execution Boundaries

## 1. Architectural Scope & Context

In the Smart Buildings competition framework, candidate policy code is loaded and executed within the same Python interpreter runtime as the building simulator and evaluation harness.
This architectural decision enables high-throughput simulation without IPC serialization overhead, but establishes fundamental boundary distinctions.

## 2. Two-Level Defense Architecture

```
+-----------------------------------------------------------------------------------+
| LEVEL 1: STATIC AST ANALYSIS & RUNTIME WRAPPER (Ring 1 - Ring 4)                 |
| - Ring 1: Interface contract validation (action shapes, bounds, dtypes, non-NaN)  |
| - Ring 2: Static AST audit of entrypoint policy & recursive local dependencies     |
| - Ring 3: Deepcopy isolation of observation & metadata structures                  |
| - Ring 4: Execution timing, latency tracking, and exception containment           |
+-----------------------------------------------------------------------------------+
|                                                                                   |
| LEVEL 2: IN-PROCESS PHYSICAL BOUNDARY (Explicit Architectural Limitations)        |
| - Python AST analysis operates exclusively on static Python source text.          |
| - AST cannot inspect machine instructions inside compiled C/C++ extensions.       |
| - Shared memory space means process isolation is NOT enforced at OS kernel level. |
+-----------------------------------------------------------------------------------+
```

## 3. Guarantees Enforced by Level 1 (Static AST Guard)

Level 1 provides deterministic, fail-closed enforcement against the following threat vectors:

- **Prohibited Imports**: Blocks imports of simulator internals (`smart_buildings.simulator`, `smart_control`), ground-truth data (`smart_buildings.weather`), native process escape (`ctypes`, `subprocess`, `multiprocessing`), and unauthorized network I/O (`socket`, `requests`, `urllib`).
- **Stack Crawling & Metaprogramming**: Blocks frame inspection (`_getframe`, `currentframe`, `f_back`, `f_locals`), garbage collector crawling (`get_objects`), class hierarchy navigation (`__subclasses__`), and dynamic execution (`eval`, `exec`, `__import__`).
- **Direct Scenario File Access**: Blocks literal and attribute calls to `open()`, `Path.read_text()`, and `Path.open()` targeting `config.gin`, `weather`, or scenario ground-truth paths.
- **Recursive Dependency Scanning**: Walks all `.py` files inside `artifacts/local_deps/`, preventing obfuscation via split modules.

## 4. Inherent Physical Limitations of In-Process Execution (Level 2)

The evaluation harness acknowledges the following theoretical and physical boundaries:

1. **Compiled C-Extensions & Shared Memory**: If a policy executes pre-compiled binary modules (`.so`, `.pyd`, `.dll`), AST analysis cannot inspect binary opcodes. Within a shared process, native C code has pointer access to process memory.
2. **Obfuscated / Dynamic Path Construction**: String operations that dynamically compute path names at runtime without literal indicators cannot be proven by static AST alone.
3. **True Security Boundary Requirement**: For untrusted multi-tenant execution or adversarial competitions where arbitrary binary execution is permitted, OS-level process isolation (e.g. gVisor sandbox, seccomp-bpf filters, or isolated container execution) is required.

## 5. Defense-in-Depth Governance

To mitigate in-process limitations without requiring full containerization overhead, the infrastructure employs multi-stage governance:
- **Artifact Vault Freezing**: Complete source of policy and dependencies is hashed and vaulted into `artifacts/` prior to execution.
- **Score Verification & Baseline Reconstruction**: Downstream verification recomputes scores independently from raw trace tensors.
- **Lineage Quarantine**: Tainted upstream experiments automatically cascade quarantine status to all dependent candidates.
- **Release Auditing**: Releases must undergo independent package auditing and signature validation before promotion.