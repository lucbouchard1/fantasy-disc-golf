from jinja2 import Environment, FileSystemLoader
import dglib

def build_player_totals(tournamentData, teamData):
    seasonTotals = tournamentData[['name', 'cash']].groupby('name', as_index=False).sum()
    seasonTotals = seasonTotals.sort_values('cash', ascending=False).iloc[0:50]

    playerTotals = []
    for _, p in seasonTotals.iterrows():
        playerTotals.append({'name': p[0], 'cash': p[1]})

    return playerTotals

def build_weekly_results(tournamentData, teamData):
    df = teamData[teamData.status == 'start']
    tournaments = dglib.get_tournaments()
    weeklyDf = df[['week', 'coach', 'cash']].groupby(by=['week', 'coach'], as_index=False).sum()
    weeklyDf = weeklyDf.pivot(index="week", columns="coach", values="cash")

    weekly = []
    for i, w in weeklyDf.iterrows():
        weekly.append([tournaments.iloc[i-1]['tournament_name']] + list(w))

    return weekly, list(weeklyDf.columns)

def build_standings(tournamentData, teamData):
    df = teamData[teamData.status == 'start']
    weekly = df[['week', 'coach', 'cash']].groupby(by=['week', 'coach'], as_index=False).sum()
    weekly = weekly.pivot(index="week", columns="coach", values="cash")
    totals = weekly.sum().sort_values(ascending=False)

    standings = []
    for t in totals.items():
        standings.append(
            {'name': t[0], 'cash': t[1]}
        )
    return standings

def build_template_variables():
    numWeeks = 1
    tournamentData = dglib.get_tournament_data()
    teamData = dglib.get_team_data(tournamentData, numWeeks)  # NOTE: If player didn't play they won't be included in this DF

    standings = build_standings(tournamentData, teamData)
    playerTotals = build_player_totals(tournamentData, teamData)
    weekly, weeklyHeader = build_weekly_results(tournamentData, teamData)

    return {
        'currentYear': 2024,
        'currentWeek': numWeeks,
        'standings': standings,
        'weekly': weekly,
        'weeklyHeader': weeklyHeader,
        'playerTotals': playerTotals
    }


environment = Environment(loader=FileSystemLoader("templates/"))
template = environment.get_template("index.html")
variables = build_template_variables()

content = template.render(**variables)

with open('docs/index.html', mode="w", encoding="utf-8") as site:
    site.write(content)
    print("Built site.")