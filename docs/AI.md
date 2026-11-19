# AI nezávislá na poskytovateli (#20)

- Konfigurace: `config/ai.yaml` (role → pořadí poskytovatelů a modelů, strop volání na běh).
- Kód: `pipeline/ai/` (`Brana.zeptej_se(role, prompt, schema)`), adaptéry `claude_cli`, `anthropic_api`, `openai_api`, `openai_compatible`.
- Poskytovatel je dostupný, jen když je nastaven jeho secret (`CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENAI_COMPATIBLE_API_KEY` + `OPENAI_COMPATIBLE_BASE_URL`). Bez něj se přeskočí; když není žádný, AI krok se přeskočí.
- Ověření (`vyloucit_vyrobce`) nikdy nepoužije výrobce, který výstup navrhl (ZADANI 4.5).
- Do dat patří `poskytovatel` a `model` (`Vysledek.puvod()`) a příznak `*_ai`; citace se ověřuje `overit_citace`.
- Předplatné ChatGPT v Actions použít nejde (zjištění Codexu 18. 11. 2026); OpenAI jen přes `OPENAI_API_KEY`.
- Zatím není napojeno na anotace ani štítky relevance (#18) a nepřibyl `codex.yml` (agent nesmí měnit `.github/workflows`).
