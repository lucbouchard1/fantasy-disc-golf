from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt
import numpy as np
import dglib, math

def make_weekly_plot(teamData, filename, status='start', title="Weekly Cash Totals"):
    df = teamData[teamData.status == status]
    weekly = df[['week', 'coach', 'cash']].groupby(by=['week', 'coach'], as_index=False).sum()
    weekly = weekly.pivot(index="week", columns="coach", values="cash")
    ax = weekly.cumsum().plot(title=title, ylabel="Total Cash ($)", xlabel="Week", style='--x')
    ax.set_ylim(bottom=0)
    plt.savefig('docs/' + filename)

def make_place_string(place):
    if (math.isnan(place)):
        return 'N/A'

    place = int(place)
    if place > 10 and place < 14:
        return str(place) + 'th'
    elif place % 10 == 1:
        return str(place) + 'st'
    elif place % 10 == 2:
        return str(place) + 'nd'
    elif place % 10 == 3:
        return str(place) + 'rd'
    return str(place) + 'th'

def build_lineups(tournamentData, numWeeks):
    tournaments = dglib.get_tournaments(year=2025)
    teamData = dglib.get_team_data(tournamentData, numWeeks, include_nonplaying=True)

    lineups = {
        "Luc": [],
        "Marina": [],
        "Wyatt": [],
        "Max": []
    }

    for coach in lineups:
        for w in range(1, numWeeks+1):
            name = tournaments[tournaments.week == w].iloc[0]['tournament_name']
            lineups[coach].append({
                'tournament': name,
                'starters': [(p['entered_name'].title(), make_place_string(p['place']), p['points']) for _, p in
                    teamData[(teamData.week == w) & (teamData.coach == coach) & (teamData.status == 'start')].sort_values(by='cash', ascending=False).iterrows()],
                'bench': [(p['entered_name'].title(), make_place_string(p['place']), p['points']) for _, p in
                    teamData[(teamData.week == w) & (teamData.coach == coach) & (teamData.status == 'bench')].sort_values(by='cash', ascending=False).iterrows()],
            })

    return lineups

def build_player_totals(tournamentData, teamData):
    seasonTotals = tournamentData[['name', 'cash']].groupby('name', as_index=False).agg(
        cash=('cash', 'sum'),
        avg=('cash', 'mean')
    )
    seasonTotals = seasonTotals.sort_values('cash', ascending=False).iloc[0:50]

    playerTotals = []
    for _, p in seasonTotals.iterrows():
        playerTotals.append({'name': p['name'], 'cash': p['cash'], 'avg': p['avg']})

    return playerTotals

def build_weekly_results(tournamentData, teamData, status='start'):
    df = teamData[teamData.status == status]
    tournaments = dglib.get_tournaments(year=2025)
    weeklyDf = df[['week', 'coach', 'points']].groupby(by=['week', 'coach'], as_index=False).sum()
    weeklyDf = weeklyDf.pivot(index="week", columns="coach", values="points")

    weekly = []
    for i, w in weeklyDf.iterrows():
        weekly.append([tournaments.iloc[i-1]['tournament_name']] + list(w))

    return weekly, list(weeklyDf.columns)

def build_standings(tournamentData, teamData, status='start'):
    df = teamData[teamData.status == status]
    weekly = df[['week', 'coach', 'points']].groupby(by=['week', 'coach'], as_index=False).sum()
    weekly = weekly.pivot(index="week", columns="coach", values="points")
    totals = weekly.sum().sort_values(ascending=False)

    standings = []
    for t in totals.items():
        standings.append(
            {'name': t[0], 'points': t[1]}
        )
    return standings

def build_template_variables(year=2025):
    numWeeks = len(dglib.get_tournaments(year=year))
    tournamentData = dglib.get_tournament_data(year=year)
    teamData = dglib.get_team_data(tournamentData, numWeeks, include_nonplaying=True)

    lineups = build_lineups(tournamentData, numWeeks)
    standings = build_standings(tournamentData, teamData)
    playerTotals = build_player_totals(tournamentData, teamData)
    weekly, weeklyHeader = build_weekly_results(tournamentData, teamData)
    bench, benchHeader = build_weekly_results(tournamentData, teamData, status='bench')
    benchTotals = build_standings(tournamentData, teamData, status='bench')
    make_weekly_plot(teamData, 'weekly.png')
    make_weekly_plot(teamData, 'bench.png', status='bench', title="Bench Cash Totals")

    return {
        'currentYear': 2025,
        'currentWeek': numWeeks,
        'standings': standings,
        'weekly': weekly,
        'weeklyHeader': weeklyHeader,
        'bench': bench,
        'benchHeader': benchHeader,
        'benchTotals': benchTotals,
        'playerTotals': playerTotals,
        'lineups': lineups
    }


environment = Environment(loader=FileSystemLoader("templates/"))
template = environment.get_template("index.html")
variables = build_template_variables()

content = template.render(**variables)

with open('docs/index.html', mode="w", encoding="utf-8") as site:
    site.write(content)
    print("Built site.")