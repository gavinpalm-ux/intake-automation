# Case Study: Automating Customer Intake for a Property Services Company

*Fictional company, realistic process. Numbers below come from running this project on the sample inbox; the manual baseline is an estimate explained in the "Assumptions" section.*

## 1. The problem

Gulf Coast Property Services offers turnover cleaning, maintenance, landscaping, pest control and inspections to property managers, HOAs, commercial owners and individual landlords. New business arrives as emails and website form submissions, and they are messy: some are a single line ("do u guys do lawns"), some bury a 64-unit portfolio in the third sentence, and some are urgent ("water is leaking from the ceiling").

### The manual process (before)

| Step | Who | Typical time |
|---|---|---|
| Read and interpret the message | Office admin | 2 min |
| Retype contact and property details into the lead spreadsheet | Office admin | 4 min |
| Decide how big and how urgent it is | Office admin | 1 min |
| Forward it to the right person | Office admin | 1 min |
| Write a first reply | Sales rep | 4 min |
| **Total** | | **~12 min per inquiry** |

### What went wrong

- **Big leads waited in line with small ones.** Inquiries were worked in the order they arrived, so a 120-home HOA bid could sit behind a one-line question.
- **Urgent requests weren't obvious.** A leak or pest problem looked the same in the inbox as a price-shopping email.
- **Data entry errors.** Retyped phone numbers and unit counts were the most common source of bad CRM data.
- **Inconsistent replies.** Each rep wrote their own first response, with different promises about timing.

## 2. Goals

1. Cut the staff time spent on intake by at least half.
2. Get high-value and urgent inquiries to the right person first.
3. Keep data accurate enough to trust (target: 90%+ field accuracy).
4. Keep a person accountable for every message that goes out.

## 3. The solution (after)

| Step | Who | Typical time |
|---|---|---|
| Extract fields from the message | Automated (AI or rules) | seconds |
| Score, tier and route the lead | Automated | seconds |
| Flag anything uncertain, with a reason | Automated | seconds |
| Draft a reply from approved templates | Automated | seconds |
| Skim and send a clean draft | Sales rep | ~1 min |
| Fix a flagged record, then send | Sales rep | ~3 min |

## 4. Results on the sample inbox

| Metric | Before | After |
|---|---|---|
| Staff time for 15 inquiries | ~180 min | ~27 min (**-85%**) |
| Field accuracy | depends on who's typing | **~96%** (offline engine, measured) |
| Order leads are worked | arrival order | priority score, highest first |
| Urgent requests | found by luck | flagged, promised a call within 2 business hours |
| Reply consistency | varies by rep | approved templates |

- **Top of the queue:** the 64-unit apartment manager needing help ASAP, the 85-home rental portfolio, the 40-unit acquisition, and the 120-home HOA bid, all routed to the senior account manager.
- **Review queue:** 6 records. Two had no contact info at all (a human has to dig), and four were high-value leads that get a personal touch by design.
- **Known misses** (listed in `output/accuracy.md`): the rules engine didn't catch "two of our duplex units" as a unit count, read "has been failing" as non-urgent, counted "irrigation maintenance" as a separate maintenance request, and treated "next year" on an HOA bid as low urgency. These are exactly the language-understanding cases an AI model handles better, and the reason the AI engine exists.

## 5. Guardrails

| Risk | Control |
|---|---|
| AI extracts the wrong details | Accuracy measured against labeled data; regression test blocks changes that drop below 90% |
| Wrong or embarrassing reply goes out | Nothing sends automatically; replies come from approved templates |
| A big deal gets an automated brush-off | Enterprise-tier leads always go to human review |
| AI service outage | Automatic fallback to the offline rules engine, flagged on the record |
| Customer data sent to a third party | AI engine is opt-in; offline mode keeps all data local |

## 6. Assumptions

- The 12-minute manual baseline is an estimate of the steps above. In a real engagement, I'd time 20–30 inquiries with the actual staff during discovery before quoting savings.
- "After" times (1 min clean / 3 min flagged) assume reps read every draft before sending.
- Accuracy is measured on a 15-message sample. A real rollout would label 100+ messages before go-live.

## 7. Lessons for an AI rollout

- **Start with the process, not the model.** The biggest win was prioritization and routing, which is simple logic. AI earns its place on the messy-language part.
- **Measure before you promise.** Having labeled answers turned "it seems to work" into a number stakeholders can approve.
- **Design for the uncertain cases.** A system that knows when to ask a human is easier to trust, and easier to get a team to adopt.
