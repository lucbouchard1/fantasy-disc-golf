from jinja2 import Environment, FileSystemLoader
import dglib


def build_template_variables():
    numWeeks = 16
    tournamentData = dglib.get_tournament_data()
    teamData = dglib.get_team_data(tournamentData, numWeeks)  # NOTE: If player didn't play they won't be included in this DF

    df = teamData[teamData.status == 'start']
    weekly = df[['week', 'coach', 'cash']].groupby(by=['week', 'coach'], as_index=False).sum()
    weekly = weekly.pivot(index="week", columns="coach", values="cash")
    totals = weekly.sum().sort_values(ascending=False)

    standings = []
    for t in totals.items():
        standings.append(
            {'name': t[0], 'cash': t[1]}
        )

    return {
        'standings': standings
    }



environment = Environment(loader=FileSystemLoader("templates/"))
template = environment.get_template("index.html")
variables = build_template_variables()

content = template.render(**variables)

with open('docs/index.html', mode="w", encoding="utf-8") as site:
    site.write(content)
    print("Built site.")