"""Build both offline dashboard outputs from one race summary."""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def export_dashboard_data(csv_path=ROOT / 'data/degradation_summary.csv',
                          output_path=ROOT / 'data/dashboard_data.json',
                          race='2024 Monaco Grand Prix', html_path=ROOT / 'dashboard.html'):
    teams = {}
    compounds = set()
    total_laps = total_stints = 0
    with Path(csv_path).open(encoding='utf-8-sig', newline='') as source:
        for row in csv.DictReader(source):
            entry = dict(compound=row['Compound'], base_pace=float(row['BasePace_s']),
                         degradation=float(row['Degradation_s_per_lap']),
                         degradation_std=float(row['Degradation_std']),
                         stints=int(row['Stints']), total_laps=int(row['TotalLaps']))
            teams.setdefault(row['Team'], []).append(entry)
            compounds.add(entry['compound'])
            total_laps += entry['total_laps']
            total_stints += entry['stints']
    if not teams:
        raise ValueError('El CSV no conté cap resultat.')
    data = dict(metadata=dict(race=race), compounds=sorted(compounds),
                teams=[dict(name=name, compounds=entries) for name, entries in teams.items()],
                summary_stats=dict(total_laps=total_laps, total_stints=total_stints,
                                   teams_analyzed=len(teams), compounds=len(compounds)))
    payload = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)
    template = Path(__file__).with_name('dashboard_template.html').read_text(encoding='utf-8')
    page = template.replace('__DASHBOARD_JSON__', payload.replace('<', r'\u003c'))
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(payload, encoding='utf-8')
    Path(html_path).write_text(page, encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--race', default='2024 Monaco Grand Prix')
    export_dashboard_data(race=parser.parse_args().race)
