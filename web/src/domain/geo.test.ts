import { describe, expect, it } from 'vitest';
import { evidenceLabel, freshnessAt } from './geo';

describe('shared geo semantics', () => {
  const now = 1_800_000_000_000;
  it('classifies freshness with shared thresholds', () => {
    expect(freshnessAt(now - 20_000, now)).toBe('LIVE');
    expect(freshnessAt(now - 90_000, now)).toBe('RECENT');
    expect(freshnessAt(now - 8 * 60_000, now)).toBe('AGING');
    expect(freshnessAt(now - 31 * 60_000, now)).toBe('STALE');
  });
  it('never labels an estimate as GPS', () => {
    expect(evidenceLabel.HISTORICAL_ESTIMATE).toBe('Estimación histórica');
    expect(evidenceLabel.HISTORICAL_ESTIMATE).not.toContain('GPS');
  });
});
