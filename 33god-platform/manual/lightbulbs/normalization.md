# What is Normalization?

Status: **modal copy drafted [P]; the concept and the dock's bobbing bulb are Jarad's [J].** Station: the receiving dock's bench (hook-hub), beside the first parcel being opened. Governed by [`../world/tone.md`](../world/tone.md). Revision 1, 2026-11-11.

## Modal copy

**What is Normalization?**

Picture the receiving dock. Its real name is hook-hub.

Vendors' vans pull up all day, and no two pack alike. Each parcel carries a label in the vendor's own words:

> Claude, Codex, Kimi: `UserPromptSubmit`  
> Copilot: `userPromptSubmitted`  
> Gemini: `BeforeAgent`  
> opencode: `chat.message`

A clerk opens every parcel and copies the news onto one house post-it: "conversation turn started." The vendor's name goes in the small "from" corner, never the headline. The original packing slip is stapled to the back.

You'll hear this called **normalization**: many shapes come in, one agreed shape goes out.

Why bother? Without the dock, every reader on the floor would have to learn every vendor's accent. With it, each accent is learned once, at the door. A new vendor tomorrow means only the dock learns something new.

You've probably done this. A shop that takes Stripe and PayPal turns both into one "payment received" record.

You'll spot it again at the ticket board's bell, where the rules cabinet turns the board's webhooks into house post-its, and at the clock, where every chore goes out in the same envelope.

*Optional closer:* databases use the same word for a cousin idea, storing each fact once. Different job, same instinct.

## Notes for the page

- **Word count** is about 190 outside the label strip. Trim from "Why bother" first, then the closer, if the modal runs long.
- **The label strip is the "before" picture.** Show it as four handwritten parcel labels, not a code block.
- **One real term:** "normalization". The vendor labels are the evidence, not new vocabulary. If a page budget needs it, cut to two labels.
- **Both readers:** the veteran gets the exact claim (one house shape, vendor identity in a field, raw payload kept). The vibe coder gets Stripe plus PayPal.
- **What it does not claim:** the dock normalizes the label, not the whole body. The vendor's raw payload still rides along, stapled to the back, so a veteran who opens an archived note will find the vendor's own JSON. The card on the receiving dock says so.
- **Second sightings** (the ticket board's bell, the clock): verify the n8n Plane-webhook workflow and the clock's envelope shape before a page prints them.

## Evidence (one line)

`bloodbank/services/agent-hooks/hooks.master.json` maps each vendor's native hook to one lifecycle role (`prompt_submit` to `bloodbank.conversation.turn.started`); `clients/*.py` build one CloudEvents envelope checked by `core/validate.py` `assert_contract`, with the original payload kept in `data` (`raw`); `hook-hub/handlers.toml` matches jobs on `on = ["prompt_submit"]`. Read 2026-11-11.
