# Verification Patterns — Detailed Pipeline

## Layer 0: Syntax Check (Always, Fast)

Purpose: Catch parse errors before committing any time to evaluation.

| Project Type | Command | Timeout |
|-------------|---------|---------|
| Rust | `cargo check 2>&1` | 30s |
| TypeScript | `npx tsc --noEmit 2>&1` | 30s |
| JavaScript | `node --check {file} 2>&1` | 10s |
| Python | `python3 -c "import ast; ast.parse(open(f).read())" 2>&1` | 10s |
| Go | `go vet ./... 2>&1` | 30s |
| Generic | skip | — |

**On failure**: Discard immediately. Do not commit. Do not run further layers.

## Layer 1: Guard Checks (User-Defined, Mandatory)

Purpose: Hard constraints that must always pass.

Defined in MISSION.md `guard` section as a bash command that must exit with code 0.

Common patterns:

### Test Suite
```bash
# Rust
cargo test --lib 2>&1 | tail -5

# TypeScript/JavaScript
npm test 2>&1 | tail -5

# Python
pytest --tb=short -q 2>&1 | tail -5

# Go
go test ./... 2>&1 | tail -5
```

### Type Check + Test
```bash
npx tsc --noEmit && npm test
```

### Build Verification
```bash
npm run build 2>&1 | tail -5
```

### Custom Guard Script
```bash
bash odyssey.checks.sh
```

Where `odyssey.checks.sh` contains multiple checks:
```bash
#!/bin/bash
set -e
cargo test --lib
cargo clippy -- -D warnings
cargo fmt -- --check
```

**Timeout**: 120 seconds default. Configurable in MISSION.md.

**On failure**: Revert to checkpoint (`git reset --hard HEAD~1`), discard waypoint.

## Layer 2: Primary Metric (User-Defined)

Purpose: Measure whether the change moved the needle on the optimization target.

### Metric Definition in MISSION.md

```markdown
| Name | Unit | Measure Command | Direction |
|------|------|----------------|-----------|
| p99_ms | ms | `bash odyssey.sh` | lower |
| coverage | % | `pytest --cov --cov-report=term-missing | grep TOTAL | awk '{print $4}'` | higher |
| bundle_kb | kb | `du -k dist/bundle.js | cut -f1` | lower |
```

### Measure Command Protocol

The measure command should output in one of these formats:

1. **METRIC prefix**: `METRIC name=value` (recommended)
   ```bash
   #!/bin/bash
   # odyssey.sh
   p99=$(curl -s http://localhost:8080/benchmark | jq '.p99')
   echo "METRIC p99_ms=${p99}"
   ```

2. **Raw number**: Just a single number on stdout
   ```
   42.5
   ```

3. **Last number**: The last numeric value on stdout is used

### Direction
- `lower`: Smaller values are better (latency, error rate, bundle size)
- `higher`: Larger values are better (coverage, throughput, score)

### Evaluation

```bash
python3 $CLAUDE_PLUGIN_ROOT/scripts/odyssey_helper.py evaluate \
  --jsonl odyssey.jsonl --metric NEW_VALUE
```

Returns JSON:
```json
{"improved": true, "previous_best": 320.5, "new_value": 245.1, "direction": "lower", "delta": -75.4}
```

**Timeout**: 600 seconds default (configurable).

## Layer 3: Quality Checks (Optional, Soft)

Purpose: Catch secondary regressions without forcing discard.

### Common Quality Metrics

| Metric | How to Measure | Alert Threshold |
|--------|---------------|-----------------|
| Bundle size | `du -k dist/` | > 10% increase |
| Lint warnings | `eslint . | grep warning | wc -l` | any increase |
| Coverage | `pytest --cov | grep TOTAL | awk '{print $4}'` | any decrease |
| Complexity | `lizard src/ | grep "Average complexity" | awk '{print $NF}'` | > 20% increase |
| Type errors | `tsc --noEmit 2>&1 | grep "error TS" | wc -l` | any increase |

### Configuration

Add to MISSION.md:
```markdown
## Quality Checks
| Check | Command | Threshold |
|-------|---------|-----------|
| bundle_size | `du -k dist/bundle.js | cut -f1` | max 150 |
| coverage | `pytest --cov | grep TOTAL | awk '{print $4}'` | min 80 |
```

**On failure**: Log a warning in odyssey.jsonl under `secondaryMetrics`. Do not force discard unless configured as hard constraint.

## Auto-Detection Logic

When no guard/metric is specified, `odyssey_helper.py detect` scans for sentinel files:

```
Cargo.toml → rust (cargo check, cargo test)
go.mod → go (go vet, go test)
pyproject.toml | setup.py → python (ast.parse, pytest)
package.json + tsconfig.json → typescript (tsc --noEmit, npm test)
package.json (no tsconfig) → javascript (node --check, npm test)
Makefile → make (make -n, make test)
```

Auto-detection results are written into MISSION.md for user review and override.

## Writing a Custom Benchmark Script

Create `odyssey.sh` in the project root:

```bash
#!/bin/bash
set -e

# Run your benchmark/metric collection
# Output MUST include: METRIC name=value

# Example: measure API response time
p50=$(wrk -t1 -c1 -d5s http://localhost:8080/api 2>&1 | grep "Latency" | awk '{print $2}' | sed 's/ms//')
p99=$(wrk -t1 -c1 -d5s http://localhost:8080/api 2>&1 | grep "99%" | awk '{print $2}' | sed 's/ms//')

echo "METRIC p50_ms=${p50}"
echo "METRIC p99_ms=${p99}"
```

Make executable: `chmod +x odyssey.sh`
