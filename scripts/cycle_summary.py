import json
import pathlib

path = pathlib.Path(__file__).resolve().parents[1] / 'outbox' / 'opportunity_dispatches.json'
with path.open('r', encoding='utf-8') as f:
    data = json.load(f)

dispatches = data['dispatches']
cycle_id = dispatches[0]['cycle_id']
count = len(dispatches)
lead = max(dispatches, key=lambda d: d['confidence_score'])['title']

print(f'Cycle: {cycle_id}')
print(f'Dispatches: {count}')
print(f'Lead: {lead}')
