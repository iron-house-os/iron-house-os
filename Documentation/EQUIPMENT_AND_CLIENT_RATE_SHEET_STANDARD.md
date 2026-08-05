# Iron House Equipment and Client Rate Sheet Standard

**Document:** IH-Estimate-RateSheet-Company-2026-08-04-v1  
**Status:** Ready for implementation  
**Owner:** Estimating  
**Approval gate:** Executive approval before external issue or production deployment  
**Effective date:** August 4, 2026

## Purpose

This standard defines the default equipment benchmarks, client-rate structure and commercial fields required in Iron House estimates and client-facing rate sheets.

It applies to:

- Vancouver / Metro West
- Surrey and Fraser Valley East

Both markets use the same base equipment library. Parking, congestion, restricted hours, access, accommodation, travel and mobilization remain separate estimate lines.

## Source and Evidence Limitation

The primary public benchmark is the Island Equipment Owners Association **2026 Suggested Equipment Rates**, effective January 1, 2026:

https://www.ieoa.ca/rates/

The IEOA rates:

- are suggested minimums for machines working in light-to-medium conditions;
- include the operator;
- exclude transportation;
- allow higher rates for difficult conditions, specialized attachments and work outside regular hours;
- include fuel provision up to $2.52/litre; and
- carry a 0% suggested fuel surcharge for July 2026.

The BC Road Builders and Heavy Construction Association / BC Ministry of Transportation **2026-2027 Blue Book** is the preferred secondary validation source when the current guide is available:

https://www.roadbuilders.bc.ca/blue-book/

Rates below are market benchmarks, not representations that Iron House owns the listed equipment. Iron House’s Year 1 model assumes rented equipment.

## Core Client Equipment Rate Library

Rates are in Canadian dollars per hour, include one qualified operator and normal fuel, and exclude mobilization, demobilization, permits, disposal, specialized attachments, taxes and project-specific premiums.

| Category | Class / description | Client benchmark |
|---|---|---:|
| Excavator | 1.4-2.75 t | $142/hr |
| Excavator | 2.75-4 t | $163/hr |
| Excavator | 4-6 t | $169/hr |
| Excavator | 6-9.5 t | $180/hr |
| Excavator | 9.5-14 t | $193/hr |
| Excavator | 14-19 t | $205/hr |
| Excavator | 20-23 t | $228/hr |
| Excavator | 23-26 t | $248/hr |
| Excavator | 26-30 t | $257/hr |
| Excavator | 30-36 t | $287/hr |
| Skid steer | Under 1,000 lb operating load | $112/hr |
| Skid steer | 1,000-2,000 lb operating load | $124/hr |
| Skid steer | 2,000-3,200 lb operating load | $143/hr |
| Compact track loader | Under 1,100 lb operating load | $121/hr |
| Compact track loader | 1,100-2,230 lb operating load | $146/hr |
| Compact track loader | 2,230-3,000 lb operating load | $151/hr |
| Compact track loader | 3,000-3,225 lb operating load | $154/hr |
| Loader/backhoe | 80-100 HP extendahoe | $165/hr |
| Loader/backhoe | 100-108 HP extendahoe | $187/hr |
| Bulldozer | Under 80 HP | $195/hr |
| Bulldozer | 80-125 HP | $228/hr |
| Bulldozer | 125-220 HP | $282/hr |
| Wheel loader | Under 1.75 yd³ | $184/hr |
| Wheel loader | 2-2.5 yd³ | $205/hr |
| Wheel loader | 3 yd³ | $249/hr |
| Vibratory compactor | Up to 4.9 t | $184/hr |
| Vibratory compactor | 5-7.9 t | $195/hr |
| Vibratory compactor | 8-11.9 t | $219/hr |
| Grader | Under 80 HP | $184/hr |
| Grader | 85-90 HP | $205/hr |
| Grader | 125-135 HP | $219/hr |
| Grader | 135-150 HP | $249/hr |
| Dump truck | Single axle, 7-8 t | $141/hr |
| Dump truck | Tandem, 13-14 t | $165/hr |
| Dump truck | Tridem, 20 t | $175/hr |
| Dump truck | Tandem and pup, 25-27 t | $219/hr |
| Dump truck | Tandem and tri-axle pup, 29-31 t | $228/hr |
| Off-road rock truck | 20 ton | $231/hr |
| Off-road rock truck | 25 ton | $249/hr |
| Off-road rock truck | 30 ton | $266/hr |
| Slinger truck | Tandem, 13-14 t | $205/hr |
| Slinger truck | Tridem, 20 t | $213/hr |
| Lowbed with tandem tractor | 20 ton | $179/hr |
| Lowbed with tandem tractor | 30 ton | $184/hr |
| Lowbed with tandem tractor | 40 ton | $202/hr |

Use **Price on Request** for larger or uncommon classes, including excavators over 36 t, dozers over 290 HP, wheel loaders over 6 yd³, compactors over 12 t, lowbeds over 50 t and specialized cranes.

## Attachments

Attachments are separate additions to the base machine rate.

| Attachment | Applicable machine | Add-on benchmark |
|---|---|---:|
| Hydraulic hammer | Approx. 13,000 lb excavator | $109/hr |
| Hydraulic hammer | Approx. 22,000 lb excavator | $128/hr |
| Hydraulic hammer | Approx. 25,000 lb excavator | $143/hr |
| Hydraulic hammer | Approx. 38,000 lb excavator | $155/hr |
| Hydraulic hammer | Approx. 45,000 lb excavator | $174/hr |
| Compactor attachment | 5 t excavator or rubber-tired backhoe | $47/hr |
| Compactor attachment | 7-10 t excavator | $58/hr |
| Compactor attachment | 20 t excavator | $79/hr |

