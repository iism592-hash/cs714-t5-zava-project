# B2C synthesis model

Only the B2C Synthesizer uses `gpt-5-mini`. Supervisor and Safety Officer retain
the existing `AZURE_AI_MODEL_DEPLOYMENT_NAME` setting, currently `gpt-4.1-mini`.
Inventory retrieval and the B2B model settings are unchanged.

`B2C_SYNTHESIZER_MODEL_DEPLOYMENT_NAME` overrides the synthesis deployment.
`B2C_SYNTHESIZER_MAX_COMPLETION_TOKENS` defaults to 4096, including reasoning
and visible output. The `gpt-5-mini` deployment uses low reasoning effort.
Streaming and the non-streaming fallback use the same options. Empty synthesis
responses trigger fallback, then a visible error if fallback is also empty.
The health endpoint reports the model for each role in `agent_models`.

Validation: nine role-routing and catalog-grounding regression tests pass.
Live Azure preflight returned complete fixture responses in both modes:
non-streaming 5.21 seconds; streaming 3.68 seconds, first text at 2.85 seconds.
These are individual observations, not a comparison proving improved quality.

Deployment overlays only `agent_service.py` onto the previous B2C image,
`catalog-grounding-2`, digest
`sha256:22fe77f9b21779618cf26e7a052823f50156faca2746f054e0f2573c277e3f9c`.
The service file also records the existing deployed SSE, multi-item lookup and
cart-confirmation implementation that was previously absent from Git HEAD.
Unrelated local infrastructure and dependency changes are excluded.

Deployed B2C image: `synthesizer-gpt5-mini-2`, pinned to
`sha256:b6d89eb2221c02794a7f6de32c29f0c665658b0460b583d6833b761354b421e9`.
The live health endpoint confirms Synthesizer `gpt-5-mini` and Supervisor/Safety
Officer `gpt-4.1-mini`. B2B retains its `inventory-compact-ui` image.
After a brief startup connection failure, the backend became healthy.

The live GFCI project query completed all four stages and returned four catalog
links with prices. The voltage tester, insulated gloves and safety goggles
were labelled for separate preparation, without shopping links. The input
and send button became available again after the response completed.
Opening the GFCI link resolved to catalog SKU `ELOTL002`, in stock, at the
same $26.87 price shown in the response.
