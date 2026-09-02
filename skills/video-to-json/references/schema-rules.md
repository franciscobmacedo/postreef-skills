# Schema rules for extraction from media

These rules come from running schema-constrained extraction over thousands of videos through Gemini's `responseSchema`, and they match the constraints of OpenAI strict mode and Anthropic structured outputs closely enough to be a safe common denominator.

## Hard constraints (the call fails or the keyword is ignored)

| Rule | Why |
|---|---|
| Top level must be `{"type": "object", "properties": {...}}` | Providers reject bare arrays/strings at the top |
| No type unions: `["string", "null"]` is rejected | Gemini's responseSchema; OpenAI strict mode also dislikes nullable-by-union. Express optional by leaving the field out of `required` |
| `enum` only on `"type": "string"`, and every value a string | No numbers, no `null` inside enums |
| `additionalProperties`, `pattern`, `minItems`, `maxItems`, `uniqueItems`, `default`, `format` may be stripped before the model sees them | The AI SDK strips several of these for Gemini; treat them as docs |
| Inline schema ≤ 100KB (Post Reef limit); keep it far smaller than that | Long schemas dilute attention |

## Soft rules (quality)

1. **Descriptions are instructions.** Write them in the imperative, say where the value comes from and what to do when absent.
   - Bad: `"price": {"type": "string", "description": "price"}`
   - Good: `"price_mentioned": {"type": "string", "description": "Price as stated in the video or shown on screen, with currency symbol (e.g. \"$129\"). Omit if no price is ever given."}`
2. **Don't require what the content might not contain.** `required` should be the fields that make the object meaningful (a recipe without `ingredients` is not a recipe). Everything else optional.
3. **One or two levels of nesting.** `steps: [{text, duration_minutes}]` is fine; `sections[].subsections[].steps[].substeps[]` degrades.
4. **Arrays of objects over parallel arrays.** `ingredients: [{name, quantity, unit}]`, not `ingredient_names[]` + `ingredient_quantities[]`.
5. **Enums for anything you'll branch on.** `verdict: recommended|mixed|not_recommended` beats a free-text `verdict`.
6. **Say the output language** in descriptions if it must differ from the content's language.
7. **Don't add fields you won't use.** Every field is a chance to hallucinate.
8. **No counts as constraints.** "At least 3 pros" pressures the model to invent a third pro. Ask for "every pro the reviewer states" instead.

## Content-match verdict

Extraction should answer "does this content match the schema's subject?" before filling fields. Post Reef returns this as `outcome: ok | no_match | uncertain` with a `verdictReason`. In a DIY pipeline, replicate it:

```json
{
  "type": "object",
  "properties": {
    "matches": {"type": "string", "enum": ["yes", "no", "unsure"], "description": "Whether the content is actually a product review. 'no' if it is about something else; 'unsure' if the provided inputs are too thin to tell."},
    "reason": {"type": "string", "description": "One sentence explaining the verdict."},
    "review": {"type": "object", "properties": {"...": "..."}, "description": "Fill only when matches is 'yes'."}
  },
  "required": ["matches", "reason"]
}
```

## Worked example: product review

```json
{
  "type": "object",
  "properties": {
    "product_name": {"type": "string", "description": "Exact name of the product being reviewed, as said or shown."},
    "brand": {"type": "string", "description": "Brand or manufacturer, if mentioned."},
    "verdict": {"type": "string", "enum": ["recommended", "mixed", "not_recommended"], "description": "The reviewer's overall verdict."},
    "rating_out_of_10": {"type": "integer", "minimum": 0, "maximum": 10, "description": "Score stated by the reviewer, or implied only if they give a clear numeric sense; omit otherwise."},
    "pros": {"type": "array", "items": {"type": "string"}, "description": "Things the reviewer liked, one short phrase each, in the reviewer's words."},
    "cons": {"type": "array", "items": {"type": "string"}, "description": "Things the reviewer disliked."},
    "price_mentioned": {"type": "string", "description": "Price as stated, with currency. Omit if none."},
    "audience_pushback": {"type": "array", "items": {"type": "string"}, "description": "From the comments: factual corrections or strong disagreements with the review, one per item. Omit if comments are unavailable."}
  },
  "required": ["product_name", "verdict", "pros", "cons"]
}
```

Output for a matching video:

```json
{
  "product_name": "AeroPress Clear",
  "brand": "AeroPress",
  "verdict": "recommended",
  "pros": ["same brew as the original", "you can see the bloom"],
  "cons": ["Tritan scratches faster than polypropylene", "$10 more"],
  "price_mentioned": "$49.95",
  "audience_pushback": ["Several commenters report the plunger seal loosening after ~3 months"]
}
```

Note what's absent: no `rating_out_of_10` because the reviewer never gave one. That's the schema working, not failing.
