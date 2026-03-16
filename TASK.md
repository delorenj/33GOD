# Question Time

I have some questions that I need cleared up. We've made a lot of progress quickly and I just wanna make sure i'm on the same page as our devs and architect.

1. The Command Adapter
   Tell me more about how this works. I'd like to get a good grip on the ins and outs to build my mental model so i can help expand on it.

- What I gather is that it's a consumer subscribed to all agent bloodbank events that route to one of the 13 OpenClaw agents, but I have other agents I want to be reachable by Bloodbank events - would I want to extend this command Adapter to include those agents or would you consider this "the openclaw" consumer?

1. The Infra Dispatcher
   What exactly is the infra dispatcher? How does it relate to OpenClaw hooks?

- I do have an agentic infra team consisting of architect Lenoon and his boss and DoE Grolf (both OpenClaw agents), but not sure how this dispatcher was implemented to service them.
- I don't intend for this 33GOD pipeline to be architected in a way that locks in frameworks - openclaw should be supported as a modular piece, with its hooks being one of many possible implementations.

1. Plane Ticket State Change
   How is this implemented? When tickets are created or their state changes, a webhook is called: <https://bloodbank.33god.delo.sh/event?secret=00c2599520fda1904aaf86e68d6a47935b068ef11d135da608bdfa3f8bd996f7>. I would like that endpoint to merely convert the hook into the equivalent bloodbank event and fire it off, Then some consumer (the command adapter? Something else like a Plane Adapter) inspects the ticket, checking the label for an explicitly mentioned agent (openclaw or otherwise), checking the state - if it's todo, then someone should pick it up - explicitly defined agent missing, then Cack should examine it and delegate how he sees fit.
