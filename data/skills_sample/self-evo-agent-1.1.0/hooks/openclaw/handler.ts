const reminder = `
<self-evolving-agent-reminder>
Before substantial work:
- default to the light loop and escalate only if the task or evidence justifies it
- check whether the learning agenda needs review
- inspect the active learning agenda
- retrieve relevant learnings and capability risks
- identify the likely weakest link
- choose an execution strategy with a verification plan
- if a legacy migration folder exists, search it as read-only evidence

After substantial work:
- log incidents and lessons
- diagnose the weakest capability involved
- keep minor incidental slips in the light loop
- refresh the learning agenda if priorities changed
- create a training unit if the weakness is recurring or high-leverage
- evaluate progress using recorded -> understood -> practiced -> passed -> generalized -> promoted
- promote only validated, transferable strategies
</self-evolving-agent-reminder>
`.trim();

console.log(reminder);
