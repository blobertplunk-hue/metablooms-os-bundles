# G1 — Adversarial MMD Reviewer Checklist

Complete after writing ADVERSARIAL_MMD.md. Check each item honestly.
You must have spent at least 15 minutes actively trying to break the plan.

## Independence

- [ ] I did NOT write the research_dossier.json or any SEE artifacts
- [ ] I approached this as an attacker, not a proofreader
- [ ] I did not start from the MMD report — I did my own independent gap hunt first

## Coverage

- [ ] I answered Question 1 (adversarial input) with a specific attack, not "N/A"
- [ ] I answered Question 2 (scale failure) with a specific bottleneck or justified N/A
- [ ] I answered Question 3 (API misuse) with a specific misuse pattern
- [ ] I answered Question 4 (false assumption) — I named the specific claim I'd bet against
- [ ] I answered Question 5 (missing integration) with a specific system or justified N/A
- [ ] I answered Question 6 (obvious unstated) — I found the thing everyone knows but nobody wrote

## Gaps

- [ ] Any new gaps I found have been added to mmd/MMD_REPORT.json
- [ ] I confirmed with the research operator that the gaps are reflected in the report

## Verdict

- [ ] All six questions are substantively answered
- [ ] New gaps (if any) are in MMD_REPORT.json
- [ ] I am confident this plan has been genuinely stress-tested
