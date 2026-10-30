# Block import delay budget

If every Ethereum node took X ms longer to import each block, how much more often would a node finish importing the block only after the [attestation deadline](https://github.com/ethereum/consensus-specs/blob/dev/specs/phase0/validator.md#attesting), 4 s into the slot? This repository answers that question from public [Xatu](https://ethpandaops.io/docs/tooling/xatu/intro/) data, which records when each of about 130 monitoring nodes imports each mainnet block.

The answer prices any delay to block processing. It sets the delay budget in Nethermind's study of the EIP-8141 `MAX_VERIFY_GAS` cap.
<!-- TODO: link the ethresear.ch post once published. -->

## Where the budget sits

Each slot lasts 12 s. A validator attests as soon as its node has imported the slot's block, and 4 s into the slot at the latest, voting for the newest block it has. Any delay to block processing, such as extra load on the node, pushes the import later. The budget `B` is the extra delay we accept.

```text
                  slot n                                   slot n+1
0 s           4 s                         12 s          4 s                        12 s
|-------------|---------------------------|-------------|---------------------------|
              ^                                         ^
              attestation deadline                      attestation deadline

Zoom on one node, first 4 s of slot n (not to scale):

0 s                                                           4 s
|-------------------------------------|=========|-------------|
 block arrives, node imports it       ^    B    ^             ^
                                      |         |             attestation deadline
                                      |         import with added delay
                                      import today

import + B before 4 s: the node attests to the new block
import + B after 4 s:  the node attests to the previous block (a late import)
```

## Result

On 30 September 2026 (UTC), across 133 nodes and 7,179 slots:

| Added delay (ms) | Late imports (%) | Increase (percentage points) |
| ---: | ---: | ---: |
| 0 | 3.86 | |
| 10 | 3.93 | 0.07 |
| 25 | 4.05 | 0.19 |
| 50 | 4.25 | 0.39 |
| 100 | 4.71 | 0.85 |
| 250 | 6.65 | 2.79 |
| 1,000 | 24.14 | 20.28 |

With no added delay, a node imported the slot's block after the deadline in 3.86% of slots. Every extra millisecond raises that share. There is no threshold below which delay is free.

## Method

1. **Data.** Xatu's [`beacon_api_eth_v1_events_block`](https://github.com/ethpandaops/xatu-data/blob/master/schema/beacon_api_.md) table has one row per node and slot. Its `propagation_slot_start_diff` column is the time, in ms from the start of the slot, at which the node's beacon node emitted the beacon API [`block` event](https://ethereum.github.io/beacon-APIs/#/Events/eventstream). The node emits that event once the block passes fork choice's `on_block` handler, so the time includes execution of the payload.
2. **Late import.** We take one row per node and slot, a *node-slot*, and call it late when the import time exceeds 4,000 ms.
3. **Added delay.** We add X ms to every import time and count the late node-slots again. The increase is reported in percentage points of all node-slots.

## Reproduce

Requires Python 3 and the packages in `requirements.txt`.

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 late_share.py                     # 30 September 2026, prints the table above
python3 late_share.py --date 2026-10-01   # any other day
```

The snapshot behind the result is committed in `data/`. Its SHA-256 is `73b7ba343fad23ba7b7dd71a0f4a65d3a2d302b4093a40b623a23408f7071bae`, and it is a byte-for-byte copy of the [public file](https://data.ethpandaops.io/xatu/mainnet/databases/default/beacon_api_eth_v1_events_block/2026/9/30.parquet). Other days are downloaded into `data/` on first use and are not tracked.

## Caveats

- **The nodes are not a random sample.** They are Xatu's monitoring nodes, run by ethPandaOps and community contributors. On 30 September 2026 they spanned six continents and eight consensus clients.
- **Times are seen by the Xatu sentry.** Each time is when the sentry received the event from its beacon node, so it includes the sentry's small lag and its clock error.
- **Optimistic imports count.** In 2.5% of rows the block was imported optimistically (`execution_optimistic` is true), and they are counted like the others.
- **The shift is a counterfactual.** It assumes the extra time adds to import only and changes nothing else in the slot.
- **One day.** The result is a single day's snapshot. Nearby days give similar values (1 October 2026: 3.47% baseline, +0.16 points at 25 ms).

## License

The data is produced by [ethPandaOps Xatu](https://github.com/ethpandaops/xatu-data) and licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The file in `data/` is redistributed unmodified. The code is under the [MIT License](LICENSE).
