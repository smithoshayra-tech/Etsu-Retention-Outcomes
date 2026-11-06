# Definitions and assumptions

Every number below that is not marked REAL is an assumption set in `src/02_simulate_funnel.py`.
None of the assumptions was measured at Utah Valley University or any other institution.

## Real anchors (IPEDS fall 2022, file EF2022C, UNITID 230737, Utah Valley University)

| Anchor | Value | Used for |
|---|---|---|
| First-time degree or certificate-seeking students | 4,752 | Target size of each simulated entering class |
| Of those, Utah residents (state code 49) | 3,555, 74.8% | In-state share of simulated inquiries |

Reproduce: open `data/EF2022C/ef2022c.csv`, keep UNITID 230737, read the total row and the row for state code 49.

## Funnel stages

| Stage | Flag column | Meaning |
|---|---|---|
| Inquiry | (every row) | A prospective student asks for information |
| Started | `started` | Opens an application |
| Completed | `completed` | Submits a finished application |
| Admitted | `admitted` | Meets the minimum requirements. UVU is open admission, so this is close to automatic |
| Registered | `registered` | Registers for classes |
| Enrolled | `enrolled` | Still registered on census day |

`registered_date` is always after `completed_date`, and both are after `inquiry_date` (check S5).

## Assumed stage rates (simulated)

| Rate | Value | Adjusted by |
|---|---|---|
| Inquiry to started | 38% base | Lead source multiplier. Multiplied by 0.72 if first contact came more than 3 days after the inquiry |
| Started to completed | 78% | Nothing |
| Completed to admitted | 98.5% | Nothing |
| Admitted to registered | 58% base | Lead source multiplier. Multiplied by 1.40 if an aid form was filed. Multiplied by 0.80 for out-of-state students |
| Registered to enrolled | 93% | Nothing |

Lead source multipliers (start, register): concurrent enrollment 1.55, 1.30; campus visit or event 1.35, 1.20; student referral 1.25, 1.10; high school counselor 1.20, 1.10; organic search 0.95, 1.00; college fair 0.85, 0.95; paid social and display 0.55, 0.80.

Other assumptions: aid-form filing is 55% for Utah residents and 40% for out-of-state students. Share of inquiries first contacted after 3 days is 20% in 2021, 20% in 2022, 21% in 2023 and 36% in 2024. Inquiry volume is 23,400 per cycle, set by trial so the 2021 to 2023 enrolled counts land within 5% of 4,752 (check S6).

## Planted effects

The simulation contains five effects on purpose: lead-source quality, a penalty for slow first contact, a boost from filing an aid form, a lower registration rate for out-of-state students, and a rise in slow first contact in 2024. The analysis in `sql/03_analysis.sql` recovers them. That shows the pipeline measures what it should. It is not evidence about any real institution.

## Metric formulas

- Start rate = started / inquiries.
- Complete rate = completed / started.
- Register rate = registered / admitted.
- Census rate = enrolled / registered.
- Inquiry to enrolled = enrolled / inquiries.
- Melt before registration = (admitted − registered) / admitted.

## Peer rule for the real IPEDS part

Utah public (CONTROL 1), four-year or above (ICLEVEL 1), active in 2023, Carnegie 2021 class 15 to 22. Snow College (class 14, associate's focus) is excluded.
