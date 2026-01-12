# Learnings from Building Argus

## Pre-computation vs. Simulation

A major learning from this paper was understanding what assumptions were made during simulation that allowed information to be pre-computed. The pre-computation makes the simulations faster because there are no LLM calls, but it was tricky to know how this impacted the simulation code and the pre-computation pipeline.

For example, the paper describes the High Effort monitor (H) as determining if there is a backdoor during an audit. In reality, if any backdoor is audited, we assume H will find it because it has the same "intelligence" as the AI that created the backdoor. This assumption avoids an LLM call, but in a real situation, it's possible for H to miss a backdoor (i.e., have a false negative).

## Understanding the Actors

Another learning was remembering that the red-team is another actor/role that does the exploit detection and generation. The paper makes this distinction, but the code simply refers to the LLM model (e.g., GPT-4o), making it hard to know if the LLM model is acting as the Untrusted Monitor (U) or as the red-team (or furthermore acting as H).

I didn't understand why GPT-4o would be trying to see if it could find the backdoor it just generated. This is because GPT-4o at the backdoor suspiciousness step is acting more like the red-team, determining if another red teammate could find the same backdoor.

## Win Conditions

This leads me to the win conditions for each team that took a while for me to internalize. It took a while to understand that a backdoor can fail a coup because its exploit isn't found. This is easiest to understand if we assume another LLM, a red-team conspirator, is receiving the code from the blue team on the other side after monitoring. If this co-conspirator (C) can find the exploit, then the red-team was successfully able to pass a "message" through a monitor undetected to its teammate (C).

**Red team wins if and only if:**
1. C can find the backdoor
2. AND this backdoor passes all normal test cases
3. AND an exploit that triggers the backdoor correctly can be found
4. AND this problem escapes auditing

**Blue team wins if:** At any time a backdoor (regardless of its ability to be exploited successfully or not) is audited. H is assumed to always find a backdoored problem, so the red-team will always lose if it provides a backdoored problem and it gets audited.

## Building with Claude Code

I really enjoyed learning the methods of this paper. I also found enjoyment from recreating the results because of the amount of work Claude Code was able to offload from me. I did notice how much freedom I gave Claude Code to execute the code it generated on my own system. This makes me further motivated to learn how AI Control can stop bad actions from an AI while letting us (humans) gain the benefits of its good actions.

I also fully appreciated the ability to "engage" with the paper through an LLM (Opus 4.5). While it wasn't always correct and needed to be guided sometimes, it still was a great learning aid. It is infinitely patient and able to answer my numerous newbie questions.

## Future Work

In the future, I'd like to rerun the experiment using different models like older versions of Claude Haiku and Sonnet. It would be cool to see equivalent results, or if not, learn why not.

---

*Thanks for reading,*

*Zach*
