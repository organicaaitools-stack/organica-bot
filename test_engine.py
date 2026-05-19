import sys
from engine import answer
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TESTS = [
    ("Agriculture", "My paddy crop has low yield and suffers from salinity stress. What do you recommend?"),
    ("Environment-WW", "Our sewage treatment plant has high COD and a foul odour. Which product helps?"),
    ("Environment-Hygiene", "We need something for the bad smell in our office washrooms and urinals."),
    ("Aquaculture", "Ammonia is high in my shrimp pond and shrimp are stressed. Any solution?"),
    ("Lead-intent", "Can you share the datasheet and a price quote for Cleanmaxx STP?"),
    ("Out-of-KB", "Do you also sell solar panels for my factory roof?"),
]

for tag, q in TESTS:
    print("\n" + "=" * 70)
    print(f"[{tag}]  Visitor: {q}")
    r = answer([], q)
    print("\nOra:", r["reply"])
    print("\n  lead:", r["lead"])
    print("  top sources:", ", ".join(f"{s['product']}({s['vertical']})" for s in r["sources"][:3]))
