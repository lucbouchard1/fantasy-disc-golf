from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt
import pandas as pd
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

def build_lineups(tournamentData, numWeeks, coaches):
    tournaments = dglib.get_tournaments(year=2025)
    teamData = dglib.get_team_data(tournamentData, numWeeks, coaches, include_nonplaying=True)

    lineups = { c:[] for c in coaches }

    for coach in lineups:
        for w in range(1, numWeeks+1):
            name = tournaments[tournaments.week == w].iloc[0]['tournament_name']
            lineups[coach].append({
                'tournament': name,
                'starters': [(p['entered_name'].title(), make_place_string(p['place']), p['points']) for _, p in
                    teamData[(teamData.week == w) & (teamData.coach == coach) & (teamData.status == 'start')].sort_values(by='points', ascending=False).iterrows()],
                'bench': [(p['entered_name'].title(), make_place_string(p['place']), p['points']) for _, p in
                    teamData[(teamData.week == w) & (teamData.coach == coach) & (teamData.status == 'bench')].sort_values(by='points', ascending=False).iterrows()],
            })

    return lineups

def build_live_score_lineups(tournamentData, week, coaches):
    tournaments = dglib.get_tournaments(year=2025)
    teamData = dglib.get_team_data(tournamentData, week, coaches, include_nonplaying=True)

    lineups = {}

    for coach in coaches:
        lineups[coach] = [p['entered_name'].title() for _, p in
                teamData[(teamData.week == week) & (teamData.coach == coach) & (teamData.status == 'start')].iterrows()]

    return lineups

def build_player_totals(tournamentData, teamData):
    seasonTotals = tournamentData[['name', 'points']].groupby('name', as_index=False).agg(
        points=('points', 'sum'),
        avg=('points', 'mean')
    )
    seasonTotals = seasonTotals.sort_values('points', ascending=False).iloc[0:50]

    playerTotals = []
    for _, p in seasonTotals.iterrows():
        playerTotals.append({'name': p['name'], 'points': p['points'], 'avg': p['avg']})

    return playerTotals

def build_weekly_results(tournamentData, teamData, status='start'):
    df = teamData[teamData.status == status]
    tournaments = dglib.get_tournaments(year=2025)
    weeklyDf = df[['week', 'coach', 'points']].groupby(by=['week', 'coach'], as_index=False).sum()
    weeklyDf = weeklyDf.pivot(index="week", columns="coach", values="points")

    weekly = []
    for i, w in weeklyDf.iterrows():
        weekly.append([tournaments.iloc[int(i-1)]['tournament_name']] + list(w))

    return weekly, list(weeklyDf.columns)

def build_weekly_win_results(tournamentData, teamData):
    df = teamData[teamData.status == 'start']
    weekly = df[['week', 'coach', 'opponent', 'points']].groupby(by=['week', 'coach'], as_index=False).agg({
        'points': 'sum',
        'opponent': 'first'
    })
    opps = weekly[['week', 'opponent']]
    r = opps.merge(weekly[['week', 'coach', 'points']],
            left_on=['week', 'opponent'],
            right_on=['week', 'coach']
        )
    weekly['opponent_points'] = r['points']
    weekly['win'] = weekly['opponent_points'] < weekly['points']
    weeklyDf = weekly.pivot(index="week", columns="coach", values="win")

    weekly = []
    for i, w in weeklyDf.iterrows():
        weekly.append(list(w))

    return weekly

def build_point_totals(tournamentData, teamData, status='start'):
    df = teamData[teamData.status == status]
    weekly = df[['week', 'coach', 'points']].groupby(by=['week', 'coach'], as_index=False).sum()
    weekly = weekly.pivot(index="week", columns="coach", values="points")
    totals = weekly.sum().sort_values(ascending=False)

    point_totals = []
    for t in totals.items():
        point_totals.append(
            {'name': t[0], 'points': t[1]}
        )
    return point_totals

def build_standings(numWeeks, tournamentData, teamData, opponents):
    df = teamData[teamData.status == 'start']
    weekly = df[['week', 'coach', 'opponent', 'points']].groupby(by=['week', 'coach'], as_index=False).agg({
        'points': 'sum',
        'opponent': 'first'
    })
    opps = weekly[['week', 'opponent']]
    r = opps.merge(weekly[['week', 'coach', 'points']],
            left_on=['week', 'opponent'],
            right_on=['week', 'coach']
        )
    weekly['opponent_points'] = r['points']
    weekly['win'] = weekly['opponent_points'] < weekly['points']
    totals = weekly[['coach', 'win']].groupby(by='coach', as_index=False).sum()
    totals['record'] = totals['win'] / numWeeks
    totals = totals.sort_values('record', ascending=False)

    standings = []
    for _, r in totals.iterrows():
        standings.append(
            {'name': r['coach'], 'record': r['record']}
        )
    return standings

def build_template_variables(year=2025):
    coaches = ['Luc', 'Marina', 'Wyatt', 'Max']
    tournaments = dglib.get_tournaments(year=year)
    numWeeks = sum([isinstance(t.url, str) for _, t in tournaments.iterrows()])
    tournamentData = dglib.get_tournament_data(year=year)
    schedule, opponents = dglib.get_schedule(coaches)
    teamData = dglib.get_team_data(tournamentData, numWeeks, coaches, include_nonplaying=True)

    standings = build_standings(numWeeks, tournamentData, teamData, opponents)
    lineups = build_lineups(tournamentData, numWeeks, coaches)
    liveWeek = numWeeks+1 if numWeeks+1 < len(schedule) else len(schedule)
    liveScores = build_live_score_lineups(tournamentData, liveWeek, coaches)
    weeklyWins = build_weekly_win_results(tournamentData, teamData)

    pointTotals = build_point_totals(tournamentData, teamData)
    playerTotals = build_player_totals(tournamentData, teamData)
    weekly, weeklyHeader = build_weekly_results(tournamentData, teamData)
    bench, benchHeader = build_weekly_results(tournamentData, teamData, status='bench')
    benchTotals = build_point_totals(tournamentData, teamData, status='bench')
    make_weekly_plot(teamData, 'weekly.png')
    make_weekly_plot(teamData, 'bench.png', status='bench', title="Bench Cash Totals")

    return {
        'currentYear': 2025,
        'currentWeek': numWeeks,
        'standings': standings,
        'pointTotals': pointTotals,
        'weekly': weekly,
        'weeklyWins': weeklyWins,
        'weeklyHeader': weeklyHeader,
        'bench': bench,
        'benchHeader': benchHeader,
        'benchTotals': benchTotals,
        'playerTotals': playerTotals,
        'lineups': lineups,
        'schedule': schedule,
        'tournaments': list(tournaments['tournament_name']),
        'liveWeek': liveWeek,
        'matchup1': schedule[liveWeek - 1][0],
        'matchup2': schedule[liveWeek - 1][1],
        'liveScores': liveScores
    }


environment = Environment(loader=FileSystemLoader("templates/"))
template = environment.get_template("index.html")
live = environment.get_template("live.html")
variables = build_template_variables()

content = template.render(**variables)
liveContent = live.render(**variables)

with open('docs/index.html', mode="w", encoding="utf-8") as site:
    site.write(content)

with open('docs/live.html', mode="w", encoding="utf-8") as site:
    site.write(liveContent)

print("Built site.")