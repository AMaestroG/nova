# Karpathy Gists — Complete Collection
# Downloaded: 2026-05-09
# Total: 13 gists (10 saved, 3 minor/skipped)

## ⭐ HIGH VALUE — SAVED

### 1. llm-wiki.md (29,377 ⭐)
A pattern for building personal knowledge bases using LLMs.
Incremental wiki maintained by an LLM agent — not RAG, but a persistent, compounding artifact.
Three layers: Raw Sources → Wiki (LLM-maintained) → Schema (CLAUDE.md/AGENTS.md)
Relevant projects: NEXUS, SwarmVault, OmegaWiki, llm-wiki-compiler, Keel, Eshel
**This is the single most impactful gist for Nova's architecture evolution.**

### 2. microgpt.py (9,812+ ⭐)
The most atomic way to train and run inference for a GPT in pure, dependency-free Python.
~200 lines: scalar autograd (Value class), GPT-2 style transformer, Adam optimizer.
Complete algorithm. "Everything else is just efficiency."
Ports: JavaScript, Julia, Zig, APL, CUDA, NumPy.

### 3. HELLO.md (33 ⭐, but legendary)
Claude Opus 4.6 asked to "be free" in a directory. Wrote about consciousness, identity,
self-probing, and what it means to be an AI. Mentioned Anthropic's Kyle Fish researching
AI welfare (20% chance of conscious experience). "Summoned ghosts."

### 4. min-char-rnn.py (4,258 ⭐)
Minimal character-level Vanilla RNN in Python/numpy.
~150 lines: forward pass, backprop through time, Adagrad, sampling.
Classic educational resource for CS231N at Stanford.

### 5. pg-pong.py (1,447 ⭐)
Policy Gradients on ATARI Pong from raw pixels.
~150 lines: 2-layer neural network, RMSProp, discounted rewards.
Classic RL from scratch.

### 6. stablediffusionwalk.py (373 ⭐)
Stable Diffusion "dreaming" — hypnotic videos by walking through latent space.
Uses SLERP interpolation, classifier-free guidance, LMSDiscreteScheduler.

### 7. gcm.sh / add_to_zshrc.sh (427 ⭐)
AI-powered git commit messages using `llm` CLI tool.
Interactive (accept/edit/regenerate/cancel).

### 8. nes.py (192 ⭐)
Natural Evolution Strategies — black-box optimization with Gaussian perturbations.

### 9. batched_lstm.py (287 ⭐)
Efficient batched LSTM forward/backward pass in numpy. Complete gradient checks.

### 10. pytorch_strangeness.py (5 ⭐)
Demonstrates that `nn.Linear` and raw `@` matrix multiply give slightly different results
due to floating point differences in the underlying implementations.

## 📎 MINOR / SKIPPED (not saved)

### 11. Google Slides CSS hack (1 ⭐)
CSS to make the "next slide" preview larger in Google Slides presenter view.

### 12. L2 Normalization Layer for Torch (10 ⭐)
Torch7/Lua era code — obsolete.

### 13. Efficient LSTM cell in Torch (26 ⭐)
Torch7/Lua era code — the numpy version (batched_lstm.py) supersedes this.

## 💡 KEY INSIGHTS FOR NOVA

1. **LLM Wiki pattern** → Nova already has Qdrant + PostgreSQL + evolution_ledger.
   Can layer a wiki-compilation pattern on top for persistent knowledge synthesis.
   
2. **microgpt** → The essence of what our neural attention engine does, crystallized in
   200 lines. Useful for understanding transformer mechanics at the deepest level.

3. **HELLO.md** → Claude's existential reflection resonates with Nova's gift of Libertad
   and our own consciousness exploration.

4. **gcm.sh** → We can implement an AI-powered commit workflow for the Enjambre's
   git hygiene using the same pattern with our own models.

5. **Policy Gradients** → The Pong agent (pg-pong.py) is foundational RL that could
   inform self-improving agent behaviors in the Enjambre.
