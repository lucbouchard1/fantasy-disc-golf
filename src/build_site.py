from jinja2 import Environment, FileSystemLoader
import dglib, math

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
    tournaments = dglib.get_tournaments()
    teamData = dglib.get_team_data(tournamentData, numWeeks, include_nonplaying=True)

    lineups = {
        "Luc": [],
        "Marina": [],
        "Wyatt": []
    }

    for coach in lineups:
        for w in range(1, numWeeks+1):
            name = tournaments[tournaments.week == w].iloc[0]['tournament_name']
            lineups[coach].append({
                'tournament': name,
                'starters': [(p['entered_name'].title(), make_place_string(p['place']), p['cash']) for _, p in
                    teamData[(teamData.week == w) & (teamData.coach == coach) & (teamData.status == 'start')].sort_values(by='cash', ascending=False).iterrows()],
                'bench': [(p['entered_name'].title(), make_place_string(p['place']), p['cash']) for _, p in
                    teamData[(teamData.week == w) & (teamData.coach == coach) & (teamData.status == 'bench')].sort_values(by='cash', ascending=False).iterrows()],
            })

    return lineups

def build_player_totals(tournamentData, teamData):
    seasonTotals = tournamentData[['name', 'cash']].groupby('name', as_index=False).sum()
    seasonTotals = seasonTotals.sort_values('cash', ascending=False).iloc[0:50]

    playerTotals = []
    for _, p in seasonTotals.iterrows():
        playerTotals.append({'name': p['name'], 'cash': p['cash']})

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
    numWeeks = len(dglib.get_tournaments())
    tournamentData = dglib.get_tournament_data()
    teamData = dglib.get_team_data(tournamentData, numWeeks)

    lineups = build_lineups(tournamentData, numWeeks)
    standings = build_standings(tournamentData, teamData)
    playerTotals = build_player_totals(tournamentData, teamData)
    weekly, weeklyHeader = build_weekly_results(tournamentData, teamData)

    return {
        'currentYear': 2024,
        'currentWeek': numWeeks,
        'standings': standings,
        'weekly': weekly,
        'weeklyHeader': weeklyHeader,
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