Price augers, grapples, thumbs, tilt buckets, trench boxes, sweepers, forks, mulchers and other specialty attachments from a current vendor quote.

## Pricing Calculation

The estimating engine must retain direct-cost detail even when the client sees one all-in rate.

```text
Rental direct cost =
vendor base rental
+ damage waiver / insurance
+ environmental or rental fees
+ fuel
+ attachment rental
+ allocated delivery and pickup
+ expected overtime-hour charges
+ cleanup allowance

Iron House all-in direct cost =
rental direct cost
+ operator labour charge-out
+ project-specific support cost

Minimum client equipment rate =
Iron House all-in direct cost / (1 - target final margin)

Selected client rate =
greater of current market benchmark or minimum client equipment rate
```

Default target final margin is **10%**. This is a margin calculation, not a 10% markup.

Do not add operator labour again when an all-in equipment-with-operator client rate is selected.

## Other Required Client Rate Sheet Sections

### Labour

Use the approved Upper-Market Wage Library and 2.1x regular labour charge-out standard in:

`Documentation/LABOUR_CHARGEOUT_AND_SMALL_JOB_STANDARD.md`

Small-job premiums apply to labour only.

### Support vehicles and light equipment

Include separate rate lines for:

- service pickup / foreman truck;
- one-ton pickup;
- dump trailer;
- equipment trailer;
- water trailer;
- plate compactor;
- jumping jack;
- concrete saw;
- trash pump;
- submersible pump;
- generator;
- light tower;
- laser, GPS rover or total-station support;
- confined-space equipment;
- trench shoring, trench box and road plates;
- traffic-control devices; and
- vacuum truck / hydrovac.

Until Iron House has verified owned-equipment cost history, price these from a current rental or subcontract quote plus the approved final-margin calculation. Do not publish invented fixed rates.

### Materials, trucking, disposal and subcontractors

Show each category separately:

- supplier or subcontractor cost;
- quote date and expiry;
- freight;
- waste;
- escalation;
- taxes where applicable;
- Iron House markup or final-margin treatment;
- selected client rate; and
- override reason.

Use current competitive quotes. A contract-stipulated markup overrides the default.

### Mobilization and project logistics

Include separate selectable lines for:

- equipment delivery and pickup;
- lowbed / float time;
- crew travel;
- loading and securement;
- permits and pilot cars;
- ferries, tolls and parking;
- accommodation and living-out allowance;
- Vancouver congestion and restricted access;
- night-shift setup;
- remobilization caused by client delay; and
- remote-location premium.

### Commercial terms

Every issued rate sheet must state:

- currency: CAD;
- GST excluded unless expressly stated;
- effective date and expiry date;
- regular working hours;
- minimum billable hours or shift;
- overtime, night, weekend and statutory-holiday treatment;
- standby and client-delay treatment;
- mobilization / demobilization basis;
- fuel-surcharge trigger;
- operator inclusion or exclusion;
- attachment inclusion or exclusion;
- difficult-ground, rock, contaminated-soil and extreme-condition qualifications;
- cleaning, damage and abnormal-wear responsibility;
- disposal and tipping fees;
- permits, engineering, testing, traffic control and bonding exclusions;
- payment terms;
- quote validity;
- cancellation terms; and
- contract or force-account precedence.

## Default Commercial Controls

- Compact equipment and labour-only service calls: **4-hour minimum**, unless a vendor minimum is greater.
- Heavy equipment, trucking and subcontracted specialty equipment: **8-hour minimum**, unless quoted otherwise.
- Standby caused by Iron House: not billable.
- Standby caused by client, other trades, access restriction or unavailable workfront: billable at the approved standby rate, subject to the contract.
- Mobilization and demobilization: always visible and separate.
- Fuel surcharge: 0% while the selected benchmark fuel provision is not exceeded; otherwise update from the current source or vendor quote.
- Rate-sheet validity: 30 days unless a shorter supplier quote expiry governs.
- Existing contract, tender or stipulated force-account rates override this standard.

## Required Model Fields

- `regional_market`
- `rate_category`
- `equipment_class`
- `equipment_description`
- `ownership_basis`: `rented`, `owned`, or `subcontracted`
- `rate_basis`: `industry_benchmark`, `vendor_quote`, `owned_cost_model`, or `contract_rate`
- `operator_included`
- `base_rate`
- `rental_period`: `hour`, `day`, `week`, or `month`
- `included_hours`
- `overtime_hour_rate`
- `fuel_included`
- `fuel_surcharge_percent`
- `damage_waiver_percent_or_amount`
- `attachment_rate`
- `delivery_cost`
- `pickup_cost`
- `mobilization_rate`
- `minimum_billable_hours`
- `standby_rate`
- `target_margin_percent`
- `calculated_client_rate`
- `selected_client_rate`
- `source_name`
- `source_url`
- `source_effective_date`
- `quote_expiry_date`
- `override_reason`
- `approval_status`

## Approval Control

A written reason and estimator or executive approval are required when:

- the selected client rate is below the applicable industry benchmark;
- final margin is below 10%;
- mobilization is waived;
- a vendor quote has expired;
- operator inclusion is changed;
- the minimum charge is waived; or
- a source or class cannot be identified.

## Review Cycle

Review public benchmarks annually, fuel treatment monthly during active estimating, and vendor rental rates for every tender or at least quarterly. Replace assumptions with Iron House actual rental invoices, production records and project results as they become available.
