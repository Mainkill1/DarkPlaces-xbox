## Reason

Explain the porting problem and why this patch is the smallest useful gate.

## Flow change

Describe the data/control flow before and after. Include the Xbox boundary involved.

## Scope

- Xbox subsystem:
- Feature-matrix row:
- Deliberate fallbacks:
- Follow-up issue:

## Build and validation

```text
Desktop command/result:
Xbox command/result:
xemu result:
Retail 64 MB result:
```

## Evidence

- Logs/captures:
- Binary size:
- Memory high-water:
- Performance baseline/candidate, when applicable:

## Content and licensing

List every new dependency/asset, its source, license, and whether it is redistributed or generated.

## Checklist

- [ ] Desktop `make sdl-release` still passes.
- [ ] The claimed Xbox acceptance gate is demonstrated, not inferred.
- [ ] Unsupported state has a deterministic fallback/diagnostic.
- [ ] No proprietary SDK, BIOS, key, retail data, or unreviewed asset was added.
- [ ] Wiki/feature matrix updated when behavior changed.
